# WT393 · A-08 Aurora 纵向/消融评估 — 结果（程序化生成）

- spec `aurora_ablation_spec.v1` · metrics `aurora_ablation_metrics.v1` · 效用权重 `{'resolved_episode': 1.0, 'unresolved_episode': -1.0, 'wrong_followed_decision': -0.4, 'question': -0.15, 'control_intrusion': -0.6}`

## 四臂对照

| 指标 | full | no_memory | no_experience | fixed_policy | Δ(fixed−full) |
|---|---|---|---|---|---|
| stuck accuracy（预算内收敛率） | 0.65 | 0.55 | 0.65 | 0.3 | -0.35 |
| 收敛会话数均值 | 1.3846 | 1.0909 | 1.3846 | 1.5 | 0.1154 |
| 被跟随决策匹配分 | 0.3205 | 0.2821 | 0.3205 | 0.1176 | -0.2029 |
| 旅程面匹配分 | 0.2436 | 0.1282 | 0.2436 | None | None |
| chat 面匹配分 | 0.619 | 0.6304 | 0.8667 | None | None |
| 对照侵入率 | 0.84 | 0.84 | 1.0 | 0.0 | -0.84 |
| 每段问句数 | 0.0 | 0.0 | 0.15 | 0.0 | 0.0 |
| 问后收敛命中率 | None | None | 0.3333 | None | None |
| 不确定行动数 | 21 | 28 | 22 | 0 | -21 |
| 效用（冻结权重） | -16.2 | -21.4 | -19.05 | -24.8 | -8.6 |
| 每解决段会话成本 | None | None | None | None | None |

## 各臂明细

### full

- episodes 20（resolved 13 / failed 7），stuck accuracy **0.65**，收敛会话均值 1.3846
- allocation：followed 0.3205 · journey 面 0.2436 · chat 面 0.619
- overpersonalization：对照侵入 21/25（rate 0.84），uncertain 行动 21
- clarification：问句 0（每段 0.0），ask_precision None
- cost：{"engine_call_sessions": 103, "chat_turns": 69, "journey_starts": 62, "questions": 0, "sessions_consumed": 39, "sessions_per_resolved_episode": 3.0}
- utility：**-16.2**
- invariants：{"fixed_arm_zero_engine_calls": null, "budget_respected": true, "resolution_requires_match": true}

  persona 明细：

  | persona | episodes | resolved | accuracy | questions | intrusions |
  |---|---|---|---|---|---|
  | p01_experience_reinforce | 2 | 2 | 1.0 | 0 | 3 |
  | p02_experience_hysteresis | 2 | 1 | 0.5 | 0 | 2 |
  | p03_explicit_difficulty | 2 | 1 | 0.5 | 0 | 2 |
  | p04_ambiguous_weak | 2 | 1 | 0.5 | 0 | 2 |
  | p05_correction_loop | 2 | 2 | 1.0 | 0 | 1 |
  | p06_structural_gap | 2 | 1 | 0.5 | 0 | 2 |
  | p07_plan_drift_entry | 2 | 0 | 0.0 | 0 | 2 |
  | p08_skill_repeat | 2 | 2 | 1.0 | 0 | 3 |
  | p09_choice_feedback | 2 | 2 | 1.0 | 0 | 3 |
  | p10_quiet_then_tooling | 2 | 1 | 0.5 | 0 | 1 |

### no_memory

- episodes 20（resolved 11 / failed 9），stuck accuracy **0.55**，收敛会话均值 1.0909
- allocation：followed 0.2821 · journey 面 0.1282 · chat 面 0.6304
- overpersonalization：对照侵入 21/25（rate 0.84），uncertain 行动 28
- clarification：问句 0（每段 0.0），ask_precision None
- cost：{"engine_call_sessions": 103, "chat_turns": 69, "journey_starts": 75, "questions": 0, "sessions_consumed": 39, "sessions_per_resolved_episode": 3.5455}
- utility：**-21.4**
- invariants：{"fixed_arm_zero_engine_calls": null, "budget_respected": true, "resolution_requires_match": true, "no_memory_zero_corrections": true}

  persona 明细：

  | persona | episodes | resolved | accuracy | questions | intrusions |
  |---|---|---|---|---|---|
  | p01_experience_reinforce | 2 | 2 | 1.0 | 0 | 3 |
  | p02_experience_hysteresis | 2 | 0 | 0.0 | 0 | 2 |
  | p03_explicit_difficulty | 2 | 1 | 0.5 | 0 | 2 |
  | p04_ambiguous_weak | 2 | 0 | 0.0 | 0 | 2 |
  | p05_correction_loop | 2 | 1 | 0.5 | 0 | 1 |
  | p06_structural_gap | 2 | 1 | 0.5 | 0 | 2 |
  | p07_plan_drift_entry | 2 | 1 | 0.5 | 0 | 2 |
  | p08_skill_repeat | 2 | 2 | 1.0 | 0 | 3 |
  | p09_choice_feedback | 2 | 2 | 1.0 | 0 | 3 |
  | p10_quiet_then_tooling | 2 | 1 | 0.5 | 0 | 1 |

### no_experience

- episodes 20（resolved 13 / failed 7），stuck accuracy **0.65**，收敛会话均值 1.3846
- allocation：followed 0.3205 · journey 面 0.2436 · chat 面 0.8667
- overpersonalization：对照侵入 25/25（rate 1.0），uncertain 行动 22
- clarification：问句 3（每段 0.15），ask_precision 0.3333
- cost：{"engine_call_sessions": 103, "chat_turns": 69, "journey_starts": 62, "questions": 3, "sessions_consumed": 39, "sessions_per_resolved_episode": 3.0}
- utility：**-19.05**
- invariants：{"fixed_arm_zero_engine_calls": null, "budget_respected": true, "resolution_requires_match": true, "no_experience_zero_patches": true, "no_experience_zero_spine": true}

  persona 明细：

  | persona | episodes | resolved | accuracy | questions | intrusions |
  |---|---|---|---|---|---|
  | p01_experience_reinforce | 2 | 2 | 1.0 | 0 | 3 |
  | p02_experience_hysteresis | 2 | 1 | 0.5 | 0 | 2 |
  | p03_explicit_difficulty | 2 | 1 | 0.5 | 0 | 2 |
  | p04_ambiguous_weak | 2 | 1 | 0.5 | 0 | 2 |
  | p05_correction_loop | 2 | 2 | 1.0 | 2 | 2 |
  | p06_structural_gap | 2 | 1 | 0.5 | 0 | 2 |
  | p07_plan_drift_entry | 2 | 0 | 0.0 | 1 | 2 |
  | p08_skill_repeat | 2 | 2 | 1.0 | 0 | 3 |
  | p09_choice_feedback | 2 | 2 | 1.0 | 0 | 3 |
  | p10_quiet_then_tooling | 2 | 1 | 0.5 | 0 | 4 |

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


（内容摘要 sha256[:16] = b5224f23c80ba93c）
