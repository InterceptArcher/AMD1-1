/**
 * Unit tests for Archer QC Analyst Agent
 * Tests git correlation, cross-run pattern detection, and output formatting.
 *
 * Run: node --test tests/unit/qc-analyst.test.mjs
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');

const mod = await import(join(ROOT, 'scripts', 'archer-qc-analyst.mjs'));
const { correlateWithGit, detectPatterns, formatAnalystNotes, analyzeWithLLM } = mod;

// ── Mock AGENTS registry (subset) ──

const AGENTS = {
  wizard: {
    name: 'Wizard + Enrichment',
    severity: 'critical',
    filesToCheck: [
      'frontend/src/components/EmailConsentForm.tsx',
      'frontend/src/components/wizard/',
      'backend/app/routes/enrichment.py',
    ],
  },
  security: {
    name: 'Security',
    severity: 'critical',
    filesToCheck: [
      'frontend/src/components/EmailConsentForm.tsx',
      'frontend/next.config.js',
      'backend/app/routes/enrichment.py',
      'vercel.json',
    ],
  },
};

// ── Git Correlation Tests ──

describe('QC Analyst — Git Correlation', () => {
  it('returns correlations for each failure', () => {
    const failures = [
      { title: 'step 3 progressive reveal', agentKey: 'wizard', error: 'Timeout', file: 'tests/e2e/wizard-flow.spec.ts' },
      { title: 'XSS injection', agentKey: 'security', error: 'Expected no script', file: 'tests/e2e/security-audit.spec.ts' },
    ];

    // Mock execSync to return fake git log
    const mockExec = (cmd) => {
      if (cmd.includes('EmailConsentForm.tsx')) return 'abc123 Updated wizard step transitions';
      return '';
    };

    const results = correlateWithGit(failures, AGENTS, { execFn: mockExec });
    assert.equal(results.length, 2);
    assert.equal(results[0].title, 'step 3 progressive reveal');
    assert.ok(results[0].recentCommits.length > 0, 'should find commits for wizard');
  });

  it('returns empty commits when no recent changes', () => {
    const failures = [
      { title: 'XSS injection', agentKey: 'security', error: 'Error', file: 'tests/e2e/security-audit.spec.ts' },
    ];

    const mockExec = () => '';
    const results = correlateWithGit(failures, AGENTS, { execFn: mockExec });
    assert.equal(results[0].recentCommits.length, 0);
    assert.equal(results[0].confidence, 'low');
  });

  it('sets high confidence when recent commits found', () => {
    const failures = [
      { title: 'wizard fails', agentKey: 'wizard', error: 'Error', file: 'tests/e2e/wizard-flow.spec.ts' },
    ];

    const mockExec = (cmd) => {
      if (cmd.includes('EmailConsentForm')) return 'abc123 Refactored form';
      return '';
    };

    const results = correlateWithGit(failures, AGENTS, { execFn: mockExec });
    assert.equal(results[0].confidence, 'high');
  });

  it('handles unknown agent gracefully', () => {
    const failures = [
      { title: 'unknown test', agentKey: 'nonexistent', error: 'Error', file: 'test.ts' },
    ];

    const results = correlateWithGit(failures, AGENTS, { execFn: () => '' });
    assert.equal(results.length, 1);
    assert.equal(results[0].recentCommits.length, 0);
  });
});

// ── Cross-Run Pattern Detection Tests ──

describe('QC Analyst — Pattern Detection', () => {
  it('detects persistent failure from existing issues', () => {
    const failures = [
      { title: 'step 3 progressive reveal', agentName: 'Wizard + Enrichment' },
    ];

    const existingIssues = [
      { title: 'QC: Wizard + Enrichment — step 3 progressive reveal', comments: 3 },
    ];

    const patterns = detectPatterns(failures, existingIssues);
    assert.equal(patterns.length, 1);
    assert.ok(patterns[0].persistent, 'should be marked persistent');
    assert.equal(patterns[0].previousRuns, 4); // 1 creation + 3 comments = 4 runs
  });

  it('detects new failure when no existing issue', () => {
    const failures = [
      { title: 'new test failure', agentName: 'Security' },
    ];

    const patterns = detectPatterns(failures, []);
    assert.equal(patterns.length, 1);
    assert.equal(patterns[0].persistent, false);
    assert.equal(patterns[0].previousRuns, 0);
  });

  it('handles multiple failures with mixed patterns', () => {
    const failures = [
      { title: 'old failure', agentName: 'Wizard + Enrichment' },
      { title: 'brand new', agentName: 'Security' },
    ];

    const existingIssues = [
      { title: 'QC: Wizard + Enrichment — old failure', comments: 5 },
    ];

    const patterns = detectPatterns(failures, existingIssues);
    assert.equal(patterns.length, 2);
    assert.ok(patterns[0].persistent);
    assert.ok(!patterns[1].persistent);
  });
});

// ── Output Formatting Tests ──

describe('QC Analyst — Output Formatting', () => {
  it('produces markdown with all sections', () => {
    const correlations = [
      {
        title: 'step 3 progressive reveal',
        agentName: 'Wizard + Enrichment',
        confidence: 'high',
        recentCommits: [{ hash: 'abc123', message: 'Updated wizard', file: 'EmailConsentForm.tsx' }],
      },
    ];

    const patterns = [
      { title: 'step 3 progressive reveal', persistent: true, previousRuns: 3 },
    ];

    const md = formatAnalystNotes(correlations, patterns, null);
    assert.ok(md.includes('QC Analyst Notes'), 'should include section title');
    assert.ok(md.includes('Failure Correlation'), 'should include correlation table');
    assert.ok(md.includes('Cross-Run Patterns'), 'should include patterns section');
    assert.ok(md.includes('abc123'), 'should include commit hash');
    assert.ok(md.includes('persistent'), 'should mention persistent');
  });

  it('includes LLM analysis when provided', () => {
    const correlations = [
      { title: 'test failure', agentName: 'Security', confidence: 'low', recentCommits: [] },
    ];
    const patterns = [
      { title: 'test failure', persistent: false, previousRuns: 0 },
    ];
    const llmResults = [
      { title: 'test failure', rootCause: 'Selector changed in recent refactor', suggestedFix: 'Update selector to data-testid' },
    ];

    const md = formatAnalystNotes(correlations, patterns, llmResults);
    assert.ok(md.includes('Root Cause Analysis'), 'should include LLM section');
    assert.ok(md.includes('Selector changed'), 'should include root cause');
    assert.ok(md.includes('Update selector'), 'should include suggested fix');
  });

  it('omits LLM section when results are null', () => {
    const md = formatAnalystNotes(
      [{ title: 't', agentName: 'A', confidence: 'low', recentCommits: [] }],
      [{ title: 't', persistent: false, previousRuns: 0 }],
      null,
    );
    assert.ok(!md.includes('Root Cause Analysis'), 'should not include LLM section');
  });

  it('returns empty string when no failures', () => {
    const md = formatAnalystNotes([], [], null);
    assert.equal(md, '');
  });
});

// ── LLM Analysis Tests ──

describe('QC Analyst — LLM Analysis', () => {
  it('returns null when no API key is set', async () => {
    const result = await analyzeWithLLM(
      [{ title: 'test', error: 'Error', file: 'test.ts' }],
      [{ title: 'test', recentCommits: [] }],
      { apiKey: null },
    );
    assert.equal(result, null);
  });

  it('returns null for empty failures list', async () => {
    const result = await analyzeWithLLM([], [], { apiKey: 'test-key' });
    assert.equal(result, null);
  });
});
