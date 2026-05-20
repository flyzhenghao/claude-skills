---
name: deep-reading-analyst
description: Deep critical analysis of long-form content — articles, conversation transcripts, and research reports — using structured frameworks to extract insights, detect patterns, and link findings to the knowledge base. Use when analyzing articles in depth, reviewing research, extracting key points from long conversations, or wanting structured analytical output. Trigger phrases: 深度阅读, 深入分析, /deep-reading, analyze this article, 帮我分析这篇, extract insights, critical analysis.
---

# Deep Reading Analyst

**一句话定位**: 对长文本（文章、对话转录、研究报告）进行深度批判性分析，输出结构化洞见。在有知识库的项目中自动联动写入和 idea 检测。

## 触发条件

**使用**: "深度分析 [文档]" / "deep reading [path]" / "分析这篇文章的核心洞见" / `/deep-reading [path]`

**不用**: 代码质量检查 → `/critic` | 方案评审 → `/peer-review` | 简单摘要 → 直接做

## 2 级深度

| 级别 | 触发 | 框架数 | 输出 |
|------|------|--------|------|
| **Standard** | 默认 / ≤300 行 | 自动选 2-3 个最相关框架 | ~500 字分析 |
| **Deep** | `--depth deep` / >300 行 / 用户指定 | 全部 5 个框架 | ~1500 字分析 |

## 5 个分析框架

### 1. Critical Thinking — 证据与逻辑

- 核心论点是什么？用一句话概括
- 证据类型：数据/案例/类比/权威引用/个人经验？
- 证据质量：可验证？样本量？是否 cherry-picking？
- 逻辑链：前提→推理→结论是否完整？有无跳跃？
- 常见谬误检测：稻草人、滑坡、虚假二分、诉诸权威、确认偏误
- 未说出的假设：作者认为什么是"理所当然"的？

### 2. First Principles — 假设剥离

- 列出所有隐含假设（≥3 个）
- 逐个质问：这个假设在什么条件下不成立？
- 剥离假设后，基本事实是什么？
- 从基本事实重新推导，结论是否改变？
- 哪些假设最脆弱？哪些最坚固？

### 3. Systems Thinking — 系统视角

- 识别系统边界：讨论的是哪个系统？
- 关键组件及其关系（画出 2-3 个核心关系）
- 反馈回路：正反馈（加速）和负反馈（稳定）
- 延迟效应：哪些影响不会立即显现？
- 杠杆点：改变哪个环节影响最大？
- 涌现属性：整体有什么部分没有的特征？

### 4. Inversion — 反转思考

- 目标反转：如果想让这件事失败，该怎么做？
- 假设反转：如果核心假设的反面为真呢？
- 因果反转：因果关系是否可能是反的？
- 时间反转：从终局回看，哪些步骤是关键的？
- 谁会反对这个观点？最强的反论是什么？

### 5. SCQA — 结构化拆解

- **S**ituation（情境）: 背景和现状是什么？
- **C**omplication（冲突）: 出了什么问题？为什么现状不可持续？
- **Q**uestion（问题）: 核心问题是什么？
- **A**nswer（答案）: 作者给出的解答是什么？是否充分？

## 执行流程

```
Step 1: 预扫描 — 判断文档类型、长度、语言 → 自动选择深度和框架
Step 2: 框架分析 — 按选定框架逐一分析
Step 3: 综合 — 交叉印证框架结果，提炼核心洞见
Step 4: 输出 — 结构化报告 + 项目集成（如有知识库则写入/idea 检测）
```

**详细执行步骤**: 见 `docs/execution-guide.md`

## 项目集成（可选 — 仅在检测到对应基础设施时启用）

> 本 skill 默认输出到当前目录。如果你的项目恰好有以下结构/命令，会自动联动；没有则跳过，**不需要手动配置**。

| 联动 | 触发条件 | 行为 |
|------|---------|------|
| **写入知识库** | 项目根有 `knowledge-base/` 目录 | 分析报告存入 `knowledge-base/ai-generated/analysis/`（或 `knowledge/analysis/`），不污染用户原创主题目录 |
| **Idea 路由** | 项目根有 `inbox/ideas/` 目录 | 分析中发现可行动想法 → 创建 idea 文件 |
| **内容素材** | 存在 `/capture-topic` 命令 | 检测到内容价值 → 提示用户录入 |
| **Research Chain** | 存在 `/research-chain` 命令 | 涉及深度研究课题 → 提示启动 |

**默认行为（无以上基础设施时）**：分析报告输出到 stdout 或当前工作目录下的 `YYYY-MM-DD-[关键词]-分析.md`。

## 输出格式

> 📖 See [REFERENCE.md](./REFERENCE.md) for full output format spec (frontmatter + report structure) and framework selection guide by document type.

## 参数

| 参数 | 值 | 默认 |
|------|---|------|
| `--depth` | `standard` / `deep` | `standard`（>300 行自动 deep） |
| `--framework` | `critical` / `first-principles` / `systems` / `inversion` / `scqa` | 自动选择 |
| `--output` | `inline` / `file` | `file`（独立分析文件） |
| `--no-idea` | flag | 不做 idea 检测 |

## 相关（可选生态联动）

以下 skill/命令如存在则自动联动，无则忽略：

- `process-inbox` — idea 检测逻辑复用
- `content-workflow` — 分析报告可作为内容素材
- `knowledge-retrieval` — 检索相关历史分析
- `/critic challenge` — 技术方案质量检查（不同用途）

## Metadata
- **版本**: v1.0.0
- **修改日期**: 2026-03-03

## Known Failures & Fixes

| 日期 | 症状 | 根因 | 修复 | 版本 |
|------|------|------|------|------|
