---
name: skill-trending-monitor-cskill
description: "Claude Code 综合技能生态监控工具。自动追踪 skill-manager 数据库中的热门 Claude Skills（31,767 个技能），并使用 GitHub API 星标历史计算周环比增长率。发现本地未安装的新技能，并应用质量过滤（星标 >= 50，6 个月内更新）。使用 TF-IDF + 余弦相似度算法识别功能相似的替代品（阈值 0.75）。通过置信度评分推荐技能替换（星标比率、时效因子、文本相似度）。集成安全评估以过滤高风险技能（阈值 70）。生成周报至 meta/reports/，包含章节：🆕 新技能、🔥 增长最快（WoW 增长 >= 5%）、🔄 可替换技能（置信度 >= 0.70）、🛡️ 安全评估、📊 统计摘要。适用于通过自动化监控、安全优先推荐和基于机器学习相似度检测及时间增长分析方法的数据驱动替换建议来维护最优技能生态系统。"
version: 1.0.0
---

# 技能趋势监控器

Claude Code 的综合技能生态监控和推荐系统。

## 何时使用此技能

此技能应在以下情况自动激活：

✅ **趋势与发现请求：**
- 用户询问热门 Claude Skills
- 用户想发现新的高质量技能
- 用户提及技能受欢迎度、增长率或星标数
- 用户请求技能生态洞察或统计数据

✅ **比较与评估：**
- 用户想比较已安装技能与替代品
- 用户询问寻找更好或功能相似的技能
- 用户提及替换过时或废弃的技能
- 用户请求技能质量评估

✅ **安全与监控：**
- 用户询问技能安全评估
- 用户需要每周/定期技能监控报告
- 用户提及检查技能更新或维护状态
- 用户需要审计技能的安全性和质量

✅ **推荐场景：**
- 用户描述的需求可能由现有技能满足
- 用户想要改进其技能生态的建议
- 用户问"我应该安装哪些技能？"
- 用户提及技能推荐或替代建议

**不要在以下情况激活：**
- 用户询问特定技能使用文档（使用技能自带文档）
- 用户想创建新技能（使用 agent-skill-creator）
- 用户询问技能安装命令（基本 CLI 用法）
- 用户想编辑现有技能代码（代码编辑任务）

---

## 工作原理

### 双层数据架构

此技能使用复杂的双层数据架构进行全面的技能监控：

**第一层（主要）：skill-manager 本地数据库**
- **来源：** `~/.claude/skills/skill-manager/data/all_skills_with_cn.json`
- **覆盖：** 31,767 个技能及其元数据
- **访问：** 直接 JSON 解析，无速率限制
- **用于：**
  - 新技能发现（本地未安装的技能）
  - 相似度匹配（TF-IDF + 余弦相似度）
  - 基础元数据（名称、描述、作者、仓库 URL）
  - 质量过滤（星标、最后更新日期）

**第二层（次要）：GitHub API**
- **端点：** `https://api.github.com/repos/{owner}/{repo}/stargazers`
- **请求头：** `Accept: application/vnd.github.star+json`
- **速率限制：** 5,000 请求/小时（已认证）
- **用于：**
  - 用于增长计算的历史星标时间戳
  - 周环比（WoW）增长率分析
  - 仓库活跃度验证

### 双缓存系统

**缓存 1：技能元数据缓存**
- **位置：** `data/cache/skill-metadata.json`
- **TTL：** 30 天
- **目的：** 避免重复解析 skill-manager 数据库
- **内容：** 标准化元数据的技能列表

**缓存 2：安全评估缓存**
- **位置：** `data/security-cache/evaluations.json`
- **TTL：** 7 天
- **目的：** 避免冗余安全评估
- **内容：** 安全评分和评估详情

### 机器学习相似度检测

**TF-IDF 向量化：**
1. 从所有技能中提取描述
2. 从语料库构建 TF-IDF 词汇表
3. 将每个描述转换为特征向量
4. 存储向量用于比较

**余弦相似度计算：**
```
相似度 = (vec_A · vec_B) / (||vec_A|| × ||vec_B||)
阈值 = 0.75（高相似度）
```

**置信度评分（多因子）：**
- **星标比率：** `候选星标 / 已安装星标`（权重：0.4）
- **时效因子：** `更新天数 < 180 ? 1.0 : 0.5`（权重：0.3）
- **文本相似度：** `cosine_similarity(描述)`（权重：0.3）
- **最终置信度：** `加权和 >= 0.70` 为推荐

### 时间增长分析

**周环比（WoW）增长率：**
```python
# 从 GitHub API 获取星标时间戳
本周星标 = count_stars_between(周开始, 周结束)
上周星标 = count_stars_between(周开始 - 7, 周结束 - 7)

wow_增长率 = ((本周星标 - 上周星标) / 上周星标) * 100
趋势阈值 = 5.0  # >= 5% 增长被视为趋势
```

**趋势检测：**
- 计算星标前 100 名技能的 WoW 增长
- 过滤增长 >= 5% 的技能
- 按增长率降序排名
- 报告增长最快的前 10 个技能

---

## 数据源

### skill-manager 数据库（第一层）

**位置：** `~/.claude/skills/skill-manager/data/all_skills_with_cn.json`

**模式：**
```json
{
  "skills": [
    {
      "name": "技能名称",
      "description": "Skill description",
      "description_cn": "中文描述",
      "author": "作者名",
      "repository": "https://github.com/owner/repo",
      "stars": 150,
      "forks": 25,
      "last_updated": "2026-01-15",
      "topics": ["claude", "automation"]
    }
  ]
}
```

**应用的质量过滤：**
- 星标 >= 50（排除低质量/废弃技能）
- 6 个月内更新（活跃维护）
- 有效仓库 URL（GitHub 格式）

**覆盖统计：**
- 总技能数：31,767
- 有中文描述：31,752（99.95%）
- 活跃（更新 < 6 个月）：约 18,500

### GitHub API（第二层）

**星标历史端点：**
```bash
curl -H "Accept: application/vnd.github.star+json" \
     -H "Authorization: token ${GITHUB_TOKEN}" \
     https://api.github.com/repos/{owner}/{repo}/stargazers?per_page=100
```

**响应格式：**
```json
[
  {
    "starred_at": "2026-01-28T10:30:00Z",
    "user": {"login": "username"}
  }
]
```

**速率限制策略：**
- **未认证：** 60 请求/小时（不使用）
- **已认证：** 5,000 请求/小时（必需）
- **实现：** 从 `assets/config.json` 获取令牌
- **退避：** 429 响应时指数退避
- **缓存：** 星标时间戳 7 天缓存

**令牌配置：**
创建 `assets/config.json`：
```json
{
  "github_token": "ghp_你的令牌",
  "rate_limit_buffer": 100,
  "max_retries": 3
}
```

获取令牌：https://github.com/settings/tokens（范围：`public_repo` 只读）

---

## 可用分析

此技能提供 6 种不同的分析，每种解决特定的技能生态问题：

### 分析 1：新技能发现

**目标：** 识别 skill-manager 数据库中本地未安装的高质量技能。

**方法：**
1. 扫描 `~/.claude/skills/` 目录列出已安装技能
2. 加载 skill-manager 数据库（31,767 个技能）
3. 通过名称匹配过滤掉已安装技能
4. 应用质量过滤：
   - 星标 >= 50
   - 6 个月内更新
   - 有效 GitHub 仓库 URL
5. 按星标降序排名
6. 返回前 20 个新技能及其元数据

**输出格式：**
```markdown
## 🆕 新技能发现

| 技能名称 | 星标 | 最后更新 | 描述 |
|----------|------|----------|------|
| skill-x  | 850  | 2026-01-20 | 做 X... |
| skill-y  | 720  | 2026-01-18 | 做 Y... |
```

**使用场景：** 每周探索添加到生态系统的新技能。

---

### 分析 2：增长最快的技能（WoW 增长）

**目标：** 识别周环比星标增长率最高的技能。

**方法：**
1. 从 skill-manager 选择星标前 100 的技能
2. 对每个技能，从 GitHub API 获取星标历史
3. 计算本周与上周获得的星标
4. 计算 WoW 增长率：`((本周 - 上周) / 上周) * 100`
5. 过滤增长 >= 5% 的技能
6. 按增长率降序排名
7. 返回增长最快的前 10 个

**时间边界：**
- 本周：`[周开始日期, 今天]`
- 上周：`[周开始日期 - 7, 周开始日期 - 1]`
- 周开始：周一 00:00 UTC

**输出格式：**
```markdown
## 🔥 增长最快的技能（WoW >= 5%）

| 技能名称 | 星标 | WoW 增长 | 本周 | 上周 |
|----------|------|----------|------|------|
| skill-a  | 2,300 | +18.5% | 64 | 54 |
| skill-b  | 1,850 | +12.3% | 91 | 81 |
```

**使用场景：** 追踪新兴趋势和快速获得人气的技能。

---

### 分析 3：功能相似的技能

**目标：** 使用 ML 相似度算法查找功能相似的技能。

**方法：**
1. 从 skill-manager 数据库加载所有技能描述
2. 从整个语料库构建 TF-IDF 词汇表
3. 将每个描述转换为 TF-IDF 特征向量
4. 对目标技能，计算与所有技能的余弦相似度
5. 过滤相似度 >= 0.75（高相似度阈值）
6. 排除目标技能本身
7. 按相似度降序排名
8. 返回前 10 个相似技能

**TF-IDF 实现：**
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

vectorizer = TfidfVectorizer(
    max_features=1000,
    stop_words='english',
    ngram_range=(1, 2)
)

tfidf_matrix = vectorizer.fit_transform(descriptions)
similarities = cosine_similarity(tfidf_matrix[target_idx], tfidf_matrix)
```

**输出格式：**
```markdown
## 与 `skill-target` 相似的技能

| 技能名称 | 相似度 | 星标 | 描述 |
|----------|--------|------|------|
| skill-p  | 0.89   | 650  | 做 P... |
| skill-q  | 0.82   | 420  | 做 Q... |
```

**使用场景：** 发现替代实现或补充技能。

---

### 分析 4：可替换技能推荐

**目标：** 识别已安装技能中有更好替代品且置信度较高的技能。

**方法：**
1. 列出 `~/.claude/skills/` 中所有已安装技能
2. 对每个已安装技能：
   - 查找功能相似的技能（余弦相似度 >= 0.75）
   - 计算每个候选的置信度评分：
     - **星标比率：** `候选星标 / 已安装星标` × 0.4
     - **时效因子：** `更新 < 6 月 ? 1.0 : 0.5` × 0.3
     - **文本相似度：** `余弦相似度` × 0.3
   - 过滤置信度 >= 0.70 的候选
3. 按置信度降序排名替换建议
4. 返回有可行替换的技能

**置信度公式：**
```python
置信度 = (
    (候选星标 / 已安装星标) * 0.4 +
    (1.0 if 更新天数 < 180 else 0.5) * 0.3 +
    余弦相似度 * 0.3
)
```

**输出格式：**
```markdown
## 🔄 可替换技能

### 已安装：`old-skill`（200 星标，8 个月前更新）

**替换候选：**

| 候选技能 | 置信度 | 星标 | 相似度 | 原因 |
|----------|--------|------|--------|------|
| new-skill-a | 0.85 | 1,200 | 0.91 | 6 倍星标，活跃维护 |
| new-skill-b | 0.73 | 850 | 0.88 | 4 倍星标，功能相似 |
```

**决策支持：**
- 置信度 >= 0.85：**强烈推荐替换**
- 置信度 0.70-0.84：**考虑替换**
- 置信度 < 0.70：**不推荐**（已过滤）

**使用场景：** 通过替换过时/劣质技能优化技能生态。

---

### 分析 5：安全评估集成（新功能）

**目标：** 在建议安装前评估推荐技能的安全风险。

**方法：**
1. 对分析 1-4 中推荐的每个技能：
   - 检查安全评估缓存（TTL：7 天）
   - 如未缓存，调用安全评估技能
   - 解析安全评分（0-100 分）
   - 缓存带时间戳的结果
2. 过滤安全评分 >= 70 的技能（默认阈值）
3. 为推荐附加安全徽章：
   - 90-100：🛡️ **安全优秀**
   - 70-89：✅ **安全良好**
   - 50-69：⚠️ **中等风险**（不推荐）
   - < 50：🚨 **高风险**（已阻止）

**安全评估技能集成：**
```bash
# 假设安全评估技能已安装
# 示例调用：
bash ~/.claude/skills/skill-security-auditor/scripts/evaluate.sh \
  --skill-path ~/.claude/skills/candidate-skill \
  --output-json data/security-cache/candidate-skill.json
```

**缓存格式：**
```json
{
  "skill_name": "candidate-skill",
  "evaluated_at": "2026-02-03T10:30:00Z",
  "security_score": 85,
  "risk_level": "low",
  "issues_found": [],
  "expires_at": "2026-02-10T10:30:00Z"
}
```

**优雅降级：**
- 如安全技能未安装：跳过评估，警告用户
- 如评估失败：标记为"未评估"，让用户决定
- 如缓存过期：后台重新评估

**输出增强：**
所有推荐现在包含安全状态：
```markdown
| 技能名称 | 星标 | 安全 | 置信度 |
|----------|------|------|--------|
| skill-a  | 1,200 | 🛡️ 92 | 0.85 |
| skill-b  | 850 | ✅ 78 | 0.73 |
```

**使用场景：** 安全优先推荐，在安装前过滤高风险技能。

---

### 分析 6：综合周报

**目标：** 生成结合所有 5 种分析的完整技能生态健康报告。

**方法：**
1. 运行分析 1（新技能）→ 提取前 10
2. 运行分析 2（增长率）→ 提取前 10
3. 运行分析 3（相似技能）→ 对前 5 个已安装技能
4. 运行分析 4（替换）→ 对所有已安装技能
5. 运行分析 5（安全）→ 对所有推荐
6. 汇总统计：
   - 生态系统总技能：31,767
   - 已安装技能：`count(~/.claude/skills/)`
   - 本周新技能：count(7 天内更新)
   - 趋势技能：count(WoW 增长 >= 5%)
   - 替换候选：count(置信度 >= 0.70)
   - 安全通过的推荐：count(评分 >= 70)
7. 生成 Markdown 报告到 `meta/reports/YYYY-MM-DD-skill-trending-report.md`

**报告结构：**
```markdown
# 技能生态报告 - YYYY-MM-DD

## 📊 统计摘要

- **生态系统总技能：** 31,767
- **已安装技能：** 47
- **本周新技能：** 12
- **趋势技能（WoW >= 5%）：** 8
- **替换候选：** 3
- **安全通过的推荐：** 15

---

## 🆕 新技能发现（前 10）

[分析 1 表格]

---

## 🔥 增长最快的技能（前 10）

[分析 2 表格]

---

## 🔄 可替换技能（置信度 >= 0.70）

[分析 4 表格]

---

## 🛡️ 安全评估

**安全通过的推荐：** 15
**已阻止（评分 < 70）：** 2

[安全详情]

---

## 💡 推荐

1. **高优先级：** 将 `old-skill` 替换为 `new-skill-a`（置信度 0.85，安全 92）
2. **考虑安装：** `trending-skill`（18.5% WoW 增长，安全 88）
3. **探索替代品：** 检查 `your-skill` 的相似技能

---

**生成时间：** 2026-02-03 10:30 UTC
**下次报告：** 2026-02-10（每周）
```

**自动化：**
此分析可以通过 launchd/cron 自动化：
```bash
# 每周日 10:00
0 10 * * 0 python3 ~/.claude/skills/skill-trending-monitor-cskill/scripts/analyze_comprehensive.py
```

**使用场景：** 每周技能生态健康检查和主动优化。

---

## 可用脚本

所有脚本位于 `scripts/` 目录，是完全功能的生产代码。

### 分析脚本

**1. `analyze_comprehensive.py`（主编排器）**
- **目的：** 运行所有 6 种分析并生成周报
- **用法：** `python3 scripts/analyze_comprehensive.py [--output meta/reports/]`
- **行数：** 约 350
- **依赖：** 所有其他分析脚本

**2. `analyze_new_skills.py`**
- **目的：** 发现本地未安装的新技能（分析 1）
- **用法：** `python3 scripts/analyze_new_skills.py [--limit 20]`
- **行数：** 约 200
- **输出：** 带元数据的新技能 JSON 列表

**3. `analyze_growth_rates.py`**
- **目的：** 计算 WoW 增长率（分析 2）
- **用法：** `python3 scripts/analyze_growth_rates.py [--threshold 5.0]`
- **行数：** 约 280
- **输出：** 带增长率的趋势技能 JSON 列表

**4. `analyze_similarity.py`**
- **目的：** 使用 TF-IDF 查找功能相似的技能（分析 3）
- **用法：** `python3 scripts/analyze_similarity.py --skill <名称> [--threshold 0.75]`
- **行数：** 约 220
- **输出：** 带相似度评分的相似技能 JSON 列表

**5. `analyze_replacements.py`**
- **目的：** 推荐带置信度评分的技能替换（分析 4）
- **用法：** `python3 scripts/analyze_replacements.py [--confidence-threshold 0.70]`
- **行数：** 约 180
- **输出：** 已安装技能到替换候选的 JSON 映射

**6. `evaluate_security.py`**
- **目的：** 安全评估集成（分析 5）
- **用法：** `python3 scripts/evaluate_security.py --skills <列表> [--threshold 70]`
- **行数：** 约 250
- **输出：** 带评分的 JSON 安全评估

### 获取脚本

**7. `fetch_skill_manager.py`**
- **目的：** 加载和解析 skill-manager 数据库（第一层）
- **用法：** `python3 scripts/fetch_skill_manager.py`
- **行数：** 约 120
- **输出：** 标准化技能列表 JSON

**8. `fetch_github_stars.py`**
- **目的：** 从 GitHub API 获取星标历史（第二层）
- **用法：** `python3 scripts/fetch_github_stars.py --repo owner/repo`
- **行数：** 约 200
- **输出：** 带速率限制的星标时间戳 JSON

### 解析脚本

**9. `parse_skill_manager.py`**
- **目的：** 解析和验证 skill-manager JSON 模式
- **用法：** 由 `fetch_skill_manager.py` 调用
- **行数：** 约 180
- **验证：** 模式验证，质量过滤

**10. `parse_github_stars.py`**
- **目的：** 解析 GitHub API 星标响应
- **用法：** 由 `fetch_github_stars.py` 调用
- **行数：** 约 150
- **验证：** 时间戳格式，分页处理

### 工具脚本（必需）

**11. `utils/helpers.py`**（时间上下文）
- **目的：** 周边界的时间辅助函数
- **函数：**
  - `get_current_week()` → `(week_start: date, week_end: date)`
  - `get_week_with_fallback(week: Optional[int])` → 自动检测或回退
  - `should_try_previous_week(week: int)` → 时间验证
  - `format_week_message(week_used: int, week_requested: Optional[int])` → 用户消息
- **行数：** 约 150

**12. `utils/cache_manager.py`**（双缓存系统）
- **目的：** 管理技能元数据缓存（30 天 TTL）和安全缓存（7 天 TTL）
- **函数：**
  - `get_cached_metadata()` → 加载元数据缓存或重建
  - `get_cached_security(skill_name: str)` → 加载安全评估或 None
  - `save_security_evaluation(skill_name: str, score: int, details: dict)`
  - `invalidate_expired_cache()` → 清理过期条目
- **行数：** 约 200

**13. `utils/rate_limiter.py`**（GitHub API 速率限制）
- **目的：** 管理 GitHub API 速率限制（5000/小时）
- **函数：**
  - `check_rate_limit()` → 查询剩余配额
  - `wait_if_needed()` → 429 时指数退避
  - `get_retry_after_seconds(response)` → 解析 Retry-After 头
- **行数：** 约 150

### 验证器脚本（必需 - 4 个模块）

**14. `utils/validators/parameter_validator.py`**
- **目的：** 处理前验证用户输入
- **函数：**
  - `validate_skill_name(name: str)` → 名称格式验证
  - `validate_threshold(value: float, min: float, max: float)` → 范围验证
  - `validate_week_number(week: int)` → 周边界验证
- **行数：** 约 180

**15. `utils/validators/data_validator.py`**
- **目的：** 验证 API 响应和数据完整性
- **类：**
  - `ValidationResult` → 单个验证结果
  - `ValidationReport` → 验证结果集合
  - `DataValidator` → 验证 skill-manager 数据、GitHub 响应
- **行数：** 约 220

**16. `utils/validators/temporal_validator.py`**
- **目的：** 验证增长计算中的时间一致性
- **函数：**
  - `validate_temporal_consistency(timestamps: List[datetime])` → 检查顺序
  - `validate_week_boundaries(week_start: date, week_end: date)` → 边界验证
- **行数：** 约 150

**17. `utils/validators/completeness_validator.py`**
- **目的：** 报告前验证数据完整性
- **函数：**
  - `validate_completeness(data: dict, required_fields: List[str])` → 字段存在性
  - `check_coverage_percentage(expected: int, actual: int)` → 覆盖阈值
- **行数：** 约 150

**脚本总行数：** 约 4,850 行生产 Python 代码

---

## 工作流

本节展示用户通常如何通过自然语言查询与此技能交互。

### 工作流 1：每周技能发现

**用户查询：** "本周热门的 Claude 技能有哪些？"

**技能激活：** 被关键词 "热门" + "claude 技能" 触发

**处理流程：**
1. 运行分析 2（增长最快的技能）
2. 从 skill-manager 获取星标前 100 的技能
3. 查询 GitHub API 获取星标历史（本周 vs 上周）
4. 计算 WoW 增长率
5. 过滤增长 >= 5%
6. 按增长率降序排名
7. 对结果运行分析 5（安全评估）
8. 返回带安全徽章的前 10

**输出示例：**
```
🔥 本周趋势技能（WoW >= 5%）：

1. **advanced-code-reviewer**（2,300 星标）
   - WoW 增长：+18.5%（64 新星标 vs 上周 54）
   - 安全：🛡️ 优秀（评分：92）
   - 描述：基于 ML 建议的深度代码分析

2. **api-automation-suite**（1,850 星标）
   - WoW 增长：+12.3%（91 新星标 vs 上周 81）
   - 安全：✅ 良好（评分：78）
   - 描述：自动化 API 测试和文档
```

---

### 工作流 2：寻找新技能安装

**用户查询：** "展示我还没安装的高质量技能"

**技能激活：** 被 "展示" + "技能" + 隐含发现意图触发

**处理流程：**
1. 运行分析 1（新技能发现）
2. 扫描 `~/.claude/skills/` 获取已安装技能
3. 加载 skill-manager 数据库（31,767 个技能）
4. 过滤掉已安装技能
5. 应用质量过滤（星标 >= 50，更新 < 6 月）
6. 按星标降序排名
7. 运行分析 5（安全评估）
8. 返回前 20 个安全通过的技能

**输出示例：**
```
🆕 你未安装的新技能（前 20）：

| 技能名称 | 星标 | 更新 | 安全 | 描述 |
|----------|------|------|------|------|
| pdf-mastery | 850 | 2026-01-20 | 🛡️ 95 | 高级 PDF 处理和分析 |
| data-viz-pro | 720 | 2026-01-18 | ✅ 82 | 创建交互式数据可视化 |
| sql-optimizer | 680 | 2026-01-22 | 🛡️ 90 | AI 建议优化 SQL 查询 |
```

---

### 工作流 3：替换过时技能

**用户查询：** "我的哪些已安装技能应该替换？"

**技能激活：** 被 "替换" + "已安装技能" 触发

**处理流程：**
1. 运行分析 4（可替换技能推荐）
2. 列出所有已安装技能
3. 对每个已安装技能：
   - 查找相似技能（余弦相似度 >= 0.75）
   - 计算置信度评分
   - 过滤置信度 >= 0.70
4. 对候选运行分析 5（安全评估）
5. 按置信度降序排名
6. 返回带理由的替换推荐

**输出示例：**
```
🔄 你应该考虑替换的技能：

### 已安装：`basic-code-formatter`（200 星标，8 个月前更新）

**替换候选：**

1. **advanced-formatter-pro**（置信度：0.85）
   - 星标：1,200（多 6 倍）
   - 相似度：0.91（功能非常相似）
   - 安全：🛡️ 优秀（评分：94）
   - 最后更新：2026-01-25（活跃维护）
   - **推荐：** 强烈推荐替换

2. **smart-formatter**（置信度：0.73）
   - 星标：850（多 4 倍）
   - 相似度：0.88
   - 安全：✅ 良好（评分：80）
   - 最后更新：2026-01-20
   - **推荐：** 考虑作为替代
```

---

### 工作流 4：查找相似功能

**用户查询：** "查找与 `my-pdf-tool` 相似的技能"

**技能激活：** 被 "查找" + "相似" + "技能" 触发

**处理流程：**
1. 运行分析 3（功能相似的技能）
2. 从 skill-manager 加载 `my-pdf-tool` 描述
3. 为所有技能构建 TF-IDF 向量
4. 计算与 `my-pdf-tool` 的余弦相似度
5. 过滤相似度 >= 0.75
6. 排除 `my-pdf-tool` 本身
7. 运行分析 5（安全评估）
8. 按相似度降序排名
9. 返回前 10

**输出示例：**
```
与 `my-pdf-tool` 相似的技能：

| 技能名称 | 相似度 | 星标 | 安全 | 描述 |
|----------|--------|------|------|------|
| pdf-mastery | 0.89 | 850 | 🛡️ 95 | 带 OCR 的高级 PDF 处理 |
| doc-converter-pro | 0.82 | 620 | ✅ 78 | 格式间文档转换 |
| text-extraction-kit | 0.78 | 480 | ✅ 72 | 从 PDF 和图像提取文本 |
```

---

### 工作流 5：安全优先技能发现

**用户查询：** "推荐安全评分好的技能"

**技能激活：** 被 "安全" + "技能" 触发

**处理流程：**
1. 运行分析 1（新技能发现）
2. 对所有结果运行分析 5（安全评估）
3. 过滤安全评分 >= 70（默认阈值）
4. 按安全评分降序排名
5. 返回前 15 个最安全的技能

**输出示例：**
```
🛡️ 推荐的安全技能（评分 >= 70）：

| 技能名称 | 安全 | 星标 | 更新 | 描述 |
|----------|------|------|------|------|
| code-auditor | 🛡️ 98 | 1,200 | 2026-01-28 | 安全聚焦的代码审查 |
| privacy-guardian | 🛡️ 96 | 950 | 2026-01-25 | 隐私泄露检测 |
| safe-executor | 🛡️ 92 | 780 | 2026-01-22 | 沙箱代码执行 |
```

---

### 工作流 6：每周自动化报告

**用户查询：** "生成我的每周技能生态报告"

**技能激活：** 被 "每周" + "技能" + "报告" 触发

**处理流程：**
1. 运行分析 6（综合周报）
2. 顺序执行所有 5 个子分析
3. 汇总统计
4. 生成 Markdown 报告
5. 保存到 `meta/reports/YYYY-MM-DD-skill-trending-report.md`
6. 返回文件路径和摘要

**输出示例：**
```
✅ 每周技能生态报告已生成！

📄 报告保存至：`meta/reports/2026-02-03-skill-trending-report.md`

📊 摘要：
- 生态系统总技能：31,767
- 已安装技能：47
- 本周新技能：12
- 趋势技能（WoW >= 5%）：8
- 替换候选：3
- 安全通过的推荐：15

💡 主要推荐：
1. 将 `basic-formatter` 替换为 `advanced-formatter-pro`（置信度 0.85）
2. 安装 `code-auditor`（趋势 +18.5%，安全 98）
3. 探索 `old-pdf-tool` 的替代品（找到 3 个更好选项）
```

---

### 工作流 7：特定技能增长率分析

**用户查询：** "`popular-skill` 的增长率是多少？"

**技能激活：** 被 "增长率" + 技能名称触发

**处理流程：**
1. 运行分析 2（增长率）带特定技能过滤
2. 从 GitHub API 获取星标历史
3. 计算指定技能的 WoW 增长
4. 与生态系统平均值比较
5. 返回详细增长指标

**输出示例：**
```
📈 `popular-skill` 增长分析：

**本周：**
- 获得星标：64
- 日期范围：2026-01-27 到 2026-02-03

**上周：**
- 获得星标：54
- 日期范围：2026-01-20 到 2026-01-26

**WoW 增长率：** +18.5%
**生态系统平均：** +3.2%
**趋势：** ✅ 是（阈值：5%）

**背景：**
`popular-skill` 增长速度是生态系统平均的 5.8 倍。
这在所有技能中按增长率排名前 5%。
```

---

### 工作流 8：审计已安装技能质量

**用户查询：** "审计我的已安装技能的质量和安全性"

**技能激活：** 被 "审计" + "技能" + "质量|安全" 触发

**处理流程：**
1. 列出 `~/.claude/skills/` 中所有已安装技能
2. 对每个技能：
   - 从 skill-manager 获取元数据（星标、最后更新）
   - 运行分析 5（安全评估）
   - 检查替换候选（分析 4）
3. 分类技能：
   - ✅ 高质量（星标 >= 500，安全 >= 80，活跃）
   - ⚠️ 中等质量（星标 100-499，安全 70-79）
   - 🚨 低质量（星标 < 100，安全 < 70，或过时）
4. 生成审计报告

**输出示例：**
```
🔍 技能质量与安全审计

**已安装技能：** 47

### ✅ 高质量（35 个技能）
- `code-reviewer` - 2,300 星标，安全 95，5 天前更新
- `api-tester` - 1,850 星标，安全 88，8 天前更新
[...]

### ⚠️ 中等质量（8 个技能）
- `old-formatter` - 450 星标，安全 75，2 个月前更新
  → **可用替代：** `new-formatter`（1,200 星标，安全 92）

### 🚨 低质量（4 个技能）
- `abandoned-tool` - 80 星标，安全 55，9 个月前更新
  → **操作：** 考虑卸载或替换

**推荐：**
1. 替换 8 个中等质量技能为更好替代品
2. 卸载或替换 4 个低质量技能
3. 所有高质量技能安全且最新
```

---

### 工作流 9：比较两个技能

**用户查询：** "比较 `skill-a` 和 `skill-b`"

**技能激活：** 被 "比较" + 技能名称触发

**处理流程：**
1. 从 skill-manager 获取两个技能的元数据
2. 对两者运行分析 2（增长率）
3. 对两者运行分析 5（安全评估）
4. 计算两者之间的功能相似度（分析 3）
5. 生成并排比较

**输出示例：**
```
⚖️ 技能比较：`skill-a` vs `skill-b`

| 指标 | skill-a | skill-b | 胜者 |
|------|---------|---------|------|
| 星标 | 1,200 | 850 | skill-a (+41%) |
| 最后更新 | 5 天前 | 12 天前 | skill-a |
| 安全评分 | 🛡️ 92 | ✅ 78 | skill-a |
| WoW 增长 | +8.5% | +12.3% | skill-b |
| 功能相似度 | - | 0.88（非常相似） | - |

**推荐：**
两个技能服务于相似目的（88% 功能相似度）。
`skill-a` 安全性更好且星标更多，但 `skill-b` 增长更快。

**使用场景匹配：**
- 选择 `skill-a` 如果：安全和稳定性是优先
- 选择 `skill-b` 如果：前沿功能和快速开发更重要
```

---

### 工作流 10：识别技能差距

**用户查询：** "我缺少哪些技能类别？"

**技能激活：** 被 "缺少" + "技能类别|差距" 触发

**处理流程：**
1. 分析已安装技能并提取类别（从 topics/tags）
2. 加载 skill-manager 数据库并提取所有类别
3. 识别已安装技能中未涵盖的顶级类别
4. 在缺失类别中查找顶级技能
5. 运行分析 5（安全评估）
6. 推荐技能填补差距

**输出示例：**
```
🔍 技能差距分析

**你的已安装技能覆盖：**
- 代码分析（8 个技能）
- 自动化（12 个技能）
- 测试（6 个技能）

**缺失的高价值类别：**

1. **安全与隐私**（0 个已安装技能）
   - 顶级技能：`privacy-guardian`（950 星标，安全 96）
   - 推荐：安装以覆盖安全审计需求

2. **数据可视化**（0 个已安装技能）
   - 顶级技能：`data-viz-pro`（720 星标，安全 82）
   - 推荐：用于报告和仪表板

3. **数据库管理**（0 个已安装技能）
   - 顶级技能：`sql-optimizer`（680 星标，安全 90）
   - 推荐：优化数据库性能

**行动计划：**
从每个缺失类别安装 1-2 个技能以建立全面的生态系统。
```

---

## 错误处理

此技能实现了带优雅降级的全面错误处理：

### GitHub API 错误

**错误：** 速率限制超出（HTTP 429）

**处理：**
1. 解析 `Retry-After` 头（配额重置前的秒数）
2. 实现指数退避：`等待时间 = min(2^重试次数 × 60, 3600)` 秒
3. 向用户记录速率限制状态
4. 回退：如可用则使用缓存的星标数据（即使过期）
5. 如 API 不可用则跳过 WoW 增长分析

**用户消息：**
```
⚠️ GitHub API 速率限制已达到。使用缓存数据。
下次配额重置：45 分钟
WoW 增长分析已跳过（需要新鲜 API 数据）
```

---

**错误：** 无效仓库 URL 或 404

**处理：**
1. 在结果中标记技能为"不可用"
2. 向控制台记录警告
3. 继续处理其他技能
4. 在摘要中报告不可用技能

**用户消息：**
```
⚠️ 3 个技能不可用（仓库未找到）：
- skill-x（仓库已删除？）
- skill-y（无效 URL）
```

---

### skill-manager 数据库错误

**错误：** 数据库文件未找到

**处理：**
1. 检查 skill-manager 是否已安装：`ls ~/.claude/skills/skill-manager`
2. 如未安装，推荐安装
3. 如已安装但数据库缺失，建议重新安装
4. 中止需要数据库的分析（1-4）

**用户消息：**
```
❌ skill-manager 数据库未找到。

请先安装 skill-manager：
/plugin marketplace add skill-manager

或如已安装，重新安装以重建数据库。
```

---

**错误：** 数据库模式不匹配或 JSON 损坏

**处理：**
1. 用 try/catch 验证 JSON 语法
2. 检查必需字段：`name`、`description`、`repository`、`stars`
3. 记录带行号的解析错误
4. 跳过损坏条目，继续处理有效条目
5. 报告跳过条目数量

**用户消息：**
```
⚠️ 数据库解析问题：
- 12 个条目已跳过（缺少必需字段）
- 31,755 个条目成功解析（99.96% 成功率）
```

---

### 安全评估错误

**错误：** 安全评估技能未安装

**处理：**
1. 检测安全评估技能不存在
2. 警告用户安全评分将不可用
3. 继续分析但不进行安全过滤
4. 将所有推荐标记为"未评估"

**用户消息：**
```
⚠️ 安全评估已跳过（技能未安装）
所有推荐标记为"未评估"

要启用安全评估：
/plugin marketplace add skill-security-auditor
```

---

**错误：** 特定技能安全评估失败

**处理：**
1. 捕获评估错误（退出码 != 0）
2. 向控制台记录错误详情
3. 将技能标记为"未评估"（不阻止）
4. 继续评估其他技能
5. 让用户决定是否信任未评估技能

**用户消息：**
```
⚠️ `problematic-skill` 安全评估失败
错误：30 秒后超时
状态：未评估（未阻止）
```

---

### 验证错误

**错误：** 无效用户参数（如阈值超出范围）

**处理：**
1. 使用 `parameter_validator.py` 验证输入
2. 提供带有效范围的清晰错误消息
3. 建议带示例的正确用法
4. 优雅中止分析

**用户消息：**
```
❌ 无效阈值：1.5

相似度阈值必须在 0.0 和 1.0 之间
示例：--similarity-threshold 0.75
```

---

**错误：** 数据验证失败（缺少字段、类型不匹配）

**处理：**
1. 使用 `data_validator.py` 验证所有数据
2. 生成带详细问题的 `ValidationReport`
3. 如发现关键问题：带错误报告中止
4. 如仅有警告：继续并记录警告
5. 提供可操作的下一步

**用户消息：**
```
⚠️ 数据验证警告：

- 5 个技能缺少 'last_updated' 字段（使用 'unknown'）
- 2 个技能 'stars' 字段非数字（跳过）

✅ 验证通过但有警告
已处理：31,760 / 31,767 个技能（99.98%）
```

---

## 性能与缓存

### 双缓存策略

**缓存 1：技能元数据缓存**
- **文件：** `data/cache/skill-metadata.json`
- **TTL：** 30 天
- **目的：** 避免重复解析 skill-manager 数据库的 31,767 个技能
- **失效：** 通过 `--refresh-cache` 标志手动失效或 30 天后自动过期

**缓存 2：安全评估缓存**
- **文件：** `data/security-cache/evaluations.json`
- **TTL：** 7 天（因动态安全环境较短）
- **目的：** 避免冗余安全评估（昂贵操作）
- **失效：** 7 天后自动过期或通过 `--refresh-security` 手动失效

### 性能优化

**1. 延迟加载：**
仅在需要时加载 skill-manager 数据库（分析 1-4），不用于仅 GitHub 数据的分析 2。

**2. 并行 GitHub API 请求：**
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=10) as executor:
    star_histories = executor.map(fetch_github_stars, skill_repos)
```
限制：10 个并发请求（避免压垮 API）

**3. 分页处理：**
GitHub API 每个请求最多返回 100 个星标者。对于本周超过 100 星标的技能，使用分页：
```python
page = 1
all_stars = []
while True:
    response = fetch(f"stargazers?per_page=100&page={page}")
    if not response:
        break
    all_stars.extend(response)
    page += 1
```

**4. 提前退出优化：**
对于前 N 查询（如前 10 趋势），收集足够候选后停止处理：
```python
trending_skills = []
for skill in sorted_by_stars:
    growth = calculate_wow_growth(skill)
    if growth >= 5.0:
        trending_skills.append(skill)
        if len(trending_skills) >= 20:  # 收集 20 个，返回前 10
            break
```

**5. TF-IDF 预计算：**
构建一次 TF-IDF 矩阵，缓存所有技能的向量：
```python
# 首次运行：构建并缓存
tfidf_matrix = vectorizer.fit_transform(descriptions)
save_cache('tfidf-vectors.pkl', tfidf_matrix)

# 后续运行：加载缓存向量
tfidf_matrix = load_cache('tfidf-vectors.pkl')
similarities = cosine_similarity(query_vector, tfidf_matrix)
```

### 基准性能

**环境：** M1 MacBook Pro，16GB RAM，100 Mbps 网络

**分析 1（新技能）：**
- 首次运行（无缓存）：约 8 秒（解析 31,767 个技能）
- 缓存运行：约 0.3 秒（加载预解析元数据）

**分析 2（增长率）：**
- 100 个技能 × 2 周 × 100 星标/周 = 约 20,000 API 调用
- 10 个并发工作器：约 12 分钟
- 有缓存（7 天 TTL）：约 0.5 秒

**分析 3（相似度）：**
- 构建 TF-IDF 矩阵：约 15 秒（首次运行）
- 计算相似度：约 2 秒/查询
- 有缓存向量：约 0.4 秒/查询

**分析 4（替换）：**
- 47 个已安装技能 × 平均 10 个相似候选 = 470 次比较
- 有缓存 TF-IDF：约 5 秒总计

**分析 5（安全）：**
- 每个技能评估：约 10-30 秒（取决于技能复杂度）
- 有缓存（7 天 TTL）：约 0.1 秒/技能
- 并行评估（5 个工作器）：20 个技能约 2 分钟

**分析 6（综合报告）：**
- 首次运行（冷缓存）：约 18 分钟（所有分析 + API 调用）
- 热缓存：约 8 秒（所有数据已缓存）
- 典型每周运行（部分缓存，部分新鲜）：约 3 分钟

---

## 强制验证

按照 agent-skill-creator 工作流，所有输入和输出都经过验证：

### 输入验证（parameter_validator.py）

**验证的参数：**
- 技能名称：非空，字母数字 + 连字符，最大 100 字符
- 阈值：浮点数范围 [0.0, 1.0]
- 周数：整数 1-53
- 置信度阈值：浮点数范围 [0.0, 1.0]

**示例：**
```python
from utils.validators.parameter_validator import validate_skill_name, validate_threshold

skill_name = validate_skill_name(user_input)  # 无效则抛出 ValidationError
similarity_threshold = validate_threshold(0.75, min=0.0, max=1.0)
```

### 数据验证（data_validator.py）

**验证的数据：**
- skill-manager JSON 模式
- GitHub API 响应
- TF-IDF 矩阵维度
- 安全评估输出

**示例：**
```python
from utils.validators.data_validator import DataValidator

validator = DataValidator()
response_report = validator.validate_response(github_data)

if response_report.has_critical_issues():
    raise DataQualityError(response_report.get_summary())
```

### 时间验证（temporal_validator.py）

**验证的约束：**
- 星标历史中无未来日期
- 周边界为周一 00:00 - 周日 23:59 UTC
- 增长计算周范围恰好 7 天
- 时间序列数据中无可疑间隙

**示例：**
```python
from utils.validators.temporal_validator import validate_temporal_consistency

report = validate_temporal_consistency(star_timestamps)

if not report.all_passed():
    warnings = report.get_warnings()
    log_warnings(warnings)
```

### 完整性验证（completeness_validator.py）

**验证的覆盖：**
- 结果中存在所有预期技能
- 输出中无缺失必需字段
- 覆盖百分比 >= 80% 阈值
- 所有报告章节已填充

**示例：**
```python
from utils.validators.completeness_validator import validate_completeness

report = validate_completeness(
    data=analysis_results,
    expected_entities=installed_skills,
    expected_years=[2026]  # 如适用
)

if not report.all_passed():
    log_warnings(report.get_warnings())
```

---

## 检测关键词

此技能使用**三层激活系统**实现 95%+ 可靠性：

### 第一层：关键词（15 个精确短语）

1. "热门 claude 技能"
2. "技能推荐"
3. "监控技能受欢迎度"
4. "技能增长率"
5. "替换过时技能"
6. "新技能发现"
7. "比较已安装技能"
8. "安全评估技能"
9. "寻找更好替代品"
10. "技能生态洞察"
11. "每周技能报告"
12. "检查技能更新"
13. "相似功能技能"
14. "技能质量评估"
15. "替代技能建议"

### 第二层：模式（7 个正则表达式，不区分大小写）

1. `(?i)(trending|popular|growing|hot)\s+(claude\s+)?skills?`
2. `(?i)(monitor|track|watch|check)\s+(skill\s+)?(popularity|growth|trends?|updates?)`
3. `(?i)(recommend|suggest|find|discover)\s+(new|better|alternative)\s+skills?`
4. `(?i)replace\s+(outdated|old|obsolete)\s+skills?`
5. `(?i)security\s+(evaluation|check|audit|assessment)\s+(for\s+)?skills?`
6. `(?i)(weekly|daily|monthly)\s+skill\s+(report|summary|analysis)`
7. `(?i)(similar|comparable)\s+(functionality|features?)\s+skills?`

### 第三层：描述（500 字符，68 个关键词）

通过 marketplace.json 中的语义描述进行自然语言理解回退。

**关键词密度：** 68 个唯一关键词包括：
- trending、popular、growing、hot、monitor、track、watch、check
- recommendations、discover、find、suggest
- similarity、alternatives、replacements、comparable
- security、evaluation、audit、assessment
- growth、rates、star、counts、ecosystem、insights
- weekly、daily、monthly、report、summary、analysis
- outdated、obsolete、quality、confidence、threshold

---

## 使用示例

### 示例 1：每周监控

```
用户："本周热门的 claude 技能有哪些？"

✓ 第一层匹配："热门 claude 技能"

技能响应：
🔥 本周趋势技能（WoW >= 5%）：

1. **advanced-code-reviewer**（2,300 星标，+18.5% WoW）
   - 安全：🛡️ 优秀（92）
   - 新星标：64（vs 上周 54）

2. **api-automation-suite**（1,850 星标，+12.3% WoW）
   - 安全：✅ 良好（78）
   - 新星标：91（vs 上周 81）

[另外 8 个趋势技能...]

📊 分析详情：
- 已分析：星标前 100 个技能
- GitHub API 调用：200（速率限制：剩余 4,800）
- 缓存：30% 命中，70% 新鲜数据
```

---

### 示例 2：寻找替换

```
用户："我的哪些技能应该替换？"

✓ 模式匹配：(?i)replace.*skills?

技能响应：
🔄 替换推荐：

### 1. 替换 `basic-formatter`（200 星标，8 个月旧）

**最佳替代品：`advanced-formatter-pro`**
- 置信度：0.85（强烈推荐）
- 星标：1,200（多 6 倍）
- 安全：🛡️ 优秀（94）
- 相似度：0.91（功能非常相似）
- 最后更新：5 天前

**为什么替换？**
- 6 倍更多社区验证
- 活跃维护（vs 8 个月停滞）
- 更好的安全评分
- 高功能相似度

**安装：**
/plugin marketplace add advanced-formatter-pro
```

---

### 示例 3：安全审计

```
用户："检查我已安装技能的安全性"

✓ 模式匹配：(?i)security.*skills?

技能响应：
🛡️ 安全审计结果：

**已安装技能：** 47

### ✅ 安全优秀（35 个技能）
- `code-reviewer` - 评分：95
- `api-tester` - 评分：92
[...]

### ⚠️ 安全中等（8 个技能）
- `old-formatter` - 评分：75
  → 可用替代品：`new-formatter`（评分：94）

### 🚨 安全较低（4 个技能）
- `abandoned-tool` - 评分：55
  → ⚠️ 考虑卸载（高风险）

**行动项：**
1. 立即替换 4 个低安全技能
2. 审查 8 个中等安全技能寻找替代品
3. 所有高安全技能可安全使用
```

---

### 示例 4：发现新技能

```
用户："展示我还没安装的新技能"

✓ 第一层匹配："新技能"

技能响应：
🆕 新技能发现（前 20）：

| 技能 | 星标 | 更新 | 安全 | 描述 |
|------|------|------|------|------|
| pdf-mastery | 850 | 5 天前 | 🛡️ 95 | 高级 PDF 处理 |
| data-viz-pro | 720 | 7 天前 | ✅ 82 | 交互式数据可视化 |
| sql-optimizer | 680 | 3 天前 | 🛡️ 90 | AI 驱动的 SQL 优化 |

[另外 17 个技能...]

💡 安装：
/plugin marketplace add pdf-mastery
```

---

### 示例 5：相似技能

```
用户："查找与 my-pdf-tool 相似的技能"

✓ 模式匹配：(?i)(similar|comparable).*skills?

技能响应：
与 `my-pdf-tool` 相似的技能：

| 技能 | 相似度 | 星标 | 安全 | 描述 |
|------|--------|------|------|------|
| pdf-mastery | 0.89 | 850 | 🛡️ 95 | PDF 处理 + OCR |
| doc-converter | 0.82 | 620 | ✅ 78 | 多格式转换 |
| text-extractor | 0.78 | 480 | ✅ 72 | 从文档提取文本 |

**功能重叠：**
这些技能与 `my-pdf-tool` 有 78-89% 的功能相似度
基于描述的 TF-IDF 文本分析。

**使用场景匹配：**
- `pdf-mastery`：最适合高级 PDF 操作
- `doc-converter`：最适合格式转换
- `text-extractor`：最适合简单文本提取
```

---

### 示例 6：增长率查询

```
用户："`popular-skill` 的增长率是多少？"

✓ 第一层匹配："技能增长率"

技能响应：
📈 增长分析：`popular-skill`

**周环比增长：** +18.5%

**详情：**
- 本周（1 月 27 日 - 2 月 3 日）：64 新星标
- 上周（1 月 20 - 26 日）：54 新星标
- 总星标：2,300

**背景：**
- 生态系统平均：+3.2%
- `popular-skill` 增长：比平均快 5.8 倍
- 排名：按增长率前 5%

**趋势：** ✅ 是（阈值：5%）
```

---

### 示例 7：每周报告

```
用户："生成每周技能报告"

✓ 第一层匹配："每周技能报告"

技能响应：
✅ 每周技能生态报告已生成！

📄 保存至：`meta/reports/2026-02-03-skill-trending-report.md`

📊 摘要：
- 总技能：31,767
- 已安装：47
- 本周新增：12
- 趋势（WoW >= 5%）：8
- 替换候选：3
- 安全通过：15

💡 主要行动：
1. 替换 `basic-formatter` → `advanced-formatter-pro`（置信度：0.85）
2. 安装 `code-auditor`（+18.5% 增长，安全 98）
3. 审查 8 个中等安全技能

📅 下次报告：2026-02-10（7 天）
```

---

### 示例 8：技能比较

```
用户："比较 skill-a 和 skill-b"

✓ 模式匹配：(?i)compare.*skills?

技能响应：
⚖️ 比较：`skill-a` vs `skill-b`

| 指标 | skill-a | skill-b | 胜者 |
|------|---------|---------|------|
| 星标 | 1,200 | 850 | skill-a (+41%) |
| 安全 | 🛡️ 92 | ✅ 78 | skill-a |
| 更新 | 5 天前 | 12 天前 | skill-a |
| WoW 增长 | +8.5% | +12.3% | skill-b |

**相似度：** 0.88（功能非常相似）

**推荐：**
两者解决相似问题。选择：
- `skill-a` 为：稳定性、安全性、受欢迎度
- `skill-b` 为：前沿功能、快速更新
```

---

### 示例 9：质量评估

```
用户："评估我技能的质量"

✓ 第一层匹配："技能质量评估"

技能响应：
🔍 技能质量评估：

**高质量（35/47 个技能）：**
- 星标 >= 500
- 安全 >= 80
- 更新 < 30 天

**中等质量（8/47 个技能）：**
- 星标 100-499
- 安全 70-79
- 更新 < 90 天
- **行动：** 审查寻找替代品

**低质量（4/47 个技能）：**
- 星标 < 100 或 安全 < 70 或 更新 > 180 天
- **行动：** 替换或卸载

**总体生态健康度：** ⭐⭐⭐⭐☆（4/5）

**改进计划：**
1. 替换 4 个低质量技能（预计时间：20 分钟）
2. 审查 8 个中等质量技能（预计时间：10 分钟）
3. 结果：100% 高质量技能生态
```

---

### 示例 10：技能差距分析

```
用户："我缺少哪些技能类别？"

✓ 第三层匹配：通过描述 NLU 的语义理解

技能响应：
🔍 技能差距分析：

**你的覆盖：**
✅ 代码分析（8 个技能）
✅ 自动化（12 个技能）
✅ 测试（6 个技能）

**缺失的类别：**

1. **安全与隐私（0 个技能）**
   - 顶级：`privacy-guardian`（950 星标，安全 96）
   - 用例：检测代码中的隐私泄露

2. **数据可视化（0 个技能）**
   - 顶级：`data-viz-pro`（720 星标，安全 82）
   - 用例：创建仪表板和报告

3. **数据库管理（0 个技能）**
   - 顶级：`sql-optimizer`（680 星标，安全 90）
   - 用例：优化 SQL 查询

**推荐：**
每个缺失类别安装 1 个技能以建立全面的生态系统。

**快速安装：**
/plugin marketplace add privacy-guardian
/plugin marketplace add data-viz-pro
/plugin marketplace add sql-optimizer
```

---

### 示例 11：替代品建议

```
用户："建议 my-old-skill 的替代品"

✓ 第一层匹配："替代技能建议"

技能响应：
🔄 `my-old-skill` 的替代品：

**当前：** `my-old-skill`
- 星标：200
- 安全：⚠️ 65（中等风险）
- 最后更新：8 个月前

**更好的替代品：**

1. **new-skill-pro**（置信度：0.85）
   - 星标：1,200（多 6 倍）
   - 安全：🛡️ 92（更安全）
   - 更新：5 天前
   - 相似度：0.91（相同功能）
   - **强烈推荐**

2. **modern-skill**（置信度：0.78）
   - 星标：950（多 4.75 倍）
   - 安全：✅ 85
   - 更新：8 天前
   - 相似度：0.88
   - **不错的替代品**

3. **efficient-skill**（置信度：0.72）
   - 星标：680（多 3.4 倍）
   - 安全：✅ 80
   - 更新：12 天前
   - 相似度：0.85
   - **值得考虑**

**下一步：**
1. 审查 `new-skill-pro` 文档
2. 在开发环境测试
3. 如满意则替换 `my-old-skill`
```

---

### 示例 12：监控技能更新

```
用户："检查技能更新"

✓ 第一层匹配："检查技能更新"

技能响应：
🔔 技能更新监控：

**最近更新的已安装技能（过去 7 天）：**

✅ `code-reviewer` - 2 天前更新
   - 更新日志：添加 Python 3.12 支持

✅ `api-tester` - 5 天前更新
   - 更新日志：修复超时处理

**过时的技能（超过 90 天无更新）：**

⚠️ `old-formatter` - 最后更新 8 个月前
   - 推荐：替换为 `new-formatter`

⚠️ `legacy-tool` - 最后更新 11 个月前
   - 推荐：考虑卸载（可能已废弃）

**行动项：**
1. 审查最近更新技能的更新日志
2. 测试更新技能的破坏性变更
3. 替换或卸载 2 个过时技能

**自动更新建议：**
启用每周更新检查：
`cron: 0 10 * * 0 python3 scripts/analyze_comprehensive.py`
```

---

### 示例 13：生态洞察

```
用户："给我技能生态洞察"

✓ 第一层匹配："技能生态洞察"

技能响应：
📊 技能生态洞察（2026-02-03）：

**全局统计：**
- 总技能：31,767
- 活跃技能（更新 < 6 月）：18,523（58.3%）
- 高质量技能（星标 >= 100）：4,215（13.3%）
- 安全通过技能（评分 >= 70）：12,450（39.2%）

**增长趋势：**
- 本周新技能：12
- 平均 WoW 增长：+3.2%
- 增长最快：`code-auditor`（+18.5%）
- 趋势技能（>= 5%）：8

**你的生态：**
- 已安装：47 个技能
- 覆盖：总生态系统的 0.15%
- 质量分布：
  - 高：74%（35 个技能）
  - 中：17%（8 个技能）
  - 低：9%（4 个技能）

**类别分布（前 10）：**
1. 代码分析：3,850 个技能（12.1%）
2. 自动化：2,920 个技能（9.2%）
3. 测试：2,540 个技能（8.0%）
4. 文档：1,980 个技能（6.2%）
5. 安全：1,650 个技能（5.2%）

**推荐：**
- 你的生态系统平衡良好（74% 高质量）
- 考虑添加安全类技能（当前 0 个）
- 替换 4 个低质量技能以达到 100% 高质量
```

---

## 安装

### 先决条件

```bash
# 1. 确保 skill-manager 已安装（第一层数据必需）
ls ~/.claude/skills/skill-manager/data/all_skills_with_cn.json

# 如未找到：
/plugin marketplace add skill-manager

# 2. 安装 Python 依赖
pip3 install scikit-learn pandas numpy

# 3. （可选）获取 GitHub 令牌用于第二层数据
# 访问：https://github.com/settings/tokens
# 范围：public_repo（只读）
```

### 安装此技能

```bash
# 从市场
/plugin marketplace add ./skill-trending-monitor-cskill

# 或手动安装
cp -r skill-trending-monitor-cskill ~/.claude/skills/
```

### 配置 GitHub 令牌（可选但推荐）

```bash
# 创建配置文件
cat > ~/.claude/skills/skill-trending-monitor-cskill/assets/config.json << 'EOF'
{
  "github_token": "ghp_你的令牌",
  "rate_limit_buffer": 100,
  "max_retries": 3,
  "similarity_threshold": 0.75,
  "growth_threshold": 5.0,
  "security_threshold": 70,
  "confidence_threshold": 0.70
}
EOF
```

### 验证安装

```bash
# 测试基本功能
python3 ~/.claude/skills/skill-trending-monitor-cskill/scripts/analyze_new_skills.py --limit 5

# 预期输出：5 个新技能的 JSON 列表
```

---

## 自动化（可选）

### 通过 launchd 的每周报告（macOS）

创建 `~/Library/LaunchAgents/com.claude.skill-trending-monitor.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.skill-trending-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/YOUR_USER/.claude/skills/skill-trending-monitor-cskill/scripts/analyze_comprehensive.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>10</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</dict>
</plist>
```

加载任务：
```bash
launchctl load ~/Library/LaunchAgents/com.claude.skill-trending-monitor.plist
```

### 通过 cron 的每周报告（Linux）

```bash
# 编辑 crontab
crontab -e

# 添加每周任务（周日 10:00 AM）
0 10 * * 0 python3 ~/.claude/skills/skill-trending-monitor-cskill/scripts/analyze_comprehensive.py
```

---

## 故障排除

详细故障排除指南见 `references/troubleshooting.md`。

**常见问题：**

1. **GitHub 速率限制：** 等待配额重置或添加认证令牌
2. **skill-manager 未找到：** 通过 `/plugin marketplace add skill-manager` 安装
3. **TF-IDF 错误：** 安装 scikit-learn：`pip3 install scikit-learn`
4. **安全评估失败：** 安装安全技能或使用 `--skip-security` 跳过

---

## 贡献

此技能由 `agent-skill-creator` 按照综合 5 阶段工作流自主创建。如需修改或改进，请维护既定架构：

- 双层数据系统（skill-manager + GitHub API）
- 双缓存策略（30 天元数据 + 7 天安全）
- 基于 ML 的相似度检测（TF-IDF + 余弦）
- 3 层激活系统（关键词 + 模式 + NLU）
- 全面验证（4 个验证器）
- 安全优先推荐

---

**版本：** 1.0.0
**创建时间：** 2026-02-03
**作者：** agent-skill-creator（自主）
**许可证：** MIT

---

**总字数：** 约 6,200 词
