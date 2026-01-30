import type { Persona, BuyerStage } from '../schemas';

/**
 * Extract domain from email address
 * @param email - Email address
 * @returns Domain part of the email
 */
export function extractDomain(email: string): string {
  const parts = email.split('@');
  if (parts.length !== 2) {
    throw new Error('Invalid email format');
  }
  return parts[1].toLowerCase();
}

/**
 * Infer persona from email prefix
 * @param email - Email address
 * @returns Inferred persona
 */
export function inferPersona(email: string): Persona {
  const prefix = email.split('@')[0].toLowerCase();

  const personaMap: Record<string, Persona> = {
    ops: 'Operations',
    operations: 'Operations',
    rev: 'Business Leader',
    revenue: 'Business Leader',
    security: 'Security',
    sec: 'Security',
    it: 'IT',
    tech: 'IT',
    finance: 'Finance',
    fin: 'Finance',
    cfo: 'Finance',
    cto: 'IT',
    ciso: 'Security',
    coo: 'Operations',
  };

  // Check if prefix matches any persona
  for (const [key, value] of Object.entries(personaMap)) {
    if (prefix.startsWith(key) || prefix.includes(key)) {
      return value;
    }
  }

  return 'Business Leader';
}

/**
 * Infer buyer stage from CTA
 * @param cta - Call-to-action string
 * @returns Buyer stage
 */
export function inferBuyerStage(cta: string): BuyerStage {
  const ctaLower = cta.toLowerCase();

  const stageMap: Record<string, BuyerStage> = {
    compare: 'evaluation',
    evaluate: 'evaluation',
    learn: 'awareness',
    discover: 'awareness',
    explore: 'awareness',
    demo: 'decision',
    buy: 'decision',
    purchase: 'decision',
    trial: 'decision',
  };

  return stageMap[ctaLower] || 'evaluation';
}
