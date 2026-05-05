# DR Lessons Learned

> 跨项目共享的研究教训库。每次 DR 结束沉淀 1-3 条结构化 lesson。
> Phase 1 启动时自动 grep 当前主题相关条目注入 prompt（scripts/lessons-injector.ts，P5 实施前手工 grep）。

## 字段约定

```markdown
### Lesson N：[一句话教训]
- **现象**: [实战中观察到什么]
- **根因**: [为什么会出现]
- **教训**: [下次怎么做]
- **应用规则**: [何时触发 / 注入 prompt 的哪个字段]
- **关键词**: [grep 用，逗号分隔]
```

> **隐私规则**：lessons-learned 是公开 git repo。条目只能含**通用模式**，不得含客户姓名、具体业务、可识别的项目代号、具体域名（即使它表现差）。涉及具体案例时用 "项目 A" / "客户 X" / "blog domain" 等中性占位。

---

## 2026-05-03 — 海外华语创作者教练产品调研（T3 Deep）

### Lesson 1：跨报告价格判断必须由同一份 Q 出
- **现象**: Q4（定价）说 "X 元合理"，Q5（流量基准）说 "目标 IP 流量不够支撑该价位"——两个 Q 各自得到逻辑自洽但相互冲突的结论
- **根因**: "X 是否合理"类二元判断需要前置条件，但 Q4 和 Q5 的 prompt 没强制锚定彼此
- **教训**: 涉及"X 是否合理 / 是否可行"类二元判断的 Q，prompt 中必须强制 "需考虑 [关联因素]" 列举所有相关 Q 的产出，并要求"明确表态，不要中立表述"
- **应用规则**: T2+ 在 Phase 1.5 critic 时检查所有 Q 的 prompt，凡含"合理性/可行性/能不能"判断的，强制添加 `### 必须前置考虑的关联条件` 章节
- **关键词**: 定价合理性, 可行性判断, 二元判断, 二元结论, pricing feasibility

### Lesson 2：单源依赖症（同域名重复引用 ≥3 次充数）
- **现象**: 两份子报告核心论证靠同一个 blog 域名（其中一份引用同源 8 次）
- **根因**: Gemini DR 找到一个相关性高的来源后倾向反复挖掘，而非主动多源验证
- **教训**: prompt 必须在 constraints 里明确写"任何核心结论 ≥2 个独立域名 A/B 级来源，否则标 [行业未公开基准]"
- **应用规则**: T1+ 在 tasks-template 的 constraints 默认包含此规则；Phase 2.5 critic 的维度 4（Source Credibility）必须扫描"同一域名引用次数"
- **关键词**: 单源依赖, 同源重复, source diversity, 来源多样性

### Lesson 3：工具盘点类需求 0 URL 问题
- **现象**: 一份"列 N 个 AI 工具"的子报告列了 12 款工具 + 价格 + 功能，但全部无官网 URL，定价数字无法验证
- **根因**: Gemini 对"列 N 个工具"类需求会自动回退到 training data，跳过实时搜索
- **教训**: prompt 必须明确写 "每个工具/产品/案例必须含官网 URL，缺失则标 [URL 待补]"，并在输出要求里强制"含 URL 的工具数 ≥ 总工具数 80%"
- **应用规则**: T1+ 凡涉及"列 N 个工具/产品/案例"的 prompt 必须 forced specify URL 字段；validate-sources.ts 检测"工具盘点段落"的 URL 密度
- **关键词**: 工具盘点, tool benchmark, list N tools, 产品列表, 案例列表

### Lesson 4：推测数字以表格形式呈现 = 看起来像数据的幻觉
- **现象**: 一份子报告把 `[推测]` 标签的数字（如"中位数 X / 爆款率 Y%"）做成正经表格
- **根因**: Gemini 在没有真实数据时倾向"用 [推测] 标签 + 表格"组合，但表格视觉权重远超标签
- **教训**: 明确禁止"表格中出现 [推测] 标签"，未公开数据应转为定性描述或标 `[行业未公开基准，需自测]`
- **应用规则**: T1+ 在 anti-patterns Tier 3 包含此规则；Phase 2.5 critic 自动 grep `\[推测\]` 在表格上下文（前后 20 行有 `|` 字符）
- **关键词**: 推测数字, 伪表格, fake table, hallucinated data

### Lesson 5：URL 透明度 = 异常清洗信号
- **现象**: 10 份 raw 报告 0 处出现 `vertexaisearch.cloud.google.com/grounding-api-redirect`，反而是异常信号
- **根因**: Gemini DR 默认会带这种 redirect URL，0 出现意味"作者/工具已清洗"，但清洗后是否替换为真实 URL 不可知
- **教训**: 不要简单期望"清洗 = 干净"，必须对核心结论的 URL 做 curl 抽查
- **应用规则**: T1+ 在 Phase 2 完成后自动跑 validate-sources.ts，抽 ≤30 URL 做 HEAD 请求，<60% 通过率触发强制 cross-validation
- **关键词**: URL 透明度, grounding-api-redirect, URL 清洗, link sanitization

---

## 跨项目通用 lessons

### Lesson G1：Phase 1.5 critic 必须预声明 cross-validation 候选
- **现象**: Phase 2.5 critic 完才发现 Top 3 结论需 cross-validation，已经晚了
- **根因**: cross-val 候选在 Phase 1.5 已经能预判（"涉及不可逆决策/具体数字/法律案例"必然要验证）
- **教训**: Phase 1.5 challenge 输出必须包含"预声明 Cross-Validation Targets"列表
- **应用规则**: T3+ 强制；写入 `dr-config.json` 的 `cross_validation_targets` 字段
- **关键词**: cross-validation, 交叉验证, pre-declare, 预声明

### Lesson G2：Tier 选择不应凭直觉
- **现象**: 项目 A 用了 "deep" 模式但其实需要 T3 全套（不可逆 + 对外交付 + 战略级）
- **根因**: 老 v7.4 的 4 档划分是按 Phase 数，没按"任务难度"
- **教训**: 用 5 个 yes/no 题机械判断 Tier（参见 references/tier-decision-tree.md）
- **应用规则**: 所有 DR 启动前必走 tier-decision-tree
- **关键词**: tier 选择, 深度选择, depth selection

---

## 词典维护规则

新增 lesson 时遵循：
1. 必须基于实战观察（不是预设的"理论上应该")
2. 必须含 5 个字段（现象/根因/教训/规则/关键词）
3. 关键词覆盖中英文 + 同义词
4. 每条 lesson 同步更新 anti-patterns-dict.md（如果产生新检测规则）
5. **脱敏**: 客户名/项目代号/具体域名 → 用 "项目 A" / "客户 X" / "blog domain" 占位

---

**版本**: v1.0
**初始化**: 2026-05-03
**条目数**: 7 (5 项目特定 + 2 跨项目通用)
