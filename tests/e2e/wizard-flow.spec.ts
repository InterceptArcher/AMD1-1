/**
 * Wizard Flow E2E Tests
 *
 * Validates the 4-step AMD AI Readiness wizard from landing page
 * through final submission. All API calls are mocked via shared fixtures
 * so no real backend is required.
 *
 * Wizard steps:
 *   Step 0 — About You (first name, last name, work email)
 *   Step 1 — Company (company name, size, industry)
 *   Step 2 — Role (auto-advances on selection)
 *   Step 3 — Situation (progressive reveal: IT env -> priority -> challenge -> consent)
 */
import { test, expect } from '@playwright/test';
import {
  TEST_USER,
  mockQuickEnrichNotFound,
  mockExecutiveReviewSuccess,
  fillStepAboutYou,
  fillStepCompany,
  fillStepRole,
  fillStepSituation,
  completeWizard,
} from './fixtures';

// ---------------------------------------------------------------------------
// Clear localStorage before each test so wizard state never leaks between runs.
// Mock quick-enrich to return not-found by default to prevent real API calls.
// ---------------------------------------------------------------------------
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
  await mockQuickEnrichNotFound(page);
});

test.describe('AMD AI Readiness Wizard', () => {
  // -------------------------------------------------------------------------
  // 1. Landing page loads correctly
  // -------------------------------------------------------------------------
  test('landing page loads correctly', async ({ page }) => {
    await page.goto('/');

    // Page title should exist (Next.js default or custom)
    await expect(page).toHaveTitle(/.+/);

    // Hero heading contains "AI Readiness"
    const heroHeading = page.locator('h1');
    await expect(heroHeading).toContainText('AI Readiness');

    // Form card visible — identified by "Get Your Guide" heading
    await expect(page.getByText('Get Your Guide')).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // 2. Step 0: validates required fields
  // -------------------------------------------------------------------------
  test('step 0: validates required fields', async ({ page }) => {
    await page.goto('/');

    const continueBtn = page.getByRole('button', { name: 'Continue' });

    // Continue should be disabled with all fields empty
    await expect(continueBtn).toBeDisabled();

    // Fill only firstName — still disabled (lastName and email missing)
    await page.locator('#wiz-firstName').fill(TEST_USER.firstName);
    await expect(continueBtn).toBeDisabled();

    // Fill lastName too — still disabled (email missing)
    await page.locator('#wiz-lastName').fill(TEST_USER.lastName);
    await expect(continueBtn).toBeDisabled();

    // Fill a valid email — now all three fields are present and valid
    await page.locator('#wiz-email').fill(TEST_USER.email);
    // Blur the email field to trigger validation
    await page.locator('#wiz-firstName').click();

    // Continue should now be enabled
    await expect(continueBtn).toBeEnabled();
  });

  // -------------------------------------------------------------------------
  // 3. Step 0: validates email format
  // -------------------------------------------------------------------------
  test('step 0: validates email format', async ({ page }) => {
    await page.goto('/');

    const emailInput = page.locator('#wiz-email');

    // Type an invalid email and blur to trigger validation
    await emailInput.fill('not-an-email');
    await page.locator('#wiz-firstName').click(); // blur

    // Error message should appear in red
    const errorMsg = page.getByText('Please enter a valid email address');
    await expect(errorMsg).toBeVisible();

    // Now type a valid email and blur
    await emailInput.fill(TEST_USER.email);
    await page.locator('#wiz-firstName').click(); // blur

    // Error message should disappear
    await expect(errorMsg).not.toBeVisible();
  });

  // -------------------------------------------------------------------------
  // 4. Step 0: completes and advances
  // -------------------------------------------------------------------------
  test('step 0: completes and advances', async ({ page }) => {
    await page.goto('/');

    // Fill all About You fields
    await page.locator('#wiz-firstName').fill(TEST_USER.firstName);
    await page.locator('#wiz-lastName').fill(TEST_USER.lastName);
    await page.locator('#wiz-email').fill(TEST_USER.email);
    // Blur email to trigger validation
    await page.locator('#wiz-firstName').click();

    // Click Continue
    await page.getByRole('button', { name: 'Continue' }).click();

    // Wait for thinking overlay to pass (~900ms + buffer)
    await page.waitForTimeout(1200);

    // Verify Step 1 content appears — company input should be visible
    await expect(page.locator('#wiz-company')).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // 5. Step 1: selects company info and advances
  // -------------------------------------------------------------------------
  test('step 1: selects company info and advances', async ({ page }) => {
    await page.goto('/');

    // Navigate through Step 0
    await fillStepAboutYou(page);

    // We should be on Step 1 — fill company name
    await page.locator('#wiz-company').fill(TEST_USER.company);

    // Select company size card and verify selected state
    const sizeBtn = page.getByRole('button', { name: TEST_USER.companySize });
    await sizeBtn.click();
    await expect(sizeBtn).toHaveClass(/selection-card-selected/);

    // Select industry card and verify selected state
    const industryBtn = page.getByRole('button', { name: TEST_USER.industry });
    await industryBtn.click();
    await expect(industryBtn).toHaveClass(/selection-card-selected/);

    // Continue to Step 2
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.waitForTimeout(1200);

    // Verify role cards appear on Step 2
    await expect(page.getByRole('button', { name: 'Tech Executive' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Business Executive' })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Engineer/ })).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // 6. Step 2: role selection auto-advances
  // -------------------------------------------------------------------------
  test('step 2: role selection auto-advances', async ({ page }) => {
    await page.goto('/');

    // Navigate through Steps 0 and 1
    await fillStepAboutYou(page);
    await fillStepCompany(page);

    // We should be on Step 2 — click Tech Executive role
    const roleBtn = page.getByRole('button', { name: 'Tech Executive' });
    await expect(roleBtn).toBeVisible();
    await roleBtn.click();

    // Role step auto-advances after 500ms delay + 900ms thinking overlay
    await page.waitForTimeout(1800);

    // Verify Step 3 content appears — IT environment cards should be visible
    // Tech Executive is a technical persona, so the label is "In the middle of a shift"
    await expect(
      page.getByRole('button', { name: /In the middle of a shift/ }),
    ).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // 7. Step 3: progressive reveal works
  // -------------------------------------------------------------------------
  test('step 3: progressive reveal works', async ({ page }) => {
    await page.goto('/');

    // Navigate through Steps 0-2
    await fillStepAboutYou(page);
    await fillStepCompany(page);
    await fillStepRole(page);

    // We are on Step 3. Section 1 (IT environment) should be visible.
    // Section 2 (priority) should NOT be visible yet.
    await expect(
      page.getByRole('button', { name: /Eliminate bottlenecks/ }),
    ).not.toBeVisible();

    // Select IT environment: "In the middle of a shift" (modernizing)
    await page.getByRole('button', { name: /In the middle of a shift/ }).click();
    await page.waitForTimeout(500);

    // Section 2 (priority) should now be visible
    await expect(
      page.getByRole('button', { name: /Eliminate bottlenecks/ }),
    ).toBeVisible();

    // Section 3 (challenge) should NOT be visible yet
    await expect(
      page.getByRole('button', { name: /Toolchain fragmentation/ }),
    ).not.toBeVisible();

    // Select a priority
    await page.getByRole('button', { name: /Eliminate bottlenecks/ }).click();
    await page.waitForTimeout(500);

    // Section 3 (challenge) should now be visible (technology industry challenges)
    await expect(
      page.getByRole('button', { name: /Toolchain fragmentation/ }),
    ).toBeVisible();

    // Section 4 (consent) should NOT be visible yet
    await expect(page.locator('#wiz-consent')).not.toBeVisible();

    // Select a challenge
    await page.getByRole('button', { name: /Toolchain fragmentation/ }).click();
    await page.waitForTimeout(500);

    // Section 4 — consent checkbox and assessment preview should now appear
    await expect(page.locator('#wiz-consent')).toBeVisible();
    await expect(page.getByText('Assessment Preview')).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // 8. Step 3: consent required for submission
  // -------------------------------------------------------------------------
  test('step 3: consent required for submission', async ({ page }) => {
    await page.goto('/');

    // Navigate through Steps 0-2
    await fillStepAboutYou(page);
    await fillStepCompany(page);
    await fillStepRole(page);

    // Fill all Step 3 fields (IT env, priority, challenge) but do NOT check consent
    await page.getByRole('button', { name: /In the middle of a shift/ }).click();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /Eliminate bottlenecks/ }).click();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /Toolchain fragmentation/ }).click();
    await page.waitForTimeout(500);

    // Submit button should be visible but disabled (consent not checked)
    const submitBtn = page.getByRole('button', { name: /Get Your AI Readiness Snapshot/ });
    await expect(submitBtn).toBeVisible();
    await expect(submitBtn).toBeDisabled();

    // Check the consent checkbox
    await page.locator('#wiz-consent').check();

    // Submit button should now be enabled
    await expect(submitBtn).toBeEnabled();
  });

  // -------------------------------------------------------------------------
  // 9. Back button navigates to previous steps
  // -------------------------------------------------------------------------
  test('back button navigates to previous steps', async ({ page }) => {
    await page.goto('/');

    // Navigate through Step 0 to reach Step 1
    await fillStepAboutYou(page);

    // We should be on Step 1 — verify company field is visible
    await expect(page.locator('#wiz-company')).toBeVisible();

    // Back button should be visible on Step 1
    const backBtn = page.getByRole('button', { name: 'Back' });
    await expect(backBtn).toBeVisible();

    // Click Back
    await backBtn.click();

    // Verify we are back on Step 0 — firstName should be visible with saved value
    const firstNameInput = page.locator('#wiz-firstName');
    await expect(firstNameInput).toBeVisible();
    await expect(firstNameInput).toHaveValue(TEST_USER.firstName);

    // lastName and email should also retain their values
    await expect(page.locator('#wiz-lastName')).toHaveValue(TEST_USER.lastName);
    await expect(page.locator('#wiz-email')).toHaveValue(TEST_USER.email);
  });

  // -------------------------------------------------------------------------
  // 10. Full wizard completion
  // -------------------------------------------------------------------------
  test('full wizard completion', async ({ page }) => {
    // Mock the executive review API to return success
    await mockExecutiveReviewSuccess(page);
    await page.goto('/');

    // Complete the entire wizard using helpers
    await completeWizard(page);

    // After clicking submit, the wizard should transition to a loading or results state.
    // The page shows a loading spinner ("Generating Your Assessment...") or the
    // executive review results (containing the company name).
    await expect(
      page.getByText(/Generating Your Assessment|TestCorp/).first(),
    ).toBeVisible({ timeout: 10000 });
  });
});
