# Cognitive Nexus 架构设计方案

## 1. 核心理念：Cognitive Nexus (认知枢纽)

本项目将引入 **Cognitive Nexus** 概念，作为连接各个独立功能模块（星图 Galaxy、错题 Error、任务 Task、对话 Chat、认知 Prism）的中枢神经系统。它不是一个单一的庞大服务，而是一套**事件驱动的信息流转协议**和**统一上下文管理机制**。

其核心目标是打破数据孤岛，实现"一处更新，处处感知"。

### 1.1 架构层次

```mermaid
graph TD
    subgraph "用户交互层 (Frontend/Mobile)"
        GalaxyView[星图视图]
        ErrorBookView[错题本视图]
        TaskView[任务视图]
        ChatView[对话界面]
    end

    subgraph "业务逻辑层 (Backend Services)"
        GalaxyService[星图服务]
        ErrorService[错题服务]
        TaskService[任务服务]
        ChatService[对话服务]
        PrismService[认知棱镜服务]
    end

    subgraph "Cognitive Nexus (Integration Layer)"
        EventBus[统一事件总线 (RabbitMQ)]
        ContextManager[统一上下文管理器 (Context API)]
        Orchestrator[智能编排器 (LLM Agents)]
    end

    subgraph "数据存储层 (Persistence)"
        PG[PostgreSQL (结构化数据)]
        VectorDB[PGVector (语义向量)]
        GraphDB[Graph Relations (逻辑关系)]
    end

    GalaxyView --> GalaxyService
    ErrorBookView --> ErrorService
    TaskView --> TaskService
    ChatView --> ChatService

    GalaxyService <--> EventBus
    ErrorService <--> EventBus
    TaskService <--> EventBus
    ChatService <--> EventBus
    PrismService <--> EventBus

    ChatService --> ContextManager
    Orchestrator --> ContextManager
    ContextManager --> GalaxyService
    ContextManager --> ErrorService
    ContextManager --> TaskService
```

## 2. 关键整合链路详解

### 2.1 星图(Galaxy) 与 错题(Error Book) 的深度融合

**痛点**：目前错题本与知识点关联较弱，难以在复习知识点时自动关联错题，或在查看错题时定位知识盲区。

**解决方案**：
1.  **双向锚点 (Bidirectional Anchoring)**：
    *   **Error -> Galaxy**: 每一道错题录入时，强制或通过 AI 自动推断关联 1-3 个 `KnowledgeNode`。若知识点不存在，AI 建议创建“临时概念节点”。
    *   **Galaxy -> Error**: 星图节点的可视化（如颜色、光晕）将受关联错题数量和掌握度影响。错题多的节点呈现“高危红色”或“裂纹”特效。
2.  **事件联动**：
    *   当 `ErrorRecord` 被复习且掌握度提升 -> 触发 `ErrorMasteryUpdated` 事件 -> 订阅者更新关联 `KnowledgeNode` 的 `mastery_score` (加权平均)。
    *   当 `KnowledgeNode` 被标记为“已掌握” -> 触发 `NodeMasteryUpdated` 事件 -> 提示用户归档关联的低难度错题。

**数据流转**：
```json
// Event: error_record.created
{
  "event_type": "error_record_created",
  "error_id": "uuid...",
  "linked_node_ids": ["node_uuid_1", "node_uuid_2"],
  "cognitive_tags": ["calculation_error", "concept_confusion"]
}
// Consumer: GalaxyService 更新节点状态，可能降低 mastery
```

### 2.2 任务(Task) 与 认知棱镜(Cognitive Prism) 的实时反馈

**痛点**：任务执行过程中的行为数据（如拖延、频繁中断、提前完成）未能转化为对用户认知模式的洞察。

**解决方案**：
1.  **行为埋点 (Behavioral Instrumentation)**：
    *   在 Task 执行页面（番茄钟、倒计时）植入无感埋点。记录：暂停次数、专注时长、任务切换频率。
2.  **棱镜分析 (Prism Analysis)**：
    *   任务完成或放弃时，打包行为数据发送给 `PrismService`。
    *   AI 分析行为模式（例如：总是低估高难度任务的时间 -> 生成 "Planning Fallacy" 标签）。
3.  **反馈回路 (Feedback Loop)**：
    *   下次创建类似任务时，PrismService 注入 `UserContext`，TaskService 提示：“你上次做此类任务超时了 20%，建议增加预算时间。”

**数据流转**：
```json
// Event: task.completed
{
  "task_id": "...",
  "planned_time": 45,
  "actual_time": 65,
  "interruptions": 3,
  "user_sentiment": "exhausted"
}
// Consumer: PrismService 生成 CognitiveFragment -> 更新 BehaviorPattern
```

### 2.3 对话(Chat) 与 全量上下文 (Galaxy + Prism)

**痛点**：Chat 目前主要依赖短期对话历史，缺乏对用户长期知识状态（星图）和行为习惯（棱镜）的感知。

**解决方案**：
1.  **动态上下文注入 (Dynamic Context Injection)**：
    *   在构建 System Prompt 前，先通过 `ContextManager` 获取当前用户的“认知快照”。
    *   **快照内容**：
        *   **Galaxy**: 最近复习的薄弱点、正在攻克的知识子图。
        *   **Prism**: 用户的学习风格（如“视觉型学习者”）、当前的认知定式（如“容易焦虑”）。
        *   **Task**: 今日待办任务、即将到期的 Deadline。
2.  **意图识别增强**：
    *   LLM 能够识别“复习”意图，并直接调用 Galaxy 工具检索特定节点。
    *   LLM 能够识别“焦虑”情绪，并调用 Prism 数据进行安抚或建议休息。

**Prompt 模板示例**：
```text
System: 你是 Sparkle。
User Context:
- [Galaxy] 正在学习 "微积分/极限"，掌握度 45% (薄弱)。
- [Prism] 用户倾向于在下午 3 点感到疲劳 (Energy Dip)。
- [Task] 有一个 "完成数学作业" 任务延期中。

User: 我不想学了，好累。
Response (AI): (感知到 Energy Dip 和薄弱点) "看起来下午这个点确实容易犯困呢。考虑到'极限'这章确实比较难，要不我们先休息 15 分钟，或者换个轻松点的任务？"
```

## 3. 数据流转协议设计

### 3.1 统一事件模型 (Standardized Event Model)

所有跨模块通讯必须遵循统一的 CloudEvents 规范变体。

```python
class SparkleEvent:
    event_id: UUID
    event_type: str  # e.g., "galaxy.node.updated", "task.completed"
    producer: str    # e.g., "service.galaxy"
    timestamp: datetime
    user_id: UUID    # 关键：所有事件必须关联用户
    payload: Dict[str, Any]
    trace_id: str    # 用于分布式追踪
```

### 3.2 核心事件定义

| 领域 | 事件类型 | 触发时机 | 消费者 (示例) |
| :--- | :--- | :--- | :--- |
| **Galaxy** | `galaxy.node.mastery_change` | 节点掌握度变化 | ErrorService (调整复习间隔), ChatService (更新上下文) |
| **Error** | `error.record.created` | 新错题录入 | GalaxyService (节点变红), TaskService (建议生成复习任务) |
| **Task** | `task.session.completed` | 专注会话结束 | PrismService (行为分析), GalaxyService (累积学习时长) |
| **Prism** | `prism.pattern.detected` | 发现新行为定式 | ChatService (调整语气/策略), User (推送通知) |

## 4. 核心文件路径及建议改动点

### 4.1 Backend

1.  **`backend/app/core/event_bus.py`**
    *   **改动**: 增强 `EventBus`，支持强类型的事件注册和分发。增加 `ContextManager` 类，用于聚合各服务的状态快照。
    *   **新增**: `ContextManager` 用于在 Chat 时快速拉取 Galaxy/Task/Prism 的摘要数据。

2.  **`backend/app/services/chat_service.py`**
    *   **改动**: 在 `stream_chat` 方法中，插入 `ContextManager.get_user_context(user_id)` 调用。
    *   **改动**: 修改 `SYSTEM_PROMPT` 构建逻辑，动态插入上下文信息。

3.  **`backend/app/models/galaxy.py` & `backend/app/services/galaxy_service.py`**
    *   **改动**: 在 `KnowledgeNode` 模型中增加 `error_count` (错题数) 和 `associated_error_ids` (冗余存储或通过关联表)。
    *   **改动**: 订阅 `error.record.created` 事件，自动更新节点状态。

4.  **`backend/app/services/task_service.py`**
    *   **改动**: 在任务完成逻辑中，发布 `task.completed` 事件，包含详细的行为指标（耗时、中断等）。

5.  **`backend/app/services/cognitive_service.py` (即 Prism)**
    *   **改动**: 实现 `BehaviorAnalyzer`，消费 `task.*` 事件，更新 `BehaviorPattern`。

### 4.2 Mobile (Flutter)

1.  **`mobile/lib/features/galaxy/presentation/widgets/galaxy/node_preview_card.dart`**
    *   **改动**: UI 展示关联的错题数量。点击可跳转到筛选了该知识点的错题本视图。

2.  **`mobile/lib/features/chat/presentation/providers/chat_provider.dart`**
    *   **改动**: 发送消息时，允许携带当前的 client-side context (如当前所在的页面、选中的知识点)，作为短期上下文补充。

## 5. 实施步骤规划

1.  **Phase 1: 基础设施 (Infrastructure)**
    *   完善 `EventBus`，定义标准事件 Schema。
    *   建立 `ContextManager` 接口。

2.  **Phase 2: 核心链路打通 (Core Integration)**
    *   实现 **Galaxy <-> Error** 的双向关联和事件同步。
    *   实现 **Chat** 读取 **Galaxy** 掌握度数据的能力。

3.  **Phase 3: 认知闭环 (Cognitive Loop)**
    *   实现 **Task -> Prism** 的数据投递。
    *   实现 **Prism -> Chat/Task** 的策略反馈（智能建议）。

4.  **Phase 4: 全局优化 (Optimization)**
    *   调整 Prompt 策略，防止上下文过长 (Context Window Optimization)。
    *   端到端测试信息流转的实时性和准确性。
