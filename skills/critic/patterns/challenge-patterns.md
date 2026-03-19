# Challenge Patterns — Common Design Blind Spots

## Usage

- Automatically read during `/critic challenge`; apply these patterns when reviewing a proposal
- Append new patterns discovered during a challenge to the "New pattern append area" below
- Periodically review hit frequency; high-frequency patterns are marked [HOT]

**Format**:
- `trigger`: which design scenarios tend to activate this pattern
- `check`: the specific verification action
- `(N/M)`: hit N times across M challenges (reset to 0/0 — build your own stats)

---

## Patterns

### P1: Incomplete Enumeration [HOT] (0/0)

- **trigger**: Any grouping / migration / reorganization design (distributing elements of A into B)
- **check**: Use the original complete list as a checklist; check off each element's destination one by one; confirm no element is missing
- **cases**: Reorganizing navigation tabs — missed one tab in new grouping | Config file lists 8 services but migration script only handles 7

### P2: Neighbor Blindspot (0/0)

- **trigger**: Modifying a navigation section, module, or configuration area
- **check**: Glob all adjacent layout/config files; confirm no overlaps or duplicates; draw out the "neighbor relationship"
- **cases**: Adding a new admin route without checking existing admin pages at the same path prefix (route conflict) | Designing two pipeline layers separately without verifying how data flows between them

### P3: Runtime Not Specified (0/0)

- **trigger**: Design includes data flows, interaction flows, or automation triggers
- **check**: For each data flow ask: who produces it? who consumes it? what triggers it? how is concurrency handled? who knows it exists in the ecosystem (registry/dashboard/docs)?
- **cases**: Choosing batch processing runtime for a real-time interaction system | Aggregating 8 data sources in a single view API — complexity underestimated

### P4: Over-Engineering / Anchoring Effect (0/0)

- **trigger**: Referenced an external solution, open-source project, or existing framework
- **check**: Ask "without building this, can existing capabilities handle it? How large is the gap — is it worth how many lines of code?"
- **cases**: 600-line framework reference file for a feature the LLM already has natively | Introducing a full AST tool chain for a pattern that a 5-line grep handles

### P5: Threshold Disconnected from Reality (0/0)

- **trigger**: Design includes thresholds, frequencies, trigger conditions, or cold-start parameters
- **check**: Run back-of-envelope calculation with actual data volume; verify parameters are viable under real traffic
- **cases**: Confidence ≥0.9 + 5 matches required before activating a rule — actual daily volume means first rule activates after 2 weeks

### P6: Data Source Not Verified (0/0)

- **trigger**: Design depends on field values from a JSON file or other data source
- **check**: Sample actual values to verify they match expectations (don't trust field names — check actual content)
- **cases**: Pipeline state file marked "manual" but actually has a scheduled job — design depended on incorrect metadata | Synthesis report adds inferred date ranges without marking them as inferred — readers can't distinguish original conclusions from synthesizer's additions

---

## New Pattern Append Area

### P7: Requirements–Solution Mismatch (solving the wrong problem) (0/0)

- **trigger**: User states a pain point; design jumps to a broader solution
- **check**: Trace back to the original pain point: "Which specific form of the problem does this solution address? What is the minimum viable solution?"
- **cases**: User says "I forget the logic I set up" → solution jumps to "full architecture diagram" when a single health-status card was the highest-value fix

### P8: Research Prompt Missing Baseline Anchor (0/0)

- **trigger**: Using AI research to supplement or validate an existing proposal (Deep Research, WebSearch, etc.)
- **check**: Does the prompt tell the research agent "I already know X — find what's beyond X"? Does it include the user's specific context (not a generalized scenario)?
- **cases**: Deep Research prompt doesn't state which concepts are already known, leading to results that duplicate known information or skew toward generic advice

### P9: Self-Review Bias (question-setter as answer-checker) (0/0)

- **trigger**: AI evaluates a proposal it also designed — open questions, feasibility judgments, self-review
- **check**: Does every recommendation happen to validate the original proposal? Did any recommendation overturn the original design? If all outputs are "maintain status quo," question why open questions were asked at all. **Reverse variant**: After challenge over-negates and user pushes back, did the flip come with an independent argument, or just follow the user's direction?
- **防护机制**: In Step 5, attach confidence `[C1-C10]` to each major claim. When challenged, show before/after confidence + independent reason. Drop >3 with no new evidence → `⚠️ P9 suspected sycophantic flip, maintaining original: [claim]`
- **cases**: 6 open-question recommendations all pointing toward "do it as originally planned," none overturning anything | Challenge scores 4/10 → user pushes back → position immediately reversed with no independent reasoning

### P12: Internal Self-Contradiction (document contradicts itself) (0/0)

- **trigger**: Long document (>200 lines) with multiple sections describing different aspects of the same concept
- **check**: For key technical constraints, grep all occurrences in the full document; verify every code example and description is consistent
- **cases**: Section 1.2 correctly warns "X must be called within a transaction"; Section 3.2 code example uses the anti-pattern that was warned against

### P13: "As Needed" = Never Executed (missing trigger condition) (0/0)

- **trigger**: Plan/rule/task contains vague trigger words like "as needed / depending on situation / when conditions allow / revisit later"
- **check**: Ask "who decides 'needed'? What event triggers this check? If 3 months pass with no action, will anyone notice?" No explicit trigger → upgrade to must-do or delete
- **cases**: Phase 3 of a plan says "add tests as needed" — no trigger condition, still undone months later | "Do ROI analysis after 3 sprints" with no event trigger = never executed → convert to automatic stats in existing retro

### P24: Collection–Consumption Imbalance (building more, using less) [HOT] (0/0)

- **trigger**: System is already producing reports/proposals/stats/alerts; discussing "add more metrics"
- **check**: Ask "what is the consumption rate of existing outputs? How many items are in `pending_review`? When did someone last make a decision based on this data?" Don't add new metrics when consumption is zero
- **cases**: System produces weekly proposals — all sitting in pending review for months, none acted upon | Discussing "add quantitative metrics" while 3 months of existing raw data has never been analyzed

### P23: Unverified Assumption Escalated to "Fatal" Judgment (0/0)

- **trigger**: A technical capability claim is marked "fatal" or "proposal foundation collapses" during a challenge
- **check**: Before marking something "fatal," do a 10-second verification: run one command, check one doc, or run one test. An unverified "fatal" judgment = the most dangerous false negative
- **cases**: Asserting a capability "doesn't work in non-interactive mode" → rejects entire approach (scores 4/10) → actual test shows it works perfectly. Root cause: researcher output taken as fact without 10 seconds of verification

---

## 预算约束 (Budget Constraints)

- **Pattern cap**: ≤15 active patterns. When exceeded, merge similar patterns or retire the lowest-hit ones
- **Per pattern**: trigger + check + cases combined ≤4 lines
- **Retirement rule**: 10 consecutive challenges with no hit → move to "Retired" section (kept but not actively checked)
- **Merge rule**: Two patterns with >70% overlapping trigger scenarios → merge into one
- **Cleanup timing**: Review all patterns when the statistics table reaches 20 entries

---

## 已退役 (Retired — kept for reference, not actively checked)

- **P14**: Data layer stacking (same information duplicated across multiple data sources) — retired, low hit rate
- **P11**: External article authority not verified — retired, merged into P6 (data source not verified)
- **P15**: Process gate evaporated after compaction (rule exists but memory is gone) — retired, low hit rate
- **P18**: Migration loses detail (feature moved but incomplete) — retired, covered by P1 (incomplete enumeration)
- **P10**: Process bloat recursion (adding process to a process) — retired, covered by P19
- **P19**: Rule saturation zone — marginal return of adding rules diminishes — retired, meta-pattern fully understood

---

## 统计记录 (Statistics)

| Date | Challenge Topic | Patterns Hit | New Discoveries |
|------|----------------|-------------|----------------|
