import Anthropic from '@anthropic-ai/sdk';
import { ClaudeOutputSchema, type ClaudeOutput } from '../schemas';

const SYSTEM_PROMPT = `You are a B2B marketing content generator. Generate personalized, safe, and compliant marketing content.

STRICT LEGAL/SAFETY RULES (MUST ENFORCE):
1. NO competitor names or identifiable companies
2. NO negative claims about identifiable companies/products
3. NO copyrighted text or quotes
4. NO invented facts or statistics
5. Compare APPROACHES, not vendors
6. All output must be factual, neutral, and professional

Output must be valid JSON matching the exact schema provided.`;

interface PersonalizationContext {
  persona: string;
  buyer_stage: string;
  industry: string;
  company_size: string;
  cta: string;
}

interface PersonalizationPromptContext {
  prompt: string;
  persona: string;
  buyer_stage: string;
  industry: string;
  company_size: string;
  cta: string;
}

/**
 * Call Claude API to generate personalized content
 */
export async function generatePersonalizedContent(
  context: PersonalizationContext
): Promise<ClaudeOutput> {
  const apiKey = process.env.ANTHROPIC_API_KEY;

  if (!apiKey) {
    throw new Error('ANTHROPIC_API_KEY environment variable is not set');
  }

  const anthropic = new Anthropic({
    apiKey: apiKey,
  });

  const userPrompt = `Generate personalized marketing content for:
- Persona: ${context.persona}
- Buyer Stage: ${context.buyer_stage}
- Industry: ${context.industry}
- Company Size: ${context.company_size}
- Call-to-Action: ${context.cta}

Create compelling, personalized content that addresses this persona's specific needs and pain points.
Focus on their buyer stage and industry context.

Return ONLY valid JSON with this exact structure:
{
  "headline": "Compelling headline (max 80 chars)",
  "subheadline": "Supporting subheadline (max 150 chars)",
  "value_propositions": [
    {
      "title": "Value prop title",
      "description": "Brief description"
    },
    {
      "title": "Value prop title",
      "description": "Brief description"
    },
    {
      "title": "Value prop title",
      "description": "Brief description"
    }
  ],
  "cta_text": "Action-oriented CTA button text",
  "personalization_rationale": "Brief explanation of personalization choices"
}`;

  try {
    const message = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 2048,
      temperature: 0.3, // Low temperature for consistency
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: 'user',
          content: userPrompt,
        },
      ],
    });

    // Extract text content
    const textContent = message.content.find((block) => block.type === 'text');
    if (!textContent || textContent.type !== 'text') {
      throw new Error('No text content in Claude response');
    }

    let jsonText = textContent.text.trim();

    // Remove markdown code blocks if present
    if (jsonText.startsWith('```')) {
      jsonText = jsonText.replace(/^```(?:json)?\n/, '').replace(/\n```$/, '');
    }

    // Parse JSON
    const parsed = JSON.parse(jsonText);

    // Validate with Zod
    const validated = ClaudeOutputSchema.parse(parsed);

    return validated;
  } catch (error) {
    if (error instanceof Anthropic.APIError) {
      console.error('Claude API Error:', error.status, error.message);
      throw new Error(`Claude API error: ${error.message}`);
    }

    if (error instanceof SyntaxError) {
      console.error('JSON parse error:', error);
      // Retry with "fix JSON" prompt
      return await retryWithFixPrompt(anthropic, context, error.message);
    }

    throw error;
  }
}

/**
 * Call Claude API with a custom prompt for template adaptation
 */
export async function generatePersonalization(
  context: PersonalizationPromptContext
): Promise<ClaudeOutput> {
  const apiKey = process.env.ANTHROPIC_API_KEY;

  if (!apiKey) {
    throw new Error('ANTHROPIC_API_KEY environment variable is not set');
  }

  const anthropic = new Anthropic({
    apiKey: apiKey,
  });

  const adaptationSystemPrompt = `You are a B2B marketing content adapter. Generate personalized content following strict requirements.

Output must be valid JSON with this EXACT structure:
{
  "headline": "string",
  "subheadline": "string",
  "cta_text": "string",
  "value_prop_1": "string",
  "value_prop_2": "string",
  "value_prop_3": "string"
}`;

  try {
    const message = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 2048,
      temperature: 0.3,
      system: adaptationSystemPrompt,
      messages: [
        {
          role: 'user',
          content: context.prompt,
        },
      ],
    });

    const textContent = message.content.find((block) => block.type === 'text');
    if (!textContent || textContent.type !== 'text') {
      throw new Error('No text content in Claude response');
    }

    let jsonText = textContent.text.trim();

    // Remove markdown code blocks if present
    if (jsonText.startsWith('```')) {
      jsonText = jsonText.replace(/^```(?:json)?\n/, '').replace(/\n```$/, '');
    }

    // Parse JSON
    const parsed = JSON.parse(jsonText);

    // Validate with Zod schema
    const validated = ClaudeOutputSchema.parse(parsed);

    return validated;
  } catch (error) {
    if (error instanceof Anthropic.APIError) {
      console.error('Claude API Error:', error.status, error.message);
      throw new Error(`Claude API error: ${error.message}`);
    }

    if (error instanceof SyntaxError) {
      console.error('JSON parse error:', error);
      throw new Error('Failed to parse Claude response as JSON');
    }

    throw error;
  }
}

/**
 * Retry Claude call with JSON fix instruction
 */
async function retryWithFixPrompt(
  anthropic: Anthropic,
  context: PersonalizationContext,
  errorMessage: string
): Promise<ClaudeOutput> {
  const fixPrompt = `The previous response had a JSON parsing error: ${errorMessage}

Please generate the same personalized content but ensure it's VALID JSON with no syntax errors.
Return ONLY the JSON object, no explanations or markdown formatting.

Context:
- Persona: ${context.persona}
- Buyer Stage: ${context.buyer_stage}
- Industry: ${context.industry}
- Company Size: ${context.company_size}
- Call-to-Action: ${context.cta}

Required JSON structure:
{
  "headline": "string",
  "subheadline": "string",
  "value_propositions": [{"title": "string", "description": "string"}],
  "cta_text": "string",
  "personalization_rationale": "string"
}`;

  try {
    const message = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 2048,
      temperature: 0.1, // Even lower for retry
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: 'user',
          content: fixPrompt,
        },
      ],
    });

    const textContent = message.content.find((block) => block.type === 'text');
    if (!textContent || textContent.type !== 'text') {
      throw new Error('No text content in Claude retry response');
    }

    let jsonText = textContent.text.trim();
    if (jsonText.startsWith('```')) {
      jsonText = jsonText.replace(/^```(?:json)?\n/, '').replace(/\n```$/, '');
    }

    const parsed = JSON.parse(jsonText);
    return ClaudeOutputSchema.parse(parsed);
  } catch (retryError) {
    console.error('Retry failed:', retryError);
    throw new Error('Failed to generate valid JSON after retry');
  }
}
