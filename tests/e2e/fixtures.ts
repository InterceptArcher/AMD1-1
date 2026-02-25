/**
 * Shared mock data and helpers for Playwright e2e tests.
 * All API responses are deterministic fixtures — no real backend needed.
 *
 * IMPORTANT: Navigation helpers use waitFor (not waitForTimeout) to handle
 * variable transition speeds in CI. Each step waits for the NEXT step's
 * content to appear before returning.
 */
import { Page, expect } from '@playwright/test';

// ── Test User Data ──────────────────────────────────────────────────
export const TEST_USER = {
  firstName: 'Jane',
  lastName: 'Chen',
  email: 'jane.chen@testcorp.com',
  company: 'TestCorp',
  companySize: 'Enterprise',  // card label text
  industry: 'Technology',     // card label text
  role: 'Tech Executive',     // card label text
};

// ── Quick-Enrich Responses ──────────────────────────────────────────
export const QUICK_ENRICH_FOUND = {
  found: true,
  company_name: 'TestCorp Inc.',
  industry: 'technology',
  employee_count: 5200,
  title: 'VP of Engineering',
  seniority: 'VP',
  company_summary: 'Enterprise software company specializing in cloud infrastructure and AI solutions.',
  founded_year: 2012,
};

export const QUICK_ENRICH_NOT_FOUND = {
  found: false,
};

// ── Executive Review Response ───────────────────────────────────────
export const EXECUTIVE_REVIEW_RESPONSE = {
  success: true,
  company_name: 'TestCorp',
  inputs: {
    industry: 'Technology',
    segment: 'Enterprise',
    persona: 'ITDM',
    stage: 'Challenger',
    priority: 'Improving Performance',
    challenge: 'Integration Friction',
  },
  executive_review: {
    company_name: 'TestCorp',
    stage: 'Challenger',
    stage_sidebar: 'Challengers are actively modernizing their infrastructure and exploring AI integration across business units.',
    stage_identification_text: 'TestCorp is positioned as a Challenger organization, with hybrid cloud adoption underway and growing investment in AI-ready infrastructure.',
    advantages: [
      {
        headline: 'Cloud-Ready Infrastructure',
        description: 'TestCorp has made significant strides in migrating core workloads to hybrid cloud environments, providing the elastic compute foundation needed for AI model training and inference at scale.',
      },
      {
        headline: 'Technical Leadership Depth',
        description: 'With experienced engineering leadership driving modernization initiatives, TestCorp has the organizational capability to evaluate and deploy GPU-accelerated computing for production AI workloads.',
      },
    ],
    risks: [
      {
        headline: 'Legacy System Dependencies',
        description: 'Ongoing reliance on legacy integration layers creates friction when deploying modern AI pipelines, potentially slowing time-to-value for new AI-driven products and services.',
      },
      {
        headline: 'AI Talent Competition',
        description: 'The technology sector faces intense competition for specialized AI and ML engineering talent, which could constrain TestCorp\'s ability to scale AI initiatives rapidly.',
      },
    ],
    recommendations: [
      {
        title: 'Establish AI Governance Framework',
        description: 'Create comprehensive policies for responsible AI deployment, including model validation protocols, bias detection workflows, and risk management procedures aligned with industry standards.',
      },
      {
        title: 'Build Unified Data Foundation',
        description: 'Invest in a unified data platform that consolidates operational and analytical data stores, enabling seamless model training pipelines and reducing data preparation overhead by an estimated 40%.',
      },
      {
        title: 'Accelerate GPU Infrastructure Adoption',
        description: 'Deploy AMD Instinct accelerators across development and production environments to support growing AI workload demands while optimizing total cost of ownership versus cloud-only approaches.',
      },
    ],
    case_study: 'KT Cloud',
    case_study_description: 'South Korean cloud infrastructure provider that achieved 3x AI workload throughput using AMD EPYC processors and Instinct accelerators.',
    case_study_link: 'https://www.amd.com/en/case-studies/kt-cloud',
    case_study_relevance: 'Like KT Cloud, TestCorp can leverage AMD GPU-accelerated computing to scale AI inference workloads while maintaining cost efficiency across hybrid infrastructure.',
  },
  enrichment: {
    first_name: 'Jane',
    last_name: 'Chen',
    title: 'VP of Engineering',
    company_name: 'TestCorp',
    employee_count: 5200,
    founded_year: 2012,
    industry: 'technology',
    data_quality_score: 0.82,
    news_themes: ['AI', 'Cloud Computing', 'Enterprise Software'],
    recent_news: [
      { title: 'TestCorp launches AI platform initiative', source: 'TechCrunch' },
      { title: 'TestCorp expands cloud infrastructure team', source: 'VentureBeat' },
    ],
  },
  inferred_context: {
    it_environment: 'modernizing',
    business_priority: 'improving_performance',
    primary_challenge: 'integration_friction',
    journey_stage: 'consideration',
  },
  news_analysis: {
    sentiment: 'positive',
    ai_readiness: 'challenger',
    crisis: false,
  },
};

// ── Route Mocking Helpers ───────────────────────────────────────────

/** Mock quick-enrich to return not-found (simplest default) */
export async function mockQuickEnrichNotFound(page: Page) {
  await page.route('**/api/rad/quick-enrich', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(QUICK_ENRICH_NOT_FOUND),
    });
  });
}

/** Mock quick-enrich to return found company data */
export async function mockQuickEnrichFound(page: Page) {
  await page.route('**/api/rad/quick-enrich', async (route) => {
    // Simulate realistic API delay
    await new Promise((r) => setTimeout(r, 500));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(QUICK_ENRICH_FOUND),
    });
  });
}

/** Mock quick-enrich to return server error */
export async function mockQuickEnrichError(page: Page) {
  await page.route('**/api/rad/quick-enrich', async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Internal server error' }),
    });
  });
}

/** Mock executive-review to return success */
export async function mockExecutiveReviewSuccess(page: Page) {
  await page.route('**/api/rad/executive-review', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(EXECUTIVE_REVIEW_RESPONSE),
    });
  });
}

/** Mock executive-review to return server error */
export async function mockExecutiveReviewError(page: Page) {
  await page.route('**/api/rad/executive-review', async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Executive review generation failed' }),
    });
  });
}

// ── Wizard Navigation Helpers ───────────────────────────────────────
// Each helper waits for the NEXT step's element to appear (not hardcoded timeouts).
// This is robust across slow CI, fast local dev, and remote Vercel targets.

/** Fill Step 0 (About You) and advance to Step 1 */
export async function fillStepAboutYou(page: Page) {
  await page.locator('#wiz-firstName').fill(TEST_USER.firstName);
  await page.locator('#wiz-lastName').fill(TEST_USER.lastName);
  await page.locator('#wiz-email').fill(TEST_USER.email);
  // Blur email to trigger validation
  await page.locator('#wiz-firstName').click();
  await page.getByRole('button', { name: 'Continue' }).click();
  // Wait for Step 1 content to appear (company input)
  await expect(page.locator('#wiz-company')).toBeVisible({ timeout: 15_000 });
}

/** Fill Step 1 (Company) and advance to Step 2 */
export async function fillStepCompany(page: Page) {
  await page.locator('#wiz-company').fill(TEST_USER.company);
  await page.getByRole('button', { name: TEST_USER.companySize }).click();
  await page.getByRole('button', { name: TEST_USER.industry }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  // Wait for Step 2 content to appear (role selection buttons)
  await expect(
    page.getByRole('button', { name: TEST_USER.role }),
  ).toBeVisible({ timeout: 15_000 });
}

/** Fill Step 2 (Role) — auto-advances to Step 3 */
export async function fillStepRole(page: Page) {
  await page.getByRole('button', { name: TEST_USER.role }).click();
  // Role auto-advances after click. Wait for Step 3 content.
  // Step 3 now starts with signal Q1 — for tech persona: "How old is your infrastructure?"
  // Wait for any Q1 option button to appear.
  await expect(
    page.getByRole('button', { name: /Mix of old and new/ }),
  ).toBeVisible({ timeout: 15_000 });
}

/**
 * Fill Step 3 (Situation) — new multi-signal flow:
 *   1. Answer 4 signal questions (progressive reveal)
 *   2. Select challenge (appears after signals → deduction)
 *   3. Check consent (appears after challenge → stage reveal)
 *
 * Uses "Tech Executive" (technical persona) button labels.
 * Signal answers produce a "Challenger" stage (modernizing + improving_performance).
 */
export async function fillStepSituation(page: Page) {
  // Q1: Infrastructure age → "Mix of old and new" (hybrid → modernizing)
  await page.getByRole('button', { name: /Mix of old and new/ }).click();

  // Q2: AI readiness → "Experimenting with pilots"
  const q2Btn = page.getByRole('button', { name: /Experimenting with pilots/ });
  await expect(q2Btn).toBeVisible({ timeout: 5_000 });
  await q2Btn.click();

  // Q3: Spending focus → "Eliminating bottlenecks" (improving_performance)
  const q3Btn = page.getByRole('button', { name: /Eliminating bottlenecks/ });
  await expect(q3Btn).toBeVisible({ timeout: 5_000 });
  await q3Btn.click();

  // Q4: Team composition → "Mix of ops and new development"
  const q4Btn = page.getByRole('button', { name: /Mix of ops and new development/ });
  await expect(q4Btn).toBeVisible({ timeout: 5_000 });
  await q4Btn.click();

  // Challenge appears after all 4 signals answered + deduction
  // Technology industry: "Toolchain fragmentation"
  const challengeBtn = page.getByRole('button', { name: /Toolchain fragmentation/ });
  await expect(challengeBtn).toBeVisible({ timeout: 10_000 });
  await challengeBtn.click();

  // Consent checkbox appears after challenge → stage reveal
  const consent = page.locator('#wiz-consent');
  await expect(consent).toBeVisible({ timeout: 10_000 });
  await consent.check();
}

/** Complete the entire wizard from start to submission */
export async function completeWizard(page: Page) {
  await fillStepAboutYou(page);
  await fillStepCompany(page);
  await fillStepRole(page);
  await fillStepSituation(page);
  await page.getByRole('button', { name: /Get Your AI Readiness Snapshot/ }).click();
}
