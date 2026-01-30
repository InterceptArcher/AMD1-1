import { z } from 'zod';

// Input validation schema
export const PersonalizeRequestSchema = z.object({
  email: z.string().email('Invalid email format'),
  name: z.string().optional(),
  company: z.string().min(1, 'Company is required'),
  role: z.string().min(1, 'Role is required'),
  modernization_stage: z.string().min(1, 'Modernization stage is required'),
  ai_priority: z.string().min(1, 'AI priority is required'),
  cta: z.string().min(1, 'CTA is required'),
});

export type PersonalizeRequest = z.infer<typeof PersonalizeRequestSchema>;

// Claude output schema - must match the expected structure
export const ClaudeOutputSchema = z.object({
  headline: z.string(),
  subheadline: z.string(),
  value_prop_1: z.string(),
  value_prop_2: z.string(),
  value_prop_3: z.string(),
  cta_text: z.string(),
  personalization_rationale: z.string().optional(),
});

export type ClaudeOutput = z.infer<typeof ClaudeOutputSchema>;

// Job data schema
export const PersonalizationJobSchema = z.object({
  email: z.string(),
  name: z.string().optional(),
  domain: z.string(),
  cta: z.string(),
  persona: z.string(),
  buyer_stage: z.string(),
  company_name: z.string().optional(),
  industry: z.string().optional(),
  company_size: z.string().optional(),
  status: z.enum(['pending', 'completed', 'failed']),
});

export type PersonalizationJob = z.infer<typeof PersonalizationJobSchema>;

// Persona types
export type Persona = 'Business Leader' | 'IT' | 'Finance' | 'Operations' | 'Security';

// Buyer stage types
export type BuyerStage = 'awareness' | 'evaluation' | 'decision';
