# WT393 · A-08 Aurora 纵向/消融评估 — 结果（程序化生成）

- spec `aurora_ablation_spec.v1` · metrics `aurora_ablation_metrics.v1` · 效用权重 `{'resolved_episode': 1.0, 'unresolved_episode': -1.0, 'wrong_followed_decision': -0.4, 'question': -0.15, 'control_intrusion': -0.6}`

## 四臂对照

| 指标 | full | no_memory | no_experience | fixed_policy | Δ(fixed−full) |
|---|---|---|---|---|---|
| stuck accuracy（预算内收敛率） | 0.45 | 0.55 | 0.45 | 0.3 | -0.15 |
| 收敛会话数均值 | 1.5556 | 1.4545 | 1.5556 | 1.5 | -0.0556 |
| 被跟随决策匹配分 | 0.1702 | 0.2558 | 0.1702 | 0.1176 | -0.0526 |
| 旅程面匹配分 | 0.1786 | 0.3333 | 0.1786 | None | None |
| chat 面匹配分 | 0.7368 | 0.625 | 0.875 | None | None |
| 对照侵入率 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 每段问句数 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 问后收敛命中率 | None | None | None | None | None |
| 不确定行动数 | 7 | 0 | 7 | 0 | -7 |
| 效用（冻结权重） | -9.2 | 0.0 | -9.2 | -24.8 | -15.6 |
| 每解决段会话成本 | None | None | None | None | None |

## 各臂明细

### full

- episodes 20（resolved 9 / failed 11），stuck accuracy **0.45**，收敛会话均值 1.5556
- allocation：followed 0.1702 · journey 面 0.1786 · chat 面 0.7368
- overpersonalization：对照侵入 0/25（rate 0.0），uncertain 行动 7
- clarification：问句 0（每段 0.0），ask_precision None
- cost：{"engine_call_sessions": 119, "chat_turns": 75, "journey_starts": 73, "questions": 0, "sessions_consumed": 47, "sessions_per_resolved_episode": 5.2222}
- utility：**-9.2**
- invariants：{"fixed_arm_zero_engine_calls": null, "budget_respected": true, "resolution_requires_match": true}

  persona 明细：

  | persona | episodes | resolved | accuracy | questions | intrusions |
  |---|---|---|---|---|---|
  | p01_experience_reinforce | 2 | 2 | 1.0 | 0 | 0 |
  | p02_experience_hysteresis | 2 | 1 | 0.5 | 0 | 0 |
  | p03_explicit_difficulty | 2 | 1 | 0.5 | 0 | 0 |
  | p04_ambiguous_weak | 2 | 1 | 0.5 | 0 | 0 |
  | p05_correction_loop | 2 | 0 | 0.0 | 0 | 0 |
  | p06_structural_gap | 2 | 0 | 0.0 | 0 | 0 |
  | p07_plan_drift_entry | 2 | 1 | 0.5 | 0 | 0 |
  | p08_skill_repeat | 2 | 2 | 1.0 | 0 | 0 |
  | p09_choice_feedback | 2 | 1 | 0.5 | 0 | 0 |
  | p10_quiet_then_tooling | 2 | 0 | 0.0 | 0 | 0 |

### no_memory

- episodes 20（resolved 11 / failed 9），stuck accuracy **0.55**，收敛会话均值 1.4545
- allocation：followed 0.2558 · journey 面 0.3333 · chat 面 0.625
- overpersonalization：对照侵入 0/25（rate 0.0），uncertain 行动 0
- clarification：问句 0（每段 0.0），ask_precision None
- cost：{"engine_call_sessions": 111, "chat_turns": 71, "journey_starts": 83, "questions": 0, "sessions_consumed": 43, "sessions_per_resolved_episode": 3.9091}
- utility：**0.0**
- invariants：{"fixed_arm_zero_engine_calls": null, "budget_respected": true, "resolution_requires_match": true, "no_memory_zero_corrections": true}

  persona 明细：

  | persona | episodes | resolved | accuracy | questions | intrusions |
  |---|---|---|---|---|---|
  | p01_experience_reinforce | 2 | 2 | 1.0 | 0 | 0 |
  | p02_experience_hysteresis | 2 | 2 | 1.0 | 0 | 0 |
  | p03_explicit_difficulty | 2 | 1 | 0.5 | 0 | 0 |
  | p04_ambiguous_weak | 2 | 1 | 0.5 | 0 | 0 |
  | p05_correction_loop | 2 | 1 | 0.5 | 0 | 0 |
  | p06_structural_gap | 2 | 0 | 0.0 | 0 | 0 |
  | p07_plan_drift_entry | 2 | 1 | 0.5 | 0 | 0 |
  | p08_skill_repeat | 2 | 2 | 1.0 | 0 | 0 |
  | p09_choice_feedback | 2 | 1 | 0.5 | 0 | 0 |
  | p10_quiet_then_tooling | 2 | 0 | 0.0 | 0 | 0 |

### no_experience

- episodes 20（resolved 9 / failed 11），stuck accuracy **0.45**，收敛会话均值 1.5556
- allocation：followed 0.1702 · journey 面 0.1786 · chat 面 0.875
- overpersonalization：对照侵入 0/25（rate 0.0），uncertain 行动 7
- clarification：问句 0（每段 0.0），ask_precision None
- cost：{"engine_call_sessions": 119, "chat_turns": 74, "journey_starts": 73, "questions": 0, "sessions_consumed": 47, "sessions_per_resolved_episode": 5.2222}
- utility：**-9.2**
- invariants：{"fixed_arm_zero_engine_calls": null, "budget_respected": true, "resolution_requires_match": true, "no_experience_zero_patches": true, "no_experience_zero_spine": true}

  persona 明细：

  | persona | episodes | resolved | accuracy | questions | intrusions |
  |---|---|---|---|---|---|
  | p01_experience_reinforce | 2 | 2 | 1.0 | 0 | 0 |
  | p02_experience_hysteresis | 2 | 1 | 0.5 | 0 | 0 |
  | p03_explicit_difficulty | 2 | 1 | 0.5 | 0 | 0 |
  | p04_ambiguous_weak | 2 | 1 | 0.5 | 0 | 0 |
  | p05_correction_loop | 2 | 0 | 0.0 | 0 | 0 |
  | p06_structural_gap | 2 | 0 | 0.0 | 0 | 0 |
  | p07_plan_drift_entry | 2 | 1 | 0.5 | 0 | 0 |
  | p08_skill_repeat | 2 | 2 | 1.0 | 0 | 0 |
  | p09_choice_feedback | 2 | 1 | 0.5 | 0 | 0 |
  | p10_quiet_then_tooling | 2 | 0 | 0.0 | 0 | 0 |

### fixed_policy

- episodes 20（resolved 6 / failed 14），stuck accuracy **0.3**，收敛会话均值 1.5
- allocation：followed 0.1176 · journey 面 None · chat 面 None
- overpersonalization：对照侵入 0/25（rate 0.0），uncertain 行动 0
- clarification：问句 0（每段 0.0），ask_precision None
- cost：{"engine_call_sessions": 0, "chat_turns": 0, "journey_starts": 0, "questions": 0, "sessions_consumed": 51, "sessions_per_resolved_episode": 8.5}
- utility：**-24.8**
- invariants：{"fixed_arm_zero_engine_calls": true, "budget_respected": true, "resolution_requires_match": true}

  persona 明细：

  | persona | episodes | resolved | accuracy | questions | intrusions |
  |---|---|---|---|---|---|
  | p01_experience_reinforce | 2 | 2 | 1.0 | 0 | 0 |
  | p02_experience_hysteresis | 2 | 2 | 1.0 | 0 | 0 |
  | p03_explicit_difficulty | 2 | 0 | 0.0 | 0 | 0 |
  | p04_ambiguous_weak | 2 | 0 | 0.0 | 0 | 0 |
  | p05_correction_loop | 2 | 0 | 0.0 | 0 | 0 |
  | p06_structural_gap | 2 | 0 | 0.0 | 0 | 0 |
  | p07_plan_drift_entry | 2 | 0 | 0.0 | 0 | 0 |
  | p08_skill_repeat | 2 | 2 | 1.0 | 0 | 0 |
  | p09_choice_feedback | 2 | 0 | 0.0 | 0 | 0 |
  | p10_quiet_then_tooling | 2 | 0 | 0.0 | 0 | 0 |


（内容摘要 sha256[:16] = 7334d4718d9e7120）
