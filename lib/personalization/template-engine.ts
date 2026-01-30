/**
 * Template Selection Engine
 *
 * Provides rule-based template selection for personalization based on
 * persona, buyer stage, industry, and company size.
 */

import type { RADEnrichmentResponse, CompanySize } from '../enrichment/rad-client';
import type { Persona, BuyerStage } from '../schemas';

export interface PersonalizationTemplate {
  id: string;
  name: string;

  // Matching criteria
  personas: Persona[];
  buyer_stages: BuyerStage[];
  industries?: string[];
  company_sizes?: CompanySize[];

  // Template content (variables: {{company_name}}, {{industry}}, {{news}}, {{persona}}, {{buyer_stage}})
  intro_template: string;
  cta_template: string;

  // Metadata
  priority: number;           // Higher = preferred
  confidence_threshold: number; // Minimum confidence to use this template
}

/**
 * Template Library
 *
 * Comprehensive set of templates covering all persona/stage/size combinations
 */
const TEMPLATES: PersonalizationTemplate[] = [
  // EXECUTIVE PERSONAS
  {
    id: 'exec-enterprise-evaluation',
    name: 'Executive - Enterprise - Evaluation Stage',
    personas: ['Business Leader'],
    buyer_stages: ['evaluation'],
    company_sizes: ['enterprise'],
    intro_template: 'As {{company_name}} evaluates enterprise solutions in {{industry}}, leadership teams like yours are looking for proven platforms that scale and deliver measurable ROI.',
    cta_template: 'Compare how leading enterprises achieve results',
    priority: 10,
    confidence_threshold: 0.8
  },
  {
    id: 'exec-enterprise-decision',
    name: 'Executive - Enterprise - Decision Stage',
    personas: ['Business Leader'],
    buyer_stages: ['decision'],
    company_sizes: ['enterprise'],
    intro_template: '{{company_name}} is making critical decisions about {{industry}} infrastructure. See how industry leaders are accelerating their transformation with confidence.',
    cta_template: 'Schedule your enterprise demo',
    priority: 10,
    confidence_threshold: 0.8
  },
  {
    id: 'exec-mid-market-awareness',
    name: 'Executive - Mid-Market - Awareness Stage',
    personas: ['Business Leader'],
    buyer_stages: ['awareness'],
    company_sizes: ['mid-market'],
    intro_template: 'Mid-market {{industry}} companies like {{company_name}} are discovering new approaches to driving growth and efficiency in competitive markets.',
    cta_template: 'Learn what\'s possible for mid-market leaders',
    priority: 8,
    confidence_threshold: 0.7
  },
  {
    id: 'exec-smb-awareness',
    name: 'Executive - SMB - Awareness Stage',
    personas: ['Business Leader'],
    buyer_stages: ['awareness'],
    company_sizes: ['SMB', 'startup'],
    intro_template: 'Growing {{industry}} businesses like {{company_name}} need solutions that scale without complexity. See how other companies are building for the future.',
    cta_template: 'Explore solutions for growing businesses',
    priority: 8,
    confidence_threshold: 0.7
  },

  // GTM PERSONAS (Security, Operations, Finance)
  {
    id: 'security-enterprise-evaluation',
    name: 'Security - Enterprise - Evaluation Stage',
    personas: ['Security'],
    buyer_stages: ['evaluation'],
    company_sizes: ['enterprise'],
    intro_template: 'Security teams at {{company_name}} are evaluating solutions that balance protection with operational efficiency. See how enterprise security leaders are modernizing their approach.',
    cta_template: 'Compare enterprise security capabilities',
    priority: 9,
    confidence_threshold: 0.8
  },
  {
    id: 'security-mid-market-awareness',
    name: 'Security - Mid-Market - Awareness Stage',
    personas: ['Security'],
    buyer_stages: ['awareness'],
    company_sizes: ['mid-market', 'SMB'],
    intro_template: 'Security professionals in {{industry}} companies like {{company_name}} are discovering how to strengthen defenses without expanding teams or budgets.',
    cta_template: 'Learn modern security approaches',
    priority: 7,
    confidence_threshold: 0.7
  },
  {
    id: 'ops-enterprise-evaluation',
    name: 'Operations - Enterprise - Evaluation Stage',
    personas: ['Operations'],
    buyer_stages: ['evaluation'],
    company_sizes: ['enterprise'],
    intro_template: 'Operations teams at {{company_name}} are comparing solutions to streamline workflows and improve reliability across {{industry}} infrastructure.',
    cta_template: 'Compare operational efficiency solutions',
    priority: 9,
    confidence_threshold: 0.8
  },
  {
    id: 'ops-mid-market-awareness',
    name: 'Operations - Mid-Market - Awareness Stage',
    personas: ['Operations'],
    buyer_stages: ['awareness'],
    company_sizes: ['mid-market', 'SMB'],
    intro_template: 'Operations leaders at {{company_name}} are exploring how {{industry}} companies are automating processes and reducing manual work.',
    cta_template: 'See how operations teams improve efficiency',
    priority: 7,
    confidence_threshold: 0.7
  },
  {
    id: 'finance-enterprise-evaluation',
    name: 'Finance - Enterprise - Evaluation Stage',
    personas: ['Finance'],
    buyer_stages: ['evaluation'],
    company_sizes: ['enterprise'],
    intro_template: 'Finance teams at {{company_name}} are evaluating solutions that deliver clear ROI and support {{industry}} financial planning at scale.',
    cta_template: 'Compare ROI and cost optimization',
    priority: 9,
    confidence_threshold: 0.8
  },
  {
    id: 'finance-mid-market-awareness',
    name: 'Finance - Mid-Market - Awareness Stage',
    personas: ['Finance'],
    buyer_stages: ['awareness'],
    company_sizes: ['mid-market', 'SMB'],
    intro_template: 'Finance leaders in {{industry}} companies like {{company_name}} are discovering how to optimize spending while driving growth.',
    cta_template: 'Learn about cost-effective solutions',
    priority: 7,
    confidence_threshold: 0.7
  },

  // TECHNICAL PERSONAS
  {
    id: 'technical-enterprise-evaluation',
    name: 'Technical - Enterprise - Evaluation Stage',
    personas: ['IT'],
    buyer_stages: ['evaluation'],
    company_sizes: ['enterprise'],
    intro_template: 'Technical teams at {{company_name}} are evaluating {{industry}} platforms that integrate seamlessly and scale with enterprise architecture requirements.',
    cta_template: 'Compare technical capabilities and integrations',
    priority: 9,
    confidence_threshold: 0.8
  },
  {
    id: 'technical-mid-market-awareness',
    name: 'Technical - Mid-Market - Awareness Stage',
    personas: ['IT'],
    buyer_stages: ['awareness'],
    company_sizes: ['mid-market', 'SMB'],
    intro_template: 'Technical professionals at {{company_name}} are exploring modern {{industry}} solutions that are powerful yet simple to implement and maintain.',
    cta_template: 'Explore technical architecture and integrations',
    priority: 7,
    confidence_threshold: 0.7
  },
  {
    id: 'technical-decision',
    name: 'Technical - Decision Stage',
    personas: ['IT'],
    buyer_stages: ['decision'],
    intro_template: 'Technical teams at {{company_name}} are finalizing {{industry}} platform decisions. See detailed architecture, security, and integration documentation.',
    cta_template: 'Review technical specifications',
    priority: 10,
    confidence_threshold: 0.8
  },

  // FALLBACK TEMPLATES (low confidence, broad matching)
  {
    id: 'fallback-evaluation',
    name: 'Fallback - Evaluation Stage',
    personas: ['Business Leader', 'IT', 'Finance', 'Operations', 'Security'],
    buyer_stages: ['evaluation'],
    intro_template: 'As your team evaluates solutions for {{industry}}, see how companies are making confident decisions with comprehensive comparisons.',
    cta_template: 'Compare solutions side-by-side',
    priority: 3,
    confidence_threshold: 0.0
  },
  {
    id: 'fallback-awareness',
    name: 'Fallback - Awareness Stage',
    personas: ['Business Leader', 'IT', 'Finance', 'Operations', 'Security'],
    buyer_stages: ['awareness'],
    intro_template: 'Discover how {{industry}} companies are modernizing their approach to solve today\'s biggest challenges.',
    cta_template: 'Learn what\'s possible',
    priority: 2,
    confidence_threshold: 0.0
  },
  {
    id: 'fallback-decision',
    name: 'Fallback - Decision Stage',
    personas: ['Business Leader', 'IT', 'Finance', 'Operations', 'Security'],
    buyer_stages: ['decision'],
    intro_template: 'Your team is making important decisions about {{industry}} solutions. Get the detailed information you need to move forward with confidence.',
    cta_template: 'Get started today',
    priority: 3,
    confidence_threshold: 0.0
  },
  {
    id: 'fallback-generic',
    name: 'Fallback - Generic',
    personas: ['Business Leader', 'IT', 'Finance', 'Operations', 'Security'],
    buyer_stages: ['awareness', 'evaluation', 'decision'],
    intro_template: 'See how companies in {{industry}} are solving complex challenges with modern solutions designed for teams like yours.',
    cta_template: 'Explore solutions',
    priority: 1,
    confidence_threshold: 0.0
  }
];

/**
 * Select the best template based on enrichment and persona data
 */
export function selectTemplate(
  enrichment: RADEnrichmentResponse,
  persona: Persona,
  buyerStage: BuyerStage
): PersonalizationTemplate {
  // Filter templates by criteria match
  const candidates = TEMPLATES.filter(template => {
    // Must match persona
    if (!template.personas.includes(persona)) {
      return false;
    }

    // Must match buyer stage
    if (!template.buyer_stages.includes(buyerStage)) {
      return false;
    }

    // Must meet confidence threshold
    if (template.confidence_threshold > enrichment.confidence_score) {
      return false;
    }

    // Optional: filter by industry (if template specifies)
    if (template.industries && template.industries.length > 0) {
      if (!template.industries.includes(enrichment.industry)) {
        return false;
      }
    }

    // Optional: filter by company size (if template specifies)
    if (template.company_sizes && template.company_sizes.length > 0) {
      if (!template.company_sizes.includes(enrichment.company_size)) {
        return false;
      }
    }

    return true;
  });

  // Score each candidate
  const scored = candidates.map(template => ({
    template,
    score: scoreTemplate(template, enrichment, persona, buyerStage)
  }));

  // Sort by score desc
  scored.sort((a, b) => b.score - a.score);

  // Return best match or ultimate fallback
  if (scored.length > 0) {
    console.log(`[Template] Selected: ${scored[0].template.id} (score: ${scored[0].score.toFixed(2)})`);
    return scored[0].template;
  }

  // Ultimate fallback
  console.log('[Template] Using ultimate fallback template');
  return TEMPLATES[TEMPLATES.length - 1]; // 'fallback-generic'
}

/**
 * Score a template based on how well it matches the context
 */
function scoreTemplate(
  template: PersonalizationTemplate,
  enrichment: RADEnrichmentResponse,
  persona: Persona,
  buyerStage: BuyerStage
): number {
  let score = template.priority;

  // Bonus points for industry match (if template specifies industries)
  if (template.industries?.includes(enrichment.industry)) {
    score += 5;
  }

  // Bonus points for company size match (if template specifies sizes)
  if (template.company_sizes?.includes(enrichment.company_size)) {
    score += 3;
  }

  // Bonus points for higher confidence enrichment
  score += enrichment.confidence_score * 2;

  // Bonus if template is highly specific (fewer persona/stage options)
  const specificity = 1 / (template.personas.length * template.buyer_stages.length);
  score += specificity * 2;

  // Penalty for fallback templates
  if (template.id.startsWith('fallback')) {
    score -= 5;
  }

  return score;
}

/**
 * Fill template variables with enrichment data
 */
export function fillTemplate(
  template: string,
  enrichment: RADEnrichmentResponse,
  persona: Persona,
  buyerStage: BuyerStage
): string {
  return template
    .replace(/\{\{company_name\}\}/g, enrichment.company_name)
    .replace(/\{\{industry\}\}/g, enrichment.industry)
    .replace(/\{\{news\}\}/g, enrichment.news_summary || 'recent developments')
    .replace(/\{\{persona\}\}/g, persona)
    .replace(/\{\{buyer_stage\}\}/g, buyerStage)
    .replace(/\{\{company_size\}\}/g, enrichment.company_size);
}

/**
 * Get all available templates (for testing/debugging)
 */
export function getAllTemplates(): PersonalizationTemplate[] {
  return TEMPLATES;
}

/**
 * Get template by ID (for testing/debugging)
 */
export function getTemplateById(id: string): PersonalizationTemplate | undefined {
  return TEMPLATES.find(t => t.id === id);
}
