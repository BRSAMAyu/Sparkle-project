# MIDSTREAM-HEARTBEAT — 建模访谈长静默窗的引擎侧心跳帧（B-02 引擎半场）

- **执行人**：C 纵队修复 Worker（北极星主链线）
- **Worktree**：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt218`（基线 `a51b01e6`）
- **缺陷依据**：主仓 `v3-output/V13-MAJORS/REPORT.md` §四-2 移交注记（B-02 引擎中段心跳未实施）
- **交付物**：本报告 + 同目录 `changes.patch`（未 commit / 未 push，零凭据）

---

## ① 静默段定位与帧型选型裁决

**静默段定位（实证，非猜测）**：建模访谈一轮 run 的帧路径是
`stream_callback`（orchestrator.py:2779，设置帧身份后经 `_enqueue_stream_response` 入队）→ **`_execute_graph` 消费循环**（execution_engine.py，orchestrator.py:3730 调用）→ gRPC 产出。`_execute_graph` 以 `task_manager.spawn(self.graph.invoke(...))` 后台跑建模 StateGraph（`app/agents/graph/workflow.py`：router → agent 节点 → tools → router），自身每 100ms 轮询队列出帧。

**根因窗**：图内 agent 节点的长 LLM 思考段 / 长工具调用段（B-02 实测 50s+）期间**队列无帧可出**，消费循环在 `TimeoutError` 分支空转、什么都不 yield——客户端只剩「思考中」胶囊、无任何服务端真实信号。此窗口即 wt207 mobile 75s 中段看门狗所覆盖的静默窗。多消息回合中段（Aurora 发出消息 1 后继续思考生成消息 2）全部发生在图执行期内，故 `_execute_graph` 消费循环就是唯一且完备的补帧点。

**帧型选型裁决**：
- **复用 `ChatResponse.status_update`（`AgentStatus.THINKING`）既有帧型，协议零扩展**。
- **网关透传现状已查证**：`backend/gateway/internal/handler/chat_orchestrator_protocol.go:133-142` 已将 `ChatResponse_StatusUpdate` 转成 WS `type:"status_update"`（status + `ux_progress`，引擎自带 `ux_progress` metadata 优先于网关派生）——**零网关改动达成**。
- **mobile 消费面已查证**：`websocket_chat_service_v2.dart:597` 解析为 `StatusUpdateEvent`；`modeling_chat_screen.dart` 的 `_handleStreamEvent` 对任意事件（含 status）重置 75s 看门狗、`chat_provider` 用 `ux_progress.headline/detail` 做状态文案。心跳帧天然兼容，mobile 侧零改动。
- 备选「在图各节点插桩发进度帧」被否：触达 `app/agents/` 全部节点、面大且只能覆盖已插桩段；消费循环补帧天然覆盖**一切**静默段（LLM/工具/checkpointer 等待均无法逃逸）。

## ② 实现（3 文件 + 1 新测试，315 行增量）

- **`backend/app/orchestration/execution_engine.py`**：
  - `_execute_graph` 增加 `frame_identity` 关键字参数与静默心跳逻辑：出队任意真实帧即重置静默计时；`TimeoutError`（队列空转）分支检测静默 ≥ `STREAM_HEARTBEAT_INTERVAL_SECONDS`（默认 10s，≤0 视为关闭，总开关 `STREAM_HEARTBEAT_ENABLED`）即**直出**心跳帧（不入队、不占背压配额、不计 usage）。
  - 新增 `_build_stream_heartbeat_response`：内容诚实——`AgentStatus.THINKING` + `"Still working on your request... (Ns elapsed)"`，metadata 带 `stream_heartbeat:"true"` 与 `ux_progress` JSON（`stage:"processing"`、`heartbeat:true`、`is_blocked:false`、detail=已耗时秒数）。**只声明「仍在处理 + 已耗时」，绝不伪造阶段进度**；帧身份（response/request/session/workflow/prompt/trace）与回合同源。
- **`backend/app/orchestration/orchestrator.py`**：唯一调用点（Step 13 `_execute_graph`）传入 `frame_identity`（变量均已在 process_stream 作用域内，与 `stream_callback` 同源同值）。
- **`backend/app/config/settings.py`**：`STREAM_HEARTBEAT_ENABLED: bool = True`、`STREAM_HEARTBEAT_INTERVAL_SECONDS: float = 10.0`（紧邻既有 `EARLY_ACK_PROGRESS_ENABLED`，同风格注释）。
- **`backend/tests/test_stream_heartbeat.py`**（新）：7 用例——帧形诚实性（THINKING+耗时+身份+metadata 可解析）；长静默（mock 0.6s 长任务、0.15s 周期）心跳 ≥2 且全为心跳帧；正常流（帧间隔 0.08s < 周期 0.3s）**零**新增心跳且 6 个 chunk 原序透传；usage 帧计账与心跳正交；缺 `frame_identity` / 总开关关 / 间隔≤0 三种回退基线情形均零心跳。

**与 wt207 75s 看门狗的协同声明**（契约级，两侧代码均已在基线核验）：
- **正常任务**：心跳每 10s 一帧 → 看门狗（任意帧重置，75s 阈值 ≫ 心跳周期）**永不触发**——正常长任务不再被误杀，中段窗口从「哑等」变为「胶囊 + 已耗时」的诚实可见。
- **真死流**：心跳由 `_execute_graph` 消费循环直出，图任务死/循环退出 → 心跳与流同停 → 75s 后看门狗照常触发，**兜底语义不变**。心跳不产生任何「僵死流永活」的新风险面。
- 取值依据：默认 10s ≪ 75s 看门狗阈值（留 7.5 倍余量防网络抖动误判），且 ≥ B-02 实测无帧窗起点，覆盖 50s+ 实测窗（5 帧）。

## ③ 冲突面声明

- **本卡触达**：`execution_engine.py::_execute_graph`（+新私有方法）、`orchestrator.py` 单调用点、`settings.py` 两行、新测试文件。**未动** `app/agents/` 任何文件、未动网关、未动 mobile。
- **wt216（只读）**：零交集。
- **wt217（llm_router/agent_profiles）**：无文件交集；`execution_engine.py` 仅动 `_execute_graph` 函数体，该函数不在 llm_router/agent_profiles 面。
- **wt206/207 已合入面（基线 `a51b01e6` 已含）**：wt207 = `galaxy_bootstrap_service.py` + mobile 4 屏件；wt206 = chat session 建链。本卡引擎侧改动与其无重叠行域；与 wt207 的关系是**协同**而非依赖：mobile 看门狗已在基线，心跳帧到达即被其重置逻辑消费，无需 mobile 再改。
- **early-ack（既有机制）**：`_emit_early_ack_progress` 未动；心跳与其互补（回执在图启动前，心跳在图执行中段）。

## ④ 诚实申报

1. **补帧点只覆盖图执行期（Step 13 `_execute_graph`）**：Step 10-12 的路由/双核/规划 LLM 调用若整体 >10s 静默，客户端仍只有 early-ack 胶囊——这些阶段帧本就积压在队列（消费循环未启动，发心跳也会迟到），且 V13 实测停摆窗在图内中段。`_continue_after_tool_result` 与 `_handle_multi_agent_mode`（unified routing 默认开，仅关闭时兜底）路径未加心跳，如需另卡。
2. **未做真 LLM 长任务活栈冒烟**（见下§主会话验收步骤）：单测以 mock 图验证机制与时序，真 LLM 50s+ 静默窗的心跳实测需活栈。
3. **心跳帧「非终局」语义**：mobile 侧若未来把 `status_update.details` 直接展示给用户，会看到英文 "Still working on your request... (Ns elapsed)"（与 `_emit_early_ack_progress` 同为引擎侧英文 details 先例；当前 modeling 屏消费 `ux_progress` headline/detail，不直接裸显 details）。
4. **elapsed 口径**：心跳 detail 的已耗时=**图执行起点至今**（本轮总耗时），非「距上一帧」——总耗时对用户更有信息量且单调，测试已钉。
5. **timing 依赖的单测**：两个用例依赖真实 sleep 时序（0.6s/0.55s 级），已在阈值上留 ≥2 倍余量；CI 慢机极端情况下可能少 1 帧心跳，断言用 `>=2` 容忍。

## 验证（定向 + 对比法零新增）

- 新测试：`SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" python3.11 -m pytest tests/test_stream_heartbeat.py --timeout=60` → **7 passed**。
- 邻域回归（worktree）：`test_execution_engine_mixin.py`（10）+ `test_done_tail_latency.py`（2，process_stream 面）+ `test_c03_multi_agent_spine_context.py`(2) + `test_event_ack2_reliability.py`（12，流队列面）+ `test_phase5_orchestrator_north_star_acceptance.py`（1p1s）→ **27 passed 1 skipped**。
- **对比法**：`git clone` 基线 `a51b01e6` 至 /tmp，proto-gen 后同命令同测试集 → **27 passed 1 skipped，失败集逐字一致，零新增失败**。
- lint：改动行 black(120) 干净（文件内仅存基线已有 3 处 black 偏差与 1 处 ruff UP041，`git show a51b01e6` 同位可证）；测试文件 black/ruff 全绿。

## 主会话验收步骤（真 LLM 长任务冒烟看心跳帧）

1. 合入本 patch（apply --3way）→ 引擎重启后建探针账号，`cd mobile && flutter run` 进建模访谈（或直接用现栈）。
2. 触发长静默：发一条迫使建模图多步思考/多工具的消息（如让 Aurora「先把我的薄弱点全部整理出来，再逐个给复习建议」——B-02 原始复现话术）。
3. **观察 mobile**：消息 1 发出后的静默段，胶囊应每 ~10s 刷新「仍在处理」状态与已耗时（`ux_progress.headline · detail`），**不再纯哑等**；75s 看门狗不触发。
4. **抓帧取证（可选，最硬）**：`backend/gateway` WS 侧或 Charles/mitmproxy 抓 ` modelling` 会话 WS 帧——静默窗内应见周期性 `{"type":"status_update","status":{"state":"THINKING",...},"metadata":{"stream_heartbeat":"true",...}}`，正常 delta 流期间无该帧。
5. **回归对照**：关掉 `STREAM_HEARTBEAT_ENABLED`（或引擎 env 置 0）重启复测同话术——回到基线行为（哑等到 75s 看门狗或回复到达），证明确系本卡生效。
6. **真死流兜底**：kill 引擎进程模拟死流 → 心跳停 → 75s 后 mobile 看门狗触发可见错误 + 重试（wt207 语义），确认兜底未失效。

## ⑤ 收工核查

- [x] 无 git commit / push（`git add -N` 仅意图登记）；交付物=本报告 + `changes.patch`
- [x] 零凭据（未起服务、未连活栈、未读 .env；测试全离线 mock）
- [x] `/tmp` 清理：`/tmp/wt218-baseline`（基线克隆）、`/tmp/wt218_changes_body.patch` 已删
- [x] worktree 构建产物：`backend/app/gen` 为 proto 生成产物（不入库，跑测必需，随 worktree 生命周期回收）；无 build/.dart_tool
- [x] 无独立端口进程残留（未起任何服务/模拟器/浏览器）；HEAVY=0（全程 pytest 单并发 + git clone）
