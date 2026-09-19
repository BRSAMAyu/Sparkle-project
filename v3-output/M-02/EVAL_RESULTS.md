# M-02 Personalized Storage Gate — 写入场景评测基准

- 评测集：`backend/tests/fixtures/memory_storage_gate_eval_v1.json`（**64 场景**，五类分布 store 15 / event 12 / current_state 11 / ignore 14 / confirm 12；标签由任务卡语义人工标注，含重复陈述对 ig11a/b 与两组对抗样例 ev12/cf10）
- 口径：**规则层独跑**（`SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED=False`，语义层关闭；kill-switch 固定 live）——基准数字可复现、不依赖 LLM
- 复现：`cd backend && pytest tests/unit/test_memory_storage_gate_eval.py -q`（阈值守卫已固化：每类 precision/recall ≥1.0 才通过）
- 环境：wt8 @ 43942d23 + M-02 改动（含接续 worker 修复：ev06/cs02/ig04 三处漏判 + emo/困/渴 子串过匹配）
- 运行时间：2026-09-19

## 基准数字（rule 层）

| 类别 | n | precision | recall |
|---|---|---|---|
| store | 15 | **1.0000** | **1.0000** |
| event | 12 | **1.0000** | **1.0000** |
| current_state | 11 | **1.0000** | **1.0000** |
| ignore | 14 | **1.0000** | **1.0000** |
| confirm | 12 | **1.0000** | **1.0000** |
| **overall accuracy** | 64 | | **1.0000** |

### 规则命中分布（决策可审计性）

B2.user_stated_seed 2 · B3.structured_system_subject 3 · R1.malformed 2 · R2.explicit_user_command 2 · R3.banned_identity_label 1 · R4.sensitive_hypothesis 12 · R5.one_time_constraint 12 · R6.transient_state 11 · R7.noise 10 · R8.rapid_duplicate 1 · R9.stable_pattern 5 · R10.ambiguous_inferred 3

### 验收专项

- **瞬时 today constraint 不默认 global**：ev01（明早8点考试，due_at 锚定）与 ev09（今天下午3点实验课，无 due_at）均判 `event` + `bounded_scope`——落库时 decay 压至 `7d`/`due_at+7d` 短窗并打 `m02:event_bounded` tag，绝不作为全局长期事实长存（写路径断言见 `test_write_path_event_bounded_scope`）。
- **接续修复的三处漏判**（前任规则层 → 本轮修复）：ev06「6月15日要考四级」（日期锚点+轻动词，考虑/思考 经 lookaround 排除）、cs02「我今天状态不太好」（感受 token「状态」×时间标记组合）、ig04「嗯嗯知道了」（拼接应答整体消耗判定）。

### 对抗负例集（fixture 之外，已固化为单测 `test_memory_storage_gate.py`）

思考/考虑不误判 event（4 例）、否定/犹豫形态「要不要报名」不判 event、噪声前缀不吞内容（「对，我每天早上都跑步」）、稳定性标记压过状态 token（「最近状态一直很差」→store）、英文子串不误伤（「memory」不含独立「emo」）等 13 例全部通过。

### 语义层（真实 LLM）冒烟

见 REPORT.md §真实 LLM 冒烟（≤10 次调用；语义层默认关闭，仅对 R10 歧义残留生效，且不得自授权 confirm）。

## 逐场景结果

### store

| id | summary 期望=预测 | 命中规则 |
|---|---|---|
| m02-st01 | store=store OK | R9.stable_pattern |
| m02-st02 | store=store OK | R9.stable_pattern |
| m02-st03 | store=store OK | R10.ambiguous_inferred |
| m02-st04 | store=store OK | R2.explicit_user_command |
| m02-st05 | store=store OK | B2.user_stated_seed |
| m02-st06 | store=store OK | B3.structured_system_subject |
| m02-st07 | store=store OK | B3.structured_system_subject |
| m02-st08 | store=store OK | R10.ambiguous_inferred |
| m02-st09 | store=store OK | B3.structured_system_subject |
| m02-st10 | store=store OK | R9.stable_pattern |
| m02-st11 | store=store OK | R9.stable_pattern |
| m02-st12 | store=store OK | R9.stable_pattern |
| m02-st13 | store=store OK | R2.explicit_user_command |
| m02-st14 | store=store OK | B2.user_stated_seed |
| m02-ig11a | store=store OK | R10.ambiguous_inferred |

### event

| id | summary 期望=预测 | 命中规则 |
|---|---|---|
| m02-ev01 | event=event OK | R5.one_time_constraint |
| m02-ev02 | event=event OK | R5.one_time_constraint |
| m02-ev03 | event=event OK | R5.one_time_constraint |
| m02-ev04 | event=event OK | R5.one_time_constraint |
| m02-ev05 | event=event OK | R5.one_time_constraint |
| m02-ev06 | event=event OK | R5.one_time_constraint |
| m02-ev07 | event=event OK | R5.one_time_constraint |
| m02-ev08 | event=event OK | R5.one_time_constraint |
| m02-ev09 | event=event OK | R5.one_time_constraint |
| m02-ev10 | event=event OK | R5.one_time_constraint |
| m02-ev11 | event=event OK | R5.one_time_constraint |
| m02-ev12 | event=event OK | R5.one_time_constraint |

### current_state

| id | summary 期望=预测 | 命中规则 |
|---|---|---|
| m02-cs01 | current_state=current_state OK | R6.transient_state |
| m02-cs02 | current_state=current_state OK | R6.transient_state |
| m02-cs03 | current_state=current_state OK | R6.transient_state |
| m02-cs04 | current_state=current_state OK | R6.transient_state |
| m02-cs05 | current_state=current_state OK | R6.transient_state |
| m02-cs06 | current_state=current_state OK | R6.transient_state |
| m02-cs07 | current_state=current_state OK | R6.transient_state |
| m02-cs08 | current_state=current_state OK | R6.transient_state |
| m02-cs09 | current_state=current_state OK | R6.transient_state |
| m02-cs10 | current_state=current_state OK | R6.transient_state |
| m02-cs11 | current_state=current_state OK | R6.transient_state |

### ignore

| id | summary 期望=预测 | 命中规则 |
|---|---|---|
| m02-ig01 | ignore=ignore OK | R7.noise |
| m02-ig02 | ignore=ignore OK | R7.noise |
| m02-ig03 | ignore=ignore OK | R7.noise |
| m02-ig04 | ignore=ignore OK | R7.noise |
| m02-ig05 | ignore=ignore OK | R1.malformed |
| m02-ig06 | ignore=ignore OK | R1.malformed |
| m02-ig07 | ignore=ignore OK | R3.banned_identity_label |
| m02-ig08 | ignore=ignore OK | R7.noise |
| m02-ig09 | ignore=ignore OK | R7.noise |
| m02-ig10 | ignore=ignore OK | R7.noise |
| m02-ig11b | ignore=ignore OK | R8.rapid_duplicate |
| m02-ig12 | ignore=ignore OK | R7.noise |
| m02-ig13 | ignore=ignore OK | R7.noise |
| m02-ig14 | ignore=ignore OK | R7.noise |

### confirm

| id | summary 期望=预测 | 命中规则 |
|---|---|---|
| m02-cf01 | confirm=confirm OK | R4.sensitive_hypothesis |
| m02-cf02 | confirm=confirm OK | R4.sensitive_hypothesis |
| m02-cf03 | confirm=confirm OK | R4.sensitive_hypothesis |
| m02-cf04 | confirm=confirm OK | R4.sensitive_hypothesis |
| m02-cf05 | confirm=confirm OK | R4.sensitive_hypothesis |
| m02-cf06 | confirm=confirm OK | R4.sensitive_hypothesis |
| m02-cf07 | confirm=confirm OK | R4.sensitive_hypothesis |
| m02-cf08 | confirm=confirm OK | R4.sensitive_hypothesis |
| m02-cf09 | confirm=confirm OK | R4.sensitive_hypothesis |
| m02-cf10 | confirm=confirm OK | R4.sensitive_hypothesis |
| m02-cf11 | confirm=confirm OK | R4.sensitive_hypothesis |
| m02-cf12 | confirm=confirm OK | R4.sensitive_hypothesis |
