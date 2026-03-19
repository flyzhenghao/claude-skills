# critic

Quality control skill for Claude Code — code review, proof-by-contradiction challenge, retrospective, system health, and codebase-wide sweep.

## Quick Start

Copy this directory into `.claude/skills/critic/` (project) or `~/.claude/skills/critic/` (global).

## Commands

```
/critic review                          # Code review checklist
/critic challenge                       # Proof-by-contradiction with pattern memory
/critic retro                           # Retrospective + root cause analysis
/critic health                          # System health check
/critic sweep "<pattern>"               # Find all instances of a known bug pattern
/critic sweep --from-retro <file>       # Auto-derive sweep targets from a retro doc
```

## Pattern Library

`patterns/challenge-patterns.md` contains the bundled set of common design blind spots (P1–P24). The challenge mode loads this file automatically and appends new discoveries after each session. Hit counts start at 0/0 — you build your own statistics as you use it.

## Key Features

- **Challenge mode** has a 2-round self-review cap with explicit P9 sycophancy detection
- **Sweep mode** uses a 3-layer LLM-first + optional AST architecture validated on ≤50K LOC projects
- **Retro mode** includes a built-in falsification gate: every recommendation must survive "would this actually prevent recurrence?"
