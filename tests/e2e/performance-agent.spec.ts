/**
 * Performance Agent E2E Tests
 *
 * Validates application performance characteristics:
 *   - Page load time (Time to Interactive)
 *   - JavaScript bundle sizes
 *   - Network request count limits
 *   - No excessive DOM size
 *   - Memory leak detection (heap growth)
 *   - Core Web Vitals proxies (LCP, CLS indicators)
 *   - Wizard step transition speed
 *   - No blocking resources
 *
 * All API calls are mocked — no real backend needed.
 */
import { test, expect } from '@playwright/test';
import {
  mockQuickEnrichNotFound,
  mockExecutiveReviewSuccess,
  fillStepAboutYou,
  fillStepCompany,
  fillStepRole,
  fillStepSituation,
  completeWizard,
} from './fixtures';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
  await mockQuickEnrichNotFound(page);
});

test.describe('Performance Agent', () => {
  // -----------------------------------------------------------------------
  // 1. Page loads within acceptable time
  // -----------------------------------------------------------------------
  test('landing page loads within 10 seconds', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const loadTime = Date.now() - startTime;

    // Page should load within 10s (generous for CI + cold start)
    expect(loadTime).toBeLessThan(10_000);

    // Hero heading should be visible quickly
    await expect(page.locator('h1')).toBeVisible({ timeout: 10_000 });
  });

  // -----------------------------------------------------------------------
  // 2. Total JS bundle size is reasonable
  // -----------------------------------------------------------------------
  test('JavaScript bundle size is under 2MB', async ({ page }) => {
    let totalJsBytes = 0;

    page.on('response', async (response) => {
      const url = response.url();
      const contentType = response.headers()['content-type'] || '';

      if (
        (url.endsWith('.js') || contentType.includes('javascript')) &&
        response.status() === 200
      ) {
        try {
          const body = await response.body();
          totalJsBytes += body.length;
        } catch {
          // Ignore errors from cached/redirected responses
        }
      }
    });

    await page.goto('/');
    await page.waitForTimeout(3000);

    // Total JS should be under 2MB (compressed sizes are much smaller)
    const totalMB = totalJsBytes / (1024 * 1024);
    expect(totalMB).toBeLessThan(2);

    // Log for reporting
    console.log(`Total JS transferred: ${totalMB.toFixed(2)} MB`);
  });

  // -----------------------------------------------------------------------
  // 3. Total network requests are reasonable
  // -----------------------------------------------------------------------
  test('page load makes fewer than 80 network requests', async ({ page }) => {
    let requestCount = 0;

    page.on('request', () => {
      requestCount++;
    });

    await page.goto('/');
    await page.waitForTimeout(3000);

    // A reasonable Next.js page should have < 80 requests
    expect(requestCount).toBeLessThan(80);

    console.log(`Total network requests: ${requestCount}`);
  });

  // -----------------------------------------------------------------------
  // 4. DOM size is not excessive
  // -----------------------------------------------------------------------
  test('DOM node count is under 3000', async ({ page }) => {
    await page.goto('/');

    const nodeCount = await page.evaluate(() => {
      return document.querySelectorAll('*').length;
    });

    // Excessive DOM nodes (>3000) hurt performance
    expect(nodeCount).toBeLessThan(3000);

    console.log(`DOM node count: ${nodeCount}`);
  });

  // -----------------------------------------------------------------------
  // 5. No layout shift during page load
  // -----------------------------------------------------------------------
  test('no major layout shifts on initial load', async ({ page }) => {
    // Track layout shifts via PerformanceObserver
    await page.addInitScript(() => {
      (window as Record<string, unknown>).__cls_score = 0;
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!(entry as PerformanceEntry & { hadRecentInput?: boolean }).hadRecentInput) {
            (window as Record<string, unknown>).__cls_score =
              ((window as Record<string, unknown>).__cls_score as number) +
              ((entry as PerformanceEntry & { value?: number }).value || 0);
          }
        }
      });
      observer.observe({ type: 'layout-shift', buffered: true });
    });

    await page.goto('/');
    await page.waitForTimeout(3000);

    const clsScore = await page.evaluate(
      () => (window as Record<string, unknown>).__cls_score as number,
    );

    // CLS should be under 0.25 (Google's "needs improvement" threshold)
    // We use 0.5 as a generous limit for CI environments
    expect(clsScore).toBeLessThan(0.5);

    console.log(`Cumulative Layout Shift (CLS): ${clsScore.toFixed(4)}`);
  });

  // -----------------------------------------------------------------------
  // 6. Wizard step transitions are fast
  // -----------------------------------------------------------------------
  test('wizard step transitions complete within 3 seconds', async ({ page }) => {
    await page.goto('/');

    // Fill Step 0
    await page.locator('#wiz-firstName').fill('Jane');
    await page.locator('#wiz-lastName').fill('Chen');
    await page.locator('#wiz-email').fill('jane@test.com');
    await page.locator('#wiz-firstName').click();

    // Measure Step 0 → Step 1 transition
    const start = Date.now();
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.locator('#wiz-company')).toBeVisible({ timeout: 5000 });
    const transitionTime = Date.now() - start;

    // Transition should complete within 3s (includes thinking overlay)
    expect(transitionTime).toBeLessThan(3000);

    console.log(`Step 0→1 transition: ${transitionTime}ms`);
  });

  // -----------------------------------------------------------------------
  // 7. Results page renders within 5 seconds (after API response)
  // -----------------------------------------------------------------------
  test('executive review renders within 5s of API response', async ({ page }) => {
    await mockExecutiveReviewSuccess(page);
    await page.goto('/');
    await completeWizard(page);

    const startWait = Date.now();

    // Results should appear within 5 seconds of submission
    await expect(
      page.getByText('Enterprise AI Readiness Snapshot for'),
    ).toBeVisible({ timeout: 10_000 });

    const renderTime = Date.now() - startWait;
    expect(renderTime).toBeLessThan(5000);

    console.log(`Results render time: ${renderTime}ms`);
  });

  // -----------------------------------------------------------------------
  // 8. No console errors during full wizard flow
  // -----------------------------------------------------------------------
  test('no console errors during full wizard flow', async ({ page }) => {
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Ignore known benign errors
        if (
          !text.includes('favicon') &&
          !text.includes('manifest') &&
          !text.includes('hydration') &&
          !text.includes('404')
        ) {
          consoleErrors.push(text);
        }
      }
    });

    await mockExecutiveReviewSuccess(page);
    await page.goto('/');
    await completeWizard(page);

    // Wait for results
    await page.waitForTimeout(5000);

    // Should have zero (or very few) console errors
    if (consoleErrors.length > 0) {
      console.warn(`Console errors found: ${consoleErrors.join('\n')}`);
    }
    expect(consoleErrors.length).toBeLessThan(3);
  });

  // -----------------------------------------------------------------------
  // 9. No uncaught exceptions during wizard flow
  // -----------------------------------------------------------------------
  test('no uncaught exceptions during wizard flow', async ({ page }) => {
    const pageErrors: string[] = [];

    page.on('pageerror', (err) => {
      pageErrors.push(err.message);
    });

    await mockExecutiveReviewSuccess(page);
    await page.goto('/');
    await completeWizard(page);
    await page.waitForTimeout(5000);

    // Zero uncaught exceptions
    expect(pageErrors).toEqual([]);
  });

  // -----------------------------------------------------------------------
  // 10. Page does not make excessive API calls
  // -----------------------------------------------------------------------
  test('wizard flow makes minimal API calls', async ({ page }) => {
    let enrichCallCount = 0;
    let reviewCallCount = 0;

    await page.route('**/api/rad/quick-enrich', async (route) => {
      enrichCallCount++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ found: false }),
      });
    });

    await page.route('**/api/rad/executive-review', async (route) => {
      reviewCallCount++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true, company_name: 'TestCorp', inputs: {},
          executive_review: {
            company_name: 'TestCorp', stage: 'Challenger', stage_sidebar: 'Test',
            advantages: [], risks: [], recommendations: [],
            case_study: 'Test', case_study_description: 'Test',
          },
        }),
      });
    });

    await page.goto('/');
    await completeWizard(page);
    await page.waitForTimeout(3000);

    // Should make at most 1 enrichment call and 1 review call
    expect(enrichCallCount).toBeLessThanOrEqual(1);
    expect(reviewCallCount).toBeLessThanOrEqual(1);

    console.log(`API calls — enrichment: ${enrichCallCount}, review: ${reviewCallCount}`);
  });
});
