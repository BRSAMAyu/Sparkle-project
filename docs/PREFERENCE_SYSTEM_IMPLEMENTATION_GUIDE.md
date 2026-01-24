# Sparkle 个人偏好系统重构实施指南

> **目标**: 将用户偏好从"散装字段"升级为**系统契约**，构建统一的 **Personalization Engine（个性化引擎）** 打通 AI / 推送 / 任务 / 知识图谱全链路闭环。

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        用户偏好系统重构架构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────────────┐    │
│  │   Flutter   │───▶│   Go Gateway     │───▶│   Python Engine         │    │
│  │   Mobile    │    │   (事件发布)      │    │   (偏好中心 + 引擎)      │    │
│  └─────────────┘    └──────────────────┘    └─────────────────────────┘    │
│         │                    │                         │                    │
│         │                    ▼                         ▼                    │
│         │           ┌──────────────────┐    ┌─────────────────────────┐    │
│         │           │   Redis          │    │   PostgreSQL            │    │
│         │           │   - 缓存          │    │   - user_preferences    │    │
│         │           │   - Pub/Sub      │    │   - 版本管理            │    │
│         │           │   - Streams      │    │   - 审计日志            │    │
│         └──────────▶└──────────────────┘    └─────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Personalization Engine                            │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │ LLMProfile  │ │ PushPolicy  │ │ TaskPlan    │ │ Community   │   │   │
│  │  │ Generator   │ │ Generator   │ │ Generator   │ │ Match Gen   │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 实施阶段划分

| 阶段 | 名称 | 核心交付物 | 预计工作量 |
|------|------|-----------|-----------|
| **Phase 1** | 偏好中心 + 事件总线 | 统一数据模型、版本管理、缓存失效 | 中 |
| **Phase 2** | Personalization Engine | 偏好映射引擎、策略生成器 | 中 |
| **Phase 3** | AI 系统深度集成 | System Prompt 个性化、动态参数 | 小 |
| **Phase 4** | 推送系统升级 | 策略适配、内容个性化、反馈闭环 | 中 |
| **Phase 5** | 任务系统闭环 | 任务→图谱链接、偏好驱动规划 | 中 |
| **Phase 6** | 可视化与反馈 | 效果预览、生效证明、自适应推断 | 小 |

---

## Phase 1: 偏好中心 + 事件总线

### 1.1 目标
- 建立统一的用户偏好数据模型（Single Source of Truth）
- 实现偏好变更事件的发布与订阅
- 修复 Go/Python 缓存不一致问题（"脑裂"）
- 修复时区处理逻辑

### 1.2 执行 Prompt

```
# Phase 1: 偏好中心与事件总线

## 任务概述
你需要为 Sparkle 项目建立统一的用户偏好中心，解决当前偏好数据分散、缓存不一致的问题。

## 背景信息
当前问题：
1. 偏好数据分散在 User 表（depth/curiosity）和 PushPreference 表（persona/slots）
2. Go Gateway 更新 DB 后，Python 端 30 分钟内仍使用旧缓存
3. active_slots 存储为字符串 "08:00"，未考虑时区转换
4. 各模块独立读取偏好，无统一版本控制

## 详细任务

### 任务 1.1: 创建统一偏好数据模型

文件：`backend/app/models/user_preferences.py`（新建）

创建 UserPreferencesCenter 模型：
```python
class UserPreferencesCenter(BaseModel):
    """统一用户偏好中心 - Single Source of Truth"""
    __tablename__ = "user_preferences_center"

    user_id: UUID (unique, FK to users.id)
    version: int (每次变更 +1, 默认 1)
    schema_version: int (数据结构版本, 默认 1)

    # 显式偏好 (用户手动设置)
    explicit: JSONB = {
        "depth_preference": float,      # 0.0-1.0
        "curiosity_preference": float,  # 0.0-1.0
        "persona_type": str,            # "coach" | "anime" | "mentor" | "friend"
        "daily_cap": int,               # 每日推送上限
        "timezone": str,                # IANA 格式，如 "Asia/Shanghai"
        "active_slots": [{              # 活跃时间段（分钟数，避免字符串解析）
            "dow": [0,1,2,3,4],         # 星期几 (0=周一)
            "start_min": 480,           # 08:00 = 8*60
            "end_min": 540              # 09:00 = 9*60
        }],
        "learning_style": str,          # "visual" | "auditory" | "kinesthetic"
        "feedback_style": str,          # "direct" | "gentle"
        "ai_verbosity": str,            # "concise" | "balanced" | "detailed"
        "focus_duration_preference": int,  # 默认专注时长（分钟）
        "enable_push": bool,
        "enable_curiosity_push": bool,
    }

    # 推断偏好 (系统根据行为推断)
    inferred: JSONB = {
        "optimal_push_hours": [int],    # 推断的最佳推送时段
        "content_difficulty_trend": float,  # 内容难度趋势
        "engagement_pattern": str,      # 参与模式
        "response_time_preference": str,  # 响应时间偏好
    }

    # 元数据
    last_explicit_update: datetime
    last_inferred_update: datetime
    created_at: datetime
    updated_at: datetime
```

### 任务 1.2: 创建偏好变更事件

文件：`backend/gateway/internal/cqrs/event/types.go`

添加新的事件类型：
```go
// User Preferences events
EventPreferencesUpdated    EventType = "user.preferences.updated"
EventPreferencesInferred   EventType = "user.preferences.inferred"
```

更新 StreamKey() 函数，将这些事件路由到 `cqrs:stream:user`。
更新 ConsumerGroup() 函数。

文件：`backend/gateway/internal/cqrs/event/preference_events.go`（新建）

创建偏好事件结构：
```go
type PreferencesUpdatedPayload struct {
    UserID            string   `json:"user_id"`
    PreferenceVersion int      `json:"preference_version"`
    ChangedKeys       []string `json:"changed_keys"`
    UpdatedAt         int64    `json:"updated_at"`
    Source            string   `json:"source"` // "explicit" | "inferred"
}
```

### 任务 1.3: 实现 Go Gateway 偏好更新时发布事件

文件：`backend/gateway/internal/service/user_preferences_service.go`（新建）

创建服务：
```go
type UserPreferencesService struct {
    pool     *pgxpool.Pool
    eventBus event.EventBus
    redis    *redis.Client
}

// UpdatePreferences 更新偏好并发布事件
func (s *UserPreferencesService) UpdatePreferences(
    ctx context.Context,
    userID uuid.UUID,
    updates map[string]interface{},
) error {
    // 1. 开启事务
    tx, _ := s.pool.Begin(ctx)
    defer tx.Rollback(ctx)

    // 2. 更新数据库 (version++)
    newVersion := s.incrementVersion(ctx, tx, userID)
    s.updateExplicitPreferences(ctx, tx, userID, updates)

    // 3. 写入 Outbox 表 (事务内)
    event := event.NewDomainEvent(
        event.EventPreferencesUpdated,
        event.AggregateUser,
        userID,
        PreferencesUpdatedPayload{
            UserID:            userID.String(),
            PreferenceVersion: newVersion,
            ChangedKeys:       extractKeys(updates),
            Source:            "explicit",
        },
        event.EventMetadata{UserID: userID},
    )
    s.eventBus.PublishWithTx(ctx, tx, event)

    // 4. 提交事务
    tx.Commit(ctx)

    // 5. 立即删除 Redis 缓存（双保险）
    s.invalidateCache(ctx, userID)

    return nil
}

func (s *UserPreferencesService) invalidateCache(ctx context.Context, userID uuid.UUID) {
    keys := []string{
        fmt.Sprintf("user:context:%s", userID),
        fmt.Sprintf("user:preferences:%s", userID),
        fmt.Sprintf("user:prefs:v:*:%s", userID), // 版本化缓存
    }
    s.redis.Del(ctx, keys...)
}
```

### 任务 1.4: Python 端订阅偏好变更事件

文件：`backend/app/services/preference_event_consumer.py`（新建）

创建消费者：
```python
class PreferenceEventConsumer:
    """消费 user.preferences.updated 事件，使本地缓存失效"""

    def __init__(self, redis_client, user_service: UserService):
        self.redis = redis_client
        self.user_service = user_service

    async def start(self):
        """启动事件消费"""
        # 订阅 Redis Stream
        stream_key = "cqrs:stream:user"
        consumer_group = "python_preference_consumer"

        while True:
            messages = await self.redis.xreadgroup(
                groupname=consumer_group,
                consumername="worker-1",
                streams={stream_key: ">"},
                count=10,
                block=1000,
            )

            for stream, entries in messages:
                for entry_id, data in entries:
                    await self._handle_event(data)
                    await self.redis.xack(stream_key, consumer_group, entry_id)

    async def _handle_event(self, data: dict):
        event_type = data.get("type")

        if event_type == "user.preferences.updated":
            payload = json.loads(data.get("payload", "{}"))
            user_id = UUID(payload["user_id"])

            # 立即使缓存失效
            await self.user_service.invalidate_user_cache(user_id)

            # 可选：发送 WebSocket 通知给客户端
            await self._notify_client(user_id, payload["preference_version"])
```

### 任务 1.5: 修复时区处理

文件：`backend/app/services/user_service.py`

更新 `get_context` 方法，确保时区正确处理：
```python
async def get_context(self, user_id: UUID) -> Optional[UserContext]:
    # ... 现有代码 ...

    # 时区感知的 active_slots 处理
    active_slots = self._normalize_active_slots(
        push_pref.active_slots,
        push_pref.timezone or "Asia/Shanghai"
    )

def _normalize_active_slots(
    self,
    slots: Optional[List[Dict]],
    timezone: str
) -> Optional[Dict]:
    """
    将字符串格式的时间段转换为分钟数格式，并附加时区信息

    输入: [{"start": "08:00", "end": "09:00"}]
    输出: {
        "timezone": "Asia/Shanghai",
        "slots": [{"dow": [0,1,2,3,4], "start_min": 480, "end_min": 540}]
    }
    """
    if not slots:
        return None

    normalized = []
    for slot in slots:
        start_str = slot.get("start", "08:00")
        end_str = slot.get("end", "09:00")

        start_min = self._time_str_to_minutes(start_str)
        end_min = self._time_str_to_minutes(end_str)
        dow = slot.get("dow", [0, 1, 2, 3, 4])  # 默认工作日

        normalized.append({
            "dow": dow,
            "start_min": start_min,
            "end_min": end_min,
        })

    return {
        "timezone": timezone,
        "slots": normalized,
    }

def _time_str_to_minutes(self, time_str: str) -> int:
    """将 "HH:MM" 转换为分钟数"""
    try:
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return 480  # 默认 08:00
```

### 任务 1.6: 创建数据库迁移

文件：`backend/alembic/versions/xxxx_create_user_preferences_center.py`

```python
def upgrade():
    op.create_table(
        'user_preferences_center',
        sa.Column('id', GUID(), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', GUID(), sa.ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('version', sa.Integer, default=1, nullable=False),
        sa.Column('schema_version', sa.Integer, default=1, nullable=False),
        sa.Column('explicit', JSONB, nullable=False, default={}),
        sa.Column('inferred', JSONB, nullable=False, default={}),
        sa.Column('last_explicit_update', sa.DateTime, nullable=True),
        sa.Column('last_inferred_update', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    op.create_index('ix_user_preferences_center_user_id', 'user_preferences_center', ['user_id'])

def downgrade():
    op.drop_table('user_preferences_center')
```

### 任务 1.7: 数据迁移脚本

文件：`backend/scripts/migrate_preferences_to_center.py`（新建）

创建迁移脚本，将现有 User.depth_preference、User.curiosity_preference 和 PushPreference 数据迁移到新的 user_preferences_center 表。

## 验收标准

1. [ ] user_preferences_center 表创建成功
2. [ ] 现有偏好数据成功迁移到新表
3. [ ] Go Gateway 更新偏好时发布 EventPreferencesUpdated 事件
4. [ ] Python 端能接收事件并使缓存失效
5. [ ] 测试：App 修改 persona 后，下一句对话立即使用新 persona（不用等 30 分钟）
6. [ ] 时区处理正确：用户设置 08:00，只在本地 08:00 触发

## 注意事项

- 保持对现有 User.depth_preference 等字段的向后兼容，通过视图或触发器同步
- 事件消费者需要幂等处理
- 缓存失效使用"立即删除 + 事件订阅"双保险模式
```

---

## Phase 2: Personalization Engine（个性化引擎）

### 2.1 目标
- 创建统一的偏好映射引擎
- 为各模块生成专用的策略配置
- 实现偏好到参数的标准化转换

### 2.2 执行 Prompt

```
# Phase 2: Personalization Engine（个性化引擎）

## 任务概述
创建一个统一的个性化引擎，负责将用户偏好映射为各模块可用的策略配置。

## 背景信息
Phase 1 已建立统一的偏好中心，现在需要一个"翻译层"将原始偏好转换为各系统可用的参数。

## 详细任务

### 任务 2.1: 创建 Personalization Engine 核心

文件：`backend/app/services/personalization/engine.py`（新建）

```python
"""
Personalization Engine - 个性化引擎

职责：
1. 从偏好中心读取用户偏好
2. 结合运行时上下文（当前计划、任务、专注状态等）
3. 为各模块生成策略配置
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID

@dataclass
class LLMProfile:
    """AI 系统策略配置"""
    system_prompt_additions: str      # 注入到 system prompt 的额外指令
    verbosity_target: str             # "concise" | "balanced" | "detailed"
    temperature: float                # 0.0 - 1.0
    should_ask_clarifying: bool       # 是否主动询问
    should_provide_examples: bool     # 是否提供示例
    exploration_level: str            # "focused" | "moderate" | "exploratory"
    tone: str                         # "professional" | "friendly" | "playful"

@dataclass
class PushPolicyProfile:
    """推送系统策略配置"""
    daily_cap: int                    # 每日上限
    min_interval_minutes: int         # 最小间隔（分钟）
    pressure_tolerance: float         # 压力容忍度 0-1
    memory_urgency_threshold: float   # 记忆临界点阈值
    curiosity_frequency: str          # "low" | "medium" | "high"
    silent_during_focus: bool         # 专注模式静默
    active_hours: list                # 活跃时段（分钟数）
    timezone: str

@dataclass
class TaskPlanProfile:
    """任务规划策略配置"""
    preferred_task_duration: int      # 偏好任务时长（分钟）
    difficulty_gradient: float        # 难度梯度 0-1
    micro_task_friendly: bool         # 是否适合微任务
    exploration_ratio: float          # 探索性任务比例 0-1
    review_priority: str              # "low" | "medium" | "high"
    fragmented_time_slots: list       # 碎片时间段

@dataclass
class CommunityMatchProfile:
    """社群匹配策略配置"""
    social_preference: str            # "solo" | "collaborative"
    visibility_preference: str        # "private" | "public"
    interest_match_weight: float      # 兴趣匹配权重
    skill_level_tolerance: float      # 技能等级容差

class PersonalizationEngine:
    """
    个性化引擎 - 偏好到策略的映射中心

    设计原则：
    1. 显式偏好优先于推断偏好
    2. 运行时上下文可覆盖静态偏好
    3. 所有映射逻辑集中在此，避免各模块分散实现
    """

    def __init__(self, preference_service, runtime_context_service):
        self.pref_service = preference_service
        self.ctx_service = runtime_context_service

    async def get_llm_profile(
        self,
        user_id: UUID,
        session_context: Optional[Dict] = None
    ) -> LLMProfile:
        """生成 AI 系统策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)
        ctx = await self.ctx_service.get_runtime_context(user_id)

        # 深度偏好映射
        depth = prefs.explicit.get("depth_preference", 0.5)
        verbosity = "detailed" if depth > 0.7 else ("concise" if depth < 0.3 else "balanced")
        temperature = 0.3 + (depth * 0.4)  # 0.3 - 0.7

        # 好奇心偏好映射
        curiosity = prefs.explicit.get("curiosity_preference", 0.5)
        exploration = "exploratory" if curiosity > 0.7 else ("focused" if curiosity < 0.3 else "moderate")

        # 反馈风格映射
        feedback_style = prefs.explicit.get("feedback_style", "balanced")
        tone = "playful" if feedback_style == "gentle" else "professional"

        # 角色映射
        persona = prefs.explicit.get("persona_type", "coach")
        persona_additions = self._get_persona_prompt_additions(persona)

        # 构建 system prompt 注入内容
        system_additions = f"""
## 用户偏好适配指令
- 回答详细程度：{verbosity}
- 探索倾向：{exploration}
- 语气风格：{tone}
{persona_additions}

如果用户偏好简洁回答，请控制在 3-5 句话内。
如果用户偏好详细回答，可以提供背景、示例和扩展内容。
"""

        return LLMProfile(
            system_prompt_additions=system_additions,
            verbosity_target=verbosity,
            temperature=temperature,
            should_ask_clarifying=depth > 0.6,
            should_provide_examples=depth > 0.5,
            exploration_level=exploration,
            tone=tone,
        )

    async def get_push_policy_profile(
        self,
        user_id: UUID
    ) -> PushPolicyProfile:
        """生成推送系统策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)
        ctx = await self.ctx_service.get_runtime_context(user_id)

        explicit = prefs.explicit

        # 基础配置
        daily_cap = explicit.get("daily_cap", 5)
        timezone = explicit.get("timezone", "Asia/Shanghai")

        # 深度偏好影响推送内容详细度
        depth = explicit.get("depth_preference", 0.5)

        # 好奇心偏好影响好奇心推送频率
        curiosity = explicit.get("curiosity_preference", 0.5)
        curiosity_freq = "high" if curiosity > 0.7 else ("low" if curiosity < 0.3 else "medium")

        # 根据连续忽略次数调整间隔
        consecutive_ignores = prefs.inferred.get("consecutive_ignores", 0)
        base_interval = 120  # 2 小时
        min_interval = min(base_interval * (1 + consecutive_ignores * 0.5), 360)  # 上限 6 小时

        # 活跃时段
        slots = explicit.get("active_slots", [])
        active_hours = []
        for slot in slots:
            active_hours.extend(range(slot["start_min"], slot["end_min"]))

        # 专注模式检测
        is_focusing = ctx.get("focus_session_active", False)

        return PushPolicyProfile(
            daily_cap=daily_cap,
            min_interval_minutes=int(min_interval),
            pressure_tolerance=depth,  # 深度高的用户更能接受压力提醒
            memory_urgency_threshold=0.3 if depth > 0.5 else 0.2,
            curiosity_frequency=curiosity_freq,
            silent_during_focus=is_focusing,
            active_hours=active_hours,
            timezone=timezone,
        )

    async def get_task_plan_profile(
        self,
        user_id: UUID
    ) -> TaskPlanProfile:
        """生成任务规划策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)

        explicit = prefs.explicit

        # 专注时长偏好
        focus_duration = explicit.get("focus_duration_preference", 25)

        # 深度偏好影响任务难度梯度
        depth = explicit.get("depth_preference", 0.5)
        difficulty_gradient = 0.3 + (depth * 0.5)  # 0.3 - 0.8

        # 好奇心偏好影响探索性任务比例
        curiosity = explicit.get("curiosity_preference", 0.5)
        exploration_ratio = curiosity * 0.4  # 0 - 0.4

        # 碎片时间检测
        slots = explicit.get("active_slots", [])
        fragmented = [s for s in slots if s["end_min"] - s["start_min"] <= 30]

        return TaskPlanProfile(
            preferred_task_duration=focus_duration,
            difficulty_gradient=difficulty_gradient,
            micro_task_friendly=len(fragmented) > 0,
            exploration_ratio=exploration_ratio,
            review_priority="high" if depth > 0.6 else "medium",
            fragmented_time_slots=fragmented,
        )

    def _get_persona_prompt_additions(self, persona: str) -> str:
        """根据角色生成额外的 prompt 指令"""
        personas = {
            "coach": "- 角色：严格的学习教练，强调纪律和效率\n- 语气：直接、专业、有时略带督促",
            "anime": "- 角色：温柔可爱的二次元助手\n- 语气：甜美、鼓励、活泼",
            "mentor": "- 角色：资深导师，提供深度指导\n- 语气：睿智、耐心、启发式",
            "friend": "- 角色：亲切的学习伙伴\n- 语气：轻松、友好、支持性",
        }
        return personas.get(persona, personas["coach"])
```

### 任务 2.2: 创建偏好服务

文件：`backend/app/services/personalization/preference_service.py`（新建）

```python
class PreferenceService:
    """
    偏好服务 - 统一的偏好数据访问层

    特性：
    1. 缓存感知（带版本号的缓存）
    2. 合并显式与推断偏好
    3. 提供默认值填充
    """

    async def get_preferences(self, user_id: UUID) -> UserPreferencesCenter:
        """获取用户偏好（带缓存）"""
        cache_key = f"user:prefs:{user_id}"

        # 尝试缓存
        cached = await self.redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            # 验证版本
            db_version = await self._get_db_version(user_id)
            if data.get("version") == db_version:
                return UserPreferencesCenter(**data)

        # 数据库查询
        prefs = await self._query_from_db(user_id)

        # 填充默认值
        prefs = self._fill_defaults(prefs)

        # 写入缓存（带版本）
        await self.redis.setex(
            cache_key,
            1800,
            json.dumps(prefs.dict())
        )

        return prefs

    def _fill_defaults(self, prefs: UserPreferencesCenter) -> UserPreferencesCenter:
        """填充默认值"""
        defaults = {
            "depth_preference": 0.5,
            "curiosity_preference": 0.5,
            "persona_type": "coach",
            "daily_cap": 5,
            "timezone": "Asia/Shanghai",
            "learning_style": "balanced",
            "feedback_style": "balanced",
            "ai_verbosity": "balanced",
            "focus_duration_preference": 25,
            "enable_push": True,
            "enable_curiosity_push": True,
        }

        for key, default in defaults.items():
            if key not in prefs.explicit or prefs.explicit[key] is None:
                prefs.explicit[key] = default

        return prefs
```

### 任务 2.3: 创建运行时上下文服务

文件：`backend/app/services/personalization/runtime_context_service.py`（新建）

```python
class RuntimeContextService:
    """
    运行时上下文服务

    收集影响个性化决策的实时状态：
    - 当前是否在专注模式
    - 当前活跃的计划和任务
    - 最近的学习进度
    - 当日推送计数
    """

    async def get_runtime_context(self, user_id: UUID) -> Dict[str, Any]:
        """获取运行时上下文"""
        return {
            "focus_session_active": await self._is_focus_active(user_id),
            "active_plan_count": await self._get_active_plan_count(user_id),
            "pending_task_count": await self._get_pending_task_count(user_id),
            "today_push_count": await self._get_today_push_count(user_id),
            "last_activity_minutes_ago": await self._get_last_activity_minutes(user_id),
            "current_local_hour": self._get_user_local_hour(user_id),
        }

    async def _is_focus_active(self, user_id: UUID) -> bool:
        """检查是否有活跃的专注会话"""
        # 查询 focus_sessions 表
        query = select(FocusSession).where(
            FocusSession.user_id == user_id,
            FocusSession.end_time.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
```

### 任务 2.4: 集成到现有服务

文件：`backend/app/services/__init__.py`

导出 PersonalizationEngine 并创建工厂函数：
```python
def get_personalization_engine(db: AsyncSession, redis) -> PersonalizationEngine:
    pref_service = PreferenceService(db, redis)
    ctx_service = RuntimeContextService(db, redis)
    return PersonalizationEngine(pref_service, ctx_service)
```

## 验收标准

1. [ ] PersonalizationEngine 能正确生成 LLMProfile
2. [ ] PersonalizationEngine 能正确生成 PushPolicyProfile
3. [ ] PersonalizationEngine 能正确生成 TaskPlanProfile
4. [ ] 偏好到策略的映射逻辑清晰、可测试
5. [ ] 运行时上下文能正确检测专注模式

## 注意事项

- 所有映射逻辑必须有单元测试覆盖
- 策略生成应该是无副作用的纯函数
- 考虑添加 A/B 测试标记，便于后续优化
```

---

## Phase 3: AI 系统深度集成

### 3.1 执行 Prompt

```
# Phase 3: AI 系统深度集成

## 任务概述
将 PersonalizationEngine 生成的 LLMProfile 集成到 AI Orchestrator，实现真正的个性化对话体验。

## 背景信息
当前 orchestrator.py 和 prompts.py 仅简单读取 depth/curiosity 两个维度，未充分利用用户偏好。

## 详细任务

### 任务 3.1: 更新 Orchestrator 使用 PersonalizationEngine

文件：`backend/app/orchestration/orchestrator.py`

找到 `_build_user_context` 方法，更新为：

```python
async def _build_user_context(self, user_id: str) -> Dict[str, Any]:
    """构建用户上下文，集成个性化引擎"""

    # 获取基础用户信息
    user_context = await self.user_service.get_context(UUID(user_id))

    # 获取个性化策略
    engine = get_personalization_engine(self.db, self.redis)
    llm_profile = await engine.get_llm_profile(UUID(user_id))

    return {
        "user_id": user_id,
        "nickname": user_context.nickname,
        "timezone": user_context.timezone,
        "preferences": user_context.preferences,
        # 新增：LLM 策略配置
        "llm_profile": {
            "system_prompt_additions": llm_profile.system_prompt_additions,
            "verbosity_target": llm_profile.verbosity_target,
            "temperature": llm_profile.temperature,
            "should_ask_clarifying": llm_profile.should_ask_clarifying,
            "should_provide_examples": llm_profile.should_provide_examples,
            "exploration_level": llm_profile.exploration_level,
            "tone": llm_profile.tone,
        }
    }
```

### 任务 3.2: 更新 System Prompt 构建

文件：`backend/app/orchestration/prompts.py`

更新 `build_system_prompt` 函数：

```python
def build_system_prompt(
    user_context: dict,
    conversation_history: dict = None,
    prompt_version: str = "v1",
) -> str:
    """构建完整的 System Prompt，深度集成用户偏好"""

    # 获取 LLM Profile（由 PersonalizationEngine 生成）
    llm_profile = user_context.get("llm_profile", {})

    # 基础上下文格式化
    formatted_user_context = format_user_context(user_context)

    # 动态注入偏好指令
    preference_instructions = llm_profile.get(
        "system_prompt_additions",
        _get_default_preference_instructions(user_context)
    )

    # 历史对话格式化
    conversation_history_section = ""
    if conversation_history:
        conversation_history_section = format_conversation_history(conversation_history)

    prompt = AGENT_SYSTEM_PROMPT.format(
        user_context=formatted_user_context,
        preference_instructions=preference_instructions,
        conversation_history_section=conversation_history_section,
    )

    return prompt

# 更新模板
AGENT_SYSTEM_PROMPT = """你是 Sparkle（星火），一个智能学习助手。

## 当前用户上下文
{user_context}

{preference_instructions}

## 对话历史
{conversation_history_section}

## 核心原则
1. 始终遵循用户的偏好设置
2. 根据用户的深度偏好调整回答详细程度
3. 根据用户的好奇心偏好决定是否扩展话题
4. 保持角色一致性
"""
```

### 任务 3.3: 动态调整 LLM 参数

文件：`backend/app/services/llm_service.py`

更新 `_call_llm` 方法，使用动态 temperature：

```python
async def _call_llm(
    self,
    messages: List[Dict],
    user_context: Optional[Dict] = None,
    **kwargs
) -> AsyncGenerator[str, None]:
    """调用 LLM，使用个性化参数"""

    # 从用户上下文获取 LLM Profile
    llm_profile = user_context.get("llm_profile", {}) if user_context else {}

    # 动态 temperature
    temperature = llm_profile.get("temperature", 0.5)

    # 构建请求
    response = await self.client.chat.completions.create(
        model=self.model,
        messages=messages,
        temperature=temperature,
        stream=True,
        **kwargs
    )

    async for chunk in response:
        yield chunk.choices[0].delta.content or ""
```

### 任务 3.4: 记录偏好版本到响应

文件：`backend/app/orchestration/orchestrator.py`

在生成响应时记录使用的偏好版本：

```python
async def _generate_response(self, ...):
    # ... 现有代码 ...

    # 记录偏好版本到响应元数据
    preference_version = user_context.get("preference_version", 0)

    response_metadata = {
        "response_id": response_id,
        "trace_id": trace_id,
        "preference_version": preference_version,  # 新增
        "llm_profile_hash": hash(str(llm_profile)),  # 便于调试
    }

    yield ChatResponse(
        # ... 现有字段 ...
        metadata=response_metadata,
    )
```

## 验收标准

1. [ ] AI 回复风格随 persona 变化（coach vs anime）
2. [ ] AI 回复详细度随 depth_preference 变化
3. [ ] AI 是否扩展话题随 curiosity_preference 变化
4. [ ] temperature 参数正确应用
5. [ ] 响应元数据包含 preference_version

## 测试场景

1. 设置 depth_preference=0.2，问"什么是机器学习"，期望简短回答
2. 设置 depth_preference=0.9，问同样问题，期望详细回答
3. 设置 persona_type="anime"，期望语气可爱活泼
4. 设置 curiosity_preference=0.9，期望 AI 主动扩展相关话题
```

---

## Phase 4: 推送系统升级

### 4.1 执行 Prompt

```
# Phase 4: 推送系统升级

## 任务概述
将推送系统与 PersonalizationEngine 深度集成，实现：
1. 策略阈值个性化（不再硬编码）
2. 推送内容个性化（结合深度/好奇心偏好）
3. 反馈闭环（consecutive_ignores 更新）

## 背景信息
当前问题：
1. MemoryStrategy 等策略使用硬编码阈值（如 retention < 0.3）
2. 推送内容仅使用 persona_type，未结合深度/好奇心偏好
3. consecutive_ignores 字段存在但从未更新

## 详细任务

### 任务 4.1: 更新推送策略基类

文件：`backend/app/services/push_strategies/strategy.py`

```python
from app.services.personalization.engine import PersonalizationEngine, PushPolicyProfile

class PushStrategy(ABC):
    """推送策略基类 - 集成个性化引擎"""

    def __init__(self, db: AsyncSession, personalization_engine: PersonalizationEngine):
        self.db = db
        self.engine = personalization_engine

    @abstractmethod
    async def should_trigger(
        self,
        user: User,
        policy: PushPolicyProfile  # 新增参数
    ) -> bool:
        """判断是否应该触发推送"""
        pass

    @abstractmethod
    async def get_context_data(self, user: User) -> Dict[str, Any]:
        """获取推送上下文数据"""
        pass


class MemoryStrategy(PushStrategy):
    """记忆临界点策略 - 个性化版本"""

    async def should_trigger(
        self,
        user: User,
        policy: PushPolicyProfile
    ) -> bool:
        # 使用个性化阈值，而不是硬编码 0.3
        urgency_threshold = policy.memory_urgency_threshold

        # 根据深度偏好调整 importance 筛选
        # 深度偏好高的用户只推送重要节点
        importance_threshold = 5 if policy.pressure_tolerance > 0.6 else 3

        query = select(UserNodeStatus, KnowledgeNode).join(KnowledgeNode).where(
            UserNodeStatus.user_id == user.id,
            UserNodeStatus.mastery_score > 0.1,  # 至少学过
            UserNodeStatus.mastery_score < urgency_threshold,  # 使用个性化阈值
            KnowledgeNode.importance_level >= importance_threshold,  # 个性化
        ).order_by(
            UserNodeStatus.mastery_score.asc()
        ).limit(1)

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None


class CuriosityStrategy(PushStrategy):
    """好奇心胶囊策略 - 个性化版本"""

    async def should_trigger(
        self,
        user: User,
        policy: PushPolicyProfile
    ) -> bool:
        # 检查好奇心推送开关
        if policy.curiosity_frequency == "low":
            return False

        # 根据频率决定触发概率
        frequency_map = {"low": 0, "medium": 0.3, "high": 0.6}
        trigger_probability = frequency_map.get(policy.curiosity_frequency, 0.3)

        import random
        return random.random() < trigger_probability


class SprintStrategy(PushStrategy):
    """冲刺提醒策略 - 个性化版本"""

    async def should_trigger(
        self,
        user: User,
        policy: PushPolicyProfile
    ) -> bool:
        # 根据压力容忍度调整 DDL 阈值
        # 高容忍度用户可以更早提醒
        base_hours = 72
        adjusted_hours = base_hours * (1 + policy.pressure_tolerance)  # 72 - 144 小时

        now = datetime.utcnow()
        deadline_threshold = now + timedelta(hours=adjusted_hours)

        query = select(Task).where(
            Task.user_id == user.id,
            Task.status == TaskStatus.PENDING,
            Task.deadline.isnot(None),
            Task.deadline <= deadline_threshold,
            Task.deadline > now,
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
```

### 任务 4.2: 更新 PushService 使用个性化策略

文件：`backend/app/services/push_service.py`

```python
class PushService:
    def __init__(self, db: AsyncSession, llm_service, redis):
        self.db = db
        self.llm = llm_service
        self.redis = redis
        self.engine = get_personalization_engine(db, redis)

    async def process_user_push(self, user: User) -> bool:
        """处理单个用户的推送（集成个性化引擎）"""

        # 1. 获取个性化策略
        policy = await self.engine.get_push_policy_profile(user.id)

        # 2. 专注模式检查
        if policy.silent_during_focus:
            logger.info(f"User {user.id} is in focus mode, skipping push")
            return False

        # 3. 活跃时间检查（使用分钟数和时区）
        if not self._is_active_time(policy):
            return False

        # 4. 频控检查（使用个性化间隔）
        if await self._check_frequency_cap(user, policy):
            return False

        # 5. 评估策略优先级（传入 policy）
        strategies = [
            SprintStrategy(self.db, self.engine),
            MemoryStrategy(self.db, self.engine),
            CuriosityStrategy(self.db, self.engine),
            InactivityStrategy(self.db, self.engine),
        ]

        for strategy in strategies:
            if await strategy.should_trigger(user, policy):
                context_data = await strategy.get_context_data(user)
                await self._send_push(user, strategy.trigger_type, context_data, policy)
                return True

        return False

    def _is_active_time(self, policy: PushPolicyProfile) -> bool:
        """检查是否在活跃时间段（使用分钟数）"""
        from zoneinfo import ZoneInfo

        try:
            tz = ZoneInfo(policy.timezone)
        except:
            tz = ZoneInfo("Asia/Shanghai")

        now = datetime.now(tz)
        current_minutes = now.hour * 60 + now.minute

        return current_minutes in policy.active_hours

    async def _check_frequency_cap(
        self,
        user: User,
        policy: PushPolicyProfile
    ) -> bool:
        """频控检查（使用个性化间隔）"""
        prefs = user.push_preference

        # 使用个性化的最小间隔
        min_interval = timedelta(minutes=policy.min_interval_minutes)

        if prefs.last_push_time:
            if datetime.utcnow() - prefs.last_push_time < min_interval:
                return True  # 冷却中

        # 日上限检查
        today_count = await self._get_today_push_count(user.id)
        return today_count >= policy.daily_cap
```

### 任务 4.3: 更新推送内容生成

文件：`backend/app/services/llm_service.py`

```python
async def generate_push_content(
    self,
    user_nickname: str,
    persona: str,
    trigger_type: str,
    context_data: Dict,
    depth_preference: float = 0.5,  # 新增
    curiosity_preference: float = 0.5,  # 新增
) -> Dict[str, str]:
    """生成推送内容（个性化版本）"""

    # 根据深度偏好调整内容详细度
    detail_instruction = ""
    if depth_preference > 0.7:
        detail_instruction = "提供详细的背景信息和具体建议。"
    elif depth_preference < 0.3:
        detail_instruction = "保持极简，一句话点明重点即可。"
    else:
        detail_instruction = "适中详细度，2-3句话。"

    # 根据好奇心偏好调整是否扩展
    exploration_instruction = ""
    if curiosity_preference > 0.6:
        exploration_instruction = "可以附带一个有趣的相关知识点。"

    persona_prompts = {
        "coach": f"Role: Strict Study Coach. Tone: Urgent, disciplined. {detail_instruction}",
        "anime": f"Role: Cute Anime Assistant. Tone: Sweet, encouraging. {detail_instruction}",
        "mentor": f"Role: Wise Mentor. Tone: Insightful, patient. {detail_instruction}",
        "friend": f"Role: Friendly Study Buddy. Tone: Casual, supportive. {detail_instruction}",
    }

    system_prompt = persona_prompts.get(persona, persona_prompts["coach"])
    system_prompt += f"\n{exploration_instruction}"

    # ... 调用 LLM 生成内容 ...
```

### 任务 4.4: 实现反馈闭环

文件：`backend/app/services/push_feedback_service.py`（新建）

```python
class PushFeedbackService:
    """推送反馈服务 - 更新 consecutive_ignores 和偏好推断"""

    async def record_push_interaction(
        self,
        user_id: UUID,
        push_id: UUID,
        interaction_type: str,  # "clicked" | "dismissed" | "ignored"
    ):
        """记录推送交互"""

        push_pref = await self._get_push_preference(user_id)

        if interaction_type == "clicked":
            # 重置连续忽略计数
            push_pref.consecutive_ignores = 0
        elif interaction_type in ("dismissed", "ignored"):
            # 增加连续忽略计数
            push_pref.consecutive_ignores += 1

        await self.db.commit()

        # 更新推断偏好
        await self._update_inferred_preferences(user_id, interaction_type)

    async def _update_inferred_preferences(
        self,
        user_id: UUID,
        interaction_type: str
    ):
        """更新推断偏好"""
        prefs = await self.pref_service.get_preferences(user_id)

        # 如果连续忽略超过 5 次，推断用户可能不喜欢当前频率
        if prefs.explicit.get("consecutive_ignores", 0) >= 5:
            # 建议降低每日上限
            current_cap = prefs.explicit.get("daily_cap", 5)
            prefs.inferred["suggested_daily_cap"] = max(1, current_cap - 1)
```

### 任务 4.5: 添加 WebSocket 推送交互反馈处理

文件：`backend/gateway/internal/handler/chat_orchestrator.go`

在 WebSocket 消息处理中添加新的消息类型：

```go
case "push_interaction":
    h.handlePushInteraction(conn, msgMap, userID)

func (h *ChatOrchestrator) handlePushInteraction(conn *websocket.Conn, msgMap map[string]interface{}, userID string) {
    pushID := msgMap["push_id"].(string)
    interactionType := msgMap["interaction_type"].(string)  // "clicked" | "dismissed" | "ignored"

    // 调用 Python 后端记录交互
    req := &agentv1.PushInteractionRequest{
        UserId:          userID,
        PushId:          pushID,
        InteractionType: interactionType,
    }

    h.agentClient.RecordPushInteraction(ctx, req)
}
```

## 验收标准

1. [ ] MemoryStrategy 使用个性化的 urgency_threshold
2. [ ] SprintStrategy 使用个性化的 DDL 阈值
3. [ ] CuriosityStrategy 使用好奇心频率设置
4. [ ] 推送内容详细度随 depth_preference 变化
5. [ ] consecutive_ignores 正确更新
6. [ ] 专注模式下推送被静默

## 测试场景

1. 设置 depth_preference=0.2，收到推送应该是一句话
2. 设置 depth_preference=0.9，收到推送应该有详细背景
3. 设置 curiosity_preference=0.9，推送可能附带有趣知识点
4. 连续忽略 5 次推送后，检查 consecutive_ignores=5
```

---

## Phase 5: 任务系统闭环

### 5.1 执行 Prompt

```
# Phase 5: 任务系统闭环

## 任务概述
修复任务完成后与知识图谱的断层，实现：
1. 任务完成 → 更新知识图谱 mastery_score
2. 偏好驱动的任务推荐
3. 碎片时间微任务推荐

## 背景信息
当前问题：
1. TaskService.complete() 未调用 galaxy_service.spark_node()
2. 任务推荐不考虑用户偏好
3. 碎片时间段（schedule_preferences）未被任务系统使用

## 详细任务

### 任务 5.1: 修复任务完成 → 知识图谱链路

文件：`backend/app/api/v1/tasks.py`

更新 `complete_task` 端点：

```python
@router.post("/{task_id}/complete", response_model=Dict[str, Any])
async def complete_task(
    request: TaskCompleteRequest,
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(None),
):
    """完成任务（集成知识图谱更新）"""

    # 1. 获取任务
    task = await get_task_by_id(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 2. 更新任务状态
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    task.actual_minutes = request.actual_minutes
    await db.commit()

    # 3. 更新计划进度
    if task.plan_id:
        plan_service = PlanService(db)
        await plan_service.update_progress(task.plan_id, task.user_id)

    # 4. 【关键修复】更新知识图谱
    if task.knowledge_node_id:
        from app.services.galaxy_service import GalaxyService
        galaxy_service = GalaxyService(db)

        spark_result = await galaxy_service.spark_node(
            user_id=current_user.id,
            node_id=task.knowledge_node_id,
            study_minutes=request.actual_minutes or task.estimated_minutes or 15,
            task_id=task.id,
            trigger_expansion=True,  # 触发 LLM 扩展
        )

        logger.info(
            f"Task {task_id} completion triggered galaxy spark: "
            f"node={task.knowledge_node_id}, "
            f"new_mastery={spark_result.new_mastery_score}"
        )

    # 5. 生成 AI 反馈
    feedback_service = TaskFeedbackService(db)
    feedback = await feedback_service.generate_feedback(task, current_user, db)

    # 6. 发布事件
    event = DomainEvent(
        type=EventTaskCompleted,
        aggregate_id=task_id,
        payload={
            "task_id": str(task_id),
            "user_id": str(current_user.id),
            "knowledge_node_id": str(task.knowledge_node_id) if task.knowledge_node_id else None,
            "actual_minutes": request.actual_minutes,
        }
    )
    await publish_event(event)

    return {
        "task": task,
        "feedback": feedback,
        "galaxy_update": spark_result.dict() if task.knowledge_node_id else None,
    }
```

### 任务 5.2: 创建偏好驱动的任务推荐服务

文件：`backend/app/services/task_recommendation_service.py`（新建）

```python
class TaskRecommendationService:
    """
    任务推荐服务 - 基于用户偏好和知识图谱

    策略：
    1. 根据 depth_preference 调整任务难度
    2. 根据 curiosity_preference 调整探索性任务比例
    3. 根据 schedule_preferences 推荐碎片时间微任务
    """

    def __init__(self, db: AsyncSession, personalization_engine: PersonalizationEngine):
        self.db = db
        self.engine = personalization_engine

    async def get_recommendations(
        self,
        user_id: UUID,
        limit: int = 5,
        context: Optional[str] = None,  # "commute" | "lunch" | "evening" | None
    ) -> List[TaskRecommendation]:
        """获取个性化任务推荐"""

        # 1. 获取任务规划策略
        profile = await self.engine.get_task_plan_profile(user_id)

        # 2. 获取待复习知识点
        review_nodes = await self._get_review_candidates(user_id, profile)

        # 3. 获取探索性知识点
        exploration_nodes = await self._get_exploration_candidates(user_id, profile)

        # 4. 混合推荐（根据 exploration_ratio）
        review_count = int(limit * (1 - profile.exploration_ratio))
        exploration_count = limit - review_count

        recommendations = []

        # 复习任务
        for node in review_nodes[:review_count]:
            task = await self._create_review_task(node, profile, context)
            recommendations.append(task)

        # 探索任务
        for node in exploration_nodes[:exploration_count]:
            task = await self._create_exploration_task(node, profile, context)
            recommendations.append(task)

        return recommendations

    async def _get_review_candidates(
        self,
        user_id: UUID,
        profile: TaskPlanProfile
    ) -> List[UserNodeStatus]:
        """获取待复习知识点"""

        # 根据复习优先级调整查询
        priority_threshold = {
            "high": 0.4,
            "medium": 0.3,
            "low": 0.2,
        }.get(profile.review_priority, 0.3)

        query = select(UserNodeStatus, KnowledgeNode).join(KnowledgeNode).where(
            UserNodeStatus.user_id == user_id,
            UserNodeStatus.mastery_score < priority_threshold,
            UserNodeStatus.mastery_score > 0.05,  # 至少学过
        ).order_by(
            UserNodeStatus.next_review_at.asc().nullsfirst()
        ).limit(10)

        result = await self.db.execute(query)
        return result.all()

    async def _get_exploration_candidates(
        self,
        user_id: UUID,
        profile: TaskPlanProfile
    ) -> List[KnowledgeNode]:
        """获取探索性知识点（用户未学过但相关的）"""

        # 获取用户已学节点的相邻节点
        # ... 图遍历逻辑 ...
        pass

    async def _create_review_task(
        self,
        node: UserNodeStatus,
        profile: TaskPlanProfile,
        context: Optional[str],
    ) -> TaskRecommendation:
        """创建复习任务"""

        # 根据上下文调整任务时长
        if context in ("commute", "lunch") and profile.micro_task_friendly:
            duration = min(15, profile.preferred_task_duration)
            task_type = "micro_review"
        else:
            duration = profile.preferred_task_duration
            task_type = "review"

        return TaskRecommendation(
            knowledge_node_id=node.knowledge_node.id,
            title=f"复习: {node.knowledge_node.label}",
            estimated_minutes=duration,
            task_type=task_type,
            difficulty=node.knowledge_node.difficulty,
            priority=self._calculate_priority(node),
            reason=f"距离上次学习已过 {self._days_since_last_study(node)} 天",
        )


@dataclass
class TaskRecommendation:
    knowledge_node_id: UUID
    title: str
    estimated_minutes: int
    task_type: str  # "review" | "micro_review" | "exploration" | "micro_exploration"
    difficulty: int
    priority: float
    reason: str
```

### 任务 5.3: 创建碎片时间微任务 API

文件：`backend/app/api/v1/tasks.py`

添加新端点：

```python
@router.get("/recommendations/micro", response_model=List[TaskRecommendation])
async def get_micro_task_recommendations(
    context: Optional[str] = Query(None, description="上下文: commute, lunch, evening"),
    limit: int = Query(3, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取碎片时间微任务推荐

    根据用户的 schedule_preferences 和当前时间上下文，
    推荐适合在碎片时间完成的微任务（15分钟以内）。
    """
    engine = get_personalization_engine(db, redis)
    service = TaskRecommendationService(db, engine)

    recommendations = await service.get_recommendations(
        user_id=current_user.id,
        limit=limit,
        context=context,
    )

    # 过滤出微任务
    micro_tasks = [r for r in recommendations if r.estimated_minutes <= 15]

    return micro_tasks
```

### 任务 5.4: 更新 Flutter 端调用

文件：`mobile/lib/features/task/data/repositories/task_repository.dart`

添加微任务推荐方法：

```dart
class TaskRepository {
  /// 获取碎片时间微任务推荐
  Future<List<TaskRecommendation>> getMicroTaskRecommendations({
    String? context,
    int limit = 3,
  }) async {
    final queryParams = <String, String>{
      'limit': limit.toString(),
    };
    if (context != null) {
      queryParams['context'] = context;
    }

    final response = await _apiClient.get<List<dynamic>>(
      '/tasks/recommendations/micro',
      queryParameters: queryParams,
    );

    return response.data!
        .map((json) => TaskRecommendation.fromJson(json))
        .toList();
  }
}
```

## 验收标准

1. [ ] 任务完成后 mastery_score 正确更新
2. [ ] 任务完成后 next_review_at 正确计算
3. [ ] 任务推荐考虑 depth_preference（难度）
4. [ ] 任务推荐考虑 curiosity_preference（探索比例）
5. [ ] 碎片时间微任务 API 正常工作
6. [ ] 任务完成后发布 EventTaskCompleted 事件

## 测试场景

1. 完成一个绑定知识点的任务后，检查该节点的 mastery_score 是否增加
2. 设置 depth_preference=0.8，推荐的任务应该倾向于高难度
3. 设置 curiosity_preference=0.9，推荐的任务中应该有探索性任务
4. 在"通勤"上下文请求微任务，应该返回 ≤15 分钟的任务
```

---

## Phase 6: 可视化与反馈

### 6.1 执行 Prompt

```
# Phase 6: 可视化与反馈

## 任务概述
实现偏好效果的可视化和自适应反馈机制：
1. 偏好效果预览（Preview）
2. 偏好生效证明（Proof）
3. 基于反馈的偏好推断

## 详细任务

### 任务 6.1: 创建偏好效果预览 API

文件：`backend/app/api/v1/preferences.py`（新建）

```python
@router.post("/preview", response_model=PreferencePreviewResponse)
async def preview_preference_effects(
    request: PreferencePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    预览偏好调整后的效果

    返回：
    - AI 回复示例
    - 推送内容示例
    - 任务推荐示例
    """
    engine = get_personalization_engine(db, redis)

    # 临时应用新偏好
    temp_prefs = current_user.preferences.copy()
    temp_prefs.update(request.preview_preferences)

    # 生成 AI 回复示例
    llm_profile = await engine.get_llm_profile(
        current_user.id,
        override_preferences=temp_prefs
    )
    ai_sample = await generate_ai_sample(llm_profile)

    # 生成推送内容示例
    push_profile = await engine.get_push_policy_profile(
        current_user.id,
        override_preferences=temp_prefs
    )
    push_sample = await generate_push_sample(push_profile, temp_prefs)

    # 生成任务推荐示例
    task_profile = await engine.get_task_plan_profile(
        current_user.id,
        override_preferences=temp_prefs
    )
    task_samples = await generate_task_samples(task_profile)

    return PreferencePreviewResponse(
        ai_sample=ai_sample,
        push_sample=push_sample,
        task_samples=task_samples,
        summary=generate_summary(temp_prefs),
    )


async def generate_ai_sample(profile: LLMProfile) -> str:
    """生成 AI 回复示例"""
    sample_question = "什么是机器学习？"

    # 使用简化版 LLM 调用
    response = await llm_service.generate_sample_response(
        question=sample_question,
        system_additions=profile.system_prompt_additions,
        temperature=profile.temperature,
        max_tokens=200,
    )

    return response


def generate_summary(prefs: Dict) -> str:
    """生成偏好效果总结"""
    depth = prefs.get("depth_preference", 0.5)
    curiosity = prefs.get("curiosity_preference", 0.5)
    persona = prefs.get("persona_type", "coach")

    summaries = []

    if depth > 0.7:
        summaries.append("AI 将提供详细深入的解答")
    elif depth < 0.3:
        summaries.append("AI 将提供简洁精炼的解答")

    if curiosity > 0.7:
        summaries.append("系统将主动推荐相关知识扩展")
    elif curiosity < 0.3:
        summaries.append("系统将专注于您当前的学习内容")

    persona_names = {"coach": "严格教练", "anime": "可爱助手", "mentor": "智慧导师", "friend": "友好伙伴"}
    summaries.append(f"AI 将以「{persona_names.get(persona, persona)}」的风格与您互动")

    return "；".join(summaries)
```

### 任务 6.2: 创建偏好生效证明 API

文件：`backend/app/api/v1/preferences.py`

```python
@router.get("/effectiveness", response_model=PreferenceEffectivenessResponse)
async def get_preference_effectiveness(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取偏好生效证明

    返回最近 N 次决策记录，展示偏好是如何影响系统行为的。
    """
    # 查询最近的决策记录
    records = await get_recent_decision_records(db, current_user.id, limit)

    return PreferenceEffectivenessResponse(
        records=[
            DecisionRecord(
                timestamp=r.created_at,
                module=r.module,  # "ai" | "push" | "task"
                action=r.action,
                preference_version=r.preference_version,
                preferences_used=r.preferences_snapshot,
                outcome=r.outcome,
            )
            for r in records
        ],
        summary=PreferenceEffectivenessSummary(
            ai_decisions=len([r for r in records if r.module == "ai"]),
            push_decisions=len([r for r in records if r.module == "push"]),
            task_decisions=len([r for r in records if r.module == "task"]),
            last_preference_update=current_user.preferences.updated_at,
        ),
    )
```

### 任务 6.3: 创建决策记录服务

文件：`backend/app/services/decision_record_service.py`（新建）

```python
class DecisionRecordService:
    """
    决策记录服务 - 记录系统决策及使用的偏好版本

    用途：
    1. 调试：追踪偏好是否正确应用
    2. 审计：记录系统行为历史
    3. 反馈：为用户提供"偏好生效证明"
    """

    async def record_decision(
        self,
        user_id: UUID,
        module: str,
        action: str,
        preference_version: int,
        preferences_snapshot: Dict,
        outcome: str,
    ):
        """记录一次决策"""
        record = DecisionRecord(
            user_id=user_id,
            module=module,
            action=action,
            preference_version=preference_version,
            preferences_snapshot=preferences_snapshot,
            outcome=outcome,
            created_at=datetime.utcnow(),
        )
        self.db.add(record)
        await self.db.commit()
```

### 任务 6.4: 在关键决策点插入记录

文件：`backend/app/orchestration/orchestrator.py`

在 AI 响应生成后记录：

```python
async def _generate_response(self, ...):
    # ... 生成响应 ...

    # 记录决策
    await self.decision_service.record_decision(
        user_id=user_id,
        module="ai",
        action="generate_response",
        preference_version=user_context.get("preference_version", 0),
        preferences_snapshot={
            "depth_preference": llm_profile.verbosity_target,
            "temperature": llm_profile.temperature,
            "persona": llm_profile.tone,
        },
        outcome=f"Generated {len(full_response)} chars response",
    )
```

文件：`backend/app/services/push_service.py`

在推送发送后记录：

```python
async def _send_push(self, user, trigger_type, context_data, policy):
    # ... 发送推送 ...

    # 记录决策
    await self.decision_service.record_decision(
        user_id=user.id,
        module="push",
        action=f"send_{trigger_type}",
        preference_version=policy.preference_version,
        preferences_snapshot={
            "daily_cap": policy.daily_cap,
            "persona_type": user.push_preference.persona_type,
            "curiosity_frequency": policy.curiosity_frequency,
        },
        outcome=f"Sent {trigger_type} push",
    )
```

### 任务 6.5: 基于反馈的偏好推断

文件：`backend/app/services/preference_inference_service.py`（新建）

```python
class PreferenceInferenceService:
    """
    偏好推断服务 - 基于用户反馈自动调整推断偏好

    原则：
    1. 显式偏好始终优先
    2. 推断只做小幅度调整（每次 ±0.05）
    3. 推断附带置信度，低置信度时不自动应用
    """

    ADJUSTMENT_STEP = 0.05
    CONFIDENCE_THRESHOLD = 0.7

    async def process_feedback(
        self,
        user_id: UUID,
        feedback_type: str,
        reasons: List[str],
    ):
        """处理用户反馈，更新推断偏好"""

        prefs = await self.pref_service.get_preferences(user_id)
        inferred = prefs.inferred.copy()

        # 根据反馈类型和原因推断偏好调整
        adjustments = self._calculate_adjustments(feedback_type, reasons)

        for key, delta in adjustments.items():
            current = inferred.get(f"suggested_{key}", prefs.explicit.get(key, 0.5))
            new_value = max(0, min(1, current + delta))
            inferred[f"suggested_{key}"] = new_value
            inferred[f"{key}_confidence"] = self._update_confidence(
                inferred.get(f"{key}_confidence", 0.5),
                abs(delta)
            )

        # 更新推断偏好
        await self.pref_service.update_inferred(user_id, inferred)

        # 如果某项推断置信度超过阈值，通知用户
        high_confidence_suggestions = [
            (key.replace("suggested_", ""), value)
            for key, value in inferred.items()
            if key.startswith("suggested_") and inferred.get(f"{key.replace('suggested_', '')}_confidence", 0) > self.CONFIDENCE_THRESHOLD
        ]

        if high_confidence_suggestions:
            await self._notify_user_suggestions(user_id, high_confidence_suggestions)

    def _calculate_adjustments(
        self,
        feedback_type: str,
        reasons: List[str]
    ) -> Dict[str, float]:
        """计算偏好调整"""
        adjustments = {}

        if feedback_type == "down":
            if "verbose" in reasons or "too_long" in reasons:
                adjustments["depth_preference"] = -self.ADJUSTMENT_STEP
            if "off_topic" in reasons or "too_exploratory" in reasons:
                adjustments["curiosity_preference"] = -self.ADJUSTMENT_STEP
            if "too_hard" in reasons:
                adjustments["depth_preference"] = -self.ADJUSTMENT_STEP
            if "too_simple" in reasons:
                adjustments["depth_preference"] = self.ADJUSTMENT_STEP

        return adjustments
```

### 任务 6.6: Flutter 端偏好设置页面增强

文件：`mobile/lib/features/user/presentation/screens/learning_mode_screen.dart`

添加预览和生效证明功能：

```dart
class LearningModeScreen extends ConsumerStatefulWidget {
  // ... 现有代码 ...

  /// 预览当前偏好效果
  Future<void> _previewEffects() async {
    final preview = await ref.read(userRepositoryProvider).previewPreferenceEffects(
      PreferencePreviewRequest(
        previewPreferences: {
          'depth_preference': _currentDepthPreference,
          'curiosity_preference': _currentCuriosityPreference,
        },
      ),
    );

    showModalBottomSheet(
      context: context,
      builder: (context) => PreferencePreviewSheet(preview: preview),
    );
  }

  /// 查看偏好生效记录
  Future<void> _viewEffectiveness() async {
    final effectiveness = await ref.read(userRepositoryProvider).getPreferenceEffectiveness();

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => PreferenceEffectivenessScreen(data: effectiveness),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // ... 现有 UI ...

      // 新增按钮
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          FloatingActionButton.small(
            onPressed: _previewEffects,
            tooltip: '预览效果',
            child: const Icon(Icons.preview),
          ),
          const SizedBox(height: 8),
          FloatingActionButton.small(
            onPressed: _viewEffectiveness,
            tooltip: '查看生效记录',
            child: const Icon(Icons.history),
          ),
        ],
      ),
    );
  }
}
```

## 验收标准

1. [ ] 偏好预览 API 返回 AI、推送、任务的示例
2. [ ] 偏好生效证明 API 返回最近决策记录
3. [ ] 决策记录包含 preference_version
4. [ ] 反馈推断服务正确计算偏好调整
5. [ ] Flutter 端能预览偏好效果
6. [ ] Flutter 端能查看生效记录

## 测试场景

1. 调整 depth_preference，预览显示 AI 回复风格变化
2. 调整 persona_type，预览显示推送内容风格变化
3. 查看生效记录，能看到最近 10 次决策及使用的偏好
4. 连续给出"太啰嗦"反馈，推断服务应该建议降低 depth_preference
```

---

## 实施时间线建议

```
Week 1: Phase 1 (偏好中心 + 事件总线)
  - Day 1-2: 数据模型 + 迁移
  - Day 3-4: 事件发布 + 消费
  - Day 5: 缓存失效 + 时区修复

Week 2: Phase 2-3 (个性化引擎 + AI 集成)
  - Day 1-2: PersonalizationEngine 核心
  - Day 3-4: AI 系统集成
  - Day 5: 测试 + 调优

Week 3: Phase 4-5 (推送 + 任务)
  - Day 1-2: 推送策略升级
  - Day 3-4: 任务系统闭环
  - Day 5: 端到端测试

Week 4: Phase 6 (可视化 + 反馈)
  - Day 1-2: 预览 + 生效证明
  - Day 3: 反馈推断
  - Day 4-5: Flutter UI + 最终测试
```

---

## 关键验收指标

| 指标 | 目标 | 测量方法 |
|------|------|----------|
| 偏好生效延迟 | ≤5 秒 | App 修改偏好到 AI 使用新偏好的时间 |
| 缓存一致性 | 100% | Go/Python 读取同一用户偏好的一致率 |
| 决策可追溯性 | 100% | 每次 AI/推送/任务决策都有 preference_version |
| 任务→图谱闭环 | 100% | 任务完成后 mastery_score 更新率 |
| 用户控制感 | 提升 | 用户调研：偏好设置是否"有效" |

---

## 文件变更清单

### 新建文件

**Python:**
- `backend/app/models/user_preferences.py`
- `backend/app/services/personalization/engine.py`
- `backend/app/services/personalization/preference_service.py`
- `backend/app/services/personalization/runtime_context_service.py`
- `backend/app/services/preference_event_consumer.py`
- `backend/app/services/task_recommendation_service.py`
- `backend/app/services/push_feedback_service.py`
- `backend/app/services/decision_record_service.py`
- `backend/app/services/preference_inference_service.py`
- `backend/app/api/v1/preferences.py`
- `backend/alembic/versions/xxxx_create_user_preferences_center.py`
- `backend/scripts/migrate_preferences_to_center.py`

**Go:**
- `backend/gateway/internal/cqrs/event/preference_events.go`
- `backend/gateway/internal/service/user_preferences_service.go`

**Flutter:**
- `mobile/lib/features/user/presentation/widgets/preference_preview_sheet.dart`
- `mobile/lib/features/user/presentation/screens/preference_effectiveness_screen.dart`

### 修改文件

**Python:**
- `backend/app/services/user_service.py` - 时区处理
- `backend/app/orchestration/orchestrator.py` - 使用 PersonalizationEngine
- `backend/app/orchestration/prompts.py` - 深度集成偏好
- `backend/app/services/llm_service.py` - 动态参数
- `backend/app/services/push_service.py` - 个性化策略
- `backend/app/services/push_strategies/strategy.py` - 个性化阈值
- `backend/app/api/v1/tasks.py` - 知识图谱链接

**Go:**
- `backend/gateway/internal/cqrs/event/types.go` - 新事件类型
- `backend/gateway/internal/handler/chat_orchestrator.go` - 推送反馈处理

**Flutter:**
- `mobile/lib/features/user/presentation/screens/learning_mode_screen.dart` - 预览/生效记录
- `mobile/lib/features/user/data/repositories/user_repository.dart` - 新 API 调用
- `mobile/lib/features/task/data/repositories/task_repository.dart` - 微任务 API

---

*文档版本: 1.0.0*
*创建日期: 2026-01-19*
*适用项目: Sparkle MVP v0.3.0+*
