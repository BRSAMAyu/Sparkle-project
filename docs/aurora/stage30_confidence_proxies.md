# Stage 30 Confidence Proxy Registry

Stage 30 only allows registered behavioral proxies. Unregistered proxies are forbidden in code and must fail CI.

## Registered Proxies

| proxy_id | Definition | Source | Window | Known Biases | Forbidden Interpretation |
| --- | --- | --- | --- | --- | --- |
| `revision_frequency` | Post-completion revision frequency as a low-confidence proxy | `tasks.updated_at` vs `tasks.completed_at` | Last 60 completed tasks | Large refactors inflate edits; collaborative work can revise more without lower confidence | Do not describe as perfectionism personality or procrastination identity |
| `self_correction_rate` | User-initiated correction rate as an uncertainty proxy | `memory_corrections` vs user chat volume | Last 90 days | Low volume is noisy; some corrections reflect system misunderstanding | Do not describe as anxiety personality or indecisive identity |
| `question_to_statement_ratio` | Question-heavy language as an inquiry proxy | `chat_messages.role=user` punctuation heuristic | Last 120 user turns | Domain and punctuation habits vary | Do not describe as dependent personality or low-confidence identity |
| `time_to_first_action` | Delay from plan creation to first action as a hesitation proxy | `plans.created_at` to earliest task action | Last 30 plans | Some plans are intentionally delayed; setup tasks can take longer | Do not describe as avoidance personality or laziness identity |
| `completion_vs_estimate_delta_sign` | Actual-vs-estimate direction as calibration proxy | `tasks.actual_minutes - tasks.estimated_minutes` sign | Last 60 completed tasks | Scope changes and interruptions can invert sign | Do not describe as optimistic personality or unrealistic identity |

## Rule AO Notes

- Proxy use is whitelist-only.
- Proxy outputs never become identity labels.
- Proxy outputs never route the user.
- Each proxy must support an independent env kill switch.
