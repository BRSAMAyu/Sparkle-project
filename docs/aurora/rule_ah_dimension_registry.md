# Rule AH Dimension Registry

Rule AH requires every dimension entering `source_state_v2` to be registered here before the encoder can consume it.

| Name | Source | Type | Value domain | TTL | SQAM evidence |
| --- | --- | --- | --- | --- | --- |
| `tool_category` | `routing_input.intent` | enum | `chat`, `plan`, `task`, `reflection`, `general` | turn | deterministic mapping; encoder stability tests |
| `sufficiency_level` | task/context sufficiency summaries | enum | `low`, `medium`, `high` | turn | deterministic threshold mapping; backfill tests |
| `conflict_outcome` | `state.context_data.unresolved_conflicts` + shadow comparison | enum | `clear`, `pending`, `resolved` | session | explicit state mapping; fallback coverage tests |
| `skill_domain` | active skill names / selected skill names | enum | `none`, `plan`, `focus`, `reflection`, `mixed` | turn | deterministic heuristics; router integration tests |
| `achievement_tier` | `achievement_summary` score + unlock count | enum | `none`, `emerging`, `active`, `advanced` | day | Stage 22 achievement wire baseline + encoder tests |
| `calendar_pressure` | `calendar_context` density + deadlines + exam urgency | enum | `none`, `low`, `medium`, `high` | day | Stage 22 calendar wire baseline + encoder tests |
| `cohort_segment` | `user_profile.goal_type` + `knowledge_level` | enum | `general`, `exam_beginner`, `exam_intermediate`, `exam_advanced`, `habit_beginner`, `habit_intermediate`, `habit_advanced`, `project_beginner`, `project_intermediate`, `project_advanced` | week | deterministic cohort mapping; Stage 22 cohort fallback tests |

## Enforcement

- Guard: `scripts/stage23/check_rule_ah_dimension_registry.py`
- Encoder source of truth: `backend/app/services/source_state_encoder.py`
- Unregistered dimensions: blocked at CI and blocked from runtime rollout
