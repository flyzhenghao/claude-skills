---
name: critic
description: "Quality control — code review, challenge/proof-by-contradiction, retrospective, system health, codebase sweep"
version: 1.0.0
author: system
created: 2026-03-19
agents: [critic]
---

# Critic — Quality Control

## Core Capabilities

1. **Code Review** — type safety, error handling, security, dead code, consistency
2. **Challenge** — structured proof-by-contradiction with pattern memory; finds hidden assumptions and design blind spots
3. **Retrospective** — sprint/project/daily retro; root cause analysis; experience sedimentation
4. **System Health** — change detection, trend alerts, dependency audits
5. **Sweep** — starting from a known bug/root cause, systematically scan the codebase for all instances of the same class of problem

---

## Installation

Copy this skill directory into your project's `.claude/skills/critic/` or your global `~/.claude/skills/critic/`. Claude Code will load it automatically when you invoke `/critic`.

The bundled pattern library lives at `patterns/challenge-patterns.md` relative to this file.

---

## Quick Usage

| Command | What it does |
|---------|-------------|
| `/critic review` | Code review — type safety, error handling, tests, security, dead code |
| `/critic challenge` | Challenge/proof-by-contradiction (loads pattern library automatically) |
| `/critic retro` | Retrospective — root cause analysis, experience sedimentation |
| `/critic health` | System health check — stale files, broken deps, config drift |
| `/critic sweep "<pattern>"` | Scan codebase for all instances of a known bug pattern |
| `/critic sweep --from-retro <file>` | Auto-derive sweep targets from a retro document |

Free-form descriptions work equally well — the keywords above are not mandatory.

> **After `/critic health`**: If you suspect context overhead is abnormal (session slowing, frequent compaction), run `/token-optimizer` as a complement. The two are complementary: `health` checks project code health, `token-optimizer` checks Claude's own config health.

---

## Code Review Checklist

- [ ] **Type safety**: No untyped `any`, no unsafe casts (unless commented)
- [ ] **Error handling**: fetch calls have error boundaries; async functions have try/catch
- [ ] **Tests**: Modified/added `.tsx` files have corresponding `.test.tsx`
- [ ] **Security**: No XSS vectors, no hardcoded secrets
- [ ] **Dead code**: No unused imports, variables, or functions
- [ ] **Consistency**: Naming style and file structure match project conventions

---

## Challenge Mode — Execution Steps

Invoked by `/critic challenge`. Uses **pattern memory** to apply known blind spots to the current proposal.

1. **Load pattern library**: Read `patterns/challenge-patterns.md` (bundled with this skill).
   - **Budget check**: Count active patterns (`### P` entries, excluding the retired section). If >15 → warn: "⚠️ challenge-patterns.md has N active patterns (budget ≤15). Consider retiring the lowest-hit ones." List the 3 lowest-hit patterns as retirement candidates.
2. **Per-pattern sweep**: For each pattern, check whether the current proposal triggers it.
   - Hit → label `[KNOWN P1]` etc. + provide the specific check item
   - New discovery → label `[NEW]`
3. **Free-form falsification**: Open-ended proof-by-contradiction not limited to known patterns (preserves free reasoning).
4. **Convergence check**: "Did this round produce actionable new information that the previous round didn't?" If only attacking the same point at the level of detail → declare convergence and give a final verdict.
5. **Scoring (with confidence anchoring)**: Give an N/10 score + key findings summary. **Attach a 1-10 confidence to each major claim** (e.g., `[C8] incremental value of X is low`). This confidence is the anchor for anti-flip checks.
6. **Anti-flip check (triggered when user challenges a claim)**: Before changing a position:
   - Show before/after confidence (e.g., `C8→C5`)
   - Give a reason independent of the user's opinion (new evidence/new angle — not "the user said so")
   - If confidence drops >3 with no new evidence → output `⚠️ P9 suspected sycophantic flip, maintaining original: [claim]`
   - Allowed flips: user provides a fact, data point, or counterexample not previously considered
7. **Sedimentation**: After challenge completes, append any `[NEW]` discoveries to the "New pattern append area" at the end of `patterns/challenge-patterns.md` and update hit counts.

**Recursive challenge constraints**:
- Same AI self-review cap: **2 rounds**. After round 2, declare P9 risk (same-source amplification) and recommend the user decide whether to continue or introduce external input (different model / human judgment / empirical data).
- Recursive challenges only record the **final round** in `challenge-patterns.md`; intermediate rounds are not sedimented.

---

## Retrospective Mode

**Before emitting each recommendation, run one internal falsification round:**

> "If this recommendation were followed, would the problem truly not recur?"

- If the answer is **a capability problem** (model reasoning depth, knowledge gap) → a rule or process won't fix it. Say so directly and recommend adjusting the model or approach instead.
- If the answer is **a process problem** (could be done but wasn't reminded) → a rule is valid; recommend it.
- **Prohibit** recommendations that "sound useful but can't survive a single follow-up question."

**Standard retro phases**:

- **Phase 1**: What happened? (timeline, facts, no judgment)
- **Phase 2**: Root cause analysis (5 Whys or equivalent)
- **Phase 3**: Actionable recommendations (each must survive the falsification check above)
- **Phase 4**: Sweep candidates (bugs/UX issues with clear root causes → feed into `/critic sweep`)
- **Phase 5**: Experience sedimentation (patterns worth recording for future use)

---

## Sweep Mode — Find All Instances of a Known Bug

### Purpose

Starting from a known bug or root cause, systematically scan the codebase to find all instances of the same class of problem. One bug surfaces a batch of same-origin issues for batch repair.

> **Design principle**: LLM-first architecture. On projects ≤50K LOC, LLM semantic understanding accuracy (~80% true positive rate, ~19% false positive rate) substantially outperforms pure AST tools (~30% true positive rate, ~70% false positive rate), because AST cannot understand business context. AST tools (ts-morph/Semgrep) are an **optional downstream acceleration layer**, introduced only when a specific pattern appears frequently enough to warrant second-level scanning.

### Syntax

```
/critic sweep "<pattern_description>" [--glob "*.tsx"]
/critic sweep --from-retro path/to/retro.md
```

### Architecture: Three-Layer Hybrid (LLM-first + optional AST)

```
Layer 1: Smart file discovery (Glob + Grep, deterministic, seconds)
  → Choose search strategy based on root cause type
  → Difference method: Grep "calls that should exist" vs "calls that do exist"
  → Output: candidate files + line numbers

Layer 2: LLM semantic review (Claude deep-read, minutes)
  → For each Layer 1 candidate: Read ±50 lines of context
  → With root cause in hand, make business logic judgment:
    "Is this absence a real bug or intentional design?"
  → Output: HIGH / MEDIUM / LOW / FALSE_POSITIVE

Layer 3: Optional AST acceleration (ts-morph / Semgrep, on-demand)
  → Trigger: a pattern recurs across ≥2 sprints/cycles
  → Write ts-morph script or Semgrep rule for that pattern
  → Use for pre-commit or CI-level continuous detection
  → Store scripts in: scripts/sweep/<pattern-name>.ts
```

### Execution Flow

**Step 1: Root cause → scan strategy**

Translate a natural-language root cause into search queries. Core techniques: **difference method** and **path semantics**.

```
Root cause: "PUT handler modifies shared data without notifying downstream consumers"
↓ Derive
  1. Glob "src/app/api/**/route.ts" → all route files
  2. Grep "export async function (PUT|PATCH)" → all mutation handlers
  3. Grep "emit|revalidate|broadcast" in same files → ones that do notify
  4. Difference = candidates for deep read
  5. Use path semantics during deep read: /admin/ routes often don't need real-time notification
```

Each root cause generates 1-3 Grep/Glob queries. For patterns that can't be matched on a single line (e.g., "await without try-catch"), skip Grep and go directly to Layer 2.

**Step 2: Layer 1 filter + Layer 2 deep read**

1. **Glob + Grep filter**: Narrow candidates (200 files → 10-20 files)
2. **Deep-read judgment**: For each candidate, Read key context and make semantic judgment against the root cause:
   - `HIGH` — confirmed hit, same root cause as original bug, needs fix
   - `MEDIUM` — possible hit, needs human confirmation or more context
   - `LOW` — suspected, but has mitigations or different scenario
   - `FALSE_POSITIVE` — initial filter matched but actually not a problem (already fixed, intentional design)

**Deep-read quality key**: Judgment must consider business context, not just structure. Ask:
- "Would this absence cause a problem in the user's actual usage scenario?"
- "Is this a real-time user-facing feature or a background admin operation?"
- "Is there another mechanism that compensates for this absence (polling, page refresh)?"

**Step 3: Output report**

```markdown
## Sweep Report: <pattern_description>

### Root Cause
<root cause description from retro>

### Scan Strategy
- Glob: `<pattern>` → N files
- Grep 1: `<pattern>` → M candidates
- Grep 2 (difference): `<pattern>` → K missing

### Hits (N total)

| # | File:Line | Confidence | Description | Suggested Fix |
|---|-----------|------------|-------------|---------------|
| 1 | src/api/items/[id]/route.ts:40 | HIGH | PUT modifies shared state, no downstream notification | Add broadcast call |
| 2 | src/api/tasks/[id]/complete/route.ts:13 | HIGH | Completion handler skips notification to subscribers | Add notify call |

### Stats
- Files scanned: X
- Initial candidates: Y
- Deep-read confirmed: HIGH a / MEDIUM b / LOW c / FP d
```

**Report ordering**: HIGH first. Limit LOW entries to 5 max to avoid noise.

### `--from-retro` Auto-Derivation

Reads the root cause analysis phase of a retro file and auto-derives scan strategies for each `bug`/`ux` type entry with clear root cause analysis.

**Scope**: Only process entries typed `bug` or `ux` with explicit root cause analysis. Feature requests, requirement clarifications, and priority changes are skipped.

**Concurrency limit**: If >3 root causes, select the 3 with the largest impact scope; record the rest as patterns without scanning.

### Layer 3 AST Acceleration (on-demand)

**Trigger**: A pattern recurs in ≥2 sprints/cycles, or pre-commit level continuous detection is needed.

**Introduction**:
1. Write `scripts/sweep/<name>.ts` (ts-morph) or `.semgrep/rules/<name>.yaml`
2. Script outputs JSON candidate list; LLM still makes final judgment
3. Register in sweep workflow (SKILL.md doesn't need modification; script acts as Layer 1 replacement/accelerator)

**Scenarios well-suited to AST**:
- Structural checks (functions missing try-catch, exports missing specific decorator) — Semgrep rules optimal
- Type-level analysis (distinguishing PrismaClient.update from plain .update) — ts-morph optimal
- Bulk schema validation (Prisma model missing required fields) — simple regex sufficient

**Scenarios where LLM deep-read is better**:
- Requires understanding business context (admin operation vs. real-time user-facing)
- Requires judging "intentional design vs. bug" (fire-and-forget telemetry vs. swallowed error)
- Cross-module data flow analysis (Semgrep CE doesn't support cross-file; ts-morph requires custom recursion)

### Sweep Outputs

- Report to stdout; summary appended to retro Phase 4
- Sweep items added to work plan marked `SWEEP_ADDED` (cap: 2 items; excess goes to backlog)

---

## Parameter Quick Reference

| Parameter | Purpose |
|-----------|---------|
| `review` | Code review (type safety, error handling, test coverage, security, dead code) |
| `challenge` | Challenge/proof-by-contradiction (auto-loads pattern library) |
| `retro` / `retrospective` | Retrospective — root cause analysis, pattern sedimentation |
| `health` | System health check (change detection, trend alerts) |
| `sweep` | Codebase-wide scan from a known root cause |
| Free description | Keywords above are not mandatory; direct description of the task works |
