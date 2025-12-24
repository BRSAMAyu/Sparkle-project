# Sparkle 项目技术架构

## 概述

Sparkle 是一款面向大学生的 AI 学习助手应用，采用前后端分离的微服务架构。项目围绕 AI 驱动的学习助手概念，构建了一个完整的学习生态系统。

## 整体架构

```
┌─────────────────┐    HTTP/HTTPS     ┌──────────────────┐
│   Mobile App    │ ◄───────────────► │   FastAPI API    │
│   (Flutter)     │                   │   (Python)       │
└─────────────────┘                   └──────────────────┘
                                              │
                                    ┌──────────────────┐
                                    │  AI/LLM Service  │
                                    │  (Qwen/DeepSeek) │
                                    └──────────────────┘
                                              │
                                    ┌──────────────────┐
                                    │  PostgreSQL DB   │
                                    │  (with pgvector) │
                                    └──────────────────┘
```

## 后端架构

### 技术栈
- **框架**: FastAPI (Python 3.11+)
- **数据库**: PostgreSQL (生产) / SQLite (开发) 通过 SQLAlchemy 2.0 (异步)
- **AI服务**: OpenAI兼容API (支持Qwen/DeepSeek)
- **向量数据库**: pgvector
- **缓存/队列**: Redis
- **异步处理**: APScheduler, 后台任务

### 核心服务层
- **UserService**: 用户认证与管理 (基础实现)
- **GalaxyService**: 知识星图核心服务 (完整实现)
- **TaskService**: 任务管理服务 (完整实现)
- **PlanService**: 计划管理服务 (API定义完整，实现有限)
- **LLMService**: 大语言模型服务 (完整实现)
- **PushService**: 智能推送服务 (完整实现)
- **CommunityService**: 社群服务 (新增)

### 项目结构
```
backend/
├── app/
│   ├── main.py                           # 应用入口点，包含 lifespan 管理
│   ├── config.py                         # 配置管理，使用 pydantic-settings
│   ├── api/
│   │   ├── v1/
│   │   │   ├── router.py                 # API 路由聚合
│   │   │   ├── galaxy.py                 # 知识星图 API
│   │   │   ├── chat.py                   # 聊天 API，支持工具调用和流式响应
│   │   │   ├── tasks.py                  # 任务 API
│   │   │   ├── plans.py                  # 计划 API
│   │   │   ├── auth.py                   # 认证 API
│   │   │   ├── community.py              # 社群 API
│   │   │   └── ...                       # 其他 API
│   ├── services/
│   │   ├── galaxy_service.py             # 知识星图核心服务，处理星图数据、节点点亮、语义搜索
│   │   ├── expansion_service.py          # 知识拓展服务，使用 LLM 自动拓展知识节点
│   │   ├── decay_service.py              # 遗忘衰减服务，实现艾宾浩斯遗忘曲线
│   │   ├── llm_service.py                # LLM 服务，与大语言模型交互
│   │   ├── task_service.py               # 任务服务，处理任务业务逻辑
│   │   ├── plan_service.py               # 计划服务，处理计划业务逻辑
│   │   ├── user_service.py               # 用户服务，处理用户业务逻辑
│   │   ├── notification_service.py       # 通知服务，处理系统通知
│   │   ├── push_service.py               # 智能推送服务，实现个性化推送
│   │   ├── scheduler_service.py          # 调度服务，定时任务管理
│   │   ├── community_service.py          # 社群服务，处理社群功能
│   │   └── ...                           # 其他服务
│   ├── models/
│   │   ├── galaxy.py                     # 知识星图模型，包含 KnowledgeNode、UserNodeStatus 等
│   │   ├── task.py                       # 任务模型
│   │   ├── plan.py                       # 计划模型
│   │   ├── user.py                       # 用户模型
│   │   ├── chat.py                       # 聊天消息模型
│   │   ├── community.py                  # 社群模型
│   │   ├── notification.py               # 通知模型
│   │   └── ...                           # 其他模型
│   ├── workers/
│   │   └── expansion_worker.py           # 知识拓展后台任务，处理节点拓展队列
│   ├── core/
│   │   ├── sse.py                        # SSE 管理，实现实时事件推送
│   │   ├── exceptions.py                 # 异常处理
│   │   ├── security.py                   # 安全相关，JWT token 处理
│   │   └── ...                           # 核心模块
│   ├── tools/
│   │   ├── registry.py                   # 工具注册表
│   │   ├── base.py                       # 工具基类
│   │   ├── knowledge_tools.py            # 知识相关工具
│   │   ├── task_tools.py                 # 任务相关工具
│   │   ├── community_tools.py            # 社群相关工具
│   │   └── schemas.py                    # 工具 Schema 定义
│   └── orchestration/
│       ├── composer.py                   # 响应编排
│       ├── executor.py                   # 工具执行器
│       ├── prompts.py                    # Prompt 管理
│       └── error_handler.py              # 错误处理
├── alembic/                              # 数据库迁移
├── seed_data/                            # 种子数据
└── ...                                   # 其他文件
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

1. **用户认证流**: 用户模块 → 认证 → 其他所有模块
2. **学习流**: 知识星图 → 任务 → 执行 → 反馈 → 计划
3. **AI交互流**: 用户输入 → LLM模块 → 工具执行 → 结果返回
4. **推送流**: 各模块状态 → 推送策略 → 用户通知
5. **社群流**: 用户 → 社群模块 → 群组/好友 → 互动/打卡

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

### 后端亮点
- **异步处理**: 全面采用异步操作提升性能
- **向量搜索**: 基于pgvector的语义搜索
- **工具系统**: 可扩展的AI工具调用机制
- **SSE推送**: 实时事件推送机制
- **遗忘曲线**: 艾宾浩斯遗忘曲线算法

### 前端亮点
- **可视化星图**: 基于Shader的动态星图渲染
- **状态管理**: Riverpod驱动的状态管理
- **响应式设计**: 适配不同屏幕尺寸
- **动画效果**: 流畅的交互动画
- **社群互动**: 丰富的社群功能

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
