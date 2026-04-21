# Rule AL PersDyn Dimensions

Stage 27 PersDyn attractor dimensions are hard-registered here. Only the five dimensions below may enter `persdyn_attractors` and `ForesightSnapshot.attractors`.

| Dimension | Definition | Signal window | Baseline | Variability | Recovery Rate | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `study_pace` | Daily study intensity | 3-day rolling study minutes | EMA with `alpha=0.1`: `ema_t = 0.1 * x_t + 0.9 * ema_(t-1)` | Population stddev over the latest 14 daily observations | `max(0, -slope(abs(x_t - baseline)))` over the same 14-day series | Derived from `StudyRecord.study_minutes` |
| `completion_rate` | Task completion ratio | 7-day rolling task completion ratio | Same EMA rule | Same 14-day stddev | Same residual-slope rule | Uses owner-scoped `Task` rows only |
| `engagement_level` | Interaction depth score | 3-day activity blend plus 7-day scene/reflection support | Same EMA rule | Same 14-day stddev | Same residual-slope rule | Blends study records, focus sessions, scene quality, reflections |
| `mood_valence` | Reflection-derived mood tendency | 7-day reflection category valence | Same EMA rule | Same 14-day stddev | Same residual-slope rule | Reflection categories map to fixed valence weights |
| `plan_adherence` | Plan follow-through | Ratio of non-overdue planned tasks | Same EMA rule | Same 14-day stddev | Same residual-slope rule | Uses plan-backed task overdue pressure |

## Confidence Rule

- Active days `< 14`: confidence is capped below `0.3`, so the attractor is persisted but filtered from live snapshot output.
- Active days `>= 14`: confidence grows linearly toward `0.95` within the 28-day lookback window.

## Guardrail

- Cross-user fitting is forbidden.
- Adding or renaming a PersDyn dimension requires updating this registry before code can ship.
