# V4-D01 · limitations（如实登记，不作实现事实外推）

## 本卡交付边界内的已知限制

1. **WS 下发面未落 proto**：`experience_event.v1` 的移动端经 WS 消费需要
   `proto/websocket.proto` 增 `ExperienceEventFrame`（oneof 挂
   `WebSocketMessage`）+ `make proto-gen`——B05 §8 指定该入口归
   contract-owner 单独合并（卡边界：禁手改 `*/gen/`；契约/迁移由单一 owner
   单独合并）。本卡交付止于服务面：确定性投影 + 幂等身份 + 既有进程内总线
   发布 + 可重放。**「移动端已能收到呈现事件」不是本卡可声明的事实。**
2. **发布主题的消费方为零**：`experience.event_projected` 走既有
   EventBus（Redis stream），当前无生产订阅者——订阅/去重消费归 V4-F03
   （experience-presenter 锁）。在 F03 接线前，本事件的可观测面 = 测试 +
   `RenderedExposureResult` 返回值 + 重放方法。
3. **无持久化事件存储（有意取舍）**：事件是权威事实
   （InterventionRecord 行 + D-05 exposed 行）的确定性投影，可任意重放；
   历史查询依赖权威行重放而非事件表。若 F03 需要事件留存/对账，须由其
   contract-owner 走 Alembic 单头迁移，本卡不夹带。
4. **`rendered_surface` 默认 "visual" 是对现有调用方的保守假设**：现有
   `mark_seen` 调用方（notification center / profile transparency / feedback
   binding）未传面信息，均落默认 `visual`。等价无障碍曝光
   （`accessibility`→`["audio"]` 模态）的词表位已冻结并有测试，但**当前
   生产路径尚无真实 a11y 上报方**——「等价无障碍曝光已被记录」不是本卡可
   声明的事实，仅「可被如实记录且不与 visual 混写」成立。
5. **copy_key 键位内容未定义**：`intervention.rendered` 只落了键纪律
   （两段式、非空）；键→文案冻结表 owner = V4-F03（B05 §3 R1-C5），
   本卡不定义文案。
6. **kind=state_confirmed 的词表适配**：B05 七元 kind 中无字面 "rendered"
   成员；`state_confirmed` 是唯一 committed+receipt 双要求成员，被选作真实
   呈现回执的 kind，subject.type=intervention 明示不跨域冒充任务/记忆
   committed。该适配是本卡的语义判定，已在 review_receipt.json
   suggested_challenge_points 首条列为独立审查必点挑战；若两审判不成立，
   修正路径 = kind 词表 v1.x bump（contract-owner），不在本卡内私扩。
7. **交付面 lifecycle 行语义仍含下发时刻**：FIX-507 写面 1a（mark_delivered
   → record_exposure）按卡面「保留」原样保留，因此 D-05 `exposed` 行的既有
   读方（摘要/漏斗）仍以交付时刻为锚。本卡增量为（a）detail 显式
   `exposure_basis=delivered` 供读侧分账、（b）真实呈现由 experience_event
   承载；**未**改写 D-05 既有读方口径——若需漏斗口径切换（以 rendered 为
   唯一锚），属独立决策卡。
8. **spine 面未加 rendered 门**：spine directive 下发（写面 2）无客户端
   确认回路，其 directive_id→WS 呈现确认的接线不在本卡（无既有确认事实可
   依）；该面维持 FIX-507 现状。

## 环境性限制（非代码事实）

- tests/core `test_bert_intent_classifier.py` 36 个 fixture error 为既有环境
  噪声（transformers 权重/依赖缺失），`git stash -u` 后基线复跑同败，与本次
  变更无关。
- `backend/app/gen` 由主检出复制以运行 2 个依赖生成物的消费方测试模块
  （.gitignore 已忽略）；该目录缺失时这两模块本就无法收集（基线同状）。
- mypy 复核排除 8 条 `app.gen ... has no attribute` 环境噪声（生成 stub 不
  全，主检出同源存在）；排除后与基线 diff 为空。
- 本机为 macOS（AGENTS.md 硬规则 4 的 Windows 表述为旧阶段事实）；纯
  Python 变更无 cgo/平台面。
