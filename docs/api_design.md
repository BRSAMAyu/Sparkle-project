# Sparkle API 设计文档

## 概述

本文档描述了 Sparkle 后端 API 的设计规范和接口定义。

## 基本信息

- **Base URL**: `http://localhost:8000`
- **API Version**: `v1`
- **API Base Path**: `/api/v1`
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON

## 认证流程

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

## 任务管理

### 获取任务列表

**请求**:
```http
GET /api/v1/tasks?status=pending&page=1&limit=20
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
      "status": "pending",
      "created_at": "2025-01-15T10:00:00Z"
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
  "title": "string",
  "type": "learning",
  "tags": ["string"],
  "estimated_minutes": 30,
  "difficulty": 3,
  "plan_id": "uuid (optional)"
}
```

### 开始任务

**请求**:
```http
POST /api/v1/tasks/{task_id}/start
Authorization: Bearer {access_token}
```

### 完成任务

**请求**:
```http
POST /api/v1/tasks/{task_id}/complete
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "actual_minutes": 25,
  "user_note": "完成得很顺利"
}
```

## 对话接口

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
  ]
}
```

## 计划管理

### 创建计划

**请求**:
```http
POST /api/v1/plans
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "计算机网络期末冲刺",
  "type": "sprint",
  "target_date": "2025-01-20",
  "daily_available_minutes": 90
}
```

### AI 生成计划任务

**请求**:
```http
POST /api/v1/plans/{plan_id}/generate-tasks
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "context": "计算机网络课程，共5章，考试范围前3章"
}
```

## 统计数据

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
  "total_minutes": 1200,
  "streak_days": 7
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

## 待实现功能

- [ ] WebSocket 实时通知
- [ ] 文件上传接口
- [ ] 数据导出接口
- [ ] 第三方登录（微信、QQ）
