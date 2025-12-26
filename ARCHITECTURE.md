# Sparkle 项目技术架构

## 概述

Sparkle 是一款面向大学生的 AI 学习助手应用，采用前后端分离的微服务架构。项目围绕 AI 驱动的学习助手概念，构建了一个完整的学习生态系统。

## 整体架构

```
┌─────────────────┐       WebSocket (ws://)      ┌─────────────────┐
│  Flutter App    │ ◄───────────────────────────►│  Go Gateway     │
│  (Mobile)       │     HTTP/HTTPS (REST API)    │  :8080          │
└─────────────────┘                               └────────┬────────┘
                                                           │ gRPC
                                                           │ (StreamChat)
                                                           │
                                                  ┌────────▼────────┐
                                                  │ Python Agent    │
                                                  │ gRPC Server     │
                                                  │ :50051          │
                                                  └────────┬────────┘
                                                           │
                                        ┌──────────────────┼──────────────────┐
                                        │                  │                  │
                                        ▼                  ▼                  ▼
                               ┌────────────┐      ┌────────────┐      ┌──────────────┐
                               │ PostgreSQL │      │ LLM Service│      │ Vector Store │
                               │ (pgvector) │      │ (Qwen/     │      │ (pgvector)   │
                               │ :5432      │      │ DeepSeek)  │      │              │
                               └────────────┘      └────────────┘      └──────────────┘
```

**架构说明**:
1. **Go Gateway**: 流量入口，处理WebSocket长连接和HTTP REST API
2. **Python Agent**: AI智能引擎，通过gRPC提供AI推理服务
3. **数据库**: PostgreSQL with pgvector，Go和Python共享同一数据源
4. **通信协议**: WebSocket用于实时对话，HTTP用于其他API，gRPC用于跨语言服务调用

## 后端架构 (混合架构)

### Go Gateway (`backend/gateway`)
**职责**: 高并发IO处理、用户鉴权、基础数据CRUD、实时通信桥接

**技术栈**:
- **框架**: Gin (HTTP/WebSocket) + Gorilla WebSocket
- **数据库访问**: SQLC (类型安全SQL代码生成) + pgx驱动
- **通信**: gRPC客户端 (连接Python Agent)
- **认证**: JWT Token解析和验证
- **并发**: Goroutine处理数千并发WebSocket连接

**核心功能**:
- WebSocket长连接管理，支持流式对话
- 用户认证和会话管理
- 基础数据CRUD (users, chat_history等表)
- 协议转换: JSON ↔ Protobuf
- 请求路由到Python gRPC服务

### Python Agent Engine (`backend/app`)
**职责**: AI推理、复杂业务逻辑、工具调用、向量检索

**技术栈**:
- **框架**: FastAPI (遗留API) + gRPC Server
- **数据库**: SQLAlchemy 2.0 (异步) + Alembic迁移
- **AI框架**: LangChain/LangGraph (Agent编排)
- **向量检索**: pgvector扩展
- **任务调度**: APScheduler

**核心功能**:
- gRPC AgentService实现 (`StreamChat`等)
- LLM交互和Prompt工程
- 工具调用系统 (知识查询、任务生成等)
- 向量语义搜索 (RAG)
- 复杂业务逻辑处理

### 共享基础设施
- **数据库**: PostgreSQL 16+ with pgvector扩展
- **缓存**: Redis (会话、限流等)
- **消息协议**: Protobuf (`.proto`文件定义接口)
- **容器化**: Docker Compose统一开发环境

### 核心服务层
- **认证服务**: Go Gateway处理JWT，Python处理业务逻辑
- **聊天服务**: Go处理WebSocket连接，Python处理AI推理
- **知识星图**: Python处理向量检索和知识拓展，Go处理状态同步
- **任务服务**: Python处理任务生成逻辑，Go处理任务状态更新
- **推送服务**: Python处理推送策略，Go处理消息推送
- **社群服务**: Go处理实时群聊，Python处理社群分析

### 项目结构
```
backend/
├── gateway/                          # Go Gateway服务
│   ├── cmd/
│   │   └── server/
│   │       └── main.go              # Go Gateway入口点
│   ├── internal/
│   │   ├── handler/
│   │   │   └── chat_orchestrator.go # WebSocket处理器，协议转换
│   │   ├── agent/
│   │   │   └── client.go            # gRPC客户端，连接Python Agent
│   │   ├── db/
│   │   │   ├── query.sql            # SQLC查询定义
│   │   │   ├── schema.sql           # 数据库Schema (从Python同步)
│   │   │   └── db.go                # 数据库连接和查询
│   │   ├── service/
│   │   │   ├── quota.go             # 配额服务
│   │   │   ├── chat_history.go      # 聊天历史服务
│   │   │   └── semantic_cache.go    # 语义缓存服务
│   │   ├── config/
│   │   │   └── config.go            # 配置管理
│   │   └── infra/
│   │       └── redis/
│   │           └── client.go        # Redis客户端
│   ├── go.mod                       # Go模块定义
│   ├── go.sum                       # 依赖校验
│   ├── sqlc.yaml                    # SQLC配置
│   └── bin/
│       └── gateway                  # 编译后的可执行文件
├── app/                             # Python gRPC服务 (原FastAPI应用)
│   ├── main.py                      # FastAPI入口点 (遗留API)
│   ├── grpc_server.py               # gRPC服务器入口点
│   ├── config.py                    # 配置管理
│   ├── services/
│   │   ├── agent_grpc_service.py    # gRPC AgentService实现
│   │   ├── llm_service.py           # LLM服务
│   │   ├── galaxy_service.py        # 知识星图服务
│   │   ├── task_service.py          # 任务服务
│   │   └── ...                      # 其他服务
│   ├── models/                      # 数据模型
│   ├── core/                        # 核心模块
│   ├── tools/                       # AI工具系统
│   └── orchestration/               # 响应编排
├── alembic/                         # 数据库迁移 (Python侧管理)
├── logs/                            # 日志目录
├── seed_data/                       # 种子数据
├── grpc_server.py                   # gRPC服务器启动脚本
├── test_websocket_client.py         # WebSocket集成测试
└── requirements.txt                 # Python依赖
```

## 前端架构

### 技术栈
- **框架**: Flutter 3.x (Dart)
- **状态管理**: flutter_riverpod
- **路由管理**: go_router
- **网络请求**: http, Dio + Retrofit
- **本地存储**: shared_preferences, hive

### 项目结构
```
mobile/
├── lib/
│   ├── main.dart                         # 应用入口点
│   ├── app/
│   │   ├── app.dart                      # 应用根组件
│   │   └── routes.dart                   # 路由配置
│   ├── presentation/
│   │   ├── screens/
│   │   │   ├── galaxy_screen.dart        # 知识星图界面
│   │   │   ├── chat_screen.dart          # 聊天界面
│   │   │   ├── task_list_screen.dart     # 任务列表界面
│   │   │   ├── task_detail_screen.dart   # 任务详情界面
│   │   │   ├── community/
│   │   │   │   ├── group_list_screen.dart    # 群组列表界面
│   │   │   │   ├── group_chat_screen.dart    # 群聊界面
│   │   │   │   ├── create_group_screen.dart  # 创建群组界面
│   │   │   │   └── ...                       # 其他社群界面
│   │   │   └── ...                       # 其他界面
│   │   ├── providers/
│   │   │   ├── galaxy_provider.dart      # 知识星图状态管理
│   │   │   ├── chat_provider.dart        # 聊天状态管理
│   │   │   ├── task_provider.dart        # 任务状态管理
│   │   │   ├── community_provider.dart   # 社群状态管理
│   │   │   └── ...                       # 其他状态管理
│   │   └── widgets/
│   │       ├── galaxy/
│   │       │   ├── flame_core.dart       # 火焰核心组件，使用 Fragment Shader
│   │       │   ├── star_map_painter.dart # 星图绘制
│   │       │   ├── energy_particle.dart   # 能量粒子动画
│   │       │   └── star_success_animation.dart # 点亮成功动画
│   │       ├── community/
│   │       │   ├── flame_avatar.dart     # 带火苗效果的头像
│   │       │   ├── bonfire_animation.dart # 火堆动画
│   │       │   ├── message_bubble.dart   # 群消息气泡
│   │       │   └── ...                   # 其他社群组件
│   │       └── ...                       # 其他组件
│   ├── data/
│   │   ├── repositories/
│   │   │   ├── galaxy_repository.dart    # 知识星图数据仓库
│   │   │   ├── chat_repository.dart      # 聊天数据仓库
│   │   │   ├── task_repository.dart      # 任务数据仓库
│   │   │   ├── community_repository.dart # 社群数据仓库
│   │   │   └── ...                       # 其他数据仓库
│   │   ├── models/
│   │   │   ├── galaxy_model.dart         # 知识星图数据模型
│   │   │   ├── chat_message_model.dart   # 聊天消息数据模型
│   │   │   ├── task_model.dart           # 任务数据模型
│   │   │   ├── community_model.dart      # 社群数据模型
│   │   │   └── ...                       # 其他数据模型
│   │   └── datasources/
│   │       ├── api_client.dart           # API 客户端
│   │       └── local_storage.dart        # 本地存储
│   └── core/
│       ├── services/
│       ├── utils/
│       ├── design/
│       └── constants/
└── shaders/
    └── core_flame.frag                   # 火焰着色器，GLSL 实现
```

## 核心模块关系

### 模块依赖关系
```
        +------------------+
        |   用户模块       |
        |  (UserService)   |
        +--------+---------+
                 |
        +--------v---------+
        |   知识星图模块    |
        | (GalaxyService)  |
        +--------+---------+
                 |
        +--------v---------+
        |   任务模块       |
        | (TaskService)    |
        +--------+---------+
                 |
        +--------v---------+
        |   计划模块       |
        | (PlanService)    |
        +--------+---------+
                 |
        +--------v---------+
        |   AI对话模块     |
        | (LLMService)     |
        +--------+---------+
                 |
        +--------v---------+
        |   推送模块       |
        | (PushService)    |
        +--------+---------+
                 |
        +--------v---------+
        |   社群模块       |
        |(CommunityService)|
        +------------------+
```

## 数据流向

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

### 社群互动流程
1. 用户创建或加入群组
2. 群内打卡或分享进度
3. 火堆状态更新
4. 通过AI工具增强互动

## 技术亮点

### 架构亮点
- **混合架构优势**: Go处理高并发IO，Python处理复杂AI逻辑，各取所长
- **协议驱动开发**: Protobuf严格定义接口，确保跨语言通信类型安全
- **数据主权分离**: Python定义Schema，Go消费数据，职责清晰
- **实时通信优化**: WebSocket长连接 + gRPC流式响应，实现真正打字机效果

### Go Gateway亮点
- **高性能并发**: Goroutine轻量级线程，支持数千并发WebSocket连接
- **零反射数据库访问**: SQLC生成类型安全代码，避免ORM性能开销
- **优雅错误处理**: 多层错误传播和恢复机制
- **生产级特性**: 结构化日志、健康检查、优雅关闭

### Python Agent亮点
- **AI能力集成**: LangChain/LangGraph支持复杂Agent编排
- **向量检索**: pgvector实现高效语义搜索和RAG
- **工具生态系统**: 可扩展的工具调用框架
- **遗忘曲线算法**: 基于艾宾浩斯曲线的智能复习提醒

### 前端亮点
- **实时交互**: WebSocket支持流式对话和状态更新
- **可视化星图**: 基于Shader的动态星图渲染
- **状态管理**: Riverpod驱动的响应式状态管理
- **社群互动**: 丰富的社群功能和动画效果

## 扩展性与维护性

### 模块化设计
- 各模块职责明确，低耦合
- API接口标准化
- 易于独立开发和测试

### 可扩展性
- 插件式工具系统
- 可配置的推送策略
- 支持多AI提供商
- 灵活的社群功能扩展

### 维护性
- 统一的错误处理机制
- 详细的日志记录
- 标准化的数据验证
