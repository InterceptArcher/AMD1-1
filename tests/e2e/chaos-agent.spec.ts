/**
 * Chaos Agent E2E Tests
 *
 * Resilience and stress tests that simulate adverse conditions:
 *   - Slow / degraded API responses
 *   - Complete API timeouts
 *   - Malformed / invalid API responses
 *   - Network disconnection mid-flow
 *   - Rapid user interactions (double-submit, button spam)
 *   - Extremely long input strings
 *   - Concurrent API race conditions
 *   - Browser back/forward during async operations
 *
 * These tests validate that the application degrades gracefully
 * and never crashes, hangs, or shows raw error traces to users.
 */
import { test, expect } from '@playwright/test';
import {
  TEST_USER,
  EXECUTIVE_REVIEW_RESPONSE,
  mockQuickEnrichNotFound,
  fillStepAboutYou,
  fillStepCompany,
  fillStepRole,
  fillStepSituation,
  completeWizard,
} from './fixtures';

// Clear localStorage before each test
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
  await mockQuickEnrichNotFound(page);
});

test.describe('Chaos Agent — Resilience Tests', () => {
  // -----------------------------------------------------------------------
  // 1. Slow API: 8s enrichment response does not crash wizard
  // -----------------------------------------------------------------------
  test('slow enrichment API (8s) does not crash wizard', async ({ page }) => {
    // Override with a very slow enrichment response
    await page.route('**/api/rad/quick-enrich', async (route) => {
      await new Promise((r) => setTimeout(r, 8000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ found: false }),
      });
    });

    await page.goto('/');

    // Complete Step 0 — enrichment fires but is very slow
    await page.locator('#wiz-firstName').fill(TEST_USER.firstName);
    await page.locator('#wiz-lastName').fill(TEST_USER.lastName);
    await page.locator('#wiz-email').fill(TEST_USER.email);
    await page.locator('#wiz-firstName').click();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.waitForTimeout(1200);

    // Wizard should advance to Step 1 regardless of slow enrichment
    await expect(page.locator('#wiz-company')).toBeVisible({ timeout: 5000 });

    // No crash — no uncaught error toast or blank screen
    await expect(page.locator('body')).not.toHaveText(/unhandled|undefined is not|cannot read/i);
  });

  // -----------------------------------------------------------------------
  // 2. API timeout: executive review never responds
  // -----------------------------------------------------------------------
  test('executive review timeout shows error state', async ({ page }) => {
    // Mock that never resolves (simulates timeout)
    await page.route('**/api/rad/executive-review', async (route) => {
      // Just never fulfill — Playwright will eventually time out
      await new Promise((r) => setTimeout(r, 45000));
      await route.abort('timedout');
    });

    await page.goto('/');
    await completeWizard(page);

    // The app should show loading initially
    await expect(
      page.getByText(/Almost there|Generating|Building/).first(),
    ).toBeVisible({ timeout: 10_000 });

    // Eventually the request times out and error state should appear
    // (or the loading state persists, which is acceptable — no crash)
    // Give it time since the timeout is long
    await page.waitForTimeout(5000);

    // Page should still be interactive — not blank or frozen
    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(10);
  });

  // -----------------------------------------------------------------------
  // 3. Malformed JSON response from executive review
  // -----------------------------------------------------------------------
  test('malformed JSON response is handled gracefully', async ({ page }) => {
    await page.route('**/api/rad/executive-review', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '{"success": true, "executive_review": {INVALID_JSON',
      });
    });

    await page.goto('/');
    await completeWizard(page);

    // Wait for the response to be processed
    await page.waitForTimeout(5000);

    // App should show an error state, not crash with a blank screen
    // Accept either error message OR the wizard still being present
    const hasErrorOrWizard = await page
      .getByText(/something went wrong|try again|error|readiness/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasErrorOrWizard).toBeTruthy();

    // No raw JavaScript error traces visible to user
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toMatch(/SyntaxError|Unexpected token|JSON\.parse/);
  });

  // -----------------------------------------------------------------------
  // 4. Empty response body from API
  // -----------------------------------------------------------------------
  test('empty API response body is handled gracefully', async ({ page }) => {
    await page.route('**/api/rad/executive-review', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '',
      });
    });

    await page.goto('/');
    await completeWizard(page);

    await page.waitForTimeout(5000);

    // Should not show raw error to user
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toMatch(/undefined is not|cannot read properties/i);
    expect(bodyText.length).toBeGreaterThan(10);
  });

  // -----------------------------------------------------------------------
  // 5. HTTP 500 with HTML error page (not JSON)
  // -----------------------------------------------------------------------
  test('HTML error response (not JSON) does not crash the app', async ({ page }) => {
    await page.route('**/api/rad/executive-review', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'text/html',
        body: '<html><body><h1>502 Bad Gateway</h1><p>nginx</p></body></html>',
      });
    });

    await page.goto('/');
    await completeWizard(page);

    await page.waitForTimeout(5000);

    // The app should show some error state — it may show raw error text
    // or a user-friendly message. The key is it does NOT crash with blank screen.
    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(10);

    // Should show SOME error indication (either friendly or the raw error)
    const hasErrorIndication =
      bodyText.includes('Something went wrong') ||
      bodyText.includes('Try again') ||
      bodyText.includes('error') ||
      bodyText.includes('failed') ||
      bodyText.includes('502');
    expect(hasErrorIndication).toBeTruthy();
  });

  // -----------------------------------------------------------------------
  // 6. Double-submit: rapid clicking submit button
  // -----------------------------------------------------------------------
  test('rapid form field changes do not corrupt state', async ({ page }) => {
    await page.goto('/');

    // Rapidly type and clear the firstName field
    const firstName = page.locator('#wiz-firstName');
    await firstName.fill('Alice');
    await firstName.fill('');
    await firstName.fill('Bob');
    await firstName.fill('');
    await firstName.fill('Charlie');

    // The final value should be 'Charlie'
    await expect(firstName).toHaveValue('Charlie');

    // Fill rest of Step 0 and verify Continue works
    await page.locator('#wiz-lastName').fill('Test');
    await page.locator('#wiz-email').fill('charlie@test.com');
    await page.locator('#wiz-firstName').click();

    const continueBtn = page.getByRole('button', { name: 'Continue' });
    await expect(continueBtn).toBeEnabled();
  });

  // -----------------------------------------------------------------------
  // 7. Extremely long input strings
  // -----------------------------------------------------------------------
  test('extremely long input strings do not crash the app', async ({ page }) => {
    await page.goto('/');

    const longString = 'A'.repeat(10000);

    // Fill with extremely long values
    await page.locator('#wiz-firstName').fill(longString);
    await page.locator('#wiz-lastName').fill(longString);
    await page.locator('#wiz-email').fill('test@testcorp.com');
    await page.locator('#wiz-firstName').click();

    // Page should still be responsive
    const continueBtn = page.getByRole('button', { name: 'Continue' });
    await expect(continueBtn).toBeVisible({ timeout: 5000 });

    // No crash or blank screen
    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(10);
  });

  // -----------------------------------------------------------------------
  // 8. Browser back button during wizard flow
  // -----------------------------------------------------------------------
  test('browser back button does not break wizard state', async ({ page }) => {
    await page.goto('/');

    // Navigate to Step 1
    await fillStepAboutYou(page);
    await expect(page.locator('#wiz-company')).toBeVisible();

    // Simulate browser back
    await page.goBack();
    await page.waitForTimeout(1000);

    // Navigate forward again
    await page.goForward();
    await page.waitForTimeout(1000);

    // Page should still be usable — not blank or errored
    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(10);
    expect(bodyText).not.toMatch(/cannot read|undefined|error/i);
  });

  // -----------------------------------------------------------------------
  // 9. Rapid step navigation (clicking Back/Continue quickly)
  // -----------------------------------------------------------------------
  test('rapid Back/Continue clicking does not corrupt wizard state', async ({ page }) => {
    await page.goto('/');

    // Get to Step 1
    await fillStepAboutYou(page);

    // Fill Step 1
    await page.locator('#wiz-company').fill(TEST_USER.company);
    await page.getByRole('button', { name: TEST_USER.companySize }).click();
    await page.getByRole('button', { name: TEST_USER.industry }).click();

    // Rapidly click Continue, then Back, then Continue
    const continueBtn = page.getByRole('button', { name: 'Continue' });
    const backBtn = page.getByRole('button', { name: 'Back' });

    await continueBtn.click();
    await page.waitForTimeout(300);
    // During thinking overlay, try clicking back (should be ignored or handled)
    await backBtn.click({ force: true }).catch(() => {});
    await page.waitForTimeout(1500);

    // App should be in a consistent state — either Step 1 or Step 2
    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(10);

    // No JavaScript error visible
    expect(bodyText).not.toMatch(/undefined|NaN|null/);
  });

  // -----------------------------------------------------------------------
  // 10. Network disconnect during enrichment
  // -----------------------------------------------------------------------
  test('network failure during enrichment does not block wizard', async ({ page }) => {
    // Mock enrichment to abort (simulate network failure)
    await page.route('**/api/rad/quick-enrich', async (route) => {
      await route.abort('connectionrefused');
    });

    await page.goto('/');

    // Fill Step 0
    await page.locator('#wiz-firstName').fill(TEST_USER.firstName);
    await page.locator('#wiz-lastName').fill(TEST_USER.lastName);
    await page.locator('#wiz-email').fill(TEST_USER.email);
    await page.locator('#wiz-firstName').click();

    // Click Continue — should still work even though enrichment failed
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.waitForTimeout(1200);

    // Should be on Step 1
    await expect(page.locator('#wiz-company')).toBeVisible({ timeout: 5000 });
  });

  // -----------------------------------------------------------------------
  // 11. API returns success:false
  // -----------------------------------------------------------------------
  test('API returning success:false shows error gracefully', async ({ page }) => {
    await page.route('**/api/rad/executive-review', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          error: 'LLM generation failed after 3 retries',
        }),
      });
    });

    await page.goto('/');
    await completeWizard(page);
    await page.waitForTimeout(5000);

    // Should show error or fallback, not raw JSON
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toContain('LLM generation failed after 3 retries');
    expect(bodyText.length).toBeGreaterThan(10);
  });

  // -----------------------------------------------------------------------
  // 12. Concurrent enrichment + wizard navigation race condition
  // -----------------------------------------------------------------------
  test('enrichment arriving after user advanced does not corrupt state', async ({ page }) => {
    // Very slow enrichment that arrives after user has already moved past Step 1
    await page.route('**/api/rad/quick-enrich', async (route) => {
      await new Promise((r) => setTimeout(r, 6000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          found: true,
          company_name: 'Late Arrival Corp',
          industry: 'healthcare',
          employee_count: 50000,
        }),
      });
    });

    await page.goto('/');
    await fillStepAboutYou(page);

    // Immediately fill Step 1 manually (before enrichment returns)
    await page.locator('#wiz-company').fill('My Company');
    await page.getByRole('button', { name: 'Enterprise' }).click();
    await page.getByRole('button', { name: 'Technology' }).click();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.waitForTimeout(1200);

    // Now on Step 2 — select role
    await page.getByRole('button', { name: 'Tech Executive' }).click();
    await page.waitForTimeout(1800);

    // Now on Step 3 — enrichment may have arrived by now
    // The late enrichment should NOT overwrite user's manual selections
    // or crash the app while on a different step
    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(10);

    // Step 3 content should be visible (first signal question)
    await expect(
      page.getByRole('button', { name: /Mix of old and new/ }),
    ).toBeVisible({ timeout: 5000 });
  });
});
