#!/usr/bin/env node

/**
 * Archer QC Analyst Agent
 *
 * Correlates test failures with recent git commits and optionally uses
 * Claude Haiku for root cause analysis. Called by archer-qc-report.mjs
 * after gate evaluation, before summary issue creation.
 *
 * Two layers:
 *   1. Git correlation (always runs, zero cost)
 *   2. LLM analysis (runs if ANTHROPIC_API_KEY is set)
 *
 * Exports (for testing):
 *   correlateWithGit, detectPatterns, analyzeWithLLM, formatAnalystNotes
 */

import { execSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

// ─────────────────────────────────────────────────
// Layer 1: Git Correlation
// ─────────────────────────────────────────────────

/**
 * For each failure, check if files monitored by the agent's registry
 * were recently modified.
 *
 * @param {Array<{ title: string, agentKey: string, error: string, file: string }>} failures
 * @param {Record<string, { filesToCheck: string[] }>} agentsRegistry
 * @param {{ execFn?: (cmd: string) => string }} options - injectable exec for testing
 * @returns {Array<{ title: string, agentName: string, confidence: string, recentCommits: Array<{ hash: string, message: string, file: string }> }>}
 */
export function correlateWithGit(failures, agentsRegistry, options = {}) {
  const exec = options.execFn || ((cmd) => {
    try {
      return execSync(cmd, { encoding: 'utf-8', timeout: 10_000 }).trim();
    } catch {
      return '';
    }
  });

  return failures.map((failure) => {
    const agent = agentsRegistry[failure.agentKey];
    const filesToCheck = agent?.filesToCheck || [];
    const recentCommits = [];

    for (const filePath of filesToCheck) {
      const output = exec(`git log --since "24 hours ago" --oneline -- "${filePath}"`);
      if (!output) continue;

      for (const line of output.split('\n').filter(Boolean)) {
        const spaceIdx = line.indexOf(' ');
        if (spaceIdx === -1) continue;
        recentCommits.push({
          hash: line.slice(0, spaceIdx),
          message: line.slice(spaceIdx + 1),
          file: filePath,
        });
      }
    }

    return {
      title: failure.title,
      agentName: failure.agentName || agent?.name || failure.agentKey,
      confidence: recentCommits.length > 0 ? 'high' : 'low',
      recentCommits,
    };
  });
}

// ─────────────────────────────────────────────────
// Cross-Run Pattern Detection
// ─────────────────────────────────────────────────

/**
 * Detect cross-run patterns by checking for existing open QC issues.
 *
 * @param {Array<{ title: string, agentName: string }>} failures
 * @param {Array<{ title: string, comments: number }>} existingIssues
 * @returns {Array<{ title: string, persistent: boolean, previousRuns: number }>}
 */
export function detectPatterns(failures, existingIssues) {
  return failures.map((failure) => {
    const issueTitle = `QC: ${failure.agentName} — ${failure.title}`;
    const match = existingIssues.find((i) => i.title === issueTitle);

    if (match) {
      // 1 creation run + N comment runs = total failing runs
      const previousRuns = 1 + (match.comments || 0);
      return {
        title: failure.title,
        persistent: true,
        previousRuns,
      };
    }

    return {
      title: failure.title,
      persistent: false,
      previousRuns: 0,
    };
  });
}

// ─────────────────────────────────────────────────
// Layer 2: LLM Analysis (optional)
// ─────────────────────────────────────────────────

/**
 * Analyze blocker failures with Claude Haiku.
 * Gracefully returns null if API key is missing or call fails.
 *
 * @param {Array<{ title: string, error: string, file: string }>} failures
 * @param {Array<{ title: string, recentCommits: Array }>} correlations
 * @param {{ apiKey?: string|null }} options
 * @returns {Promise<Array<{ title: string, rootCause: string, suggestedFix: string }>|null>}
 */
export async function analyzeWithLLM(failures, correlations, options = {}) {
  const apiKey = options.apiKey ?? process.env.ANTHROPIC_API_KEY;
  if (!apiKey || failures.length === 0) return null;

  let Anthropic;
  try {
    const sdk = await import('@anthropic-ai/sdk');
    Anthropic = sdk.default || sdk.Anthropic;
  } catch {
    console.warn('  [analyst] @anthropic-ai/sdk not available — skipping LLM analysis');
    return null;
  }

  const client = new Anthropic({ apiKey });
  const results = [];

  for (const failure of failures) {
    const correlation = correlations.find((c) => c.title === failure.title);
    const commitContext = correlation?.recentCommits?.length
      ? correlation.recentCommits.map((c) => `- ${c.hash} ${c.message} (${c.file})`).join('\n')
      : 'No recent commits to related files';

    // Read source snippets (best-effort)
    let sourceSnippet = '';
    try {
      const agent = correlation?.recentCommits?.[0]?.file;
      if (agent) {
        const content = readFileSync(agent, 'utf-8');
        sourceSnippet = content.split('\n').slice(0, 200).join('\n');
      }
    } catch { /* file not available in CI */ }

    const prompt = `Analyze this E2E test failure. Be concise (2-3 sentences each for root cause and fix).

Test: ${failure.title}
File: ${failure.file}
Error: ${failure.error}

Recent git changes to related files:
${commitContext}

${sourceSnippet ? `Source snippet:\n\`\`\`\n${sourceSnippet.slice(0, 2000)}\n\`\`\`` : ''}

Respond with:
ROOT CAUSE: <2-3 sentences>
SUGGESTED FIX: <2-3 sentences>`;

    try {
      const response = await client.messages.create({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 300,
        messages: [{ role: 'user', content: prompt }],
      });

      const text = response.content?.[0]?.text || '';
      const rootCauseMatch = text.match(/ROOT CAUSE:\s*(.+?)(?=SUGGESTED FIX:|$)/s);
      const fixMatch = text.match(/SUGGESTED FIX:\s*(.+)/s);

      results.push({
        title: failure.title,
        rootCause: rootCauseMatch?.[1]?.trim() || text.trim(),
        suggestedFix: fixMatch?.[1]?.trim() || '',
      });
    } catch (err) {
      console.warn(`  [analyst] LLM analysis failed for "${failure.title}": ${err.message}`);
    }
  }

  return results.length > 0 ? results : null;
}

// ─────────────────────────────────────────────────
// Output Formatting
// ─────────────────────────────────────────────────

/**
 * Format analyst notes as markdown to append to the QC summary.
 *
 * @param {Array} correlations - from correlateWithGit
 * @param {Array} patterns - from detectPatterns
 * @param {Array|null} llmResults - from analyzeWithLLM
 * @returns {string} markdown string (empty if no failures)
 */
export function formatAnalystNotes(correlations, patterns, llmResults) {
  if (!correlations || correlations.length === 0) return '';

  let md = '\n### 🔍 QC Analyst Notes\n\n';

  // Failure Correlation table
  md += '#### Failure Correlation\n\n';
  md += '| Test | Likely Cause | Confidence |\n';
  md += '|------|-------------|------------|\n';

  for (const c of correlations) {
    let cause;
    if (c.recentCommits.length > 0) {
      const commit = c.recentCommits[0];
      cause = `Commit \`${commit.hash}\` modified \`${commit.file}\` — "${commit.message}"`;
    } else {
      cause = 'No recent changes to related files';
    }
    const conf = c.confidence === 'high' ? 'High' : 'Low (investigate)';
    md += `| ${c.agentName} — ${c.title} | ${cause} | ${conf} |\n`;
  }
  md += '\n';

  // Cross-Run Patterns
  md += '#### Cross-Run Patterns\n\n';
  for (const p of patterns) {
    if (p.persistent) {
      md += `- **${p.title}**: Failed ${p.previousRuns} of last runs — persistent issue\n`;
    } else {
      md += `- **${p.title}**: New failure — first seen this run\n`;
    }
  }
  md += '\n';

  // LLM Analysis (optional)
  if (llmResults && llmResults.length > 0) {
    md += '#### Root Cause Analysis (Claude)\n\n';
    for (const r of llmResults) {
      md += `**${r.title}**\n`;
      md += `> ${r.rootCause}\n`;
      if (r.suggestedFix) {
        md += `> **Fix:** ${r.suggestedFix}\n`;
      }
      md += '\n';
    }
  }

  return md;
}
