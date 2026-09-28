# V4-D01 二审 receipt（独立审查 #2）

- **审查会话**：wtD01R2（未参与 D01 实现与一审；本文件为全部二审产物）
- **日期**：2026-09-28
- **审查基线**：branch `agent/v4/d01`，实现 commit `8a6a5048`（base `1a53b8c3`）
- **契约真源**：`v4/evidence/V4-B05/contract_receipt_min.md` §3（experience_event.v1：E1–E4、receipt_ref 双门、commit_state=X-03 唯一真源、ACTION_INVALID_COMMAND fail-loud）+ §6（五错误态投影全函数）
- **方法**：只读审查 + 独立复跑 + 独立反例探针（临时测试文件，运行后即删，未入库未提交）。已读一审 `review_receipt.json` 登记的 3 条 suggested_challenge_points，但以下判定全部独立作出。

## 0. 总裁决：**APPROVE**（CHALLENGED 4 项，均非阻塞，见 §7）

高风险卡独立审查 #1/#2 双审齐后可销账。实现与 B05 冻结契约逐项对得上，无静默吞错路径，无第二权威，无越权面。

## 1. 独立靶 1：投影器正确性压力面 — ✅ PASS（含 2 项独立探针补充）

除读实现与既有 44 测外，另以临时探针独立验证测试未覆盖的边缘序列（探针文件已删）：

| 边缘序列 | 行为 | 判定 |
|---|---|---|
| 乱序 mark_seen（CREATED→SEEN） | `_ensure_transition_allowed` 抛 `ValueError`（fail-loud），**零事件发布、状态不变**；与改动前 `mark_seen` 行为逐点一致（旧实现同样直接抛），非 D01 引入的回退 | ✅ 探针独立证实 |
| 逆向 mark_delivered（SEEN→DELIVERED） | 同上 fail-loud；SEEN 时已发布的 1 条呈现事件不被追加 | ✅ 探针独立证实 |
| 重复 mark_seen（已 SEEN） | `already_seen` 短路 → 挂勾不触发 → 恰 1 条事件（`test_repeated_mark_seen_does_not_repeat_exposure`） | ✅ |
| SNOOZED→SEEN 再渲染 | 挂勾再触发，2 次发布**同 event_id/dedupe_key**（内容寻址身份恒一，唯一曝光数=1）；消费侧去重归 F03（契约原文），与实现分工一致 | ✅ |
| receipt_ref 悬空（exposed 行被清） | `no_authoritative_receipt` 可观测拒绝：不产事件、不伪造成功、SEEN 转场照常 | ✅ 测试钉死 |
| **跨用户回执**（他人 user_id 的同 decision_id exposed 行） | gate 查询 `user_id == record.user_id` + 未软删过滤 → 拒绝（`no_authoritative_receipt`），零事件——I3 用户绑定真实生效 | ✅ 探针独立证实 |
| commit_state 非法枚举 / 词表外 kind/scheme/modality/copy_key | `ExperienceEventValidationError` 构造期拒绝，无静默归一（`test_closed_vocabulary_violations_rejected` 等） | ✅ |
| rendered_surface 非法值 | `rendered_surface_invalid` 拒收不归一（不静默折成 visual） | ✅ |
| 投影/发布异常 | 韧性壳 `record_rendered_exposure_safe` 只 warning + 返回 None，SEEN 转场永不拖垮（`test_publish_failure_does_not_break_seen_transition` 佐证宿主总线不受染） | ✅ |

词表封闭性由 `test_experience_event.py` 精确字面冻结（新成员不改测试即红），词表外值全部 fail-loud 或显式 refused，**未发现任何静默吞错路径**。

## 2. 独立靶 2：事件身份内容寻址 — ✅ PASS

- `dedupe_key = sha256(receipt_ref + kind + subject.version_token)`（契约公式冻结，测试对字面公式逐字节断言）；`event_id = "eev_" + sha256(json{schema,dedupe_key})[:32]`。
- **派生输入无任何非确定因素**：时间（issued_at/expires_at）、uuid、随机量均不进派生；`test_event_id_is_deterministic_and_time_independent` 用 2026 与 2030 两个 issued_at 证明恒同；`test_lost_event_replays_to_identical_identity` 证明重放事件体除 issued_at 外逐字段恒等。
- 身份唯一性的存储层机制：事件本身无持久化表（limitations #3 如实登记），幂等由 (a) 内容寻址恒同 id + (b) `mark_seen` 仅真实转场挂勾 + (c) D-05 exposed 行 DB 唯一约束 `(decision_id, event_type, dedupe_subkey)` 三层构成。**同内容重放不产生重复事件行**在当前交付面成立（无事件表可重复）；消费侧重播抑制按契约归 F03（event_id 键位已冻结）。
- 小注（非阻塞）：契约公式不含 subject.id（冻结如此）；实践中 `decision_id` 内容寻址 `intervention_record:<record.uuid>`（`build_record_decision_contract` 实读），decision↔record 为 1:1，不同 record 撞同身份的场景理论化。`str(record.content_version or "1")` 兜底仅在 content_version 空值时与字面 "1" 别名——`create_record` 默认恒 "1"，实际不可达。

## 3. 独立靶 3：生产接线完备性 — ✅ PASS

全仓 grep（`mark_seen` / `InterventionAcceptanceStatus.SEEN` / `record_rendered_exposure` / `acceptance_status =` 赋值面）：

- **SEEN 写入唯一收敛点**：全部经 `InterventionRecordService._transition_acceptance` 状态机；**零处**直接 `acceptance_status = SEEN` 赋值（其余 20+ 处 SEEN 引用均为读侧过滤/分析桶，逐点核过：notification_analytics / outcome_verifier / health_intervention_bridge / feedback_binding / notification_center）。
- **生产 mark_seen 调用面 3 处全部走新入口**：`notification_center_service.py:1207`（仅 DELIVERED 态放行）、`profile_transparency.py:255`（CREATED→delivered→DELIVERED→seen 顺序守卫）、`intervention_feedback_binding_service.py:384`（CREATED 先补 delivered）。三处均因 keyword-only 默认参数零改动兼容。
- **无绕过路径**：`record_rendered_exposure` 生产调用仅 `mark_seen` 挂点 1 处；`experience_event` 写面仅新 2 文件；`mark_delivered`/spine 下发路径零调用投影器（`test_delivery_alone_never_projects_presentation_event` 钉死）。
- notification center 无 bus 形态（一审 challenge #2）：`InterventionRecordService(self.db)` event_bus=None → 投影成立、发布跳过（`published=False`），落点 = 可重放兜底（`replay_rendered_exposure`，`test_mark_seen_without_event_bus_still_transitions_and_projects` 钉死）。与「本卡只落服务面、WS Frame 归 contract-owner」的边界声明一致——**满足**。

## 4. 独立靶 4：X-03 唯一真源 — ✅ PASS（附 1 项如实性注记）

- D01 路径的 commit 真源 = **D-05 exposed 行**（契约 §1 干预生命周期面「intervention 面回执的写真源」），由 gate 直查 DB（同 session select：decision_id + user_id + event_type=exposed + 未软删，occurred_at asc limit 1），行唯一性由 DB 唯一约束保证。**无从队列/缓存取陈旧态的路径**；`experience.event_projected` 发布是 fire-and-forget 下行，commit_state 不回读总线。
- `project_terminal_reason`/`project_error_state` 与源词表 import 期 assert 对齐（源词表漂移在 import 即炸，1:1 映射 5 值 + INVALID_COMMAND 显式排除 + user_cancelled/user_rejected 唯二 skip，均测试钉死），词表复用不复制。
- **如实性注记（非阻塞，C-1）**：`project_terminal_reason`/`project_error_state` 当前**无生产调用方**（grep 证实仅测试触达）——ACTION_INVALID_COMMAND fail-loud 与终态全函数投影是**契约层已落地、测试钉死**的事实，尚无生产路径把 X-03 权威回执喂进投影器（该接线归后续卡/F03，B05 §8/§11 分工明确，不在 D01 卡面「FIX-507 曝光语义」范围内）。服务内 `commit_state` 硬编码 `committed` 之所以成立，恰因 I2 第二门已证明 exposed 行（committed 权威回执）真实存在——投影源即 committed 回执本身，逻辑自洽。**引用本卡证据时不得把「X-03 投影 fail-loud」表述为已上生产路径的运行事实。**

## 5. 独立靶 5：复跑 — ✅ PASS

审查环境：worktree wtD01 @ `8a6a5048`（工作树 clean，仅本 receipt 增量），venv 共享主检出（Python 3.11.15 / pytest 9.0.2）。注：worktree 无 .env，pytest 需环境变量 SECRET_KEY（审查用一次性抛置值；conftest 强制 ENVIRONMENT=test + sqlite，不触 dev DB）——run_manifest 未登记此点，补记于此。

| 命令 | 结果 |
|---|---|
| `pytest tests/core/test_experience_event.py tests/services/test_experience_event_service.py -q` | **44 passed in 5.53s**（31 契约 + 13 集成，独立复现） |
| `pytest tests/services/test_f507_lifecycle_wiring.py -q`（抽样本） | **9 passed in 3.32s**（FIX-507 生产接线不回退） |
| 独立探针 3 条（乱序转场 ×2 + 跨用户回执 ×1） | **3 passed**（临时文件，运行后已删） |

## 6. 独立靶 6：limitations 如实性 — ✅ PASS

逐条核验 `limitations.md`：

- #1「移动端已能收到呈现事件不是本卡可声明的事实」（WS Frame 归 contract-owner）——与实现一致（无 proto/无 WS 下发），如实。
- #4「当前生产路径尚无真实 a11y 上报方」「等价无障碍曝光已被记录不可声明，仅可被如实记录且不与 visual 混写」——grep 证实 3 个生产 mark_seen 调用方均未传面参数、落默认 visual；`accessibility` 位有测试无生产上报方。表述精确、不越声明。
- #2 零订阅方、#3 无事件存储（可重放取舍）、#8 spine 面无 rendered 门——均与代码事实相符。
- 一审 3 条 challenge 独立复核：① `state_confirmed` 词表适配——七元 kind 中唯一 committed+receipt 双要求成员属实，subject.type=intervention 显式锚定不跨域冒充，**判成立**（bump 修正路径已登记归 contract-owner）；② event_bus=None 兜底——**满足**（§3）；③ exposure_basis 仅入 detail JSON——读侧分账以 detail 为据在当前读方形态下成立，列级拆分若需走 Alembic 单 owner，边界声明正确，**判成立**。

## 6.1 一审移交复核项（wtD01R1 review_receipt 提请，独立下判）

- **R1-RULING-1（kind=state_confirmed × receipt_ref=intervention_lifecycle 的 commit_state 真源解释）**：**维持成立**。契约 §1 干预生命周期行明文「intervention 面回执的写真源」= D-05 三写面；该路径的 committed 判定源（exposed 行真实存在）就是本面权威回执本身，非从队列/缓存/accepted 态转写——与「accepted≠committed」反例不冲突（本路径无 accept 中间态，投影条件即权威回执行存在）。七元 kind 中 state_confirmed 为唯一 committed+receipt 双要求成员属实，适配成立；bump 修正路径归 contract-owner 已登记（limitations #6）。
- **G1 边界（D-05 exposed 锚点仍按交付时刻落账）**：**边界声明与实现相符**。`record_delivery_exposure` 既有语义/时刻/幂等（重复 mark_delivered 恰 1 行，测试钉死）原样保留，detail 增 `exposure_basis=delivered`；真实呈现由新事件流承载——双层分账读法成立；漏斗口径切换归独立决策卡（limitations #7 如实）。无静默改写既有读方。

## 7. CHALLENGED（4 项，均非阻塞；不 gating 销账）

1. **C-1 权威面如实性**：`project_terminal_reason`/`project_error_state`（含 ACTION_INVALID_COMMAND fail-loud）当前无生产调用方——契约层事实，非运行事实。后续引用证据时须限定表述（§4 注记）。
2. **C-2 降级可观测强度**：`_refused` 走 `logger.info`，且 `record_rendered_exposure_safe` 的返回结果在 `mark_seen` 挂点被丢弃——生产降级（`no_authoritative_receipt` 等）的可观测面仅剩 info 日志行，无 skip 计数/指标。与 FIX-507 交付面判例同形（该面同样忽略返回值），可接受；建议 F03 接线消费方时把降级 reason 纳入其可观测面。
3. **C-3 文档措辞不一致**：`diff_or_evidence_only.md`「既有**进程内** EventBus」与 `limitations.md`「既有 EventBus（**Redis stream**）」矛盾；`app/core/event_bus.py` 实为 Redis stream 总线（redis.asyncio/xadd + 进程内 consumer）。「无新总线、复用既有实例」的实质成立，仅「进程内」限定词失准。建议顺手更正为「既有 EventBus 实例（Redis stream）」。
4. **C-4 复跑环境注记缺登记**：worktree 无 .env，pytest 需设置 SECRET_KEY 环境变量方可收集（本审查用一次性值）；run_manifest 环境节未登记。不影响结论（sqlite/test 环境），补记于本 receipt §5。

## 8. 红线与边界复核

- 纯 backend：`git diff 1a53b8c3..8a6a5048 -- mobile gateway proto` 为空（实核）。
- 无新表/迁移/proto/同义总线；FIX-507 三写面与既有测试原样保留（抽样复跑 + services 全量证据链一致）。
- E3/I1：`to_dict` 键集冻结测试禁词扫描（permission/role/token_scope/can_write/grants）；事件无权限语义字段。
- 一审/二审独立会话分离：本审查未参与实现与一审；本 commit 为本分支唯一二审产物。

— wtD01R2，2026-09-28，审查基线 `8a6a5048`（branch `agent/v4/d01`）
