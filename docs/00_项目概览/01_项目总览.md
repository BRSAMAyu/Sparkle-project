# Sparkle项目总体框架与模块关系

## 项目概述

Sparkle（星火）是一个AI驱动的学习助手应用，专为大学生设计。项目采用Go + Python混合架构，前端使用Flutter框架。整体架构围绕"AI时间导师"概念，引导用户完成学习循环：对话→任务卡片→执行→反馈→冲刺计划。

## 技术架构 (混合架构)

### Go Gateway (流量入口层)
- **框架**: Gin + Gorilla WebSocket
- **职责**: 高并发IO处理、用户鉴权、WebSocket长连接管理
- **数据库访问**: SQLC (类型安全代码生成) + pgx驱动
- **认证**: JWT Token解析和验证
- **通信**: gRPC客户端连接Python Agent

### Python Agent (AI智能引擎)
- **框架**: FastAPI (遗留API) + gRPC Server
- **职责**: AI推理、复杂业务逻辑、工具调用、向量检索
- **数据库**: SQLAlchemy 2.0 (异步) + Alembic迁移
- **AI框架**: LangChain/LangGraph (Agent编排)
- **向量检索**: pgvector扩展

### 共享基础设施
- **数据库**: PostgreSQL 16+ with pgvector扩展
- **缓存**: Redis (会话、限流等)
- **消息协议**: Protobuf (`.proto`文件定义接口)
- **容器化**: Docker Compose统一开发环境

### 前端架构 (Flutter)
- **框架**: Flutter 3.x (Dart)
- **状态管理**: flutter_riverpod
- **路由管理**: go_router
- **网络请求**: http, Dio + Retrofit + WebSocket
- **本地存储**: shared_preferences, hive

### 前端架构 (Flutter)
- **框架**: Flutter 3.x (Dart)
- **状态管理**: flutter_riverpod
- **路由管理**: go_router
- **网络请求**: http, Dio + Retrofit
- **本地存储**: shared_preferences, hive

## 核心模块功能与关系

### 1. 用户管理模块 (User Service)
**功能**: 处理用户认证、注册、个人信息管理
- **后端**: UserService (基础实现)
- **前端**: AuthScreen, ProfileScreen
- **关系**: 为其他所有模块提供用户上下文

### 2. 知识星图模块 (Galaxy Service)
**功能**: 知识点管理、学习进度跟踪、语义搜索
- **后端**: GalaxyService, ExpansionService, DecayService
- **前端**: GalaxyScreen, 星图可视化组件
- **关系**: 与用户模块关联，使用AI模块生成内容，触发推送模块

### 3. 任务管理模块 (Task Service)
**功能**: 任务创建、执行、状态管理
- **后端**: TaskService (完整实现)
- **前端**: TaskListScreen, TaskDetailScreen, TaskExecutionScreen
- **关系**: 与用户、知识星图模块关联，可触发AI对话

### 4. 计划管理模块 (Plan Service)
**功能**: 冲刺计划、成长计划管理
- **后端**: PlanService (API定义完整，但实现有限)
- **前端**: SprintScreen, GrowthScreen (前端实现完整)
- **关系**: 与任务、用户模块关联，触发推送模块

### 5. AI对话模块 (LLM Service)
**功能**: 智能对话、工具调用、内容生成
- **后端**: LLMService, ToolExecutor, Orchestration
- **前端**: ChatScreen
- **关系**: 与所有模块交互，提供智能服务

### 6. 智能推送模块 (Push Service)
**功能**: 基于策略的个性化推送
- **后端**: PushService, 多种推送策略
- **前端**: 通知中心
- **关系**: 与用户、知识星图、计划模块关联

## 混合架构模块关系图

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

### 传统模块视图 (按功能划分)
```
         +----------------+
         |   Go Gateway   |
         |  (流量入口层)   |
         +-------+--------+
                 │ WebSocket/HTTP
         +-------v-------+
         |  Python Agent  |
         |  (AI智能引擎)   |
         +-------+-------+
                 │ 业务逻辑调用
         +-------v-------+
         |     数据库层    |
         |  (PostgreSQL)  |
         +---------------+
```

## 数据流向 (混合架构)

### 实时对话流 (核心路径)
```
Flutter App → WebSocket消息 → Go Gateway → JSON解析 → ChatRequest (Protobuf) →
gRPC StreamChat → Python Agent → LLM API/工具调用 → 流式响应 (Protobuf) →
JSON转换 → WebSocket推送 → Flutter App渲染 (打字机效果)
```

### REST API流
```
Flutter App → HTTP请求 → Go Gateway → 业务处理 → 数据库CRUD → HTTP响应
```

### 后台处理流
```
定时任务/事件 → Python Agent → 复杂业务逻辑 → 数据库更新 → Go Gateway推送通知
```

### 核心业务流
1. **用户认证流**: Go Gateway处理JWT → 用户信息查询 → 权限验证
2. **学习流**: 知识星图状态 → Python分析 → 任务生成 → Go同步状态
3. **AI交互流**: 用户输入 → Go转发 → Python推理 → 工具调用 → 结果返回
4. **推送流**: Python分析策略 → 生成内容 → Go推送通知
5. **社群流**: Go处理实时消息 → Python分析互动 → 火堆状态更新

## 关键业务流程

### 学习循环流程
1. 用户通过AI对话获取学习建议
2. 系统生成相关任务卡片
3. 用户执行任务并更新进度
4. 知识星图状态更新
5. 系统提供反馈和新计划

### 智能推送流程
1. 定时检查用户状态
2. 评估多种推送策略
3. 生成个性化推送内容
4. 发送通知到前端

## 项目状态总结 (Go重构完成)

### ✅ 已完成模块
- **用户模块**: Go处理认证，Python处理业务逻辑
- **知识星图模块**: Python处理向量检索，Go处理状态同步
- **任务模块**: Python处理任务生成，Go处理任务状态
- **AI对话模块**: Python处理LLM推理，Go处理WebSocket流式传输
- **推送模块**: Python分析推送策略，Go推送通知
- **社群模块**: Go处理实时群聊，Python分析社群互动

### ✅ Go后端重构完成
- **架构升级**: 从Python单体转为Go+Python混合架构
- **Go Gateway**: 基于Gin+WebSocket的高性能网关
- **Python gRPC服务**: 专注AI推理和复杂逻辑
- **实时通信**: WebSocket流式对话，支持打字机效果
- **协议驱动**: Protobuf定义接口，gRPC跨语言通信
- **Flutter适配**: WebSocket客户端适配完成

### 🎯 核心亮点
- **混合架构优势**: Go处理高并发IO，Python处理复杂AI逻辑
- **实时交互体验**: 真正的流式对话，打字机效果
- **类型安全通信**: Protobuf确保跨语言接口类型安全
- **数据主权分离**: Python定义Schema，Go消费数据，职责清晰

## 开发要点

### 后端关键实现
- **Go Gateway**: 异步WebSocket连接管理，JWT认证，gRPC客户端池
- **Python Agent**: gRPC Server实现，工具调用系统，向量检索(RAG)
- **数据库**: SQLC类型安全访问，SQLAlchemy异步ORM，pgvector向量搜索
- **协议**: Protobuf接口定义，JSON↔Protobuf双向转换
- **实时通信**: WebSocket长连接，gRPC流式响应，打字机效果

### 前端关键实现
- 星图可视化(Shader动画)
- 状态管理(Riverpod)
- 实时聊天界面
- 响应式UI设计

## 扩展性设计

### 架构扩展性
- **模块化设计**: Go Gateway和Python Agent可独立部署和扩展
- **水平扩展**: Go Gateway可水平扩展处理更多并发连接
- **服务发现**: 未来可集成服务发现机制支持多实例Python Agent
- **微服务演进**: 为未来进一步拆分为独立微服务打下基础

### 功能扩展性
- **工具系统**: 插件式工具调用框架，支持动态加载新工具
- **AI提供商**: 支持多AI提供商切换，统一的LLM抽象层
- **推送策略**: 可配置的推送策略系统，支持自定义策略
- **社群功能**: 模块化的社群系统，支持多种互动模式

### 协议驱动
- **契约优先**: Protobuf定义所有跨语言接口，确保向前兼容
- **版本控制**: 支持API版本管理，平滑升级
- **监控指标**: 内置健康检查和性能监控接口
