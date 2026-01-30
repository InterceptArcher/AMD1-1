// TypeScript type definitions shared between frontend and backend

// Persona types
export type Persona = 'Business Leader' | 'IT' | 'Finance' | 'Operations' | 'Security';

// Buyer stage types
export type BuyerStage = 'awareness' | 'evaluation' | 'decision';

// AI Priority types
export type AIPriority =
  | 'AI/ML Development'
  | 'Cost Optimization'
  | 'Security/Compliance'
  | 'Developer Experience'
  | 'Infrastructure Modernization'
  | 'Data Analytics';

// Company size types
export type CompanySize = 'startup' | 'smb' | 'mid-market' | 'enterprise';

// Job status types
export type JobStatus = 'pending' | 'completed' | 'failed';

// Enrichment confidence levels
export type ConfidenceLevel = 'high' | 'medium' | 'low';

// API response types
export interface PersonalizedContent {
  headline: string;
  subheadline: string;
  value_prop_1: string;
  value_prop_2: string;
  value_prop_3: string;
  cta_text: string;
  personalization_rationale?: string;
}

export interface EnrichmentData {
  company_name?: string;
  industry?: string;
  company_size?: string;
  employee_count?: number;
  revenue_range?: string;
  technologies?: string[];
  confidence: ConfidenceLevel;
  source: string;
}

export interface PersonalizationResult {
  job_id: string;
  content: PersonalizedContent;
  enrichment?: EnrichmentData;
  status: JobStatus;
  created_at: string;
}
