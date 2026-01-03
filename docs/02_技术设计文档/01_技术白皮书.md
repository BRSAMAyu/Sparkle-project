# Sparkle 项目技术白皮书

## 1. 🏗️ 系统架构与配置详情 (System Architecture & Configuration)

### 依赖矩阵

#### 后端 (FastAPI)
- **fastapi**: Web 框架，用于构建 RESTful API
- **uvicorn**: ASGI 服务器，用于运行 FastAPI 应用
- **sqlalchemy**: ORM 框架，用于数据库操作
- **asyncpg**: 异步 PostgreSQL 驱动
- **pydantic**: 数据验证和设置管理
- **pydantic-settings**: 配置管理
- **python-jose**: JWT token 处理
- **passlib**: 密码哈希
- **loguru**: 日志记录
- **apscheduler**: 定时任务调度
- **openai**: 与 LLM 交互
- **pgvector**: 向量数据库支持
- **redis**: 缓存和后台任务队列

#### 移动端 (Flutter)
- **flutter_riverpod**: 状态管理
- **go_router**: 路由管理
- **http**: HTTP 客户端
- **shared_preferences**: 本地存储
- **hive**: 本地数据库
- **flutter_svg**: SVG 图像渲染
- **intl**: 国际化支持

### 环境与配置

#### 后端配置 (`backend/app/config.py`)
后端配置通过 `pydantic-settings` 管理，从 `.env` 文件读取环境变量：

- `APP_NAME`: 应用名称 ("Sparkle")
- `APP_VERSION`: 应用版本 ("0.1.0")
- `DEBUG`: 调试模式开关
- `SECRET_KEY`: 用于 JWT 签名的密钥
- `DATABASE_URL`: 数据库连接 URL
- `BACKEND_CORS_ORIGINS`: CORS 白名单
- `LLM_API_BASE_URL`: LLM API 基础 URL
- `LLM_API_KEY`: LLM API 密钥
- `LLM_MODEL_NAME`: LLM 模型名称
- `LLM_PROVIDER`: LLM 提供商
- `EMBEDDING_MODEL`: 向量模型名称
- `EMBEDDING_DIM`: 向量维度 (1536)
- `UPLOAD_DIR`: 文件上传目录
- `MAX_UPLOAD_SIZE`: 最大上传文件大小
- `LOG_LEVEL`: 日志级别
- `DEMO_MODE`: 演示模式开关

这些配置在 `Settings` 类中定义，并通过 `settings = Settings()` 全局实例化。

#### 移动端配置
移动端配置主要通过 `pubspec.yaml` 文件管理依赖包，并通过 `shared_preferences` 和 `hive` 进行本地数据存储。

### 启动流程

#### 后端启动流程 (`backend/app/main.py`)
1. 应用启动时，FastAPI 的 `lifespan` 上下文管理器被调用
2. **启动阶段**:
   - 初始化数据库数据 (`init_db`)
   - 恢复中断的 Job (`JobService.startup_recovery`)
   - 加载学科缓存 (`SubjectService.load_cache`)
   - 启动定时任务调度器 (`scheduler_service.start`)
   - 启动知识拓展后台任务 (`start_expansion_worker`)
3. **关闭阶段**:
   - 停止知识拓展后台任务 (`stop_expansion_worker`)

#### 移动端启动流程 (`mobile/lib/main.dart`)
1. `WidgetsFlutterBinding.ensureInitialized()`: 确保 Flutter 绑定初始化
2. `Hive.initFlutter()`: 初始化 Hive 本地存储
3. `SharedPreferences.getInstance()`: 初始化共享偏好设置
4. `runApp(ProviderScope(...))`: 运行应用，使用 Riverpod 进行状态管理

## 2. 🔌 后端深度解析 (Backend Deep Dive)

### API 路由全集

| HTTP Method | Endpoint | 对应 Controller 函数 | 核心 Service 调用 |
|-------------|----------|----------------------|-------------------|
| GET | `/api/v1/galaxy/graph` | `get_galaxy_graph` | `GalaxyService.get_galaxy_graph` |
| POST | `/api/v1/galaxy/node/{node_id}/spark` | `spark_node` | `GalaxyService.spark_node` |
| GET | `/api/v1/galaxy/node/{node_id}` | `get_node_detail` | `GalaxyService._get_user_status` |
| POST | `/api/v1/galaxy/search` | `search_nodes` | `GalaxyService.semantic_search` |
| GET | `/api/v1/galaxy/review/suggestions` | `get_review_suggestions` | `DecayService.get_review_suggestions` |
| POST | `/api/v1/galaxy/node/{node_id}/decay/pause` | `pause_node_decay` | `DecayService.pause_decay` |
| GET | `/api/v1/galaxy/stats` | `get_galaxy_stats` | `GalaxyService._calculate_user_stats`, `DecayService.get_decay_stats` |
| GET | `/api/v1/galaxy/events` | `galaxy_events_stream` | `sse_manager.connect` |
| POST | `/api/v1/chat` | `chat` | `llm_service.chat_with_tools`, `ToolExecutor.execute_tool_calls` |
| POST | `/api/v1/chat/stream` | `chat_stream` | `llm_service.chat_stream_with_tools`, `ToolExecutor.execute_tool_call` |
| POST | `/api/v1/chat/confirm` | `confirm_action` | `ToolExecutor.execute_tool_call` |
| GET | `/api/v1/tasks` | `get_tasks` | `TaskService.get_multi` |
| POST | `/api/v1/tasks` | `create_task` | `TaskService.create` |
| GET | `/api/v1/tasks/{id}` | `get_task` | `TaskService.get_by_id` |
| PUT | `/api/v1/tasks/{id}` | `update_task` | `TaskService.update` |
| POST | `/api/v1/tasks/{id}/start` | `start_task` | `TaskService.start` |
| POST | `/api/v1/tasks/{id}/complete` | `complete_task` | `TaskService.complete` |
| POST | `/api/v1/tasks/{id}/abandon` | `abandon_task` | `TaskService.abandon` |
| GET | `/api/v1/plans` | `get_plans` | `PlanService.get_multi` |
| POST | `/api/v1/plans` | `create_plan` | `PlanService.create` |

### 数据模型透视 (Database Schema)

#### 核心表结构

##### `users` (用户表)
- `id` (GUID): 主键
- `username` (String): 用户名
- `email` (String): 邮箱
- `hashed_password` (String): 加密密码
- `nickname` (String): 昵称
- `avatar_url` (String): 头像URL
- `flame_level` (Integer): 火花等级 (1-10)
- `flame_brightness` (Float): 火花亮度 (0-1)
- `depth_preference` (Float): 深度偏好 (0-1)
- `curiosity_preference` (Float): 好奇偏好 (0-1)
- `schedule_preferences` (JSON): 碎片时间/日程偏好
- `is_active` (Boolean): 是否激活

##### `knowledge_nodes` (知识节点表)
- `id` (GUID): 主键
- `subject_id` (Integer): 关联学科 ID (外键到 `subjects` 表)
- `parent_id` (GUID): 父节点 ID (自关联)
- `name` (String): 节点名称
- `name_en` (String): 英文名称
- `description` (Text): 描述
- `keywords` (JSON): 关键词数组
- `importance_level` (Integer): 重要性等级 (1-5)
- `is_seed` (Boolean): 是否为种子节点
- `source_type` (String): 节点来源 (seed/user_created/llm_expanded)
- `source_task_id` (GUID): 来源任务 ID
- `embedding` (Vector): 向量嵌入

##### `user_node_status` (用户节点状态表)
- `user_id` (GUID): 用户 ID (复合主键之一)
- `node_id` (GUID): 节点 ID (复合主键之一)
- `mastery_score` (Float): 掌握度分数 (0-100)
- `total_study_minutes` (Integer): 总学习分钟数
- `study_count` (Integer): 学习次数
- `is_unlocked` (Boolean): 是否已解锁
- `is_collapsed` (Boolean): 是否已折叠
- `is_favorite` (Boolean): 是否收藏
- `last_study_at` (DateTime): 最后学习时间
- `decay_paused` (Boolean): 是否暂停遗忘衰减
- `next_review_at` (DateTime): 下次复习时间
- `first_unlock_at` (DateTime): 首次解锁时间

##### `node_relations` (节点关系表)
- `source_node_id` (GUID): 源节点 ID
- `target_node_id` (GUID): 目标节点 ID
- `relation_type` (String): 关系类型 (prerequisite/related/application/composition/evolution)
- `strength` (Float): 关系强度 (0-1)
- `created_by` (String): 创建者 (seed/user/llm)

##### `study_records` (学习记录表)
- `user_id` (GUID): 用户 ID
- `node_id` (GUID): 节点 ID
- `task_id` (GUID): 关联任务 ID
- `study_minutes` (Integer): 学习分钟数
- `mastery_delta` (Float): 掌握度增量
- `record_type` (String): 记录类型 (task_complete/review/exploration)

##### `node_expansion_queue` (节点拓展队列表)
- `trigger_node_id` (GUID): 触发节点 ID
- `trigger_task_id` (GUID): 触发任务 ID
- `user_id` (GUID): 用户 ID
- `expansion_context` (Text): 拓展上下文
- `status` (String): 状态 (pending/processing/completed/failed)
- `expanded_nodes` (JSON): 拓展的节点
- `error_message` (Text): 错误信息
- `processed_at` (DateTime): 处理时间

##### `tasks` (任务表)
- `id` (GUID): 主键
- `user_id` (GUID): 所属用户ID
- `plan_id` (GUID): 关联计划ID（可选）
- `title` (String): 任务标题
- `type` (Enum): 任务类型 (learning/training/error_fix/reflection/social/planning)
- `tags` (JSON): 标签列表
- `estimated_minutes` (Integer): 预估时长(分钟)
- `difficulty` (Integer): 难度等级 (1-5)
- `energy_cost` (Integer): 能量消耗 (1-5)
- `guide_content` (Text): 引导内容(AI生成)
- `status` (Enum): 任务状态 (pending/in_progress/completed/abandoned)
- `started_at` (DateTime): 开始时间
- `completed_at` (DateTime): 完成时间
- `actual_minutes` (Integer): 实际时长
- `user_note` (Text): 用户笔记
- `priority` (Integer): 优先级
- `due_date` (Date): 截止日期
- `knowledge_node_id` (GUID): 关联知识节点ID
- `auto_expand_enabled` (Boolean): 是否启用自动拓展

##### `plans` (计划表)
- `id` (GUID): 主键
- `user_id` (GUID): 所属用户ID
- `name` (String): 计划名称
- `type` (Enum): 计划类型 (sprint/growth)
- `description` (Text): 计划描述
- `target_date` (Date): 目标日期(冲刺计划用)
- `daily_available_minutes` (Integer): 每日可用时间(分钟)
- `total_estimated_hours` (Float): 总预估时长(小时)
- `mastery_level` (Float): 掌握程度 (0-1)
- `progress` (Float): 进度百分比 (0-1)
- `is_active` (Boolean): 是否激活

##### `chat_messages` (聊天消息表)
- `id` (GUID): 主键
- `user_id` (GUID): 所属用户ID
- `session_id` (GUID): 会话ID(用于区分不同对话)
- `task_id` (GUID): 关联任务ID(可选，当对话与某个任务相关)
- `role` (Enum): 消息角色(user/assistant/system)
- `content` (Text): 消息内容
- `actions` (JSON): AI执行的动作列表
- `tokens_used` (Integer): 消耗的token数量
- `model_name` (String): 使用的模型名称

##### `notifications` (通知表)
- `id` (GUID): 主键
- `user_id` (GUID): 所属用户ID
- `title` (String): 通知标题
- `content` (String): 通知内容
- `type` (String): 通知类型 (fragmented_time/system/reminder)
- `is_read` (Boolean): 是否已读
- `read_at` (DateTime): 阅读时间
- `data` (JSON): 关联的数据

##### `push_preferences` (推送偏好设置表)
- `id` (GUID): 主键
- `user_id` (GUID): 所属用户ID
- `active_slots` (JSON): 活跃时间段
- `timezone` (String): 时区
- `enable_curiosity` (Boolean): 是否启用好奇心推送
- `persona_type` (String): 推送人格类型 (coach/anime)
- `daily_cap` (Integer): 每日推送上限
- `last_push_time` (DateTime): 上次推送时间
- `consecutive_ignores` (Integer): 连续忽略次数

##### `push_histories` (推送历史记录表)
- `id` (GUID): 主键
- `user_id` (GUID): 所属用户ID
- `trigger_type` (String): 触发类型 (memory/sprint/inactivity)
- `content_hash` (String): 内容哈希
- `status` (String): 状态 (sent/clicked/snoozed/dismissed)

### 核心服务逻辑 (Service Logic)

#### GalaxyService (知识星图服务)
`GalaxyService (backend/app/services/galaxy_service.py)` 负责知识星图的核心功能：

1. **获取星图数据** (`get_galaxy_graph`):
   - 查询用户的所有知识节点及其状态
   - 查询节点间的关系
   - 组装成完整的星图数据结构返回

2. **点亮知识点** (`spark_node`):
   - 计算掌握度增量：基于学习时长和节点重要性等级
   - 更新用户节点状态 (掌握度、学习次数、最后学习时间等)
   - 记录学习历史
   - 当学习次数达到2次时，触发 LLM 拓展

3. **ExpansionService (知识拓展服务)**:
   - `queue_expansion`: 将拓展请求加入队列
   - `_should_expand`: 检查是否应该触发拓展
   - `_build_expansion_context`: 构建发送给 LLM 的拓展上下文
   - `process_expansion`: 处理拓展请求
   - `_create_expanded_nodes`: 创建拓展的知识节点

4. **ExpansionWorker (拓展工作线程)**:
   - 定期扫描 `node_expansion_queue` 表
   - 处理 `pending` 状态的拓展任务
   - 调用 `ExpansionService.process_expansion` 处理任务
   - 通过 SSE 通知前端新节点已创建

3. **语义搜索** (`semantic_search`):
   - 使用向量相似度搜索相关知识点
   - 结合用户状态信息返回搜索结果

#### LLMService (大语言模型服务)
`LLMService (backend/app/services/llm_service.py)` 负责与大语言模型交互：

1. **聊天功能** (`chat_with_tools`):
   - 支持工具调用的聊天接口
   - 构建系统提示词和对话历史
   - 调用 LLM 并处理工具调用

2. **流式聊天** (`chat_stream_with_tools`):
   - 流式返回聊天内容，支持实时显示
   - 处理流式工具调用

3. **继续对话** (`continue_with_tool_results`):
   - 将工具执行结果反馈给 LLM，获取最终回复

#### TaskService (任务服务)
`TaskService (backend/app/services/task_service.py)` 负责任务管理：

1. **创建任务** (`create`)
2. **更新任务** (`update`)
3. **开始任务** (`start`)
4. **完成任务** (`complete`)
5. **放弃任务** (`abandon`)

#### PushService (智能推送服务)
`PushService (backend/app/services/push_service.py)` 负责智能推送逻辑：

1. **处理所有用户推送** (`process_all_users`):
   - 获取所有具有推送偏好的活跃用户
   - 为每个用户调用 `process_user_push` 方法

2. **处理单个用户推送** (`process_user_push`):
   - 检查用户是否在活跃时间段内
   - 检查频率限制（每日上限和冷却时间）
   - 评估推送策略（冲刺策略 > 记忆策略 > 不活跃策略）
   - 生成推送内容
   - 发送推送并记录历史

#### Push Strategies (推送策略)
推送策略通过抽象基类 `PushStrategy` 实现，具体包括：

1. **MemoryStrategy (记忆策略)**:
   - 检测用户掌握度较低但重要性较高的知识点
   - 当计算的记忆保留率小于0.3且重要性大于4时触发
   - 通过 `DecayService` 的遗忘曲线算法计算保留率

2. **SprintStrategy (冲刺策略)**:
   - 检测用户即将到期的冲刺计划
   - 当计划目标日期在72小时内时触发

3. **InactivityStrategy (不活跃策略)**:
   - 检测长期未活跃的用户
   - 当用户超过24小时未活动时触发

#### SchedulerService (调度服务)
`SchedulerService (backend/app/services/scheduler_service.py)` 负责定时任务调度：

1. **智能推送循环**:
   - 每15分钟运行一次 `run_smart_push_cycle`
   - 触发 `PushService.process_all_users()`

2. **每日衰减任务**:
   - 每天凌晨3点运行 `apply_daily_decay`
   - 对所有用户的知识点应用遗忘曲线衰减

#### DecayService (遗忘衰减服务)
`DecayService (backend/app/services/decay_service.py)` 实现艾宾浩斯遗忘曲线：

1. **每日衰减** (`apply_daily_decay`):
   - 对所有符合条件的节点应用遗忘衰减
   - 计算衰减后的掌握度

2. **获取复习建议** (`get_review_suggestions`):
   - 根据掌握度和下次复习时间推荐需要复习的节点

## 3. 📱 移动端深度解析 (Mobile Deep Dive)

### 路由体系
移动端使用 `go_router` 进行路由管理，主要页面包括：
- `/`: 启动页 (SplashScreen)
- `/login`: 登录页 (LoginScreen)
- `/register`: 注册页 (RegisterScreen)
- `/home`: 主页 (HomeScreen)
- `/tasks`: 任务列表页 (TaskListScreen)
- `/tasks/:id`: 任务详情页 (TaskDetailScreen)
- `/tasks/:id/execute`: 任务执行页 (TaskExecutionScreen)
- `/chat`: 聊天页 (ChatScreen)
- `/sprint`: 冲刺计划页 (SprintScreen)
- `/growth`: 成长计划页 (GrowthScreen)
- `/profile`: 个人资料页 (ProfileScreen)
- `/galaxy`: 知识星图页 (GalaxyScreen)

### 状态管理图谱 (State Management)
移动端使用 `Riverpod` 进行状态管理，核心 Provider 包括：
- `authProvider`: 认证状态管理
- `galaxyProvider`: 知识星图状态管理
- `chatProvider`: 聊天状态管理
- `taskProvider`: 任务状态管理

### 关键 UI 组件实现

#### Knowledge Galaxy (知识星图)
`GalaxyScreen (mobile/lib/presentation/screens/galaxy_screen.dart)` 是知识星图的主界面：

1. **星图绘制**:
   - 使用 `InteractiveViewer` 实现可缩放和拖拽的画布
   - 使用 `CustomPaint` 和 `StarMapPainter` 绘制星图
   - 节点位置通过 `_calculateLayout` 方法计算

2. **火焰核心**:
   - 使用 `FlameCore` 组件渲染中心的火焰效果
   - 通过 Fragment Shader 实现动态火焰动画

3. **交互动画**:
   - 点击节点时触发动画效果
   - 使用 `EnergyTransferAnimation` 实现能量传输动画
   - 使用 `StarSuccessAnimation` 实现点亮成功动画

#### Shader 实现
`FlameCore (mobile/lib/presentation/widgets/galaxy/flame_core.dart)` 使用 Fragment Shader 实现火焰效果：

1. **Shader 加载**:
   - 通过 `FragmentProgram.fromAsset` 加载 GLSL 着色器程序

2. **参数传递**:
   - 通过 `setFloat` 方法向着色器传递时间、强度等参数

3. **渲染**:
   - 使用 `CustomPaint` 和 `_ShaderPainter` 进行渲染

## 4. 🧠 跨端核心业务流 (Critical Business Flows)

### "点亮星星"全链路

1. **用户点击前端星星**:
   - `GalaxyScreen` 捕获点击事件
   - 触发 `_sparkNodeWithAnimation` 方法

2. **调用 API**:
   - 前端调用 `/api/v1/galaxy/node/{node_id}/spark` 接口

3. **后端计算**:
   - `GalaxyService.spark_node` 计算掌握度增量
   - 更新 `UserNodeStatus` 模型的 `mastery_score` 字段
   - 记录学习历史到 `StudyRecord` 表

4. **数据库更新**:
   - SQLAlchemy 提交事务，更新数据库

5. **触发 AI 拓展**:
   - 当学习次数达到2次时，`ExpansionService.queue_expansion` 将拓展请求加入队列

6. **SSE 推送**:
   - `ExpansionWorker` 处理拓展队列
   - 通过 `sse_manager.send_to_user` 向前端推送新节点信息

7. **前端播放动画**:
   - 前端接收到 SSE 事件后，更新界面并播放动画

### AI 对话流

1. **用户发送消息**:
   - 用户在聊天界面输入消息并发送

2. **后端接收**:
   - `chat` 或 `chat_stream` 接口接收消息

3. **检索上下文**:
   - `get_user_context` 获取用户学习状态
   - `get_conversation_history` 获取对话历史

4. **调用 LLM**:
   - `llm_service.chat_with_tools` 调用 LLM 并传递工具定义

5. **流式返回**:
   - LLM 流式返回文本内容和工具调用信息

6. **前端渲染**:
   - 前端实时显示 LLM 返回的内容
   - 处理工具调用并显示相应组件

### 智能推送流

1. **定时触发**:
   - `SchedulerService` 每15分钟触发一次智能推送循环

2. **评估用户**:
   - `PushService.process_all_users` 获取所有具有推送偏好的活跃用户
   - 为每个用户调用 `process_user_push` 方法

3. **策略评估**:
   - 按优先级评估推送策略：冲刺策略 > 记忆策略 > 不活跃策略
   - `SprintStrategy.should_trigger` 检查是否有即将到期的冲刺计划
   - `MemoryStrategy.should_trigger` 检查是否有掌握度较低的重要知识点
   - `InactivityStrategy.should_trigger` 检查用户是否长期未活跃

4. **生成内容**:
   - 选择触发的策略，调用 `get_trigger_data` 获取触发数据
   - `llm_service.generate_push_content` 根据用户人格类型生成个性化推送内容

5. **发送推送**:
   - `NotificationService.create` 创建通知记录
   - `PushHistory` 记录推送历史用于频控和分析

6. **前端展示**:
   - 用户在通知中心看到推送通知
   - 点击通知可跳转到相应页面（计划页面、知识点页面等）

## 5. 📂 目录与关键文件索引 (File Index)

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
│   │   └── ...                           # 其他服务
│   ├── models/
│   │   ├── galaxy.py                     # 知识星图模型，包含 KnowledgeNode、UserNodeStatus 等
│   │   ├── task.py                       # 任务模型
│   │   ├── plan.py                       # 计划模型
│   │   ├── user.py                       # 用户模型
│   │   ├── chat.py                       # 聊天消息模型
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
│   │   └── schemas.py                    # 工具 Schema 定义
│   └── orchestration/
│       ├── composer.py                   # 响应编排
│       ├── executor.py                   # 工具执行器
│       ├── prompts.py                    # Prompt 管理
│       └── error_handler.py              # 错误处理
├── alembic/                              # 数据库迁移
├── seed_data/                            # 种子数据
└── ...                                   # 其他文件

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
│   │   │   └── ...                       # 其他界面
│   │   ├── providers/
│   │   │   ├── galaxy_provider.dart      # 知识星图状态管理
│   │   │   ├── chat_provider.dart        # 聊天状态管理
│   │   │   ├── task_provider.dart        # 任务状态管理
│   │   │   └── ...                       # 其他状态管理
│   │   └── widgets/
│   │       ├── galaxy/
│   │       │   ├── flame_core.dart       # 火焰核心组件，使用 Fragment Shader
│   │       │   ├── star_map_painter.dart # 星图绘制
│   │       │   ├── energy_particle.dart   # 能量粒子动画
│   │       │   └── star_success_animation.dart # 点亮成功动画
│   │       └── ...                       # 其他组件
│   ├── data/
│   │   ├── repositories/
│   │   │   ├── galaxy_repository.dart    # 知识星图数据仓库
│   │   │   ├── chat_repository.dart      # 聊天数据仓库
│   │   │   ├── task_repository.dart      # 任务数据仓库
│   │   │   └── ...                       # 其他数据仓库
│   │   ├── models/
│   │   │   ├── galaxy_model.dart         # 知识星图数据模型
│   │   │   ├── chat_message_model.dart   # 聊天消息数据模型
│   │   │   ├── task_model.dart           # 任务数据模型
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

## 6. ⚠️ 异常处理与边界情况 (Error Handling)

### 后端异常处理
后端通过 `app/core/exceptions.py` 统一处理 HTTP 异常，定义了多种自定义异常类型，如 `BadRequestException`、`UnauthorizedException`、`NotFoundException`、`InternalServerErrorException` 等，并在 API 路由中捕获这些异常，返回标准化的错误响应。

异常处理机制包括：
1. **自定义异常类**: 定义了各种业务相关的异常类型
2. **全局异常处理器**: 在 `app/main.py` 中注册全局异常处理器，捕获未处理的异常
3. **HTTP 状态码映射**: 将自定义异常映射到标准的 HTTP 状态码
4. **错误日志记录**: 使用 `loguru` 记录详细的错误日志，便于调试和监控
5. **错误响应格式**: 统一的错误响应格式，包含错误码、错误消息和详细信息

### 前端网络异常处理
前端在网络断开时，通常会显示友好的错误提示，并提供重试机制。对于关键操作，会在本地缓存操作记录，待网络恢复后重新提交。

异常处理机制包括：
1. **网络状态检测**: 使用 `connectivity_plus` 插件检测网络连接状态
2. **HTTP 错误处理**: 捕获 HTTP 请求错误，根据状态码显示相应的错误消息
3. **超时处理**: 设置合理的请求超时时间，避免长时间等待
4. **重试机制**: 对于可重试的操作，提供重试按钮或自动重试功能
5. **本地缓存**: 使用 `hive` 或 `shared_preferences` 缓存关键操作，在网络恢复后重新提交
6. **用户友好提示**: 显示清晰易懂的错误提示，避免技术术语
