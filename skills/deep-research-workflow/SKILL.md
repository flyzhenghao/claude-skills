---
name: deep-research-workflow
description: >
  深度研究工作流 v7.5 — 5-Tier 分层架构（T0 Spot Check / T1 Light / T2 Standard /
  T3 Deep / T4 Strategic）+ 横向 Quality Foundation Layer。
  Use when the user asks to research, investigate, evaluate, or compare topics in depth.
  Trigger words: "调研", "研究", "深度", "比较", "评估", "选型", "deep dive", "research",
  "evaluate", "compare". Covers: market research, competitor analysis, technology evaluation,
  regulatory/process investigation, industry trends, multi-criteria comparison of
  products/services/platforms, or any query requiring gathering and synthesizing information
  from multiple sources. Works for English and Chinese.
  Do NOT use for: single-fact lookups, reading one URL, code review, sprint retros,
  font/design choices, or tasks solvable with a quick web search.
version: 7.5.0
author: haozheng
created: 2026-02-06
last_updated: 2026-05-03
triggers:
  - "深度研究"
  - "deep research"
  - "批量研究"
  - "市场调研"
  - "竞品分析"
  - "competitor analysis"
  - "技术选型"
  - "tech evaluation"
  - "行业研究"
  - "industry research"
  - "调研"
  - "research workflow"
agents: [researcher, strategist, critic]
depends_on: ["critic:challenge"]
---

# Deep Research Workflow v7.5

> **双轴架构**：5 Tier 任务难度纵向分层 × Quality Foundation Layer 横向能力共享。
> 默认走 T2 Standard，根据 Phase 0 的 5 题决策树自动建议升降。

---

## 一、双轴架构

### 纵向：5 Tier（按任务难度）

| Tier | 用例 | 时间 | Anthropic Token | 何时用 |
|------|------|------|-----------------|--------|
| **T0 Spot Check** | 单点 fact-check | 1-2 min | ~3K | "Pickaxe 月费多少？" |
| **T1 Light** | 摸底类 | 5-10 min | ~15K | "竞品有哪几家？" |
| **T2 Standard** ⭐ | 选型/产品调研（默认）| 15-30 min | ~80K | "PDT 接 Mem0 选型" |
| **T3 Deep** | 客户报告/不可逆决策 | 45-90 min | ~250K | "客户教练新产品调研" |
| **T4 Strategic** | 战略级/HTML 演示 | 2-4h | ~600K-1M | "PDT 5 年商业化" |

### 横向：Quality Foundation Layer（所有 Tier 共享）

| Q | 能力 | 实现 | T0 | T1 | T2 | T3 | T4 |
|---|------|------|-----|-----|-----|-----|-----|
| Q1 | Anti-Patterns Dict | `references/anti-patterns-dict.md` + `lib/quality/anti-patterns.ts` | ❌ | ✅ | ✅ | ✅ | ✅ |
| Q2 | Source Validation | `scripts/validate-sources.ts` + `lib/quality/source-tier.ts` | light | ✅ | ✅ | ✅ | ✅ |
| Q3 | Lessons-Learned | `lessons-learned.md`（跨项目共享） | ❌ | read | r+w | r+w | r+w |
| Q4 | Format Contract | `dr-config.json` 字段（**T1+ 强制**） | ❌ | min | ✅ | ✅ | ✅ |
| Q5 | Token Budget Tracker | `lib/quality/token-budget.ts` | ❌ | ✅ | ✅ | ✅ | ✅ |
| Q6 | Midpoint Check | `scripts/midpoint-checker.ts`（P5）| ❌ | ❌ | ✅ | ✅ | ✅ |
| Q7 | Adversarial Loop | Phase 2.6 后 critic 二审 | ❌ | ❌ | ❌ | ✅ | ✅ |

---

## 二、Tier 决策树（Phase 0 强制）

5 题机械判断（详见 `references/tier-decision-tree.md`）：

```
Q1: 单点还是多角度？     单点→T0  多角度→Q2
Q2: 一次性还是要落盘？   一次性→T1  要落盘→Q3
Q3: 决策可逆？          可逆→T2  不可逆→Q4
Q4: 受众？              自用→T3  对外→Q5
Q5: 战略级 6+ 个月？    否→T3  是→T4
```

显式覆盖：用户说 "做个 T1/T2/T3/T4 调研" 时直接锁定，跳过决策树（仍记录用作 lessons）。

---

## 三、Tier × Phase 矩阵

| Phase | T0 | T1 | T2 | T3 | T4 |
|-------|-----|-----|-----|-----|-----|
| **0 Tier 选择** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **1 问题分解** | minimal | ✅ | ✅ | ✅ | ✅ |
| **1.5 Critic prompt** | ❌ | ❌ | haiku | opus | opus |
| **2 数据采集** | WebSearch×1 | WebSearch×3-5 | Gemini DR×4-6 | Gemini DR×6-9 | Multi-engine×8-10 |
| **2.4 Midpoint** | ❌ | ❌ | ✅ haiku | ✅ haiku | ✅ haiku |
| **2.5 Critic raw** | ❌ | ❌ | haiku | opus | opus |
| **2.6 Cross-Val** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **2.7 Outline refine** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **3 综合（Opus）** | ❌ | sonnet | opus 单 Pass | opus 单 Pass | opus Multi-Pass |
| **4 落地** | inline | ✅ | ✅ | ✅ | ✅ |
| **4.0 时效性摘要** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **4.5 HTML 报告** | ❌ | ❌ | ❌ | optional | ✅ |
| **4.6 Stakeholder review** | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 四、Quality Foundation Layer 详细规则

### Q1 — Anti-Patterns Dict（T1+ 强制）

**注入点**：
- Phase 1 生成 prompt 时：`anti_patterns` 字段引用 `references/anti-patterns-dict.md` Tier 1-3
- Phase 2.5 critic：自动跑 `lib/quality/anti-patterns.ts` 检测 + 命中数报告

**触发处理**：
- Tier 1 单个 → ack（Phase 2.7 改写）
- Tier 1 密度 >5/千字 → critic 标记，Gemini 改写整段
- Tier 2/3 任一 → reject，必须返工

### Q2 — Source Validation（所有 Tier）

**注入点**：
- Phase 2 末（数据采集后）自动跑 `scripts/validate-sources.ts`
- T0：仅检查域名 tier（不抽查 URL liveness）
- T1+：HEAD 请求抽查 ≤30 URL + 域名分级 + 重复来源检测

**触发处理**：
- URL pass rate <60% → 强制 Phase 2.6 cross-validation（即使 T2 也升级）
- 同域名引用 ≥3 次 → 标 single-source warning
- 同域名贡献 ≥40% → reject + 返工

```bash
# CLI 用法
npx tsx scripts/validate-sources.ts dr-raw/*.md --threshold 0.6 --max-urls 30 --anti-patterns
# Exit code: 0=PASS, 1=WARN, 2=FAIL
```

### Q3 — Lessons-Learned（跨项目共享）

**注入点**：
- Phase 1 启动时：grep `lessons-learned.md` 当前主题相关条目（关键词匹配）
- Phase 4 落地时：写入 1-3 条新 lessons（T2+）

**字段**：现象 / 根因 / 教训 / 应用规则 / 关键词

### Q4 — Format Contract（T1+ 强制）

`dr-config.json` 必填字段：
- audience（谁来读）
- purpose（决策依据/学习/执行指南）
- required_sections（章节列表）
- citation_style
- length_target

### Q5 — Token Budget Tracker（T1+）

**功能**：
- 每 Phase 完成时记录 input/output token 到 `meta/token-usage.jsonl`
- 累计超 80% 时弹警告 + 推荐降级路径
- 通过 `lib/quality/token-budget.ts` API 调用

### Q6 — Midpoint Check（T2+）

**触发**：Phase 2 期间，每完成 N=3 份 raw 报告
**执行**：haiku 扫描已完成报告核心结论的 inconsistency
**输出**：写入 `dr-config.json` 的 `known_inconsistencies` 字段，注入后续 prompt

### Q7 — Adversarial Loop（T3+）

**触发**：Phase 2.6 cross-validation 完成后
**执行**：critic 二审 cross-val 结果 vs 原报告，找"未被任何 cross-val 推翻的薄弱论断"
**输出**：交用户决定是否继续

---

## 五、Phase 详解（按 Tier 分支）

### Phase 0：Tier 选择（强制）

走 5 题决策树或接受用户显式 Tier。**锁定结果写入 `dr-config.json`**：

```json
{
  "tier": "T2",
  "format_contract": true,
  "midpoint_check": true,
  "cross_validation": false,
  "output_html": false,
  "token_budget": 80000
}
```

### Phase 0.5：DR 预算检查

同主题已有 ≥4 份 DR → 必须声明增量价值，否则不启动新 DR。

### Phase 1：问题分解

模板：
- T1：`templates/tasks-template-t1.json`（3-5 queries）
- T2：`templates/tasks-template-t2.json`（4-6 markets，**默认**）
- T3：`templates/tasks-template-t3.json`（6-9 markets + cross-val 字段）
- T4：`templates/tasks-template-t4.json`（8-10 markets + multi-engine + stakeholder map）

**强制规则**：
- `existing_knowledge` 不得为空数组
- T1+ 必须填 `format_contract`
- T3+ 必须填 `cross_validation_targets`（至少 3 个候选结论）
- T4 必须填 `stakeholders`（≥2）

### Phase 1.5：Critic Challenge prompt

调用 `/critic challenge`，输入：研究目标 + 子任务列表 + known_context
检查项（按 Tier 加严）：
1. 子任务 MECE？
2. 各 prompt 是否锚定了已知信息
3. 粒度是否合适（5-10 min/任务）
4. 是否有 P8 调研基准缺失 / P10 过度分解
5. （T3+）预声明 cross-validation 候选 ≥3 个

### Phase 2：数据采集（按 Tier 分支）

- **T0**：Claude 单 query WebSearch
- **T1**：3-5 个并发 WebSearch
- **T2/T3**：Gemini DR Chrome 模式（gemini-2.5-pro）
  ```bash
  npx tsx ~/.claude/skills/deep-research-workflow/scripts/gemini-deep-research.ts <prompts...>
  ```
- **T4**：每 market 由 Gemini DR + Researcher agent + WebSearch 三路并行

### Phase 2.4：Midpoint Check（T2+，自动）

监控 `dr-raw/` 完成数，每 3 份触发 haiku 扫矛盾。
输出写入 `dr-config.json` 的 `known_inconsistencies` 字段。
后续 prompt 自动注入"已发现矛盾：A 报告说 X，本研究需明确表态"。

### Phase 2.5：Critic Challenge raw（强制）

```bash
# 自动跑 source validation 作为 critic 输入
npx tsx ~/.claude/skills/deep-research-workflow/scripts/validate-sources.ts dr-raw/*.md --anti-patterns
```

然后 critic 6 维度审查：
1. 跨报告矛盾（已被 Q6 部分预防）
2. 好听不可执行建议（Q1 已自动检测，critic 二审）
3. 数据源可验证（Q2 已跑，critic 读结果）
4. Source Credibility A/B/C（Q2 已跑）
5. Anti-Hallucination
6. Timeliness

按 Tier 用不同模型：
- T2：haiku（机械检查）
- T3+：opus（判断 nuance）

### Phase 2.6：Cross-Validation（T3+ 强制）

对 Phase 1.5 预声明的 Top 3 结论做 WebSearch 反证 / 独立佐证：
- ✅ 多源佐证 / ⚠️ 矛盾 / ❌ 无法独立验证

### Phase 2.7：Outline Refinement（T3+）

基于 Phase 2 实际证据调整 outline：
- 增加/降权/重排
- 补 2-3 次定向 WebSearch（限 5min）
- 调整幅度 ≤50%

### Phase 3：综合分析

**Step 0**：原始报告核心结论摘录（standard+ 强制）
**Step 1**：综合（按 Tier）
- T1：sonnet 5 段
- T2/T3：opus 单 Pass 5 维度
- T4：opus Multi-Pass（2-3 个 subagent + UNION merge）

**Step 2**：偏离检查（T2+ 强制）
**Step 3**：综合报告落盘到 `deep-research-results/<date>-<topic>-synthesis-report.md`

### Phase 4：研究落地（强制）

**4.0 时效性摘要**（T2+ 强制开头）：
```markdown
> 时效性: ✅/⚠️/❌
> 来源日期分布: 2025-2026: N% | 2024: N% | ≤2023: N%
> 执行模式: Chrome (Gemini 2.5 Pro) / API (Flash)
> 引用透明度: ✅ 原始 URL 可读 / ⚠️ redirect URL 不可读
> 核心结论支撑年份: [Top 3 结论支撑来源最旧年份]
> Source Validation: <verdict from validate-sources.ts>
```

**4.1 提取 Action Items**（六字段）
**4.2 写入目标项目 backlog.md**
**4.3 追加 research-index.md**
**4.4 写入 lessons-learned.md**（T2+ 强制 1-3 条）
**4.5 McKinsey HTML 报告**（T4 强制，T3 optional）
**4.6 Stakeholder Review Loop**（T4 强制）

---

## 六、Compaction 恢复检查清单

| 检查项 | 验证方法 |
|--------|---------|
| 当前 Tier？ | 读 `dr-config.json` 的 `tier` 字段 |
| Phase 1.5 challenge 做了吗？ | 搜索对话或文件 |
| Phase 2.4 Midpoint 触发过吗？ | 读 `dr-config.json` 的 `known_inconsistencies` |
| Phase 2.5 critic 做了吗？ | 搜索原始报告 challenge 输出 |
| Phase 2.6 cross-val 做了吗？ | T3+ 必查 |
| Source validation 跑了吗？ | 检查 `validate-sources.ts` 输出 |
| 综合报告落盘了吗？ | `ls deep-research-results/*-synthesis-report.md` |
| Token 用了多少？ | 读 `meta/token-usage.jsonl` |
| Lessons 写了吗？ | T2+ Phase 4 末检查 `lessons-learned.md` 是否新增条目 |

**口诀**: 提交前 challenge prompt，并发中 midpoint 扫矛盾，综合前 challenge 报告，三关都过才出报告。

---

## 七、Token 平衡策略

### 同 Tier 内"质量手段降级"
T2 默认全开 Q1-Q6，但提供 `--lite` flag 跳过 Q6 midpoint：
- 适用：4 个 markets 且彼此弱相关时

### 自动降级触发（保护 Token 预算）
累计超 80% 时弹警告：
- T4 → T3：跳过 Multi-Pass
- T3 → T2：跳过 Phase 2.6 cross-val
- T2 → T1：跳过 Gemini DR 改 WebSearch

### 禁止降级
- T3+ 涉及客户交付（已签合同/已承诺）→ 禁降到 T2
- T4 涉及法律/合规（合同/监管）→ 禁降到 T3

### 模型分工（Token 性价比）
| 任务 | 模型 | 理由 |
|------|------|------|
| Phase 1 分解 | Sonnet | 中等推理够，Opus 浪费 |
| Phase 1.5 critic | Haiku（T2）/ Opus（T3+）| T2 机械检查，T3 要 nuance |
| Phase 2 数据 | Gemini DR | 不消耗 Anthropic |
| Phase 2.4 midpoint | Haiku | 仅 inconsistency 扫描 |
| Phase 2.5 critic raw | Haiku（T2）/ Opus（T3+）| 同上 |
| Phase 2.6 cross-val | Sonnet + WebSearch | 综合搜索结果，Opus 大材小用 |
| **Phase 3 synthesis** | **Opus** | 核心智力输出，省不得 |
| Phase 4 落地 | Sonnet | 模板填充 |

---

## 八、降级链（Gemini → API → WebSearch）

执行优先级（依次尝试，不得跳步）：

1. **模式 D (Chrome + Playwright)** [默认] — Gemini 2.5 Pro，质量最高
2. **模式 E (Interactions API)** [降级] — Gemini 2.0 Flash preview，质量次之
3. **明确告知用户** — 失败时询问是否用 WebSearch 替代

---

## 九、文件结构

```
~/.claude/skills/deep-research-workflow/
├── SKILL.md                              # v7.5 双轴架构（本文件）
├── lessons-learned.md                    # 跨项目沉淀（Q3）
├── research-index.md                     # DR 索引
├── references/
│   ├── setup-and-config.md
│   ├── anti-patterns-dict.md             # Q1 词典
│   ├── tier-decision-tree.md             # Phase 0 5 题决策树
│   └── domain-tier-table.md              # Q2 域名分级表
├── templates/
│   ├── tasks-template-t1.json            # T1 Light
│   ├── tasks-template-t2.json            # T2 Standard（默认）
│   ├── tasks-template-t3.json            # T3 Deep（含 cross-val）
│   ├── tasks-template-t4.json            # T4 Strategic（含 multi-engine）
│   ├── tasks-template.json               # 兼容旧版（指向 t2）
│   └── mckinsey-report-template.html     # T4 用
├── scripts/
│   ├── gemini-deep-research.ts           # Phase 2 主入口
│   ├── gemini-dr-extract.ts              # 提取报告
│   ├── gemini-dr-check.ts                # 状态检查
│   ├── gemini-dr-api.ts                  # API 降级
│   ├── validate-sources.ts               # Q2 主入口（CLI）
│   └── lib/
│       ├── gemini/                        # 已有
│       └── quality/                       # 新增（v7.5）
│           ├── anti-patterns.ts           # Q1
│           ├── source-tier.ts             # Q2 域名分类
│           └── token-budget.ts            # Q5
└── docs/
    └── design-decisions.md
```

---

## 十、快速开始

```bash
# 默认 T2（4 markets 标准调研）
cp ~/.claude/skills/deep-research-workflow/templates/tasks-template-t2.json ./tasks.json
# 编辑 tasks.json...
npx tsx ~/.claude/skills/deep-research-workflow/scripts/gemini-deep-research.ts \
  prompts/Q1.md prompts/Q2.md prompts/Q3.md prompts/Q4.md

# Phase 2 完成后跑 source validation
npx tsx ~/.claude/skills/deep-research-workflow/scripts/validate-sources.ts \
  dr-raw/*.md --anti-patterns
```

---

## 更新日志

### v7.5.0 (2026-05-03) — 双轴分层架构
- **5 Tier**（T0/T1/T2/T3/T4）按任务难度纵向分层，token 预算明确
- **Quality Foundation Layer**（Q1-Q7）横向能力共享
- **新增 references**: anti-patterns-dict.md / tier-decision-tree.md / domain-tier-table.md
- **新增 lessons-learned.md** 跨项目共享教训库（基于实战项目反思初始化 7 条）
- **新增 4 个 tier 模板**: tasks-template-t1/t2/t3/t4.json
- **新增 quality lib**: anti-patterns.ts / source-tier.ts / token-budget.ts
- **新增 validate-sources.ts** CLI 自动 URL 抽查 + 域名分级 + 重复来源检测
- **强制规则升级**：T1+ 必填 format_contract，T3+ 必填 cross_validation_targets
- **Token 平衡**：同 Tier 内 --lite flag + 自动降级触发 + 模型分工矩阵
- **根因**: 实战项目发现 Q4/Q5/Q8 单源依赖 + URL 失效 + 大量空话；老 v7.4 4 档划分按 Phase 数而非任务难度

### v7.4.0 (2026-04-30)
Gemini Web UI 适配 + Multi-Account 支持。详见 git history。

### v7.3.0 (2026-04-05)
Phase 4.5 McKinsey HTML 模板重建。详见 git history。

### v7.2.x (2026-04-02 ~ 2026-04-03)
Chrome 优先 + 时效性检查。详见 git history。

### v7.0 ~ v7.1 (2026-03-27 ~ 2026-04-01)
模式 E API 回归 + Phase 0 lock 持久化。详见 git history。

### v6.0 (2026-03-26)
Phase 0 深度模式 + Phase 2.5 增强 + Phase 2.6 Cross-Validation。详见 git history。

### v5.x (2026-03-07 ~ 2026-03-14)
Auto-poll + research-index + 落地率追踪。详见 git history。

### v4 及更早
模式 D (Chrome + Playwright) 引入。详见 git history。

---

**作者**: haozheng
**当前版本**: v7.5.0 (2026-05-03)
**核心理念**: 任务难度决定 Tier，Quality Layer 决定基线，Token 预算决定降级
