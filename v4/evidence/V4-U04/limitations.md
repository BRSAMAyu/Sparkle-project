# V4-U04 · limitations — 已知边界与限制

1. **WS Frame 契约 owner 未定（F03 CH-2 延续）**：本卡全走 REST 读面/轮询（`GET /runs?active=true` + 下拉刷新 + 操作后 invalidate），**未私定任何 WS frame**——工作台不挂事件流；run 状态实时性以手动刷新与操作后重查为界。若后续 contract-owner 落 ExperienceEventFrame，工作台可在 `activeAgentRunsProvider` 处换流，挂点已收敛。
2. **无 taskId 启动的锚点漂移**：workbench「开始一起推进」在无任务上下文时走 `j06:start:auto` 幂等键，后端锚定「最近触碰的在飞任务」。同用户多次点击 → 幂等回放同一段 run（同 run 不重复工件），但若期间用户触碰了别的任务，期望的锚点可能不是当前最近任务。任务面入口（带 taskId）无此问题。裁决归 review_receipt CH-2。一审 F-B 整改后，带 `task_id` 的深链同样无此问题（路由消费 task_id → `j06:start:<taskId>`）；无上下文的 workbench 空态启动仍走 auto 键，边界不变。
3. **generic run 的 agent 步无推进面（设计使然）**：agent-owned 步骤的完成由编排层经 `agent-complete` 端点发生（服务端语义时刻），工作台只呈现「等待中/已完成」，不提供也不该提供客户端触发——即 generic run 在移动端只能「查看/确认 human 步/取消/离开」。
4. **取消幂等键的 'run' 回退段**：无 awaiting step 的运行中取消，客户端键为 `x07:<runId>:run:cancel`；与 awaiting 态卡内推导（`x07:<runId>:<stepId>:cancel`）同形不同源。后端 cancel 的 idempotency_key 为可选参数，键冲突面评估归 review_receipt CH-1。
5. **工作台空态启动入口在深链/通知恢复族之外**：通知点击→工作台的接线（推送 payload 携 run_id）不在本卡（无推送卡在 U 线在飞）；当前恢复入口 = OpenClaw hub / 任务面 / 手动深链 `/journey/workbench?run_id=`（一审 F-B 整改后深链亦可带 `task_id=` 锚定启动）。
6. **语义证据的回退口径**：测试环境 semanticsOwner 根不可用，u04_workbench_semantics.txt 采用「渲染可读面枚举」（全部 Text + 按钮 label），非完整 SemanticsNode 树 dump——覆盖了读屏文本来源与按钮朗读等价面，但非逐节点 flag 证据。真机读屏（VoiceOver/TalkBack）实测不在本卡（无设备授权面）。
7. **UI 证据为测试渲染（U10 同款）**：截图来自 flutter test 真实渲染 + 宿主字体（U02TestFonts），非物理设备截屏；真实操作（恢复/取消拦截）由测试断言背书。物理设备口径与音触面本卡不涉及（工作台零声零触新增）。
8. **五 Tab 合同与 RF-06**：本卡未触碰五 Tab 分支结构（routes.dart 仅尾部 +1 行 routes spread）与 RF-06 冲突面（理解读出/校准族文件零 diff）；工作台为独立新页面文件。`task_execution_screen.dart` 与 `openclaw_hub_screen.dart` 为 V3 既有文件的只增挂载（+4/+9 行），若其他分支并行改同屏需以行级 rebase 解决（登记给集成面）。

## 审查挑战预登记

见 review_receipt.json `challenge_pre_registration`（CH-1 ~ CH-5）：幂等键双轨、'auto' 锚点漂移、任务面回归广度、深链鉴权读面、step_replay 呈现口径。
