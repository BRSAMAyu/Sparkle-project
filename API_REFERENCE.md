# Sparkle API 接口参考

## 概述

本文档提供了 Sparkle 应用的完整 API 接口参考，包括请求格式、响应格式和错误处理。

## 基本信息

- **Base URL**: `http://localhost:8000` (开发环境) 或 `https://api.sparkle-learning.com` (生产环境)
- **API Version**: `v1`
- **API Base Path**: `/api/v1`
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON

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
  "refresh_token": "string"
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

## AI对话

### 发送消息

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

### 流式对话

**请求**:
```http
POST /api/v1/chat/stream
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "session_id": "uuid (optional)",
  "content": "解释一下微积分的基本定理",
  "task_id": "uuid (optional)"
}
```

**响应** (SSE流):
```
data: {"type": "text", "content": "微积分基本定理建立了微分和积分之间的关系"}

data: {"type": "text", "content": "它包含两个部分"}

data: {"type": "tool_call", "name": "search_nodes", "arguments": {"query": "微积分基本定理"}}

data: {"type": "finish", "finish_reason": "stop"}
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

## 错误响应

所有 API 在发生错误时返回统一格式：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "detail": {}
  }
}
```

常见状态码：
- `200`: 成功
- `201`: 创建成功
- `400`: 请求参数错误
- `401`: 未认证
- `403`: 权限不足
- `404`: 资源不存在
- `422`: 数据验证失败
- `500`: 服务器内部错误

## 速率限制

API 实施速率限制以保护服务器：
- 普通请求：每分钟60次
- 认证请求：每分钟100次
- 搜索请求：每分钟30次
- 超出限制将返回 `429 Too Many Requests` 错误
