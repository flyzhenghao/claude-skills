# Deep Reading Analyst — Reference

## 输出格式规范

### Frontmatter

```yaml
---
type: deep-reading-analysis
source: "[原文档路径]"
depth: standard|deep
frameworks: [使用的框架列表]
created: YYYY-MM-DD
subject: "[文档主题]"
tags: [analysis, deep-reading, ...]
---
```

### 报告结构

```markdown
# 深度阅读分析: [文档标题]

## 元信息
- 来源: [路径/URL]
- 类型: [文章/对话/报告/论文]
- 分析深度: Standard / Deep
- 框架: [使用的框架]

## 核心发现
[3-5 个 bullet points，每个 1-2 句]

## 框架分析
### [框架名称]
[分析内容]

## 综合洞见
[交叉印证后的深层发现]

## 盲点与局限
[作者/对话未覆盖的角度]

## 可行动建议
[基于分析的具体下一步]

## 检测到的素材/想法
[如果有，列出可孵化的 ideas]
```

## 框架选择指南

| 文档类型 | 推荐框架 (Standard) | Deep 时追加 |
|---------|---------------------|------------|
| 观点文章/博客 | Critical Thinking + SCQA | First Principles + Inversion |
| 对话转录 | Systems Thinking + First Principles | Critical Thinking + SCQA + Inversion |
| 研究报告 | Critical Thinking + Systems Thinking | First Principles + SCQA |
| 技术方案 | First Principles + Inversion | Systems Thinking + Critical Thinking |
| 商业分析 | SCQA + Systems Thinking | Inversion + Critical Thinking |
| 混合/不确定 | Critical Thinking + Systems Thinking | 按主体类型（>60%）补选，或全部 5 个 |
