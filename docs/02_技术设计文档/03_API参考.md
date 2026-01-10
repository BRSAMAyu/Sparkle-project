# API 参考文档 (API Reference)

## 1. WebSocket API

WebSocket 接口主要用于实时对话、状态同步和复杂交互。

### 1.1 连接
- **URL**: `ws://<host>/api/v1/ws/chat`
- **鉴权**: 需要在 Header 或 Query Param 中携带 JWT Token (具体取决于客户端实现，通常 Header `Authorization: Bearer <token>` 或 Cookie)。

### 1.2 客户端消息 (Client -> Server)

#### 发送消息 (Chat Message)
```json
{
  "type": "message",
  "message": "帮我制定一个学习计划",
  "session_id": "optional-uuid",
  "nickname": "User",
  "file_ids": ["file-uuid-1"],
  "include_references": true,
  "extra_context": {
    "current_page": "home"
  }
}
```

#### 动作反馈 (Action Feedback)
用于确认或取消 AI 生成的 UI 卡片（如任务列表、计划卡片）。
```json
{
  "type": "action_feedback",
  "action": "confirm", // 或 "dismiss"
  "widget_type": "task_list", // "task_list", "plan_card", "focus_card"
  "tool_result_id": "tool-call-uuid"
}
```

#### 知识点掌握度更新 (Node Mastery Update)
```json
{
  "type": "update_node_mastery",
  "payload": {
    "nodeId": "node-uuid",
    "mastery": 80, // 0-100
    "version": "2023-10-27T10:00:00Z" // ISO8601
  }
}
```

#### 专注完成 (Focus Completed)
```json
{
  "type": "focus_completed",
  "session_id": "session-uuid",
  "actual_duration": 25.0, // 分钟
  "tasks_completed": ["task-uuid-1", "task-uuid-2"]
}
```

### 1.3 服务端消息 (Server -> Client)

服务端返回的消息也是 JSON 格式，通过 `type` 字段区分。

| Type | 说明 | 关键字段 |
| :--- | :--- | :--- |
| `delta` | 文本流增量 | `delta`: string |
| `tool_call` | 工具调用 | `tool_call`: { `id`, `name`, `arguments` } |
| `tool_result` | 工具执行结果 | `tool_result`: { `tool_name`, `success`, `data`, `widget_type` } |
| `status_update` | 状态更新 | `status`: { `state`, `details` } |
| `citations` | 引用来源 | `citations`: [ { `title`, `url`, `content` } ] |
| `usage` | Token 消耗 | `usage`: { `total_tokens` } |
| `error` | 错误信息 | `error`: { `code`, `message` } |
| `action_status` | 动作确认回执 | `action_id`, `status` |
| `ack_update_node_mastery` | 掌握度更新确认 | `payload`: { `nodeId`, `status` } |

---

## 2. gRPC 服务 (Internal)

内部微服务通信使用 gRPC。

### 2.1 AgentServiceV2
定义在 `proto/agent_service_v2.proto`。

#### StreamChat
双向流式对话接口。
- **Request**: `ChatRequestV2` (user_id, message, session_id, active_tools)
- **Response**: `stream ChatResponseV2` (content, type, timestamp)

#### GetUserProfile
获取用户画像。
- **Request**: `ProfileRequestV2` (user_id)
- **Response**: `ProfileResponseV2` (nickname, level, avatar_url)

#### GetWeeklyReport
生成周报。
- **Request**: `WeeklyReportRequest` (user_id, week_id)
- **Response**: `WeeklyReport` (summary, tasks_completed)

### 2.2 GalaxyService
定义在 `proto/galaxy_service.proto`。

#### UpdateNodeMastery
更新知识节点掌握度。
- **Request**: `UpdateNodeMasteryRequest`
- **Response**: `UpdateNodeMasteryResponse`

#### SyncCollaborativeGalaxy
协作星图同步 (CRDT)。
- **Request**: `SyncCollaborativeGalaxyRequest` (partial_update)
- **Response**: `SyncCollaborativeGalaxyResponse` (server_update)

---

## 3. REST API (HTTP)

主要用于资源管理、文件上传和账户设置。

### 3.1 认证 (Auth)
- `POST /api/v1/auth/login`: 登录
- `POST /api/v1/auth/refresh`: 刷新 Token

### 3.2 文件 (Files)
- `POST /api/v1/files/upload`: 上传文件 (Multipart)
- `GET /api/v1/files/:id`: 获取文件详情

### 3.3 用户 (User)
- `GET /api/v1/user/profile`: 获取个人资料
- `PUT /api/v1/user/settings`: 更新设置

## 4. 错误码 (Error Codes)

| 代码 | 说明 | 处理建议 |
| :--- | :--- | :--- |
| `UNAUTHENTICATED` | 未登录或 Token 过期 | 跳转登录或刷新 Token |
| `PERMISSION_DENIED` | 无权访问 | 提示用户权限不足 |
| `INVALID_ARGUMENT` | 参数错误 | 检查输入格式 |
| `RESOURCE_EXHAUSTED` | 配额耗尽 | 提示用户充值或等待 |
| `UNAVAILABLE` | 服务暂不可用 | 稍后重试 (Exponential Backoff) |