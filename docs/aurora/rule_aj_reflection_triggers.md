# Aurora Rule AJ Reflection Trigger Registry

Version: v1
Frozen at: 2026-04-21T19:00:00+08:00

This registry is the single source of truth for Stage 25 reflection triggers.

| Category | Trigger Condition | Prompt Template Version | Env Toggle |
| --- | --- | --- | --- |
| `too_difficult` | Task feedback category is `too_difficult` and time spent > 10 minutes | `v1` | `AURORA_REFLECTION_TRIGGER_TOO_DIFFICULT` |
| `unclear` | Task feedback category is `unclear` and time spent > 10 minutes | `v1` | `AURORA_REFLECTION_TRIGGER_UNCLEAR` |
| `abandoned` | Task abandonment feedback is created for a plan-linked task | `v1` | `AURORA_REFLECTION_TRIGGER_ABANDONED` |
| `intervention_ineffective` | Intervention was accepted/seen/acted on, but outcome resolves to `INEFFECTIVE` | `v1` | `AURORA_REFLECTION_TRIGGER_INTERVENTION_INEFFECTIVE` |
| `plan_stall` | Outcome verifier resolves a `STALL_PATTERN` intervention to `UNKNOWN`/`INEFFECTIVE`, or repeated negative feedback shows no recovery | `v1` | `AURORA_REFLECTION_TRIGGER_PLAN_STALL` |
| `overload` | Outcome verifier resolves an `OVERLOAD` intervention to `UNKNOWN`/`INEFFECTIVE`, or overload evidence remains after the intervention window | `v1` | `AURORA_REFLECTION_TRIGGER_OVERLOAD` |

Rule AJ obligations:

1. New trigger categories must be added here before they enter `TaskReflectionService.ELIGIBLE_CATEGORIES`.
2. Every trigger must expose an independent env toggle.
3. Trigger outputs may consume only user-scoped route history slices.
