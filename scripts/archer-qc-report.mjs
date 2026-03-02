#!/usr/bin/env node

/**
 * Archer QC Report — Transforms Playwright JSON results into GitHub Issues.
 *
 * Reads test-results-*.json from qc-results/, creates/updates/closes issues
 * per failing test, and generates a summary dashboard.
 *
 * Usage: node scripts/archer-qc-report.mjs
 *
 * Environment:
 *   GITHUB_OUTPUT   — path for setting outputs (set by GitHub Actions)
 *   GITHUB_REPOSITORY — owner/repo (set by GitHub Actions)
 *   GITHUB_RUN_ID   — run ID for linking (set by GitHub Actions)
 *   GITHUB_RUN_NUMBER — run number for display
 *   QC_RESULTS_DIR  — override results directory (default: qc-results)
 *
 * Exports (for testing):
 *   parsePlaywrightJson, evaluateGate, formatIssueTitle, formatIssueBody, classifyFailure
 */

import { readFileSync, writeFileSync, readdirSync, existsSync, appendFileSync } from 'node:fs';
import { join, basename } from 'node:path';
import { execSync } from 'node:child_process';
import { correlateWithGit, detectPatterns, analyzeWithLLM, formatAnalystNotes } from './archer-qc-analyst.mjs';

// ─────────────────────────────────────────────────
// Agent metadata registry
// ─────────────────────────────────────────────────

const AGENTS = {
  wizard: {
    name: 'Wizard + Enrichment',
    severity: 'critical',
    label: 'agent:wizard',
    description: 'Tests wizard form flow, validation, enrichment pre-fill, step navigation, and session reset.',
    commonCauses: [
      'Form selector changed (data-testid or role query no longer matches)',
      'Backend /rad/quick-enrich endpoint down or returning different shape',
      'Step transition timing — animation not waited for before assertion',
      'Enrichment banner component not rendering pre-filled fields',
      'localStorage persistence broken (TTL expired or key renamed)',
    ],
    filesToCheck: [
      'frontend/src/components/EmailConsentForm.tsx',
      'frontend/src/components/wizard/',
      'backend/app/routes/enrichment.py',
    ],
  },
  'exec-review': {
    name: 'Executive Review',
    severity: 'critical',
    label: 'agent:exec-review',
    description: 'Tests executive review API integration, response rendering, stage styling, input pills, and error handling.',
    commonCauses: [
      'Backend /rad/executive-review endpoint changed response shape',
      'LLM service returning mock fallback (check _source field)',
      'ExecutiveReviewDisplay component prop changes',
      'Stage badge CSS classes renamed',
      'API timeout — Render cold start exceeds Playwright timeout',
    ],
    filesToCheck: [
      'frontend/src/components/ExecutiveReviewDisplay.tsx',
      'backend/app/services/executive_review_service.py',
      'backend/app/routes/enrichment.py',
    ],
  },
  security: {
    name: 'Security',
    severity: 'critical',
    label: 'agent:security',
    description: 'Tests XSS injection, secrets in DOM/JS, security headers, consent gating, email injection, localStorage safety, and API field whitelisting.',
    commonCauses: [
      'New form field added without sanitization',
      'dangerouslySetInnerHTML introduced in a component',
      'Environment variable leaked into client bundle (check NEXT_PUBLIC_ prefix)',
      'API response includes fields not in the whitelist',
      'Content-Security-Policy header missing or misconfigured on Vercel',
    ],
    filesToCheck: [
      'frontend/src/components/EmailConsentForm.tsx',
      'frontend/next.config.js',
      'backend/app/routes/enrichment.py',
      'vercel.json',
    ],
  },
  chaos: {
    name: 'Chaos',
    severity: 'advisory',
    label: 'agent:chaos',
    description: 'Tests resilience against slow APIs, timeouts, malformed JSON, empty responses, HTML errors, navigation abuse, rapid input, and race conditions.',
    commonCauses: [
      'Error boundary removed or not wrapping the right component',
      'Missing try/catch around fetch — unhandled rejection crashes page',
      'Timeout value too tight for degraded network simulation',
      'Race condition in concurrent state updates (React batching issue)',
      'Back/forward navigation triggers double-mount without cleanup',
    ],
    filesToCheck: [
      'frontend/src/components/EmailConsentForm.tsx',
      'frontend/src/app/page.tsx',
      'frontend/src/components/ExecutiveReviewDisplay.tsx',
    ],
  },
  a11y: {
    name: 'Accessibility',
    severity: 'advisory',
    label: 'agent:a11y',
    description: 'Tests WCAG 2.1 AA compliance: form labels, tab navigation, keyboard Enter, heading hierarchy, focus indicators, ARIA attributes, and duplicate IDs.',
    commonCauses: [
      'New interactive element missing aria-label or associated <label>',
      'Focus ring removed by CSS reset (outline: none without replacement)',
      'Heading level skipped (h1 → h3 without h2)',
      'Duplicate id attribute on dynamically rendered list items',
      'Tab order broken by absolute/fixed positioning or z-index stacking',
    ],
    filesToCheck: [
      'frontend/src/components/EmailConsentForm.tsx',
      'frontend/src/components/wizard/',
      'frontend/src/app/globals.css',
    ],
  },
  perf: {
    name: 'Performance',
    severity: 'advisory',
    label: 'agent:perf',
    description: 'Tests load time, bundle size, request count, DOM node count, CLS, step transitions, console errors, and unhandled exceptions.',
    commonCauses: [
      'Large dependency added without dynamic import (bundle size regression)',
      'Unoptimized image or font blocking initial render',
      'Too many DOM nodes from rendering full list without virtualization',
      'Layout shift from element loading without reserved dimensions',
      'Console error from third-party script (analytics, tracking pixel)',
    ],
    filesToCheck: [
      'frontend/src/app/layout.tsx',
      'frontend/src/app/page.tsx',
      'frontend/next.config.js',
      'package.json',
    ],
  },
};

// Map filename patterns → agent keys
const FILE_TO_AGENT = {
  'test-results-wizard.json': 'wizard',
  'test-results-exec-review.json': 'exec-review',
  'test-results-security.json': 'security',
  'test-results-chaos.json': 'chaos',
  'test-results-a11y.json': 'a11y',
  'test-results-perf.json': 'perf',
};

const SLOW_THRESHOLD_MS = 30_000;

// ─────────────────────────────────────────────────
// Failure classification
// ─────────────────────────────────────────────────

const TIMEOUT_PATTERNS = [
  /Timeout \d+ms exceeded/i,
  /waiting for locator/i,
  /waiting for selector/i,
  /Navigation timeout/i,
  /Test timeout of \d+ms exceeded/i,
];

const ASSERTION_PATTERNS = [
  /expect\(received\)/i,
  /Expected.*Received/s,
  /AssertionError/i,
];

/**
 * Classify a failure error message.
 * Timeout is checked first because Playwright timeout messages often contain
 * `expect()` keywords (e.g. "expect(locator).toBeVisible(): Timeout 30000ms exceeded").
 *
 * @param {string|null|undefined} errorMessage
 * @returns {'timeout' | 'assertion' | 'unknown'}
 */
export function classifyFailure(errorMessage) {
  if (!errorMessage) return 'unknown';
  const msg = String(errorMessage);

  for (const pattern of TIMEOUT_PATTERNS) {
    if (pattern.test(msg)) return 'timeout';
  }
  for (const pattern of ASSERTION_PATTERNS) {
    if (pattern.test(msg)) return 'assertion';
  }
  return 'unknown';
}

// ─────────────────────────────────────────────────
// Pure functions (exported for testing)
// ─────────────────────────────────────────────────

/**
 * Parse a Playwright JSON report file.
 * Recursively walks suites → specs → tests → results.
 *
 * @param {string} filePath - Absolute path to JSON file
 * @returns {{ passed: number, failed: number, flaky: number, total: number,
 *             failures: Array, flakyTests: Array, slowTests: Array, passedTests: Array }}
 */
export function parsePlaywrightJson(filePath) {
  const raw = readFileSync(filePath, 'utf-8');
  const report = JSON.parse(raw);

  const failures = [];
  const flakyTests = [];
  const slowTests = [];
  const passedTests = [];
  let passed = 0;
  let failed = 0;
  let flaky = 0;

  function walkSuites(suites, parentFile) {
    for (const suite of suites) {
      const file = suite.file || parentFile;

      // Recurse into nested suites
      if (suite.suites && suite.suites.length > 0) {
        walkSuites(suite.suites, file);
      }

      // Process specs at this level
      if (suite.specs) {
        for (const spec of suite.specs) {
          for (const test of spec.tests || []) {
            const lastResult = test.results[test.results.length - 1];
            const maxDuration = Math.max(...test.results.map(r => r.duration || 0));

            if (test.status === 'flaky') {
              flaky++;
              flakyTests.push({
                title: spec.title,
                file,
                duration: maxDuration,
              });
            } else if (!spec.ok) {
              failed++;
              const errorResult = test.results.find(r => r.error) || lastResult;
              failures.push({
                title: spec.title,
                file,
                duration: lastResult?.duration || 0,
                error: errorResult?.error?.message || 'Unknown error',
                stack: errorResult?.error?.stack || '',
                retries: test.results.length - 1,
              });
            } else {
              passed++;
              passedTests.push({
                title: spec.title,
                file,
                duration: lastResult?.duration || 0,
              });
            }

            // Track slow tests (>30s) regardless of pass/fail
            if (maxDuration > SLOW_THRESHOLD_MS) {
              slowTests.push({
                title: spec.title,
                file,
                duration: maxDuration,
              });
            }
          }
        }
      }
    }
  }

  walkSuites(report.suites || [], '');

  return {
    passed,
    failed,
    flaky,
    total: passed + failed + flaky,
    failures,
    flakyTests,
    slowTests,
    passedTests,
  };
}

/**
 * Evaluate the quality gate.
 *
 * When classification fields (timeoutFailures, assertionFailures, unknownFailures)
 * are present, only assertion + unknown failures on critical agents block.
 * Timeout-only failures are downgraded to warnings.
 *
 * Backward-compatible: if classification fields aren't present, falls back to
 * old behavior where any failed > 0 on critical agent blocks.
 *
 * @param {Array<{ agent: string, severity: string, failed: number, infraFailure: boolean,
 *                  timeoutFailures?: number, assertionFailures?: number, unknownFailures?: number }>} agentResults
 * @returns {boolean} true if gate passes
 */
export function evaluateGate(agentResults) {
  for (const result of agentResults) {
    if (result.severity === 'critical') {
      if (result.infraFailure) return false;

      // Classification-aware gate
      if (typeof result.assertionFailures === 'number' || typeof result.unknownFailures === 'number') {
        const blocking = (result.assertionFailures || 0) + (result.unknownFailures || 0);
        if (blocking > 0) return false;
      } else {
        // Backward-compatible: no classification fields → use raw failed count
        if (result.failed > 0) return false;
      }
    }
  }
  return true;
}

/**
 * Format a de-duplication issue title.
 *
 * @param {string} agentName - Display name of the agent
 * @param {string} testTitle - Test title
 * @returns {string}
 */
export function formatIssueTitle(agentName, testTitle) {
  return `QC: ${agentName} — ${testTitle}`;
}

/**
 * Format the issue body for a single failing test.
 *
 * @param {{ agentName: string, severity: string, testTitle: string, file: string,
 *           duration: number, error: string, stack: string, runUrl: string, runNumber: number }} opts
 * @returns {string}
 */
export function formatIssueBody(opts) {
  const { agentName, severity, testTitle, file, duration, error, stack, runUrl, runNumber } = opts;
  const badge = severity === 'critical' ? '🔴 **BLOCKER**' : '🟡 **ADVISORY**';
  const durationStr = (duration / 1000).toFixed(2) + 's';
  const agentKey = Object.keys(AGENTS).find(k => AGENTS[k].name === agentName) || '';
  const agentMeta = AGENTS[agentKey] || {};
  const commonCauses = (agentMeta.commonCauses || []).map(c => `- ${c}`).join('\n');
  const filesToCheck = (agentMeta.filesToCheck || []).map(f => `- \`${f}\``).join('\n');
  const agentDescription = agentMeta.description || '';

  return `${badge}

| Field | Value |
|-------|-------|
| **Agent** | ${agentName} |
| **Test** | ${testTitle} |
| **File** | \`${file}\` |
| **Duration** | ${durationStr} |
| **Run** | [#${runNumber}](${runUrl}) |

---

### Error

\`\`\`
${error}
\`\`\`

<details>
<summary>Stack trace</summary>

\`\`\`
${stack || 'No stack trace available'}
\`\`\`

</details>

---

### Reproduce

\`\`\`bash
npx playwright test ${file} -g "${testTitle.replace(/"/g, '\\"')}"
\`\`\`

---

### What this test validates

${agentDescription}

### Common causes

${commonCauses || '- No common causes documented'}

### Files to check

${filesToCheck || '- No specific files documented'}

---
*Auto-created by Archer QC Report — run #${runNumber}*
`;
}

// ─────────────────────────────────────────────────
// CLI orchestration (only runs when invoked directly)
// ─────────────────────────────────────────────────

function isMainModule() {
  // In ESM, detect if this is the entry point
  try {
    const mainUrl = new URL(import.meta.url).pathname;
    return process.argv[1] && mainUrl.endsWith(process.argv[1].replace(/.*\//, ''));
  } catch {
    return false;
  }
}

function gh(args, { ignoreError = false } = {}) {
  try {
    return execSync(`gh ${args}`, { encoding: 'utf-8', timeout: 30_000 }).trim();
  } catch (err) {
    if (ignoreError) {
      console.warn(`  [gh warn] ${err.message.split('\n')[0]}`);
      return '';
    }
    throw err;
  }
}

function findExistingIssue(title) {
  // Search for open issue with exact title match
  const result = gh(
    `issue list --search "${title.replace(/"/g, '\\"')}" --state open --json number,title --jq '.[] | select(.title == "${title.replace(/"/g, '\\"')}") | .number'`,
    { ignoreError: true }
  );
  const num = parseInt(result, 10);
  return Number.isNaN(num) ? null : num;
}

function setOutput(key, value) {
  const outputFile = process.env.GITHUB_OUTPUT;
  if (outputFile) {
    appendFileSync(outputFile, `${key}=${value}\n`);
  }
  console.log(`  [output] ${key}=${value}`);
}

async function main() {
  const resultsDir = process.env.QC_RESULTS_DIR || 'qc-results';
  const runUrl = `https://github.com/${process.env.GITHUB_REPOSITORY || 'unknown'}/actions/runs/${process.env.GITHUB_RUN_ID || '0'}`;
  const runNumber = parseInt(process.env.GITHUB_RUN_NUMBER || '0', 10);

  console.log('╔══════════════════════════════════════════════╗');
  console.log('║         ARCHER QC REPORT GENERATOR           ║');
  console.log('╚══════════════════════════════════════════════╝');
  console.log(`  Results dir: ${resultsDir}`);
  console.log(`  Run: #${runNumber}`);
  console.log('');

  // ── 1. Read all result files ──
  const agentResults = [];
  const allFailures = [];
  const allPassedTests = [];
  const allFlakyTests = [];
  const allSlowTests = [];
  let issuesCreated = 0;
  let issuesUpdated = 0;
  let issuesClosed = 0;

  for (const [fileName, agentKey] of Object.entries(FILE_TO_AGENT)) {
    const filePath = join(resultsDir, fileName);
    const agentMeta = AGENTS[agentKey];
    const agentResult = {
      agent: agentKey,
      name: agentMeta.name,
      severity: agentMeta.severity,
      passed: 0,
      failed: 0,
      flaky: 0,
      total: 0,
      infraFailure: false,
      timeoutFailures: 0,
      assertionFailures: 0,
      unknownFailures: 0,
      failures: [],
      passedTests: [],
      flakyTests: [],
      slowTests: [],
    };

    if (!existsSync(filePath)) {
      console.log(`  ⚠ ${agentMeta.name}: no results file (infrastructure failure)`);
      agentResult.infraFailure = true;
      agentResults.push(agentResult);
      continue;
    }

    try {
      const parsed = parsePlaywrightJson(filePath);
      agentResult.passed = parsed.passed;
      agentResult.failed = parsed.failed;
      agentResult.flaky = parsed.flaky;
      agentResult.total = parsed.total;
      agentResult.failures = parsed.failures;
      agentResult.passedTests = parsed.passedTests;
      agentResult.flakyTests = parsed.flakyTests;
      agentResult.slowTests = parsed.slowTests;

      // Classify each failure
      for (const f of parsed.failures) {
        f.classification = classifyFailure(f.error);
        if (f.classification === 'timeout') agentResult.timeoutFailures++;
        else if (f.classification === 'assertion') agentResult.assertionFailures++;
        else agentResult.unknownFailures++;
      }

      allFailures.push(...parsed.failures.map(f => ({ ...f, agentKey, agentName: agentMeta.name, severity: agentMeta.severity })));
      allPassedTests.push(...parsed.passedTests.map(t => ({ ...t, agentKey, agentName: agentMeta.name })));
      allFlakyTests.push(...parsed.flakyTests.map(t => ({ ...t, agentKey, agentName: agentMeta.name })));
      allSlowTests.push(...parsed.slowTests.map(t => ({ ...t, agentKey, agentName: agentMeta.name })));

      const status = parsed.failed > 0 ? '❌' : '✅';
      console.log(`  ${status} ${agentMeta.name}: ${parsed.passed} passed, ${parsed.failed} failed, ${parsed.flaky} flaky (${parsed.total} total)`);
    } catch (err) {
      console.log(`  ⚠ ${agentMeta.name}: corrupted JSON (${err.message})`);
      agentResult.infraFailure = true;
    }

    agentResults.push(agentResult);
  }

  // ── 2. Evaluate quality gate ──
  const gatePassed = evaluateGate(agentResults);
  console.log('');
  console.log(`  Quality gate: ${gatePassed ? '✅ PASSED' : '❌ BLOCKED'}`);
  setOutput('gate_passed', gatePassed.toString());

  // ── 3. Create/update/close issues ──
  console.log('');
  console.log('  Processing failure issues...');

  for (const failure of allFailures) {
    const title = formatIssueTitle(failure.agentName, failure.title);
    const existingNum = findExistingIssue(title);

    if (existingNum) {
      // Update existing issue with new comment
      const commentBody = `Still failing in run [#${runNumber}](${runUrl}).\n\n\`\`\`\n${failure.error}\n\`\`\``;
      const tmpFile = `/tmp/qc-comment-${Date.now()}.md`;
      writeFileSync(tmpFile, commentBody);
      gh(`issue comment ${existingNum} --body-file "${tmpFile}"`, { ignoreError: true });
      issuesUpdated++;
      console.log(`    ↻ Updated #${existingNum}: ${failure.title}`);
    } else {
      // Create new issue
      const body = formatIssueBody({
        agentName: failure.agentName,
        severity: failure.severity,
        testTitle: failure.title,
        file: failure.file,
        duration: failure.duration,
        error: failure.error,
        stack: failure.stack,
        runUrl,
        runNumber,
      });

      const agentMeta = AGENTS[failure.agentKey];
      const severityLabel = failure.classification === 'timeout' ? 'qc:timeout'
        : failure.severity === 'critical' ? 'qc:blocker' : 'qc:advisory';
      const labels = `archer,${severityLabel},${agentMeta.label}`;
      const tmpFile = `/tmp/qc-issue-${Date.now()}.md`;
      writeFileSync(tmpFile, body);

      const result = gh(
        `issue create --title "${title.replace(/"/g, '\\"')}" --body-file "${tmpFile}" --label "${labels}"`,
        { ignoreError: true }
      );
      issuesCreated++;
      console.log(`    + Created: ${failure.title} ${result ? `(${result})` : ''}`);
    }
  }

  // ── 4. Auto-close resolved issues ──
  console.log('');
  console.log('  Checking for resolved issues...');

  for (const passedTest of allPassedTests) {
    const title = formatIssueTitle(passedTest.agentName, passedTest.title);
    const existingNum = findExistingIssue(title);

    if (existingNum) {
      gh(
        `issue close ${existingNum} --comment "✅ Resolved in run [#${runNumber}](${runUrl}). Test is now passing."`,
        { ignoreError: true }
      );
      issuesClosed++;
      console.log(`    ✓ Closed #${existingNum}: ${passedTest.title}`);
    }
  }

  // ── 5. Generate summary report ──
  console.log('');
  console.log('  Generating summary report...');

  const totalTests = agentResults.reduce((sum, a) => sum + a.total, 0);
  const totalPassed = agentResults.reduce((sum, a) => sum + a.passed, 0);
  const totalFailed = agentResults.reduce((sum, a) => sum + a.failed, 0);
  const totalFlaky = agentResults.reduce((sum, a) => sum + a.flaky, 0);
  const infraFailures = agentResults.filter(a => a.infraFailure);

  let summary = `## Archer QC Report — Run #${runNumber}\n\n`;
  summary += `**Date:** ${new Date().toISOString().replace('T', ' ').replace(/\.\d+Z/, ' UTC')}\n`;
  summary += `**Quality Gate:** ${gatePassed ? '✅ PASSED' : '❌ BLOCKED'}\n`;
  summary += `**Run:** [View logs](${runUrl})\n\n`;

  // Agent results table
  summary += '### Agent Results\n\n';
  summary += '| # | Agent | Role | Passed | Failed | Flaky | Slow | Status |\n';
  summary += '|---|-------|------|--------|--------|-------|------|--------|\n';

  const agentNumbers = { wizard: '1a', 'exec-review': '1b', security: '2', chaos: '3', a11y: '4', perf: '5' };

  for (const result of agentResults) {
    const num = agentNumbers[result.agent] || '?';
    const role = result.severity === 'critical' ? 'Critical' : 'Advisory';
    const slowCount = result.slowTests.length;

    let status;
    if (result.infraFailure) {
      status = '⚠️ INFRA FAILURE';
    } else if (result.failed > 0) {
      status = '❌ FAIL';
    } else if (result.flaky > 0) {
      status = '⚡ FLAKY';
    } else {
      status = '✅ PASS';
    }

    summary += `| ${num} | ${result.name} | ${role} | ${result.passed} | ${result.failed} | ${result.flaky} | ${slowCount} | ${status} |\n`;
  }

  summary += `\n**${totalTests} tests** across ${agentResults.length} agents: ${totalPassed} passed, ${totalFailed} failed, ${totalFlaky} flaky\n\n`;

  // Blockers section — excludes timeout-only failures on critical agents
  const blockers = allFailures.filter(f => f.severity === 'critical' && f.classification !== 'timeout');
  if (blockers.length > 0) {
    summary += '### 🔴 Blockers\n\n';
    for (const b of blockers) {
      summary += `- **${b.agentName}** — ${b.title}\n`;
      summary += `  \`\`\`\n  ${b.error.split('\n')[0]}\n  \`\`\`\n`;
    }
    summary += '\n';
  }

  // Timeouts section — timeout failures from any agent
  const timeouts = allFailures.filter(f => f.classification === 'timeout');
  if (timeouts.length > 0) {
    summary += '### ⏱ Timeouts (likely infrastructure — not blocking)\n\n';
    for (const t of timeouts) {
      summary += `- **${t.agentName}** — ${t.title}: ${t.error.split('\n')[0]}\n`;
    }
    summary += '\n';
  }

  // Advisory warnings — non-timeout failures from advisory agents
  const advisories = allFailures.filter(f => f.severity === 'advisory' && f.classification !== 'timeout');
  if (advisories.length > 0) {
    summary += '### 🟡 Advisory Warnings\n\n';
    for (const a of advisories) {
      summary += `- **${a.agentName}** — ${a.title}: ${a.error.split('\n')[0]}\n`;
    }
    summary += '\n';
  }

  // Infrastructure failures
  if (infraFailures.length > 0) {
    summary += '### ⚠️ Infrastructure Failures\n\n';
    for (const inf of infraFailures) {
      summary += `- **${inf.name}** — No test results produced (Playwright may have crashed before generating JSON output)\n`;
    }
    summary += '\n';
  }

  // Flaky tests
  if (allFlakyTests.length > 0) {
    summary += '### ⚡ Flaky Tests (passed on retry — investigate intermittent failures)\n\n';
    for (const f of allFlakyTests) {
      summary += `- **${f.agentName}** — ${f.title} (\`${f.file}\`)\n`;
    }
    summary += '\n';
  }

  // Slow tests
  if (allSlowTests.length > 0) {
    summary += `### 🐢 Slow Tests (>${SLOW_THRESHOLD_MS / 1000}s — approaching 45s timeout)\n\n`;
    for (const s of allSlowTests) {
      summary += `- **${s.agentName}** — ${s.title}: ${(s.duration / 1000).toFixed(1)}s (\`${s.file}\`)\n`;
    }
    summary += '\n';
  }

  // Issue activity
  if (issuesCreated > 0 || issuesUpdated > 0 || issuesClosed > 0) {
    summary += '### Issue Activity\n\n';
    summary += `| Action | Count |\n`;
    summary += `|--------|-------|\n`;
    if (issuesCreated > 0) summary += `| Created | ${issuesCreated} |\n`;
    if (issuesUpdated > 0) summary += `| Updated | ${issuesUpdated} |\n`;
    if (issuesClosed > 0) summary += `| Resolved | ${issuesClosed} |\n`;
    summary += '\n';
  }

  // Recommended next actions
  summary += '### Recommended Next Actions\n\n';
  let actionNum = 1;
  if (blockers.length > 0) {
    summary += `${actionNum++}. **Fix blockers first** — critical agent failures prevent promotion to production\n`;
    summary += `${actionNum++}. Review individual QC issues (labeled \`qc:blocker\`) for detailed error info and reproduce commands\n`;
  }
  if (timeouts.length > 0) {
    summary += `${actionNum++}. **No action needed** — ${timeouts.length} timeout failure${timeouts.length > 1 ? 's' : ''} likely caused by infrastructure cold starts (passed on other recent runs)\n`;
  }
  if (allFlakyTests.length > 0) {
    summary += `${actionNum++}. **Investigate flaky tests** — they passed on retry but indicate intermittent issues\n`;
  }
  if (allSlowTests.length > 0) {
    summary += `${actionNum++}. **Optimize slow tests** — approaching the 45s timeout threshold\n`;
  }
  if (blockers.length === 0 && timeouts.length === 0 && allFlakyTests.length === 0 && allSlowTests.length === 0) {
    summary += '1. All clear — no blockers, flaky tests, or slow tests detected\n';
  }

  // ── QC Analyst Agent ──
  if (allFailures.length > 0) {
    console.log('');
    console.log('  Running QC Analyst...');

    try {
      // Layer 1: Git correlation (always runs)
      const correlations = correlateWithGit(allFailures, AGENTS);

      // Cross-run pattern detection
      let existingIssues = [];
      try {
        const issueJson = gh(
          'issue list --state open --label "archer" --json title,comments --jq "[.[] | {title: .title, comments: (.comments | length)}]"',
          { ignoreError: true }
        );
        if (issueJson) existingIssues = JSON.parse(issueJson);
      } catch { /* gh not available or parse error */ }

      const patterns = detectPatterns(allFailures, existingIssues);

      // Layer 2: LLM analysis (only for blockers, only if API key set)
      const blockerFailures = allFailures.filter(f => f.severity === 'critical' && f.classification !== 'timeout');
      const blockerCorrelations = correlations.filter(c => blockerFailures.some(b => b.title === c.title));
      const llmResults = await analyzeWithLLM(blockerFailures, blockerCorrelations);

      const analystNotes = formatAnalystNotes(correlations, patterns, llmResults);
      if (analystNotes) {
        summary += analystNotes;
        console.log('  QC Analyst notes appended to summary.');
      }
    } catch (err) {
      console.warn(`  [analyst] Error: ${err.message}`);
    }
  }

  summary += '\n---\n*Auto-created by Archer QC Report*\n';

  // Write summary
  writeFileSync('qc-summary.md', summary);
  console.log('  Summary written to qc-summary.md');

  // ── 6. Close previous summary issue ──
  console.log('');
  console.log('  Closing previous summary issues...');

  const prevSummaries = gh(
    'issue list --search "Archer QC Report" --state open --label "qc:report" --json number --jq ".[].number"',
    { ignoreError: true }
  );

  if (prevSummaries) {
    for (const num of prevSummaries.split('\n').filter(Boolean)) {
      gh(`issue close ${num} --comment "Superseded by run [#${runNumber}](${runUrl})"`, { ignoreError: true });
      console.log(`    ✓ Closed previous summary #${num}`);
    }
  }

  console.log('');
  console.log('  Done.');
}

// Run main only when executed directly (not imported for testing)
if (isMainModule()) {
  main();
}
