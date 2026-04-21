# Aurora Stage 23 Source-State Design

Date: 2026-04-21
Stage: 23
Rule: AH

## Scope

Stage 23 freezes the first multidimensional `source_state_v2` contract used by Bayesian routing wire-on. The encoder is centralized in `backend/app/services/source_state_encoder.py`; no other module may mint new source-state dimensions ad hoc.

## Dimension Set

| Dimension | Source | Type | Allowed values | TTL |
| --- | --- | --- | --- | --- |
| `tool_category` | `routing_input.intent` | enum | `chat`, `plan`, `task`, `reflection`, `general` | turn |
| `sufficiency_level` | task/context sufficiency summaries | enum | `low`, `medium`, `high` | turn |
| `conflict_outcome` | `state.context_data` conflict hints | enum | `clear`, `pending`, `resolved` | session |
| `skill_domain` | active skill names / selected skill names | enum | `none`, `plan`, `focus`, `reflection`, `mixed` | turn |
| `achievement_tier` | `achievement_summary.total_achievement_score` + unlock count | enum | `none`, `emerging`, `active`, `advanced` | day |
| `calendar_pressure` | `calendar_context.workload_density` + deadlines + exam urgency | enum | `none`, `low`, `medium`, `high` | day |
| `cohort_segment` | `user_profile.goal_type` + `knowledge_level` | enum | `general`, `exam_beginner`, `exam_intermediate`, `exam_advanced`, `habit_beginner`, `habit_intermediate`, `habit_advanced`, `project_beginner`, `project_intermediate`, `project_advanced` | week |

## Encoding Rules

1. Canonical order is fixed:
   `tool_category`, `sufficiency_level`, `conflict_outcome`, `skill_domain`, `achievement_tier`, `calendar_pressure`, `cohort_segment`.
2. Encoded key format is pipe-delimited:
   `tool_category=plan|sufficiency_level=medium|...`
3. Unknown values are coerced to deterministic defaults, not dropped.
4. Legacy `state_{tool_category}` remains read-only fallback; Stage 23 writes `source_state_v2` and `source_state_v2_key` beside it.

## Budget Control

- Per-user source-state combination budget: `128`
- Priority order for keeping dimensions under budget:
  `tool_category` > `sufficiency_level` > `calendar_pressure` > `cohort_segment` > `skill_domain` > `achievement_tier` > `conflict_outcome`
- Pruning is deterministic and implemented in `prune_dimension_space_for_budget()`

## SQAM Notes

- ID1: every dimension has one registered source and one stable value domain.
- ST1: same inputs always produce the same encoded key.
- DP1: Stage 23 synthetic density artifact requires `>=150` decision→outcome pairs per synthetic user and `>=5` active dimensions.
- SM1: metrics exposed for encoder latency, routing outcome backfill latency, Bayesian recommendation events, and shadow divergence.
