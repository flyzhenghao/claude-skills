// Token Budget Tracker
// 记录每个 Phase 的 token 消耗，提供降级建议

import * as fs from 'node:fs';
import * as path from 'node:path';

export type Tier = 'T0' | 'T1' | 'T2' | 'T3' | 'T4';

export const TIER_BUDGETS: Record<Tier, number> = {
  T0: 3_000,
  T1: 15_000,
  T2: 80_000,
  T3: 250_000,
  T4: 1_000_000,
};

export interface PhaseUsage {
  phase: string;
  inputTokens: number;
  outputTokens: number;
  model: string;
  timestamp: string;
}

export interface BudgetState {
  tier: Tier;
  budget: number;
  used: number;
  phases: PhaseUsage[];
  warningTriggered: boolean;
}

const DEFAULT_STATE_PATH = path.join(process.cwd(), 'meta', 'token-usage.jsonl');

export function logUsage(usage: PhaseUsage, statePath = DEFAULT_STATE_PATH): void {
  const dir = path.dirname(statePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(statePath, JSON.stringify(usage) + '\n');
}

export function loadUsage(statePath = DEFAULT_STATE_PATH): PhaseUsage[] {
  if (!fs.existsSync(statePath)) return [];
  return fs.readFileSync(statePath, 'utf-8')
    .split('\n')
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

export function summarize(tier: Tier, statePath = DEFAULT_STATE_PATH): BudgetState {
  const phases = loadUsage(statePath);
  const used = phases.reduce((s, p) => s + p.inputTokens + p.outputTokens, 0);
  const budget = TIER_BUDGETS[tier];
  return {
    tier,
    budget,
    used,
    phases,
    warningTriggered: used / budget >= 0.8,
  };
}

export function recommendDowngrade(state: BudgetState): string | null {
  if (state.used / state.budget < 0.8) return null;
  const map: Record<Tier, string> = {
    T0: '已超 T0 预算，结果异常 — 不应到达此情况',
    T1: 'T1 → T0：将剩余问题缩为单点 fact-check',
    T2: 'T2 → T1：跳过 Gemini DR，改用 WebSearch 快速综合',
    T3: 'T3 → T2：跳过 Phase 2.6 cross-validation，单 Pass 综合',
    T4: 'T4 → T3：跳过 Multi-Pass 综合，单 Opus 综合即可',
  };
  return map[state.tier];
}
