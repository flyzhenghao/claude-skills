// Domain Tier Classifier
// 基于 references/domain-tier-table.md 的 Tier A/B/C 三级分类

export type SourceTier = 'A' | 'B' | 'C' | '?';

const TIER_A_DOMAINS = new Set([
  // China
  'eol.cn', 'moe.gov.cn', 'mofcom.gov.cn', 'stats.gov.cn',
  'safe.gov.cn', 'chinatax.gov.cn', 'pbc.gov.cn', 'csrc.gov.cn',
  // NZ/AU
  'stats.govt.nz', 'employment.govt.nz', 'courtsofnz.govt.nz',
  'legislation.govt.nz', 'homeaffairs.gov.au', 'abs.gov.au',
  // North America
  'census.gov', 'bls.gov', 'sec.gov', 'statcan.gc.ca',
  // International
  'oecd.org', 'worldbank.org', 'imf.org', 'un.org', 'wto.org',
  // Academic
  'nature.com', 'science.org', 'arxiv.org', 'pubmed.ncbi.nlm.nih.gov',
  'nih.gov', 'frontiersin.org',
  // Top consulting
  'mckinsey.com', 'bcg.com', 'bain.com', 'deloitte.com',
  'pwc.com', 'ey.com', 'kpmg.com', 'accenture.com',
  'gartner.com', 'forrester.com', 'idc.com',
  'iresearch.cn', 'cnki.net',
]);

const TIER_B_DOMAINS = new Set([
  // International media
  'reuters.com', 'wsj.com', 'ft.com', 'bloomberg.com',
  'economist.com', 'nytimes.com', 'theguardian.com',
  'cnbc.com', 'forbes.com', 'techcrunch.com', 'wired.com',
  'arstechnica.com', 'theverge.com',
  // China media
  '36kr.com', 'huxiu.com', 'pingwest.com', 'geekpark.net',
  'caixin.com', 'yicai.com', 'nbd.com.cn', '21jingji.com',
  'tmtpost.com', 'lieyunwang.com', 'china-cbn.com',
  // Legal
  'dentons.com', 'dentons.co.nz', 'laneneave.co.nz',
  'wolterskluwer.com', 'lexisnexis.com', 'dlapiper.com',
  'harmans.co.nz', 'frontlinelaw.co.nz',
  // Industry
  'linkedin.com', 'coursera.org', 'icf.global', 'cdanz.org.nz',
  // Recruitment
  'liepin.com', 'zhaopin.com', '51job.com', 'glassdoor.com',
  'seek.co.nz', 'seek.com.au',
]);

const TIER_C_DOMAINS = new Set([
  // UGC
  'zhihu.com', 'weibo.com', 'xiaohongshu.com', 'douyin.com',
  'bilibili.com', 'medium.com', 'substack.com',
  'caifuhao.eastmoney.com', 'cngoesglobal.com',
  // Marketing/blog
  'dchbi.com', 'wescrm.com', 'growthhk.cn',
  'woshipm.com', 'digitaling.com',
  // Forums
  'reddit.com', 'stackoverflow.com', 'quora.com',
  // Wiki
  'wikipedia.org', 'baike.baidu.com', 'wiki.mbalib.com',
]);

const KNOWN_GROUNDING_REDIRECT = 'vertexaisearch.cloud.google.com';

export function classifyDomain(url: string): { tier: SourceTier; host: string; reason: string } {
  let host: string;
  try {
    host = new URL(url).hostname.toLowerCase();
  } catch {
    return { tier: '?', host: url, reason: 'Invalid URL' };
  }

  // Gemini grounding redirect — 必须解 redirect 才能评级
  if (host.includes(KNOWN_GROUNDING_REDIRECT)) {
    return { tier: '?', host, reason: 'Gemini grounding redirect, resolve first' };
  }

  // Tier A: gov/edu patterns
  if (/\.gov(\.[a-z]{2})?$/.test(host)) return { tier: 'A', host, reason: 'gov domain' };
  if (/\.edu(\.[a-z]{2})?$/.test(host)) return { tier: 'A', host, reason: 'edu domain' };
  if (/\.ac\.[a-z]{2}$/.test(host)) return { tier: 'A', host, reason: 'academic domain' };
  if (/^stats\./.test(host)) return { tier: 'A', host, reason: 'statistics domain' };
  if (/^(census|legislation|courts)\./.test(host)) return { tier: 'A', host, reason: 'official record' };

  // Lookup tables
  if (TIER_A_DOMAINS.has(host)) return { tier: 'A', host, reason: 'known A-tier' };
  for (const d of TIER_A_DOMAINS) if (host.endsWith('.' + d)) return { tier: 'A', host, reason: `subdomain of ${d}` };

  if (TIER_B_DOMAINS.has(host)) return { tier: 'B', host, reason: 'known B-tier' };
  for (const d of TIER_B_DOMAINS) if (host.endsWith('.' + d)) return { tier: 'B', host, reason: `subdomain of ${d}` };

  if (TIER_C_DOMAINS.has(host)) return { tier: 'C', host, reason: 'known C-tier' };
  for (const d of TIER_C_DOMAINS) if (host.endsWith('.' + d)) return { tier: 'C', host, reason: `subdomain of ${d}` };

  // Default to C (conservative)
  return { tier: 'C', host, reason: 'unknown domain, default C' };
}

export function isTierA(url: string): boolean { return classifyDomain(url).tier === 'A'; }
export function isTierAB(url: string): boolean {
  const t = classifyDomain(url).tier;
  return t === 'A' || t === 'B';
}
