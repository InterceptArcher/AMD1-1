// Card option type used across all wizard steps
export interface CardOption {
  value: string;
  label: string;
  description?: string;
}

// Step 2: Company Size (3 cards)
export const COMPANY_SIZE_OPTIONS: CardOption[] = [
  {
    value: 'small',
    label: 'Small Business',
    description: '1-200 employees',
  },
  {
    value: 'midmarket',
    label: 'Mid-Market',
    description: '201-1,000 employees',
  },
  {
    value: 'enterprise',
    label: 'Enterprise',
    description: '1,000+ employees',
  },
];

// Step 2: Industry (12 tiles)
export const INDUSTRY_OPTIONS: CardOption[] = [
  { value: 'technology', label: 'Technology' },
  { value: 'financial_services', label: 'Financial Services' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'retail', label: 'Retail' },
  { value: 'energy', label: 'Energy' },
  { value: 'telecommunications', label: 'Telecom' },
  { value: 'media', label: 'Media' },
  { value: 'government', label: 'Government' },
  { value: 'education', label: 'Education' },
  { value: 'professional_services', label: 'Prof. Services' },
  { value: 'other', label: 'Other' },
];

// Step 3: Role groups (8 cards)
export const ROLE_OPTIONS: CardOption[] = [
  { value: 'cto', label: 'Tech Executive', description: 'CTO, CIO, CISO' },
  { value: 'ceo', label: 'Business Executive', description: 'CEO, CFO, COO' },
  { value: 'vp_engineering', label: 'Tech Leadership', description: 'VP Engineering, VP IT' },
  { value: 'vp_ops', label: 'Business Leadership', description: 'VP Ops, VP Finance' },
  { value: 'eng_manager', label: 'Tech Manager', description: 'Eng, IT, or Data Mgr' },
  { value: 'senior_engineer', label: 'Engineer', description: 'Sr Engineer, SysAdmin' },
  { value: 'ops_manager', label: 'Business Ops', description: 'Ops, Finance, Procurement' },
  { value: 'other', label: 'Other', description: 'Another role entirely' },
];

// Step 4: IT Environment — scenario-style (3 cards)
// Descriptions normalized to ~50-55 chars
export const IT_ENVIRONMENT_OPTIONS: CardOption[] = [
  {
    value: 'traditional',
    label: 'Keeping the lights on',
    description: 'More time maintaining what we have than building new',
  },
  {
    value: 'modernizing',
    label: 'In the middle of a shift',
    description: 'Migrating to cloud and modernizing our stack',
  },
  {
    value: 'modern',
    label: "Built for what's next",
    description: 'Cloud-native infrastructure, ready for AI workloads',
  },
];

// Step 4: Business Priority — scenario-style (3 cards)
// Descriptions normalized to ~45-50 chars
export const BUSINESS_PRIORITY_OPTIONS: CardOption[] = [
  {
    value: 'reducing_cost',
    label: 'Free up budget',
    description: 'Cut legacy overhead and optimize our spend',
  },
  {
    value: 'improving_performance',
    label: 'Move faster',
    description: 'Accelerate workloads and remove bottlenecks',
  },
  {
    value: 'preparing_ai',
    label: 'Get AI-ready',
    description: 'Build the foundation for ML and AI adoption',
  },
];

// Step 4: Challenge (5 cards)
// Descriptions normalized to ~35-40 chars
export const CHALLENGE_OPTIONS: CardOption[] = [
  {
    value: 'legacy_systems',
    label: 'Legacy systems',
    description: 'Old infrastructure slowing us down',
  },
  {
    value: 'integration_friction',
    label: 'Integration friction',
    description: 'Hard to connect tools and platforms',
  },
  {
    value: 'resource_constraints',
    label: 'Resource constraints',
    description: 'Limited budget, compute, or people',
  },
  {
    value: 'skills_gap',
    label: 'Skills gap',
    description: 'Team needs cloud or AI expertise',
  },
  {
    value: 'data_governance',
    label: 'Data governance',
    description: 'Compliance, security, or data quality',
  },
];

// Wizard form data that accumulates across steps
export interface WizardData {
  firstName: string;
  lastName: string;
  email: string;
  company: string;
  companySize: string;
  industry: string;
  persona: string;
  itEnvironment: string;
  businessPriority: string;
  challenge: string;
  consent: boolean;
}

export const INITIAL_WIZARD_DATA: WizardData = {
  firstName: '',
  lastName: '',
  email: '',
  company: '',
  companySize: '',
  industry: '',
  persona: '',
  itEnvironment: '',
  businessPriority: '',
  challenge: '',
  consent: false,
};

// Step validators — return true if the step is complete
export const STEP_VALIDATORS: Array<(data: WizardData) => boolean> = [
  // Step 1: Name + email
  (data) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return data.firstName.length > 0 && data.lastName.length > 0 && emailRegex.test(data.email);
  },
  // Step 2: Company + size + industry
  (data) => data.company.length > 0 && data.companySize.length > 0 && data.industry.length > 0,
  // Step 3: Role
  (data) => data.persona.length > 0,
  // Step 4: Situation (environment + priority + challenge + consent)
  (data) =>
    data.itEnvironment.length > 0 &&
    data.businessPriority.length > 0 &&
    data.challenge.length > 0 &&
    data.consent,
];

export const STEP_TITLES = [
  "Let's get started",
  'About your company',
  "What's your role?",
  'Your situation',
];

export const TOTAL_STEPS = 4;

// Thinking micro-moment messages shown between steps
export const TRANSITION_MESSAGES = [
  'Setting up your profile...',
  'Mapping your industry landscape...',
  'Tailoring for your role...',
  // No transition after step 4 (submit instead)
];

// Social proof messages keyed by field:value
export const SOCIAL_PROOF: Record<string, string> = {
  'itEnvironment:traditional':
    "You're not alone — many enterprises are starting here",
  'itEnvironment:modernizing':
    '58% of companies are actively in this stage',
  'itEnvironment:modern':
    "You're ahead of the curve — only 33% reach this stage",
  'businessPriority:reducing_cost':
    'Cost optimization is the #1 priority for modernizing companies',
  'businessPriority:improving_performance':
    'Performance gains deliver the fastest measurable ROI',
  'businessPriority:preparing_ai':
    'Getting AI-ready now positions you years ahead of peers',
  'challenge:legacy_systems':
    "The most common barrier — we'll show proven migration paths",
  'challenge:integration_friction':
    'Integration is the hidden tax on every IT initiative',
  'challenge:resource_constraints':
    "We'll focus on high-impact, low-cost wins for your team",
  'challenge:skills_gap':
    'Skills development is the fastest-growing IT investment area',
  'challenge:data_governance':
    'Strong governance frameworks unlock safe AI adoption',
};

// Display labels for the assessment preview
export const STAGE_LABELS: Record<string, string> = {
  traditional: 'Observer',
  modernizing: 'Challenger',
  modern: 'Leader',
};

// Free email providers — used to detect work emails for company extraction
export const FREE_EMAIL_PROVIDERS = [
  'gmail', 'yahoo', 'hotmail', 'outlook', 'aol', 'icloud',
  'protonmail', 'mail', 'live', 'msn', 'ymail', 'me', 'zoho',
];

// Extract company name from work email domain
export function extractCompanyFromEmail(email: string): string | null {
  const match = email.match(/@([^.]+)\./);
  if (!match) return null;
  const domain = match[1].toLowerCase();
  if (FREE_EMAIL_PROVIDERS.includes(domain)) return null;
  return domain.charAt(0).toUpperCase() + domain.slice(1);
}

// Get filtered challenges based on IT environment
export function getFilteredChallenges(itEnvironment: string): CardOption[] {
  if (itEnvironment === 'modern') {
    return CHALLENGE_OPTIONS.filter((c) => c.value !== 'legacy_systems');
  }
  return CHALLENGE_OPTIONS;
}
