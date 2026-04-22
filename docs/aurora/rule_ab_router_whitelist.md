# Rule AB Router Whitelist

| field | registered_at | source_stage | allowed_use | permanent_boundary |
| --- | --- | --- | --- | --- |
| `task_sufficiency_summary` | 2026-04-21 | Stage 20 | follow-up question selection | only the low-sufficiency clarification branch may read it |
| `context_sufficiency_summary` | 2026-04-21 | Stage 20 | prompt caveat rendering | never a Router branch condition |
| `active_skills_summary` | 2026-04-21 | Stage 21 | skill selection input | may not expand into generic profile-driven routing |
| `metacognition_profile` | 2026-04-22 | Stage 35 | derive `MetacognitionHintV1` only | raw profile may only be summarized into `accuracy/awareness/last_updated`; no dashboard/process payload or cross-user reads |

未登记字段默认禁止进入 Router 读取路径，包括但不限于：

- `achievement_summary`
- `calendar_context`
- `recent_reflections`
- `recent_scenes`
- `foresight_hint`
- `traits_prior`
- `srl_phase`
