# Deep Reading Analyst

> Deep critical analysis of long-form content — articles, conversation transcripts, and research reports — using 5 structured frameworks.

## What it does

对长文本进行批判性分析，输出结构化洞见。适用于：

- 观点文章 / 博客
- 对话转录（多人）
- 研究报告 / 论文
- 技术方案文档
- 商业分析

## 5 个分析框架

1. **Critical Thinking** — 证据与逻辑（论点、证据质量、谬误检测、隐含假设）
2. **First Principles** — 假设剥离（识别假设 → 质问 → 重新推导）
3. **Systems Thinking** — 系统视角（边界、反馈回路、延迟效应、杠杆点）
4. **Inversion** — 反转思考（目标/假设/因果/时间四类反转）
5. **SCQA** — 结构化拆解（Situation / Complication / Question / Answer）

## 2 级深度

| 级别 | 触发 | 框架数 | 输出 |
|------|------|--------|------|
| **Standard** | 默认 / ≤300 行 | 自动选 2-3 个最相关 | ~500 字分析 |
| **Deep** | `--depth deep` / >300 行 | 全部 5 个框架 | ~1500 字分析 |

## Quick Start

```bash
# 1. 安装到 ~/.claude/skills/
git clone https://github.com/flyzhenghao/claude-skills.git
cp -r claude-skills/skills/deep-reading-analyst ~/.claude/skills/

# 2. 在 Claude Code 中触发
# 任一关键词均可：
#   "深度分析 ./some-article.md"
#   "deep reading ./report.pdf"
#   "/deep-reading ./transcript.md"
#   "分析这篇文章的核心洞见"
```

## 参数

| 参数 | 值 | 默认 |
|------|---|------|
| `--depth` | `standard` / `deep` | `standard`（>300 行自动 deep） |
| `--framework` | `critical` / `first-principles` / `systems` / `inversion` / `scqa` | 自动选择 |
| `--output` | `inline` / `file` | `file` |
| `--no-idea` | flag | 不做 idea 检测 |

## 项目集成（可选）

若你的项目恰好有以下结构/命令，会自动联动；没有则跳过。

- `knowledge-base/` 目录 → 分析报告自动归档到 `knowledge-base/ai-generated/analysis/`
- `inbox/ideas/` 目录 → 检测到可行动想法时自动创建 idea 文件
- `/capture-topic` 命令 → 检测到内容素材时提示录入
- `/research-chain` 命令 → 涉及深度研究课题时提示启动

无以上基础设施：分析报告输出到当前目录。

## 文件结构

```
deep-reading-analyst/
├── SKILL.md              # Skill 定义（框架 + 参数）
├── REFERENCE.md          # 输出格式规范 + 框架选择指南
└── docs/
    └── execution-guide.md  # 执行步骤详解
```

完整规格见 [SKILL.md](./SKILL.md)。

## License

MIT
