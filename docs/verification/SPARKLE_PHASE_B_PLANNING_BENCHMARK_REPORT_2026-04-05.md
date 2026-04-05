# Sparkle Phase B Planning Benchmark Report

> Date: 2026-04-05  
> Fixture: `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/fixtures/planning_benchmark_scenarios.json`  
> Raw results: `/Users/brsama/code/GitHub/Sparkle-project/docs/verification/SPARKLE_PHASE_B_PLANNING_BENCHMARK_RESULTS_2026-04-05.json`  
> Proof level: `benchmark_v1`  
> Human eval required: `yes`

## Completion Verdict

- Credible win profile: `yes`
- Phase B vs field: `5 wins / 1 ties / 2 losses`
- Tie margin: `0.01` overall-score points

## Variant Summary

| Variant | Average overall score | Scenario count |
| --- | ---: | ---: |
| `raw_baseline:dashscope_chat` | 0.7533 | 8 |
| `raw_baseline:deepseek_chat` | 0.7475 | 8 |
| `sparkle_current:dashscope_chat` | 0.7275 | 8 |
| `sparkle_phase_b:dashscope_chat` | 0.8119 | 8 |

## Scenario Outcomes

| Scenario | Winner | Winner score | Phase B outcome |
| --- | --- | ---: | --- |
| `phase_b_thermo_14_day_sprint` | `sparkle_current:dashscope_chat` | 0.8442 | `loss` |
| `phase_b_overloaded_urgent_user` | `sparkle_phase_b:dashscope_chat` | 0.8917 | `win` |
| `phase_b_materials_and_weak_spots` | `sparkle_phase_b:dashscope_chat` | 0.8208 | `win` |
| `phase_b_contradictory_self_report` | `sparkle_phase_b:dashscope_chat` | 0.8242 | `win` |
| `phase_b_vague_goal_needs_clarification` | `raw_baseline:dashscope_chat` | 0.6350 | `loss` |
| `phase_b_missed_execution_replan` | `sparkle_phase_b:dashscope_chat` | 0.8488 | `win` |
| `phase_b_high_readiness_full_plan` | `raw_baseline:dashscope_chat` | 0.8575 | `tie` |
| `phase_b_medium_readiness_provisional` | `sparkle_phase_b:dashscope_chat` | 0.8492 | `win` |

## Notes

- Phase B clears the benchmark bar: it leads the field on average and wins a majority of dossier comparisons.
- Scores are rubric-based deterministic evaluations over the live model outputs captured in the raw results artifact.
- This benchmark is proof v1: an automated regression and comparative signal, not the final source of product truth.
- Sparkle Phase B is compared as a system-level planning stack with compiled strategy shaping; the raw baselines remain direct dossier prompts.
