# V4-I04 · diff_or_evidence_only（无动作仍可纠正与一次决策性澄清）

- 实现会话：wtI04（worktree `../wtI04`，分支 `agent/v4/i04`）
- base SHA：`be495611`（main 心跳#5）；本卡实现 commit：`2be0be2a`（`feat(v4): I04 无动作可纠正与一次决策性澄清`）
- 状态：实现 + 自测完成，**待独立审查（1 位，risk=normal）**；review_receipt.json 由实现会话如实标 PENDING，不自签通过

## 一句话

FIX97 落地：`backend/app/aurora/no_action_supplement.py`（新增契约层，零 IO 零模型）给 no_action/abstain/无提案面一个**恒可达的自由补充出口**（「还有什么情况需要我知道？」+ ≤2 个不同操作后果例子），补充作为用户主动证据重放既有 A-03 引擎（单一权威，不造第二诊断器）——no_action 是**可纠正状态不是终审**；临时约束（今天只有15分钟）显式会话作用域、**永久偏好写授权=空集**（结构保证）；自动澄清 ≤1 轮，已答仍想追问 → **出口斜坡**（直接说情况/保守可试方案/先暂停，不 surfaced 第二问）；纠正追踪内容寻址随 `context_data["friction_decision"]` checkpoint 持久（重开可见）。接线进 `FrictionChatWiringService`，行为开关 `NO_ACTION_CORRECTION_MODE`（默认 **off** = V3 链路零变化）。

## 差量（全部新增/插入；零删除既有断言或检查）

| 文件 | 变更 |
|---|---|
| `backend/app/aurora/no_action_supplement.py` | 新增：三面契约层（FIX97 补充入口/apply、临时约束分类+难度族守卫、一次澄清预算+出口斜坡+纠正追踪；import 期词表不变式） |
| `backend/app/services/friction_chat_wiring.py` | +接线（版本 v3→v4）：`_fresh_turn` no_action 面挂补充入口（含 FIX-49 门拦静默面）；`_answer_turn` 跳过/暂停封闭词表先行 + 已答一轮仍想追问 → `budget_declared_replay`（引擎自身 B1/B2/B3 出口）+ 出口斜坡 + 纠正追踪；live/shadow/off 三档 |
| `backend/app/config/settings.py` | +8 行：`NO_ACTION_CORRECTION_MODE: str = "off"`（off/shadow/live；未知值 fail-closed 按 off） |
| `backend/app/core/metrics.py` | +1 计数器：`sparkle_aurora_no_action_correction_total{surface,mode}` |
| `backend/app/orchestration/semantic_selector.py` | +6 行：I03 **O-2 移交闭合**——`_RULE_DECISION_TO_INTERVENTIONS` 干预名 import 期不变式（字面量漂移 import 即红） |
| `backend/tests/unit/test_no_action_supplement.py` | 新增 33 测（三验收面一正一反 + 接线三档 + I03 **O-1 移交闭合**：冻结语料快照 23 条直读重算零 mismatch） |
| `v4/04_tasks/tasks.json` | I04 状态流转（本 evidence commit） |

## 验收逐条（卡面，全部可失败）

1. **没有错误提案也能纠正并形成合法经验**：
   - 正例：`supplement_entry(outcome=None)`（连提案都没有）恒可达（`test_entry_available_without_any_proposal`）；`apply_free_supplement(prior=None)` 把「不是不会，是不知道怎么开始」翻转为 act/entry 提名并产出合法经验记录（封闭 scheme 证据引用 + 会话作用域 + 可撤回 + 写授权空集声明，`test_apply_free_supplement_without_prior_forms_legal_experience`）；用户主动补充不占系统追问预算（`test_supplement_does_not_consume_clarification_budget`）。
   - 反例（可失败）：act/ask 面入口必须缺席（`test_entry_absent_on_act_and_ask_surfaces`——各有既有通道，不双轨出面）；无证据补充不伪造行动翻转（`test_no_evidence_supplement_keeps_honest_uncertainty`）。
2. **今天15分钟不写永久偏好；「不是不会」不追难度**：
   - 正例：`classify_supplement_constraint("今天只有15分钟…")` → `{kind: time_budget_today, scope: this_session, permanent_preference_write: False}`；`SUPPLEMENT_WRITE_SURFACES == frozenset()` 冻结（本层对 A-05 patch/self-model 的写路径结构性不存在）；「其实不是太难了」→ `difficulty:太难了` 落否定注记零权重、出口归 dependency 不归 difficulty、守卫 True。
   - 反例（可失败）：每周/每次口径 fail-closed 返 None（`test_non_today_horizon_fail_closed`——多天枚举归 A-05 契约 owner，不猜）；否定词牌被计分（绕过引擎 FIX-110）→ `difficulty_not_chased` 返 False 即红（`test_difficulty_guard_catches_naive_wordmark_counting`）；正向难度自报是合法归因不误伤（`test_positive_difficulty_report_is_legitimate_not_chasing`）。
3. **澄清后行动改变依据可追踪，用户可跳过/暂停**：
   - 正例：live 档已答 1 个自动澄清轮（`V4_AUTO_CLARIFICATION_BUDGET=1`）引擎仍想追问 → 第二问不出面（`suppressed_second_ask` 注记）+ 出口斜坡（question 结构性恒 None）+ 追踪（前后出口/答句分支/reason 码/证据引用，`test_live_mode_suppresses_second_ask_with_exit_ramp`）；跳过 → pending 清除 + 保守可试方案或如实无行动（`test_skip_turn_clears_pending_with_conservative_or_honest_no_action`）；暂停 → 本域静默 + 追踪 `paused=True`（`test_pause_turn_is_visible_user_choice_not_failure`）；追踪内容寻址重放幂等 + `reopen_visible_via: context_data.friction_decision`（checkpoint 持久，重开可见，`test_trace_is_content_addressed_and_reopen_visible`）。
   - 反例（可失败）：保守方案无引擎 B1 reason 背书 → ValueError（`test_exit_ramp_rejects_fabricated_conservative_option`——本层零伪造第二诊断）；B2/B3 no_action 出口不包装成保守方案（`test_conservative_option_requires_engine_b1_endorsement`）。

## 三档行为（回滚 = 关旗标）

| 档位 | 行为 |
|---|---|
| `off`（默认） | 本卡零行为：无入口、无斜坡、无追踪、无跳过/暂停——V3 第二问链保持（`test_off_mode_keeps_v3_second_ask_chain` 钉死） |
| `shadow` | 指标+结构化日志留痕，payload 零变化（`test_shadow_mode_records_without_payload_change`） |
| `live` | 载荷出面；首次激活显式 WARN（I03 N-2 消费侧标识，一次性）+ 未知值 fail-closed 按 off（`test_live_mode_activation_warns_explicitly` / `test_unknown_mode_fails_closed_to_off`） |

## 与既有事实的关系（不重建 V3）

- **诊断真源唯一**：所有语义判定都是 `diagnose_friction`/`apply_question_answer` 引擎重放；本模块零词牌、零问题库、零权重复制（引擎预算常量 2/5 不动，`test_engine_session_budget_unchanged`；V4 的 ≤1 在 stuck-policy 消费层执行——引擎冻结面由 sha256 双钉测试保护）。
- **保守方案零伪造**：出口斜坡的保守可试方案只能取自引擎自身「预算已用完」B1 best-guess（J-05 同律），B2/B3 如实给纯斜坡。
- **I03 移交闭合**：O-1（语料快照零测试消费者 → 23 条直读重算 diff 零 mismatch 冻结，`test_o1_corpus_snapshot_recomputes_zero_mismatch`）、O-2（干预名 import 期不变式落 semantic_selector.py）、N-2 本卡面（live 激活显式 WARN + mode 维度 metric）；**O-3（钩子键集冻结断言）与 N-1/N-3 再移交**——本卡未消费 `semantic_selector` 两 context 键，键集断言应在真正挂消费时落地（归 V4-I07），见 limitations。
- 本卡无 DB 迁移、无 proto 变更、无生成文件改动、无 HEAVY、零真实模型调用。

## 交付物索引

`run_manifest.json`（命令/exit/环境/零模型预算声明，pin 实现 commit `2be0be2a`）、`test_results.json`（33 新测 + 6 面回归 660 passed 明细）、`review_receipt.json`（PENDING，待独立会话在集成 SHA 复验）、`limitations.md`。
