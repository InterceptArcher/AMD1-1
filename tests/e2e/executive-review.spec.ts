/**
 * Executive Review E2E Tests
 *
 * Validates the full flow: wizard submission -> loading spinner ->
 * executive review results display -> error handling -> reset.
 * All API calls are mocked via shared fixtures so no real backend is required.
 */
import { test, expect } from '@playwright/test';
import {
  TEST_USER,
  EXECUTIVE_REVIEW_RESPONSE,
  mockQuickEnrichNotFound,
  mockExecutiveReviewSuccess,
  mockExecutiveReviewError,
  completeWizard,
} from './fixtures';

// ---------------------------------------------------------------------------
// Clear localStorage before each test so wizard state never leaks between runs
// ---------------------------------------------------------------------------
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
});

test.describe('Executive Review Flow', () => {
  // -----------------------------------------------------------------------
  // 1. Loading state appears after wizard submission
  // -----------------------------------------------------------------------
  test('shows loading state after submission', async ({ page }) => {
    await mockQuickEnrichNotFound(page);

    // Use a slow mock (2s delay) so the loading state is visible
    await page.route('**/api/rad/executive-review', async (route) => {
      await new Promise((r) => setTimeout(r, 2000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(EXECUTIVE_REVIEW_RESPONSE),
      });
    });

    await page.goto('/');
    await completeWizard(page);

    // With the delayed response, the loading state should be visible
    await expect(
      page.getByText(/Almost there|Generating|Building/).first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  // -----------------------------------------------------------------------
  // 2. Executive review results display correctly
  // -----------------------------------------------------------------------
  test('displays executive review results', async ({ page }) => {
    await mockQuickEnrichNotFound(page);
    await mockExecutiveReviewSuccess(page);
    await page.goto('/');

    await completeWizard(page);

    // Wait for results to render (loading state resolves once the mock API returns)
    await expect(
      page.getByText('Enterprise AI Readiness Snapshot for'),
    ).toBeVisible({ timeout: 30_000 });

    // Company name in header
    await expect(page.getByText('TestCorp', { exact: true }).first()).toBeVisible();

    // Stage displayed
    await expect(page.getByText('Challenger', { exact: true }).first()).toBeVisible();

    // ADVANTAGES section with headline
    await expect(page.getByText('Advantages', { exact: false })).toBeVisible();
    await expect(page.getByText('Cloud-Ready Infrastructure')).toBeVisible();

    // RISKS section with headline
    await expect(page.getByText('Risks', { exact: false })).toBeVisible();
    await expect(page.getByText('Legacy System Dependencies')).toBeVisible();

    // 3 recommendation titles
    await expect(page.getByText('Establish AI Governance Framework')).toBeVisible();
    await expect(page.getByText('Build Unified Data Foundation')).toBeVisible();
    await expect(page.getByText('Accelerate GPU Infrastructure Adoption')).toBeVisible();

    // Case study
    await expect(page.getByRole('heading', { name: 'KT Cloud' })).toBeVisible();

    // Case study link
    await expect(page.getByText('Read the case study')).toBeVisible();
  });

  // -----------------------------------------------------------------------
  // 3. Correct stage styling for Challenger (blue theme)
  // -----------------------------------------------------------------------
  test('shows correct stage styling for Challenger', async ({ page }) => {
    await mockQuickEnrichNotFound(page);
    await mockExecutiveReviewSuccess(page);
    await page.goto('/');

    await completeWizard(page);

    // Wait for results
    await expect(
      page.getByText('Enterprise AI Readiness Snapshot for'),
    ).toBeVisible({ timeout: 30_000 });

    // The stage text "Challenger" should be rendered inside a span with blue styling
    const stageText = page.locator('span').filter({ hasText: /^Challenger$/ });
    await expect(stageText).toBeVisible();
    await expect(stageText).toHaveClass(/text-blue-400/);

    // The parent container should have the blue background/border classes
    const stageContainer = page.locator('.bg-blue-500\\/10');
    await expect(stageContainer).toBeVisible();
  });

  // -----------------------------------------------------------------------
  // 4. Input summary pills display correct values
  // -----------------------------------------------------------------------
  test('displays input summary pills', async ({ page }) => {
    await mockQuickEnrichNotFound(page);
    await mockExecutiveReviewSuccess(page);
    await page.goto('/');

    await completeWizard(page);

    // Wait for results
    await expect(
      page.getByText('Enterprise AI Readiness Snapshot for'),
    ).toBeVisible({ timeout: 30_000 });

    // The input summary pills are rendered as spans with bg-white/10 class
    // Check for the expected pill values from EXECUTIVE_REVIEW_RESPONSE.inputs
    const pillContainer = page.locator('.flex.flex-wrap.gap-2.text-xs');
    await expect(pillContainer).toBeVisible();

    // Verify each pill value
    await expect(pillContainer.getByText('Technology')).toBeVisible();
    await expect(pillContainer.getByText('Enterprise')).toBeVisible();
    await expect(pillContainer.getByText('ITDM')).toBeVisible();
    await expect(pillContainer.getByText('Improving Performance')).toBeVisible();
    await expect(pillContainer.getByText('Integration Friction')).toBeVisible();
  });

  // -----------------------------------------------------------------------
  // 5. API error is handled gracefully
  // -----------------------------------------------------------------------
  test('handles API error gracefully', async ({ page }) => {
    await mockQuickEnrichNotFound(page);
    await mockExecutiveReviewError(page);
    await page.goto('/');

    await completeWizard(page);

    // Wait for error state to appear (loading finishes, error is shown)
    await expect(
      page.getByText('Something went wrong'),
    ).toBeVisible({ timeout: 30_000 });

    // "Try again" button should be visible
    await expect(
      page.getByRole('button', { name: 'Try again' }),
    ).toBeVisible();
  });

  // -----------------------------------------------------------------------
  // 6. Reset button returns user to wizard
  // -----------------------------------------------------------------------
  test('reset button returns to wizard', async ({ page }) => {
    await mockQuickEnrichNotFound(page);
    await mockExecutiveReviewSuccess(page);
    await page.goto('/');

    await completeWizard(page);

    // Wait for results
    await expect(
      page.getByText('Enterprise AI Readiness Snapshot for'),
    ).toBeVisible({ timeout: 30_000 });

    // Click the reset button
    await page.getByRole('button', { name: 'Start over with different information' }).click();

    // Wizard form should reappear — the firstName input on Step 0
    await expect(page.locator('#wiz-firstName')).toBeVisible({ timeout: 10_000 });
  });

  // -----------------------------------------------------------------------
  // 7. Executive review API receives correct request data
  // -----------------------------------------------------------------------
  test('executive review API receives correct data', async ({ page }) => {
    await mockQuickEnrichNotFound(page);

    // Set up a custom route handler that captures the request body before fulfilling
    let capturedBody: Record<string, unknown> | null = null;

    await page.route('**/api/rad/executive-review', async (route) => {
      const request = route.request();
      capturedBody = JSON.parse(request.postData() || '{}');

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(EXECUTIVE_REVIEW_RESPONSE),
      });
    });

    await page.goto('/');

    await completeWizard(page);

    // Wait for results to confirm the API was called
    await expect(
      page.getByText('Enterprise AI Readiness Snapshot for'),
    ).toBeVisible({ timeout: 30_000 });

    // Verify the captured request body contains expected fields
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.email).toBe(TEST_USER.email);
    expect(capturedBody!.firstName).toBe(TEST_USER.firstName);
    expect(capturedBody!.company).toBe(TEST_USER.company);
    expect(capturedBody).toHaveProperty('itEnvironment');
    expect(capturedBody).toHaveProperty('businessPriority');
    expect(capturedBody).toHaveProperty('challenge');
  });
});
