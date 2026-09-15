## Sparkle 偏好系统对齐文档

### 1. 目标与范围
- 目标：将分散的用户偏好统一为单一事实来源，并让 AI/Push/Task/Graph 全链路一致使用。
- 范围：Phase 1-6 + 任务闭环补丁（TaskService 个性化默认值与图谱回写）。

### 2. 总体架构与统一原则
- Single Source of Truth：`user_preferences_center` 作为显式/推断偏好的唯一主表。
- 统一映射层：`PersonalizationEngine` 将偏好映射为模块策略（LLM/Push/Task）。
- 事件与缓存：Go 发布偏好事件 + Python 订阅失效，双保险确保偏好秒级生效。
- 统一读写：写入路径统一到 `PreferenceService`，读取路径由 `UserService/ContextOrchestrator/Engine` 统一拉取。

### 3. 已完成的核心交付（按阶段）
#### Phase 1：偏好中心 + 事件总线
- 模型：`backend/app/models/user_preferences.py`
- 迁移：`backend/alembic/versions/f3b8c1d2e4f5_create_user_preferences_center.py`
- 事件类型：`backend/gateway/internal/cqrs/event/types.go`
- Go 偏好服务：`backend/gateway/internal/service/user_preferences_service.go`
- Python 事件消费者：`backend/app/services/preference_event_consumer.py`
- 时区与 active_slots 标准化：`backend/app/services/user_service.py`
- 数据迁移脚本：`backend/scripts/migrate_preferences_to_center.py`

#### Phase 2：Personalization Engine
- Profiles：`backend/app/services/personalization/profiles.py`
- 偏好访问层：`backend/app/services/personalization/preference_service.py`
- 运行时上下文：`backend/app/services/personalization/runtime_context_service.py`
- 引擎映射：`backend/app/services/personalization/engine.py`
- 工厂函数：`backend/app/services/personalization/__init__.py`

#### Phase 3：AI 系统集成
- Orchestrator 注入 LLMProfile：`backend/app/orchestration/orchestrator.py`
- System Prompt 动态偏好：`backend/app/orchestration/prompts.py`
- 动态 temperature：`backend/app/services/llm_service.py`
- 响应元数据 preference_version：`proto/agent_service.proto` + `backend/gateway/internal/handler/chat_orchestrator.go`

#### Phase 4：推送系统升级
- 策略基类改造：`backend/app/services/push_strategies/strategy.py`
- PushService 接入策略：`backend/app/services/push_service.py`
- LLM 推送内容个性化：`backend/app/services/llm_service.py`
- 反馈闭环：`backend/app/services/push_feedback_service.py`
- PushHistory 交互字段迁移：`backend/alembic/versions/f4c9d1e2a3b5_add_push_history_interactions.py`

#### Phase 5：任务系统闭环
- 任务完成 -> 图谱：`backend/app/api/v1/tasks.py`
- 微任务推荐 API：`backend/app/api/v1/tasks.py`
- 推荐服务：`backend/app/services/task_recommendation_service.py`

#### Phase 6：可视化与反馈
- 偏好预览/生效证明 API：`backend/app/api/v1/preferences.py`
- 决策记录服务：`backend/app/services/decision_record_service.py`
- 决策记录模型：`backend/app/models/decision_record.py`
- 迁移：`backend/alembic/versions/f5d0a1b2c3d4_add_decision_records.py`
- 路由注册：`backend/app/api/v1/router.py`
- AI/Push 决策落库：`backend/app/orchestration/orchestrator.py`、`backend/app/services/push_service.py`

#### 补丁：任务闭环 + 个性化默认值
- TaskService 完成任务图谱回写：`backend/app/services/task_service.py`
- TaskService 创建任务使用 TaskPlanProfile：`backend/app/services/task_service.py`
- API 统一走 TaskService：`backend/app/api/v1/tasks.py`
- 创建任务入参放开默认值：`backend/app/schemas/task.py`

### 4. 统一读写路径的对齐说明
- 写入入口统一：
  - 用户偏好更新：`backend/app/api/v1/users.py` -> `PreferenceService.update_explicit`
  - Push 反馈闭环：`backend/app/services/push_feedback_service.py` -> `PreferenceService.update_inferred`
  - PushPreference 更新：`backend/app/services/user_service.py` 同步写入偏好中心
- 读取入口统一：
  - UserContext/Preferences：`backend/app/services/user_service.py`
  - CognitiveContext：`backend/app/core/context_manager.py`
  - Chat 快路径上下文：`backend/app/api/v1/chat.py`
  - Curiosity Capsule：`backend/app/services/curiosity_capsule_service.py`

### 5. 缓存一致性与事件链路
- Go 侧更新后删除缓存：`backend/gateway/internal/service/user_preferences_service.go`
- Python 侧消费 Redis Stream：
  - 监听 `cqrs:stream:user`
  - 失效 `user:context:*` / `user:context:snapshot:*` / `user:prefs:center:*`
- 事件消费者已接入 app 生命周期：`backend/app/main.py`

### 6. 策略映射一致性
#### LLMProfile
- 基于 depth/curiosity/persona/feedback_style 映射 verbosity/temperature/tone。
- 注入 System Prompt 的偏好说明由引擎统一生成。

#### PushPolicyProfile
- min_interval 使用 inferred.consecutive_ignores。
- active_hours 使用 active_slots + DOW 过滤。
- silent_during_focus 来自 RuntimeContextService。

#### TaskPlanProfile
- preferred_task_duration 用于任务创建默认值。
- exploration_ratio/micro_task_friendly 用于推荐与微任务筛选。

### 7. 可追溯性与可视化
- 决策记录覆盖 AI 与 Push，包含 preference_version 与 snapshot。
- 预览 API 可在保存前模拟 AI/Push/Task 效果。
- 生效证明 API 返回近期决策记录汇总。

### 8. 验证与结论
- 已完成链路验证：偏好更新 -> 缓存失效 -> Engine 映射 -> Prompt 注入。
- 系统输出已符合预期：temperature/verbosity/persona 及时变化。
- 任务系统闭环已补齐：完成任务可触发图谱学习回写。

### 9. 已知注意事项与建议
- 环境迁移需保持最新：建议演示前执行 `alembic upgrade head`。
- 旧字段保留用于兼容，但核心逻辑以偏好中心为准。
- 如需进一步提升闭环可视化，可把 Task 决策纳入 DecisionRecordService。

### 10. 关键文件总览
- 偏好中心：`backend/app/models/user_preferences.py`
- 引擎与服务：`backend/app/services/personalization/*`
- 事件与缓存：`backend/gateway/internal/cqrs/event/types.go`、`backend/app/services/preference_event_consumer.py`
- AI 集成：`backend/app/orchestration/orchestrator.py`、`backend/app/orchestration/prompts.py`
- 推送系统：`backend/app/services/push_service.py`、`backend/app/services/push_strategies/strategy.py`
- 任务闭环：`backend/app/services/task_service.py`、`backend/app/api/v1/tasks.py`
- 可视化：`backend/app/api/v1/preferences.py`
- 决策记录：`backend/app/models/decision_record.py`、`backend/app/services/decision_record_service.py`
