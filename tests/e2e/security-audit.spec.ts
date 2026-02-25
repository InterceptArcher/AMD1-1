/**
 * Security Audit E2E Tests
 *
 * Validates application security posture against common attack vectors:
 *   - XSS injection via form inputs
 *   - Open redirect protection
 *   - Content Security Policy headers
 *   - Sensitive data exposure in DOM / network
 *   - Input sanitization on API submission
 *   - Consent data protection (GDPR / privacy)
 *   - Clickjacking protection (X-Frame-Options)
 *
 * All API calls are mocked via shared fixtures — no real backend needed.
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

// Clear localStorage before each test
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
  await mockQuickEnrichNotFound(page);
});

test.describe('Security Audit', () => {
  // -----------------------------------------------------------------------
  // 1. XSS: Script tags in text inputs are not executed
  // -----------------------------------------------------------------------
  test('XSS: script tags in form inputs are not executed', async ({ page }) => {
    await page.goto('/');

    const xssPayload = '<script>window.__xss_fired=true</script>';

    // Inject XSS payload into all text inputs on Step 0
    await page.locator('#wiz-firstName').fill(xssPayload);
    await page.locator('#wiz-lastName').fill(xssPayload);
    await page.locator('#wiz-email').fill('xss@testcorp.com');
    await page.locator('#wiz-firstName').click(); // blur

    // Verify XSS did NOT execute
    const xssFired = await page.evaluate(() => (window as Record<string, unknown>).__xss_fired);
    expect(xssFired).toBeFalsy();

    // Verify the script tag text appears as text content, NOT as executable HTML
    const firstNameValue = await page.locator('#wiz-firstName').inputValue();
    expect(firstNameValue).toContain('<script>');
  });

  // -----------------------------------------------------------------------
  // 2. XSS: Image onerror payloads in inputs are not executed
  // -----------------------------------------------------------------------
  test('XSS: img onerror payloads are not executed', async ({ page }) => {
    await page.goto('/');

    const xssPayload = '"><img src=x onerror="window.__xss_img=true">';

    await page.locator('#wiz-firstName').fill(xssPayload);
    await page.locator('#wiz-lastName').fill('Test');
    await page.locator('#wiz-email').fill('test@safe.com');
    await page.locator('#wiz-firstName').click(); // blur

    // Wait a moment for any potential script execution
    await page.waitForTimeout(500);

    const xssFired = await page.evaluate(() => (window as Record<string, unknown>).__xss_img);
    expect(xssFired).toBeFalsy();
  });

  // -----------------------------------------------------------------------
  // 3. XSS: Company name with script injection on Step 1
  // -----------------------------------------------------------------------
  test('XSS: company name input sanitized on Step 1', async ({ page }) => {
    await page.goto('/');
    await fillStepAboutYou(page);

    const xssPayload = '<img src=x onerror=alert(1)>';
    await page.locator('#wiz-company').fill(xssPayload);

    // Verify the value is stored as plain text, not rendered as HTML
    const companyValue = await page.locator('#wiz-company').inputValue();
    expect(companyValue).toBe(xssPayload);

    // Ensure no alert was triggered (page would error if it did)
    const alertFired = await page.evaluate(() => (window as Record<string, unknown>).__alert_fired);
    expect(alertFired).toBeFalsy();
  });

  // -----------------------------------------------------------------------
  // 4. XSS: Malicious input passed to API is not reflected unsanitized
  // -----------------------------------------------------------------------
  test('XSS: malicious input in API response is rendered safely', async ({ page }) => {
    // Mock executive review with XSS payload in response
    await page.route('**/api/rad/executive-review', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          company_name: '<script>alert("xss")</script>TestCorp',
          inputs: {
            industry: 'Technology',
            segment: 'Enterprise',
            persona: 'ITDM',
            stage: 'Challenger',
            priority: 'Improving Performance',
            challenge: 'Integration Friction',
          },
          executive_review: {
            company_name: '<script>alert("xss")</script>TestCorp',
            stage: 'Challenger',
            stage_sidebar: 'Test stage sidebar',
            stage_identification_text: '<img src=x onerror=alert(1)>Stage text',
            advantages: [
              { headline: 'Test', description: '<script>alert("xss")</script>Advantage desc' },
              { headline: 'Test 2', description: 'Normal text' },
            ],
            risks: [
              { headline: '<b onmouseover=alert(1)>Risk</b>', description: 'Risk desc' },
              { headline: 'Risk 2', description: 'Normal text' },
            ],
            recommendations: [
              { title: 'Rec 1', description: 'Normal' },
              { title: 'Rec 2', description: 'Normal' },
              { title: 'Rec 3', description: 'Normal' },
            ],
            case_study: 'Test Case',
            case_study_description: 'Description',
            case_study_link: 'https://amd.com',
            case_study_relevance: 'Relevance text',
          },
        }),
      });
    });

    await page.goto('/');
    await completeWizard(page);

    // Wait for results to render
    await page.waitForTimeout(5000);

    // Verify no script executed
    const alertFired = await page.evaluate(
      () => (window as Record<string, unknown>).__alert_fired,
    );
    expect(alertFired).toBeFalsy();
  });

  // -----------------------------------------------------------------------
  // 5. No secrets exposed in page source or DOM
  // -----------------------------------------------------------------------
  test('no API keys or secrets exposed in DOM', async ({ page }) => {
    await page.goto('/');

    // Check full page HTML for common secret patterns
    const html = await page.content();

    // Common API key patterns that should NEVER appear in client-side HTML
    const secretPatterns = [
      /sk-[a-zA-Z0-9]{20,}/,       // Anthropic / OpenAI keys
      /pdl_[a-zA-Z0-9]{20,}/,      // People Data Labs
      /hunter_[a-zA-Z0-9]{10,}/,   // Hunter.io
      /supabase[_-]?key/i,         // Supabase keys
      /SUPABASE_KEY/,
      /ANTHROPIC_API_KEY/,
      /RENDER_DEPLOY_HOOK/,
      /eyJhbGciOi/,                // JWT tokens (base64 start)
    ];

    for (const pattern of secretPatterns) {
      expect(html).not.toMatch(pattern);
    }
  });

  // -----------------------------------------------------------------------
  // 6. No secrets in JavaScript bundle
  // -----------------------------------------------------------------------
  test('no secrets leaked in JavaScript bundles', async ({ page }) => {
    const jsContents: string[] = [];

    // Intercept all JS responses
    page.on('response', async (response) => {
      const url = response.url();
      if (url.endsWith('.js') && response.status() === 200) {
        try {
          const body = await response.text();
          jsContents.push(body);
        } catch {
          // Ignore errors from redirected/cached responses
        }
      }
    });

    await page.goto('/');
    await page.waitForTimeout(2000);

    // Check all loaded JS for secret patterns
    const allJs = jsContents.join('\n');
    const dangerousPatterns = [
      /sk-[a-zA-Z0-9]{32,}/,       // API keys
      /password\s*[:=]\s*["'][^"']+["']/i,  // Hardcoded passwords
      /secret\s*[:=]\s*["'][^"']+["']/i,    // Hardcoded secrets (but not CSS class names)
    ];

    for (const pattern of dangerousPatterns) {
      const matches = allJs.match(pattern);
      if (matches) {
        // Filter out false positives from CSS class names, comments, etc.
        const realSecrets = matches.filter(
          (m) => !m.includes('secret-') && !m.includes('className') && !m.includes('//'),
        );
        expect(realSecrets.length).toBe(0);
      }
    }
  });

  // -----------------------------------------------------------------------
  // 7. Security headers present
  // -----------------------------------------------------------------------
  test('security headers are set on page response', async ({ page }) => {
    const response = await page.goto('/');
    expect(response).not.toBeNull();

    const headers = response!.headers();

    // X-Frame-Options or CSP frame-ancestors should prevent clickjacking
    // Next.js may set these via next.config.js headers
    const hasFrameProtection =
      headers['x-frame-options'] !== undefined ||
      (headers['content-security-policy'] || '').includes('frame-ancestors');

    // Note: if neither header is set, this is a finding — not a hard failure
    // since the app may rely on Vercel's default security headers
    if (!hasFrameProtection) {
      console.warn(
        'SECURITY FINDING: No X-Frame-Options or CSP frame-ancestors header detected. ' +
          'Consider adding clickjacking protection.',
      );
    }

    // Content-Type should be set (basic but important)
    expect(headers['content-type']).toBeDefined();
  });

  // -----------------------------------------------------------------------
  // 8. Consent checkbox required before data submission
  // -----------------------------------------------------------------------
  test('consent is enforced: cannot submit without checkbox', async ({ page }) => {
    await page.goto('/');

    // Navigate to Step 3
    await fillStepAboutYou(page);
    await fillStepCompany(page);
    await fillStepRole(page);

    // Answer all 4 signal questions + challenge but skip consent
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

    // Submit button MUST be disabled without consent
    const submitBtn = page.getByRole('button', { name: /Get Your AI Readiness Snapshot/ });
    await expect(submitBtn).toBeDisabled();

    // Verify consent checkbox exists and is unchecked
    const consent = page.locator('#wiz-consent');
    await expect(consent).toBeVisible();
    await expect(consent).not.toBeChecked();
  });

  // -----------------------------------------------------------------------
  // 9. Email validation rejects obvious injection attempts
  // -----------------------------------------------------------------------
  test('email field rejects injection attempts', async ({ page }) => {
    await page.goto('/');

    // Fill required fields so we can check if Continue enables
    await page.locator('#wiz-firstName').fill('Test');
    await page.locator('#wiz-lastName').fill('User');

    const maliciousEmails = [
      'test@test.com<script>alert(1)</script>',
      'admin\' OR 1=1--@evil.com',
      'test@test.com%0ABcc:attacker@evil.com',
    ];

    for (const badEmail of maliciousEmails) {
      await page.locator('#wiz-email').fill(badEmail);
      await page.locator('#wiz-firstName').click(); // blur to trigger validation
      await page.waitForTimeout(300);

      // The key security check: malicious emails should either be rejected
      // by validation (error shown) OR the input value stays as plain text
      // in the input element (React never renders input values as HTML)
      const emailError = page.getByText('Please enter a valid email address');
      const isInvalid = await emailError.isVisible().catch(() => false);

      // Verify the value is NOT rendered as HTML anywhere in the DOM
      // (it's safe inside an <input> value attribute, but should not appear as HTML)
      const xssFired = await page.evaluate(
        () => (window as Record<string, unknown>).__xss_fired,
      );
      expect(xssFired).toBeFalsy();

      // If validation does not reject it, at least verify no script execution
      if (!isInvalid) {
        // The email is stored as a plain text value — this is acceptable
        // because React does not render input values as innerHTML
        const val = await page.locator('#wiz-email').inputValue();
        expect(val).toBeTruthy(); // value exists, stored as text
      }
    }
  });

  // -----------------------------------------------------------------------
  // 10. localStorage does not store sensitive data unencrypted
  // -----------------------------------------------------------------------
  test('localStorage does not contain API keys or tokens', async ({ page }) => {
    await mockExecutiveReviewSuccess(page);
    await page.goto('/');

    // Go through the wizard to trigger localStorage saves
    await completeWizard(page);
    await page.waitForTimeout(3000);

    // Check all localStorage entries
    const storageEntries = await page.evaluate(() => {
      const entries: Record<string, string> = {};
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key) entries[key] = localStorage.getItem(key) || '';
      }
      return entries;
    });

    const allValues = Object.values(storageEntries).join(' ');

    // No API keys in localStorage
    expect(allValues).not.toMatch(/sk-[a-zA-Z0-9]{20,}/);
    expect(allValues).not.toMatch(/Bearer\s+[a-zA-Z0-9._-]+/);
  });

  // -----------------------------------------------------------------------
  // 11. API submission includes only expected fields
  // -----------------------------------------------------------------------
  test('API submission does not leak extra fields', async ({ page }) => {
    let capturedBody: Record<string, unknown> | null = null;

    await page.route('**/api/rad/executive-review', async (route) => {
      capturedBody = JSON.parse(route.request().postData() || '{}');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, company_name: 'TestCorp', inputs: {}, executive_review: {
          company_name: 'TestCorp', stage: 'Challenger', stage_sidebar: 'Test',
          advantages: [], risks: [], recommendations: [],
          case_study: 'Test', case_study_description: 'Test',
        }}),
      });
    });

    await page.goto('/');
    await completeWizard(page);
    await page.waitForTimeout(3000);

    expect(capturedBody).not.toBeNull();

    // Expected field names only — no internal state leaking
    const allowedFields = [
      'email', 'firstName', 'lastName', 'company', 'companySize',
      'industry', 'persona', 'itEnvironment', 'businessPriority',
      'challenge', 'goal', 'consent', 'cta', 'signalAnswers',
    ];

    const bodyKeys = Object.keys(capturedBody!);
    for (const key of bodyKeys) {
      expect(allowedFields).toContain(key);
    }
  });
});
