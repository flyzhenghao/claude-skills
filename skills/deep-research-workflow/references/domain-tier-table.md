# Source Credibility Domain Tier Table

> 用于 Phase 2.5 critic 维度 4（Source Credibility）的自动评级。
> 域名→Tier 映射，可被 lessons-learned 自动扩充。
> 维护规则：新增前先在 anti-patterns / lessons-learned 中观察 ≥3 次。

---

## Tier A — 政府/官方/权威机构（最可信）

### 中国
- `*.gov.cn` （所有政府域名）
- `moe.gov.cn`（教育部）
- `eol.cn`（教育部直属）
- `mofcom.gov.cn`（商务部）
- `stats.gov.cn`（国家统计局）
- `safe.gov.cn`（外汇管理局）
- `chinatax.gov.cn`（国家税务总局）
- `pbc.gov.cn`（央行）
- `csrc.gov.cn`（证监会）

### 新西兰 / 澳大利亚
- `*.govt.nz`（NZ 政府）
- `stats.govt.nz`
- `employment.govt.nz`
- `courtsofnz.govt.nz`
- `legislation.govt.nz`
- `*.gov.au`（澳洲政府）
- `homeaffairs.gov.au`
- `abs.gov.au`（澳统计局）

### 北美
- `*.gov`（美政府）
- `census.gov`
- `bls.gov`（劳工统计局）
- `sec.gov`（SEC）
- `*.gc.ca`（加拿大政府）
- `statcan.gc.ca`

### 欧盟 / 国际
- `oecd.org`
- `worldbank.org`
- `imf.org`
- `un.org`
- `*.europa.eu`
- `wto.org`

### 学术 / 研究
- `*.edu`（美国大学）
- `*.edu.cn`（中国大学）
- `*.ac.nz`（NZ 大学）
- `*.ac.uk`（英国大学）
- `nature.com`
- `science.org`
- `arxiv.org`
- `pubmed.ncbi.nlm.nih.gov`
- `nih.gov`
- `frontiersin.org`（peer-reviewed）

### 顶级行业研究 / 咨询
- `mckinsey.com`
- `bcg.com`
- `bain.com`
- `deloitte.com`
- `pwc.com`
- `ey.com`
- `kpmg.com`
- `accenture.com`
- `gartner.com`
- `forrester.com`
- `idc.com`
- `iresearch.cn`（艾瑞咨询）
- `cnki.net`（中国知网）

---

## Tier B — 行业头部媒体 / 上市公司 / 行业研究

### 财经/科技媒体（国际）
- `reuters.com`
- `wsj.com`
- `ft.com`
- `bloomberg.com`
- `economist.com`
- `nytimes.com`
- `theguardian.com`
- `cnbc.com`
- `forbes.com`
- `techcrunch.com`
- `wired.com`
- `arstechnica.com`
- `theverge.com`

### 财经/科技媒体（中国）
- `36kr.com`（36 氪）
- `huxiu.com`（虎嗅）
- `pingwest.com`（PingWest 品玩）
- `geekpark.net`（极客公园）
- `sohu.com/business`
- `caixin.com`（财新）
- `yicai.com`（第一财经）
- `nbd.com.cn`（每日经济新闻）
- `21jingji.com`（21 经济报道）
- `china-cbn.com`（中国财经网）
- `tmtpost.com`（钛媒体）
- `lieyunwang.com`（猎云）

### 法律 / 专业服务
- `dentons.com` / `dentons.co.nz`
- `lanenneave.co.nz`
- `chapman tripp`
- `simpson grierson`
- `wolters kluwer`
- `lexisnexis.com`
- `dlapiper.com`
- `harmans.co.nz`
- `frontlinelaw.co.nz`

### 行业协会 / 认证
- `linkedin.com`（官方数据）
- `linkedin.com/business/`
- `coursera.org`
- `icf.global`（International Coach Federation）
- `cdanz.org.nz`（NZ 职业发展协会）

### 上市公司财报 / 投资者关系
- `*.investor.*` 子域名
- `seekingalpha.com`（机构观点）

### 招聘 / HR 行业
- `liepin.com`（猎聘）
- `zhaopin.com`（智联）
- `51job.com`
- `glassdoor.com`
- `seek.co.nz`
- `seek.com.au`

---

## Tier C — 自媒体 / UGC / 单一作者博客

### UGC 平台
- `zhihu.com`
- `weibo.com`
- `xiaohongshu.com`（小红书帖）
- `douyin.com`
- `bilibili.com`
- `*.medium.com`
- `*.substack.com`（除非作者是 A/B 级机构）
- `caifuhao.eastmoney.com`（东方财富号 = UGC）
- `cngoesglobal.com`

### 个人博客 / 营销号
- `dchbi.com` ⚠️（实测：易触发单源依赖陷阱）
- `wescrm.com`
- `growthhk.cn`
- `woshipm.com`（人人都是产品经理，部分 B 级）
- `digitaling.com`（数英网，部分 B 级）

### 论坛 / 问答
- `reddit.com`（除非引用 r/personalfinance 等高质量子版）
- `stackoverflow.com`（技术 OK，商业不 OK）
- `quora.com`

### 维基 / 用户编辑
- `wikipedia.org`
- `baike.baidu.com`
- `wiki.mbalib.com`

---

## 自动评级规则

```typescript
function classifyDomain(url: string): 'A' | 'B' | 'C' {
  const host = new URL(url).hostname.toLowerCase();

  // Tier A patterns
  if (/(\.gov(\.[a-z]{2})?(:|$|\/))/.test(host)) return 'A';
  if (/(\.edu(\.[a-z]{2})?(:|$|\/))/.test(host)) return 'A';
  if (/(\.ac\.[a-z]{2}(:|$|\/))/.test(host)) return 'A';
  if (/^(stats\.|census\.|legislation\.|courts)/.test(host)) return 'A';
  if (TIER_A_DOMAINS.includes(host)) return 'A';

  // Tier B patterns
  if (TIER_B_DOMAINS.some(d => host.endsWith(d))) return 'B';

  // Tier C patterns + everything else
  if (TIER_C_DOMAINS.some(d => host.endsWith(d))) return 'C';

  // 未知域名默认 C（保守）
  return 'C';
}
```

完整查询表：`scripts/lib/quality/source-tier.ts`（P3 实施）

---

## 特殊规则

### Gemini 间接链接
- `vertexaisearch.cloud.google.com/grounding-api-redirect/...` → 未知（必须解 redirect 到真实 URL 后再评级）
- 如果无法解 redirect → 标 `?` 并触发 Phase 2.6 cross-validation

### 子域名优先
- `careers.google.com` → A（继承 google.com）
- `blog.individual.com` → C（即使主域名是 A，blog 子域可能是 UGC）
- 公司官方 blog 通常是 B（如 `engineering.fb.com`）

### 时效性叠加
- A/B 级来源但日期 ≤2022 → 自动降一级
- C 级但日期 ≥2025 → 仍是 C（时效不能补可信度）

---

## 维护责任

每次 DR 完成后检查：
- 实际遇到的新域名（不在表中的）
- Critic 已评级的域名是否合理
- lessons-learned 中提到的"危险来源"是否更新到 Tier C

新增域名时遵循 anti-patterns-dict 的"≥3 次实战才入典"规则。

---

**版本**: v1.0
**初始化**: 2026-05-03
**下次更新**: 跑完 ≥3 个 DR 项目后审计
