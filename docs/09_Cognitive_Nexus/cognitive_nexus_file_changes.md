# Cognitive Nexus 实施方案：核心文件变更清单

## 1. 后端 (Backend Python)

### 基础架构层
*   **`backend/app/core/event_bus.py`**:
    *   [ ] 新增 `SparkleEvent` 数据类，遵循 CloudEvents 规范。
    *   [ ] 扩展 `publish` 方法，支持 `user_id` 和 `timestamp` 的自动注入。
*   **`backend/app/core/context_manager.py` (New)**:
    *   [ ] 创建新文件，定义 `ContextManager` 类。
    *   [ ] 实现 `get_user_context(user_id)` 方法，并行调用 Galaxy/Task/Prism 服务获取摘要。

### 业务模型层
*   **`backend/app/models/galaxy.py`**:
    *   [ ] `KnowledgeNode`: 新增 `error_count`, `last_error_at` 字段。
    *   [ ] 创建 Alembic 迁移脚本。
*   **`backend/app/models/cognitive.py`**:
    *   [ ] `BehaviorPattern`: 新增 `context_domains`, `trigger_conditions` 字段。
*   **`backend/app/models/chat.py`**:
    *   [ ] `ChatMessage`: 新增 `context_snapshot` JSONB 字段。

### 业务服务层
*   **`backend/app/services/galaxy_service.py`**:
    *   [ ] 新增监听 `sparkle.error.record.created` 事件，实现节点红点逻辑。
*   **`backend/app/services/error_book_service.py`**:
    *   [ ] 创建错题时，触发 `sparkle.error.record.created` 事件。
    *   [ ] 实现 `get_linked_nodes(error_id)` 方法。
*   **`backend/app/services/task_service.py`**:
    *   [ ] 任务完成时，触发 `sparkle.task.completed` 事件。
    *   [ ] 在创建任务前，调用 `PrismService` 获取行为建议（助推）。
*   **`backend/app/services/chat_service.py`**:
    *   [ ] 在 `stream_chat` 中集成 `ContextManager`。
    *   [ ] 优化 System Prompt 模板，支持动态插入 Context。

### 接口层
*   **`proto/agent_service_v2.proto`**:
    *   [ ] 定义新的 gRPC 消息类型，用于跨服务查询（如 Go Gateway 查询 Galaxy 状态）。

## 2. 后端 (Gateway Go)

*   **`backend/gateway/internal/handler/websocket.go`**:
    *   [ ] 增强 WebSocket 协议，支持前端推送 Client Context (如 `ScreenState`)。
*   **`backend/gateway/internal/event/consumer.go`**:
    *   [ ] 订阅 RabbitMQ 事件，将关键通知（如 Prism 助推）通过 WS 推送给客户端。

## 3. 移动端 (Flutter)

### 状态管理层
*   **`mobile/lib/presentation/providers/chat_provider.dart`**:
    *   [ ] 增加 `ClientContext` 状态，记录当前用户所在的页面和选中的对象。
    *   [ ] 发送消息时附带上下文信息。
*   **`mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart`**:
    *   [ ] 监听 `ErrorAdded` 通知，实时刷新星图节点状态。

### UI 组件层
*   **`mobile/lib/features/galaxy/presentation/widgets/galaxy/node_preview_card.dart`**:
    *   [ ] 增加错题关联指示器（Error Badge）。
*   **`mobile/lib/features/task/presentation/screens/task_create_screen.dart`**:
    *   [ ] 增加 Prism 助推提示框（Nudge Widget）。

## 4. 迁移与兼容性

*   **Alembic Migrations**: 必须为所有模型变更编写数据库迁移脚本。
*   **Event Versioning**: 事件 Payload 包含版本号，确保消费者兼容旧版本事件。
