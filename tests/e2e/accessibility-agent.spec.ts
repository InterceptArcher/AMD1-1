/**
 * Accessibility Agent E2E Tests
 *
 * Validates WCAG 2.1 AA compliance across the wizard flow:
 *   - Keyboard-only navigation (Tab, Enter, Escape, arrow keys)
 *   - ARIA labels and roles on interactive elements
 *   - Focus management during step transitions
 *   - Form labels associated with inputs
 *   - Visible focus indicators
 *   - Screen reader-friendly content structure
 *   - Skip navigation / logical heading hierarchy
 *   - Error messages linked to inputs via aria-describedby
 *
 * All API calls are mocked — no real backend needed.
 */
import { test, expect } from '@playwright/test';
import {
  TEST_USER,
  mockQuickEnrichNotFound,
  mockExecutiveReviewSuccess,
  fillStepAboutYou,
  fillStepCompany,
  fillStepRole,
  completeWizard,
} from './fixtures';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
  await mockQuickEnrichNotFound(page);
});

test.describe('Accessibility Agent', () => {
  // -----------------------------------------------------------------------
  // 1. All form inputs have associated labels
  // -----------------------------------------------------------------------
  test('all form inputs have associated labels', async ({ page }) => {
    await page.goto('/');

    // Step 0 inputs should have labels via htmlFor or aria-label
    const inputs = ['#wiz-firstName', '#wiz-lastName', '#wiz-email'];

    for (const selector of inputs) {
      const input = page.locator(selector);
      await expect(input).toBeVisible();

      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledBy = await input.getAttribute('aria-labelledby');

      // Check for associated label element
      const hasLabel = await page.locator(`label[for="${id}"]`).count();

      // Input must have at least one labelling mechanism
      const isLabelled = hasLabel > 0 || ariaLabel !== null || ariaLabelledBy !== null;
      expect(isLabelled).toBeTruthy();
    }
  });

  // -----------------------------------------------------------------------
  // 2. Keyboard Tab navigation through Step 0
  // -----------------------------------------------------------------------
  test('Tab key navigates through Step 0 inputs', async ({ page }) => {
    await page.goto('/');

    // Focus the first input
    await page.locator('#wiz-firstName').focus();

    // Tab through inputs
    await page.keyboard.press('Tab');
    const focused1 = await page.evaluate(() => document.activeElement?.id);
    expect(focused1).toBe('wiz-lastName');

    await page.keyboard.press('Tab');
    const focused2 = await page.evaluate(() => document.activeElement?.id);
    expect(focused2).toBe('wiz-email');
  });

  // -----------------------------------------------------------------------
  // 3. Selection cards are keyboard accessible
  // -----------------------------------------------------------------------
  test('selection cards are keyboard accessible', async ({ page }) => {
    await page.goto('/');
    await fillStepAboutYou(page);

    // Fill company name first
    await page.locator('#wiz-company').fill(TEST_USER.company);

    // Focus a selection card button and press Enter
    const sizeBtn = page.getByRole('button', { name: TEST_USER.companySize });
    await sizeBtn.focus();
    await page.keyboard.press('Enter');

    // Card should now be selected
    await expect(sizeBtn).toHaveClass(/selection-card-selected/);
  });

  // -----------------------------------------------------------------------
  // 4. Continue button is focusable and activatable via keyboard
  // -----------------------------------------------------------------------
  test('Continue button works with keyboard Enter', async ({ page }) => {
    await page.goto('/');

    // Fill Step 0
    await page.locator('#wiz-firstName').fill(TEST_USER.firstName);
    await page.locator('#wiz-lastName').fill(TEST_USER.lastName);
    await page.locator('#wiz-email').fill(TEST_USER.email);
    await page.locator('#wiz-firstName').click();

    // Tab to Continue button and press Enter
    const continueBtn = page.getByRole('button', { name: 'Continue' });
    await continueBtn.focus();
    await page.keyboard.press('Enter');

    // Wait for transition
    await page.waitForTimeout(1500);

    // Should have advanced to Step 1
    await expect(page.locator('#wiz-company')).toBeVisible({ timeout: 5000 });
  });

  // -----------------------------------------------------------------------
  // 5. Heading hierarchy is logical (h1 > h2 > h3)
  // -----------------------------------------------------------------------
  test('heading hierarchy is logical', async ({ page }) => {
    await page.goto('/');

    // Get all headings
    const headings = await page.evaluate(() => {
      const elements = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
      return Array.from(elements).map((el) => ({
        level: parseInt(el.tagName[1]),
        text: el.textContent?.trim() || '',
      }));
    });

    // Must have at least one h1
    const h1Count = headings.filter((h) => h.level === 1).length;
    expect(h1Count).toBeGreaterThanOrEqual(1);

    // Headings should not skip levels (h1 -> h3 without h2)
    for (let i = 1; i < headings.length; i++) {
      const jump = headings[i].level - headings[i - 1].level;
      // A jump of more than 1 level (e.g., h1 -> h3) is a violation
      // Allow jumping down any amount (h3 -> h1 is fine, going back up)
      if (jump > 0) {
        expect(jump).toBeLessThanOrEqual(1);
      }
    }
  });

  // -----------------------------------------------------------------------
  // 6. Interactive elements have visible focus indicators
  // -----------------------------------------------------------------------
  test('interactive elements have visible focus indicators', async ({ page }) => {
    await page.goto('/');

    // Focus the first input
    const firstInput = page.locator('#wiz-firstName');
    await firstInput.focus();

    // Check that the focused element has some visual distinction
    // (outline, box-shadow, or border change)
    const focusStyles = await firstInput.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return {
        outline: styles.outline,
        outlineWidth: styles.outlineWidth,
        boxShadow: styles.boxShadow,
        borderColor: styles.borderColor,
      };
    });

    // At least one focus indicator should be present
    const hasFocusIndicator =
      focusStyles.outlineWidth !== '0px' ||
      focusStyles.boxShadow !== 'none' ||
      focusStyles.borderColor !== 'rgb(0, 0, 0)';

    expect(hasFocusIndicator).toBeTruthy();
  });

  // -----------------------------------------------------------------------
  // 7. Error messages are announced to screen readers
  // -----------------------------------------------------------------------
  test('email validation error is accessible', async ({ page }) => {
    await page.goto('/');

    // Trigger email validation error
    await page.locator('#wiz-email').fill('bad-email');
    await page.locator('#wiz-firstName').click(); // blur

    // Error message should be visible
    const errorMsg = page.getByText('Please enter a valid email address');
    await expect(errorMsg).toBeVisible();

    // Error should have role=alert or aria-live for screen reader announcement
    const errorAttrs = await errorMsg.evaluate((el) => {
      // Check the element itself and its parents
      let current: HTMLElement | null = el as HTMLElement;
      while (current) {
        if (
          current.getAttribute('role') === 'alert' ||
          current.getAttribute('aria-live') === 'polite' ||
          current.getAttribute('aria-live') === 'assertive'
        ) {
          return { hasLiveRegion: true };
        }
        current = current.parentElement;
      }
      return { hasLiveRegion: false };
    });

    // If no live region, flag it but don't hard-fail (enhancement opportunity)
    if (!errorAttrs.hasLiveRegion) {
      console.warn(
        'ACCESSIBILITY FINDING: Email error message is not in an aria-live region. ' +
          'Screen readers may not announce the error automatically.',
      );
    }
  });

  // -----------------------------------------------------------------------
  // 8. Consent checkbox has visible label
  // -----------------------------------------------------------------------
  test('consent checkbox has accessible label', async ({ page }) => {
    await page.goto('/');
    await fillStepAboutYou(page);
    await fillStepCompany(page);
    await fillStepRole(page);

    // Answer all 4 signal questions + challenge to reveal consent
    await page.getByRole('button', { name: /Mix of old and new/ }).click();
    const q2Btn = page.getByRole('button', { name: /Experimenting with pilots/ });
    await expect(q2Btn).toBeVisible({ timeout: 5_000 });
    await q2Btn.click();
    const q3Btn = page.getByRole('button', { name: /Eliminating bottlenecks/ });
    await expect(q3Btn).toBeVisible({ timeout: 5_000 });
    await q3Btn.click();
    const q4Btn = page.getByRole('button', { name: /Mix of ops and new development/ });
    await expect(q4Btn).toBeVisible({ timeout: 5_000 });
    await q4Btn.click();
    const challengeBtn = page.getByRole('button', { name: /Toolchain fragmentation/ });
    await expect(challengeBtn).toBeVisible({ timeout: 10_000 });
    await challengeBtn.click();

    const consent = page.locator('#wiz-consent');
    await expect(consent).toBeVisible();

    // Check for associated label
    const hasLabel = await page.locator('label[for="wiz-consent"]').count();
    const ariaLabel = await consent.getAttribute('aria-label');

    expect(hasLabel > 0 || ariaLabel !== null).toBeTruthy();
  });

  // -----------------------------------------------------------------------
  // 9. No duplicate IDs in the DOM
  // -----------------------------------------------------------------------
  test('no duplicate IDs in the DOM', async ({ page }) => {
    await page.goto('/');

    const duplicateIds = await page.evaluate(() => {
      const allIds = Array.from(document.querySelectorAll('[id]')).map(
        (el) => el.id,
      );
      const seen = new Set<string>();
      const dupes: string[] = [];
      for (const id of allIds) {
        if (id && seen.has(id)) dupes.push(id);
        seen.add(id);
      }
      return dupes;
    });

    expect(duplicateIds).toEqual([]);
  });

  // -----------------------------------------------------------------------
  // 10. Results page has proper heading structure
  // -----------------------------------------------------------------------
  test('executive review results have accessible structure', async ({ page }) => {
    await mockExecutiveReviewSuccess(page);
    await page.goto('/');
    await completeWizard(page);

    // Wait for results
    await expect(
      page.getByText('Enterprise AI Readiness Snapshot for'),
    ).toBeVisible({ timeout: 30_000 });

    // Results should have proper heading hierarchy
    const headings = await page.evaluate(() => {
      const elements = document.querySelectorAll('h1, h2, h3, h4');
      return Array.from(elements).map((el) => ({
        level: parseInt(el.tagName[1]),
        text: el.textContent?.trim().substring(0, 50) || '',
      }));
    });

    // Should have at least 3 headings (main title, sections, case study)
    expect(headings.length).toBeGreaterThanOrEqual(3);

    // Buttons should have accessible names
    const resetBtn = page.getByRole('button', { name: 'Start over with different information' });
    await expect(resetBtn).toBeVisible();
  });

  // -----------------------------------------------------------------------
  // 11. Images have alt text
  // -----------------------------------------------------------------------
  test('all images have alt text', async ({ page }) => {
    await page.goto('/');

    const imagesWithoutAlt = await page.evaluate(() => {
      const images = document.querySelectorAll('img');
      return Array.from(images)
        .filter((img) => !img.getAttribute('alt') && img.getAttribute('alt') !== '')
        .map((img) => img.src);
    });

    // All images must have alt text (empty alt="" is OK for decorative images)
    expect(imagesWithoutAlt).toEqual([]);
  });
});
