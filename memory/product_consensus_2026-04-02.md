---
name: Product Consensus 2026-04-02
description: Final product positioning, 90-day roadmap, and technical priorities after expert panel discussion
type: project
---

# Sparkle Product Consensus (2026-04-02)

## Positioning
- Short-term: "AI学习教练" (for competition, early users)
- Long-term: "AI成长操作系统" (brand, investors)
- Internal tech goal: "成长操作系统"
- Core principle: Sparkle不指出你不行，而是帮助你重新变得能走

## Core Loop
发现问题 → 以用户可接受的方式交付 → 用户愿意采纳 → 产生行动 → 验证有效 → 更新系统

## 6 Technical Breakpoints (from code audit)
1. adaptive_replanner results never consumed — adjustments calculated but never applied to plans
2. Error analysis updates profile signals, not knowledge node mastery — data flow direction wrong
3. plan health=critical doesn't publish events — warning signal lost
4. Push system only has time triggers, no behavioral triggers
5. cognitive_adjustments only change prompt text, not actual plan parameters
6. No post-intervention verification — system can't learn what works

## 90-Day Roadmap
- 0-20d: Fix breakpoint 2 (error→mastery) + breakpoint 1 (replanner→plan) + design intervention language system
- 21-50d: Fix breakpoint 3 (plan health events) + 4 (behavioral push) + A/B test intervention language
- 51-70d: Fix breakpoint 5 (parameter-level adjustments) + 6 (verification feedback loop)
- 71-90d: End-to-end polish + competition demo

## North Star (Staged)
- 0-30d: Key path completion rate
- 30-60d: Proactive correction adoption rate
- 60-90d: 7-day key bottleneck resolution rate

## Moat
- Short-term: Execution-layer embedding depth (focus timer, error logging, task-path linkage)
- Mid-term: Correction ability (detect earlier than user, deliver acceptably)
- Long-term: Longitudinal causal evidence chain

## Key Risk
User resistance to intervention. System must feel like a perceptive coach, not a critical teacher or taskmaster. Intervention language must trigger curiosity, not anxiety.

## Competition Demo
Single end-to-end scenario: student failing thermodynamics → system detects conceptual bottleneck → delivers intervention without triggering defensiveness → student fixes gap → system remembers what works
