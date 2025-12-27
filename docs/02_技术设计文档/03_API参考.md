# Sparkle API 接口参考

## 概述

本文档提供了 Sparkle 应用的完整 API 接口参考，基于 Go + Python 混合架构。包括 HTTP REST API、WebSocket 实时接口以及 gRPC 内部接口。

## 架构说明

Sparkle 采用混合架构，API 由两部分组成：
1. **Go Gateway** (`:8080`): 处理 HTTP REST API、WebSocket 连接、用户认证和基础数据 CRUD
2. **Python gRPC 服务** (`:50051`): 处理 AI 推理、复杂业务逻辑、工具调用（通过 Go Gateway 代理）

## 基本信息

- **Go Gateway Base URL**: `http://localhost:8080` (开发环境) 或 `https://api.sparkle-learning.com` (生产环境)
- **WebSocket URL**: `ws://localhost:8080/ws/chat` (开发环境) 或 `wss://api.sparkle-learning.com/ws/chat` (生产环境)
- **API Version**: `v1`
- **API Base Path**: `/api/v1`
- **认证方式**: JWT Bearer Token (HTTP) / JWT Token (WebSocket)
- **数据格式**: JSON (HTTP/WebSocket), Protobuf (内部 gRPC)

## 认证

### 用户注册

**请求**:
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "string",
  "email": "string",
  "password": "string",
  "nickname": "string"
}
```

**响应**:
```json
{
  "user_id": "uuid",
  "username": "string",
  "email": "string",
  "nickname": "string",
  "access_token": "string",
  "refresh_token": "string"
}
```

### 用户登录

**请求**:
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}
```

**响应**:
```json
{
  "user_id": "uuid",
  "username": "string",
  "access_token": "string",
  "refresh_token": "string"
}
```

### 令牌刷新

**请求**:
```http
POST /api/v1/auth/refresh
Authorization: Bearer {refresh_token}
```

**响应**:
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600
}
```

### 获取当前用户信息

**请求**:
```http
GET /api/v1/auth/me
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "nickname": "string",
  "avatar_url": "string",
  "flame_level": 3,
  "flame_brightness": 0.75,
  "depth_preference": 0.6,
  "curiosity_preference": 0.8,
  "schedule_preferences": {
    "morning": true,
    "afternoon": false,
    "evening": true
  },
  "stats": {
    "total_study_minutes": 1200,
    "streak_days": 7,
    "completed_tasks": 35
  },
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

## 知识星图

### 获取星图数据

**请求**:
```http
GET /api/v1/galaxy/graph?star_domain=math&include_locked=false
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "nodes": [
    {
      "id": "uuid",
      "name": "微积分基础",
      "name_en": "Calculus Basics",
      "description": "微积分的基本概念",
      "subject_id": 1,
      "importance_level": 4,
      "keywords": ["导数", "积分", "极限"],
      "is_seed": true,
      "source_type": "seed",
      "source_task_id": "uuid",
      "position": {"x": 100, "y": 200},
      "user_status": {
        "mastery_score": 75.0,
        "total_study_minutes": 120,
        "study_count": 3,
        "is_unlocked": true,
        "is_favorite": false,
        "last_study_at": "2025-01-15T10:00:00Z",
        "next_review_at": "2025-01-18T10:00:00Z"
      }
    }
  ],
  "edges": [
    {
      "source_node_id": "uuid1",
      "target_node_id": "uuid2",
      "relation_type": "prerequisite",
      "strength": 0.8
    }
  ],
  "stats": {
    "total_nodes": 50,
    "unlocked_nodes": 25,
    "mastery_average": 65.5,
    "study_minutes_today": 45
  }
}
```

### 点亮知识点

**请求**:
```http
POST /api/v1/galaxy/node/{node_id}/spark
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "study_minutes": 30,
  "context": "完成相关任务后学习"
}
```

**响应**:
```json
{
  "node_id": "uuid",
  "mastery_score": 78.5,
  "mastery_delta": 3.5,
  "total_study_minutes": 150,
  "study_count": 4,
  "next_review_at": "2025-01-19T10:00:00Z",
  "animation_events": [
    {
      "type": "spark",
      "target": "node_uuid",
      "intensity": 0.8
    }
  ]
}
```

### 语义搜索

**请求**:
```http
POST /api/v1/galaxy/search
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "query": "微积分中的导数概念",
  "subject_id": 1,
  "limit": 10
}
```

**响应**:
```json
{
  "results": [
    {
      "node_id": "uuid",
      "name": "导数概念",
      "name_en": "Derivative Concept",
      "description": "导数的基本定义和性质",
      "subject_id": 1,
      "similarity": 0.95,
      "user_status": {
        "mastery_score": 60.0,
        "is_unlocked": true
      }
    }
  ]
}
```

### 获取复习建议

**请求**:
```http
GET /api/v1/galaxy/review/suggestions
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "suggestions": [
    {
      "node_id": "uuid",
      "name": "微积分基础",
      "mastery_score": 45.0,
      "importance_level": 5,
      "time_until_review": 86400,
      "decay_rate": 0.15
    }
  ]
}
```

## 任务管理

### 获取任务列表

**请求**:
```http
GET /api/v1/tasks?status=pending&page=1&limit=20&type=learning
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "total": 100,
  "page": 1,
  "limit": 20,
  "items": [
    {
      "id": "uuid",
      "title": "复习计算机网络第一章",
      "type": "learning",
      "tags": ["计算机网络", "期末考试"],
      "estimated_minutes": 30,
      "difficulty": 3,
      "energy_cost": 2,
      "guide_content": "建议先阅读教材第一章，然后完成课后习题",
      "status": "pending",
      "priority": 2,
      "due_date": "2025-01-20",
      "knowledge_node_id": "uuid",
      "auto_expand_enabled": true,
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z",
      "started_at": null,
      "completed_at": null,
      "actual_minutes": null,
      "user_note": null
    }
  ]
}
```

### 创建任务

**请求**:
```http
POST /api/v1/tasks
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "title": "完成线性代数习题",
  "type": "training",
  "tags": ["线性代数", "练习"],
  "estimated_minutes": 45,
  "difficulty": 4,
  "energy_cost": 3,
  "plan_id": "uuid",
  "knowledge_node_id": "uuid",
  "auto_expand_enabled": true
}
```

**响应**:
```json
{
  "id": "uuid",
  "title": "完成线性代数习题",
  "type": "training",
  "status": "pending",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

### 开始任务

**请求**:
```http
POST /api/v1/tasks/{task_id}/start
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "id": "uuid",
  "status": "in_progress",
  "started_at": "2025-01-15T10:00:00Z"
}
```

### 完成任务

**请求**:
```http
POST /api/v1/tasks/{task_id}/complete
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "actual_minutes": 25,
  "user_note": "完成得很顺利，掌握了主要概念"
}
```

**响应**:
```json
{
  "id": "uuid",
  "status": "completed",
  "completed_at": "2025-01-15T10:25:00Z",
  "actual_minutes": 25,
  "user_note": "完成得很顺利，掌握了主要概念"
}
```

## 计划管理

### 获取计划列表

**请求**:
```http
GET /api/v1/plans
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "计算机网络期末冲刺",
      "type": "sprint",
      "description": "为期3周的期末考试准备计划",
      "target_date": "2025-01-20",
      "daily_available_minutes": 90,
      "total_estimated_hours": 27.0,
      "mastery_level": 0.6,
      "progress": 0.45,
      "is_active": true,
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

### 创建计划

**请求**:
```http
POST /api/v1/plans
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "考研数学基础夯实",
  "type": "growth",
  "description": "系统复习考研数学基础知识",
  "daily_available_minutes": 120,
  "target_date": "2025-06-01"
}
```

**响应**:
```json
{
  "id": "uuid",
  "name": "考研数学基础夯实",
  "type": "growth",
  "is_active": true,
  "created_at": "2025-01-15T10:00:00Z"
}
```

## 实时对话 (WebSocket)

### WebSocket 连接建立

**连接URL**: `ws://localhost:8080/ws/chat`

**连接参数**:
```javascript
// 连接示例 (JavaScript)
const ws = new WebSocket('ws://localhost:8080/ws/chat');

// 连接建立后发送认证消息
ws.onopen = () => {
  ws.send(JSON.stringify({
    "type": "auth",
    "token": "JWT_ACCESS_TOKEN"
  }));
};
```

### 消息格式

#### 客户端 → 服务器
```json
{
  "type": "chat",
  "message_id": "uuid (客户端生成)",
  "session_id": "uuid (可选，新会话自动生成)",
  "content": "我想准备计算机网络的期末考试",
  "task_id": "uuid (可选)",
  "tools_enabled": true
}
```

#### 服务器 → 客户端 (流式响应事件)

服务器通过 WebSocket 发送 JSON 对象，每个对象包含 `type` 字段：

1. **`delta` (增量文本)**:
   ```json
   {"type": "delta", "delta": "内容片段"}
   ```

2. **`status_update` (状态更新)**:
   ```json
   {"type": "status_update", "status": {"state": "THINKING", "details": "正在分析问题..."}}
   ```
   *状态值*: `THINKING`, `GENERATING`, `EXECUTING_TOOL`, `SEARCHING`

3. **`tool_call` (工具调用)**:
   ```json
   {"type": "tool_call", "tool_call": {"name": "search_nodes", "arguments": "{...}"}}
   ```

4. **`full_text` (完整文本)**:
   ```json
   {"type": "full_text", "full_text": "AI 生成的最终完整回复"}
   ```

5. **`usage` (资源消耗)**:
   ```json
   {"type": "usage", "usage": {"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60}}
   ```

6. **`error` (错误报告)**:
   ```json
   {"type": "error", "error": {"code": "LLM_ERROR", "message": "服务暂时不可用", "retryable": true}}
   ```

7. **流结束 (finish_reason)**:
   包含 `finish_reason` 字段的消息表示流结束：
   ```json
   {"finish_reason": "stop"}
   ```

### HTTP 聊天接口 (备用)

**请求**:
```http
POST /api/v1/chat
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "session_id": "uuid (optional)",
  "content": "我想准备计算机网络的期末考试",
  "task_id": "uuid (optional)"
}
```

**响应**:
```json
{
  "message_id": "uuid",
  "session_id": "uuid",
  "role": "assistant",
  "content": "好的！我来帮你制定一个复习计划...",
  "actions": [
    {
      "type": "create_plan",
      "params": {
        "name": "计算机网络期末冲刺",
        "type": "sprint",
        "target_date": "2025-01-20"
      }
    }
  ],
  "tokens_used": 150,
  "model_name": "qwen-max"
}
```

### 工具调用确认

**请求**:
```http
POST /api/v1/chat/confirm
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "message_id": "uuid",
  "tool_name": "search_nodes",
  "confirmation": "allow",
  "custom_input": "可选的自定义输入"
}
```

**响应**:
```json
{
  "success": true,
  "result": {
    "type": "tool_result",
    "content": "找到了3个相关知识点"
  }
}
```

## 社群功能

### 获取我的群组

**请求**:
```http
GET /api/v1/community/groups
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "计算机网络期末冲刺群",
      "type": "sprint",
      "description": "一起准备计算机网络期末考试",
      "deadline": "2025-01-20",
      "sprint_goal": "掌握所有重点知识点",
      "member_count": 15,
      "max_members": 20,
      "role": "member",
      "joined_at": "2025-01-10T10:00:00Z",
      "visibility": "public"
    }
  ]
}
```

### 创建群组

**请求**:
```http
POST /api/v1/community/groups
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "数据结构学习小队",
  "type": "squad",
  "description": "每日刷题，共同进步",
  "visibility": "public",
  "max_members": 10
}
```

**响应**:
```json
{
  "id": "uuid",
  "name": "数据结构学习小队",
  "type": "squad",
  "created_by": "user_uuid",
  "role": "owner"
}
```

### 获取群组消息

**请求**:
```http
GET /api/v1/community/groups/{group_id}/messages?limit=50&before_id=uuid
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "sender_id": "user_uuid",
      "sender_nickname": "张三",
      "message_type": "text",
      "content": "今天完成了链表的练习题",
      "content_data": {},
      "created_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

### 群组打卡

**请求**:
```http
POST /api/v1/community/checkin
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "group_id": "uuid",
  "duration_minutes": 45,
  "message": "今天学习了图论算法"
}
```

**响应**:
```json
{
  "checkin_id": "uuid",
  "flame_gained": 25,
  "streak_days": 7,
  "total_flame_contribution": 150,
  "group_flame_boost": 2.5
}
```

## 通知与推送

### 获取通知列表

**请求**:
```http
GET /api/v1/notifications?read_status=all&page=1&limit=20
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "知识点复习提醒",
      "content": "您有一个重要知识点需要复习：微积分基础",
      "type": "reminder",
      "is_read": false,
      "created_at": "2025-01-15T10:00:00Z",
      "read_at": null,
      "data": {
        "node_id": "uuid",
        "mastery_score": 45.0,
        "importance_level": 5
      }
    }
  ]
}
```

### 标记通知为已读

**请求**:
```http
PUT /api/v1/notifications/{notification_id}/read
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "success": true,
  "read_at": "2025-01-15T10:00:00Z"
}
```

## 统计与分析

### 获取学习概览

**请求**:
```http
GET /api/v1/statistics/overview
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "flame_level": 3,
  "flame_brightness": 0.75,
  "total_tasks": 50,
  "completed_tasks": 35,
  "completion_rate": 0.7,
  "total_minutes": 1200,
  "streak_days": 7,
  "study_minutes_today": 45,
  "study_hours_this_week": 15.5,
  "mastery_average": 65.5,
  "nodes_unlocked": 25,
  "nodes_mastered": 8
}
```

## 速率限制与配额

### HTTP API 速率限制
- **普通请求**: 每分钟 60 次
- **认证请求**: 每分钟 100 次  
- **搜索请求**: 每分钟 30 次
- **超出限制**: 返回 `429 Too Many Requests` 错误

### WebSocket 连接限制
- **最大并发连接数**: 每个用户 3 个
- **消息频率限制**: 每秒 10 条消息
- **连接超时**: 无活动 5 分钟后断开

### AI 服务配额
- **免费用户**: 每天 100 条 AI 对话
- **高级用户**: 每天 1000 条 AI 对话
- **超出配额**: 返回 `QUOTA_EXCEEDED` 错误

## 错误响应

所有 API 在发生错误时返回统一格式：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "detail": {},
    "request_id": "请求唯一标识"
  }
}
```

常见错误码：
- `AUTH_REQUIRED`: 需要认证
- `INVALID_TOKEN`: 令牌无效
- `PERMISSION_DENIED`: 权限不足
- `RATE_LIMIT_EXCEEDED`: 超出速率限制
- `QUOTA_EXCEEDED`: 超出配额限制
- `RESOURCE_NOT_FOUND`: 资源不存在
- `VALIDATION_ERROR`: 数据验证失败
- `INTERNAL_SERVER_ERROR`: 服务器内部错误

常见 HTTP 状态码：
- `200`: 成功
- `201`: 创建成功
- `400`: 请求参数错误
- `401`: 未认证
- `403`: 权限不足
- `404`: 资源不存在
- `422`: 数据验证失败
- `429`: 超出速率限制
- `500`: 服务器内部错误
- `503`: 服务不可用 (AI 服务暂时不可用)

## WebSocket 状态码

WebSocket 连接可能返回以下关闭码：
- `1000`: 正常关闭
- `1001`: 端点离开
- `1008`: 策略违规
- `1011`: 服务器内部错误
- `4001`: 认证失败
- `4002`: 令牌过期
- `4003`: 超出配额
- `4004`: 并发连接数超限

## 健康检查

### 服务器健康状态
```http
GET /health
```

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:00:00Z",
  "services": {
    "go_gateway": "healthy",
    "python_agent": "healthy",
    "database": "healthy",
    "redis": "healthy"
  }
}
```

### 服务版本信息
```http
GET /version
```

**响应**:
```json
{
  "name": "sparkle-gateway",
  "version": "0.3.0",
  "commit": "40d7bb3ba95976ba9e71cd81088cc544f9df7026",
  "build_time": "2025-12-27T02:00:00Z"
}
```
