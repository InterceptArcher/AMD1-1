// =============================================================================
// WIZARD TYPES & ADAPTIVE DATA LAYER
// =============================================================================

// Card option type used across all wizard steps
export interface CardOption {
  value: string;
  label: string;
  description?: string;
}

// Enrichment data returned from quick-enrich API
export interface EnrichmentPreview {
  company_name?: string;
  industry?: string;
  employee_count?: number;
  employee_count_range?: string;
  founded_year?: number;
  title?: string;
  company_summary?: string;
  recent_news?: Array<{ title: string; source?: string }>;
  seniority?: string;
}

// =============================================================================
// STEP 2: COMPANY
// =============================================================================

export const COMPANY_SIZE_OPTIONS: CardOption[] = [
  { value: 'small', label: 'Small Business', description: '1-200 employees' },
  { value: 'midmarket', label: 'Mid-Market', description: '201-1,000 employees' },
  { value: 'enterprise', label: 'Enterprise', description: '1,000+ employees' },
];

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

// =============================================================================
// STEP 3: ROLE
// =============================================================================

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

// Persona type classification
export type PersonaType = 'technical' | 'business';

const TECHNICAL_ROLES = ['cto', 'vp_engineering', 'eng_manager', 'senior_engineer'];
const BUSINESS_ROLES = ['ceo', 'vp_ops', 'ops_manager'];

export function getPersonaType(role: string): PersonaType {
  if (TECHNICAL_ROLES.includes(role)) return 'technical';
  if (BUSINESS_ROLES.includes(role)) return 'business';
  return 'business'; // default for 'other'
}

// =============================================================================
// STEP 4: ROLE-ADAPTIVE FRAMINGS
// =============================================================================

// IT Environment options adapt based on persona type
export const IT_ENVIRONMENT_OPTIONS: Record<PersonaType, CardOption[]> = {
  technical: [
    {
      value: 'traditional',
      label: 'Keeping the lights on',
      description: 'Mostly on-prem, maintaining legacy systems',
    },
    {
      value: 'modernizing',
      label: 'In the middle of a shift',
      description: 'Hybrid cloud, actively migrating workloads',
    },
    {
      value: 'modern',
      label: "Built for what's next",
      description: 'Cloud-native, containerized, GPU-ready',
    },
  ],
  business: [
    {
      value: 'traditional',
      label: "We're maintaining what we have",
      description: 'More time keeping things running than building new',
    },
    {
      value: 'modernizing',
      label: "We're investing in modernization",
      description: 'Upgrading systems and migrating to the cloud',
    },
    {
      value: 'modern',
      label: "We're positioned for the next wave",
      description: 'Modern infrastructure, ready for AI investment',
    },
  ],
};

// Business Priority options adapt based on persona type
export const BUSINESS_PRIORITY_OPTIONS: Record<PersonaType, CardOption[]> = {
  technical: [
    {
      value: 'reducing_cost',
      label: 'Reduce infrastructure overhead',
      description: 'Cut legacy spend and optimize resource usage',
    },
    {
      value: 'improving_performance',
      label: 'Eliminate bottlenecks',
      description: 'Faster workloads, lower latency, better throughput',
    },
    {
      value: 'preparing_ai',
      label: 'Build the compute layer for AI',
      description: 'GPU infrastructure, ML pipelines, model serving',
    },
  ],
  business: [
    {
      value: 'reducing_cost',
      label: 'Cut operational costs',
      description: 'Reduce overhead and optimize technology spend',
    },
    {
      value: 'improving_performance',
      label: 'Speed up time-to-market',
      description: 'Faster delivery, fewer delays, better throughput',
    },
    {
      value: 'preparing_ai',
      label: 'Unlock AI-driven revenue',
      description: 'Position the business for AI-powered growth',
    },
  ],
};

// =============================================================================
// STEP 4: SIGNAL QUESTIONS (multi-signal stage deduction)
// =============================================================================

// Score contribution for each signal option across all 6 axes
export interface SignalScore {
  traditional: number;
  modernizing: number;
  modern: number;
  reducing_cost: number;
  improving_performance: number;
  preparing_ai: number;
}

// A single option within a signal question
export interface SignalOption {
  value: string;
  label: string;
  description: string;
  scores: SignalScore;
}

// A signal question with persona-adaptive options
export interface SignalQuestion {
  id: string;
  topic: string;
  labels: Record<PersonaType, string>;
  weight: number;
  options: Record<PersonaType, SignalOption[]>;
}

// Result of running deduceFromSignals()
export interface SignalDeduction {
  itEnvironment: string;
  businessPriority: string;
  confidence: number;
}

export const SIGNAL_QUESTIONS: SignalQuestion[] = [
  // Q1: Infrastructure age — strong signal for itEnvironment (1.5x)
  {
    id: 'infra_age',
    topic: 'Infrastructure age',
    labels: {
      technical: 'How old is your infrastructure?',
      business: 'How would you describe your technology foundation?',
    },
    weight: 1.5,
    options: {
      technical: [
        {
          value: 'legacy',
          label: '10+ years, mostly on-prem',
          description: 'Mainframes, VMs, or bare metal running production',
          scores: { traditional: 3, modernizing: 0, modern: 0, reducing_cost: 2, improving_performance: 1, preparing_ai: 0 },
        },
        {
          value: 'hybrid',
          label: 'Mix of old and new',
          description: 'Some cloud, some on-prem, actively migrating',
          scores: { traditional: 0, modernizing: 3, modern: 0, reducing_cost: 1, improving_performance: 2, preparing_ai: 1 },
        },
        {
          value: 'cloud_native',
          label: 'Cloud-native, < 5 years old',
          description: 'Containers, K8s, serverless — built for scale',
          scores: { traditional: 0, modernizing: 0, modern: 3, reducing_cost: 0, improving_performance: 1, preparing_ai: 2 },
        },
      ],
      business: [
        {
          value: 'legacy',
          label: 'Established, long-standing systems',
          description: 'Reliable but aging — built over many years',
          scores: { traditional: 3, modernizing: 0, modern: 0, reducing_cost: 2, improving_performance: 1, preparing_ai: 0 },
        },
        {
          value: 'hybrid',
          label: 'In transition',
          description: 'Upgrading some systems while maintaining others',
          scores: { traditional: 0, modernizing: 3, modern: 0, reducing_cost: 1, improving_performance: 2, preparing_ai: 1 },
        },
        {
          value: 'cloud_native',
          label: 'Modern and flexible',
          description: 'Recent platforms designed for agility and growth',
          scores: { traditional: 0, modernizing: 0, modern: 3, reducing_cost: 0, improving_performance: 1, preparing_ai: 2 },
        },
      ],
    },
  },
  // Q2: AI readiness — signals for both axes (1.0x)
  {
    id: 'ai_readiness',
    topic: 'AI readiness',
    labels: {
      technical: 'Where are you with AI workloads?',
      business: 'How is your org using AI today?',
    },
    weight: 1.0,
    options: {
      technical: [
        {
          value: 'no_ai',
          label: 'Not on our roadmap yet',
          description: 'No GPU workloads, no ML pipelines in place',
          scores: { traditional: 2, modernizing: 1, modern: 0, reducing_cost: 2, improving_performance: 1, preparing_ai: 0 },
        },
        {
          value: 'experimenting',
          label: 'Experimenting with pilots',
          description: 'POCs, evaluating tools, some data science work',
          scores: { traditional: 0, modernizing: 2, modern: 1, reducing_cost: 0, improving_performance: 2, preparing_ai: 1 },
        },
        {
          value: 'production_ai',
          label: 'AI in production',
          description: 'Models deployed, GPU clusters, ML pipelines running',
          scores: { traditional: 0, modernizing: 0, modern: 3, reducing_cost: 0, improving_performance: 1, preparing_ai: 3 },
        },
      ],
      business: [
        {
          value: 'no_ai',
          label: 'Not a priority right now',
          description: 'Focused on other business initiatives first',
          scores: { traditional: 2, modernizing: 1, modern: 0, reducing_cost: 2, improving_performance: 1, preparing_ai: 0 },
        },
        {
          value: 'experimenting',
          label: 'Exploring use cases',
          description: 'Evaluating where AI could add business value',
          scores: { traditional: 0, modernizing: 2, modern: 1, reducing_cost: 0, improving_performance: 2, preparing_ai: 1 },
        },
        {
          value: 'production_ai',
          label: 'Driving business results with AI',
          description: 'AI actively improving revenue, efficiency, or customer experience',
          scores: { traditional: 0, modernizing: 0, modern: 3, reducing_cost: 0, improving_performance: 1, preparing_ai: 3 },
        },
      ],
    },
  },
  // Q3: Spending focus — strong signal for businessPriority (1.5x)
  {
    id: 'spending_focus',
    topic: 'Spending focus',
    labels: {
      technical: 'Where is most of your IT budget going?',
      business: 'Where is your tech investment focused?',
    },
    weight: 1.5,
    options: {
      technical: [
        {
          value: 'cost_reduction',
          label: 'Reducing infrastructure costs',
          description: 'Consolidating, decommissioning, cutting licenses',
          scores: { traditional: 2, modernizing: 1, modern: 0, reducing_cost: 3, improving_performance: 0, preparing_ai: 0 },
        },
        {
          value: 'performance',
          label: 'Eliminating bottlenecks',
          description: 'Faster workloads, better throughput, lower latency',
          scores: { traditional: 0, modernizing: 2, modern: 1, reducing_cost: 0, improving_performance: 3, preparing_ai: 0 },
        },
        {
          value: 'ai_capabilities',
          label: 'Building AI capabilities',
          description: 'GPU infrastructure, ML platforms, data pipelines',
          scores: { traditional: 0, modernizing: 0, modern: 2, reducing_cost: 0, improving_performance: 0, preparing_ai: 3 },
        },
      ],
      business: [
        {
          value: 'cost_reduction',
          label: 'Cutting operational costs',
          description: 'Reducing overhead and optimizing technology spend',
          scores: { traditional: 2, modernizing: 1, modern: 0, reducing_cost: 3, improving_performance: 0, preparing_ai: 0 },
        },
        {
          value: 'performance',
          label: 'Speeding up delivery',
          description: 'Faster time-to-market, fewer delays',
          scores: { traditional: 0, modernizing: 2, modern: 1, reducing_cost: 0, improving_performance: 3, preparing_ai: 0 },
        },
        {
          value: 'ai_capabilities',
          label: 'Investing in AI-driven growth',
          description: 'Positioning the business for AI-powered revenue',
          scores: { traditional: 0, modernizing: 0, modern: 2, reducing_cost: 0, improving_performance: 0, preparing_ai: 3 },
        },
      ],
    },
  },
  // Q4: Team composition — balancing signal (1.0x)
  {
    id: 'team_composition',
    topic: 'Team composition',
    labels: {
      technical: 'What does your engineering team look like?',
      business: 'What talent are you investing in?',
    },
    weight: 1.0,
    options: {
      technical: [
        {
          value: 'maintaining',
          label: 'Mostly maintaining existing systems',
          description: 'Ops-heavy, focused on uptime and patching',
          scores: { traditional: 2, modernizing: 1, modern: 0, reducing_cost: 2, improving_performance: 1, preparing_ai: 0 },
        },
        {
          value: 'mixed',
          label: 'Mix of ops and new development',
          description: 'Some legacy support, some new projects',
          scores: { traditional: 0, modernizing: 2, modern: 1, reducing_cost: 1, improving_performance: 2, preparing_ai: 1 },
        },
        {
          value: 'ai_heavy',
          label: 'Hiring for cloud and AI',
          description: 'ML engineers, platform engineers, data scientists',
          scores: { traditional: 0, modernizing: 0, modern: 3, reducing_cost: 0, improving_performance: 1, preparing_ai: 2 },
        },
      ],
      business: [
        {
          value: 'maintaining',
          label: 'Keeping things running smoothly',
          description: 'Team focused on stability and reliability',
          scores: { traditional: 2, modernizing: 1, modern: 0, reducing_cost: 2, improving_performance: 1, preparing_ai: 0 },
        },
        {
          value: 'mixed',
          label: 'Balancing operations and innovation',
          description: 'Some resources on new initiatives, some on core ops',
          scores: { traditional: 0, modernizing: 2, modern: 1, reducing_cost: 1, improving_performance: 2, preparing_ai: 1 },
        },
        {
          value: 'ai_heavy',
          label: 'Building the future workforce',
          description: 'Hiring for AI, analytics, and digital transformation',
          scores: { traditional: 0, modernizing: 0, modern: 3, reducing_cost: 0, improving_performance: 1, preparing_ai: 2 },
        },
      ],
    },
  },
];

// Signal question IDs for tie-breaking
const INFRA_TIEBREAK_Q = 'infra_age';     // Q1 breaks itEnvironment ties
const PRIORITY_TIEBREAK_Q = 'spending_focus'; // Q3 breaks businessPriority ties

/**
 * Accumulates weighted scores across all answered signal questions.
 * Winner-take-all for each axis. Tie-breaker: Q1 for itEnvironment, Q3 for businessPriority.
 * Returns deduced itEnvironment, businessPriority, and confidence (0-1).
 */
export function deduceFromSignals(
  answers: Record<string, string>,
  personaType: PersonaType = 'technical',
): SignalDeduction {
  // Accumulate scores
  const totals: SignalScore = {
    traditional: 0, modernizing: 0, modern: 0,
    reducing_cost: 0, improving_performance: 0, preparing_ai: 0,
  };

  // Track per-question contributions for tie-breaking
  const perQuestion: Record<string, SignalScore> = {};

  for (const question of SIGNAL_QUESTIONS) {
    const answerValue = answers[question.id];
    if (!answerValue) continue;

    const options = question.options[personaType] || question.options.technical;
    const selected = options.find((o) => o.value === answerValue);
    if (!selected) continue;

    const w = question.weight;
    const weighted: SignalScore = {
      traditional: selected.scores.traditional * w,
      modernizing: selected.scores.modernizing * w,
      modern: selected.scores.modern * w,
      reducing_cost: selected.scores.reducing_cost * w,
      improving_performance: selected.scores.improving_performance * w,
      preparing_ai: selected.scores.preparing_ai * w,
    };

    perQuestion[question.id] = weighted;

    totals.traditional += weighted.traditional;
    totals.modernizing += weighted.modernizing;
    totals.modern += weighted.modern;
    totals.reducing_cost += weighted.reducing_cost;
    totals.improving_performance += weighted.improving_performance;
    totals.preparing_ai += weighted.preparing_ai;
  }

  // Resolve itEnvironment (winner-take-all with Q1 tiebreak)
  const envCandidates = [
    { key: 'traditional', score: totals.traditional },
    { key: 'modernizing', score: totals.modernizing },
    { key: 'modern', score: totals.modern },
  ];
  const itEnvironment = resolveWinner(envCandidates, perQuestion[INFRA_TIEBREAK_Q], ['traditional', 'modernizing', 'modern']);

  // Resolve businessPriority (winner-take-all with Q3 tiebreak)
  const priCandidates = [
    { key: 'reducing_cost', score: totals.reducing_cost },
    { key: 'improving_performance', score: totals.improving_performance },
    { key: 'preparing_ai', score: totals.preparing_ai },
  ];
  const businessPriority = resolveWinner(priCandidates, perQuestion[PRIORITY_TIEBREAK_Q], ['reducing_cost', 'improving_performance', 'preparing_ai']);

  // Confidence: ratio of winner score to total on the winning axis
  const envWinnerScore = envCandidates.find((c) => c.key === itEnvironment)?.score || 0;
  const envTotal = envCandidates.reduce((s, c) => s + c.score, 0);
  const priWinnerScore = priCandidates.find((c) => c.key === businessPriority)?.score || 0;
  const priTotal = priCandidates.reduce((s, c) => s + c.score, 0);

  const envConfidence = envTotal > 0 ? envWinnerScore / envTotal : 0.5;
  const priConfidence = priTotal > 0 ? priWinnerScore / priTotal : 0.5;
  const confidence = Math.round(((envConfidence + priConfidence) / 2) * 100) / 100;

  return { itEnvironment, businessPriority, confidence };
}

function resolveWinner(
  candidates: Array<{ key: string; score: number }>,
  tiebreakScores: SignalScore | undefined,
  tiebreakKeys: string[],
): string {
  const sorted = [...candidates].sort((a, b) => b.score - a.score);

  // No scores at all — default to first candidate
  if (sorted[0].score === 0) return sorted[0].key;

  // Clear winner
  if (sorted[0].score > sorted[1].score) return sorted[0].key;

  // Tie — use tiebreak question scores
  if (tiebreakScores) {
    const tied = sorted.filter((c) => c.score === sorted[0].score);
    const tiebroken = tied
      .map((c) => ({
        key: c.key,
        tieScore: tiebreakScores[c.key as keyof SignalScore] || 0,
      }))
      .sort((a, b) => b.tieScore - a.tieScore);
    return tiebroken[0].key;
  }

  return sorted[0].key;
}

/**
 * Convert signal answer values to human-readable labels for backend consumption.
 * Returns e.g. { "infra_age": "10+ years, mostly on-prem", "ai_readiness": "Experimenting with pilots", ... }
 */
export function getSignalAnswerLabels(
  answers: Record<string, string>,
  personaType: PersonaType = 'technical',
): Record<string, string> {
  const labels: Record<string, string> = {};
  for (const question of SIGNAL_QUESTIONS) {
    const answerValue = answers[question.id];
    if (!answerValue) continue;
    const options = question.options[personaType] || question.options.technical;
    const selected = options.find((o) => o.value === answerValue);
    if (selected) {
      labels[question.id] = selected.label;
    }
  }
  return labels;
}

// Stage reveal copy shown after signal deduction + challenge are selected
export const STAGE_REVEAL_COPY: Record<string, {
  titleHigh: string;
  titleLow: string;
  description: string;
  stat: string;
}> = {
  Observer: {
    titleHigh: "You're at the Observer stage",
    titleLow: "You're leaning toward the Observer stage",
    description: "Focused on stability — we'll show proven paths to start modernizing.",
    stat: '9% of Observers plan to modernize within the next two years.',
  },
  Challenger: {
    titleHigh: "You're at the Challenger stage",
    titleLow: "You're leaning toward the Challenger stage",
    description: "Actively transforming — we'll help you accelerate and avoid common pitfalls.",
    stat: '58% of Challengers are currently undertaking modernization initiatives.',
  },
  Leader: {
    titleHigh: "You're at the Leader stage",
    titleLow: "You're leaning toward the Leader stage",
    description: "Ahead of the curve — we'll focus on AI-readiness and competitive advantage.",
    stat: '33% of Leaders have fully modernized in the past two years.',
  },
};

export function getStageRevealTitle(stage: string, confidence: number): string {
  const copy = STAGE_REVEAL_COPY[stage];
  if (!copy) return '';
  return confidence > 0.55 ? copy.titleHigh : copy.titleLow;
}

// =============================================================================
// STEP 4: INDUSTRY-SPECIFIC CHALLENGES
// =============================================================================

// Generic fallback challenges
const GENERIC_CHALLENGES: CardOption[] = [
  { value: 'legacy_systems', label: 'Legacy systems', description: 'Old infrastructure slowing us down' },
  { value: 'integration_friction', label: 'Integration friction', description: 'Hard to connect tools and platforms' },
  { value: 'resource_constraints', label: 'Resource constraints', description: 'Limited budget, compute, or people' },
  { value: 'skills_gap', label: 'Skills gap', description: 'Team needs cloud or AI expertise' },
  { value: 'data_governance', label: 'Data governance', description: 'Compliance, security, or data quality' },
];

// Industry-specific challenge options (same underlying values, different language)
const INDUSTRY_CHALLENGES: Record<string, CardOption[]> = {
  healthcare: [
    { value: 'legacy_systems', label: 'EHR complexity', description: 'Legacy clinical systems slow everything down' },
    { value: 'integration_friction', label: 'Clinical data silos', description: 'EHR, imaging, and ops systems disconnected' },
    { value: 'resource_constraints', label: 'Budget constraints', description: 'Limited funding for infrastructure upgrades' },
    { value: 'skills_gap', label: 'Clinical AI readiness', description: 'Team needs AI and cloud expertise' },
    { value: 'data_governance', label: 'HIPAA and compliance', description: 'Patient data security and regulatory burden' },
  ],
  financial_services: [
    { value: 'legacy_systems', label: 'Core banking legacy', description: 'Aging transaction and settlement systems' },
    { value: 'integration_friction', label: 'System fragmentation', description: 'Trading, risk, and ops platforms disconnected' },
    { value: 'resource_constraints', label: 'Budget pressure', description: 'Compliance spend crowds out modernization' },
    { value: 'skills_gap', label: 'AI talent gap', description: 'Need ML engineers for fraud and risk models' },
    { value: 'data_governance', label: 'Regulatory compliance', description: 'SOX, PCI, and data sovereignty requirements' },
  ],
  retail: [
    { value: 'legacy_systems', label: 'POS and ecommerce legacy', description: 'Aging retail platforms limit growth' },
    { value: 'integration_friction', label: 'Omnichannel gaps', description: 'Online, in-store, and supply chain disconnected' },
    { value: 'resource_constraints', label: 'Seasonal scaling', description: 'Not enough capacity for peak demand' },
    { value: 'skills_gap', label: 'Digital skills gap', description: 'Team needs ecommerce and analytics expertise' },
    { value: 'data_governance', label: 'Customer data risk', description: 'PCI compliance and data unification' },
  ],
  manufacturing: [
    { value: 'legacy_systems', label: 'OT system aging', description: 'Plant-floor and ERP systems outdated' },
    { value: 'integration_friction', label: 'IT/OT convergence', description: 'Factory systems disconnected from enterprise IT' },
    { value: 'resource_constraints', label: 'CapEx constraints', description: 'Equipment and infrastructure compete for budget' },
    { value: 'skills_gap', label: 'Automation skills', description: 'Need IoT, robotics, and AI expertise' },
    { value: 'data_governance', label: 'Production data quality', description: 'Sensor data scattered and inconsistent' },
  ],
  technology: [
    { value: 'legacy_systems', label: 'Technical debt', description: 'Monoliths and legacy services slow shipping' },
    { value: 'integration_friction', label: 'Toolchain fragmentation', description: 'Too many platforms, not enough integration' },
    { value: 'resource_constraints', label: 'Compute constraints', description: 'Not enough GPUs or infrastructure budget' },
    { value: 'skills_gap', label: 'AI/ML skills gap', description: 'Need ML engineers and infra specialists' },
    { value: 'data_governance', label: 'Data pipeline governance', description: 'Data quality, lineage, and compliance gaps' },
  ],
  energy: [
    { value: 'legacy_systems', label: 'SCADA and OT legacy', description: 'Aging grid and operational technology' },
    { value: 'integration_friction', label: 'Field-to-office gap', description: 'Remote assets disconnected from central systems' },
    { value: 'resource_constraints', label: 'Infrastructure budget', description: 'Physical assets compete with IT modernization' },
    { value: 'skills_gap', label: 'Digital transformation gap', description: 'Need cloud and analytics skills in OT teams' },
    { value: 'data_governance', label: 'NERC/regulatory compliance', description: 'Critical infrastructure security requirements' },
  ],
  telecommunications: [
    { value: 'legacy_systems', label: 'Network legacy systems', description: '3G/4G infrastructure alongside 5G rollout' },
    { value: 'integration_friction', label: 'BSS/OSS integration', description: 'Billing, service, and network platforms fragmented' },
    { value: 'resource_constraints', label: 'Spectrum and CapEx', description: '5G buildout stretches available budget' },
    { value: 'skills_gap', label: 'Cloud-native networking', description: 'Need SDN and virtualization expertise' },
    { value: 'data_governance', label: 'Subscriber data privacy', description: 'GDPR, CCPA, and network data governance' },
  ],
  government: [
    { value: 'legacy_systems', label: 'Legacy citizen systems', description: 'Decades-old platforms for critical services' },
    { value: 'integration_friction', label: 'Agency silos', description: 'Systems across departments don\'t connect' },
    { value: 'resource_constraints', label: 'Procurement cycles', description: 'Budget constraints and slow acquisition' },
    { value: 'skills_gap', label: 'Workforce modernization', description: 'Need to upskill on cloud and AI' },
    { value: 'data_governance', label: 'FedRAMP and compliance', description: 'Data sovereignty and security mandates' },
  ],
  education: [
    { value: 'legacy_systems', label: 'Campus system legacy', description: 'Aging SIS and learning platforms' },
    { value: 'integration_friction', label: 'Platform fragmentation', description: 'LMS, SIS, and research systems disconnected' },
    { value: 'resource_constraints', label: 'Institutional budget', description: 'IT competes with academic program funding' },
    { value: 'skills_gap', label: 'Research computing gap', description: 'Faculty need HPC and AI infrastructure' },
    { value: 'data_governance', label: 'FERPA and data privacy', description: 'Student data protection and compliance' },
  ],
};

// =============================================================================
// STEP 4: INDUSTRY × PERSONA DESCRIPTION OVERRIDES FOR IT ENVIRONMENT
// =============================================================================

// When both industry and persona are known, override IT env descriptions
const IT_ENV_OVERRIDES: Record<string, Record<PersonaType, Record<string, string>>> = {
  healthcare: {
    technical: {
      traditional: 'Maintaining EHR and imaging systems is most of the workload',
      modernizing: 'Migrating clinical workloads to cloud, keeping HIPAA compliance',
      modern: 'Cloud-native infrastructure for clinical AI and imaging',
    },
    business: {
      traditional: 'Clinical systems need constant attention just to stay running',
      modernizing: 'Investing in modern platforms to improve patient outcomes',
      modern: 'Ready to deploy AI that transforms care delivery and operations',
    },
  },
  financial_services: {
    technical: {
      traditional: 'Core banking and trading systems run on aging infrastructure',
      modernizing: 'Moving transaction workloads to cloud with regulatory controls',
      modern: 'Low-latency cloud infrastructure for real-time trading and AI',
    },
    business: {
      traditional: 'Legacy systems are a drag on our ability to innovate',
      modernizing: 'Upgrading platforms to compete with fintech challengers',
      modern: 'Infrastructure supports AI-driven fraud detection and risk models',
    },
  },
  retail: {
    technical: {
      traditional: 'POS and ecommerce systems need constant patching',
      modernizing: 'Migrating retail platforms to handle omnichannel demand',
      modern: 'Auto-scaling infrastructure for seasonal peaks and AI analytics',
    },
    business: {
      traditional: 'Technology is holding back our growth and customer experience',
      modernizing: 'Investing in platforms that can scale with customer demand',
      modern: 'Ready for AI-driven personalization and demand forecasting',
    },
  },
  technology: {
    technical: {
      traditional: 'Running mostly on-prem with some legacy services',
      modernizing: 'Breaking monoliths, containerizing, moving to K8s',
      modern: 'Cloud-native, CI/CD automated, GPU clusters for ML',
    },
    business: {
      traditional: 'Engineering spends too much time on maintenance',
      modernizing: 'Investing in developer productivity and platform upgrades',
      modern: 'Infrastructure is a competitive advantage, AI-ready',
    },
  },
  manufacturing: {
    technical: {
      traditional: 'Plant-floor OT and ERP systems are decades old',
      modernizing: 'Connecting factory systems to cloud for analytics',
      modern: 'IoT-connected, real-time monitoring, AI-driven optimization',
    },
    business: {
      traditional: 'Production systems are reliable but can\'t support growth',
      modernizing: 'Digitizing operations to improve efficiency and quality',
      modern: 'Smart factory infrastructure ready for predictive AI',
    },
  },
};

// =============================================================================
// CHALLENGE FILTERING & RESOLUTION
// =============================================================================

export function getFilteredChallenges(
  itEnvironment: string,
  industry: string = '',
): CardOption[] {
  // Get industry-specific or generic challenges
  const base = INDUSTRY_CHALLENGES[industry] || GENERIC_CHALLENGES;

  // Filter out legacy systems for modern environments
  if (itEnvironment === 'modern') {
    return base.filter((c) => c.value !== 'legacy_systems');
  }
  return base;
}

// Get IT environment options with industry overrides applied
export function getITEnvironmentOptions(
  personaType: PersonaType,
  industry: string = '',
): CardOption[] {
  const baseOptions = IT_ENVIRONMENT_OPTIONS[personaType];
  const overrides = IT_ENV_OVERRIDES[industry]?.[personaType];

  if (!overrides) return baseOptions;

  return baseOptions.map((opt) => ({
    ...opt,
    description: overrides[opt.value] || opt.description,
  }));
}

// Get priority options based on persona
export function getPriorityOptions(personaType: PersonaType): CardOption[] {
  return BUSINESS_PRIORITY_OPTIONS[personaType];
}

// =============================================================================
// INTELLIGENCE NUGGETS (shown after selection)
// =============================================================================

export const INTELLIGENCE_NUGGETS: Record<string, string> = {
  // industry:challenge
  'healthcare:legacy_systems': 'Healthcare orgs spend 23% more on legacy maintenance than the industry average',
  'healthcare:data_governance': '78% of health system CIOs cite HIPAA compliance as their top AI blocker',
  'healthcare:skills_gap': 'Clinical AI roles have grown 340% in the past 3 years',
  'financial_services:legacy_systems': 'The average bank runs on 45-year-old core systems',
  'financial_services:integration_friction': 'Financial institutions average 900+ applications requiring integration',
  'financial_services:data_governance': 'Regulatory compliance consumes 15-20% of banking IT budgets',
  'retail:legacy_systems': 'Retailers lose $1.8T annually from out-of-stock events tied to legacy inventory systems',
  'retail:integration_friction': 'Only 29% of retailers have fully integrated omnichannel platforms',
  'retail:resource_constraints': 'Peak season traffic can spike 10x — 40% of retailers can\'t scale fast enough',
  'technology:legacy_systems': 'Engineering teams spend 33% of time on technical debt maintenance',
  'technology:integration_friction': 'The average enterprise uses 371 SaaS applications',
  'technology:skills_gap': 'ML engineer demand has outpaced supply 3:1 since 2023',
  'manufacturing:legacy_systems': '70% of manufacturers still run equipment monitoring on 15+ year old systems',
  'manufacturing:integration_friction': 'Only 24% of factories have connected IT and OT environments',
  'energy:legacy_systems': 'SCADA systems in energy average 20+ years in service',
  'government:legacy_systems': 'Federal agencies spend 80% of IT budgets maintaining legacy systems',
  'education:resource_constraints': 'Higher ed IT budgets average just 4-5% of institutional spending',
  'telecommunications:legacy_systems': '5G rollout requires modernizing 70% of existing network infrastructure',
};

// Fallback to challenge-only nuggets
const CHALLENGE_NUGGETS: Record<string, string> = {
  legacy_systems: "The most common barrier — we'll show proven migration paths",
  integration_friction: 'Integration is the hidden tax on every IT initiative',
  resource_constraints: "We'll focus on high-impact, low-cost wins for your team",
  skills_gap: 'Skills development is the fastest-growing IT investment area',
  data_governance: 'Strong governance frameworks unlock safe AI adoption',
};

export function getIntelligenceNugget(industry: string, challenge: string): string {
  return INTELLIGENCE_NUGGETS[`${industry}:${challenge}`]
    || CHALLENGE_NUGGETS[challenge]
    || '';
}

// =============================================================================
// SOCIAL PROOF (environment and priority)
// =============================================================================

export const SOCIAL_PROOF: Record<string, string> = {
  'itEnvironment:traditional': "You're not alone — many enterprises are starting here",
  'itEnvironment:modernizing': '58% of companies are actively in this stage',
  'itEnvironment:modern': "You're ahead of the curve — only 33% reach this stage",
  'businessPriority:reducing_cost': 'Cost optimization is the #1 priority for modernizing companies',
  'businessPriority:improving_performance': 'Performance gains deliver the fastest measurable ROI',
  'businessPriority:preparing_ai': 'Getting AI-ready now positions you years ahead of peers',
};

// =============================================================================
// WIZARD FORM DATA
// =============================================================================

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
  signalAnswers: Record<string, string>;
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
  signalAnswers: {},
};

// =============================================================================
// STEP VALIDATORS
// =============================================================================

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
  // Step 4: Situation (all 4 signal questions + challenge + consent)
  (data) =>
    Object.keys(data.signalAnswers).length >= SIGNAL_QUESTIONS.length &&
    data.itEnvironment.length > 0 &&
    data.businessPriority.length > 0 &&
    data.challenge.length > 0 &&
    data.consent,
];

// =============================================================================
// STEP TITLES (adapt based on persona type)
// =============================================================================

export const STEP_TITLES = [
  "Let's get started",
  'About your company',
  "What's your role?",
  'Your situation',
];

export function getAdaptiveStepTitle(step: number, personaType?: PersonaType, companyName?: string): string {
  if (step === 1 && companyName) {
    return `About ${companyName}`;
  }
  if (step === 3 && personaType) {
    if (companyName) {
      return personaType === 'technical'
        ? `Your infrastructure at ${companyName}`
        : `Your business situation at ${companyName}`;
    }
    return personaType === 'technical' ? 'Your infrastructure' : 'Your business situation';
  }
  return STEP_TITLES[step];
}

// =============================================================================
// STEP 4 QUESTION LABELS (adapt based on persona type)
// =============================================================================

export function getEnvLabel(personaType: PersonaType): string {
  return personaType === 'technical'
    ? 'What does your stack look like?'
    : 'How would you describe your tech posture?';
}

export function getPriorityLabel(personaType: PersonaType): string {
  return personaType === 'technical'
    ? 'Where do you need the biggest improvement?'
    : 'Where do you want to see ROI first?';
}

export function getChallengeLabel(personaType: PersonaType): string {
  return personaType === 'technical'
    ? "What's blocking your engineering org?"
    : "What's the biggest barrier to progress?";
}

export const TOTAL_STEPS = 4;

// =============================================================================
// TRANSITION MESSAGES (adapt based on context)
// =============================================================================

export function getTransitionMessage(fromStep: number, data: WizardData): string {
  if (fromStep === 0) return 'Setting up your profile...';

  if (fromStep === 1) {
    const industry = INDUSTRY_OPTIONS.find((i) => i.value === data.industry)?.label;
    if (industry && data.companySize === 'enterprise') {
      return `Mapping the ${industry.toLowerCase()} enterprise landscape...`;
    }
    if (industry) {
      return `Mapping the ${industry.toLowerCase()} landscape...`;
    }
    return 'Mapping your industry landscape...';
  }

  if (fromStep === 2) {
    const pt = getPersonaType(data.persona);
    return pt === 'technical'
      ? 'Tailoring for a technical decision-maker...'
      : 'Calibrating for executive-level insights...';
  }

  return 'Processing...';
}

// =============================================================================
// ASSESSMENT DEPTH
// =============================================================================

export interface AssessmentDepth {
  percentage: number;
  items: Array<{ label: string; done: boolean }>;
}

export function getAssessmentDepth(data: WizardData): AssessmentDepth {
  const signalCount = Object.keys(data.signalAnswers).length;
  const items = [
    { label: 'Contact identified', done: data.firstName.length > 0 && data.email.length > 0 },
    { label: 'Industry context loaded', done: data.industry.length > 0 },
    { label: 'Role-specific framing applied', done: data.persona.length > 0 },
    { label: 'Infrastructure signal', done: signalCount >= 1 },
    { label: 'AI readiness signal', done: signalCount >= 2 },
    { label: 'Spending focus signal', done: signalCount >= 3 },
    { label: 'Team composition signal', done: signalCount >= 4 },
    { label: 'Challenge focus sharpened', done: data.challenge.length > 0 },
  ];
  const done = items.filter((i) => i.done).length;
  return { percentage: Math.round((done / items.length) * 100), items };
}

// =============================================================================
// DISPLAY HELPERS
// =============================================================================

export const STAGE_LABELS: Record<string, string> = {
  traditional: 'Observer',
  modernizing: 'Challenger',
  modern: 'Leader',
};

export const FREE_EMAIL_PROVIDERS = [
  'gmail', 'yahoo', 'hotmail', 'outlook', 'aol', 'icloud',
  'protonmail', 'mail', 'live', 'msn', 'ymail', 'me', 'zoho',
];

export function extractCompanyFromEmail(email: string): string | null {
  const match = email.match(/@([^.]+)\./);
  if (!match) return null;
  const domain = match[1].toLowerCase();
  if (FREE_EMAIL_PROVIDERS.includes(domain)) return null;
  return domain.charAt(0).toUpperCase() + domain.slice(1);
}

export function isWorkEmail(email: string): boolean {
  const match = email.match(/@([^.]+)\./);
  if (!match) return false;
  return !FREE_EMAIL_PROVIDERS.includes(match[1].toLowerCase());
}

// Map employee count to company size value
export function employeeCountToSize(count: number): string {
  if (count <= 200) return 'small';
  if (count <= 1000) return 'midmarket';
  return 'enterprise';
}

// Map enrichment industry to our canonical industry value
export function normalizeEnrichmentIndustry(raw: string): string {
  const lower = raw.toLowerCase();
  const mappings: Record<string, string[]> = {
    technology: ['technology', 'software', 'internet', 'computer', 'saas', 'information technology'],
    financial_services: ['financial', 'banking', 'insurance', 'fintech', 'investment'],
    healthcare: ['healthcare', 'health care', 'medical', 'pharma', 'biotech', 'life sciences'],
    manufacturing: ['manufacturing', 'industrial', 'automotive', 'aerospace'],
    retail: ['retail', 'ecommerce', 'consumer', 'e-commerce', 'wholesale'],
    energy: ['energy', 'oil', 'gas', 'utilities', 'renewable', 'mining'],
    telecommunications: ['telecom', 'telecommunications', 'wireless', 'network'],
    media: ['media', 'entertainment', 'publishing', 'advertising', 'broadcast'],
    government: ['government', 'public sector', 'defense', 'military'],
    education: ['education', 'university', 'academic', 'higher education', 'school'],
    professional_services: ['consulting', 'legal', 'accounting', 'professional services', 'staffing'],
  };

  for (const [canonical, keywords] of Object.entries(mappings)) {
    if (keywords.some((k) => lower.includes(k))) return canonical;
  }
  return 'other';
}

// =============================================================================
// SENIORITY → ROLE MAPPING (for pre-selection from enrichment)
// =============================================================================

const TECH_TITLE_KEYWORDS = [
  'cto', 'engineering', 'it', 'data', 'security', 'infrastructure',
  'software', 'systems', 'architect', 'devops', 'technology', 'technical',
  'platform', 'cloud', 'network', 'developer',
];

const BIZ_TITLE_KEYWORDS = [
  'ceo', 'coo', 'cfo', 'operations', 'finance', 'business', 'strategy',
  'revenue', 'sales', 'marketing', 'procurement', 'supply chain',
  'general manager', 'managing director',
];

function isTechTitle(title: string): boolean {
  const lower = title.toLowerCase();
  return TECH_TITLE_KEYWORDS.some((k) => lower.includes(k));
}

function isBizTitle(title: string): boolean {
  const lower = title.toLowerCase();
  return BIZ_TITLE_KEYWORDS.some((k) => lower.includes(k));
}

export function mapSeniorityToRole(seniority: string, title: string): string | null {
  const s = (seniority || '').toLowerCase();
  const tech = isTechTitle(title);
  const biz = isBizTitle(title);

  if (s === 'c_suite' || s === 'owner' || s === 'founder') {
    if (tech) return 'cto';
    if (biz) return 'ceo';
    return 'ceo'; // default c-suite to business exec
  }
  if (s === 'vp') {
    if (tech) return 'vp_engineering';
    if (biz) return 'vp_ops';
    return 'vp_ops';
  }
  if (s === 'director' || s === 'manager') {
    if (tech) return 'eng_manager';
    if (biz) return 'ops_manager';
    return null;
  }
  if (s === 'senior' || s === 'entry') {
    if (tech) return 'senior_engineer';
    return null;
  }
  return null;
}

// =============================================================================
// DOMAIN EXTRACTION (for company logo)
// =============================================================================

export function extractFullDomainFromEmail(email: string): string | null {
  const match = email.match(/@(.+)$/);
  if (!match) return null;
  const domain = match[1].toLowerCase();
  const base = domain.split('.')[0];
  if (FREE_EMAIL_PROVIDERS.includes(base)) return null;
  return domain;
}

// =============================================================================
// LOCALSTORAGE PERSISTENCE
// =============================================================================

const STORAGE_KEY = 'amd_wizard_progress';

export function saveWizardProgress(step: number, data: WizardData): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ step, data, savedAt: Date.now() }));
  } catch {
    // localStorage may be unavailable
  }
}

export function loadWizardProgress(): { step: number; data: WizardData } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    // Expire after 30 minutes
    if (Date.now() - parsed.savedAt > 30 * 60 * 1000) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return { step: parsed.step, data: parsed.data };
  } catch {
    return null;
  }
}

export function clearWizardProgress(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
