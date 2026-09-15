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

### 2.1 AgentService
定义在 `proto/agent_service.proto`。

#### StreamChat
双向流式对话接口。
- **Request**: `ChatRequest` (user_id, session_id, input, active_tools, chat_mode, config, file_ids)
- **Response**: `stream ChatResponse` (delta/tool_call/status_update/full_text/usage/citations/tool_result, finish_reason, timestamp)

#### GetUserProfile
获取用户画像。
- **Request**: `ProfileRequest` (user_id)
- **Response**: `UserProfile` (nickname, level, avatar_url, preferences, extra_context)

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

### 2.3 ErrorBookService
定义在 `proto/error_book.proto`，由 Python gRPC server 注册。

#### CreateError / ListErrors / SubmitReview
错题创建、查询、AI 分析触发和复习表现回写。

### 2.4 STTService
定义在 `proto/stt_service.proto`，由 Python gRPC server 注册。

#### TranscribeAudio / EnhanceTranscript / StreamSpeechToText
语音文件转写、转写文本增强，以及实时双向流式转写。

### 2.5 InferenceService
定义在 `proto/sparkle/inference/v1/inference.proto`，由 Python gRPC server 注册。

#### RunInference
统一 LLM/信号推理入口，当前由 `LLMDispatcher` 承载。

### 2.6 CommunityService
定义在 `proto/community_service.proto`，但已标记为 `deprecated`。生产社区能力通过 REST API 与 Go gateway CQRS 路径提供，不作为 live Python gRPC 服务注册。

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

### 3.4 成就 (Achievements)
- `GET /api/v1/achievements`: 获取成就列表
- `GET /api/v1/achievements/{achievement_id}`: 获取成就详情（canonical）
- `POST /api/v1/achievements/{achievement_id}/share`: 生成 PNG 分享卡（canonical）
- `POST /api/v1/achievements/{achievement_id}/pin?pinned=true|false`: 置顶/取消置顶（canonical）
- `GET /api/v1/achievements/close-to-unlock`: 获取接近解锁的成就
- `POST /api/v1/achievements/events/process`: 内部接口，需 `X-Internal-Token`

兼容旧路由仍保留一阶段：
- `GET /api/v1/achievements/achievements/{achievement_id}`
- `POST /api/v1/achievements/achievements/{achievement_id}/share`
- `POST /api/v1/achievements/achievements/{achievement_id}/pin`

## 4. 错误码 (Error Codes)

| 代码 | 说明 | 处理建议 |
| :--- | :--- | :--- |
| `UNAUTHENTICATED` | 未登录或 Token 过期 | 跳转登录或刷新 Token |
| `PERMISSION_DENIED` | 无权访问 | 提示用户权限不足 |
| `INVALID_ARGUMENT` | 参数错误 | 检查输入格式 |
| `RESOURCE_EXHAUSTED` | 配额耗尽 | 提示用户充值或等待 |
| `UNAVAILABLE` | 服务暂不可用 | 稍后重试 (Exponential Backoff) |
