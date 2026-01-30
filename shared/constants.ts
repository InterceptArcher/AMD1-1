// Shared constants between frontend and backend

// Persona options
export const PERSONAS = [
  'Business Leader',
  'IT',
  'Finance',
  'Operations',
  'Security',
] as const;

// Buyer stage options
export const BUYER_STAGES = [
  'awareness',
  'evaluation',
  'decision',
] as const;

// AI Priority options
export const AI_PRIORITIES = [
  'AI/ML Development',
  'Cost Optimization',
  'Security/Compliance',
  'Developer Experience',
  'Infrastructure Modernization',
  'Data Analytics',
] as const;

// Company size options
export const COMPANY_SIZES = [
  'startup',
  'smb',
  'mid-market',
  'enterprise',
] as const;

// Template matching scores
export const TEMPLATE_MATCH_THRESHOLD = 0.6;
export const HIGH_CONFIDENCE_THRESHOLD = 0.8;
export const MEDIUM_CONFIDENCE_THRESHOLD = 0.5;

// Performance targets
export const SLA_TARGET_MS = 60000; // 60 seconds
export const ENRICHMENT_TIMEOUT_MS = 10000; // 10 seconds
export const LLM_TIMEOUT_MS = 30000; // 30 seconds

// Caching
export const ENRICHMENT_CACHE_TTL_HOURS = 24;

// Rate limiting
export const RATE_LIMIT_REQUESTS = 10;
export const RATE_LIMIT_WINDOW_MS = 60000; // 1 minute

// Logging levels
export const LOG_LEVELS = ['debug', 'info', 'warn', 'error'] as const;
export type LogLevel = typeof LOG_LEVELS[number];
