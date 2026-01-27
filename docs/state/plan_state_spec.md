# PlanScope 状态规范设计文档

> **版本**: 1.0.0
> **状态**: Draft
> **最后更新**: 2026-01-24

---

## 1. 背景与目标

### 1.1 现有 UserScope 架构

当前系统通过 `ContextPackBuilder` 构建用户上下文包，主要包含三类信息：

| 类型 | 数据源 | 注入路径 | 更新频率 |
|------|--------|----------|----------|
| **Preferences** | `MemoryPreference` + `UserPreferencesCenter` | `MemoryService.list_preference_records()` | 用户操作/推断更新 |
| **Goals** | `MemoryGoal` | `MemoryService.list_active_goals()` | 目标创建/状态变更 |
| **Episodic** | `EpisodicMemory` | `MemoryService.list_recent_episodic()` | 事件发生时写入 |

这些信息都是 **用户级别 (User-Level)** 的长期状态，不区分具体计划上下文。

### 1.2 问题陈述

当前架构缺失 **计划级别 (Plan-Level)** 的状态管理：

- 计划执行期间产生的事实、里程碑、用户反馈无法持久化
- 切换计划时上下文丢失
- 无法区分"计划特定的偏好调整"与"用户全局偏好"
- 无法实现计划间的经验迁移

### 1.3 设计目标

引入 `PlanScope` 层，实现：

1. **最小侵入**: 不改变现有 `ContextPack` 结构，仅扩展注入源
2. **清晰边界**: 明确 Plan 级状态与 User 级状态的职责划分
3. **可追溯**: 支持状态版本控制和变更审计
4. **高效缓存**: Redis 优先读取，DB 持久化兜底

---

## 2. PlanScope 最小字段定义

### 2.1 核心字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `plan_id` | UUID | Y | - | 主键，关联 `plans.id` |
| `user_id` | UUID | Y | - | 所属用户，用于权限隔离 |
| `facts` | JSONB | N | `{}` | 计划执行期间收集的事实 |
| `milestones` | JSONB | N | `[]` | 里程碑记录 |
| `task_index` | JSONB | N | `{}` | 任务完成情况索引 |
| `feedback_log` | JSONB | N | `[]` | 用户反馈历史 |
| `constraints` | JSONB | N | `{}` | 运行时约束 |
| `version` | INT | Y | `1` | 乐观锁版本号 |
| `status` | ENUM | Y | `active` | 状态: `active` / `archived` |
| `archived_at` | DATETIME | N | `null` | 归档时间 |
| `created_at` | DATETIME | Y | `now()` | 创建时间 |
| `updated_at` | DATETIME | Y | `now()` | 最后更新时间 |

### 2.2 字段详细定义

#### 2.2.1 `facts` - 事实存储

```json
{
  "learning_style_override": "visual",       // 计划特定的学习风格调整
  "difficulty_preference": 0.7,              // 当前计划的难度偏好
  "avg_task_duration_minutes": 23,           // 实际平均任务时长
  "preferred_time_slots": ["09:00-11:00"],   // 偏好时间段
  "weak_points": ["概率论", "积分"],          // 薄弱点识别
  "strong_points": ["线性代数"]              // 强项识别
}
```

#### 2.2.2 `milestones` - 里程碑记录

```json
[
  {
    "id": "ms-001",
    "title": "完成第一章基础知识",
    "achieved_at": "2026-01-15T10:30:00Z",
    "tasks_completed": 5,
    "mastery_level": 0.75
  },
  {
    "id": "ms-002",
    "title": "第一次模拟测试",
    "achieved_at": "2026-01-20T14:00:00Z",
    "score": 78,
    "feedback": "需要加强概率部分"
  }
]
```

#### 2.2.3 `task_index` - 任务完成索引

```json
{
  "total": 25,
  "completed": 12,
  "in_progress": 2,
  "abandoned": 1,
  "by_type": {
    "LEARNING": { "total": 15, "completed": 8 },
    "TRAINING": { "total": 8, "completed": 4 },
    "ERROR_FIX": { "total": 2, "completed": 0 }
  },
  "avg_completion_rate": 0.48,
  "last_completed_task_id": "task-uuid-123"
}
```

#### 2.2.4 `feedback_log` - 反馈历史

```json
[
  {
    "id": "fb-001",
    "timestamp": "2026-01-18T15:00:00Z",
    "type": "task_difficulty",
    "task_id": "task-uuid-456",
    "content": "任务太难了",
    "sentiment": "negative",
    "applied_adjustment": { "difficulty_preference": -0.1 }
  },
  {
    "id": "fb-002",
    "timestamp": "2026-01-19T09:30:00Z",
    "type": "schedule_preference",
    "content": "下午效率更高",
    "applied_adjustment": { "preferred_time_slots": ["14:00-18:00"] }
  }
]
```

#### 2.2.5 `constraints` - 运行时约束

```json
{
  "daily_task_limit": 5,                    // 每日任务上限
  "min_break_minutes": 10,                   // 最小休息时间
  "deadline": "2026-02-15",                  // 硬性截止日期
  "blocked_time_slots": ["12:00-13:00"],     // 不可用时间段
  "priority_tags": ["必考", "高频"]           // 优先标签
}
```

---

## 3. 写入触发点

### 3.1 触发事件清单

| 触发点 | 触发时机 | 更新字段 | 版本递增 |
|--------|----------|----------|----------|
| **任务完成** | `Task.status` -> `COMPLETED` | `task_index`, `milestones`(条件) | Y |
| **任务更新** | `Task.status` 变更 | `task_index` | Y |
| **用户反馈** | 用户提交反馈 | `feedback_log`, `facts`(可选) | Y |
| **方案变更** | 计划参数调整 | `constraints`, `facts` | Y |
| **里程碑达成** | 进度触发/手动标记 | `milestones` | Y |
| **计划切换** | 激活其他计划 | 当前计划 `status` -> `archived` | N |
| **计划归档** | 用户手动归档 | `status`, `archived_at` | N |

### 3.2 触发点实现位置

```python
# 任务完成触发
# Location: backend/app/services/task_service.py::complete_task()
async def complete_task(task_id: UUID, ...):
    # 1. 更新任务状态
    task.status = TaskStatus.COMPLETED
    # 2. 触发 PlanState 更新
    if task.plan_id:
        await plan_state_service.on_task_completed(task)

# 用户反馈触发
# Location: backend/app/services/feedback_service.py::submit_feedback()
async def submit_feedback(plan_id: UUID, feedback: FeedbackInput):
    # 1. 记录反馈
    # 2. 触发 PlanState 更新
    await plan_state_service.append_feedback(plan_id, feedback)

# 方案变更触发
# Location: backend/app/services/plan_service.py::update_plan()
async def update_plan(plan_id: UUID, updates: PlanUpdate):
    # 1. 更新计划
    # 2. 触发约束同步
    await plan_state_service.sync_constraints(plan_id, updates)
```

### 3.3 事件驱动模式（推荐）

使用领域事件解耦触发逻辑：

```python
# Event Definitions
class TaskCompletedEvent:
    task_id: UUID
    plan_id: Optional[UUID]
    completed_at: datetime

class FeedbackSubmittedEvent:
    plan_id: UUID
    feedback_type: str
    content: str

# Event Handler
class PlanStateEventHandler:
    async def handle_task_completed(self, event: TaskCompletedEvent):
        if event.plan_id:
            await self.plan_state_service.on_task_completed(event.task_id)
```

---

## 4. 状态值示例

### 4.1 输入示例

**场景**: 用户完成了一个任务，触发状态更新

```json
// 输入: TaskCompletedEvent
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "plan_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_type": "LEARNING",
  "actual_minutes": 28,
  "difficulty_rating": 4
}
```

### 4.2 更新前状态

```json
{
  "plan_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-uuid-123",
  "facts": {
    "avg_task_duration_minutes": 25,
    "difficulty_preference": 0.5
  },
  "task_index": {
    "total": 20,
    "completed": 10,
    "by_type": {
      "LEARNING": { "total": 12, "completed": 6 }
    }
  },
  "milestones": [],
  "feedback_log": [],
  "constraints": {},
  "version": 5,
  "status": "active"
}
```

### 4.3 更新后状态

```json
{
  "plan_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-uuid-123",
  "facts": {
    "avg_task_duration_minutes": 25.3,  // 重新计算: (25*10 + 28) / 11
    "difficulty_preference": 0.5
  },
  "task_index": {
    "total": 20,
    "completed": 11,                     // +1
    "by_type": {
      "LEARNING": { "total": 12, "completed": 7 }  // +1
    },
    "avg_completion_rate": 0.55,
    "last_completed_task_id": "550e8400-e29b-41d4-a716-446655440001"
  },
  "milestones": [],
  "feedback_log": [],
  "constraints": {},
  "version": 6,                          // +1
  "status": "active",
  "updated_at": "2026-01-24T10:30:00Z"
}
```

### 4.4 里程碑触发示例

当 `task_index.completed >= 10` 且 `milestones` 中没有 "first-10-tasks" 里程碑时：

```json
{
  "milestones": [
    {
      "id": "ms-first-10-tasks",
      "title": "完成前 10 个任务",
      "achieved_at": "2026-01-24T10:30:00Z",
      "tasks_completed": 10,
      "mastery_level": 0.45
    }
  ]
}
```

---

## 5. plan_id 缺失时的降级行为

### 5.1 降级场景

| 场景 | 行为 | 说明 |
|------|------|------|
| **无活跃计划** | 仅使用 UserScope | 用户未创建任何计划 |
| **计划已归档** | 使用归档快照（只读） | 历史计划回顾 |
| **plan_id 无效** | 回退到 UserScope + 告警 | 数据一致性问题 |

### 5.2 降级策略代码

```python
async def get_effective_scope(
    user_id: UUID,
    plan_id: Optional[UUID] = None,
) -> EffectiveScope:
    """
    获取有效的上下文范围

    优先级: PlanScope > UserScope
    """
    user_scope = await self.get_user_scope(user_id)

    if not plan_id:
        # 场景1: 无 plan_id，仅使用 UserScope
        return EffectiveScope(
            user=user_scope,
            plan=None,
            source="user_only"
        )

    plan_state = await self.plan_state_service.get_plan_state(
        user_id=user_id,
        plan_id=plan_id,
        refresh=False
    )

    if plan_state is None:
        # 场景3: plan_id 无效
        logger.warning(f"Invalid plan_id {plan_id} for user {user_id}")
        return EffectiveScope(
            user=user_scope,
            plan=None,
            source="user_fallback"
        )

    if plan_state.status == "archived":
        # 场景2: 已归档计划
        return EffectiveScope(
            user=user_scope,
            plan=plan_state,  # 只读
            source="archived_plan",
            read_only=True
        )

    # 正常情况: 合并 PlanScope + UserScope
    return EffectiveScope(
        user=user_scope,
        plan=plan_state,
        source="active_plan"
    )
```

---

## 6. PlanScope 与 UserScope 的边界

### 6.1 状态归属原则

| 状态类型 | 归属 | 示例 |
|----------|------|------|
| **全局偏好** | UserScope | 语言、时区、通知设置 |
| **计划特定偏好** | PlanScope | 当前计划的难度调整 |
| **行为模式** | UserScope | 拖延模式、专注模式 |
| **计划进度** | PlanScope | 任务完成情况 |
| **学习记忆** | UserScope | 情景记忆、目标 |
| **计划反馈** | PlanScope | 针对当前计划的反馈 |

### 6.2 上浮规则 (PlanScope -> UserScope)

当以下条件满足时，PlanScope 中的状态应上浮到 UserScope：

```python
# 上浮条件
PROMOTION_RULES = {
    "difficulty_preference": {
        # 条件: 连续 3 个计划的 difficulty_preference 偏差 < 0.1
        "min_plans": 3,
        "max_variance": 0.1,
        "target_field": "inferred.difficulty_preference"
    },
    "preferred_time_slots": {
        # 条件: 80% 以上计划使用相同时间段
        "min_plans": 5,
        "consistency_threshold": 0.8,
        "target_field": "inferred.active_slots"
    },
    "weak_points": {
        # 条件: 多个计划识别出相同薄弱点
        "min_occurrences": 3,
        "target_field": "memory_goals"  # 创建目标
    }
}
```

### 6.3 归档规则

计划归档时的状态处理：

```python
async def archive_plan_state(plan_id: UUID) -> None:
    state = await self.get_plan_state(plan_id)

    # 1. 检查是否有可上浮的状态
    promotable = self._extract_promotable_facts(state)
    if promotable:
        await self.promote_to_user_scope(state.user_id, promotable)

    # 2. 创建归档快照
    await self.create_archive_snapshot(state)

    # 3. 更新状态
    state.status = "archived"
    state.archived_at = datetime.utcnow()
    await self.upsert_plan_state(state)

    # 4. 清理缓存
    await self.invalidate_plan_cache(plan_id)
```

### 6.4 继承规则 (新计划从 UserScope 继承)

创建新计划时，从 UserScope 继承初始状态：

```python
async def create_plan_state(
    user_id: UUID,
    plan_id: UUID,
) -> PlanState:
    # 从 UserScope 获取可继承的初始值
    user_prefs = await self.pref_service.get_preferences(user_id)

    initial_facts = {
        "difficulty_preference": user_prefs.inferred.get(
            "difficulty_preference", 0.5
        ),
        "preferred_time_slots": user_prefs.explicit.get(
            "active_slots", []
        ),
    }

    return PlanState(
        plan_id=plan_id,
        user_id=user_id,
        facts=initial_facts,
        milestones=[],
        task_index={"total": 0, "completed": 0, "by_type": {}},
        feedback_log=[],
        constraints={},
        version=1,
        status="active",
    )
```

---

## 7. 数据库设计 (预览)

> **注意**: 阶段 0 不创建迁移，仅提供设计参考

### 7.1 表结构

```sql
CREATE TABLE plan_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL UNIQUE REFERENCES plans(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),

    facts JSONB NOT NULL DEFAULT '{}',
    milestones JSONB NOT NULL DEFAULT '[]',
    task_index JSONB NOT NULL DEFAULT '{}',
    feedback_log JSONB NOT NULL DEFAULT '[]',
    constraints JSONB NOT NULL DEFAULT '{}',

    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    archived_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_status CHECK (status IN ('active', 'archived'))
);

-- 索引
CREATE INDEX idx_plan_states_user_id ON plan_states(user_id);
CREATE INDEX idx_plan_states_status ON plan_states(status);
CREATE INDEX idx_plan_states_plan_id ON plan_states(plan_id);
CREATE INDEX idx_plan_states_updated_at ON plan_states(updated_at);
```

### 7.2 Redis 缓存设计

```
Key: state:plan:{plan_id}
Value: JSON序列化的 PlanState
TTL: 3600 (1小时)
```

---

## 8. 附录

### 8.1 现有信息流图

```
┌──────────────────────────────────────────────────────────────────┐
│                         UserScope (现有)                          │
├──────────────────────────────────────────────────────────────────┤
│  UserPreferencesCenter                                            │
│    ├── explicit: { depth_pref, curiosity_pref, ... }             │
│    └── inferred: { consecutive_ignores, ... }                    │
│                                                                   │
│  MemoryPreference / MemoryGoal / EpisodicMemory                  │
│    └── evidence_score, version, ...                              │
│                                                                   │
│  RuntimeContext                                                   │
│    └── focus_active, pending_tasks, local_hour, ...              │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                      ContextPackBuilder                           │
│  build(user_id, intent) → ContextPack                             │
│    ├── preferences: trimmed by budget                            │
│    ├── goals: ranked & trimmed                                   │
│    └── episodic_memories: ranked & trimmed                       │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                      PersonalizationEngine                        │
│  get_llm_profile(user_id) → LLMProfile                           │
│  get_push_policy_profile(user_id) → PushPolicyProfile            │
│  get_task_plan_profile(user_id) → TaskPlanProfile                │
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 引入 PlanScope 后的信息流图

```
┌──────────────────────────────────────────────────────────────────┐
│                         UserScope (现有)                          │
└───────────────────────────────┬──────────────────────────────────┘
                                │
┌──────────────────────────────────────────────────────────────────┐
│                         PlanScope (新增)                          │
├──────────────────────────────────────────────────────────────────┤
│  PlanState                                                        │
│    ├── facts: { difficulty_pref_override, weak_points, ... }     │
│    ├── milestones: [ { title, achieved_at, ... } ]               │
│    ├── task_index: { total, completed, by_type, ... }            │
│    ├── feedback_log: [ { type, content, adjustment, ... } ]      │
│    └── constraints: { deadline, daily_limit, ... }               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                  EffectiveScopeBuilder (新增)                     │
│  build(user_id, plan_id) → EffectiveScope                        │
│    ├── merge UserScope + PlanScope                               │
│    └── apply injection_merge_rules                               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│              ContextPackBuilder (扩展注入源)                       │
│              PersonalizationEngine (扩展注入源)                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 9. 变更历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-01-24 | 初始版本 | Claude |
