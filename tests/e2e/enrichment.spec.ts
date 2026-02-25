/**
 * Email-First Enrichment E2E Tests
 *
 * Validates the quick-enrich feature: when a user enters a work email on
 * Step 0, the frontend calls POST /api/rad/quick-enrich to look up their
 * company and pre-fill wizard fields on Step 1.
 *
 * All API calls are mocked via shared fixtures — no real backend needed.
 */
import { test, expect } from '@playwright/test';
import {
  TEST_USER,
  QUICK_ENRICH_FOUND,
  mockQuickEnrichFound,
  mockQuickEnrichNotFound,
  mockQuickEnrichError,
  fillStepAboutYou,
} from './fixtures';

// Clear localStorage before each test so wizard state never leaks between runs
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
});

test.describe('Email-first enrichment', () => {
  // -------------------------------------------------------------------------
  // 1. Work email triggers enrichment API call
  // -------------------------------------------------------------------------
  test('work email triggers enrichment API call', async ({ page }) => {
    await mockQuickEnrichFound(page);
    await page.goto('/');

    // Fill first name and last name so email blur has somewhere to land
    await page.locator('#wiz-firstName').fill(TEST_USER.firstName);
    await page.locator('#wiz-lastName').fill(TEST_USER.lastName);

    // Fill work email
    await page.locator('#wiz-email').fill(TEST_USER.email);

    // Set up the response waiter BEFORE triggering blur
    const enrichPromise = page.waitForResponse('**/api/rad/quick-enrich');

    // Blur email by clicking another field
    await page.locator('#wiz-firstName').click();

    // Verify the API call was actually made
    const response = await enrichPromise;
    expect(response.status()).toBe(200);
  });

  // -------------------------------------------------------------------------
  // 2. Enrichment pre-fills company fields on Step 1
  // -------------------------------------------------------------------------
  test('enrichment pre-fills company fields', async ({ page }) => {
    await mockQuickEnrichFound(page);
    await page.goto('/');

    // Complete Step 0 (About You) — this triggers enrichment on email blur
    await fillStepAboutYou(page);

    // We should now be on Step 1 — verify pre-filled fields

    // Company name input should be pre-filled (either from enrichment or domain extraction)
    // The frontend extracts company from email domain immediately, then enrichment may
    // overwrite if the field was still empty. Either way, the field should not be empty.
    const companyInput = page.locator('#wiz-company');
    await expect(companyInput).not.toHaveValue('');

    // Company size "Enterprise" card should be selected
    // (employee_count 5200 maps to 'enterprise' via employeeCountToSize)
    const enterpriseBtn = page.getByRole('button', { name: 'Enterprise' });
    await expect(enterpriseBtn).toHaveClass(/selection-card-selected/);

    // Industry "Technology" card should be selected
    // (industry 'technology' maps to 'technology' via normalizeEnrichmentIndustry)
    const technologyBtn = page.getByRole('button', { name: 'Technology' });
    await expect(technologyBtn).toHaveClass(/selection-card-selected/);

    // Detection banner should be visible with enrichment company name
    const banner = page.locator('.company-detected');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText('We found');
  });

  // -------------------------------------------------------------------------
  // 3. Free email does not trigger enrichment
  // -------------------------------------------------------------------------
  test('free email does not trigger enrichment', async ({ page }) => {
    let enrichCalled = false;

    // Set up a route handler that tracks whether it was called
    await page.route('**/api/rad/quick-enrich', async (route) => {
      enrichCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ found: false }),
      });
    });

    await page.goto('/');

    // Fill names
    await page.locator('#wiz-firstName').fill(TEST_USER.firstName);
    await page.locator('#wiz-lastName').fill(TEST_USER.lastName);

    // Fill a free/personal email (gmail)
    await page.locator('#wiz-email').fill('test@gmail.com');

    // Blur the email field
    await page.locator('#wiz-firstName').click();

    // Give time for any async call to fire (if it were going to)
    await page.waitForTimeout(1000);

    // Verify the enrichment route was NOT called
    expect(enrichCalled).toBe(false);
  });

  // -------------------------------------------------------------------------
  // 4. Enrichment failure does not break wizard
  // -------------------------------------------------------------------------
  test('enrichment failure does not break wizard', async ({ page }) => {
    await mockQuickEnrichError(page);
    await page.goto('/');

    // Complete Step 0 — enrichment will fail with 500 but wizard should continue
    await fillStepAboutYou(page);

    // We should be on Step 1 without any crash

    // Company name should be empty (not pre-filled since enrichment failed)
    // Note: the domain-extraction fallback may set company from email domain,
    // but the enrichment banner should NOT appear
    const companyInput = page.locator('#wiz-company');
    await expect(companyInput).toBeVisible();

    // No enrichment detection banner should appear
    const banner = page.locator('.company-detected');
    // The rich enrichment banner should not be present (enrichment failed)
    // A simple domain-detection banner might appear, but .company-detected
    // with "We found" text should not
    await expect(banner).not.toContainText('We found');

    // User can still manually fill the company and continue
    await companyInput.clear();
    await companyInput.fill('Manual Corp');

    // Select company size
    await page.getByRole('button', { name: 'Enterprise' }).click();

    // Select industry
    await page.getByRole('button', { name: 'Technology' }).click();

    // Continue button should be enabled
    const continueBtn = page.getByRole('button', { name: 'Continue' });
    await expect(continueBtn).toBeEnabled();

    // Click continue — should advance to Step 2 (Role)
    await continueBtn.click();
    await page.waitForTimeout(1200);

    // Verify we advanced — role cards should be visible
    await expect(page.getByRole('button', { name: 'Tech Executive' })).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // 5. Enrichment banner shows company details
  // -------------------------------------------------------------------------
  test('enrichment banner shows company details', async ({ page }) => {
    await mockQuickEnrichFound(page);
    await page.goto('/');

    // Complete Step 0 to trigger enrichment and advance to Step 1
    await fillStepAboutYou(page);

    // Verify the banner exists and contains detailed information
    const banner = page.locator('.company-detected');
    await expect(banner).toBeVisible();

    // Company name
    await expect(banner).toContainText('We found');
    await expect(banner).toContainText(QUICK_ENRICH_FOUND.company_name);

    // Title (VP of Engineering)
    await expect(banner).toContainText(QUICK_ENRICH_FOUND.title!);

    // Employee count — rendered with toLocaleString() so "5,200"
    await expect(banner).toContainText('5,200');
    await expect(banner).toContainText('employees');

    // Industry tag
    await expect(banner).toContainText(QUICK_ENRICH_FOUND.industry);

    // Founded year
    await expect(banner).toContainText(`Founded ${QUICK_ENRICH_FOUND.founded_year}`);

    // Footer text
    await expect(banner).toContainText('Fields pre-filled');
    await expect(banner).toContainText('feel free to edit');
  });

  // -------------------------------------------------------------------------
  // 6. User can override pre-filled fields
  // -------------------------------------------------------------------------
  test('user can override pre-filled fields', async ({ page }) => {
    await mockQuickEnrichFound(page);
    await page.goto('/');

    // Complete Step 0 — enrichment pre-fills Step 1
    await fillStepAboutYou(page);

    // Verify pre-fill happened (company field should not be empty)
    await expect(page.locator('#wiz-company')).not.toHaveValue('');

    // Override company name
    await page.locator('#wiz-company').clear();
    await page.locator('#wiz-company').fill('Different Corp');
    await expect(page.locator('#wiz-company')).toHaveValue('Different Corp');

    // Override industry — select Financial Services instead of Technology
    const finServicesBtn = page.getByRole('button', { name: 'Financial Services' });
    await finServicesBtn.click();
    await expect(finServicesBtn).toHaveClass(/selection-card-selected/);

    // Technology should no longer be selected
    const technologyBtn = page.getByRole('button', { name: 'Technology' });
    await expect(technologyBtn).not.toHaveClass(/selection-card-selected/);

    // Enterprise size should still be selected (we did not change it)
    await expect(page.getByRole('button', { name: 'Enterprise' })).toHaveClass(
      /selection-card-selected/,
    );

    // Continue should work with the overridden values
    const continueBtn = page.getByRole('button', { name: 'Continue' });
    await expect(continueBtn).toBeEnabled();

    await continueBtn.click();
    await page.waitForTimeout(1200);

    // Verify we advanced to Step 2 (Role)
    await expect(page.getByRole('button', { name: 'Tech Executive' })).toBeVisible();
  });
});
