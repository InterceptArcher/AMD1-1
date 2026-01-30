import { NextRequest, NextResponse } from 'next/server';
import { PersonalizeRequestSchema } from '@/lib/schemas';
import { extractDomain, inferPersona, inferBuyerStage } from '@/lib/utils/email';
import { enrichCompanyData as enrichCompanyDataRAD } from '@/lib/enrichment/rad-client';
import { selectTemplate } from '@/lib/personalization/template-engine';
import { adaptTemplate } from '@/lib/personalization/llm-adapter';
import { generateMockPersonalizedContent } from '@/lib/anthropic/mock-client';
import {
  createPersonalizationJob,
  storePersonalizationOutput,
  updateJobStatus,
  updateJobEnrichment,
  updateOutputMetadata,
} from '@/lib/supabase/queries';

// Check if running in mock mode (for testing without API keys)
const MOCK_MODE = process.env.MOCK_MODE === 'true';

export async function POST(request: NextRequest) {
  try {
    // Parse and validate request body
    const body = await request.json();
    const validationResult = PersonalizeRequestSchema.safeParse(body);

    if (!validationResult.success) {
      return NextResponse.json(
        {
          error: 'Invalid request data',
          details: validationResult.error.flatten().fieldErrors,
        },
        { status: 400 }
      );
    }

    const { email, cta, name, company, role, modernization_stage, ai_priority } = validationResult.data;
    const requestStartTime = Date.now();

    // Step 1: Extract domain from email
    const domain = extractDomain(email);

    // Step 2: Use user-selected persona and buyer stage (from dropdowns)
    const persona = role as any; // Role maps directly to Persona
    const buyer_stage = modernization_stage as any; // Modernization stage maps to buyer stage

    console.log(`[Personalization] Starting for ${email} at ${company} (${persona}, ${buyer_stage}, ${ai_priority})`);

    // MOCK MODE: Skip database and RAD, use mock AI
    if (MOCK_MODE) {
      console.log('🧪 MOCK MODE: Generating mock personalized content...');

      // Use mock enrichment
      const mockEnrichment = await enrichCompanyDataRAD({ domain, email });

      const personalizedContent = await generateMockPersonalizedContent({
        persona,
        buyer_stage,
        industry: mockEnrichment.industry,
        company_size: mockEnrichment.company_size,
        cta,
      });

      const totalLatency = Date.now() - requestStartTime;

      return NextResponse.json({
        success: true,
        jobId: 'mock-' + Date.now(),
        data: personalizedContent,
        enrichment: {
          company_name: company,
          industry: mockEnrichment.industry,
          company_size: mockEnrichment.company_size,
          confidence_score: mockEnrichment.confidence_score,
        },
        metadata: {
          persona,
          buyer_stage,
          company,
          ai_priority,
          template_used: 'mock-template',
          total_latency_ms: totalLatency,
        },
        mock: true,
      });
    }

    // PRODUCTION MODE: Use RAD enrichment, template selection, and Claude API
    // Step 3: Create initial job record in Supabase
    const jobId = await createPersonalizationJob({
      email,
      name,
      domain,
      cta,
      persona,
      buyer_stage,
      company_name: company,
      ai_priority,
    } as any);

    try {
      // Step 4: RAD Enrichment (10-20s)
      console.log(`[Personalization] Starting RAD enrichment for ${domain}...`);
      const enrichmentStartTime = Date.now();

      const enrichment = await enrichCompanyDataRAD({ domain, email });

      console.log(
        `[Personalization] RAD enrichment completed in ${enrichment.enrichment_duration_ms}ms`
      );
      console.log(`[Personalization] Company: ${enrichment.company_name} (confidence: ${enrichment.confidence_score.toFixed(2)})`);

      // Update job with enrichment data
      await updateJobEnrichment(jobId, enrichment);

      // Step 5: Template Selection (<100ms)
      console.log('[Personalization] Selecting template...');
      const template = selectTemplate(enrichment, persona, buyer_stage);
      console.log(`[Personalization] Selected template: ${template.name}`);

      // Step 6: LLM Adaptation (5-10s)
      console.log('[Personalization] Adapting template with Claude...');
      const adaptation = await adaptTemplate(template, enrichment, persona, buyer_stage);
      console.log(`[Personalization] LLM adaptation completed in ${adaptation.metadata.llm_latency_ms}ms`);

      // Convert adaptation to ClaudeOutput format
      const personalizedContent = {
        headline: adaptation.content.headline,
        subheadline: adaptation.content.subheadline,
        cta_text: adaptation.content.cta_text,
        value_prop_1: adaptation.content.value_prop_1,
        value_prop_2: adaptation.content.value_prop_2,
        value_prop_3: adaptation.content.value_prop_3,
      };

      // Step 7: Store the output in Supabase
      await storePersonalizationOutput(jobId, personalizedContent);

      // Step 8: Update output metadata
      const totalLatency = Date.now() - requestStartTime;
      await updateOutputMetadata(jobId, {
        template_id: adaptation.metadata.template_id,
        template_name: adaptation.metadata.template_name,
        llm_model: adaptation.metadata.model_used,
        llm_latency_ms: adaptation.metadata.llm_latency_ms,
        total_latency_ms: totalLatency,
      });

      // Step 9: Update job status to completed
      await updateJobStatus(jobId, 'completed');

      console.log(`[Personalization] ✅ Completed in ${totalLatency}ms (${totalLatency < 60000 ? 'WITHIN' : 'EXCEEDED'} 60s SLA)`);

      // Step 10: Return the personalized content to frontend
      return NextResponse.json({
        success: true,
        jobId,
        data: personalizedContent,
        enrichment: {
          company_name: enrichment.company_name,
          industry: enrichment.industry,
          company_size: enrichment.company_size,
          employee_count: enrichment.employee_count,
          confidence_score: enrichment.confidence_score,
          sources_used: enrichment.sources_used,
        },
        metadata: {
          persona,
          buyer_stage,
          company,
          ai_priority,
          template_id: adaptation.metadata.template_id,
          template_name: adaptation.metadata.template_name,
          enrichment_duration_ms: enrichment.enrichment_duration_ms,
          llm_latency_ms: adaptation.metadata.llm_latency_ms,
          total_latency_ms: totalLatency,
          sla_met: totalLatency < 60000,
        },
      });
    } catch (error) {
      // Update job status to failed
      await updateJobStatus(jobId, 'failed');

      console.error('[Personalization] ❌ Error:', error);

      // Check for specific error types
      if (error instanceof Error) {
        if (error.message.includes('ANTHROPIC_API_KEY')) {
          return NextResponse.json(
            {
              error: 'Service configuration error',
              message:
                'Claude API key is not configured. Please set ANTHROPIC_API_KEY environment variable.',
              jobId,
            },
            { status: 503 }
          );
        }

        if (error.message.includes('RAD') || error.message.includes('enrichment')) {
          return NextResponse.json(
            {
              error: 'Enrichment error',
              message: 'Failed to enrich company data. Using fallback templates.',
              jobId,
            },
            { status: 500 }
          );
        }
      }

      throw error;
    }
  } catch (error) {
    console.error('API error:', error);

    // Handle specific error types
    if (error instanceof Error) {
      if (error.message.includes('Invalid email format')) {
        return NextResponse.json(
          { error: 'Invalid email format' },
          { status: 400 }
        );
      }

      if (error.message.includes('Supabase')) {
        return NextResponse.json(
          {
            error: 'Database error',
            message: 'Failed to process request. Please check Supabase configuration.',
          },
          { status: 503 }
        );
      }
    }

    // Generic server error
    return NextResponse.json(
      {
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

// Reject non-POST requests
export async function GET() {
  return NextResponse.json(
    { error: 'Method not allowed' },
    { status: 405, headers: { Allow: 'POST' } }
  );
}

export async function PUT() {
  return NextResponse.json(
    { error: 'Method not allowed' },
    { status: 405, headers: { Allow: 'POST' } }
  );
}

export async function DELETE() {
  return NextResponse.json(
    { error: 'Method not allowed' },
    { status: 405, headers: { Allow: 'POST' } }
  );
}
