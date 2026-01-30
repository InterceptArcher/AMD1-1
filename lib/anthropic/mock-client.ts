// Mock Claude API for testing without API key
import type { ClaudeOutput } from '../schemas';

export async function generateMockPersonalizedContent(context: {
  persona: string;
  buyer_stage: string;
  industry: string;
  company_size: string;
  cta: string;
}): Promise<ClaudeOutput> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 2000));

  return {
    headline: `${context.persona} Solutions for ${context.company_size} Companies`,
    subheadline: `Tailored for ${context.industry} professionals in the ${context.buyer_stage} stage`,
    value_prop_1: `Optimized for ${context.persona} Teams with reliable, scalable solutions`,
    value_prop_2: `Resources and tools designed for teams in the ${context.buyer_stage} phase`,
    value_prop_3: `Enterprise-grade features that work for ${context.company_size} organizations`,
    cta_text: `${context.cta === 'compare' ? 'Compare Solutions' : context.cta === 'demo' ? 'Schedule Demo' : 'Learn More'}`,
    personalization_rationale: `MOCK DATA: Generated for ${context.persona} in ${context.industry} (${context.company_size}) at ${context.buyer_stage} stage.`,
  };
}
