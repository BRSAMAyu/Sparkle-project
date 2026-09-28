# V4-D01 独立审查 receipt（一审 · wtD01R1）

- 审查对象：commit `8a6a5048`（branch `agent/v4/d01`，base `1a53b8c3`）——`backend/app/core/experience_event.py`（新 471 行）、`backend/app/services/experience_event_service.py`（新 293 行）、`intervention_lifecycle_wiring.py`（+10）、`intervention_record_service.py`（+31/-4）、两测试文件（31+13 测）、证据五件套、tasks.json 状态行
- 审查人：wtD01R1（未参与 D01 实现；只读审查 + 本 receipt，未 push）
- 卡标准：`Sparkle-project/v4/04_tasks/cards/V4-D01.md`（implementation · high · 2 位独立审查）
- 契约：`v4/evidence/V4-B05/contract_receipt_min.md` §3/§6（B05 DONE_REVIEWED）
- 方法：卡验收逐条对照 diff；E1–E4 逐条对实现行号；G1/G2 现状-增量语义比对（含 S07 裁决原文 `v4/03_intelligence/DATA_AND_GRAPH.md:4/7`）；幂等/重放/韧性按测试断言读语义；f507 回归面抽读 2 断言；**独立复跑两组测试**（环境：worktree 无 .env，`SECRET_KEY=<dummy>` + conftest 默认 REDIS_URL，sqlite 内存——与 run_manifest 环境注记一致）

---

## 1. G1/G2 缺口闭合 — CONFIRMED（边界如实声明）

**G1（交付即曝光）现状核实**：base 上 FIX-507 写面 1a 确实在 `mark_delivered`（服务端下发收敛点）落 D-05 `exposed` 漏斗锚点（`intervention_lifecycle_wiring.py:233-260`），后台/不可见下发计成"已曝光"。S07 裁决原文（DATA_AND_GRAPH.md:7 "dispatched/delivered……不等于用户看到"）确认该现状不可推导为"看到"。

**落地方式判定（审查要点 1 的直接回答）**：`exposure_basis=delivered` 本身**只是标注**（detail JSON 键，:250-251，无迁移无列），**语义分离由第二层承载**——新增 experience_event.v1 流只从 `mark_seen` 真实转场进入：

- 投影服务唯一生产调用点 = `intervention_record_service.py:164`（mark_seen 且非 already_seen）；`mark_delivered`/spine 下发路径零调用（全仓 grep 核实：`record_rendered_exposure` 仅此一处生产调用）。
- `mark_seen` 的既有生产调用方 = profile_transparency.py:255 / intervention_feedback_binding_service.py:384 / notification_center_service.py:1207，全部是用户侧读/反馈面，无一下发路径。
- 反向守卫有测试钉死：`test_delivery_alone_never_projects_presentation_event`（下发后 `EXPERIENCE_EVENT_TOPIC` 恒空 + exposed 行 detail 携 `exposure_basis=delivered`）、`test_invalid_rendered_surface_is_refused_not_normalized`（非法面拒收不静默归一）。

**边界（非缺陷，已在 limitations #7 如实登记）**：D-05 `exposed` 锚点仍按交付时刻落账（卡面明文"保留FIX507生产hook"；漏斗完整性门依赖 exposure 先行）；故**只读 exposed 行的既有漏斗/摘要消费方口径未切换**，delivered/rendered 分账需读侧按 detail 标注 + 新事件流联合。若未来要以 rendered 为唯一漏斗锚，属独立决策卡——本卡不夹带，判定合规。

**G2（真实渲染零记录）**：闭合。`mark_seen` 从单行转场（base 单行 :141-143）增为"真实转场 → experience_event.v1 投影"（:144-170）；无障碍等价曝光以封闭两值词表 `RENDERED_SURFACES={visual, accessibility}` 记录真实面，非法值拒收。

**S07 裁决尊重判定**：尊重。任何下发语义永不产出"看到"语义工件——下发只产交付回执（exposed 行，显式标注 basis），"看到"只产 rendered 事件（kind=state_confirmed + receipt_ref 挂权威回执）。无任何路径用下发冒充看到。

## 2. 契约符合性（E1–E4 + §6 投影纪律）— CONFIRMED（1 处解释性裁定，见 R1-RULING-1）

| 不变量 | 实现位置 | 判定 |
|---|---|---|
| E1 `state_confirmed ⇒ committed ∧ receipt_ref 必选` | `experience_event.py:401-402`（committed 强制）+ :397-400（RECEIPT_REF_REQUIRED_KINDS 构造期拒绝）；测试 `test_e1_*` 三例 | ✅ 无例外路径 |
| E2 `error ⇒ error_state 必选；committed ⇒ error_state=None`（双向互斥） | :403-412 双向检查；测试 `test_e2_*` 三例 | ✅ |
| E3/I1 事件无权限字段 | `to_dict` 键集冻结（:429-443）+ 测试断言 11 键精确集 + forbidden 词扫描 | ✅ 结构面封死 |
| E4/I3 ref scheme 封闭集拒绝 | :392-396（`EXPERIENCE_RECEIPT_REF_SCHEMES` 六元）；`test_e4_fabricated_ref_scheme_rejected` | ✅ 词表外 fail 而非降级 |
| I2 成功可溯源（双门） | 门一：构造期 :397-400；门二：服务期查证 D-05 exposed 行真实存在（:156-160 → `_get_authoritative_receipt` :211-228，`decision_id + user_id + event_type=exposed + not_deleted_filter`）；缺失 → `no_authoritative_receipt` 可观测降级，不产事件不伪造成功 | ✅ 双门真实落地（测试 `test_missing_authoritative_receipt_degrades_observably` 用删行模拟） |
| §6 commit_state 全函数投影（唯一真源 X-03） | `project_terminal_reason` :231-246：committed→(committed,None)、expired→(error,expired)、user_cancelled/user_rejected→None（跳过不产事件）、词表外→Refused；import 期断言 :167-174 与 `TERMINAL_REASON_VOCABULARY` 严格对齐 | ✅ 每终态恰一结局 |
| §6 `ACTION_INVALID_COMMAND` fail-loud | `project_error_state` :249-265 显式拒绝 + `ExperienceProjectionRefused`；import 断言映射集 = 6 值减该码；测试 `test_invalid_command_is_fail_loud_never_silently_mapped` + `len(ACTION_ERROR_CODES)==6` 钉源词表漂移 | ✅ R1-C3 断言机制化 |
| §3 词表冻结 | 七元 kind/五元 error_state/六元 subject/三元 modality/六 scheme 全部精确字面测试冻结（TestFrozenVocabularies） | ✅ 扩展即红 |
| §3 dedupe_key 公式 | `sha256(receipt_ref+kind+version_token)`（:203-209），与契约公式逐字节一致（测试硬编码期望值比对） | ✅ |

**R1-RULING-1（提请二审独立复核的解释性裁定，非缺陷）**：契约 §3 字面"commit_state 唯一真源 = X-03 权威回执的 TerminalReason/ACTION_ERROR_CODES"与本实现"intervention_lifecycle ref 以 D-05 exposed 行存在性为 committed 真源"存在字面张力。裁定**可接受**：(a) 契约自身把 `intervention_lifecycle://<decision_id>` 列入 receipt_ref 封闭 scheme 且允许 state_confirmed 使用——若 committed 只能源自 X-03 终态，该 scheme 对必选 ref 的 kind 永不可用，契约自相矛盾；(b) X-03 侧投影机制（terminal_reason/error_state 全函数 + INVALID_COMMAND fail-loud）已按契约实现且有测试，供 action_command 锚生产者使用（当前无生产调用方，属 F03/B06+ 面的待用机制，非死代码违规）；(c) I2 双门 + subject.type=intervention 不跨域冒充任务/记忆 committed。该适配点实现方已在 review_receipt.json suggested_challenge_points 首条自报，本审确认其论证成立；若二审判不成立，修正路径 = kind 词表 v1.x bump（contract-owner），与本卡无涉。

**E4"记安全遥测"补充核对**：本服务面跨对象向量不存在——subject 即调用方传入的 record 本身，回执查询强制 `user_id == record.user_id` 绑定（I3 属主校验在查询条件内）；record 归属校验保持既有 handler 层检查（硬规则 3 下游不因上游删检）。词表外 scheme 走结构拒绝。满足契约意图；refusal 走 info 级留痕 + `RenderedExposureResult.reason` 可观测。

## 3. 幂等/重放 — CONFIRMED

- **重复 mark_seen 短路**：`already_seen` 前置检查（:158-161）+ `_transition_acceptance` 同态 no-op（:549-550）→ 已 SEEN 不再挂投影。测试 `test_repeated_mark_seen_does_not_repeat_exposure` 断言发布数恒 1。
- **SNOOZED→SEEN 再渲染**：属新真实渲染，再次发布，但事件身份内容寻址（dedupe_key 不含时间）→ 同 event_id/dedupe_key，唯一曝光数恒 1。测试 `test_re_render_after_snooze_keeps_single_exposure_identity` 显式断言"两次发布、身份恒一"——语义正确（"该干预被真实渲染过"是单数事实）。
- **丢事件重放**：`replay_rendered_exposure` 按权威行重算，测试断言 event_id/dedupe_key 恒同且事件体逐字段恒等（issued_at 除外，如实注明投影时点可异）。`event_id` 派生 `eev_<sha256[:32]>` 与 `derive_lifecycle_event_id` 先例同风格。
- **decision_id 一致性（I2 门不会误伤）**：服务侧与交付侧共用 `build_record_decision_contract(record)`；`decision_id_or_compute` 确定性（aurora_decision.py:357-382），`input_context_hash=sha256("intervention_record:<record.id>")` 使 decision_id 逐 record 唯一，spine 面 hash 域不同（`directive:`）无碰撞面。
- **竞态备注（非阻塞）**：`already_seen` 为 check-then-act，并发重复 mark_seen 理论可双发布——但双发布携带同一内容寻址 event_id，消费方按 event_id 去重后曝光数仍为 1，与卡幂等判据（按唯一身份计）一致。设计上以身份幂等兜底并发，可接受。
- **降级不拖主业务**：回执缺失/发布失败/投影异常三路均不阻断 SEEN 转场（`record_rendered_exposure_safe` 韧性壳 + wiring 同款判例），各有测试。

## 4. FIX-507 三写面零破坏 — CONFIRMED

- 三写面接线（mark_delivered→exposure / accepted·dismissed·acted→response / 6h beat 扫描）**diff 零删改**；唯一交付面变化 = detail 增 `exposure_basis` 键（:250-251），无列/无迁移/无词表扩展（D-05 词表 seen/snoozed 仍未私扩）。
- f507 回归面在审：`test_f507_lifecycle_wiring.py` 9 测 + `test_intervention_lifecycle_service.py` 18 测 + 9 个 mark_seen 消费方模块，本审复跑 **98 passed in 100.75s**（与 run_manifest 声明的 11 模块组合逐一致）。
- **抽读两条断言核语义**（审查要点 4）：
  1. `test_delivery_exposure_idempotent_on_repeated_mark`（:111-133）：重复 mark_delivered 后按 decision_id 非空计 exposed 行数 `count == 1`——交付面幂等不回退，且 D01 的 detail 增键未破坏 `_insert_once` 幂等。
  2. `test_lifecycle_failure_does_not_break_delivery_transition`（:135-151）：monkeypatch `record_exposure` 抛 RuntimeError 后 `delivered.acceptance_status == DELIVERED`——韧性壳语义保持；与 D01 新增面衔接自洽（该失败场景下后续 mark_seen 走 `no_authoritative_receipt` 降级，有 D01 侧测试覆盖）。
- tasks.json 状态 = `in_progress`/`REVIEW_READY`/`NOT_RUN`，与 B05/B01 的 done/DONE_REVIEWED 词表衔接正确（审查会话销账，实现会话未自签——`review_receipt.json` reviews 为空属实）。

## 5. 复跑证据（本审独立执行，非转抄）

| 命令（cwd `wtD01/backend`） | 结果 |
|---|---|
| `python -m pytest tests/core/test_experience_event.py tests/services/test_experience_event_service.py -q` | **44 passed in 6.20s**（契约守卫 31 + 三态集成 13，与声明逐一致；测试函数逐一清点 31/13 属实） |
| `python -m pytest <11 消费方模块，同 run_manifest 组合> -q` | **98 passed in 100.75s** |
| `grep -rn "record_rendered_exposure" backend/app` | 生产调用点仅 `intervention_record_service.py:164`（mark_seen 面） |

环境注记：worktree 无 .env，需 `SECRET_KEY` 环境变量（Settings 导入期校验）；测试落 sqlite 内存（conftest :109），不触 dev DB。全量 tests/services（1018）与 mypy/ruff 未在本审重跑（本审范围 = 新测 + 消费方回归 + 抽验；声明数字与证据内部一致性已核，无矛盾信号）。

## 6. Limitations 如实性 — CONFIRMED

逐条核验 limitations.md 八条 + test_results.json honesty_notes：

- **WS Frame 归 contract-owner/F03**（#1）：属实——全 diff 无 proto/无 gen 改动；"移动端已能收到呈现事件"未被声明为事实。
- **无真实 a11y 上报方**（#4）：属实——三个 mark_seen 生产调用方均不传 rendered_surface，落默认 visual；accessibility 位已冻结有测试但无生产上报方，声明口径（"可被如实记录且不与 visual 混写"成立 / "已被记录"不可声明）诚实。
- **发布主题零消费方**（#2）、**无事件持久表**（#3，可重放设计使然）、**copy_key 内容归 F03**（#5）、**state_confirmed 词表适配**（#6，见上文 RULING-1）、**漏斗口径未切换**（#7）、**spine 面无 rendered 门**（#8）：全部与代码事实一致。
- 核心套件 36 errors（test_bert_intent_classifier transformers fixture）已声明为既有环境噪声并附 stash 基线对照方法；本审未复现该组（超出范围），无反证。

## 7. 总裁决

**APPROVE（一审通过；高风险卡待二审 wtD01R2 后方可销账 DONE_REVIEWED）**

- CHALLENGED：**无**。
- 提请二审重点复核 2 项（均为裁定/边界确认，非缺陷）：R1-RULING-1（state_confirmed×intervention_lifecycle 的 commit_state 真源解释）；§1 边界（exposed 锚点仍交付时刻，读侧分账依赖 detail 标注 + 新事件流——limitations #7 已声明，判定在卡边界内）。
- 非阻塞观察 2 条：mark_seen 新增一次前置 `_get_record` 读（与转场内读取重复，成本可忽略）；already_seen 竞态以内容寻址身份幂等兜底（§3 已述）。
