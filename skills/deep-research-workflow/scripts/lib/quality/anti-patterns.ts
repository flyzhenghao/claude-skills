// Anti-Patterns Detector
// 基于 references/anti-patterns-dict.md 的 Tier 1-4 检测规则

export interface AntiPatternHit {
  tier: 1 | 2 | 3 | 4;
  pattern: string;
  matched: string;
  line: number;
  context: string;
  severity: 'warn' | 'reject';
}

// Tier 1: 禁用修饰词（warn）
const TIER_1_WORDS = [
  '工业化', '工业化的',
  '强有力', '强有力的',
  '全方位', '全方位的',
  '根本性', '根本性的',
  '体系化', '体系化的',
  '战略级', '战略级的',
  '颠覆性', '颠覆性的',
  '革命性', '革命性的',
  '划时代', '划时代的',
  '穿行', '跃迁', '着力', '助力', '拥抱', '锻造', '打磨', '重塑',
  '一定的', '较好的', '较为',
  '多维度', '全维度', '综合性', '立体的',
  // English equivalents
  'industrial-grade', 'robust', 'comprehensive', '360°',
  'fundamental', 'systematic', 'strategic-level',
  'disruptive', 'revolutionary', 'epoch-making', 'empower',
];

// Tier 2: 可执行性陷阱（reject 关键词组合）
const TIER_2_PHRASES = [
  '做好质量管控',
  '建立差异化优势',
  '持续学习迭代',
  '提升用户体验',
  '加强协同',
  '优化流程',
  '建立护城河',
  '形成正向循环',
  '占领心智',
  '做大做强',
  '推动落地',
  '保持高度警觉',
  '灵活应对',
];

// Tier 3: 数据陷阱
const TIER_3_REGEX = [
  { pattern: /\[推测\]/g, name: '推测标签' },
  { pattern: /vertexaisearch\.cloud\.google\.com\/grounding-api-redirect/g, name: 'Gemini grounding redirect' },
  { pattern: /(据估计|据说|通常认为|普遍认为|业内人士透露)(?![\s\S]{0,80}\[\d+\])/g, name: '无来源传闻' },
];

export interface AntiPatternReport {
  totalHits: number;
  tier1Hits: number;
  tier2Hits: number;
  tier3Hits: number;
  hitsPerKChar: number;
  hits: AntiPatternHit[];
  verdict: 'PASS' | 'WARN' | 'FAIL';
}

export function detectAntiPatterns(text: string): AntiPatternReport {
  const hits: AntiPatternHit[] = [];
  const lines = text.split('\n');

  // Tier 1
  lines.forEach((line, idx) => {
    TIER_1_WORDS.forEach((word) => {
      const regex = new RegExp(word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
      const matches = line.match(regex);
      if (matches) {
        matches.forEach((m) => hits.push({
          tier: 1,
          pattern: word,
          matched: m,
          line: idx + 1,
          context: line.trim().slice(0, 100),
          severity: 'warn',
        }));
      }
    });
  });

  // Tier 2
  lines.forEach((line, idx) => {
    TIER_2_PHRASES.forEach((phrase) => {
      if (line.includes(phrase)) {
        hits.push({
          tier: 2,
          pattern: phrase,
          matched: phrase,
          line: idx + 1,
          context: line.trim().slice(0, 100),
          severity: 'reject',
        });
      }
    });
  });

  // Tier 3
  lines.forEach((line, idx) => {
    TIER_3_REGEX.forEach(({ pattern, name }) => {
      const matches = line.match(pattern);
      if (matches) {
        matches.forEach((m) => hits.push({
          tier: 3,
          pattern: name,
          matched: m,
          line: idx + 1,
          context: line.trim().slice(0, 100),
          severity: 'reject',
        }));
      }
    });
  });

  const totalChars = text.length;
  const hitsPerKChar = totalChars > 0 ? (hits.length / totalChars) * 1000 : 0;

  const tier1Hits = hits.filter((h) => h.tier === 1).length;
  const tier2Hits = hits.filter((h) => h.tier === 2).length;
  const tier3Hits = hits.filter((h) => h.tier === 3).length;

  let verdict: AntiPatternReport['verdict'] = 'PASS';
  if (tier2Hits > 0 || tier3Hits > 0) verdict = 'FAIL';
  else if (hitsPerKChar > 5 || tier1Hits > 10) verdict = 'WARN';

  return {
    totalHits: hits.length,
    tier1Hits,
    tier2Hits,
    tier3Hits,
    hitsPerKChar: Number(hitsPerKChar.toFixed(2)),
    hits,
    verdict,
  };
}

export function formatAntiPatternReport(r: AntiPatternReport): string {
  const lines: string[] = [];
  lines.push(`## Anti-Patterns Report`);
  lines.push(`- **Verdict**: ${r.verdict}`);
  lines.push(`- **Total hits**: ${r.totalHits} (Tier 1: ${r.tier1Hits}, Tier 2: ${r.tier2Hits}, Tier 3: ${r.tier3Hits})`);
  lines.push(`- **Density**: ${r.hitsPerKChar} hits / 1000 chars`);
  lines.push(``);

  if (r.tier2Hits > 0) {
    lines.push(`### ❌ Tier 2 (Reject — 必须返工)`);
    r.hits.filter((h) => h.tier === 2).slice(0, 20).forEach((h) =>
      lines.push(`- L${h.line}: \`${h.matched}\` — ${h.context}`),
    );
    lines.push(``);
  }
  if (r.tier3Hits > 0) {
    lines.push(`### ❌ Tier 3 (Reject — 数据陷阱)`);
    r.hits.filter((h) => h.tier === 3).slice(0, 20).forEach((h) =>
      lines.push(`- L${h.line}: \`${h.pattern}\` matched "${h.matched}" — ${h.context}`),
    );
    lines.push(``);
  }
  if (r.tier1Hits > 0) {
    lines.push(`### ⚠️ Tier 1 (Warn — 修饰词，前 30 个)`);
    r.hits.filter((h) => h.tier === 1).slice(0, 30).forEach((h) =>
      lines.push(`- L${h.line}: \`${h.matched}\``),
    );
  }

  return lines.join('\n');
}
