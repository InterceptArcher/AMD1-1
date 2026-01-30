/**
 * LLM Adaptation Layer
 *
 * Takes selected templates and uses Claude to adapt them with specific company context
 * while maintaining strict length and tone requirements.
 */

import { generatePersonalization } from '../anthropic/client';
import type { PersonalizationTemplate } from './template-engine';
import type { RADEnrichmentResponse } from '../enrichment/rad-client';
import type { Persona, BuyerStage, ClaudeOutput } from '../schemas';
import { fillTemplate } from './template-engine';

export interface AdaptedContent {
  headline: string;
  subheadline: string;
  cta_text: string;
  value_prop_1: string;
  value_prop_2: string;
  value_prop_3: string;
}

export interface AdaptationMetadata {
  template_id: string;
  template_name: string;
  llm_tokens_used?: number;
  llm_latency_ms: number;
  model_used: string;
}

export interface AdaptationResult {
  content: AdaptedContent;
  metadata: AdaptationMetadata;
}

/**
 * Adapt a template using Claude LLM with strict constraints
 */
export async function adaptTemplate(
  template: PersonalizationTemplate,
  enrichment: RADEnrichmentResponse,
  persona: Persona,
  buyerStage: BuyerStage
): Promise<AdaptationResult> {
  const startTime = Date.now();

  // Fill template variables
  const introFilled = fillTemplate(template.intro_template, enrichment, persona, buyerStage);
  const ctaFilled = fillTemplate(template.cta_template, enrichment, persona, buyerStage);

  // Build context for Claude
  const contextPrompt = buildAdaptationPrompt(
    introFilled,
    ctaFilled,
    enrichment,
    persona,
    buyerStage
  );

  // Call Claude to adapt the template
  const claudeOutput = await generatePersonalization({
    prompt: contextPrompt,
    persona,
    buyer_stage: buyerStage,
    industry: enrichment.industry,
    company_size: enrichment.company_size,
    cta: buyerStage
  });

  const latency = Date.now() - startTime;

  return {
    content: {
      headline: claudeOutput.headline,
      subheadline: claudeOutput.subheadline,
      cta_text: claudeOutput.cta_text,
      value_prop_1: claudeOutput.value_prop_1,
      value_prop_2: claudeOutput.value_prop_2,
      value_prop_3: claudeOutput.value_prop_3
    },
    metadata: {
      template_id: template.id,
      template_name: template.name,
      llm_latency_ms: latency,
      model_used: 'claude-3-5-sonnet-20241022'
    }
  };
}

/**
 * Build the adaptation prompt for Claude
 */
function buildAdaptationPrompt(
  introTemplate: string,
  ctaTemplate: string,
  enrichment: RADEnrichmentResponse,
  persona: Persona,
  buyerStage: BuyerStage
): string {
  const companyContext = buildCompanyContext(enrichment);
  const personaContext = buildPersonaContext(persona, buyerStage);

  return `You are adapting B2B marketing content for a specific company and persona.

TEMPLATE GUIDANCE (use as inspiration, but adapt naturally):
Introduction inspiration: "${introTemplate}"
CTA inspiration: "${ctaTemplate}"

${companyContext}

${personaContext}

STRICT REQUIREMENTS:
1. Headline: 6-12 words, compelling and specific to this company
2. Subheadline: 15-25 words, expand on headline with concrete value
3. CTA: 3-6 words, action-oriented and matched to buyer stage
4. Value Props: Each 8-15 words, specific benefits

TONE RULES:
- Professional and confident, not salesy
- Use company name naturally in headline or subheadline
- Reference industry context when relevant
- Match urgency to buyer stage (${buyerStage})
- Speak to persona pain points (${persona})

DO NOT:
- Mention competitors by name
- Make unverifiable claims ("best", "#1", "revolutionary")
- Use exclamation marks or emoji
- Include pricing or specific numbers without data
- Use marketing jargon ("synergy", "disrupt", "paradigm shift")

Generate content that feels personal to ${enrichment.company_name} while maintaining the template's strategic intent.`;
}

/**
 * Build company context for Claude
 */
function buildCompanyContext(enrichment: RADEnrichmentResponse): string {
  let context = `COMPANY CONTEXT:
- Name: ${enrichment.company_name}
- Industry: ${enrichment.industry}
- Size: ${enrichment.company_size} (${enrichment.employee_count} employees)
- Location: ${enrichment.headquarters}`;

  if (enrichment.founded_year) {
    const age = new Date().getFullYear() - enrichment.founded_year;
    context += `\n- Founded: ${enrichment.founded_year} (${age} years ago)`;
  }

  if (enrichment.technology && enrichment.technology.length > 0) {
    context += `\n- Technology Stack: ${enrichment.technology.slice(0, 5).join(', ')}`;
  }

  if (enrichment.news_summary) {
    context += `\n- Recent News: ${enrichment.news_summary}`;
  }

  if (enrichment.intent_signal) {
    context += `\n- Buying Intent: ${enrichment.intent_signal} stage`;
  }

  context += `\n- Data Confidence: ${(enrichment.confidence_score * 100).toFixed(0)}%`;

  return context;
}

/**
 * Build persona context for Claude
 */
function buildPersonaContext(persona: Persona, buyerStage: BuyerStage): string {
  const personaDetails: Record<Persona, string> = {
    'Business Leader': 'Executive decision-maker focused on ROI, strategic impact, and business outcomes',
    'IT': 'Technical professional focused on architecture, integrations, security, and maintainability',
    'Finance': 'Financial decision-maker focused on cost optimization, ROI, and budget allocation',
    'Operations': 'Operations professional focused on efficiency, reliability, and workflow automation',
    'Security': 'Security professional focused on risk mitigation, compliance, and protection'
  };

  const stageDetails: Record<BuyerStage, string> = {
    'awareness': 'Early stage - educating, exploring problems and solutions',
    'evaluation': 'Mid stage - comparing options, seeking detailed information',
    'decision': 'Late stage - ready to purchase, needs final validation'
  };

  return `PERSONA & STAGE:
- Persona: ${persona}
  ${personaDetails[persona]}
- Buyer Stage: ${buyerStage}
  ${stageDetails[buyerStage]}`;
}

/**
 * Validate adapted content meets requirements
 */
export function validateAdaptedContent(content: AdaptedContent): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Validate headline length (6-12 words)
  const headlineWords = content.headline.split(/\s+/).length;
  if (headlineWords < 6 || headlineWords > 12) {
    errors.push(`Headline has ${headlineWords} words, expected 6-12`);
  }

  // Validate subheadline length (15-25 words)
  const subheadlineWords = content.subheadline.split(/\s+/).length;
  if (subheadlineWords < 15 || subheadlineWords > 25) {
    errors.push(`Subheadline has ${subheadlineWords} words, expected 15-25`);
  }

  // Validate CTA length (3-6 words)
  const ctaWords = content.cta_text.split(/\s+/).length;
  if (ctaWords < 3 || ctaWords > 6) {
    errors.push(`CTA has ${ctaWords} words, expected 3-6`);
  }

  // Validate value props length (8-15 words each)
  const valueProps = [content.value_prop_1, content.value_prop_2, content.value_prop_3];
  valueProps.forEach((prop, index) => {
    const words = prop.split(/\s+/).length;
    if (words < 8 || words > 15) {
      errors.push(`Value prop ${index + 1} has ${words} words, expected 8-15`);
    }
  });

  // Check for banned phrases/patterns
  const allText = Object.values(content).join(' ').toLowerCase();
  const bannedPatterns = [
    { pattern: /best|#1|number one/i, message: 'Contains superlative claim' },
    { pattern: /competitor names/i, message: 'Mentions competitors' },
    { pattern: /!!|😀|🚀/i, message: 'Contains emoji or multiple exclamation marks' },
    { pattern: /synergy|disrupt|paradigm shift/i, message: 'Contains marketing jargon' }
  ];

  for (const { pattern, message } of bannedPatterns) {
    if (pattern.test(allText)) {
      errors.push(message);
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
}
