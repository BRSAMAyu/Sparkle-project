# Cognitive Nexus: 深度实施方案 v2.0

## 1. 核心架构设计

为了实现 Sparkle 系统中星图 (Galaxy)、错题 (Error Book)、任务 (Task)、认知棱镜 (Cognitive Prism) 和对话 (Chat) 的深度融合，我们将构建 **Cognitive Nexus (认知枢纽)**。该架构基于 **Redis Streams 事件总线** 和 **Context Injection (上下文注入)** 双引擎驱动。

### 1.1 架构图示

```mermaid
graph TD
    subgraph "Infrastructure"
        Redis[Redis Streams (Event Bus)]
        VectorDB[PGVector (Memory Store)]
    end

    subgraph "Services (Backend)"
        Gateway[Go Gateway]
        GalaxySvc[Galaxy Service]
        ErrorSvc[Error Book Service]
        TaskSvc[Task Service]
        PrismSvc[Cognitive Service]
        ChatSvc[Agent/Chat Service]
        ContextMgr[Context Manager]
    end

    subgraph "Flow: Event Driven"
        ErrorSvc -->|Publish 'error.created'| Redis
        TaskSvc -->|Publish 'task.completed'| Redis
        GalaxySvc -->|Subscribe 'error.created'| Redis
        PrismSvc -->|Subscribe 'task.*'| Redis
    end

    subgraph "Flow: Context Injection"
        ChatSvc -->|Request Context| ContextMgr
        ContextMgr -->|Fetch Mastery| GalaxySvc
        ContextMgr -->|Fetch Patterns| PrismSvc
        ContextMgr -->|Fetch Pending| TaskSvc
        ContextMgr -->|Assemble| ChatSvc
    end
```

### 1.2 关键基础设施决策

*   **统一事件总线 (Unified Event Bus)**:
    *   放弃 Python 端现有的 `pika` (RabbitMQ) 实现，统一迁移至 **Redis Streams**。
    *   **理由**: 现有架构中 Go Gateway 已使用 Redis Streams，且 `docker-compose` 中未部署 RabbitMQ。统一技术栈可降低运维复杂度并提升跨语言通信效率。
    *   **Stream Key**: `sparkle_events` (所有服务共享同一个 Stream，通过消费者组区分处理)。

*   **上下文管理器 (Context Manager)**:
    *   新建 Python 核心组件 `backend/app/core/context_manager.py`。
    *   **职责**: 负责在 LLM 调用前，根据用户 ID 快速聚合跨模块的实时状态（星图掌握度、近期错题、行为模式、紧急任务），并生成结构化的 Prompt Context。

---

## 2. 深度整合链路

### 2.1 星图 (Galaxy) x 错题 (Error Book)

**目标**: 错题直接驱动知识掌握度的动态变化，实现"所错即所弱"。

*   **数据流**:
    1.  **事件触发**: 用户在 `Error Book` 录入错题，Error Service 发布 `error.created` 事件。
        *   Payload: `{ "error_id": "...", "related_concepts": ["limit", "derivative"], "severity": "high" }`
    2.  **状态同步**: Galaxy Service 订阅该事件。
        *   逻辑: 查找关联的 `KnowledgeNode`，应用惩罚算法（如 `mastery = mastery * 0.85`）。
        *   效果: 星图节点颜色变暗/出现裂纹视觉效果。
    3.  **复习闭环**: 当 Galaxy Service 检测到某节点掌握度回升（通过刷题或阅读）至 >90% 时，发布 `galaxy.node.mastered` 事件。
    4.  **智能归档**: Error Service 收到事件后，标记相关错题为 "建议归档" 状态。

### 2.2 任务 (Task) x 认知棱镜 (Cognitive Prism)

**目标**: 将行为数据实时转化为认知洞察，形成自我调节的反馈回路。

*   **数据流**:
    1.  **行为埋点**: 移动端/Gateway 捕获任务执行细节（专注时长、切换后台次数、提前/延后完成）。
    2.  **事件发布**: Task Service 发布 `task.session.completed`。
        *   Payload: `{ "task_id": "...", "planned_duration": 30, "actual_duration": 45, "interruptions": 3, "mood": "frustrated" }`
    3.  **模式分析**: Prism Service 消费事件，更新用户的 `BehaviorPattern`。
        *   分析逻辑: 若连续 3 次 "actual > planned * 1.5"，生成/更新 "规划乐观偏差 (Optimism Bias)" 模式标签。
    4.  **实时干预**: 下次创建任务时，Prism Service 检查 Draft Task，若命中 "Optimism Bias" 模式，Task Service 在 API 响应中注入 `nudge` 字段："检测到您通常低估耗时，建议将时长调整为 45 分钟"。

### 2.3 对话 (Chat) x 全量上下文 (Full Context)

**目标**: 让 AI 助手拥有用户的"完整记忆"和"当前状态感知"。

*   **实现机制**:
    1.  **拦截请求**: `AgentService.StreamChat` 接收到请求。
    2.  **上下文装配**: 调用 `ContextManager.get_composite_context(user_id)`。
        *   **Galaxy**: 获取最低掌握度的 Top 3 概念。
        *   **Error**: 获取今日新增错题摘要。
        *   **Prism**: 获取活跃的高置信度行为模式（如"考前焦虑"）。
        *   **Task**: 获取未来 24 小时 Deadline 的任务。
    3.  **Prompt 注入**:
        ```python
        system_prompt += f"""
        [User Context]
        - Weak Points: {galaxy_context}
        - Recent Errors: {error_context}
        - Behavioral Patterns: {prism_context}
        - Urgent Tasks: {task_context}
        Use this info to tailor your teaching style.
        """
        ```

---

## 3. 数据流转协议 (Data Protocol)

采用 **CloudEvents** 规范的 JSON 格式，通过 Redis Streams 传输。

### 3.1 事件信封结构

```json
{
  "specversion": "1.0",
  "type": "com.sparkle.error.created",  // 事件类型
  "source": "/service/error-book",      // 发源服务
  "subject": "error/12345",             // 实体标识
  "id": "evt-unique-id-xyz",
  "time": "2026-01-06T08:00:00Z",
  "datacontenttype": "application/json",
  "data": { ... }                       // 业务负载
}
```

### 3.2 核心事件定义

| 事件类型 (`type`) | 生产者 | 消费者 | `data` 关键字段 | 业务意图 |
| :--- | :--- | :--- | :--- | :--- |
| `error.created` | Error Svc | Galaxy Svc | `knowledge_node_ids`, `severity` | 降低关联知识点掌握度 |
| `galaxy.mastery_up` | Galaxy Svc | Error Svc | `node_id`, `new_level` | 触发错题归档建议 |
| `task.completed` | Task Svc | Prism Svc | `duration_delta`, `distractions` | 训练/更新行为模式 |
| `prism.pattern_detected` | Prism Svc | Chat Svc | `pattern_name`, `confidence` | 调整对话策略/语气 |
| `user.mood_updated` | Chat Svc | Prism Svc | `sentiment_score`, `trigger` | 记录情绪波动源 |

---

## 4. 核心文件路径与改动建议

### 4.1 基础设施层
*   **`backend/app/core/event_bus.py`**
    *   **改动**: 重写 `EventBus` 类，移除 `pika` 依赖，集成 `redis-py`。实现 `publish` (XADD) 和 `subscribe` (XREADGROUP) 方法。
*   **`backend/app/core/context_manager.py` (New)**
    *   **改动**: 新增 `ContextManager` 类，注入 GalaxyService, ErrorService, CognitiveService 等依赖，实现 `get_user_context_snapshot()` 方法。

### 4.2 业务服务层
*   **`backend/app/services/galaxy_service.py`**
    *   **改动**: 新增 `handle_error_created_event` 方法。实现消费逻辑，根据错题严重程度扣减 `KnowledgeNode` 的 `mastery_level`。
*   **`backend/app/services/cognitive_service.py`**
    *   **改动**: 增强 `analyze_task_session` 方法。当收到任务完成数据时，更新用户的 `BehaviorPattern` 记录。
*   **`backend/app/services/agent_service.py`** (或对应的 Chat 实现)
    *   **改动**: 在处理 Chat 请求前，集成 `ContextManager`。将获取的 Context 格式化并添加到 System Prompt 中。

### 4.3 协议层
*   **`proto/agent_service_v2.proto`**
    *   **改动**: 确认 `ChatRequest` 或 `UserProfile` 中预留了 `extra_context` 字段，确保 Gateway 可以透传必要的上下文标识（如果需要）。

---

## 5. 实施路线图

1.  **Foundation**: 改造 Python 端 `EventBus` 适配 Redis Streams，确保与 Go Gateway 互通。
2.  **Logic Link 1 (Error -> Galaxy)**: 实现错题录入对星图的即时反馈。这是最直观的整合点。
3.  **Logic Link 2 (Chat Context)**: 实现 `ContextManager` 并在 Chat 服务中接入，让 AI 立即变"聪明"。
4.  **Logic Link 3 (Task -> Prism)**: 完成行为数据的闭环分析，实现智能助推 (Nudge)。
