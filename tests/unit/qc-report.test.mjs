/**
 * Unit tests for Archer QC Report Script
 * Tests the Playwright JSON parser, issue formatting, and quality gate logic.
 *
 * Run: node --test tests/unit/qc-report.test.mjs
 */

import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');
const FIXTURES_DIR = join(ROOT, 'tests', 'fixtures', 'qc-report');

// Dynamically import the module under test
const mod = await import(join(ROOT, 'scripts', 'archer-qc-report.mjs'));
const { parsePlaywrightJson, evaluateGate, formatIssueTitle, formatIssueBody, classifyFailure } = mod;

// ── Fixtures ──

const SAMPLE_JSON_MIXED = {
  config: { projects: [{ name: 'chromium' }] },
  suites: [
    {
      title: 'security-audit.spec.ts',
      file: 'tests/e2e/security-audit.spec.ts',
      suites: [
        {
          title: 'Security Audit',
          specs: [
            {
              title: 'XSS: script tags in form inputs are not executed',
              ok: false,
              tests: [
                {
                  status: 'unexpected',
                  expectedStatus: 'passed',
                  projectName: 'chromium',
                  results: [
                    {
                      status: 'failed',
                      duration: 4532,
                      error: {
                        message: 'Expected no alert but got one',
                        stack: 'Error: Expected no alert\n    at tests/e2e/security-audit.spec.ts:42:5',
                      },
                      retry: 0,
                    },
                    {
                      status: 'failed',
                      duration: 4210,
                      error: {
                        message: 'Expected no alert but got one',
                        stack: 'Error: Expected no alert\n    at tests/e2e/security-audit.spec.ts:42:5',
                      },
                      retry: 1,
                    },
                  ],
                },
              ],
            },
            {
              title: 'No secrets exposed in page source',
              ok: true,
              tests: [
                {
                  status: 'expected',
                  expectedStatus: 'passed',
                  projectName: 'chromium',
                  results: [
                    { status: 'passed', duration: 1234, retry: 0 },
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
  ],
};

const SAMPLE_JSON_ALL_PASS = {
  config: { projects: [{ name: 'chromium' }] },
  suites: [
    {
      title: 'wizard-flow.spec.ts',
      file: 'tests/e2e/wizard-flow.spec.ts',
      suites: [
        {
          title: 'Wizard Flow',
          specs: [
            {
              title: 'completes full wizard flow',
              ok: true,
              tests: [
                {
                  status: 'expected',
                  expectedStatus: 'passed',
                  projectName: 'chromium',
                  results: [{ status: 'passed', duration: 3000, retry: 0 }],
                },
              ],
            },
          ],
        },
      ],
    },
  ],
};

const SAMPLE_JSON_FLAKY = {
  config: { projects: [{ name: 'chromium' }] },
  suites: [
    {
      title: 'chaos-agent.spec.ts',
      file: 'tests/e2e/chaos-agent.spec.ts',
      suites: [
        {
          title: 'Chaos Agent',
          specs: [
            {
              title: 'handles slow API responses',
              ok: true,
              tests: [
                {
                  status: 'flaky',
                  expectedStatus: 'passed',
                  projectName: 'chromium',
                  results: [
                    {
                      status: 'failed',
                      duration: 12000,
                      error: { message: 'Timeout waiting for response', stack: '' },
                      retry: 0,
                    },
                    { status: 'passed', duration: 8000, retry: 1 },
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
  ],
};

const SAMPLE_JSON_SLOW = {
  config: { projects: [{ name: 'chromium' }] },
  suites: [
    {
      title: 'performance-agent.spec.ts',
      file: 'tests/e2e/performance-agent.spec.ts',
      suites: [
        {
          title: 'Performance Agent',
          specs: [
            {
              title: 'initial load completes within budget',
              ok: true,
              tests: [
                {
                  status: 'expected',
                  expectedStatus: 'passed',
                  projectName: 'chromium',
                  results: [{ status: 'passed', duration: 38000, retry: 0 }],
                },
              ],
            },
          ],
        },
      ],
    },
  ],
};

// ── Setup / Teardown ──

before(() => {
  mkdirSync(FIXTURES_DIR, { recursive: true });
});

after(() => {
  rmSync(FIXTURES_DIR, { recursive: true, force: true });
});

// ── JSON Parser Tests ──

describe('QC Report — JSON Parser', () => {
  it('extracts failures from nested suites', () => {
    const fixturePath = join(FIXTURES_DIR, 'mixed.json');
    writeFileSync(fixturePath, JSON.stringify(SAMPLE_JSON_MIXED));

    const result = parsePlaywrightJson(fixturePath);
    assert.equal(result.passed, 1);
    assert.equal(result.failed, 1);
    assert.equal(result.failures.length, 1);
    assert.equal(result.failures[0].title, 'XSS: script tags in form inputs are not executed');
    assert.equal(result.failures[0].file, 'tests/e2e/security-audit.spec.ts');
    assert.ok(result.failures[0].error.includes('Expected no alert'));
  });

  it('reports zero failures for all-passing suite', () => {
    const fixturePath = join(FIXTURES_DIR, 'allpass.json');
    writeFileSync(fixturePath, JSON.stringify(SAMPLE_JSON_ALL_PASS));

    const result = parsePlaywrightJson(fixturePath);
    assert.equal(result.passed, 1);
    assert.equal(result.failed, 0);
    assert.equal(result.failures.length, 0);
  });

  it('detects flaky tests (failed then passed on retry)', () => {
    const fixturePath = join(FIXTURES_DIR, 'flaky.json');
    writeFileSync(fixturePath, JSON.stringify(SAMPLE_JSON_FLAKY));

    const result = parsePlaywrightJson(fixturePath);
    assert.equal(result.flaky, 1);
    assert.equal(result.failed, 0);
    assert.equal(result.flakyTests.length, 1);
    assert.equal(result.flakyTests[0].title, 'handles slow API responses');
  });

  it('detects slow tests (>30s)', () => {
    const fixturePath = join(FIXTURES_DIR, 'slow.json');
    writeFileSync(fixturePath, JSON.stringify(SAMPLE_JSON_SLOW));

    const result = parsePlaywrightJson(fixturePath);
    assert.equal(result.slowTests.length, 1);
    assert.equal(result.slowTests[0].title, 'initial load completes within budget');
    assert.equal(result.slowTests[0].duration, 38000);
  });

  it('captures stack trace from final retry', () => {
    const fixturePath = join(FIXTURES_DIR, 'mixed.json');
    writeFileSync(fixturePath, JSON.stringify(SAMPLE_JSON_MIXED));

    const result = parsePlaywrightJson(fixturePath);
    assert.ok(result.failures[0].stack.includes('security-audit.spec.ts:42'));
  });
});

// ── Quality Gate Tests ──

describe('QC Report — Quality Gate', () => {
  it('fails when critical agent has failures', () => {
    const result = evaluateGate([
      { agent: 'security', severity: 'critical', failed: 2, infraFailure: false },
      { agent: 'wizard', severity: 'critical', failed: 0, infraFailure: false },
      { agent: 'chaos', severity: 'advisory', failed: 3, infraFailure: false },
    ]);
    assert.equal(result, false);
  });

  it('passes when only advisory agents fail', () => {
    const result = evaluateGate([
      { agent: 'security', severity: 'critical', failed: 0, infraFailure: false },
      { agent: 'wizard', severity: 'critical', failed: 0, infraFailure: false },
      { agent: 'exec-review', severity: 'critical', failed: 0, infraFailure: false },
      { agent: 'chaos', severity: 'advisory', failed: 5, infraFailure: false },
      { agent: 'a11y', severity: 'advisory', failed: 2, infraFailure: false },
      { agent: 'perf', severity: 'advisory', failed: 1, infraFailure: false },
    ]);
    assert.equal(result, true);
  });

  it('fails when critical agent has infrastructure failure', () => {
    const result = evaluateGate([
      { agent: 'security', severity: 'critical', failed: 0, infraFailure: true },
      { agent: 'wizard', severity: 'critical', failed: 0, infraFailure: false },
    ]);
    assert.equal(result, false);
  });

  it('passes when advisory agent has infrastructure failure', () => {
    const result = evaluateGate([
      { agent: 'security', severity: 'critical', failed: 0, infraFailure: false },
      { agent: 'wizard', severity: 'critical', failed: 0, infraFailure: false },
      { agent: 'exec-review', severity: 'critical', failed: 0, infraFailure: false },
      { agent: 'perf', severity: 'advisory', failed: 0, infraFailure: true },
    ]);
    assert.equal(result, true);
  });

  it('passes when all agents pass with zero failures', () => {
    const result = evaluateGate([
      { agent: 'security', severity: 'critical', failed: 0, infraFailure: false },
      { agent: 'wizard', severity: 'critical', failed: 0, infraFailure: false },
      { agent: 'exec-review', severity: 'critical', failed: 0, infraFailure: false },
      { agent: 'chaos', severity: 'advisory', failed: 0, infraFailure: false },
      { agent: 'a11y', severity: 'advisory', failed: 0, infraFailure: false },
      { agent: 'perf', severity: 'advisory', failed: 0, infraFailure: false },
    ]);
    assert.equal(result, true);
  });
});

// ── Issue Title Format Tests ──

describe('QC Report — Issue Title', () => {
  it('produces correct de-dup key', () => {
    const title = formatIssueTitle('Security', 'XSS: script tags in form inputs are not executed');
    assert.equal(title, 'QC: Security — XSS: script tags in form inputs are not executed');
  });

  it('handles special characters in test name', () => {
    const title = formatIssueTitle('Chaos', 'handles "quoted" & <angled> input');
    assert.equal(title, 'QC: Chaos — handles "quoted" & <angled> input');
  });
});

// ── Issue Body Format Tests ──

describe('QC Report — Issue Body', () => {
  it('contains all required sections for critical failure', () => {
    const body = formatIssueBody({
      agentName: 'Security',
      severity: 'critical',
      testTitle: 'XSS: script tags',
      file: 'tests/e2e/security-audit.spec.ts',
      duration: 4532,
      error: 'Expected no alert but got one',
      stack: 'Error: Expected no alert at line 42',
      runUrl: 'https://github.com/test/runs/1',
      runNumber: 42,
    });

    assert.ok(body.includes('BLOCKER'), 'should include BLOCKER badge');
    assert.ok(body.includes('Reproduce'), 'should include reproduce section');
    assert.ok(body.includes('npx playwright test'), 'should include reproduce command');
    assert.ok(body.includes('Common causes'), 'should include common causes');
    assert.ok(body.includes('Files to check'), 'should include files to check');
    assert.ok(body.includes('<details>'), 'should include collapsible stack trace');
    assert.ok(body.includes('4.53s'), 'should include formatted duration');
  });

  it('shows ADVISORY badge for advisory severity', () => {
    const body = formatIssueBody({
      agentName: 'Chaos',
      severity: 'advisory',
      testTitle: 'handles slow API',
      file: 'tests/e2e/chaos-agent.spec.ts',
      duration: 12000,
      error: 'Timeout',
      stack: '',
      runUrl: 'https://github.com/test/runs/1',
      runNumber: 42,
    });

    assert.ok(body.includes('ADVISORY'), 'should include ADVISORY badge');
    assert.ok(!body.includes('BLOCKER'), 'should not include BLOCKER badge');
  });
});

// ── Failure Classification Tests ──

describe('QC Report — Failure Classification', () => {
  // Timeout patterns (checked FIRST)
  it('classifies "Timeout 30000ms exceeded" as timeout', () => {
    assert.equal(classifyFailure('expect(locator).toBeVisible(): Timeout 30000ms exceeded'), 'timeout');
  });

  it('classifies "Timeout 45000ms exceeded" as timeout', () => {
    assert.equal(classifyFailure('Timeout 45000ms exceeded waiting for element'), 'timeout');
  });

  it('classifies "waiting for locator" as timeout', () => {
    assert.equal(classifyFailure('waiting for locator(".wizard-step")'), 'timeout');
  });

  it('classifies "waiting for selector" as timeout', () => {
    assert.equal(classifyFailure('waiting for selector "#submit-btn"'), 'timeout');
  });

  it('classifies "Navigation timeout" as timeout', () => {
    assert.equal(classifyFailure('Navigation timeout of 30000ms exceeded'), 'timeout');
  });

  it('classifies "Test timeout of 45000ms exceeded" as timeout', () => {
    assert.equal(classifyFailure('Test timeout of 45000ms exceeded'), 'timeout');
  });

  // Timeout takes priority over assertion keywords
  it('classifies timeout with expect() in message as timeout (not assertion)', () => {
    const msg = 'expect(locator).toBeVisible(): Timeout 30000ms exceeded\nCall log: waiting for locator';
    assert.equal(classifyFailure(msg), 'timeout');
  });

  // Assertion patterns (checked second)
  it('classifies "expect(received)" as assertion', () => {
    assert.equal(classifyFailure('expect(received).toBe(expected)\n\nExpected: 5\nReceived: 3'), 'assertion');
  });

  it('classifies "Expected...Received" multiline as assertion', () => {
    assert.equal(classifyFailure('Error:\nExpected value to be truthy\nReceived: false'), 'assertion');
  });

  it('classifies "AssertionError" as assertion', () => {
    assert.equal(classifyFailure('AssertionError: expected true to be false'), 'assertion');
  });

  it('classifies pure expect failure as assertion', () => {
    assert.equal(classifyFailure('expect(received).toEqual(expected)\n\nExpected: "hello"\nReceived: "world"'), 'assertion');
  });

  // Unknown
  it('classifies empty string as unknown', () => {
    assert.equal(classifyFailure(''), 'unknown');
  });

  it('classifies unrecognized error as unknown', () => {
    assert.equal(classifyFailure('Something went terribly wrong'), 'unknown');
  });

  it('classifies null/undefined gracefully as unknown', () => {
    assert.equal(classifyFailure(null), 'unknown');
    assert.equal(classifyFailure(undefined), 'unknown');
  });
});

// ── Updated Quality Gate with Classification ──

describe('QC Report — Quality Gate with Classification', () => {
  it('passes when critical agent has only timeout failures', () => {
    const result = evaluateGate([
      { agent: 'wizard', severity: 'critical', failed: 2, infraFailure: false, timeoutFailures: 2, assertionFailures: 0, unknownFailures: 0 },
      { agent: 'security', severity: 'critical', failed: 0, infraFailure: false },
    ]);
    assert.equal(result, true);
  });

  it('blocks when critical agent has assertion failures', () => {
    const result = evaluateGate([
      { agent: 'wizard', severity: 'critical', failed: 3, infraFailure: false, timeoutFailures: 1, assertionFailures: 2, unknownFailures: 0 },
    ]);
    assert.equal(result, false);
  });

  it('blocks when critical agent has unknown failures', () => {
    const result = evaluateGate([
      { agent: 'security', severity: 'critical', failed: 1, infraFailure: false, timeoutFailures: 0, assertionFailures: 0, unknownFailures: 1 },
    ]);
    assert.equal(result, false);
  });

  it('falls back to old behavior when classification fields absent', () => {
    // No timeoutFailures/assertionFailures/unknownFailures → uses failed count directly
    const result = evaluateGate([
      { agent: 'wizard', severity: 'critical', failed: 1, infraFailure: false },
    ]);
    assert.equal(result, false);
  });

  it('passes when critical agent has mixed timeout + flaky but zero assertion/unknown', () => {
    const result = evaluateGate([
      { agent: 'wizard', severity: 'critical', failed: 3, infraFailure: false, timeoutFailures: 3, assertionFailures: 0, unknownFailures: 0 },
      { agent: 'exec-review', severity: 'critical', failed: 0, infraFailure: false },
      { agent: 'security', severity: 'critical', failed: 0, infraFailure: false },
    ]);
    assert.equal(result, true);
  });
});
