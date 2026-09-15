# 注入合并规则设计文档

> **版本**: 1.0.0
> **状态**: Draft
> **最后更新**: 2026-01-24
> **依赖文档**: [plan_state_spec.md](./plan_state_spec.md)

---

## 1. 概述

本文档定义了 `PlanScope`、`UserScope` 和 `RuntimeContext` 三层状态在注入到 `ContextPack` 时的合并规则。

### 1.1 状态层级

```
┌─────────────────────────────────────────────┐
│  RuntimeContext (运行时)                     │  ← 最高优先级
│  - focus_active, local_hour, etc.           │
├─────────────────────────────────────────────┤
│  PlanScope (计划级)                          │  ← 中优先级
│  - facts, constraints, etc.                 │
├─────────────────────────────────────────────┤
│  UserScope (用户级)                          │  ← 基础
│  - preferences, goals, episodic, etc.       │
└─────────────────────────────────────────────┘
```

### 1.2 核心原则

1. **Runtime > Plan > User**: 运行时状态覆盖计划状态，计划状态覆盖用户状态
2. **显式 > 推断**: 用户显式设置的值优先于系统推断的值
3. **近期 > 远期**: 更新时间更近的状态优先
4. **安全降级**: 任何层级缺失时，安全回退到下一层级

---

## 2. 合并优先级矩阵

### 2.1 偏好类字段

| 字段 | Runtime | PlanScope | UserScope.explicit | UserScope.inferred | 默认值 |
|------|---------|-----------|-------------------|-------------------|--------|
| `difficulty_preference` | - | facts.difficulty_preference | depth_preference | depth_preference | 0.5 |
| `verbosity` | - | - | ai_verbosity | - | "balanced" |
| `time_slots` | blocked_times | constraints.blocked_time_slots | active_slots | - | [] |
| `daily_task_limit` | - | constraints.daily_task_limit | daily_cap | - | 5 |
| `focus_duration` | - | - | focus_duration_preference | - | 25 |

### 2.2 状态类字段

| 字段 | Runtime | PlanScope | UserScope | 说明 |
|------|---------|-----------|-----------|------|
| `is_focusing` | focus_session_active | - | - | 仅从运行时获取 |
| `current_plan_progress` | - | task_index.avg_completion_rate | - | 仅从计划获取 |
| `pending_tasks` | pending_task_count | - | - | 仅从运行时获取 |
| `weak_points` | - | facts.weak_points | memory_goals.tagged("weak") | 合并两者 |

---

## 3. 合并算法

### 3.1 基础合并器

```python
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class Source(Enum):
    RUNTIME = "runtime"
    PLAN_EXPLICIT = "plan_explicit"
    PLAN_INFERRED = "plan_inferred"
    USER_EXPLICIT = "user_explicit"
    USER_INFERRED = "user_inferred"
    DEFAULT = "default"

@dataclass
class MergedValue:
    """合并后的值，带来源标记"""
    value: Any
    source: Source
    confidence: float = 1.0

class InjectionMerger:
    """
    注入合并器 - 实现多层状态合并逻辑
    """

    # 优先级顺序（从高到低）
    PRIORITY_ORDER = [
        Source.RUNTIME,
        Source.PLAN_EXPLICIT,
        Source.USER_EXPLICIT,
        Source.PLAN_INFERRED,
        Source.USER_INFERRED,
        Source.DEFAULT,
    ]

    def merge_scalar(
        self,
        field: str,
        runtime_value: Optional[Any] = None,
        plan_value: Optional[Any] = None,
        plan_inferred: Optional[Any] = None,
        user_explicit: Optional[Any] = None,
        user_inferred: Optional[Any] = None,
        default: Any = None,
    ) -> MergedValue:
        """
        合并标量值

        按优先级顺序查找第一个非空值
        """
        candidates = [
            (Source.RUNTIME, runtime_value),
            (Source.PLAN_EXPLICIT, plan_value),
            (Source.USER_EXPLICIT, user_explicit),
            (Source.PLAN_INFERRED, plan_inferred),
            (Source.USER_INFERRED, user_inferred),
            (Source.DEFAULT, default),
        ]

        for source, value in candidates:
            if value is not None:
                return MergedValue(
                    value=value,
                    source=source,
                    confidence=self._get_confidence(source)
                )

        return MergedValue(value=default, source=Source.DEFAULT, confidence=0.5)

    def merge_dict(
        self,
        runtime: Dict = None,
        plan: Dict = None,
        user: Dict = None,
        default: Dict = None,
    ) -> Dict:
        """
        合并字典值

        深度合并，高优先级的键覆盖低优先级
        """
        result = (default or {}).copy()

        # 逐层覆盖
        for layer in [user, plan, runtime]:
            if layer:
                self._deep_merge(result, layer)

        return result

    def merge_list(
        self,
        runtime: List = None,
        plan: List = None,
        user: List = None,
        strategy: str = "union",  # "union", "replace", "intersect"
    ) -> List:
        """
        合并列表值

        策略:
        - union: 取并集（去重）
        - replace: 高优先级完全替换
        - intersect: 取交集
        """
        if strategy == "replace":
            return runtime or plan or user or []

        lists = [l for l in [user, plan, runtime] if l]
        if not lists:
            return []

        if strategy == "union":
            seen = set()
            result = []
            for lst in lists:
                for item in lst:
                    key = self._get_item_key(item)
                    if key not in seen:
                        seen.add(key)
                        result.append(item)
            return result

        if strategy == "intersect":
            if len(lists) < 2:
                return lists[0] if lists else []
            result = set(map(self._get_item_key, lists[0]))
            for lst in lists[1:]:
                result &= set(map(self._get_item_key, lst))
            return [item for item in lists[0] if self._get_item_key(item) in result]

        return []

    def _deep_merge(self, base: Dict, overlay: Dict) -> None:
        """深度合并字典"""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _get_confidence(self, source: Source) -> float:
        """根据来源返回置信度"""
        confidence_map = {
            Source.RUNTIME: 1.0,
            Source.PLAN_EXPLICIT: 0.95,
            Source.USER_EXPLICIT: 0.9,
            Source.PLAN_INFERRED: 0.7,
            Source.USER_INFERRED: 0.6,
            Source.DEFAULT: 0.5,
        }
        return confidence_map.get(source, 0.5)

    def _get_item_key(self, item: Any) -> str:
        """获取列表项的唯一键"""
        if isinstance(item, dict):
            return item.get("id") or item.get("key") or str(item)
        return str(item)
```

### 3.2 ContextPack 注入实现

```python
class EffectiveScopeBuilder:
    """
    有效范围构建器 - 整合多层状态
    """

    def __init__(
        self,
        pref_service: PreferenceService,
        runtime_service: RuntimeContextService,
        plan_state_service: PlanStateService,
    ):
        self.pref_service = pref_service
        self.runtime_service = runtime_service
        self.plan_state_service = plan_state_service
        self.merger = InjectionMerger()

    async def build(
        self,
        user_id: UUID,
        plan_id: Optional[UUID] = None,
        intent: str = "default",
    ) -> EffectiveScope:
        """
        构建有效范围

        合并顺序: Runtime > Plan > User > Default
        """
        # 1. 获取各层状态
        user_prefs = await self.pref_service.get_preferences(user_id)
        runtime = await self.runtime_service.get_runtime_context(
            user_id,
            user_prefs.explicit.get("timezone", "Asia/Shanghai")
        )

        plan_state = None
        if plan_id:
            plan_state = await self.plan_state_service.get_plan_state(
                user_id=user_id,
                plan_id=plan_id,
            )

        # 2. 合并偏好
        merged_prefs = self._merge_preferences(
            runtime=runtime,
            plan=plan_state,
            user=user_prefs,
        )

        # 3. 合并约束
        merged_constraints = self._merge_constraints(
            runtime=runtime,
            plan=plan_state,
            user=user_prefs,
        )

        # 4. 合并上下文
        merged_context = self._merge_context(
            runtime=runtime,
            plan=plan_state,
            user=user_prefs,
        )

        return EffectiveScope(
            user_id=user_id,
            plan_id=plan_id,
            preferences=merged_prefs,
            constraints=merged_constraints,
            context=merged_context,
            source_metadata=self._build_source_metadata(runtime, plan_state, user_prefs),
        )

    def _merge_preferences(
        self,
        runtime: Dict,
        plan: Optional[PlanState],
        user: UserPreferencesCenter,
    ) -> Dict:
        """合并偏好设置"""
        plan_facts = (plan.facts if plan else {}) or {}

        return {
            "difficulty_preference": self.merger.merge_scalar(
                "difficulty_preference",
                plan_value=plan_facts.get("difficulty_preference"),
                user_explicit=user.explicit.get("depth_preference"),
                user_inferred=user.inferred.get("depth_preference") if user.inferred else None,
                default=0.5,
            ).value,

            "verbosity": self.merger.merge_scalar(
                "verbosity",
                user_explicit=user.explicit.get("ai_verbosity"),
                default="balanced",
            ).value,

            "exploration_level": self.merger.merge_scalar(
                "exploration_level",
                plan_value=plan_facts.get("exploration_preference"),
                user_explicit=user.explicit.get("curiosity_preference"),
                user_inferred=user.inferred.get("curiosity_preference") if user.inferred else None,
                default=0.5,
            ).value,

            "learning_style": self.merger.merge_scalar(
                "learning_style",
                plan_value=plan_facts.get("learning_style_override"),
                user_explicit=user.explicit.get("learning_style"),
                default="balanced",
            ).value,

            "focus_duration": self.merger.merge_scalar(
                "focus_duration",
                user_explicit=user.explicit.get("focus_duration_preference"),
                default=25,
            ).value,
        }

    def _merge_constraints(
        self,
        runtime: Dict,
        plan: Optional[PlanState],
        user: UserPreferencesCenter,
    ) -> Dict:
        """合并约束条件"""
        plan_constraints = (plan.constraints if plan else {}) or {}
        user_slots = user.explicit.get("active_slots", [])
        if isinstance(user_slots, dict):
            user_slots = user_slots.get("slots", [])

        # 时间段: 计划约束的阻塞时间 + 用户偏好时间
        blocked_slots = plan_constraints.get("blocked_time_slots", [])

        return {
            "daily_task_limit": self.merger.merge_scalar(
                "daily_task_limit",
                plan_value=plan_constraints.get("daily_task_limit"),
                user_explicit=user.explicit.get("daily_cap"),
                default=5,
            ).value,

            "deadline": plan_constraints.get("deadline"),

            "active_time_slots": self.merger.merge_list(
                plan=plan_constraints.get("preferred_time_slots", []),
                user=user_slots,
                strategy="union",
            ),

            "blocked_time_slots": blocked_slots,

            "priority_tags": plan_constraints.get("priority_tags", []),

            "min_break_minutes": plan_constraints.get("min_break_minutes", 5),
        }

    def _merge_context(
        self,
        runtime: Dict,
        plan: Optional[PlanState],
        user: UserPreferencesCenter,
    ) -> Dict:
        """合并上下文信息"""
        task_index = (plan.task_index if plan else {}) or {}

        return {
            # 运行时状态（仅 Runtime 提供）
            "is_focusing": runtime.get("focus_session_active", False),
            "current_local_hour": runtime.get("current_local_hour"),
            "pending_task_count": runtime.get("pending_task_count", 0),
            "last_activity_minutes_ago": runtime.get("last_activity_minutes_ago"),

            # 计划状态（仅 Plan 提供）
            "plan_progress": task_index.get("avg_completion_rate"),
            "tasks_completed": task_index.get("completed", 0),
            "tasks_total": task_index.get("total", 0),
            "weak_points": (plan.facts.get("weak_points", []) if plan and plan.facts else []),
            "recent_milestones": (plan.milestones[-3:] if plan and plan.milestones else []),
        }

    def _build_source_metadata(
        self,
        runtime: Dict,
        plan: Optional[PlanState],
        user: UserPreferencesCenter,
    ) -> Dict:
        """构建来源元数据（用于调试）"""
        return {
            "runtime_available": bool(runtime),
            "plan_available": plan is not None,
            "plan_status": plan.status if plan else None,
            "plan_version": plan.version if plan else None,
            "user_pref_version": user.version,
            "merged_at": datetime.utcnow().isoformat(),
        }
```

---

## 4. 字段级合并规则详解

### 4.1 难度偏好 (difficulty_preference)

```python
# 合并规则
difficulty = merger.merge_scalar(
    "difficulty_preference",
    # Plan 可以临时覆盖难度设置
    plan_value=plan_facts.get("difficulty_preference"),
    # User 显式设置的深度偏好
    user_explicit=user.explicit.get("depth_preference"),
    # User 推断的深度偏好（基于历史行为）
    user_inferred=user.inferred.get("depth_preference"),
    default=0.5,
)
```

**合并示例**:

| Plan.facts.difficulty_preference | User.explicit.depth_preference | User.inferred.depth_preference | 结果 | 来源 |
|----------------------------------|-------------------------------|-------------------------------|------|------|
| 0.8 | 0.5 | 0.6 | 0.8 | plan_explicit |
| None | 0.5 | 0.6 | 0.5 | user_explicit |
| None | None | 0.6 | 0.6 | user_inferred |
| None | None | None | 0.5 | default |

### 4.2 时间段约束 (time_slots)

```python
# 合并规则: 并集策略
active_slots = merger.merge_list(
    # 计划级偏好时间
    plan=plan_constraints.get("preferred_time_slots", []),
    # 用户级偏好时间
    user=user_prefs.explicit.get("active_slots", []),
    strategy="union",  # 取并集
)

# 阻塞时间: 仅从计划获取（不与用户合并）
blocked_slots = plan_constraints.get("blocked_time_slots", [])
```

**合并示例**:

| Plan.constraints.preferred_time_slots | User.explicit.active_slots | 结果 |
|--------------------------------------|---------------------------|------|
| ["09:00-11:00"] | ["14:00-16:00"] | ["09:00-11:00", "14:00-16:00"] |
| [] | ["14:00-16:00"] | ["14:00-16:00"] |
| ["09:00-11:00"] | [] | ["09:00-11:00"] |

### 4.3 薄弱点识别 (weak_points)

```python
# 合并规则: 并集 + 去重
weak_points = merger.merge_list(
    # 计划中识别的薄弱点
    plan=plan_facts.get("weak_points", []),
    # 用户目标中标记的薄弱点
    user=[g.title for g in user_goals if "weak" in (g.tags or [])],
    strategy="union",
)
```

### 4.4 专注状态 (is_focusing)

```python
# 仅从运行时获取，不合并
is_focusing = runtime.get("focus_session_active", False)
```

---

## 5. 冲突解决策略

### 5.1 显式冲突

当 Plan 和 User 都有显式设置时：

```python
def resolve_explicit_conflict(
    field: str,
    plan_value: Any,
    user_value: Any,
    plan_updated_at: datetime,
    user_updated_at: datetime,
) -> Tuple[Any, str]:
    """
    解决显式冲突

    规则: 更新时间更近的优先
    """
    if plan_updated_at >= user_updated_at:
        return plan_value, "plan_explicit"
    else:
        return user_value, "user_explicit"
```

### 5.2 类型冲突

当不同层级的值类型不一致时：

```python
def resolve_type_conflict(
    field: str,
    values: List[Tuple[Source, Any]],
) -> Any:
    """
    解决类型冲突

    规则: 使用第一个类型正确的值
    """
    expected_type = FIELD_TYPES.get(field, str)

    for source, value in values:
        if isinstance(value, expected_type):
            return value

    return FIELD_DEFAULTS.get(field)
```

### 5.3 范围冲突

当合并后的值超出有效范围时：

```python
FIELD_RANGES = {
    "difficulty_preference": (0.0, 1.0),
    "daily_task_limit": (1, 20),
    "focus_duration": (5, 120),
}

def clamp_to_range(field: str, value: float) -> float:
    """将值限制在有效范围内"""
    range_spec = FIELD_RANGES.get(field)
    if range_spec:
        min_val, max_val = range_spec
        return max(min_val, min(max_val, value))
    return value
```

---

## 6. ContextPackBuilder 集成示例

### 6.1 扩展 build 方法

```python
class ContextPackBuilder:
    """
    扩展后的 ContextPackBuilder，支持 PlanScope 注入
    """

    def __init__(
        self,
        db: AsyncSession,
        scheduler: Optional[ContextBudgetScheduler] = None,
        plan_state_service: Optional[PlanStateService] = None,
    ) -> None:
        self.db = db
        self.memory_service = MemoryService(db)
        self.scheduler = scheduler or ContextBudgetScheduler(db=db)
        self.plan_state_service = plan_state_service
        self.scope_builder = EffectiveScopeBuilder(...)  # 注入依赖

    async def build(
        self,
        user_id: UUID,
        intent: str,
        plan_id: Optional[UUID] = None,  # 新增参数
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> ContextPack:
        """
        构建上下文包

        如果提供 plan_id，则合并 PlanScope
        """
        # 1. 获取有效范围
        effective_scope = None
        if plan_id and self.plan_state_service:
            effective_scope = await self.scope_builder.build(
                user_id=user_id,
                plan_id=plan_id,
                intent=intent,
            )

        # 2. 原有逻辑...
        budgets = await self.scheduler.allocate(intent, user_id=user_id)
        # ...

        # 3. 合并 PlanScope 到 metadata
        metadata = {}
        if effective_scope:
            metadata["plan_context"] = {
                "plan_id": str(plan_id),
                "progress": effective_scope.context.get("plan_progress"),
                "weak_points": effective_scope.context.get("weak_points"),
                "constraints": effective_scope.constraints,
            }

        # 4. 返回扩展后的 ContextPack
        return ContextPack(
            user_id=user_id,
            intent=intent,
            preferences=trimmed_preferences,
            goals=trimmed_goals,
            episodic_memories=trimmed_episodic,
            budgets=budgets,
            token_usage=token_usage,
            budget_remaining=budget_remaining,
            pack_id=pack_id,
            metadata=metadata or None,
        )
```

### 6.2 PersonalizationEngine 集成

```python
class PersonalizationEngine:
    """
    扩展后的 PersonalizationEngine，支持 PlanScope
    """

    async def get_llm_profile(
        self,
        user_id: UUID,
        plan_id: Optional[UUID] = None,  # 新增参数
        session_context: Optional[Dict] = None,
        override_preferences: Optional[Dict] = None,
    ) -> LLMProfile:
        """
        生成 AI 系统策略配置

        如果提供 plan_id，则考虑计划级覆盖
        """
        # 1. 获取有效范围
        if plan_id:
            scope = await self.scope_builder.build(user_id, plan_id)
            effective_prefs = scope.preferences
        else:
            prefs = await self.pref_service.get_preferences(user_id)
            effective_prefs = {
                "difficulty_preference": prefs.explicit.get("depth_preference", 0.5),
                "exploration_level": prefs.explicit.get("curiosity_preference", 0.5),
            }

        # 2. 应用覆盖
        if override_preferences:
            effective_prefs.update(override_preferences)

        # 3. 生成 LLMProfile
        depth = effective_prefs.get("difficulty_preference", 0.5)
        exploration = effective_prefs.get("exploration_level", 0.5)

        verbosity = "detailed" if depth > 0.7 else ("concise" if depth < 0.3 else "balanced")
        exploration_level = "exploratory" if exploration > 0.7 else ("focused" if exploration < 0.3 else "moderate")

        # ... 其余逻辑
```

---

## 7. 输入输出示例

### 7.1 完整合并示例

**输入**:

```json
// RuntimeContext
{
  "focus_session_active": true,
  "current_local_hour": 10,
  "pending_task_count": 3,
  "last_activity_minutes_ago": 15
}

// PlanState
{
  "plan_id": "plan-uuid-123",
  "facts": {
    "difficulty_preference": 0.7,
    "learning_style_override": "visual",
    "weak_points": ["概率论"]
  },
  "constraints": {
    "daily_task_limit": 8,
    "blocked_time_slots": ["12:00-13:00"],
    "deadline": "2026-02-15"
  },
  "task_index": {
    "total": 20,
    "completed": 12,
    "avg_completion_rate": 0.6
  }
}

// UserPreferencesCenter
{
  "explicit": {
    "depth_preference": 0.5,
    "curiosity_preference": 0.6,
    "daily_cap": 5,
    "active_slots": [{"start_min": 540, "end_min": 660}]
  },
  "inferred": {
    "depth_preference": 0.55
  }
}
```

**输出** (EffectiveScope):

```json
{
  "user_id": "user-uuid-456",
  "plan_id": "plan-uuid-123",

  "preferences": {
    "difficulty_preference": 0.7,        // 来源: plan_explicit
    "verbosity": "balanced",             // 来源: user_explicit (无plan覆盖)
    "exploration_level": 0.6,            // 来源: user_explicit
    "learning_style": "visual",          // 来源: plan_explicit
    "focus_duration": 25                 // 来源: default
  },

  "constraints": {
    "daily_task_limit": 8,               // 来源: plan_explicit
    "deadline": "2026-02-15",            // 来源: plan_explicit
    "active_time_slots": [
      {"start_min": 540, "end_min": 660}
    ],
    "blocked_time_slots": ["12:00-13:00"],
    "priority_tags": [],
    "min_break_minutes": 5
  },

  "context": {
    "is_focusing": true,                 // 来源: runtime
    "current_local_hour": 10,            // 来源: runtime
    "pending_task_count": 3,             // 来源: runtime
    "plan_progress": 0.6,                // 来源: plan
    "tasks_completed": 12,               // 来源: plan
    "tasks_total": 20,                   // 来源: plan
    "weak_points": ["概率论"],            // 来源: plan
    "recent_milestones": []              // 来源: plan
  },

  "source_metadata": {
    "runtime_available": true,
    "plan_available": true,
    "plan_status": "active",
    "plan_version": 5,
    "user_pref_version": 3,
    "merged_at": "2026-01-24T10:30:00Z"
  }
}
```

### 7.2 降级示例（无 PlanScope）

**输入**:

```json
// plan_id = null

// RuntimeContext
{
  "focus_session_active": false,
  "current_local_hour": 14
}

// UserPreferencesCenter
{
  "explicit": {
    "depth_preference": 0.5,
    "daily_cap": 5
  },
  "inferred": {}
}
```

**输出**:

```json
{
  "user_id": "user-uuid-456",
  "plan_id": null,

  "preferences": {
    "difficulty_preference": 0.5,        // 来源: user_explicit
    "verbosity": "balanced",             // 来源: default
    "exploration_level": 0.5,            // 来源: default
    "learning_style": "balanced",        // 来源: default
    "focus_duration": 25                 // 来源: default
  },

  "constraints": {
    "daily_task_limit": 5,               // 来源: user_explicit
    "deadline": null,
    "active_time_slots": [],
    "blocked_time_slots": [],
    "priority_tags": [],
    "min_break_minutes": 5
  },

  "context": {
    "is_focusing": false,
    "current_local_hour": 14,
    "pending_task_count": 0,
    "plan_progress": null,               // 无计划
    "tasks_completed": 0,
    "tasks_total": 0,
    "weak_points": [],
    "recent_milestones": []
  },

  "source_metadata": {
    "runtime_available": true,
    "plan_available": false,
    "plan_status": null,
    "plan_version": null,
    "user_pref_version": 2,
    "merged_at": "2026-01-24T10:30:00Z"
  }
}
```

---

## 8. 测试用例

### 8.1 单元测试覆盖点

```python
class TestInjectionMerger:
    """合并器测试"""

    def test_merge_scalar_priority_order(self):
        """测试标量合并优先级"""
        merger = InjectionMerger()

        # Runtime > Plan
        result = merger.merge_scalar(
            "test",
            runtime_value=1,
            plan_value=2,
        )
        assert result.value == 1
        assert result.source == Source.RUNTIME

        # Plan > User Explicit
        result = merger.merge_scalar(
            "test",
            plan_value=2,
            user_explicit=3,
        )
        assert result.value == 2
        assert result.source == Source.PLAN_EXPLICIT

    def test_merge_scalar_fallback(self):
        """测试标量合并降级"""
        merger = InjectionMerger()

        result = merger.merge_scalar(
            "test",
            runtime_value=None,
            plan_value=None,
            user_explicit=None,
            default=99,
        )
        assert result.value == 99
        assert result.source == Source.DEFAULT

    def test_merge_list_union(self):
        """测试列表并集合并"""
        merger = InjectionMerger()

        result = merger.merge_list(
            runtime=["a"],
            plan=["b"],
            user=["c"],
            strategy="union",
        )
        assert set(result) == {"a", "b", "c"}

    def test_merge_list_replace(self):
        """测试列表替换合并"""
        merger = InjectionMerger()

        result = merger.merge_list(
            runtime=["a"],
            plan=["b"],
            user=["c"],
            strategy="replace",
        )
        assert result == ["a"]


class TestEffectiveScopeBuilder:
    """有效范围构建器测试"""

    async def test_build_with_plan(self):
        """测试有计划时的构建"""
        # ...

    async def test_build_without_plan(self):
        """测试无计划时的降级"""
        # ...

    async def test_explicit_over_inferred(self):
        """测试显式优先于推断"""
        # ...
```

---

## 9. 变更历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-01-24 | 初始版本 | Claude |
