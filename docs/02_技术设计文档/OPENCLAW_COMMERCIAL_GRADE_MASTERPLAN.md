# OpenClaw 商业级深度融合方案 — 完整设计文档

**版本**: v1.0
**日期**: 2026-04-02
**作者**: Claude (总设计师)
**状态**: 设计完成，待实施

---

## 文档概述

你说得对：**问题不是"链路跑不跑得通"，而是"它是否真的给用户带来了价值"。**

当前状态：技术链路已通（Phase 0-4 完成，37 tests passing），但用户体验停留在"开发者验证可行性"的阶段。接下来要做的，是把它从**"一个能用的功能"**变成**"一个用户离不开的能力"**。

### 核心设计哲学

1. **无感融合** — OpenClaw 不是 Sparkle 的"附加功能"，而是双核执行系统的延伸肢体。用户不应该意识到自己在"使用 OpenClaw"，他应该只觉得"Sparkle 帮我做了"
2. **信任渐进** — 不同用户对自动化的接受度不同。提供从"每步确认"到"全权委托"的连续信任谱系
3. **闭环价值** — 每一次执行都必须回流到 Sparkle 的认知核心：更新用户画像、优化未来建议、强化成长反馈
4. **故障透明** — 出问题时用户不是看到一个红色错误卡片，而是 Sparkle 像一个聪明的伙伴告诉他"发生了什么、我建议怎么办"

---

# Phase 5: 实时感知层 — "执行不再是黑箱"

**目标**：用户从点击执行到看到结果的全程，都有实时、渐进、有意义的反馈。

## 5.1 流式执行输出

**现状问题**：当前 OpenClaw 执行是"黑箱等待"模式 — dispatch 之后，用户只能等到全部完成才能看到结果。对于 30 秒以上的任务，这种体验是不可接受的。

**方案**：
- **后端**：在 `gateway_ws_client.py` 的 event callback 中，将 `agent` 类型事件（即 OpenClaw 的中间输出）实时转发到 Sparkle 的 WebSocket 通道
- **网关**：`chat_orchestrator_protocol.go` 新增 `execution_progress` 消息类型，携带增量输出、当前步骤描述、预估进度
- **前端**：聊天流中渲染一个"活的"执行卡片 — 不是静态等待条，而是实时展示 Agent 正在做什么（"正在打开浏览器…""正在读取页面内容…""正在整理结果…"）
- **设计要点**：用户应该能看到执行的"思维过程"，就像看一个聪明的助手在屏幕共享一样

### 详细技术方案

**现状锚点**：

当前 `gateway_ws_client.py:249-297` 的 `execute()` 循环已经通过 `event_callback(frame)` 将每一帧实时传递给 `execution_service.py:792` 的 `_handle_gateway_stream_event()`。但这个 callback 目前只做了一件事：调用 `_publish_monitor_progress()` 更新后台任务进度（给 task_monitor_service），**没有推送到前端**。

同时，`execution_engine.py:331-450` 的 `_maybe_short_circuit_openclaw_chat_control()` 是**同步阻塞**的 — 它 `await service.handoff_chat_control()` 后，整个方法返回一组完整的 `ChatResponse`。前端要么收到最终结果，要么什么都没有。

**改造方案**：

**第一步：在 Python 后端增加中间输出流**

在 `execution_service.py` 中，`_handle_gateway_stream_event()` 的改造思路：

- 当前该方法的签名是 `async def _handle_gateway_stream_event(self, intent, frame) -> None`，没有返回值也没有推送通道
- 需要新增一个参数 `stream_sink`：一个 callable，用于将中间输出推送到聊天流
- `stream_sink` 的签名：`Callable[[str, dict], Awaitable[None]]` — 接收 `(event_type, payload)`
- 对 `agent` 事件的 `stream="assistant"` 类型帧：提取 `payload.content` 中的文本片段，通过 `stream_sink("execution_delta", {"intent_id": str(intent.id), "text": text_chunk, "tool_calls_count": capture.tool_calls_count})` 推送
- 对 `stream="tool"` 类型帧：提取工具名（如果 payload 里有），推送 `stream_sink("execution_tool_call", {"intent_id": str(intent.id), "tool_name": tool_name, "step_index": capture.tool_calls_count})`
- 对 `stream="lifecycle"` 的 `phase="start"` 和 `phase="end"`：已有逻辑不变，但额外推送 `stream_sink("execution_lifecycle", {...})`

**第二步：在 Orchestrator 层面把 stream_sink 接入 gRPC 流**

当前 `_maybe_short_circuit_openclaw_chat_control()` 返回 `list[ChatResponse]` — 这是一次性的。需要改造成**异步生成器模式**：

- 新增方法 `_stream_openclaw_chat_control()` 返回 `AsyncGenerator[ChatResponse, None]`
- 这个方法先 yield 一个 `status_update`（"正在连接你的 OpenClaw..."）
- 然后传入 `stream_sink`，sink 的实现是：每收到一个中间事件，yield 一个 `status_update` 类型的 `ChatResponse`，其中 `details` 字段携带阶段描述
- 最后 yield 最终的 `tool_result`（沿用现有的 `_build_openclaw_chat_control_payload()`）
- 在 `orchestrator.py:904` 的调用点，从一次性调用改为 `async for resp in self._stream_openclaw_chat_control(...)` 逐个 yield

**第三步：Go Gateway 协议层**

`chat_orchestrator_protocol.go` 不需要新增消息类型。当前的 `status_update` 消息已经能承载中间状态：

```go
// 已有结构：
type statusUpdate struct {
    state   string  // "GENERATING"
    details string  // 这里放阶段描述
}
```

需要确保 Python 侧的中间 `status_update` 消息被正确转换为 JSON 发到前端。

**第四步：Flutter 前端接收**

`websocket_chat_service_v2.dart` 已经能处理 `status_update` 类型的消息。需要做的：

- 在 `chat_provider.dart` 中监听 `status_update`，如果 `details` 以 `execution_delta` 或 `execution_tool_call` 前缀开头，更新当前执行卡片的状态文本
- `action_card.dart` 新增一个"执行中"状态：不是静态卡片，而是带有实时滚动文本区域的动态卡片。显示 Agent 的中间输出（类似于终端输出效果），以及当前正在调用的工具
- 新增 `_ExecutionLiveOutputWidget`：一个 `AnimatedList` 或 `ListView`，接收流式追加的文本行

**边界条件**：

- 如果用户中途离开聊天页面再回来，中间输出已丢失 — 这是可接受的。回来后只显示最终结果卡片
- 如果 OpenClaw 执行超时，流式输出停在最后一个已推送的 delta 处，超时错误通过最终的 `tool_result` 返回
- 如果 transport 是 `responses_http` 而不是 `gateway_ws`，没有流式事件 — 直接走现有逻辑，一次返回最终结果

## 5.2 执行心跳与超时恢复

**现状问题**：硬超时 300s，无心跳，无重试。长任务可能假死但用户不知道。

**方案**：
- 后端每 5s 向 OpenClaw 发送 heartbeat，若连续 3 次无响应则判定连接丢失
- 连接丢失后：不是直接标记失败，而是进入"恢复模式" — 尝试通过 `external_run_id` 重新 attach 到运行中的任务
- 超时前 30s 给用户推送提醒："这个任务比预期久，要继续等待还是取消？"
- 支持用户主动"延长时限"而不是只能等它超时

### 详细技术方案

**现状锚点**：

`gateway_ws_client.py:247` 设置 `deadline = monotonic() + timeout_seconds`，`252` 行用 `_recv_json(timeout_seconds=min(1.0, remaining))` 做短间隔轮询。超时后 `299` 行抛 `OpenClawTimeout`。没有心跳，没有恢复。

**改造方案**：

**心跳**：

- 在 `gateway_ws_client.py` 的 `execute()` 循环中，每收到一帧就更新 `last_activity = monotonic()`
- 如果连续 5 个 `_recv_json` 超时（即 5 秒无新帧），向 OpenClaw 发送一个 ping 帧（或 `_rpc(method="ping")` 如果 OpenClaw 支持）
- 如果 ping 也没有响应，标记连接为 `degraded`，通过 `event_callback` 推送一个 `("execution_degraded", {"reason": "no_activity", "last_event_age_seconds": X})` 事件
- 不主动断开 — 让 deadline 到期后自然超时，但提前通知前端

**超时前预警**：

- 在 `execution_service.py` 的 `dispatch()` 中，当 timeout 达到 80% 时（`elapsed > timeout_seconds * 0.8`），通过 stream_sink 推送一个 `execution_timeout_warning` 事件
- 前端收到后显示一个 toast："任务执行时间比预期久，是否继续等待？" — 用户可以选择"延长 60 秒"或"取消"
- "延长"按钮通过 WebSocket 发送一条 `action_feedback` 消息（复用现有的 `chat_orchestrator_feedback.go` 通道），后端收到后更新 deadline
- 这需要在 `dispatch()` 中把 deadline 改为可变的（存在某个可变状态中，比如一个 dict 或简单类）

**恢复模式**：

- `gateway_ws_client.py` 新增方法 `attach_run(run_id: str, *, timeout_seconds: int) -> dict`
- 该方法连接 WebSocket 后，发送 `_rpc(method="run.status", params={"runId": run_id})` 查询运行状态
- 如果 run 仍在运行，重新注册 event listener，继续接收后续事件
- 在 `execution_service.py` 中，当收到 `OpenClawTimeout` 异常时，不要立即标记失败，而是检查 `intent.external_run_id` — 如果有值，进入 `attach_run` 尝试恢复
- 恢复成功后继续正常流程；恢复失败（run 已结束、run 不存在）才真正标记超时

## 5.3 执行阶段语义化

**方案**：
- 将 OpenClaw 的原始事件流翻译为用户可理解的阶段描述：
  - `tool_call(browser_navigate)` → "正在访问目标网页"
  - `tool_call(file_write)` → "正在保存文件到你的电脑"
  - `tool_call(shell_exec)` → "正在执行终端命令"
- 这些翻译规则维护在 `intent_translator.py` 的语义映射表中
- 前端用动画过渡展示阶段切换，让用户感受到"进展"

### 详细技术方案

**现状锚点**：

`_handle_gateway_stream_event()` 中对 `stream="tool"` 事件只更新了 `progress_message="OpenClaw is using tools"`。没有提取工具名或参数。

**改造方案**：

在 `gateway_ws_client.py` 的 `_GatewayRunCapture.observe()` 中，`stream=="tool"` 分支已有 `tool_calls_count` 计数。扩展它：

- 提取 `payload` 中的工具调用信息：OpenClaw 的 tool 事件通常包含 `payload.name`（工具名）和 `payload.input`（参数摘要）
- 存入一个新的列表 `tool_trace: list[dict]`，每条记录 `{"name": "browser_navigate", "input_summary": "https://example.com", "timestamp": ...}`

在 `intent_translator.py` 新增一个语义映射表：

```python
_TOOL_STAGE_DESCRIPTIONS = {
    "browser_navigate": "正在访问目标网页",
    "browser_click": "正在点击页面元素",
    "browser_screenshot": "正在截取页面截图",
    "browser_extract": "正在提取页面内容",
    "shell_exec": "正在执行终端命令",
    "file_read": "正在读取文件",
    "file_write": "正在保存文件",
    "file_delete": "正在删除文件",
    "web_search": "正在搜索信息",
    "web_fetch": "正在获取网页内容",
    "code_execute": "正在运行代码",
}

def describe_tool_call(tool_name: str, input_summary: str | None = None) -> str:
    base = _TOOL_STAGE_DESCRIPTIONS.get(tool_name, f"正在执行操作：{tool_name}")
    if input_summary:
        return f"{base}（{input_summary[:50]}）"
    return base
```

这个描述通过 stream_sink 推送到前端，显示在执行卡片的"当前步骤"区域。

---

# Phase 6: 信任谱系 — "让用户选择自己的舒适区"

**目标**：不同用户对自动化有截然不同的偏好。构建从"全手动审批"到"全权委托"的连续信任模型。

## 6.1 用户执行偏好系统

**现状问题**：当前审批策略由 OpenClaw 节点决定，Sparkle 侧没有用户级偏好。有的用户想全部自动执行，有的用户想每步都看一眼。

**方案**：
- 在用户设置中新增"执行偏好"模块，提供三种预设 + 自定义：
  - **谨慎模式**（Cautious）：所有执行前确认，执行后审阅，结果手动确认才写入
  - **平衡模式**（Balanced）：低风险动作自动执行（读取、查询），高风险动作需确认（写入、删除、发送），默认模式
  - **信任模式**（Autonomous）：除"不可逆高危动作"外全部自动执行，用户只在最后看结果
  - **自定义**：按动作类型（read/write/delete/send/install）逐项设置是否需要确认
- 这个偏好存入用户 preference，`execution_service.py` 的 `create_intent()` 在构建 policy 时合并用户偏好
- 偏好可随时调整，且 Sparkle 会基于用户历史自动建议调整（"你已经连续 20 次确认了浏览器操作，要不要把它设为自动？"）

### 详细技术方案

**现状锚点**：

当前没有任何"用户执行偏好"的存储或读取。用户偏好存放在 `user_preferences` 表（通过 `openclaw_connection_profile_service.py` 管理 OpenClaw 连接配置）。执行策略完全由代码常量和 intent 的 `policy` dict 决定。

**数据模型设计**：

在 `user_preferences` 的 JSONB 字段中新增一个 key `execution_preferences`，结构：

```python
{
    "execution_preferences": {
        "mode": "balanced",  # "cautious" | "balanced" | "autonomous" | "custom"
        "custom_rules": {    # 仅 mode="custom" 时使用
            "browser_read": "auto",      # "auto" | "confirm" | "skip"
            "browser_write": "confirm",
            "file_read": "auto",
            "file_write": "confirm",
            "file_delete": "confirm",
            "shell_exec": "confirm",
            "shell_read": "auto",
            "install": "reject",         # "reject" = 不允许执行
            "send": "confirm",
        },
        "notification_level": "essential",  # "all" | "essential" | "silent"
        "auto_extend_timeout": True,
        "trust_auto_upgrade": True,
    }
}
```

**后端改造点**：

1. `execution_service.py` 的 `create_intent()` 方法（当前在构建 `policy` dict 时使用硬编码默认值）：
   - 新增一步：读取 `user.execution_preferences`
   - 根据 `mode` 合并 policy：
     - `cautious`：所有 `approval_policy` 设为 `"always"`
     - `balanced`：读取类设为 `"never"`，写入/删除类设为 `"on_risky"`
     - `autonomous`：所有设为 `"never"`，但不可逆操作仍设为 `"always"`
     - `custom`：按 `custom_rules` 逐项映射
   - 合并后的 policy 写入 `intent.policy`

2. `execution_service.py` 的 `handoff_chat_control()` 方法（聊天远控入口）：
   - 同样读取偏好，但逻辑更轻量：只在 `mode="cautious"` 时，dispatch 前先通过 stream_sink 发一个"确认"请求给前端，用户确认后才真正 dispatch
   - 其他模式直接 dispatch

3. 新增 API 端点 `PUT /api/v1/executions/preferences` 和 `GET /api/v1/executions/preferences`
   - 写入 `user_preferences` 表
   - `GET` 返回当前偏好 + 推荐调整建议（基于 `execution_learning_service` 的统计数据）

**Flutter 前端改造点**：

1. 在 OpenClaw 设置页（`openclaw_settings_screen.dart`）新增"执行偏好"区块
   - 三种预设卡片的 radio 选择
   - 选择 `custom` 时展开逐项配置
   - 通知级别选择
   - 每个选项都有中文解释

2. 在 `openclaw_hub_screen.dart` 的仪表盘中新增偏好摘要卡片："当前模式：平衡 — 读取操作自动执行，写入操作需确认"

## 6.2 动态信任升级

**现状问题**：当前 TrustEngine 的 auto-promote 逻辑（5 次成功 + 85% 成功率）是全局的，不区分动作类型。

**方案**：
- 信任升级按**动作类别**独立计算：浏览器操作的信任、文件操作的信任、终端命令的信任各自独立
- 用户可以在某个类别上快速建立信任（"浏览器查资料已经做了 10 次都没问题"），但另一个类别保持谨慎（"终端命令还是让我确认"）
- 引入"信任回退"机制：一次失败执行会让该类别的信任降一级，而不是全部归零
- 数据存入 `execution_learning_service.py`，按 `(user_id, target_env, action_category)` 维度追踪

### 详细技术方案

**现状锚点**：

`execution_learning_service.py:33-37` 定义了常量 `TRUST_BUILDING_STREAK = 5`，`68-80` 行在连续 5 次 `TRUSTED` 成功后创建 `Delegation Trust Building` 行为模式。但这是全局的，不区分动作类别。

`execution_service.py` 中的 `ExecutionTrustEngine`（在 `execution_trust.py`）用 `OPENCLAW_TRUST_AUTO_PROMOTE_MIN_HISTORY=5` 和 `OPENCLAW_TRUST_AUTO_PROMOTE_SUCCESS_RATE=0.85` 做全局 auto-promote。

**改造方案**：

1. 在 `execution_learning_service.py` 新增维度化信任追踪：

```python
async def get_category_trust_stats(
    self, *, user_id: UUID, target_env: str
) -> dict[str, dict]:
    """返回按 target_env 分类的信任统计。

    返回结构：
    {
        "browser": {"total": 15, "succeeded": 13, "success_rate": 0.87, "current_trust": "validated"},
        "shell": {"total": 3, "succeeded": 2, "success_rate": 0.67, "current_trust": "raw"},
        ...
    }
    """
```

- 查询 `execution_intents` 表，按 `user_id` + `target_env` 聚合 `status` 统计
- 与 `execution_records` 的 `trust_level` 关联

2. 在 `execution_service.py` 的 `create_intent()` 中，构建 policy 时查询该用户的 `target_env` 维度信任：
   - 如果该类别已经是 `trusted` 且成功率 > 0.85，降低审批要求
   - 如果该类别成功率 < 0.6，即使模式是 `autonomous`，也强制 `confirm`

3. 信任回退机制：
   - 在 `execution_ingestor.py` 的 `ingest()` 中，如果执行失败（`status=FAILED`），调用 `execution_learning_service.record_category_failure(user_id, target_env)`
   - 该方法将该类别的连续成功计数归零，`current_trust` 降一级（`trusted` → `validated`，`validated` → `raw`）
   - 不跨类别影响

## 6.3 风险预评估与智能审批

**方案**：
- 在 dispatch 之前，对 intent 进行风险评估（不只是分类路由）：
  - **影响范围**：这个操作影响一个文件还是整个目录？一个网页还是会触发购买？
  - **可逆性**：这个操作能 undo 吗？（读取 = 完全可逆，删除 = 不可逆）
  - **敏感度**：涉及密码、支付、个人数据吗？
- 风险评估结果决定是否需要用户确认，而不是一刀切
- 高风险操作即使在"信任模式"下也强制确认，并向用户解释为什么："这个操作会删除文件，即使在自动模式下我也需要你确认一下"

### 详细技术方案

新增 `execution_risk_assessor.py`，核心逻辑：

```python
class ExecutionRiskAssessor:
    """在 dispatch 前评估 intent 的风险等级。"""

    IRREVERSIBLE_PATTERNS = [
        r"\brm\s+-rf\b", r"\bdrop\s+table\b", r"\bgit\s+push\s+--force\b",
        r"\bDELETE\s+FROM\b", r"\bformat\b", r"\bshutdown\b",
    ]

    SENSITIVE_PATTERNS = [
        r"\bpassword\b", r"\bapi[_-]?key\b", r"\bsecret\b",
        r"\btoken\b", r"\bcredential\b",
    ]

    def assess(self, *, intent_goal: str, policy: dict) -> RiskAssessment:
        """返回 RiskAssessment(level="low"|"medium"|"high"|"critical",
           reasons=[...], forced_confirm=bool)"""
```

- 在 `execution_service.py` 的 `dispatch()` 中，dispatch 前调用 `assessor.assess()`
- 如果 `forced_confirm=True`（高风险），即使用户偏好是 `autonomous`，也通过 stream_sink 推送确认请求
- 风险评估结果存入 `intent.policy["_risk_assessment"]`，用于审计

---

# Phase 7: 深度系统融合 — "OpenClaw 不是功能，是能力"

**目标**：让 OpenClaw 的执行能力渗透到 Sparkle 的每一个子系统，而不是只在"执行页"或"聊天远控"两个入口存在。

## 7.1 计划系统融合

**现状**：计划系统（ExecutablePlan v5.0）生成的任务，用户需要手动进入执行入口委派。

**方案**：
- 计划生成时，Orchestrator 自动评估每个子任务的"可委派性"（delegability score）
- 可委派的任务在计划卡片上直接标记"可自动执行"图标
- 用户在审阅计划时可以一键勾选"哪些交给 Agent 做"
- 计划批准后，被勾选的任务自动进入执行队列，按依赖顺序串行/并行调度
- **关键设计**：这不是"帮用户按按钮"，而是把执行能力嵌入到计划层。用户看到的不是"手动任务列表"，而是"一部分我做、一部分 Agent 做"的协作计划

### 详细技术方案

**现状锚点**：

计划系统生成子任务后，用户需要手动到 `task_execution_screen.dart` 点 handoff。没有"可委派性评估"的概念。

**改造方案**：

1. 在 `execution_template_service.py` 新增方法 `assess_delegability(task: Task) -> DelegabilityScore`：

```python
@dataclass
class DelegabilityScore:
    score: float  # 0.0 - 1.0
    reasons: list[str]  # ["包含浏览器操作", "可通过模板匹配"]
    suggested_template: str | None
    estimated_duration_seconds: int | None
```

- 评分逻辑：匹配到模板的加分，`target_env=browser` 加分，纯文本任务减分
- 返回的 score 存在内存中（不在 DB），只在计划审阅时计算

2. 在 `orchestrator.py` 生成计划后（`ExecutablePlan` 返回时），对每个子任务调用 `assess_delegability()`
- 结果附加在 `ExecutablePlan.steps[i].metadata` 中：`{"delegability_score": 0.85, "delegable": True}`

3. 前端在 `plan_review_card.dart` 的计划审阅卡片中：
- 可委派的任务旁显示一个 toggle："交给 Agent 执行"
- 默认根据 score 自动勾选（score > 0.7 的默认勾选）
- 用户审阅确认时，勾选的任务带上 `execution_mode: "agent"` 标记

4. 计划批准后的自动调度：
- 在 `orchestrator.py` 处理 `SubmitPlanReview` 时，检查每个子任务的 `execution_mode`
- 如果是 `agent`，在创建 Task 后立即调用 `execution_service.handoff_to_openclaw()`
- 如果多个任务可委派且无依赖关系，可以并行 dispatch（受并发限额控制）
- 如果有依赖关系（任务 B 依赖任务 A 的输出），串行执行，A 完成后自动触发 B

5. 新增事件类型 `EXECUTION_BATCH_STARTED` 和 `EXECUTION_BATCH_COMPLETED`
- 批量执行开始时发布 `EXECUTION_BATCH_STARTED`，携带 `task_ids` 列表
- 每个子任务完成时发布 `EXECUTION_RESULT_INGESTED`（已有）
- 全部完成时发布 `EXECUTION_BATCH_COMPLETED`，携带汇总统计

## 7.2 知识星图融合

**方案**：
- OpenClaw 执行的结果（查到的资料、爬到的数据、整理的笔记）自动进入知识星图
- 不是简单地"把原始输出丢进去"，而是通过认知核心提取关键知识点，创建 GalaxyNode
- 执行产生的知识节点与用户已有的知识图谱建立关联
- 例如：用户说"帮我查一下 React Server Components 的最新进展"，OpenClaw 查到的内容被结构化后进入星图，与用户已有的"React"、"前端框架"节点产生连线

### 详细技术方案

**现状锚点**：

`execution_ingestor.py` 的 `_apply_execution_result()` 完成任务状态更新后发布 `EXECUTION_RESULT_INGESTED` 事件。目前没有 consumer 将执行结果写入星图。

**改造方案**：

1. 新增 `galaxy_execution_consumer.py`（仿照 `galaxy_event_consumer.py`）：

- 订阅 `EXECUTION_RESULT_INGESTED` 事件
- 过滤条件：`trust_level == "trusted"` 且 `parsed_output` 不为空
- 处理逻辑：
  - 从 `parsed_output` 中提取关键信息（使用 LLM 做一次轻量级的知识提取）
  - 调用 `galaxy_service.create_node()` 创建知识节点
  - 节点类型：`execution_artifact`
  - 与用户已有的相关节点建立连线（通过 LLM 判断关联性，或通过 `target_env` + `goal` 的 embedding 相似度匹配）
  - 节点的 `source` 标记为 `"openclaw_execution"`，`origin_intent_id` 关联到原始 intent

2. 数据模型：
- `galaxy_nodes` 表已有 `source` 字段，新增枚举值 `"openclaw_execution"`
- 节点的 `metadata` JSONB 中存储：`{"intent_id": "...", "target_env": "browser", "execution_duration_ms": 12345}`

## 7.3 成就系统融合

**方案**：
- 新增执行相关成就：
  - "首次远程执行"、"连续 10 次成功执行"、"节省了 X 小时"
  - 基于 `execution_learning_service.py` 的统计数据触发
- 执行效率指标进入成长报告：
  - "本周你通过 Agent 完成了 12 项数字任务，节省了约 3 小时"
  - "你最常委派的任务类型是：资料检索 (45%)、代码操作 (30%)、文档整理 (25%)"

### 详细技术方案

在 `achievement_engine.py` 的新增成就定义中添加执行相关成就：

```python
# 新增事件类型映射
"first_execution": "首次远程执行",
"execution_streak_10": "连续10次成功执行",
"execution_streak_50": "连续50次成功执行",
"execution_hours_saved": "累计节省X小时",
"execution_diversity": "使用了3种以上的执行环境",
```

触发逻辑：
- 在 `execution_ingestor.py` 的 `_apply_execution_result()` 中，当 `intent.status == SUCCEEDED` 时，发布细分事件：
  - `{"event_type": "execution_succeeded", "user_id": ..., "target_env": ..., "duration_ms": ...}`
- `achievement_event_consumer.py` 已订阅事件总线，新增对 `execution_succeeded` 的处理
- 统计逻辑复用 `execution_learning_service.py` 的查询方法

成长报告融合：
- 在 `services/report/` 的报告生成中，新增"执行概览"板块
- 数据来源：`execution_intents` + `execution_records` 按用户、按周聚合

## 7.4 认知核心融合

**方案**：
- 执行偏好和执行模式成为用户画像的一部分
- 认知棱镜（Cognitive Prism）能感知用户的执行习惯，调整交互策略：
  - 用户频繁拒绝执行 → 降低主动委派建议频率
  - 用户频繁手动做可自动化的事 → 温和提示"这个我可以帮你做"
  - 用户在某个时间段更倾向于委派 → 学习时间偏好
- 双核路由器（DualCoreRouter）能在感知到"用户需要执行帮助"时，主动切换到执行模式

### 详细技术方案

1. 在 `profile_context_service.py`（已在 Phase 3 中扩展了 `execution_pattern` 相关字段）基础上，新增：
   - `execution_preference_profile`：用户的实际执行行为画像（而不是用户声称的偏好）
   - 字段：`delegate_acceptance_rate`, `preferred_execution_time_slots`, `category_success_rates`
   - 这些数据由 `execution_learning_service.py` 在每次执行后更新

2. 在 `dual_core_router.py` 的 `DualCoreRoutingInput` 中新增字段：
   - `has_openclaw_connected: bool`
   - `execution_preference_mode: str`
   - `recent_execution_success_rate: float | None`
   - 在路由决策中：如果用户已连接 OpenClaw 且成功率 > 0.8，当意图涉及"可执行的数字操作"时，增加路由到 Execution Core 的权重

3. 在 `cognitive_service.py` 的认知棱镜中，新增执行维度：
   - 用户拒绝率高的操作类别 → 降低主动委派建议频率
   - 用户手动完成了可自动化的任务 → 温和建议"这个我可以帮你做"
   - 建议的触发时机：不是每次都建议，而是通过一个 `suggestion_cooldown`（默认 3 次）控制 — 连续 3 次拒绝后进入 7 天冷却

## 7.5 社区融合

**方案**：
- 用户可以在社区分享自己的"执行模板"（脱敏后）
- 其他用户可以"采纳"别人的模板到自己的 OpenClaw
- 群组内可以有共享的执行策略（如学习小组共用的"论文检索模板"）
- 这让 OpenClaw 从"个人工具"变成"社区共建的能力库"

### 详细技术方案

1. 在 `community_service.py` 新增"执行模板分享"功能：
   - 用户可以将自己的执行模板（脱敏：移除 `working_dir`、`user_id` 等私人信息）发布到社区
   - 数据模型：复用现有的社区内容发布机制，新增 `content_type="execution_template"`
   - 模板分享时包含：`name`, `description`, `target_env`, `estimated_duration`, `success_rate`（该用户自己的）

2. "采纳"流程：
   - 其他用户看到分享的模板后，点击"采纳"
   - 后端将该模板写入该用户的 `execution_template_overrides`（存在 `user_preferences` 中）
   - 下次该用户的任务匹配到该模板时优先使用

3. 群组共享执行策略：
   - 群组管理员可以设置"群组默认执行模板"
   - 存储在 `groups` 表的 `settings` JSONB 中
   - 群成员委派任务时，模板匹配额外考虑群组模板

---

# Phase 8: 多设备与连接体验 — "无处不在的延伸"

**目标**：让用户的 OpenClaw 连接稳定、简单、安全，支持多设备场景。

## 8.1 连接配对简化

**现状问题**：当前配对需要手动填写 Gateway URL、选择认证方式、输入 Token。这对普通用户来说太技术化了。

**方案**：
- **扫码配对**：OpenClaw 桌面端显示一个二维码，Sparkle App 扫描即可完成配对（二维码包含 gateway URL + 一次性配对 token）
- **发现模式**：同一局域网内，Sparkle 自动发现运行中的 OpenClaw 节点（mDNS/Bonjour），用户只需点击确认
- **一键预设**：对于标准部署（Tailscale、Cloudflare Tunnel），提供一键配置模板
- 配对成功后，设备之间通过 Ed25519 长期密钥维持信任关系，不需要反复输入 Token

### 详细技术方案

**现状锚点**：

当前配对流程（`openclaw_connection_panel.dart`）：用户手动填写 Gateway URL → 选择 Auth Mode → 输入 Token → 点"测试连接"。纯技术操作。

**改造方案**：

1. **扫码配对**：
   - OpenClaw 桌面端新增一个 API 端点 `GET /v1/pair/qr`，返回二维码数据（JSON：`{"gateway_url": "ws://...", "pair_token": "one-time-token", "device_name": "My MacBook"}`）
   - Sparkle App 新增二维码扫描页面（使用 `mobile_scanner` Flutter 包）
   - 扫描后自动填充所有配置字段，一键完成配对
   - 后端调用 `PUT /api/v1/executions/connection/profile` 写入配置

2. **局域网发现**：
   - 后端（Python）新增一个 mDNS/Bonjour 广播服务（使用 `zeroconf` 库）
   - 当 OpenClaw 启动时广播 `_openclaw._tcp.local.` 服务
   - Flutter 端使用 `nsd_flutter` 包扫描局域网内的 OpenClaw 服务
   - 发现后展示设备列表，用户点击即配对
   - 这是一个可选的增强功能，不阻塞主流程

3. **一键预设**：
   - 在 `openclaw_connection_panel.dart` 的预设下拉框（当前已有 `guest_local_main`）中新增：
     - `tailscale`：自动获取 Tailscale IP，构建 `ws://100.x.x.x:18789`
     - `cloudflare_tunnel`：提示用户填入 Tunnel 域名
   - 每个预设提供配置向导，而不是让用户自己拼 URL

## 8.2 多节点管理

**现状**：代码支持多节点但 UI 体验是单节点的。

**方案**：
- OpenClaw Hub 升级为真正的"设备管理中心"：
  - 展示所有已配对设备的实时状态（在线/离线/忙碌）
  - 每个设备的能力标签（有浏览器、有 GPU、有开发环境…）
  - 设备亲和性设置（"代码相关的任务发到工作站，浏览相关的发到笔记本"）
- 任务调度器根据设备能力自动选择最合适的节点
- 设备离线时优雅降级：不是报错，而是"你的工作站当前不在线，要等它上线后自动执行，还是换到笔记本上？"

### 详细技术方案

**现状锚点**：

`openclaw_hub_screen.dart`（847 行）已经有节点列表展示，`execution_service.py` 有 `list_nodes()` 和 `invoke_node()` 方法。但调度逻辑是"用户指定或默认"。

**改造方案**：

1. 在 `execution_service.py` 新增 `_select_best_node()` 方法：

```python
async def _select_best_node(
    self, *, user_id: UUID, target_env: ExecutionTargetEnv, nodes: list[dict]
) -> dict | None:
    """根据节点能力和负载选择最优节点。

    选择因子：
    1. 能力匹配：节点 capabilities 包含 target_env
    2. 负载：节点当前 run 数量（通过 list_nodes 的 status 字段判断）
    3. 历史成功率：该用户在该节点的历史执行成功率
    4. 用户亲和性：用户 preference 中指定的节点偏好
    """
```

2. 在 `user_preferences` 的 `execution_preferences` 中新增：
   ```python
   "node_affinity": {
       "browser": "node-macbook-pro",   # 浏览器任务发到这台
       "shell": "node-workstation",     # 终端任务发到这台
   }
   ```

3. 前端在 `openclaw_hub_screen.dart` 新增"设备亲和性"设置入口：
   - 展示所有已配对设备
   - 为每种任务环境指定偏好设备
   - 未指定时自动选择

4. 离线优雅降级：
   - `dispatch()` 中，如果选中的节点离线：
     - 检查是否有其他在线节点能执行该任务
     - 如果有：自动切换，并通过 stream_sink 通知前端"已切换到备用设备"
     - 如果没有：进入"等待上线"模式，任务状态标记为 `QUEUED`
     - 新增 `ExecutionIntentStatus.QUEUED` 枚举值
     - 新增后台轮询（Celery Beat，每 60 秒检查一次），节点上线后自动 dispatch

## 8.3 连接稳定性

**方案**：
- WebSocket 断线自动重连（指数退避 + jitter）
- 连接状态在 Sparkle App 顶栏有持续可见的指示器（类似蓝牙/WiFi 图标）
- 跨公网场景下，提供内置的连接诊断工具："连接失败？点击这里，我帮你排查"
- 支持离线排队：设备不在线时，任务进入待执行队列，设备上线后自动 dispatch

### 详细技术方案

1. **断线重连**（`gateway_ws_client.py`）：
   - 在 `_connect()` 中包装重连逻辑：
     - 首次失败：等 1 秒重试
     - 第二次失败：等 2 秒
     - 第三次：等 4 秒
     - 最大等待 30 秒
     - 总重试次数不超过 5 次
     - Jitter：等待时间 ±20% 随机偏移

2. **连接状态指示器**（Flutter）：
   - 在 App 顶栏（`app_bar.dart` 或全局 overlay）新增一个 OpenClaw 连接状态图标
   - 状态来源：`openclaw_connection_service.dart` 已有 `OpenClawConnectionInfo.status`
   - 三种状态：绿色（已连接）、黄色（降级/执行中）、灰色（未连接/不可达）
   - 点击图标打开连接诊断面板

3. **连接诊断工具**：
   - 后端新增 API `GET /api/v1/executions/connection/diagnose`
   - 执行一系列检查：
     - DNS 解析（gateway URL 能否解析）
     - TCP 连接（端口是否可达）
     - WebSocket 握手（协议是否匹配）
     - 认证（token/设备密钥是否有效）
     - OpenClaw 版本兼容性
   - 返回一个诊断报告，前端渲染为分步检查列表（类似 macOS 网络诊断）

---

# Phase 9: 商业级健壮性 — "用户可以放心用"

**目标**：把所有边界情况、安全防护、资源管控做到用户无需担心。

## 9.1 并发与资源管控

**现状问题**：`OPENCLAW_MAX_CONCURRENT_RUNS=3` 已配置但**未实际执行**限流。

**方案**：
- 后端实际执行并发限流（Redis 分布式信号量）
- 超过限额时排队而非拒绝，并通知用户"当前有 2 个任务在执行，你的任务排在第 3 位"
- Token 预算管控：用户可设置每日/每月的 Token 消耗上限
- 执行时长预估：dispatch 前基于历史数据预估耗时，让用户有预期

### 详细技术方案

**现状锚点**：

`settings.py` 中 `OPENCLAW_MAX_CONCURRENT_RUNS=3` 已定义但在 `execution_service.py` 中没有实际检查。

**改造方案**：

1. 在 `execution_service.py` 的 `dispatch()` 方法最前面新增并发检查：

```python
async def _check_concurrency(self, *, user_id: UUID) -> None:
    """检查当前用户是否有并发执行配额。"""
    active_count = await self._db.scalar(
        select(func.count(ExecutionIntent.id)).where(
            ExecutionIntent.user_id == user_id,
            ExecutionIntent.status.in_([
                ExecutionIntentStatus.DISPATCHED,
                ExecutionIntentStatus.RUNNING,
                ExecutionIntentStatus.WAITING_APPROVAL,
            ]),
        )
    )
    if active_count >= self._config.max_concurrent_runs:
        raise ExecutionConcurrencyExceeded(
            f"当前有 {active_count} 个任务在执行中，最多允许 {self._config.max_concurrent_runs} 个并发。"
        )
```

2. Token 预算管控：
   - 在 `user_preferences` 新增 `execution_budget`：
     ```python
     "execution_budget": {
         "daily_token_limit": 100000,   # None 表示无限制
         "monthly_token_limit": None,
         "daily_used": 0,
         "monthly_used": 0,
         "reset_date": "2026-04-02",
     }
     ```
   - 在 `execution_ingestor.py` 的 `ingest()` 中，执行完成后累加 `token_usage` 到预算
   - 在 `dispatch()` 前，检查当日预算是否超限
   - 超限时返回友好提示而不是直接报错

3. 执行时长预估：
   - 在 `execution_learning_service.py` 新增 `estimate_duration(target_env, goal_keywords) -> int | None`
   - 基于历史同类型执行的中位数时长
   - 返回值附加在 intent 的 metadata 中，前端展示"预计 X 分钟"

## 9.2 安全沙箱强化

**方案**：
- Sparkle 侧的 policy 层增加"不可逆操作白名单"机制：
  - 默认禁止：`rm -rf`、`drop table`、`git push --force`、支付类操作
  - 用户可以逐项解锁，但需要二次确认
- 敏感数据检测：在 intent 发送前检查是否包含密码、API Key 等敏感信息
- 执行审计日志：所有执行操作在 Sparkle 侧留完整审计链（谁、什么时候、做了什么、结果是什么）

### 详细技术方案

1. 不可逆操作白名单：
   - 在 `execution_risk_assessor.py`（6.3 中新增的）中新增硬性禁止列表：
     ```python
     BLOCKED_COMMANDS = [
         r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+/|-[a-zA-Z]*r[a-zA-Z]*\s+/)",
         r"\bdd\s+if=",
         r"\bmkfs\b",
         r"\b:()\s*\{",  # fork bomb
     ]
     ```
   - 在 `intent_translator.py` 的 `translate()` 中，最终 payload 发送前扫描 `instructions` 和 `goal`
   - 命中时直接拒绝 dispatch，返回具体原因："该指令包含不可逆操作（删除整个目录），出于安全考虑无法自动执行"

2. 敏感数据检测：
   - 在 `intent_translator.py` 中，dispatch 前扫描 intent payload
   - 检测常见敏感数据模式（信用卡号、API Key 格式、JWT 格式）
   - 命中时：不阻止执行（因为用户可能确实需要操作这些），但在 `metadata` 中标记 `contains_sensitive_data=True`
   - 前端渲染时显示一个警告："本次执行涉及敏感数据，请确认执行环境安全"

3. 执行审计日志：
   - 新增 `execution_audit_log` 表：
     ```sql
     CREATE TABLE execution_audit_log (
         id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
         intent_id UUID NOT NULL REFERENCES execution_intents(id),
         user_id UUID NOT NULL,
         action TEXT NOT NULL,           -- "dispatch"|"confirm"|"reject"|"cancel"|"timeout"|"retry"
         actor TEXT NOT NULL,            -- "user"|"system"|"auto_timeout"
         details JSONB,                  -- 任意详情
         created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
     );
     ```
   - 在 `execution_service.py` 的每个关键操作（dispatch, confirm, reject, cancel）后写入审计记录
   - 不影响主流程性能（异步写入或通过 EventBus 投递）

## 9.3 错误恢复与智能诊断

**方案**：
- 构建执行错误知识库（基于历史执行数据）：
  - 常见错误 → 自动修复建议（"网页加载超时，可能是网络问题，要重试吗？"）
  - 重复失败 → 主动降级（"这个网站似乎屏蔽了自动访问，要不要我换个方式？"）
- 错误发生时，Sparkle 不只是显示错误，而是像一个伙伴一样给出建议
- 支持"一键重试"（带上次的上下文），而不是让用户从头开始

### 详细技术方案

1. 执行错误知识库：
   - 在 `execution_learning_service.py` 新增方法 `get_error_suggestion(error_category, target_env) -> dict | None`
   - 基于历史数据聚合：相同 `error_category` + `target_env` 的后续操作统计
   - 返回结构：
     ```python
     {
         "suggestion": "网页加载超时，可能是网络问题",
         "retry_success_rate": 0.72,  # 同类错误重试的成功率
         "recommended_action": "retry" # "retry" | "manual" | "alternative"
     }
     ```

2. 前端错误卡片增强（`action_card.dart`）：
   - 当执行失败时，不只是显示红色错误
   - 显示：错误描述 + 建议操作 + "一键重试"按钮
   - "一键重试"：复用原始 intent 的参数创建新 intent 并 dispatch
   - 建议操作来自后端的 `get_error_suggestion()`

3. 重复失败主动降级：
   - 在 `execution_service.py` 中，如果同一个 goal（或相似 goal）连续失败 3 次：
     - 进入降级模式：不再尝试自动执行
     - 生成一份"手动操作指南"（由 LLM 根据意图生成步骤）
     - 推送给用户："我试了 3 次都没有成功，可能环境有问题。这是一份手动操作步骤：..."

## 9.4 优雅降级

**方案**：
- OpenClaw 不可用时，Sparkle 的所有功能必须正常工作（这是已有原则，但需要在 UI 层彻底贯彻）
- 所有可能触发 OpenClaw 的入口都有"手动模式"兜底
- 降级时的措辞是"我可以给你详细的步骤指引，你自己来操作"而不是"功能不可用"

### 详细技术方案

1. OpenClaw 不可用时的体验：
   - `_looks_like_openclaw_chat_control_request()` 返回 True 但 `dispatch()` 失败时（连接不可达）：
     - 不返回错误卡片
     - 改为在正常对话流中回复："看起来你想在你的电脑上做这件事，但当前 OpenClaw 没有连接。我可以给你详细的操作步骤，你自己来执行。"
     - 然后让 LLM 基于用户意图生成手动操作指南
   - 这样 OpenClaw 不可用时，Sparkle 从"执行助手"退化为"咨询助手"，而不是直接报错

2. 前端降级 UI：
   - OpenClaw Hub 页面在设备离线时，不显示空状态，而是显示"连接指南"
   - 聊天中的执行相关回复，在 OpenClaw 不可用时仍然能展示手动步骤

---

# Phase 10: 智能委派引擎 — "Sparkle 主动帮你做"

**目标**：从"用户主动发起委派"进化到"Sparkle 主动识别可委派的时机并建议执行"。

## 10.1 主动委派建议

**方案**：
- 当用户在聊天中描述一个手动操作时（"我需要去查一下…""我得下载这个…"），Sparkle 自动识别并温和建议："我可以帮你做这个，要不要让我试试？"
- 建议的频率和方式基于用户画像（参见 6.1 的偏好系统）
- 不是弹窗打断，而是在对话流中自然地提出
- 这与现有的 `_maybe_short_circuit_bridge_tool()` 逻辑对齐，但从"检测显式指令"升级为"理解隐含意图"

### 详细技术方案

1. 在 `orchestrator.py` 的主对话流中（LLM 响应生成后），新增一个后处理步骤：

```python
async def _maybe_suggest_delegation(
    self,
    *,
    user_message: str,
    assistant_response: str,
    user_id: UUID,
    session_id: str,
) -> ChatResponse | None:
    """如果助手响应中包含'可委派'的操作建议，主动询问是否委派。"""
```

- 触发条件：LLM 的回复中包含类似"你可以去...""你需要...""建议你..."的操作建议，且这些操作属于可委派类型
- 不是用关键词匹配，而是让 LLM 在 system prompt 中被指示：当你建议用户做某个数字操作时，在回复的 metadata 中标记 `{"delegable": true, "delegation_summary": "在浏览器中搜索 React Server Components"}`
- 如果 `delegable=True` 且用户已连接 OpenClaw：在助手回复末尾追加一句"要不要我直接帮你在电脑上做？" + 一个快捷委派按钮
- 如果用户偏好是 `autonomous`，不问直接做（但事后告知）

2. 委派建议频率控制：
   - 在 session context 中维护一个 `delegation_suggestions_count` 和 `delegation_suggestions_accepted`
   - 如果连续 3 次建议被忽略（用户没有点委派按钮），进入冷却（本 session 内不再建议）
   - 跨 session 的冷却：存在 `user_preferences` 中，7 天后重置

## 10.2 批量执行编排

**方案**：
- 支持用户一次性委派多个相关任务，Sparkle 自动编排执行顺序
- 任务之间的依赖关系自动检测（"先查资料，再写摘要，最后发邮件"）
- 并行无依赖任务以缩短总耗时
- 整个批次有统一的进度视图和最终报告

### 详细技术方案

1. 在 `execution_service.py` 新增方法：

```python
async def dispatch_batch(
    self,
    *,
    intents: list[UUID],  # intent IDs
    user_id: UUID,
    execution_strategy: str = "auto",  # "auto" | "sequential" | "parallel"
) -> BatchExecutionHandle:
```

- `auto` 模式：根据 intent 之间的依赖关系自动决定串行/并行
- 依赖关系检测：通过 LLM 分析各 intent 的 goal，判断是否有输入输出依赖
- `BatchExecutionHandle` 包含：`batch_id`, `status`, `task_ids`, `completed_count`, `failed_count`

2. 前端在聊天流中渲染批量执行卡片：
   - 整体进度条（N/M 完成）
   - 可展开查看每个子任务的状态
   - 支持对单个子任务确认/拒绝

## 10.3 定时/条件执行

**方案**：
- 用户可以设置定时任务："每天早上 8 点帮我查看 GitHub 通知"
- 条件触发："当这个 PR 被 merge 后，帮我更新文档"
- 与 Sparkle 日历系统集成，执行结果出现在用户的日程视图中
- 基于 Celery Beat 调度，结果通过 EventBus 推送

### 详细技术方案

1. 新增 `execution_schedule` 表：
   ```sql
   CREATE TABLE execution_schedules (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       user_id UUID NOT NULL REFERENCES users(id),
       intent_template JSONB NOT NULL,    -- 序列化的 intent 模板
       trigger_type TEXT NOT NULL,        -- "cron" | "event" | "condition"
       trigger_config JSONB NOT NULL,     -- cron: {"cron": "0 8 * * *"}, event: {"event_type": "pr_merged"}, condition: {"check_url": "...", "condition": "contains('merged')"}
       last_run_at TIMESTAMPTZ,
       next_run_at TIMESTAMPTZ,
       is_active BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );
   ```

2. Celery Beat 集成：
   - 新增 Celery 任务 `execution_scheduler_tick`，每分钟执行一次
   - 查询 `next_run_at <= now()` 的活跃 schedule，dispatch 对应的 intent
   - Cron 类型：标准 cron 表达式解析
   - 条件类型：轮询检查条件是否满足（有频率限制，最多每 5 分钟检查一次）

3. 前端在 OpenClaw Hub 新增"定时任务"标签页：
   - 展示所有活跃的定时执行
   - 支持创建（简化界面：选模板 + 设定时间/条件）
   - 支持暂停/恢复/删除

4. 结果通过 EventBus 推送通知到 Flutter：
   - 定时执行完成后发布 `EXECUTION_SCHEDULED_COMPLETED` 事件
   - `achievement_event_consumer` 或新的 consumer 转为 push notification
   - 用户打开 App 后在通知中心看到结果

---

## 实施优先级与依赖关系

```
Phase 5 (实时感知)  ──┐
                       ├──→ Phase 7 (系统融合) ──→ Phase 10 (智能委派)
Phase 6 (信任谱系)  ──┘         │
                                │
Phase 8 (多设备连接) ──────────┘

Phase 9 (商业健壮性) ← 贯穿所有阶段，每个阶段都要做对应的健壮性工作
```

**建议的实施顺序**：

| 顺序 | Phase | 理由 |
|------|-------|------|
| 1st | **Phase 5** (实时感知) | 用户体验的基础。没有实时反馈，后面的一切都打折扣 |
| 2nd | **Phase 6** (信任谱系) | 让不同用户都能找到舒适区，是"可以放心用"的前提 |
| 3rd | **Phase 9.1-9.2** (并发管控 + 安全) | 商业上线的底线 |
| 4th | **Phase 8.1** (扫码配对) | 降低接入门槛，从"开发者能用"到"普通用户能用" |
| 5th | **Phase 7.1-7.2** (计划 + 星图融合) | 体现"深度融合"的核心价值 |
| 6th | **Phase 7.3-7.5** (成就 + 认知 + 社区) | 完成全系统渗透 |
| 7th | **Phase 8.2-8.3** (多节点 + 稳定性) | 多设备场景的完整体验 |
| 8th | **Phase 10** (智能委派) | 最高级的体验，需要前面所有积累 |
| 贯穿 | **Phase 9.3-9.4** (错误恢复 + 降级) | 每个阶段同步完善 |

---

## 数据依赖关系详解

```
Phase 5 (实时感知)
  └─ 新增: stream_sink 参数, _ExecutionLiveOutputWidget
  └─ 修改: gateway_ws_client.execute(), execution_service._handle_gateway_stream_event()
  └─ 修改: execution_engine._maybe_short_circuit_openclaw_chat_control() → 改为 async generator
  └─ 修改: chat_orchestrator_protocol.go (status_update 承载中间状态)
  └─ 修改: action_card.dart (新增执行中动态状态)

Phase 6 (信任谱系)
  └─ 新增: execution_risk_assessor.py
  └─ 新增: user_preferences.execution_preferences JSONB
  └─ 修改: execution_service.create_intent() (合并用户偏好到 policy)
  └─ 修改: execution_learning_service.py (维度化信任)
  └─ 新增: Flutter 执行偏好设置页
  └─ 依赖: Phase 5 的 stream_sink (用于推送确认请求)

Phase 7 (系统融合)
  └─ 新增: galaxy_execution_consumer.py
  └─ 新增: execution_audit_log 表
  └─ 修改: execution_template_service.py (delegability 评估)
  └─ 修改: orchestrator.py (计划审阅时标注可委派性)
  └─ 修改: achievement_engine.py (新增执行成就)
  └─ 修改: profile_context_service.py (执行行为画像)
  └─ 修改: dual_core_router.py (执行维度路由)
  └─ 依赖: Phase 6 的偏好系统 (决定哪些任务自动委派)

Phase 8 (多设备连接)
  └─ 新增: 扫码配对流程
  └─ 新增: 连接诊断 API
  └─ 修改: gateway_ws_client.py (断线重连)
  └─ 修改: execution_service.py (节点智能选择 + QUEUED 状态)
  └─ 新增: execution_schedules 表
  └─ 依赖: Phase 9.1 (并发管控，否则多节点场景可能超限)

Phase 9 (商业健壮性)
  └─ 新增: 并发检查逻辑
  └─ 新增: Token 预算管控
  └─ 新增: 安全审计日志
  └─ 修改: intent_translator.py (敏感数据检测)
  └─ 修改: execution_learning_service.py (错误诊断)
  └─ 修改: action_card.dart (错误恢复 UI)
  └─ 独立于其他 Phase，可并行推进

Phase 10 (智能委派)
  └─ 修改: orchestrator.py (LLM 输出后处理 + delegation metadata)
  └─ 新增: dispatch_batch() 批量编排
  └─ 新增: execution_schedules 定时任务
  └─ 依赖: Phase 5 (流式输出), Phase 6 (偏好系统), Phase 7.4 (认知融合), Phase 9.1 (并发管控)
```

---

## 每个 Phase 的验收标准

**Phase 5 验收**：
- 用户发送聊天控制指令后，在执行完成前能看到至少 3 个中间状态更新
- 超时前 80% 时收到预警通知
- 用户可延长超时
- transport=responses_http 时回退到现有行为，不报错

**Phase 6 验收**：
- 用户可在设置中选择三种偏好模式并立即生效
- cautious 模式下所有执行都需用户确认才 dispatch
- autonomous 模式下浏览器读取类任务直接执行
- 高风险操作（rm -rf 等）在任何模式下都强制确认
- 连续失败某个类别后该类别自动降级

**Phase 7 验收**：
- 计划审阅卡片上可委派的任务有 toggle
- 勾选委派的任务在计划批准后自动执行
- TRUSTED 执行结果出现在知识星图中
- 执行成就正常解锁
- 认知棱镜能反映用户的执行习惯

**Phase 8 验收**：
- 扫码配对 3 步内完成
- 多节点时任务自动路由到最合适的节点
- 节点离线时任务排队等待而不是失败
- WebSocket 断线后 30 秒内自动重连

**Phase 9 验收**：
- 第 4 个并发任务被排队而不是执行
- 日 Token 预算超限后友好提示
- 敏感数据操作有警告
- 执行失败时有具体建议和一键重试
- OpenClaw 离线时 Sparkle 给出手动步骤

**Phase 10 验收**：
- LLM 建议操作时自动附带委派选项
- 连续 3 次忽略后停止建议（7 天冷却）
- 批量执行有统一进度视图
- 定时任务在指定时间自动执行

---

## 附录：新增数据结构定义

### 用户偏好数据模型

```python
{
    "execution_preferences": {
        "mode": "balanced",  # "cautious" | "balanced" | "autonomous" | "custom"
        "custom_rules": {
            "browser_read": "auto",
            "browser_write": "confirm",
            "file_read": "auto",
            "file_write": "confirm",
            "file_delete": "confirm",
            "shell_exec": "confirm",
            "shell_read": "auto",
            "install": "reject",
            "send": "confirm",
        },
        "notification_level": "essential",
        "auto_extend_timeout": True,
        "trust_auto_upgrade": True,
        "node_affinity": {
            "browser": "node-macbook-pro",
            "shell": "node-workstation",
        }
    },
    "execution_budget": {
        "daily_token_limit": 100000,
        "monthly_token_limit": None,
        "daily_used": 0,
        "monthly_used": 0,
        "reset_date": "2026-04-02",
    }
}
```

### 新增数据库表

```sql
-- 执行审计日志表
CREATE TABLE execution_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_id UUID NOT NULL REFERENCES execution_intents(id),
    user_id UUID NOT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 定时执行表
CREATE TABLE execution_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    intent_template JSONB NOT NULL,
    trigger_type TEXT NOT NULL,
    trigger_config JSONB NOT NULL,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 新增枚举值

```python
# ExecutionIntentStatus 新增
QUEUED = "queued"  # 节点离线时排队等待

# 执行偏好 custom_rules 的可能值
APPROVAL_ACTION = "auto" | "confirm" | "skip" | "reject"
```

### 新增事件类型

```python
# 执行相关事件
EXECUTION_DELTA = "execution.delta"
EXECUTION_TOOL_CALL = "execution.tool_call"
EXECUTION_LIFECYCLE = "execution.lifecycle"
EXECUTION_DEGRADED = "execution.degraded"
EXECUTION_TIMEOUT_WARNING = "execution.timeout_warning"
EXECUTION_BATCH_STARTED = "execution.batch_started"
EXECUTION_BATCH_COMPLETED = "execution.batch_completed"
EXECUTION_SCHEDULED_COMPLETED = "execution.scheduled_completed"
EXECUTION_SUCCEEDED = "execution.succeeded"
```

---

## 一句话总结

当前 OpenClaw 是"一条跑得通的链路"。这份方案的目标，是把它变成**"用户打开 Sparkle 就自然而然想委派任务、执行无感、反馈即时、信任渐进、价值闭环的核心能力"** — 不是加了个功能，而是 Sparkle 长出了手脚。

---

**文档结束**

本文档是 OpenClaw 子系统从"技术验证"到"商业产品"的完整路线图。所有设计都基于现有代码的真实状态，确保可执行、可验收、不漂移。
