# Sparkle 功能模块详解

## 概述

Sparkle 项目由多个功能模块组成，采用Go + Python混合架构。本文档详细介绍各模块的功能、接口和实现细节，并说明Go Gateway和Python gRPC服务之间的职责划分。

## 模块列表

### 1. 用户管理模块 (User Service)

#### 功能概述
用户管理模块是Sparkle应用的基础模块，负责用户认证、注册、信息管理等功能。该模块处理用户的身份验证、个性化设置以及与用户相关的各种配置，为整个应用提供用户上下文支持。

#### 架构职责划分
- **Go Gateway处理**: JWT令牌验证、会话管理、基础用户信息CRUD
- **Python gRPC服务处理**: 用户业务逻辑、个性化设置计算、火焰等级更新

#### 核心功能
- 用户认证（登录/注册） - Go Gateway处理认证流程
- JWT令牌管理 - Go Gateway处理令牌签发和验证
- 用户信息管理 - Go处理基础信息，Python处理业务逻辑
- 个性化设置（火焰等级、偏好设置等） - Python计算，Go同步状态

#### API端点 (由Go Gateway提供)
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/refresh` - 令牌刷新
- `GET /api/v1/auth/me` - 获取当前用户信息
- `PUT /api/v1/auth/me` - 更新用户信息
- `POST /api/v1/auth/logout` - 用户登出

#### 实时通信
- WebSocket连接管理 - Go Gateway处理
- 用户状态同步 - Go ↔ Python通过gRPC同步

#### 数据模型
- **用户表 (users)**: 存储用户基本信息、认证信息和个性化设置
  - 基础信息：用户名、邮箱、昵称、头像
  - 个性化设置：火焰等级、火焰亮度、深度偏好、好奇心偏好
  - 时间安排：碎片时间/日程偏好
  - 账户状态：激活状态

### 2. 知识星图模块 (Galaxy Service)

#### 功能概述
知识星图模块是Sparkle应用的核心功能模块，负责管理用户的知识学习进度、提供可视化的知识结构以及实现基于艾宾浩斯遗忘曲线的学习辅助。该模块通过"点亮星星"的隐喻，将知识点转化为可视化星图，让用户能够直观地看到自己的学习进度和知识结构。

#### 核心功能
- 星图数据管理
- 知识点点亮（Spark）功能
- 语义搜索
- 节点管理
- 任务自动归类
- 遗忘曲线算法
- LLM拓展集成

#### 掌握度计算机制
- **基础计算公式**: 
  - 基础掌握度点数：5.0
  - 时间系数：`min(study_minutes / 30.0, 2.0)` (30分钟为标准，最多2倍)
  - 难度系数：`1 + (importance_level - 1) * 0.1` (重要性越高，增长越多)
  - 最大掌握度：100.0

- **掌握度等级**:
  - 未点亮 (<0): 未解锁
  - 微光 (1-29): 刚接触知识点
  - 闪耀 (30-79): 有一定掌握
  - 璀璨 (80-94): 掌握良好
  - 精通 (95-100): 完全掌握

#### API端点
- `GET /api/v1/galaxy/graph` - 获取星图数据
- `POST /api/v1/galaxy/node/{node_id}/spark` - 点亮知识点
- `POST /api/v1/galaxy/search` - 语义搜索
- `GET /api/v1/galaxy/review/suggestions` - 获取复习建议
- `POST /api/v1/galaxy/node/{node_id}/decay/pause` - 暂停遗忘衰减
- `GET /api/v1/galaxy/stats` - 获取统计信息
- `GET /api/v1/galaxy/events` - SSE事件流

#### 数据模型
- **knowledge_nodes**: 知识节点表
- **user_node_status**: 用户节点状态表
- **node_relations**: 节点关系表
- **study_records**: 学习记录表

### 3. 任务管理模块 (Task Service)

#### 功能概述
任务管理模块是Sparkle应用中负责任务全生命周期管理的核心模块。该模块支持任务的创建、更新、开始、完成、放弃等操作，并与知识星图、计划、推送等模块紧密集成，为用户提供结构化的学习任务管理功能。

#### 核心功能
- 任务CRUD操作
- 任务状态管理
- 任务分类管理
- 任务与知识点关联
- 时间跟踪

#### 任务类型
- `learning`: 学习任务
- `training`: 训练任务
- `error_fix`: 错误修复任务
- `reflection`: 反思任务
- `social`: 社交任务
- `planning`: 规划任务

#### 任务状态
- `PENDING`: 待处理
- `IN_PROGRESS`: 进行中
- `COMPLETED`: 已完成
- `ABANDONED`: 已放弃

#### API端点
- `GET /api/v1/tasks` - 获取任务列表
- `POST /api/v1/tasks` - 创建任务
- `GET /api/v1/tasks/{id}` - 获取任务详情
- `PUT /api/v1/tasks/{id}` - 更新任务
- `POST /api/v1/tasks/{id}/start` - 开始任务
- `POST /api/v1/tasks/{id}/complete` - 完成任务
- `POST /api/v1/tasks/{id}/abandon` - 放弃任务

#### 数据模型
- **tasks**: 任务表，包含标题、描述、类型、时间管理、难度评估、关联信息等

### 4. 计划管理模块 (Plan Service)

#### 功能概述
计划管理模块是Sparkle应用中负责学习计划管理的核心模块。该模块支持两种类型的计划：短期冲刺计划（Sprint Plan）和长期成长计划（Growth Plan），帮助用户设定学习目标、跟踪进度并生成相关任务。

#### 计划类型
- `sprint`: 冲刺计划 - 短期目标导向
- `growth`: 成长计划 - 长期发展导向

#### 核心功能
- 计划创建和管理
- 进度跟踪
- 任务关联
- 目标日期管理

#### API端点
- `GET /api/v1/plans` - 获取计划列表
- `POST /api/v1/plans` - 创建计划
- `GET /api/v1/plans/{id}` - 获取计划详情
- `PUT /api/v1/plans/{id}` - 更新计划
- `DELETE /api/v1/plans/{id}` - 删除计划

#### 数据模型
- **plans**: 计划表，包含名称、类型、目标日期、时间安排、进度等信息

### 5. AI对话模块 (LLM Service)

#### 功能概述
LLM服务模块是Sparkle应用的AI核心，负责处理与大语言模型的交互，包括对话、工具调用、内容生成等功能。该模块不仅支持常规的AI对话功能，还集成了演示模式、智能推送内容生成等特色功能，为整个应用提供智能化支持。

#### 架构职责划分
- **Go Gateway处理**: WebSocket连接管理、协议转换(JSON↔Protobuf)、消息路由
- **Python gRPC服务处理**: LLM交互、工具调用、Prompt工程、流式响应生成

#### 核心功能
- 实时流式对话 - Go处理WebSocket，Python处理AI推理
- 工具调用功能 - Python执行工具，Go转发结果
- 演示模式 - Python生成模拟响应，Go流式推送
- 内容生成功能 - Python生成内容，Go交付给客户端
- 推送内容生成 - Python生成推送内容，Go发送通知

#### 技术架构
- **Go Gateway层**: WebSocket服务器、gRPC客户端、协议转换
- **Python Agent层**: gRPC Server、LLM提供商抽象、工具调用系统
- **通信协议**: Protobuf定义接口，支持7种响应类型

#### 实时对话流程
```
Flutter App → WebSocket消息 → Go Gateway → JSON解析 → ChatRequest (Protobuf) →
gRPC StreamChat → Python Agent → LLM API/工具调用 → 流式响应 (Protobuf) →
JSON转换 → WebSocket推送 → Flutter App渲染 (打字机效果)
```

#### API端点
- **WebSocket端点**: `ws://localhost:8080/ws/chat` - 实时流式对话
- **HTTP端点** (由Go Gateway提供): 
  - `POST /api/v1/chat` - 标准聊天接口
  - `POST /api/v1/chat/confirm` - 工具调用确认接口

### 6. 智能推送模块 (Push Service)

#### 功能概述
智能推送模块是Sparkle应用中的个性化推送系统，基于多种策略为用户提供智能化、个性化的内容推送。该模块通过分析用户的学习行为、知识掌握情况、计划进度等因素，智能地推送相关内容，帮助用户保持学习动力和效率。

#### 推送策略
- **MemoryStrategy**: 记忆策略 - 基于艾宾浩斯遗忘曲线计算
- **SprintStrategy**: 冲刺策略 - 检测接近截止日期的冲刺计划
- **InactivityStrategy**: 不活跃策略 - 检测长时间未活跃的用户

#### 核心功能
- 推送策略管理
- 推送内容生成
- 频率控制
- 时区感知

#### API端点
- `GET /api/v1/notifications` - 获取通知列表
- `PUT /api/v1/notifications/{id}/read` - 标记通知为已读
- `GET /api/v1/push/preferences` - 获取推送偏好
- `PUT /api/v1/push/preferences` - 更新推送偏好

#### 数据模型
- **push_preferences**: 推送偏好表
- **push_histories**: 推送历史表
- **notifications**: 通知表

### 7. 社群功能模块 (Community Service)

#### 功能概述
社群功能模块为用户提供社交学习体验，包括好友系统、学习小队、冲刺群等功能。通过社群互动，用户可以与他人共同学习、互相激励、分享进度。

#### 核心功能
- 好友系统（基于共同课程/考试匹配）
- 学习小队（长期目标社群）
- 冲刺群（短期临时群组，带DDL倒计时）
- 群聊功能
- 打卡功能
- 火堆状态管理

#### 社群类型
- `squad`: 学习小队 - 长期目标导向
- `sprint`: 冲刺群 - 短期目标导向

#### API端点
- `POST /api/v1/community/groups` - 创建群组
- `GET /api/v1/community/groups` - 获取我的群组
- `GET /api/v1/community/groups/search` - 搜索公开群组
- `GET /api/v1/community/groups/{id}` - 群组详情
- `POST /api/v1/community/groups/{id}/join` - 加入群组
- `POST /api/v1/community/groups/{id}/leave` - 退出群组
- `GET /api/v1/community/groups/{id}/messages` - 获取群消息
- `POST /api/v1/community/groups/{id}/messages` - 发送群消息
- `POST /api/v1/community/checkin` - 群组打卡
- `GET /api/v1/community/groups/{id}/tasks` - 群任务列表
- `POST /api/v1/community/groups/{id}/tasks` - 创建群任务
- `POST /api/v1/community/tasks/{id}/claim` - 认领任务
- `GET /api/v1/community/groups/{id}/flame` - 火堆状态

#### 数据模型
- **friendships**: 好友关系表
- **groups**: 群组表
- **group_members**: 群成员表
- **group_messages**: 群消息表
- **group_tasks**: 群任务表
- **group_task_claims**: 任务认领表

## 模块间关系

### 混合架构职责划分
```
┌─────────────────────────────────────────────────────────────┐
│                     Flutter App (前端)                       │
├─────────────────────────────────────────────────────────────┤
│                 Go Gateway (流量入口层)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  用户认证    │  │ WebSocket   │  │  REST API路由       │  │
│  │  JWT验证    │  │  连接管理    │  │  基础数据CRUD       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                     gRPC通信 (Protobuf)                      │
├─────────────────────────────────────────────────────────────┤
│                Python Agent (AI智能引擎层)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  LLM交互    │  │  工具调用    │  │  复杂业务逻辑       │  │
│  │  Prompt工程 │  │  向量检索    │  │  数据分析计算       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 模块依赖关系
```
        +------------------+
        |   Go Gateway     |
        |  (流量入口层)     |
        +--------+---------+
                 │ WebSocket/HTTP
        +--------v---------+
        |   Python Agent   |
        |  (AI智能引擎)     |
        +--------+---------+
                 │ 业务逻辑调用
        +--------v---------+
        |   数据库层        |
        |  (PostgreSQL)    |
        +------------------+
```

### 集成点与通信路径
- **用户认证流**: Flutter → Go Gateway (JWT验证) → Python (业务逻辑)
- **实时对话流**: Flutter → WebSocket → Go Gateway → gRPC → Python → LLM
- **数据同步流**: Python (业务计算) → 数据库 → Go Gateway (状态同步) → Flutter
- **推送通知流**: Python (策略分析) → Go Gateway (消息推送) → Flutter
- **社群交互流**: Flutter → WebSocket → Go Gateway (实时消息) → 数据库

### 跨语言协作模式
1. **契约驱动**: Protobuf定义所有跨语言接口
2. **数据主权**: Python定义数据库Schema，Go通过SQLC消费数据
3. **错误传播**: Go ↔ Python通过gRPC状态码传递错误
4. **日志追踪**: Trace-ID贯穿全链路，统一日志格式

## 技术亮点

### 1. 混合架构优势
- **高性能IO处理**: Go处理WebSocket高并发连接，支持数千并发
- **复杂AI计算**: Python处理LLM交互、工具调用、向量检索等复杂逻辑
- **类型安全通信**: Protobuf确保Go↔Python跨语言通信类型安全
- **数据主权清晰**: Python定义Schema，Go消费数据，职责分离

### 2. 实时通信优化
- **WebSocket长连接**: Go Gateway管理连接生命周期
- **gRPC流式响应**: Python Agent实现真正的打字机效果
- **协议转换高效**: JSON↔Protobuf双向转换，支持7种响应类型
- **连接池管理**: Go管理gRPC连接池，Python处理业务逻辑

### 3. 模块化设计
- 各模块职责明确，低耦合
- API接口标准化
- 易于独立开发和测试
- 支持蓝绿部署和滚动升级

### 4. 可扩展性
- 插件式工具系统（Python Agent层）
- 可配置的推送策略（推送模块）
- 支持多AI提供商（LLM模块）
- 灵活的社群功能扩展（社群模块）

### 5. 智能化功能
- 基于遗忘曲线的学习算法（知识星图模块）
- 个性化推送系统（推送模块）
- 智能任务生成（AI对话模块）
- 自动知识拓展（知识星图模块）
- 实时流式对话（混合架构实现）
