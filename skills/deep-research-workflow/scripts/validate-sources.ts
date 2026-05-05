#!/usr/bin/env npx tsx
// Source Validation Script
// 用法: npx tsx validate-sources.ts <markdown-files...> [--threshold 0.6] [--max-urls 30] [--json]
// 输出: 每份报告的 URL 健康度报告 + 整体 verdict

import * as fs from 'node:fs';
import * as path from 'node:path';
import { classifyDomain, type SourceTier } from './lib/quality/source-tier.ts';
import { detectAntiPatterns, formatAntiPatternReport } from './lib/quality/anti-patterns.ts';

interface ValidationResult {
  file: string;
  totalUrls: number;
  uniqueDomains: number;
  tierA: number;
  tierB: number;
  tierC: number;
  tierUnknown: number;
  duplicateSources: { host: string; count: number }[];
  validationPassRate: number;
  validationSampled: number;
  validationFailed: { url: string; status: string }[];
  groundingRedirects: number;
  verdict: 'PASS' | 'WARN' | 'FAIL';
  warnings: string[];
}

interface CombinedResult {
  files: ValidationResult[];
  overallVerdict: 'PASS' | 'WARN' | 'FAIL';
  recommendations: string[];
}

function extractUrls(text: string): string[] {
  // Markdown link [text](url) + plain http(s) URLs
  const urls: string[] = [];
  const mdLink = /\[[^\]]*\]\((https?:\/\/[^\s)]+)\)/g;
  const plainUrl = /(?<![("\[])(https?:\/\/[^\s)\]"'`<>]+)/g;

  let m: RegExpExecArray | null;
  while ((m = mdLink.exec(text)) !== null) urls.push(m[1]);
  while ((m = plainUrl.exec(text)) !== null) urls.push(m[1]);

  // De-dup but preserve order
  return Array.from(new Set(urls));
}

function getHostSafe(url: string): string | null {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return null;
  }
}

async function checkUrlAlive(url: string, timeoutMs = 8000): Promise<{ ok: boolean; status: string }> {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    const res = await fetch(url, {
      method: 'HEAD',
      signal: ctrl.signal,
      redirect: 'follow',
      headers: { 'User-Agent': 'Mozilla/5.0 (DR-validate-sources)' },
    });
    clearTimeout(timer);
    return { ok: res.ok || res.status < 400, status: String(res.status) };
  } catch (e: any) {
    return { ok: false, status: e.message || 'fetch_error' };
  }
}

function pickSampleUrls(urls: string[], maxN: number): string[] {
  if (urls.length <= maxN) return urls;
  const step = Math.floor(urls.length / maxN);
  const sample: string[] = [];
  for (let i = 0; i < urls.length && sample.length < maxN; i += step) sample.push(urls[i]);
  return sample;
}

async function validateFile(file: string, opts: { threshold: number; maxUrls: number }): Promise<ValidationResult> {
  const text = fs.readFileSync(file, 'utf-8');
  const urls = extractUrls(text);

  // Tier classification (all URLs)
  const hostCounts = new Map<string, number>();
  let tierA = 0, tierB = 0, tierC = 0, tierUnknown = 0, groundingRedirects = 0;

  for (const url of urls) {
    const { tier, host } = classifyDomain(url);
    if (host.includes('vertexaisearch.cloud.google.com')) groundingRedirects++;
    hostCounts.set(host, (hostCounts.get(host) ?? 0) + 1);
    if (tier === 'A') tierA++;
    else if (tier === 'B') tierB++;
    else if (tier === 'C') tierC++;
    else tierUnknown++;
  }

  const duplicateSources = Array.from(hostCounts.entries())
    .filter(([, c]) => c >= 3)
    .sort((a, b) => b[1] - a[1])
    .map(([host, count]) => ({ host, count }));

  // URL liveness sampling
  const sample = pickSampleUrls(urls, opts.maxUrls);
  const validationFailed: { url: string; status: string }[] = [];
  let validationOk = 0;

  // Concurrency 5
  const results = await Promise.all(
    sample.map(async (url) => ({ url, ...(await checkUrlAlive(url)) })),
  );
  for (const r of results) {
    if (r.ok) validationOk++;
    else validationFailed.push({ url: r.url, status: r.status });
  }

  const validationPassRate = sample.length > 0 ? validationOk / sample.length : 1;

  const warnings: string[] = [];
  let verdict: ValidationResult['verdict'] = 'PASS';

  // Verdict rules
  if (validationPassRate < opts.threshold) {
    verdict = 'FAIL';
    warnings.push(`URL pass rate ${(validationPassRate * 100).toFixed(0)}% < threshold ${(opts.threshold * 100).toFixed(0)}%`);
  }
  if (groundingRedirects > 0) {
    warnings.push(`${groundingRedirects} Gemini grounding redirects (URL transparency low)`);
    if (verdict === 'PASS') verdict = 'WARN';
  }
  if (duplicateSources.length > 0) {
    warnings.push(`Single-source over-reliance: ${duplicateSources.map((d) => `${d.host} ×${d.count}`).join(', ')}`);
    if (verdict === 'PASS') verdict = 'WARN';
  }
  const totalAB = tierA + tierB;
  const totalUrls = urls.length;
  if (totalUrls > 5 && totalAB / totalUrls < 0.5) {
    warnings.push(`A/B-tier coverage ${((totalAB / totalUrls) * 100).toFixed(0)}% < 50%`);
    if (verdict === 'PASS') verdict = 'WARN';
  }
  // Domain concentration
  for (const [host, count] of hostCounts) {
    if (totalUrls > 5 && count / totalUrls >= 0.4) {
      warnings.push(`Domain concentration: ${host} = ${((count / totalUrls) * 100).toFixed(0)}% of URLs`);
      verdict = 'FAIL';
    }
  }

  return {
    file,
    totalUrls,
    uniqueDomains: hostCounts.size,
    tierA,
    tierB,
    tierC,
    tierUnknown,
    duplicateSources,
    validationPassRate: Number(validationPassRate.toFixed(2)),
    validationSampled: sample.length,
    validationFailed,
    groundingRedirects,
    verdict,
    warnings,
  };
}

function formatHumanReport(combined: CombinedResult): string {
  const lines: string[] = [];
  lines.push(`# Source Validation Report`);
  lines.push(``);
  lines.push(`## Overall Verdict: ${combined.overallVerdict}`);
  lines.push(``);

  for (const r of combined.files) {
    lines.push(`### ${path.basename(r.file)}`);
    lines.push(`- **Verdict**: ${r.verdict}`);
    lines.push(`- **URLs**: ${r.totalUrls} total, ${r.uniqueDomains} unique domains`);
    lines.push(`- **Tier**: A=${r.tierA} | B=${r.tierB} | C=${r.tierC} | ?=${r.tierUnknown}`);
    lines.push(`- **Liveness**: ${(r.validationPassRate * 100).toFixed(0)}% pass (${r.validationSampled} sampled)`);
    if (r.duplicateSources.length > 0) {
      lines.push(`- **Single-source warnings**:`);
      r.duplicateSources.forEach((d) => lines.push(`  - ${d.host} ×${d.count}`));
    }
    if (r.validationFailed.length > 0) {
      lines.push(`- **Failed URLs** (top 5):`);
      r.validationFailed.slice(0, 5).forEach((f) => lines.push(`  - [${f.status}] ${f.url}`));
    }
    if (r.groundingRedirects > 0) {
      lines.push(`- **⚠️ Grounding redirects**: ${r.groundingRedirects}`);
    }
    if (r.warnings.length > 0) {
      lines.push(`- **Warnings**: ${r.warnings.join(' | ')}`);
    }
    lines.push(``);
  }

  if (combined.recommendations.length > 0) {
    lines.push(`## Recommendations`);
    combined.recommendations.forEach((rec) => lines.push(`- ${rec}`));
  }

  return lines.join('\n');
}

async function main() {
  const args = process.argv.slice(2);
  const flags = {
    threshold: 0.6,
    maxUrls: 30,
    json: false,
    antiPatterns: false,
  };
  const files: string[] = [];

  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--threshold') flags.threshold = parseFloat(args[++i]);
    else if (a === '--max-urls') flags.maxUrls = parseInt(args[++i], 10);
    else if (a === '--json') flags.json = true;
    else if (a === '--anti-patterns') flags.antiPatterns = true;
    else files.push(a);
  }

  if (files.length === 0) {
    console.error('Usage: validate-sources.ts <md-files...> [--threshold 0.6] [--max-urls 30] [--json] [--anti-patterns]');
    process.exit(1);
  }

  const results: ValidationResult[] = [];
  for (const f of files) {
    if (!fs.existsSync(f)) {
      console.error(`Skip: ${f} not found`);
      continue;
    }
    process.stderr.write(`Validating ${path.basename(f)}... `);
    const r = await validateFile(f, flags);
    results.push(r);
    process.stderr.write(`${r.verdict}\n`);
  }

  let overallVerdict: CombinedResult['overallVerdict'] = 'PASS';
  if (results.some((r) => r.verdict === 'FAIL')) overallVerdict = 'FAIL';
  else if (results.some((r) => r.verdict === 'WARN')) overallVerdict = 'WARN';

  const recs: string[] = [];
  if (results.some((r) => r.duplicateSources.length > 0)) {
    recs.push('Single-source warnings detected → Phase 2.6 cross-validation REQUIRED for affected reports');
  }
  if (results.some((r) => r.validationPassRate < flags.threshold)) {
    recs.push(`URL liveness below ${(flags.threshold * 100).toFixed(0)}% → Manual URL audit + replace dead URLs`);
  }
  if (results.some((r) => r.groundingRedirects > 0)) {
    recs.push('Gemini grounding redirects present → Resolve to real URLs before publishing');
  }
  const totalAB = results.reduce((s, r) => s + r.tierA + r.tierB, 0);
  const totalUrls = results.reduce((s, r) => s + r.totalUrls, 0);
  if (totalUrls > 0 && totalAB / totalUrls < 0.5) {
    recs.push(`Overall A/B coverage ${((totalAB / totalUrls) * 100).toFixed(0)}% < 50% → Strengthen authoritative sourcing`);
  }

  const combined: CombinedResult = { files: results, overallVerdict, recommendations: recs };

  // Optional anti-patterns scan
  if (flags.antiPatterns) {
    const apReports: string[] = [];
    for (const f of files) {
      if (!fs.existsSync(f)) continue;
      const text = fs.readFileSync(f, 'utf-8');
      const ap = detectAntiPatterns(text);
      apReports.push(`### ${path.basename(f)} — Anti-Patterns: ${ap.verdict} (${ap.totalHits} hits, ${ap.hitsPerKChar}/1Kchar)`);
      if (ap.tier2Hits + ap.tier3Hits > 0) apReports.push(formatAntiPatternReport(ap));
    }
    if (flags.json) {
      console.log(JSON.stringify({ ...combined, antiPatterns: apReports }, null, 2));
    } else {
      console.log(formatHumanReport(combined));
      console.log('\n---\n');
      console.log(apReports.join('\n\n'));
    }
  } else {
    console.log(flags.json ? JSON.stringify(combined, null, 2) : formatHumanReport(combined));
  }

  process.exit(overallVerdict === 'FAIL' ? 2 : overallVerdict === 'WARN' ? 1 : 0);
}

main().catch((e) => {
  console.error('Fatal:', e);
  process.exit(3);
});
