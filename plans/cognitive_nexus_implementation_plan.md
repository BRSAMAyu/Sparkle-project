# Cognitive Nexus: 全链路智能整合实施方案

**版本**: 1.0.0
**状态**: 待审批
**日期**: 2026-01-06

---

## 1. 执行摘要 (Executive Summary)

本项目旨在构建 **Cognitive Nexus (认知枢纽)**，打破 Sparkle 系统中星图(Galaxy)、错题(Error Book)、任务(Task)、对话(Chat)与认知棱镜(Prism)之间的信息孤岛。通过**事件驱动架构**和**统一上下文管理**，实现数据在各模块间的无缝流转，赋予 AI 引擎对用户学习状态的“全知视角”，从而提供更加个性化、连贯且智能的学习体验。

**核心价值**:
*   **一处更新，处处感知**: 错题录入立刻反映在星图中；任务拖延立刻被认知分析捕获。
*   **上下文感知的对话**: Chat 不再只是聊天，而是基于用户全量学习数据的智能顾问。
*   **闭环反馈机制**: 行为数据 -> 认知分析 -> 策略调整 -> 行为改变。

---

## 2. 总体架构设计

采用 **Event-Driven Architecture (EDA)** 为核心，辅以 **Context Injection** 机制。

### 2.1 逻辑视图

```mermaid
graph TD
    User((用户))
    
    subgraph "前端交互层 (Flutter)"
        GalaxyUI[星图视图]
        ErrorUI[错题视图]
        TaskUI[任务视图]
        ChatUI[对话视图]
    end
    
    subgraph "核心服务层 (Python)"
        GalaxySvc[Galaxy Service]
        ErrorSvc[Error Book Service]
        TaskSvc[Task Service]
        PrismSvc[Cognitive Service]
        ChatSvc[Chat Service]
    end
    
    subgraph "Cognitive Nexus (Integration)"
        EventBus[Event Bus (RabbitMQ)]
        ContextMgr[Context Manager]
    end
    
    User <--> GalaxyUI
    User <--> ErrorUI
    User <--> TaskUI
    User <--> ChatUI
    
    GalaxyUI <--> GalaxySvc
    ErrorUI <--> ErrorSvc
    TaskUI <--> TaskSvc
    ChatUI <--> ChatSvc
    
    GalaxySvc <--> EventBus
    ErrorSvc <--> EventBus
    TaskSvc <--> EventBus
    PrismSvc <--> EventBus
    
    ChatSvc ..> ContextMgr : Get User Context
    ContextMgr ..> GalaxySvc : Fetch Mastery
    ContextMgr ..> PrismSvc : Fetch Patterns
    ContextMgr ..> TaskSvc : Fetch Schedule
```

### 2.2 核心组件

1.  **Event Bus (事件总线)**: 基于 RabbitMQ，负责跨服务的异步消息传递。所有状态变更都必须广播为标准事件。
2.  **Context Manager (上下文管理器)**: 一个轻量级聚合器，负责在 Chat 或 Plan 生成时，快速拉取用户的 Galaxy（知识状态）、Prism（行为偏好）和 Task（日程安排）的实时快照。
3.  **Behavioral Interceptors (行为拦截器)**: 嵌入在 Task 执行流中的埋点模块，实时捕获用户的微观行为（如暂停、切换应用）并发送给 Prism。

---

## 3. 关键整合链路

### 3.1 知识与错误的深度融合 (Galaxy x Error Book)

**目标**: 让错题成为星图的“负反馈”，让星图成为错题的“导航图”。

**机制**:
*   **错题 -> 星图**:
    *   **录入即关联**: ErrorRecord 创建时必须关联 1-3 个 KnowledgeNode。
    *   **掌握度惩罚**: 录入新错题会触发 `node_mastery_updated` 事件，降低关联节点的 Mastery Score（例如 -15%）。
    *   **视觉反馈**: 星图节点出现“裂纹”或“红晕”特效，视觉化展示薄弱点。
*   **星图 -> 错题**:
    *   **复习入口**: 点击星图节点 -> 查看关联错题。
    *   **自动归档**: 当节点通过学习（如刷题、阅读）恢复到高 Mastery 时，提示用户将关联的旧错题归档。

### 3.2 任务与认知的反馈闭环 (Task x Prism)

**目标**: 将执行过程中的“行为数据”转化为“认知洞察”，并反哺到未来的任务规划中。

**机制**:
*   **数据采集**: Task Session 结束时，打包 `FocusLog` (专注时长、打断次数、情绪自评) 发送给 Prism。
*   **模式识别**: Prism 分析长短期数据，识别模式（如 "Friday Slump" - 周五效率低，或 "Overconfidence" - 实际耗时远超预估）。
*   **智能助推 (Nudge)**:
    *   **Pre-Task**: 创建任务时，若检测到高风险（如用户正在低谷期却创建了高难度任务），弹出建议：“根据历史数据，此刻攻克难关成功率较低，建议拆解任务。”
    *   **In-Task**: 实时检测分心，温和提醒。

### 3.3 对话的全知视角 (Chat x All Context)

**目标**: 让 Chat 能够像真人导师一样，了解用户的背景、状态和历史。

**机制**:
*   **Context Assembly**: 每次对话前，`ContextManager` 组装以下信息：
    *   **Knowledge**: "正在攻克 '微积分'，目前在 '极限' 章节卡住了。"
    *   **Schedule**: "今天还有 2 个待办任务，Deadline 是明晚。"
    *   **Persona**: "用户喜欢严厉的督促风格。"
*   **Prompt Injection**: 将上述 Context 注入 System Prompt，使 LLM 的回复具有高度的情境感知能力。

---

## 4. 数据流转协议 (Data Protocol)

### 4.1 事件定义 (CloudEvents)

所有事件均包含 `user_id`, `timestamp`, `producer` 等标准头。

| 事件 Topic | Payload 关键字段 | 消费者 | 作用 |
| :--- | :--- | :--- | :--- |
| `sparkle.error.created` | `error_id`, `linked_node_ids`, `tags` | Galaxy Service | 更新节点掌握度与视觉状态 |
| `sparkle.galaxy.mastery_up` | `node_id`, `new_mastery` | Error Service | 建议归档相关错题 |
| `sparkle.task.completed` | `actual_duration`, `interruptions` | Prism Service | 更新行为画像 |
| `sparkle.prism.pattern_new` | `pattern_type`, `description` | Chat Service | 调整对话策略 |

---

## 5. 核心实施步骤

### Phase 1: 基础设施构建 (Infrastructure)
1.  升级 `EventBus`，支持强类型事件定义与验证。
2.  实现 `ContextManager` 基础框架，提供 `get_user_context` 接口。

### Phase 2: Galaxy-Error 链路打通
1.  修改 `KnowledgeNode` 模型，增加 `error_stats` 字段。
2.  实现 Error Service 发布 `error.created` 事件。
3.  实现 Galaxy Service 消费事件并更新节点状态。
4.  Flutter 端 Galaxy 视图增加错题关联展示。

### Phase 3: Task-Prism 反馈闭环
1.  完善 Task 模块的埋点，确保能采集精准的行为数据。
2.  实现 Prism Service 的分析逻辑，能够消费 Task 事件并更新 `BehaviorPattern`。
3.  在 Task 创建页植入 `NudgeWidget`，展示 Prism 的建议。

### Phase 4: Chat 全量接入
1.  改造 `ChatService`，接入 `ContextManager`。
2.  优化 Prompt Template，使其能有效利用注入的 Context。
3.  端到端测试：验证 Chat 是否知道用户刚录入的错题或刚完成的任务。

---

## 6. 风险与对策

*   **风险**: 上下文过长导致 LLM 成本增加或遗忘。
    *   **对策**: `ContextManager` 实施严格的 Token 预算控制，对历史数据进行摘要（Summarization）而非全量透传。
*   **风险**: 事件循环依赖（Galaxy 更新 -> Error 更新 -> Galaxy 更新）。
    *   **对策**: 明确事件流向的单向性或使用 `trigger_id` 追踪调用链，防止死循环。
*   **风险**: 实时性要求过高导致系统延迟。
    *   **对策**: 采用异步处理，UI 层进行乐观更新（Optimistic UI），不阻塞用户操作。
