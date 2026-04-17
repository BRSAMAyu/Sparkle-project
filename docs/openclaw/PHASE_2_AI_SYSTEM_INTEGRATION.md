# Phase 2: AI系统贯通 — "让执行成为对话的自然延伸"

> **交给Coding Agent执行的完整指令**
> **预计改动**: 5个新文件, 6个修改文件 (Python后端 + Flutter)
> **依赖**: Phase 1 已完成

---

## 背景

Phase 1 完成了执行UI的视觉升级。但执行仍然是一个需要用户主动进入任务详情页才能触发的独立操作。本阶段目标: 将执行链路嵌入Sparkle的核心AI对话流, 让Orchestrator能主动建议委派, 让执行结果直接在聊天流中展示。

### 关键现有代码

- `ChatOrchestrator.process_stream()` (backend/app/orchestration/orchestrator.py ~line 655) — 主对话处理流
- `UXEnvelopeBuilder.build()` (backend/app/orchestration/ux_envelope.py ~line 199) — 5种展示模式
- `AgentProfileRegistry` (backend/app/core/agent_profiles.py) — 13+个Agent人格
- `websocket_chat_service_v2.dart` (mobile) — 聊天WebSocket服务
- `chat_stream_events.dart` (mobile) — 聊天流事件模型

---

## 任务 2.1: 后端 — Orchestrator执行意图检测

**修改文件**: `backend/app/orchestration/orchestrator.py`

### 修改目标

在 `process_stream()` 的路由决策阶段(约line 1191-1220, route decision部分), 增加执行意图检测逻辑。当用户消息匹配可委派模式时, 在response metadata中注入执行建议。

### 精确修改

#### 1. 添加import (文件顶部)

```python
from app.core.execution_router import ExecutionRouter
from app.config.settings import settings
```

#### 2. 新增私有方法 `_detect_execution_suggestion`

在ChatOrchestrator类中添加(建议放在路由相关方法附近):

```python
async def _detect_execution_suggestion(
    self,
    user_message: str,
    task_context: dict[str, Any] | None,
    cognitive_context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Detect if user's message implies a task that could be delegated to OpenClaw.

    Returns execution suggestion metadata or None.
    """
    if not settings.OPENCLAW_ENABLED:
        return None

    # 不在有活跃任务上下文时才建议
    if not task_context or not task_context.get("active_task_id"):
        return None

    task_id = task_context["active_task_id"]

    # 关键词模式匹配 — 检测委派意图
    delegation_signals = [
        "帮我查", "帮我找", "帮我搜", "帮我整理", "帮我总结",
        "你来做", "交给你", "自动完成", "帮我执行",
        "help me search", "look up", "find for me", "summarize this",
    ]

    message_lower = user_message.lower()
    has_delegation_signal = any(sig in message_lower for sig in delegation_signals)

    if not has_delegation_signal:
        return None

    # 用ExecutionRouter做正式分类
    try:
        router = ExecutionRouter(openclaw_enabled=True)
        task_type = task_context.get("task_type", "general")
        task_description = task_context.get("task_description", user_message)

        decision = router.classify(
            task_type=task_type,
            task_description=task_description,
            has_side_effects=False,  # 保守估计
            success_criteria=None,
        )

        if decision.mode.value in ("agent", "hybrid"):
            return {
                "type": "execution_suggestion",
                "task_id": task_id,
                "execution_mode": decision.mode.value,
                "reason": decision.reason,
                "suggested_action": "handoff",
            }
    except Exception:
        pass  # 检测失败不影响主流程

    return None
```

#### 3. 在process_stream中注入执行建议

在 `process_stream()` 方法中, 在构建response metadata的位置(搜索 `metadata` 或 `ux_envelope` 相关的代码), 在最终yield response之前, 添加执行建议检测:

```python
# 在构建最终response的附近, 检测执行建议
execution_suggestion = await self._detect_execution_suggestion(
    user_message=request.content,
    task_context=context_data.get("task_context") if context_data else None,
    cognitive_context=context_data.get("cognitive_context") if context_data else None,
)

# 将建议注入到response的metadata中
if execution_suggestion:
    # metadata是已有的dict, 在其中追加
    if "metadata" not in final_response_data:
        final_response_data["metadata"] = {}
    final_response_data["metadata"]["execution_suggestion"] = execution_suggestion
```

**重要注意**: 你需要找到process_stream中实际构建和yield ChatResponse的确切位置, 上述代码是逻辑描述, 需要根据实际代码结构适配。核心原则: execution_suggestion作为metadata的一个字段随response下发, 不改变现有response结构。

---

## 任务 2.2: 后端 — UX信封系统扩展执行模式

**修改文件**: `backend/app/orchestration/ux_envelope.py`

### 精确修改

#### 1. 添加第6种展示模式

在 `_MODE_PROFILES` dict中(约line 48之后), 添加:

```python
"execution_delegate": PresentationProfile(
    mode_label="执行委派",
    companion_frame="我帮你把这个交给AI执行，你可以在完成前随时取回控制权。",
    answer_kind="delegation_brief",
    default_retry_options=["换一个方案执行", "我自己来", "修改执行参数"],
    first_screen_focus="delegation_status",
    next_actions_title="执行完成后",
    blocked_title="执行受限",
    blocked_message="当前任务不适合自动执行，建议手动完成。",
    partial_message="AI已部分完成执行，你可以在此基础上继续。",
    next_action_limit=2,
),
```

#### 2. 在build方法中增加执行模式选择逻辑

在 `UXEnvelopeBuilder.build()` 方法中, 选择presentation mode的逻辑附近(搜索mode selection或profile lookup), 添加:

```python
# 如果response metadata中包含execution_suggestion, 使用执行委派模式
if execution_validation and execution_validation.get("execution_suggestion"):
    mode_key = "execution_delegate"
```

这段逻辑应该在已有的mode selection逻辑之前, 作为优先判断。

---

## 任务 2.3: 后端 — Agent Profile添加执行助理

**修改文件**: `backend/app/core/agent_profiles.py`

### 精确修改

#### 1. 在AgentRole枚举中添加

```python
EXECUTION_ASSISTANT = "execution_assistant"
```

#### 2. 在registry的默认注册中添加profile

找到profiles注册的位置(通常在 `__init__` 或模块级别的profile定义), 添加:

```python
AgentProfile(
    role=AgentRole.EXECUTION_ASSISTANT,
    display_name="执行助理",
    description="协助任务委派、执行监控和结果验证的专用Agent",
    persona_archetype="reliable_executor",
    expertise_domains=["task_delegation", "execution_monitoring", "result_verification"],
    public_entry=False,
    model_tier=ModelTier.STANDARD,
    temperature=0.3,
    max_tokens=1024,
    system_prompt_template=(
        "你是Sparkle的执行助理。你的职责是:\n"
        "1. 精确描述任务目标，确保AI执行器理解用户意图\n"
        "2. 监控执行进度，在关键节点向用户汇报\n"
        "3. 验证执行结果是否符合用户预期\n"
        "4. 用简洁友好的语言与用户沟通执行状态\n"
        "保持简短、准确、可靠。不要过度解释，不要猜测用户未表达的需求。"
    ),
    allowed_tools=["execution_handoff", "execution_status", "execution_confirm"],
    tool_choice="auto",
    streaming=True,
    cost_tier=1,
),
```

---

## 任务 2.4: Flutter — 聊天流中渲染执行建议卡

**创建文件**: `mobile/lib/features/chat/presentation/widgets/execution_suggestion_card.dart`

### 设计规格

当聊天消息的metadata中包含 `execution_suggestion` 时, 在AI回复下方渲染一个可交互的委派建议卡片。

#### 构造函数
```dart
const ExecutionSuggestionCard({
  required Map<String, dynamic> suggestion,
  required VoidCallback onAccept,
  required VoidCallback onDismiss,
  Key? key,
})
```

#### 数据
`suggestion` map包含:
- `type`: "execution_suggestion"
- `task_id`: String
- `execution_mode`: "agent" | "hybrid"
- `reason`: String (路由原因)
- `suggested_action`: "handoff"

#### 布局

整体容器:
- `DS.surfaceSecondary` 背景
- `BorderRadius.circular(16)`, padding `DS.spacing12`
- 左边有3px宽竖条, 颜色 `DS.brandPrimary`

内容:
- 顶部: 图标 `Icons.smart_toy_rounded` (DS.brandPrimary) + 文字 "我可以帮你自动完成这个任务"(fontSize 14, w500)
- 中间: 路由原因 `suggestion['reason']` (fontSize 13, DS.textSecondary)
- 如果execution_mode == "hybrid": 额外提示 "执行完成后需要你确认结果"(fontSize 12, DS.semanticWarning)
- 底部: 两按钮横排
  - "交给AI" — FilledButton, DS.brandPrimary, 圆角16
  - "我自己来" — TextButton, DS.textSecondary, 圆角16

#### 入场动画
- 使用 `SparkleStaggerItem(index: 0, axis: Axis.vertical)` 包裹

#### 交互
- 点击"交给AI": 调用onAccept, 播放 `SensoryFeedbackEvent.confirm`
- 点击"我自己来": 调用onDismiss, 卡片用 `SparkleExitTransition` 消失
- 卡片需要是有状态的, 维护 `_dismissed` bool 控制 SparkleExitTransition

#### 必要import
```dart
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_motion_primitives.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
```

---

## 任务 2.5: Flutter — 聊天流中内联显示执行结果

**创建文件**: `mobile/lib/features/chat/presentation/widgets/execution_result_inline.dart`

### 设计规格

当执行完成后(succeeded/partial/failed), 在聊天流中渲染执行结果摘要, 用户无需跳转到任务详情页。

#### 构造函数
```dart
const ExecutionResultInline({
  required ExecutionIntentModel intent,
  ExecutionRecordModel? record,
  VoidCallback? onViewDetails,
  Key? key,
})
```

#### 布局 (根据状态不同)

**succeeded:**
- 容器: `DS.semanticSuccess.withOpacity(0.08)` 背景, 圆角16
- 顶行: check_circle图标(绿) + "AI执行完成" + 耗时badge
- 内容: parsedOutput摘要(前200字符), 用 `SelectableText` 让用户可以复制
- 底行: "查看详情" TextButton → 调用onViewDetails

**partial:**
- 容器: `DS.semanticWarning.withOpacity(0.08)` 背景
- 顶行: rule图标(黄) + "AI部分完成"
- 内容: 同上

**failed:**
- 容器: `DS.semanticError.withOpacity(0.08)` 背景
- 顶行: error_outline图标(红) + "执行未成功"
- 内容: intent.errorMessage (如果有), 或 "执行过程中遇到问题"
- 底行: "重试" TextButton + "我来做" TextButton

**指标行** (所有状态通用, 放在内容和底行之间):
- 水平Row, 小字(fontSize 11, DS.textTertiary):
  - "耗时 {durationMs格式化}" | "工具调用 {toolCallsCount}次" | "信任 {trustLevel.label}"
- 仅当record不为null时显示

#### 入场动画
- `SparkleStaggerItem(index: 0)`

---

## 任务 2.6: Flutter — 在聊天provider中处理执行建议

**修改文件**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart`

### 修改目标

在处理AI回复消息时, 检测metadata中的execution_suggestion, 存入provider state以供UI渲染。

### 精确修改

#### 1. State类中添加字段

找到chat provider的state class, 添加:
```dart
Map<String, dynamic>? pendingExecutionSuggestion;
```

#### 2. 消息处理中检测execution_suggestion

找到处理AI response/delta消息的方法(通常在处理WebSocket消息的回调中), 在解析metadata的位置添加:

```dart
// 检测执行建议
final metadata = message['metadata'] as Map<String, dynamic>?;
if (metadata != null && metadata.containsKey('execution_suggestion')) {
  state = state.copyWith(
    pendingExecutionSuggestion: metadata['execution_suggestion'] as Map<String, dynamic>,
  );
}
```

#### 3. 处理用户接受建议

添加方法:
```dart
Future<void> acceptExecutionSuggestion() async {
  final suggestion = state.pendingExecutionSuggestion;
  if (suggestion == null) return;

  final taskId = suggestion['task_id'] as String?;
  if (taskId == null) return;

  // 清除建议
  state = state.copyWith(pendingExecutionSuggestion: null);

  // 委托给task provider发起handoff
  // 注意: 跨provider调用需要通过ref, 具体实现取决于你的provider架构
  // 可能需要通过callback或shared service实现
}

void dismissExecutionSuggestion() {
  state = state.copyWith(pendingExecutionSuggestion: null);
}
```

**注意**: 跨provider调用(chat → task)的具体实现方式取决于项目的Riverpod架构。如果provider间不能直接引用, 可以:
1. 在chat_provider中expose suggestion, 让UI层通过ref同时读取两个provider
2. 或者通过event bus/callback机制转发

请根据项目现有的跨provider通信模式选择最合适的方案。

---

## 任务 2.7: Flutter — 在聊天消息列表中渲染执行建议和结果

**修改文件**: 聊天消息列表widget (找到渲染AI消息气泡的位置)

### 修改目标

在AI消息气泡下方, 根据条件渲染 `ExecutionSuggestionCard` 或 `ExecutionResultInline`。

### 精确修改

找到渲染assistant消息的widget(可能在 `chat_message_list.dart` 或类似文件中), 在每条assistant消息的widget之后, 添加:

```dart
// 在assistant消息widget后面
// 执行建议卡
if (isLastAssistantMessage && pendingExecutionSuggestion != null)
  Padding(
    padding: const EdgeInsets.only(top: DS.spacing8, left: DS.spacing12, right: DS.spacing12),
    child: ExecutionSuggestionCard(
      suggestion: pendingExecutionSuggestion,
      onAccept: () {
        ref.read(chatProvider.notifier).acceptExecutionSuggestion();
        // 触发handoff — 通过taskProvider
        final taskId = pendingExecutionSuggestion['task_id'] as String;
        ref.read(taskListProvider.notifier).handoffTaskToAi(taskId);
      },
      onDismiss: () => ref.read(chatProvider.notifier).dismissExecutionSuggestion(),
    ),
  ),
```

具体的集成位置需要你阅读聊天消息列表的实际代码来确定。核心原则: 建议卡跟在最后一条assistant消息后面, 不插入到消息列表的数据源中。

---

## 验收标准

### 后端验收

```bash
cd backend && python -m pytest tests/ -x -q
```

确认现有37个openclaw测试仍全部通过, 且新增代码不破坏任何现有测试。

手动验证:
```bash
# 确认新的UX模式能被正确选择
cd backend && python -c "
from app.orchestration.ux_envelope import _MODE_PROFILES
assert 'execution_delegate' in _MODE_PROFILES
print('UX mode OK:', _MODE_PROFILES['execution_delegate'].companion_frame)
"

# 确认新的Agent角色已注册
cd backend && python -c "
from app.core.agent_profiles import AgentRole
assert hasattr(AgentRole, 'EXECUTION_ASSISTANT')
print('Agent role OK')
"
```

### Flutter验收

```bash
cd mobile && flutter analyze --no-fatal-infos
```

### 功能验收 (人工)

1. [ ] 在聊天中输入包含"帮我查..."的消息, 如果有活跃任务上下文, 收到的AI回复metadata中应包含execution_suggestion
2. [ ] 建议卡在聊天流中正确渲染, 带入场动画
3. [ ] 点击"交给AI"能触发handoff流程
4. [ ] 点击"我自己来"卡片平滑消失
5. [ ] 执行完成后, 结果内联显示在聊天流中(如果能触发完整执行的话)
6. [ ] UX信封的execution_delegate模式在执行场景下正确激活
