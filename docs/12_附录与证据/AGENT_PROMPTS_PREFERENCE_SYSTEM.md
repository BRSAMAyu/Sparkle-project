# Sparkle 偏好系统重构 - Coding Agent 执行 Prompts

> **使用说明**: 本文档包含 6 个分阶段的 Agent Prompt，请按顺序执行。每个 Phase 完成后需验收通过再进入下一阶段。

---

## 执行须知

1. **按顺序执行**: Phase 1 → 2 → 3 → 4 → 5 → 6
2. **验收后再继续**: 每个 Phase 末尾有验收标准，全部通过后再进入下一阶段
3. **保持向后兼容**: 修改现有代码时，确保旧功能不受影响
4. **测试覆盖**: 关键逻辑必须有单元测试

---

# Phase 1: 偏好中心与事件总线

## Agent Prompt

```
你是 Sparkle 项目的后端开发专家。现在需要建立统一的用户偏好中心，解决当前偏好数据分散、Go/Python 缓存不一致的问题。

## 项目背景

Sparkle 是一个 AI 学习助手，使用 Go Gateway + Python Engine + Flutter Mobile 架构：
- Go Gateway: `backend/gateway/` - 处理 WebSocket、HTTP 代理、事件发布
- Python Engine: `backend/app/` - AI 逻辑、业务服务
- Proto: `proto/agent_service.proto` - API 契约

## 当前问题

1. 偏好数据分散：User 表存 depth/curiosity，PushPreference 表存 persona/slots
2. 缓存脑裂：Go 更新 DB 后，Python 端 30 分钟内仍用旧缓存
3. active_slots 存储为字符串 "08:00"，未考虑时区转换

## 你的任务

### 1. 创建统一偏好数据模型

创建文件：`backend/app/models/user_preferences.py`

```python
"""
用户偏好中心 - Single Source of Truth
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from app.db.base_class import BaseModel

class UserPreferencesCenter(BaseModel):
    """统一用户偏好中心"""
    __tablename__ = "user_preferences_center"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    schema_version = Column(Integer, default=1, nullable=False)

    # 显式偏好 (用户手动设置)
    explicit = Column(JSONB, nullable=False, default=dict)
    # 结构:
    # {
    #     "depth_preference": 0.5,           # 0.0-1.0
    #     "curiosity_preference": 0.5,       # 0.0-1.0
    #     "persona_type": "coach",           # coach|anime|mentor|friend
    #     "daily_cap": 5,
    #     "timezone": "Asia/Shanghai",       # IANA 格式
    #     "active_slots": [                  # 分钟数格式
    #         {"dow": [0,1,2,3,4], "start_min": 480, "end_min": 540}
    #     ],
    #     "learning_style": "balanced",      # visual|auditory|kinesthetic|balanced
    #     "feedback_style": "balanced",      # direct|gentle|balanced
    #     "ai_verbosity": "balanced",        # concise|balanced|detailed
    #     "focus_duration_preference": 25,   # 分钟
    #     "enable_push": True,
    #     "enable_curiosity_push": True,
    # }

    # 推断偏好 (系统基于行为推断)
    inferred = Column(JSONB, nullable=False, default=dict)
    # 结构:
    # {
    #     "optimal_push_hours": [8, 12, 18],
    #     "content_difficulty_trend": 0.6,
    #     "engagement_pattern": "morning_focused",
    #     "suggested_depth_preference": 0.6,
    #     "depth_preference_confidence": 0.3,
    # }

    last_explicit_update = Column(DateTime, nullable=True)
    last_inferred_update = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def increment_version(self):
        self.version += 1
        return self.version
```

### 2. 创建数据库迁移

创建文件：`backend/alembic/versions/{timestamp}_create_user_preferences_center.py`

使用 `alembic revision -m "create_user_preferences_center"` 生成迁移文件，内容：

```python
def upgrade():
    op.create_table(
        'user_preferences_center',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('version', sa.Integer, default=1, nullable=False),
        sa.Column('schema_version', sa.Integer, default=1, nullable=False),
        sa.Column('explicit', sa.dialects.postgresql.JSONB, nullable=False, default={}),
        sa.Column('inferred', sa.dialects.postgresql.JSONB, nullable=False, default={}),
        sa.Column('last_explicit_update', sa.DateTime, nullable=True),
        sa.Column('last_inferred_update', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow),
    )
    op.create_index('ix_user_preferences_center_user_id', 'user_preferences_center', ['user_id'])

def downgrade():
    op.drop_table('user_preferences_center')
```

### 3. 添加偏好变更事件类型

修改文件：`backend/gateway/internal/cqrs/event/types.go`

在 EventType 常量中添加：
```go
// User Preferences events
EventPreferencesUpdated  EventType = "user.preferences.updated"
EventPreferencesInferred EventType = "user.preferences.inferred"
```

更新 StreamKey() 函数，将这些事件路由到 "cqrs:stream:user"。

### 4. 创建 Go 端偏好服务

创建文件：`backend/gateway/internal/service/user_preferences_service.go`

```go
package service

import (
    "context"
    "encoding/json"
    "fmt"
    "time"

    "github.com/google/uuid"
    "github.com/jackc/pgx/v5/pgxpool"
    "github.com/redis/go-redis/v9"
    "sparkle/backend/gateway/internal/cqrs/event"
)

type PreferencesUpdatedPayload struct {
    UserID            string   `json:"user_id"`
    PreferenceVersion int      `json:"preference_version"`
    ChangedKeys       []string `json:"changed_keys"`
    UpdatedAt         int64    `json:"updated_at"`
    Source            string   `json:"source"` // "explicit" | "inferred"
}

type UserPreferencesService struct {
    pool     *pgxpool.Pool
    eventBus event.EventBus
    redis    *redis.Client
}

func NewUserPreferencesService(pool *pgxpool.Pool, eventBus event.EventBus, redis *redis.Client) *UserPreferencesService {
    return &UserPreferencesService{pool: pool, eventBus: eventBus, redis: redis}
}

// UpdatePreferences 更新偏好并发布事件
func (s *UserPreferencesService) UpdatePreferences(
    ctx context.Context,
    userID uuid.UUID,
    updates map[string]interface{},
) error {
    tx, err := s.pool.Begin(ctx)
    if err != nil {
        return err
    }
    defer tx.Rollback(ctx)

    // 1. 更新数据库并增加版本号
    var newVersion int
    err = tx.QueryRow(ctx, `
        UPDATE user_preferences_center
        SET explicit = explicit || $2::jsonb,
            version = version + 1,
            last_explicit_update = NOW(),
            updated_at = NOW()
        WHERE user_id = $1
        RETURNING version
    `, userID, updates).Scan(&newVersion)

    if err != nil {
        return err
    }

    // 2. 构建事件
    changedKeys := make([]string, 0, len(updates))
    for k := range updates {
        changedKeys = append(changedKeys, k)
    }

    payload := PreferencesUpdatedPayload{
        UserID:            userID.String(),
        PreferenceVersion: newVersion,
        ChangedKeys:       changedKeys,
        UpdatedAt:         time.Now().UnixMilli(),
        Source:            "explicit",
    }

    payloadBytes, _ := json.Marshal(payload)
    evt := event.NewDomainEvent(
        event.EventPreferencesUpdated,
        event.AggregateUser,
        userID,
        map[string]interface{}{"data": string(payloadBytes)},
        event.EventMetadata{UserID: userID},
    )

    // 3. 发布事件（通过 Outbox 模式）
    if err := s.eventBus.PublishWithTx(ctx, tx, evt); err != nil {
        return err
    }

    // 4. 提交事务
    if err := tx.Commit(ctx); err != nil {
        return err
    }

    // 5. 立即删除 Redis 缓存（双保险）
    s.invalidateCache(ctx, userID)

    return nil
}

func (s *UserPreferencesService) invalidateCache(ctx context.Context, userID uuid.UUID) {
    keys := []string{
        fmt.Sprintf("user:context:%s", userID),
        fmt.Sprintf("user:preferences:%s", userID),
        fmt.Sprintf("user:analytics:%s", userID),
        fmt.Sprintf("user:stats:%s", userID),
    }
    s.redis.Del(ctx, keys...)
}
```

### 5. 创建 Python 端事件消费者

创建文件：`backend/app/services/preference_event_consumer.py`

```python
"""
偏好事件消费者 - 订阅 Go 发布的偏好变更事件，使 Python 端缓存失效
"""
import json
import asyncio
from uuid import UUID
from loguru import logger
from app.services.user_service import UserService

class PreferenceEventConsumer:
    """消费 user.preferences.updated 事件"""

    def __init__(self, redis_client, user_service: UserService):
        self.redis = redis_client
        self.user_service = user_service
        self.stream_key = "cqrs:stream:user"
        self.consumer_group = "python_preference_consumer"
        self.consumer_name = "worker-1"

    async def start(self):
        """启动事件消费循环"""
        # 创建 Consumer Group（如果不存在）
        try:
            await self.redis.xgroup_create(
                self.stream_key,
                self.consumer_group,
                id="0",
                mkstream=True
            )
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Failed to create consumer group: {e}")

        logger.info(f"PreferenceEventConsumer started, listening on {self.stream_key}")

        while True:
            try:
                messages = await self.redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.stream_key: ">"},
                    count=10,
                    block=1000,
                )

                for stream, entries in messages:
                    for entry_id, data in entries:
                        await self._handle_event(data)
                        await self.redis.xack(self.stream_key, self.consumer_group, entry_id)

            except Exception as e:
                logger.error(f"Error consuming events: {e}")
                await asyncio.sleep(1)

    async def _handle_event(self, data: dict):
        """处理单个事件"""
        event_type = data.get(b"type", b"").decode()

        if event_type == "user.preferences.updated":
            try:
                payload_str = data.get(b"payload", b"{}").decode()
                payload = json.loads(payload_str)
                inner_data = json.loads(payload.get("data", "{}"))

                user_id = UUID(inner_data["user_id"])
                version = inner_data["preference_version"]

                logger.info(f"Received preferences update for user {user_id}, version={version}")

                # 立即使缓存失效
                await self.user_service.invalidate_user_cache(user_id)

            except Exception as e:
                logger.error(f"Failed to handle preferences update event: {e}")
```

### 6. 修复时区处理

修改文件：`backend/app/services/user_service.py`

在 UserService 类中添加以下方法，并更新 get_context：

```python
def _normalize_active_slots(
    self,
    slots: Optional[List[Dict]],
    timezone: str
) -> Optional[Dict]:
    """
    将字符串格式的时间段转换为分钟数格式

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

在 get_context 方法中，更新 active_slots 处理：
```python
# 替换原有的 active_slots 处理代码
active_slots = self._normalize_active_slots(
    push_pref.active_slots if push_pref else None,
    push_pref.timezone if push_pref else "Asia/Shanghai"
)
```

### 7. 创建数据迁移脚本

创建文件：`backend/scripts/migrate_preferences_to_center.py`

```python
"""
将现有偏好数据迁移到 user_preferences_center 表
"""
import asyncio
from uuid import UUID
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User, PushPreference
from app.models.user_preferences import UserPreferencesCenter

async def migrate():
    async with AsyncSessionLocal() as db:
        # 获取所有用户
        result = await db.execute(select(User))
        users = result.scalars().all()

        for user in users:
            # 检查是否已迁移
            existing = await db.execute(
                select(UserPreferencesCenter).where(
                    UserPreferencesCenter.user_id == user.id
                )
            )
            if existing.scalar_one_or_none():
                continue

            # 获取推送偏好
            push_pref_result = await db.execute(
                select(PushPreference).where(PushPreference.user_id == user.id)
            )
            push_pref = push_pref_result.scalar_one_or_none()

            # 构建 explicit 偏好
            explicit = {
                "depth_preference": user.depth_preference,
                "curiosity_preference": user.curiosity_preference,
                "persona_type": push_pref.persona_type if push_pref else "coach",
                "daily_cap": push_pref.daily_cap if push_pref else 5,
                "timezone": push_pref.timezone if push_pref else "Asia/Shanghai",
                "enable_push": True,
                "enable_curiosity_push": push_pref.enable_curiosity if push_pref else True,
            }

            # 转换 active_slots
            if push_pref and push_pref.active_slots:
                explicit["active_slots"] = _convert_slots(push_pref.active_slots)

            # 创建偏好中心记录
            prefs = UserPreferencesCenter(
                user_id=user.id,
                explicit=explicit,
                inferred={},
            )
            db.add(prefs)

        await db.commit()
        print(f"Migrated {len(users)} users")

def _convert_slots(slots):
    """转换时间段格式"""
    if not slots:
        return []
    result = []
    for slot in slots:
        start = slot.get("start", "08:00")
        end = slot.get("end", "09:00")
        start_min = int(start.split(":")[0]) * 60 + int(start.split(":")[1])
        end_min = int(end.split(":")[0]) * 60 + int(end.split(":")[1])
        result.append({
            "dow": [0, 1, 2, 3, 4],
            "start_min": start_min,
            "end_min": end_min,
        })
    return result

if __name__ == "__main__":
    asyncio.run(migrate())
```

## 验收标准

1. [ ] 运行 `alembic upgrade head` 成功创建 user_preferences_center 表
2. [ ] 运行迁移脚本，现有用户数据成功迁移
3. [ ] Go 端 UpdatePreferences 能正确发布事件
4. [ ] Python 端消费者能接收事件并使缓存失效
5. [ ] 测试：通过 API 修改 persona 后，立即调用 AI 接口，AI 使用新 persona（不用等 30 分钟）
6. [ ] active_slots 正确转换为分钟数格式

## 测试命令

```bash
# 运行迁移
cd backend && alembic upgrade head
cd backend && python scripts/migrate_preferences_to_center.py

# 验证缓存失效
# 1. 记录当前 Redis 缓存
redis-cli GET "user:context:{user_id}"

# 2. 通过 API 更新偏好

# 3. 验证缓存被删除
redis-cli GET "user:context:{user_id}"  # 应该返回 nil
```



# Phase 2: Personalization Engine

## Agent Prompt

你是 Sparkle 项目的后端开发专家。Phase 1 已建立统一的偏好中心，现在需要创建 Personalization Engine，将用户偏好映射为各模块可用的策略配置。

## 项目背景

已完成：
- user_preferences_center 表（存储 explicit 和 inferred 偏好）
- Go/Python 缓存一致性（通过事件机制）

## 你的任务

### 1. 创建策略配置数据类

创建文件：`backend/app/services/personalization/profiles.py`

```python
"""
策略配置数据类 - 各模块的个性化参数
"""
from dataclasses import dataclass
from typing import List, Optional

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
    active_hours: List[int]           # 活跃时段（分钟数列表）
    timezone: str
    preference_version: int           # 偏好版本号

@dataclass
class TaskPlanProfile:
    """任务规划策略配置"""
    preferred_task_duration: int      # 偏好任务时长（分钟）
    difficulty_gradient: float        # 难度梯度 0-1
    micro_task_friendly: bool         # 是否适合微任务
    exploration_ratio: float          # 探索性任务比例 0-1
    review_priority: str              # "low" | "medium" | "high"
    fragmented_time_slots: List[dict] # 碎片时间段
```

### 2. 创建偏好服务

创建文件：`backend/app/services/personalization/preference_service.py`

```python
"""
偏好服务 - 统一的偏好数据访问层
"""
import json
from typing import Optional, Dict, Any
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user_preferences import UserPreferencesCenter

class PreferenceService:
    """偏好服务 - 带缓存的偏好数据访问"""

    DEFAULT_EXPLICIT = {
        "depth_preference": 0.5,
        "curiosity_preference": 0.5,
        "persona_type": "coach",
        "daily_cap": 5,
        "timezone": "Asia/Shanghai",
        "active_slots": [],
        "learning_style": "balanced",
        "feedback_style": "balanced",
        "ai_verbosity": "balanced",
        "focus_duration_preference": 25,
        "enable_push": True,
        "enable_curiosity_push": True,
    }

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.cache_ttl = 1800  # 30分钟

    async def get_preferences(self, user_id: UUID) -> UserPreferencesCenter:
        """获取用户偏好（带缓存）"""
        cache_key = f"user:prefs:center:{user_id}"

        # 尝试缓存
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    # 验证版本
                    db_version = await self._get_db_version(user_id)
                    if data.get("version") == db_version:
                        return self._dict_to_model(data)
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")

        # 数据库查询
        result = await self.db.execute(
            select(UserPreferencesCenter).where(
                UserPreferencesCenter.user_id == user_id
            )
        )
        prefs = result.scalar_one_or_none()

        if not prefs:
            # 创建默认偏好
            prefs = UserPreferencesCenter(
                user_id=user_id,
                explicit=self.DEFAULT_EXPLICIT.copy(),
                inferred={},
            )
            self.db.add(prefs)
            await self.db.commit()

        # 填充默认值
        prefs = self._fill_defaults(prefs)

        # 写入缓存
        if self.redis:
            try:
                await self.redis.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(self._model_to_dict(prefs), ensure_ascii=False)
                )
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")

        return prefs

    async def _get_db_version(self, user_id: UUID) -> int:
        """获取数据库中的版本号"""
        result = await self.db.execute(
            select(UserPreferencesCenter.version).where(
                UserPreferencesCenter.user_id == user_id
            )
        )
        version = result.scalar_one_or_none()
        return version or 0

    def _fill_defaults(self, prefs: UserPreferencesCenter) -> UserPreferencesCenter:
        """填充默认值"""
        for key, default in self.DEFAULT_EXPLICIT.items():
            if key not in prefs.explicit or prefs.explicit[key] is None:
                prefs.explicit[key] = default
        return prefs

    def _model_to_dict(self, prefs: UserPreferencesCenter) -> dict:
        return {
            "user_id": str(prefs.user_id),
            "version": prefs.version,
            "explicit": prefs.explicit,
            "inferred": prefs.inferred,
        }

    def _dict_to_model(self, data: dict) -> UserPreferencesCenter:
        prefs = UserPreferencesCenter(
            user_id=UUID(data["user_id"]),
            version=data["version"],
            explicit=data["explicit"],
            inferred=data["inferred"],
        )
        return prefs
```

### 3. 创建运行时上下文服务

创建文件：`backend/app/services/personalization/runtime_context_service.py`

```python
"""
运行时上下文服务 - 收集影响个性化的实时状态
"""
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import UUID
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.focus_session import FocusSession
from app.models.task import Task
from app.models.plan import Plan
from app.models.notification import PushHistory

class RuntimeContextService:
    """运行时上下文服务"""

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def get_runtime_context(self, user_id: UUID, timezone: str = "Asia/Shanghai") -> Dict[str, Any]:
        """获取运行时上下文"""
        return {
            "focus_session_active": await self._is_focus_active(user_id),
            "active_plan_count": await self._get_active_plan_count(user_id),
            "pending_task_count": await self._get_pending_task_count(user_id),
            "today_push_count": await self._get_today_push_count(user_id),
            "last_activity_minutes_ago": await self._get_last_activity_minutes(user_id),
            "current_local_hour": self._get_user_local_hour(timezone),
            "current_local_minute": self._get_user_local_minute(timezone),
        }

    async def _is_focus_active(self, user_id: UUID) -> bool:
        """检查是否有活跃的专注会话"""
        result = await self.db.execute(
            select(FocusSession).where(
                FocusSession.user_id == user_id,
                FocusSession.end_time.is_(None)
            )
        )
        return result.scalar_one_or_none() is not None

    async def _get_active_plan_count(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Plan.id)).where(
                Plan.user_id == user_id,
                Plan.status == "active"
            )
        )
        return result.scalar() or 0

    async def _get_pending_task_count(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status == "pending"
            )
        )
        return result.scalar() or 0

    async def _get_today_push_count(self, user_id: UUID) -> int:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(func.count(PushHistory.id)).where(
                PushHistory.user_id == user_id,
                PushHistory.created_at >= today_start
            )
        )
        return result.scalar() or 0

    async def _get_last_activity_minutes(self, user_id: UUID) -> int:
        """获取距离上次活动的分钟数"""
        # 简化实现：检查最近的任务更新
        result = await self.db.execute(
            select(Task.updated_at).where(
                Task.user_id == user_id
            ).order_by(Task.updated_at.desc()).limit(1)
        )
        last_update = result.scalar_one_or_none()
        if not last_update:
            return 9999

        delta = datetime.utcnow() - last_update
        return int(delta.total_seconds() / 60)

    def _get_user_local_hour(self, timezone: str) -> int:
        try:
            tz = ZoneInfo(timezone)
        except:
            tz = ZoneInfo("Asia/Shanghai")
        return datetime.now(tz).hour

    def _get_user_local_minute(self, timezone: str) -> int:
        try:
            tz = ZoneInfo(timezone)
        except:
            tz = ZoneInfo("Asia/Shanghai")
        now = datetime.now(tz)
        return now.hour * 60 + now.minute
```

### 4. 创建 Personalization Engine

创建文件：`backend/app/services/personalization/engine.py`

```python
"""
Personalization Engine - 偏好到策略的映射中心
"""
from typing import Optional, Dict
from uuid import UUID
from loguru import logger

from .profiles import LLMProfile, PushPolicyProfile, TaskPlanProfile
from .preference_service import PreferenceService
from .runtime_context_service import RuntimeContextService

class PersonalizationEngine:
    """
    个性化引擎 - 偏好到策略的映射中心

    设计原则：
    1. 显式偏好优先于推断偏好
    2. 运行时上下文可覆盖静态偏好
    3. 所有映射逻辑集中在此，避免各模块分散实现
    """

    def __init__(self, pref_service: PreferenceService, ctx_service: RuntimeContextService):
        self.pref_service = pref_service
        self.ctx_service = ctx_service

    async def get_llm_profile(
        self,
        user_id: UUID,
        session_context: Optional[Dict] = None,
        override_preferences: Optional[Dict] = None,
    ) -> LLMProfile:
        """生成 AI 系统策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)
        explicit = prefs.explicit.copy()

        # 应用覆盖（用于预览）
        if override_preferences:
            explicit.update(override_preferences)

        # 深度偏好映射
        depth = explicit.get("depth_preference", 0.5)
        verbosity = "detailed" if depth > 0.7 else ("concise" if depth < 0.3 else "balanced")
        temperature = 0.3 + (depth * 0.4)  # 0.3 - 0.7

        # 好奇心偏好映射
        curiosity = explicit.get("curiosity_preference", 0.5)
        exploration = "exploratory" if curiosity > 0.7 else ("focused" if curiosity < 0.3 else "moderate")

        # 反馈风格映射
        feedback_style = explicit.get("feedback_style", "balanced")
        tone = "playful" if feedback_style == "gentle" else "professional"

        # 角色映射
        persona = explicit.get("persona_type", "coach")
        persona_additions = self._get_persona_prompt_additions(persona)

        # 构建 system prompt 注入内容
        system_additions = f"""
## 用户偏好适配指令
- 回答详细程度：{verbosity}（depth_preference={depth:.2f}）
- 探索倾向：{exploration}（curiosity_preference={curiosity:.2f}）
- 语气风格：{tone}
{persona_additions}

根据用户偏好调整回答：
- 如果 verbosity=concise，控制在 3-5 句话内，直击要点
- 如果 verbosity=detailed，提供完整背景、示例和扩展内容
- 如果 exploration=exploratory，可以主动引入相关的有趣知识点
- 如果 exploration=focused，严格围绕用户问题，不发散
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
        user_id: UUID,
        override_preferences: Optional[Dict] = None,
    ) -> PushPolicyProfile:
        """生成推送系统策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)
        explicit = prefs.explicit.copy()
        inferred = prefs.inferred

        if override_preferences:
            explicit.update(override_preferences)

        timezone = explicit.get("timezone", "Asia/Shanghai")
        ctx = await self.ctx_service.get_runtime_context(user_id, timezone)

        # 基础配置
        daily_cap = explicit.get("daily_cap", 5)
        depth = explicit.get("depth_preference", 0.5)
        curiosity = explicit.get("curiosity_preference", 0.5)

        # 好奇心频率
        curiosity_freq = "high" if curiosity > 0.7 else ("low" if curiosity < 0.3 else "medium")

        # 自适应间隔（根据推断的连续忽略次数）
        consecutive_ignores = inferred.get("consecutive_ignores", 0)
        base_interval = 120  # 2 小时
        min_interval = min(base_interval * (1 + consecutive_ignores * 0.5), 360)  # 上限 6 小时

        # 活跃时段（转换为分钟数列表）
        active_hours = []
        slots = explicit.get("active_slots", [])
        for slot in slots:
            start = slot.get("start_min", 480)
            end = slot.get("end_min", 540)
            active_hours.extend(range(start, end))

        # 专注模式检测
        is_focusing = ctx.get("focus_session_active", False)

        return PushPolicyProfile(
            daily_cap=daily_cap,
            min_interval_minutes=int(min_interval),
            pressure_tolerance=depth,
            memory_urgency_threshold=0.3 if depth > 0.5 else 0.2,
            curiosity_frequency=curiosity_freq,
            silent_during_focus=is_focusing,
            active_hours=active_hours,
            timezone=timezone,
            preference_version=prefs.version,
        )

    async def get_task_plan_profile(
        self,
        user_id: UUID,
        override_preferences: Optional[Dict] = None,
    ) -> TaskPlanProfile:
        """生成任务规划策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)
        explicit = prefs.explicit.copy()

        if override_preferences:
            explicit.update(override_preferences)

        # 专注时长偏好
        focus_duration = explicit.get("focus_duration_preference", 25)
        depth = explicit.get("depth_preference", 0.5)
        curiosity = explicit.get("curiosity_preference", 0.5)

        # 难度梯度（深度偏好高 = 更陡的难度曲线）
        difficulty_gradient = 0.3 + (depth * 0.5)  # 0.3 - 0.8

        # 探索比例（好奇心偏好高 = 更多探索性任务）
        exploration_ratio = curiosity * 0.4  # 0 - 0.4

        # 碎片时间段（时长 <= 30 分钟的）
        slots = explicit.get("active_slots", [])
        fragmented = [s for s in slots if s.get("end_min", 0) - s.get("start_min", 0) <= 30]

        return TaskPlanProfile(
            preferred_task_duration=focus_duration,
            difficulty_gradient=difficulty_gradient,
            micro_task_friendly=len(fragmented) > 0,
            exploration_ratio=exploration_ratio,
            review_priority="high" if depth > 0.6 else ("medium" if depth > 0.3 else "low"),
            fragmented_time_slots=fragmented,
        )

    def _get_persona_prompt_additions(self, persona: str) -> str:
        """根据角色生成额外的 prompt 指令"""
        personas = {
            "coach": "- 角色：严格的学习教练，强调纪律和效率\n- 语气：直接、专业、有时略带督促",
            "anime": "- 角色：温柔可爱的二次元助手\n- 语气：甜美、鼓励、活泼，可以使用颜文字",
            "mentor": "- 角色：资深导师，提供深度指导\n- 语气：睿智、耐心、启发式提问",
            "friend": "- 角色：亲切的学习伙伴\n- 语气：轻松、友好、支持性",
        }
        return personas.get(persona, personas["coach"])
```

### 5. 创建工厂函数

创建文件：`backend/app/services/personalization/__init__.py`

```python
"""
Personalization 模块
"""
from sqlalchemy.ext.asyncio import AsyncSession

from .engine import PersonalizationEngine
from .preference_service import PreferenceService
from .runtime_context_service import RuntimeContextService
from .profiles import LLMProfile, PushPolicyProfile, TaskPlanProfile

def get_personalization_engine(db: AsyncSession, redis=None) -> PersonalizationEngine:
    """工厂函数：创建 PersonalizationEngine 实例"""
    pref_service = PreferenceService(db, redis)
    ctx_service = RuntimeContextService(db, redis)
    return PersonalizationEngine(pref_service, ctx_service)

__all__ = [
    "PersonalizationEngine",
    "PreferenceService",
    "RuntimeContextService",
    "LLMProfile",
    "PushPolicyProfile",
    "TaskPlanProfile",
    "get_personalization_engine",
]
```

## 验收标准

1. [ ] PersonalizationEngine 能正确生成 LLMProfile
2. [ ] PersonalizationEngine 能正确生成 PushPolicyProfile
3. [ ] PersonalizationEngine 能正确生成 TaskPlanProfile
4. [ ] 偏好到策略的映射逻辑清晰、可测试
5. [ ] 运行时上下文能正确检测专注模式
6. [ ] 所有 Profile 包含必要的字段

## 测试代码

```python
# 在 Python shell 中测试
import asyncio
from uuid import UUID
from app.services.personalization import get_personalization_engine
from app.db.session import AsyncSessionLocal

async def test():
    async with AsyncSessionLocal() as db:
        engine = get_personalization_engine(db)
        user_id = UUID("your-test-user-id")

        llm_profile = await engine.get_llm_profile(user_id)
        print(f"LLM Profile: verbosity={llm_profile.verbosity_target}, temp={llm_profile.temperature}")

        push_profile = await engine.get_push_policy_profile(user_id)
        print(f"Push Profile: cap={push_profile.daily_cap}, interval={push_profile.min_interval_minutes}min")

        task_profile = await engine.get_task_plan_profile(user_id)
        print(f"Task Profile: duration={task_profile.preferred_task_duration}min, exploration={task_profile.exploration_ratio}")

asyncio.run(test())
```


---

# Phase 3: AI 系统深度集成

## Agent Prompt

你是 Sparkle 项目的后端开发专家。Phase 2 已创建 PersonalizationEngine，现在需要将其集成到 AI Orchestrator，实现真正的个性化对话体验。

## 已完成

- PersonalizationEngine 可生成 LLMProfile
- LLMProfile 包含 system_prompt_additions、temperature 等

## 你的任务

### 1. 更新 Orchestrator 使用 PersonalizationEngine

修改文件：`backend/app/orchestration/orchestrator.py`

找到 `_build_user_context` 或类似方法，更新为：

```python
async def _build_user_context(self, user_id: str, session_id: str = None) -> Dict[str, Any]:
    """构建用户上下文，集成个性化引擎"""
    from app.services.personalization import get_personalization_engine

    # 获取基础用户信息
    user_context = await self.user_service.get_context(UUID(user_id))
    if not user_context:
        return {"user_id": user_id, "nickname": "同学"}

    # 获取个性化策略
    engine = get_personalization_engine(self.db, self.redis)
    llm_profile = await engine.get_llm_profile(UUID(user_id))

    # 获取偏好版本
    prefs = await engine.pref_service.get_preferences(UUID(user_id))

    return {
        "user_id": user_id,
        "nickname": user_context.nickname,
        "timezone": user_context.timezone,
        "preferences": user_context.preferences,
        "preference_version": prefs.version,
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

### 2. 更新 System Prompt 构建

修改文件：`backend/app/orchestration/prompts.py`

更新 `build_system_prompt` 函数：

```python
def build_system_prompt(
    user_context: dict,
    conversation_history: dict = None,
    prompt_version: str = "v1",
) -> str:
    """构建完整的 System Prompt，深度集成用户偏好"""

    # 获取 LLM Profile
    llm_profile = user_context.get("llm_profile", {})

    # 基础上下文格式化
    formatted_user_context = format_user_context(user_context)

    # 动态注入偏好指令（由 PersonalizationEngine 生成）
    preference_instructions = llm_profile.get(
        "system_prompt_additions",
        _get_default_preference_instructions(user_context)
    )

    # 历史对话格式化
    conversation_history_section = ""
    if conversation_history:
        conversation_history_section = format_conversation_history(conversation_history)

    # 使用模板构建
    prompt = AGENT_SYSTEM_PROMPT.format(
        user_context=formatted_user_context,
        preference_instructions=preference_instructions,
        conversation_history_section=conversation_history_section,
    )

    return prompt


def _get_default_preference_instructions(user_context: dict) -> str:
    """默认的偏好指令（兜底）"""
    prefs = user_context.get("preferences", {})
    depth = prefs.get("depth_preference", 0.5)
    curiosity = prefs.get("curiosity_preference", 0.5)

    depth_text = "深入详尽" if depth >= 0.7 else ("简洁概览" if depth < 0.3 else "适中")
    curiosity_text = "探索扩展" if curiosity >= 0.7 else ("专注聚焦" if curiosity < 0.3 else "适中")

    return f"""
## 用户偏好适配
- 回答深度：{depth_text}
- 探索倾向：{curiosity_text}
"""


# 更新模板
AGENT_SYSTEM_PROMPT = """你是 Sparkle（星火），一个智能学习助手。你的目标是帮助用户高效学习，同时保持学习的乐趣。

## 当前用户上下文
{user_context}

{preference_instructions}

## 对话历史
{conversation_history_section}

## 核心原则
1. 始终遵循用户的偏好设置，这是最重要的
2. 根据 verbosity 目标调整回答长度
3. 根据 exploration_level 决定是否扩展话题
4. 保持角色一致性
5. 提供准确、有帮助的回答
"""
```

### 3. 动态调整 LLM 参数

修改文件：`backend/app/services/llm_service.py`

在调用 LLM 的方法中，使用动态 temperature：

```python
async def _call_llm_stream(
    self,
    messages: List[Dict],
    user_context: Optional[Dict] = None,
    **kwargs
) -> AsyncGenerator[str, None]:
    """调用 LLM（流式），使用个性化参数"""

    # 从用户上下文获取 LLM Profile
    llm_profile = {}
    if user_context:
        llm_profile = user_context.get("llm_profile", {})

    # 动态 temperature（默认 0.5）
    temperature = llm_profile.get("temperature", 0.5)

    # 构建请求
    response = await self.client.chat.completions.create(
        model=self.model,
        messages=messages,
        temperature=temperature,  # 使用个性化的 temperature
        stream=True,
        **kwargs
    )

    async for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            yield content
```

### 4. 记录偏好版本到响应

在生成响应时，确保元数据包含 preference_version：

```python
# 在 ChatResponse 或类似的响应消息中添加
response_metadata = {
    "response_id": str(response_id),
    "trace_id": trace_id,
    "preference_version": user_context.get("preference_version", 0),
    "verbosity_target": llm_profile.get("verbosity_target", "balanced"),
}
```

## 验收标准

1. [ ] AI 回复风格随 persona_type 变化（coach 严肃 vs anime 可爱）
2. [ ] AI 回复详细度随 depth_preference 变化（0.2 简短 vs 0.9 详细）
3. [ ] AI 是否扩展话题随 curiosity_preference 变化
4. [ ] temperature 参数正确应用（可通过日志确认）
5. [ ] 响应元数据包含 preference_version

## 测试方法

1. 创建两个测试用户，分别设置：
   - 用户A: depth=0.2, curiosity=0.2, persona=coach
   - 用户B: depth=0.9, curiosity=0.9, persona=anime

2. 向两个用户发送相同问题："什么是机器学习？"

3. 验证：
   - 用户A 收到简短、专注的回答
   - 用户B 收到详细、可能扩展的回答，语气活泼

---

# Phase 4: 推送系统升级

## Agent Prompt

你是 Sparkle 项目的后端开发专家。现在需要将推送系统与 PersonalizationEngine 深度集成。

## 当前问题

1. 推送策略使用硬编码阈值（如 retention < 0.3）
2. 推送内容仅使用 persona_type，未结合 depth/curiosity
3. consecutive_ignores 字段从未更新

## 你的任务

### 1. 更新推送策略基类

修改文件：`backend/app/services/push_strategies/strategy.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, PushPreference
from app.models.task import Task, TaskStatus
from app.models.galaxy import UserNodeStatus, KnowledgeNode
from app.services.personalization import PushPolicyProfile

class PushStrategy(ABC):
    """推送策略基类 - 集成个性化引擎"""

    trigger_type: str = "unknown"

    def __init__(self, db: AsyncSession):
        self.db = db

    @abstractmethod
    async def should_trigger(
        self,
        user: User,
        policy: PushPolicyProfile
    ) -> bool:
        """判断是否应该触发推送（使用个性化策略）"""
        pass

    @abstractmethod
    async def get_context_data(self, user: User) -> Dict[str, Any]:
        """获取推送上下文数据"""
        pass


class MemoryStrategy(PushStrategy):
    """记忆临界点策略 - 个性化版本"""

    trigger_type = "memory"

    async def should_trigger(
        self,
        user: User,
        policy: PushPolicyProfile
    ) -> bool:
        # 使用个性化阈值
        urgency_threshold = policy.memory_urgency_threshold

        # 根据深度偏好调整重要性筛选
        importance_threshold = 5 if policy.pressure_tolerance > 0.6 else 3

        query = select(UserNodeStatus, KnowledgeNode).join(
            KnowledgeNode, UserNodeStatus.knowledge_node_id == KnowledgeNode.id
        ).where(
            UserNodeStatus.user_id == user.id,
            UserNodeStatus.mastery_score > 0.1,  # 至少学过
            UserNodeStatus.mastery_score < urgency_threshold,  # 个性化阈值
            KnowledgeNode.importance_level >= importance_threshold,
        ).order_by(
            UserNodeStatus.mastery_score.asc()
        ).limit(1)

        result = await self.db.execute(query)
        return result.first() is not None

    async def get_context_data(self, user: User) -> Dict[str, Any]:
        # 获取最需要复习的节点
        query = select(UserNodeStatus, KnowledgeNode).join(
            KnowledgeNode, UserNodeStatus.knowledge_node_id == KnowledgeNode.id
        ).where(
            UserNodeStatus.user_id == user.id,
            UserNodeStatus.mastery_score > 0.1,
            UserNodeStatus.mastery_score < 0.4,
        ).order_by(
            UserNodeStatus.mastery_score.asc()
        ).limit(1)

        result = await self.db.execute(query)
        row = result.first()

        if row:
            status, node = row
            return {
                "node_label": node.label,
                "current_mastery": status.mastery_score,
                "importance": node.importance_level,
            }
        return {}


class CuriosityStrategy(PushStrategy):
    """好奇心胶囊策略 - 个性化版本"""

    trigger_type = "curiosity"

    async def should_trigger(
        self,
        user: User,
        policy: PushPolicyProfile
    ) -> bool:
        # 根据好奇心频率决定触发概率
        if policy.curiosity_frequency == "low":
            return False

        import random
        frequency_map = {"low": 0, "medium": 0.3, "high": 0.6}
        trigger_probability = frequency_map.get(policy.curiosity_frequency, 0.3)

        return random.random() < trigger_probability

    async def get_context_data(self, user: User) -> Dict[str, Any]:
        return {"capsule_type": "curiosity"}


class SprintStrategy(PushStrategy):
    """冲刺提醒策略 - 个性化版本"""

    trigger_type = "sprint"

    async def should_trigger(
        self,
        user: User,
        policy: PushPolicyProfile
    ) -> bool:
        # 根据压力容忍度调整 DDL 阈值
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
        return result.first() is not None

    async def get_context_data(self, user: User) -> Dict[str, Any]:
        now = datetime.utcnow()
        query = select(Task).where(
            Task.user_id == user.id,
            Task.status == TaskStatus.PENDING,
            Task.deadline.isnot(None),
            Task.deadline > now,
        ).order_by(Task.deadline.asc()).limit(1)

        result = await self.db.execute(query)
        task = result.scalar_one_or_none()

        if task:
            hours_left = (task.deadline - now).total_seconds() / 3600
            return {
                "task_title": task.title,
                "hours_left": int(hours_left),
                "deadline": task.deadline.isoformat(),
            }
        return {}


class InactivityStrategy(PushStrategy):
    """唤醒策略 - 个性化版本"""

    trigger_type = "inactivity"

    async def should_trigger(
        self,
        user: User,
        policy: PushPolicyProfile
    ) -> bool:
        # 简化：检查最后活动时间
        if not user.last_login_at:
            return True

        hours_inactive = (datetime.utcnow() - user.last_login_at).total_seconds() / 3600
        return hours_inactive >= 24

    async def get_context_data(self, user: User) -> Dict[str, Any]:
        return {"reason": "长时间未学习"}
```

### 2. 更新 PushService

修改文件：`backend/app/services/push_service.py`

```python
# 在现有 PushService 类中更新

async def process_user_push(self, user: User) -> bool:
    """处理单个用户的推送（集成个性化引擎）"""
    from app.services.personalization import get_personalization_engine

    # 1. 获取个性化策略
    engine = get_personalization_engine(self.db, self.redis)
    policy = await engine.get_push_policy_profile(user.id)

    # 2. 专注模式检查
    if policy.silent_during_focus:
        logger.info(f"User {user.id} is in focus mode, skipping push")
        return False

    # 3. 活跃时间检查
    if not self._is_active_time(policy):
        return False

    # 4. 频控检查
    if await self._check_frequency_cap(user, policy):
        return False

    # 5. 评估策略优先级
    strategies = [
        SprintStrategy(self.db),
        MemoryStrategy(self.db),
        CuriosityStrategy(self.db),
        InactivityStrategy(self.db),
    ]

    for strategy in strategies:
        if await strategy.should_trigger(user, policy):
            context_data = await strategy.get_context_data(user)
            await self._send_push(user, strategy.trigger_type, context_data, policy)
            return True

    return False

def _is_active_time(self, policy: PushPolicyProfile) -> bool:
    """检查是否在活跃时间段"""
    from zoneinfo import ZoneInfo

    try:
        tz = ZoneInfo(policy.timezone)
    except:
        tz = ZoneInfo("Asia/Shanghai")

    now = datetime.now(tz)
    current_minutes = now.hour * 60 + now.minute

    # 检查是否在活跃时段
    if policy.active_hours:
        return current_minutes in policy.active_hours

    # 默认活跃时段：8:00-22:00
    return 480 <= current_minutes <= 1320

async def _check_frequency_cap(
    self,
    user: User,
    policy: PushPolicyProfile
) -> bool:
    """频控检查（使用个性化间隔）"""
    prefs = user.push_preference
    if not prefs:
        return False

    # 使用个性化的最小间隔
    min_interval = timedelta(minutes=policy.min_interval_minutes)

    if prefs.last_push_time:
        if datetime.utcnow() - prefs.last_push_time < min_interval:
            return True  # 冷却中

    # 日上限检查
    today_count = await self._get_today_push_count(user.id)
    return today_count >= policy.daily_cap
```

### 3. 更新推送内容生成

修改文件：`backend/app/services/llm_service.py`

在 `generate_push_content` 方法中添加 depth/curiosity 参数：

```python
async def generate_push_content(
    self,
    user_nickname: str,
    persona: str,
    trigger_type: str,
    context_data: Dict,
    depth_preference: float = 0.5,
    curiosity_preference: float = 0.5,
) -> Dict[str, str]:
    """生成推送内容（个性化版本）"""

    # 根据深度偏好调整内容详细度
    if depth_preference > 0.7:
        detail_instruction = "提供详细的背景信息和具体建议。"
    elif depth_preference < 0.3:
        detail_instruction = "保持极简，一句话点明重点即可。"
    else:
        detail_instruction = "适中详细度，2-3句话。"

    # 根据好奇心偏好调整是否扩展
    exploration_instruction = ""
    if curiosity_preference > 0.6:
        exploration_instruction = "可以附带一个有趣的相关知识点或冷知识。"

    persona_prompts = {
        "coach": f"Role: Strict Study Coach. Tone: Urgent, disciplined. {detail_instruction}",
        "anime": f"Role: Cute Anime Assistant. Tone: Sweet, encouraging, use emoticons. {detail_instruction}",
        "mentor": f"Role: Wise Mentor. Tone: Insightful, patient. {detail_instruction}",
        "friend": f"Role: Friendly Study Buddy. Tone: Casual, supportive. {detail_instruction}",
    }

    system_prompt = persona_prompts.get(persona, persona_prompts["coach"])
    system_prompt += f"\n{exploration_instruction}"

    # ... 继续调用 LLM 生成内容
```

### 4. 实现反馈闭环

创建文件：`backend/app/services/push_feedback_service.py`

```python
"""
推送反馈服务 - 更新 consecutive_ignores
"""
from uuid import UUID
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.user import PushPreference
from app.models.notification import PushHistory

class PushFeedbackService:
    """推送反馈服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_push_interaction(
        self,
        user_id: UUID,
        push_id: UUID,
        interaction_type: str,  # "clicked" | "dismissed" | "ignored"
    ):
        """记录推送交互"""

        # 更新推送记录
        await self.db.execute(
            update(PushHistory).where(
                PushHistory.id == push_id
            ).values(
                interaction_type=interaction_type,
                interacted_at=datetime.utcnow()
            )
        )

        # 更新 consecutive_ignores
        result = await self.db.execute(
            select(PushPreference).where(PushPreference.user_id == user_id)
        )
        push_pref = result.scalar_one_or_none()

        if push_pref:
            if interaction_type == "clicked":
                push_pref.consecutive_ignores = 0
            elif interaction_type in ("dismissed", "ignored"):
                push_pref.consecutive_ignores = (push_pref.consecutive_ignores or 0) + 1

            await self.db.commit()
            logger.info(
                f"Updated consecutive_ignores for user {user_id}: "
                f"{push_pref.consecutive_ignores}"
            )
```

## 验收标准

1. [ ] MemoryStrategy 使用个性化的 urgency_threshold
2. [ ] SprintStrategy 使用个性化的 DDL 阈值（72-144小时）
3. [ ] CuriosityStrategy 使用 curiosity_frequency 设置
4. [ ] 推送内容详细度随 depth_preference 变化
5. [ ] consecutive_ignores 在用户交互后正确更新
6. [ ] 专注模式下推送被静默
```

---

# Phase 5: 任务系统闭环

## Agent Prompt

```
你是 Sparkle 项目的后端开发专家。现在需要修复任务完成与知识图谱的断层。

## 当前问题

TaskService.complete() 未调用 galaxy_service.spark_node()，导致：
- mastery_score 不更新
- 遗忘曲线不计算
- 学习行为成为"死胡同"

## 你的任务

### 1. 修复任务完成 → 知识图谱链路

修改文件：`backend/app/api/v1/tasks.py`

在 `complete_task` 端点中添加知识图谱更新：

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
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == current_user.id
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == TaskStatus.COMPLETED:
        return {"task": task, "message": "Task already completed"}

    # 2. 更新任务状态
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    task.actual_minutes = request.actual_minutes
    await db.commit()

    # 3. 更新计划进度（如果有关联计划）
    plan_update_result = None
    if task.plan_id:
        from app.services.plan_service import PlanService
        plan_service = PlanService(db)
        plan_update_result = await plan_service.update_progress(task.plan_id, task.user_id)

    # 4. 【关键】更新知识图谱
    spark_result = None
    if task.knowledge_node_id:
        from app.services.galaxy_service import GalaxyService

        galaxy_service = GalaxyService(db)
        study_minutes = request.actual_minutes or task.estimated_minutes or 15

        try:
            spark_result = await galaxy_service.spark_node(
                user_id=current_user.id,
                node_id=task.knowledge_node_id,
                study_minutes=study_minutes,
                task_id=task.id,
                trigger_expansion=True,
            )

            logger.info(
                f"Task {task_id} completion triggered galaxy spark: "
                f"node={task.knowledge_node_id}, "
                f"new_mastery={spark_result.new_mastery_score if spark_result else 'N/A'}"
            )
        except Exception as e:
            logger.error(f"Failed to spark node after task completion: {e}")

    # 5. 生成 AI 反馈（可选）
    feedback = None
    try:
        from app.services.task_feedback_service import TaskFeedbackService
        feedback_service = TaskFeedbackService(db)
        feedback = await feedback_service.generate_feedback(task, current_user, db)
    except Exception as e:
        logger.warning(f"Failed to generate feedback: {e}")

    return {
        "task": {
            "id": str(task.id),
            "title": task.title,
            "status": task.status.value,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "actual_minutes": task.actual_minutes,
        },
        "plan_update": plan_update_result,
        "galaxy_update": {
            "node_id": str(task.knowledge_node_id) if task.knowledge_node_id else None,
            "new_mastery": spark_result.new_mastery_score if spark_result else None,
            "next_review_at": spark_result.next_review_at.isoformat() if spark_result and spark_result.next_review_at else None,
        } if task.knowledge_node_id else None,
        "feedback": feedback,
    }
```

### 2. 确保 GalaxyService.spark_node 存在且完整

检查文件：`backend/app/services/galaxy_service.py`（或类似路径）

确保 spark_node 方法包含以下逻辑：

```python
async def spark_node(
    self,
    user_id: UUID,
    node_id: UUID,
    study_minutes: int,
    task_id: Optional[UUID] = None,
    trigger_expansion: bool = False,
) -> SparkResult:
    """
    记录学习行为，更新掌握度

    Args:
        user_id: 用户 ID
        node_id: 知识节点 ID
        study_minutes: 学习时长（分钟）
        task_id: 关联的任务 ID（可选）
        trigger_expansion: 是否触发 LLM 扩展

    Returns:
        SparkResult: 包含新的掌握度、下次复习时间等
    """
    # 1. 获取或创建用户节点状态
    status = await self._get_or_create_status(user_id, node_id)

    # 2. 计算掌握度增量
    mastery_delta = self._calculate_mastery_delta(study_minutes, status.study_count)

    # 3. 更新掌握度
    old_mastery = status.mastery_score
    status.mastery_score = min(status.mastery_score + mastery_delta, 1.0)
    status.study_count += 1
    status.total_study_minutes += study_minutes
    status.last_study_at = datetime.utcnow()

    # 4. 计算下次复习时间（遗忘曲线）
    status.next_review_at = self._calculate_next_review(status.mastery_score, status.study_count)

    # 5. 创建学习记录
    study_record = StudyRecord(
        user_id=user_id,
        knowledge_node_id=node_id,
        task_id=task_id,
        study_minutes=study_minutes,
        mastery_before=old_mastery,
        mastery_after=status.mastery_score,
    )
    self.db.add(study_record)

    await self.db.commit()

    # 6. 触发 LLM 扩展（如果满足条件）
    expansion_triggered = False
    if trigger_expansion and status.study_count >= 2:
        try:
            await self._trigger_expansion(user_id, node_id)
            expansion_triggered = True
        except Exception as e:
            logger.warning(f"Expansion trigger failed: {e}")

    return SparkResult(
        node_id=node_id,
        old_mastery_score=old_mastery,
        new_mastery_score=status.mastery_score,
        mastery_delta=mastery_delta,
        study_count=status.study_count,
        next_review_at=status.next_review_at,
        expansion_triggered=expansion_triggered,
    )

def _calculate_mastery_delta(self, study_minutes: int, study_count: int) -> float:
    """计算掌握度增量"""
    # 基础增量
    base_delta = min(study_minutes / 60, 0.2)  # 上限 0.2

    # 递减因子（学习次数越多，增量越小）
    decay_factor = 1 / (1 + study_count * 0.1)

    return base_delta * decay_factor

def _calculate_next_review(self, mastery: float, study_count: int) -> datetime:
    """计算下次复习时间（基于遗忘曲线）"""
    # Ebbinghaus 遗忘曲线简化实现
    # 掌握度越高，复习间隔越长
    base_hours = 24  # 基础间隔 24 小时

    # 间隔 = 基础间隔 * 掌握度 * 学习次数因子
    interval_hours = base_hours * (1 + mastery * 3) * (1 + study_count * 0.5)

    # 上限 30 天
    interval_hours = min(interval_hours, 24 * 30)

    return datetime.utcnow() + timedelta(hours=interval_hours)
```

### 3. 创建碎片时间微任务 API

修改文件：`backend/app/api/v1/tasks.py`

添加新端点：

```python
@router.get("/recommendations/micro", response_model=List[TaskRecommendationResponse])
async def get_micro_task_recommendations(
    context: Optional[str] = Query(None, description="上下文: commute, lunch, evening"),
    limit: int = Query(3, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    """
    获取碎片时间微任务推荐

    根据用户偏好和知识图谱状态，推荐适合在碎片时间完成的微任务。
    """
    from app.services.personalization import get_personalization_engine
    from app.services.task_recommendation_service import TaskRecommendationService

    engine = get_personalization_engine(db, redis)
    service = TaskRecommendationService(db, engine)

    recommendations = await service.get_recommendations(
        user_id=current_user.id,
        limit=limit * 2,  # 多获取一些再过滤
        context=context,
    )

    # 过滤出微任务（≤15 分钟）
    micro_tasks = [r for r in recommendations if r.estimated_minutes <= 15]

    return micro_tasks[:limit]
```

### 4. 创建任务推荐服务

创建文件：`backend/app/services/task_recommendation_service.py`

```python
"""
任务推荐服务 - 基于用户偏好和知识图谱
"""
from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.galaxy import UserNodeStatus, KnowledgeNode
from app.services.personalization import PersonalizationEngine, TaskPlanProfile

@dataclass
class TaskRecommendation:
    knowledge_node_id: UUID
    title: str
    estimated_minutes: int
    task_type: str  # "review" | "micro_review" | "exploration"
    difficulty: int
    priority: float
    reason: str

class TaskRecommendationService:
    """任务推荐服务"""

    def __init__(self, db: AsyncSession, engine: PersonalizationEngine):
        self.db = db
        self.engine = engine

    async def get_recommendations(
        self,
        user_id: UUID,
        limit: int = 5,
        context: Optional[str] = None,
    ) -> List[TaskRecommendation]:
        """获取个性化任务推荐"""

        # 1. 获取任务规划策略
        profile = await self.engine.get_task_plan_profile(user_id)

        # 2. 获取待复习知识点
        review_nodes = await self._get_review_candidates(user_id, profile)

        # 3. 计算复习/探索比例
        review_count = int(limit * (1 - profile.exploration_ratio))

        recommendations = []

        # 复习任务
        for row in review_nodes[:review_count]:
            status, node = row
            task = self._create_review_task(status, node, profile, context)
            recommendations.append(task)

        return recommendations

    async def _get_review_candidates(
        self,
        user_id: UUID,
        profile: TaskPlanProfile
    ):
        """获取待复习知识点"""
        priority_threshold = {
            "high": 0.4,
            "medium": 0.3,
            "low": 0.2,
        }.get(profile.review_priority, 0.3)

        query = select(UserNodeStatus, KnowledgeNode).join(
            KnowledgeNode, UserNodeStatus.knowledge_node_id == KnowledgeNode.id
        ).where(
            UserNodeStatus.user_id == user_id,
            UserNodeStatus.mastery_score < priority_threshold,
            UserNodeStatus.mastery_score > 0.05,
        ).order_by(
            UserNodeStatus.next_review_at.asc().nullsfirst()
        ).limit(10)

        result = await self.db.execute(query)
        return result.all()

    def _create_review_task(
        self,
        status: UserNodeStatus,
        node: KnowledgeNode,
        profile: TaskPlanProfile,
        context: Optional[str],
    ) -> TaskRecommendation:
        """创建复习任务"""
        # 根据上下文调整时长
        if context in ("commute", "lunch") and profile.micro_task_friendly:
            duration = min(15, profile.preferred_task_duration)
            task_type = "micro_review"
        else:
            duration = profile.preferred_task_duration
            task_type = "review"

        # 计算优先级
        priority = (1 - status.mastery_score) * node.importance_level / 10

        # 计算距离上次学习的天数
        days_since = 0
        if status.last_study_at:
            days_since = (datetime.utcnow() - status.last_study_at).days

        return TaskRecommendation(
            knowledge_node_id=node.id,
            title=f"复习: {node.label}",
            estimated_minutes=duration,
            task_type=task_type,
            difficulty=node.difficulty or 1,
            priority=priority,
            reason=f"掌握度 {status.mastery_score:.0%}，距上次学习 {days_since} 天",
        )
```

## 验收标准

1. [ ] 任务完成后 mastery_score 正确更新
2. [ ] 任务完成后 next_review_at 正确计算
3. [ ] 任务完成后返回 galaxy_update 信息
4. [ ] 微任务 API 返回 ≤15 分钟的任务
5. [ ] 任务推荐考虑 review_priority 设置

## 测试方法

1. 创建一个绑定知识节点的任务
2. 完成任务，检查返回的 galaxy_update
3. 查询该节点的 UserNodeStatus，确认 mastery_score 增加
4. 调用 /tasks/recommendations/micro?context=commute，确认返回微任务
```

---

# Phase 6: 可视化与反馈

## Agent Prompt

```
你是 Sparkle 项目的后端开发专家。现在需要实现偏好效果的可视化和反馈机制。

## 你的任务

### 1. 创建偏好效果预览 API

创建文件：`backend/app/api/v1/preferences.py`

```python
"""
偏好 API - 预览和生效证明
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.personalization import get_personalization_engine

router = APIRouter(prefix="/preferences", tags=["preferences"])


class PreferencePreviewRequest(BaseModel):
    preview_preferences: Dict[str, Any]


class PreferencePreviewResponse(BaseModel):
    ai_sample: str
    push_sample: str
    task_summary: str
    effect_summary: str


@router.post("/preview", response_model=PreferencePreviewResponse)
async def preview_preference_effects(
    request: PreferencePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    预览偏好调整后的效果

    在用户保存偏好之前，展示调整后系统会如何响应。
    """
    from app.services.llm_service import get_llm_service

    engine = get_personalization_engine(db)
    llm_service = get_llm_service()

    # 使用预览偏好生成 LLM Profile
    llm_profile = await engine.get_llm_profile(
        current_user.id,
        override_preferences=request.preview_preferences
    )

    # 生成 AI 回复示例
    ai_sample = await _generate_ai_sample(llm_service, llm_profile)

    # 生成推送内容示例
    push_sample = await _generate_push_sample(
        llm_service,
        request.preview_preferences
    )

    # 生成任务推荐摘要
    task_profile = await engine.get_task_plan_profile(
        current_user.id,
        override_preferences=request.preview_preferences
    )
    task_summary = _generate_task_summary(task_profile)

    # 生成效果总结
    effect_summary = _generate_effect_summary(request.preview_preferences)

    return PreferencePreviewResponse(
        ai_sample=ai_sample,
        push_sample=push_sample,
        task_summary=task_summary,
        effect_summary=effect_summary,
    )


async def _generate_ai_sample(llm_service, llm_profile) -> str:
    """生成 AI 回复示例"""
    sample_question = "什么是机器学习？请简单介绍一下。"

    messages = [
        {"role": "system", "content": f"你是一个学习助手。{llm_profile.system_prompt_additions}"},
        {"role": "user", "content": sample_question},
    ]

    try:
        response = await llm_service.generate_simple(
            messages=messages,
            temperature=llm_profile.temperature,
            max_tokens=200,
        )
        return response
    except Exception as e:
        return f"[预览生成失败: {e}]"


async def _generate_push_sample(llm_service, prefs: Dict) -> str:
    """生成推送内容示例"""
    persona = prefs.get("persona_type", "coach")
    depth = prefs.get("depth_preference", 0.5)

    detail_level = "详细" if depth > 0.7 else ("简洁" if depth < 0.3 else "适中")

    persona_styles = {
        "coach": f"【严格教练风格 | {detail_level}】该复习「数据结构」了！你的掌握度只有 35%，不抓紧就要忘光了。",
        "anime": f"【可爱助手风格 | {detail_level}】主人~ 「数据结构」想你啦！(◕ᴗ◕✿) 掌握度 35%，一起来复习吧~",
        "mentor": f"【导师风格 | {detail_level}】根据遗忘曲线分析，「数据结构」已进入关键复习期。建议抽 15 分钟回顾核心概念。",
        "friend": f"【伙伴风格 | {detail_level}】嘿，「数据结构」有点生疏了，要不一起看看？不用太久，15 分钟就好。",
    }

    return persona_styles.get(persona, persona_styles["coach"])


def _generate_task_summary(profile) -> str:
    """生成任务推荐摘要"""
    return (
        f"推荐任务时长：{profile.preferred_task_duration} 分钟\n"
        f"难度梯度：{profile.difficulty_gradient:.0%}\n"
        f"探索任务比例：{profile.exploration_ratio:.0%}\n"
        f"复习优先级：{profile.review_priority}"
    )


def _generate_effect_summary(prefs: Dict) -> str:
    """生成效果总结"""
    summaries = []

    depth = prefs.get("depth_preference", 0.5)
    if depth > 0.7:
        summaries.append("AI 将提供详细深入的解答")
    elif depth < 0.3:
        summaries.append("AI 将提供简洁精炼的解答")

    curiosity = prefs.get("curiosity_preference", 0.5)
    if curiosity > 0.7:
        summaries.append("系统将主动推荐相关知识扩展")
    elif curiosity < 0.3:
        summaries.append("系统将专注于您当前的学习内容")

    persona = prefs.get("persona_type", "coach")
    persona_names = {
        "coach": "严格教练",
        "anime": "可爱助手",
        "mentor": "智慧导师",
        "friend": "友好伙伴"
    }
    summaries.append(f"AI 将以「{persona_names.get(persona, persona)}」的风格与您互动")

    return "；".join(summaries) + "。"


# 偏好生效证明
class DecisionRecord(BaseModel):
    timestamp: datetime
    module: str
    action: str
    preference_version: int
    outcome: str


class EffectivenessResponse(BaseModel):
    records: List[DecisionRecord]
    total_decisions: int
    modules_summary: Dict[str, int]


@router.get("/effectiveness", response_model=EffectivenessResponse)
async def get_preference_effectiveness(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取偏好生效证明

    展示最近的系统决策记录，证明偏好正在被使用。
    """
    from app.services.decision_record_service import DecisionRecordService

    service = DecisionRecordService(db)
    records = await service.get_recent_records(current_user.id, limit)

    modules_summary = {}
    for r in records:
        modules_summary[r.module] = modules_summary.get(r.module, 0) + 1

    return EffectivenessResponse(
        records=[
            DecisionRecord(
                timestamp=r.created_at,
                module=r.module,
                action=r.action,
                preference_version=r.preference_version,
                outcome=r.outcome,
            )
            for r in records
        ],
        total_decisions=len(records),
        modules_summary=modules_summary,
    )
```

### 2. 创建决策记录服务

创建文件：`backend/app/services/decision_record_service.py`

```python
"""
决策记录服务 - 记录系统决策及使用的偏好版本
"""
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.decision_record import DecisionRecord as DecisionRecordModel

class DecisionRecordService:
    """决策记录服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_decision(
        self,
        user_id: UUID,
        module: str,
        action: str,
        preference_version: int,
        preferences_snapshot: Dict[str, Any],
        outcome: str,
    ):
        """记录一次决策"""
        record = DecisionRecordModel(
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

    async def get_recent_records(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[DecisionRecordModel]:
        """获取最近的决策记录"""
        result = await self.db.execute(
            select(DecisionRecordModel).where(
                DecisionRecordModel.user_id == user_id
            ).order_by(
                DecisionRecordModel.created_at.desc()
            ).limit(limit)
        )
        return result.scalars().all()
```

### 3. 创建决策记录模型

创建文件：`backend/app/models/decision_record.py`

```python
"""
决策记录模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from app.db.base_class import BaseModel

class DecisionRecord(BaseModel):
    """系统决策记录"""
    __tablename__ = "decision_records"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    module = Column(String(50), nullable=False, index=True)  # "ai" | "push" | "task"
    action = Column(String(100), nullable=False)
    preference_version = Column(Integer, nullable=False)
    preferences_snapshot = Column(JSONB, nullable=True)
    outcome = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
```

### 4. 在关键决策点插入记录

修改文件：`backend/app/orchestration/orchestrator.py`

在生成响应后添加决策记录：

```python
# 在 _generate_response 或类似方法的末尾添加
from app.services.decision_record_service import DecisionRecordService

# 记录决策
try:
    decision_service = DecisionRecordService(self.db)
    await decision_service.record_decision(
        user_id=UUID(user_id),
        module="ai",
        action="generate_response",
        preference_version=user_context.get("preference_version", 0),
        preferences_snapshot={
            "verbosity": llm_profile.get("verbosity_target"),
            "temperature": llm_profile.get("temperature"),
            "tone": llm_profile.get("tone"),
        },
        outcome=f"Generated response with {len(full_text)} chars",
    )
except Exception as e:
    logger.warning(f"Failed to record decision: {e}")
```

修改文件：`backend/app/services/push_service.py`

在发送推送后添加决策记录：

```python
# 在 _send_push 方法末尾添加
from app.services.decision_record_service import DecisionRecordService

try:
    decision_service = DecisionRecordService(self.db)
    await decision_service.record_decision(
        user_id=user.id,
        module="push",
        action=f"send_{trigger_type}",
        preference_version=policy.preference_version,
        preferences_snapshot={
            "daily_cap": policy.daily_cap,
            "persona_type": user.push_preference.persona_type if user.push_preference else "coach",
            "curiosity_frequency": policy.curiosity_frequency,
        },
        outcome=f"Sent {trigger_type} push notification",
    )
except Exception as e:
    logger.warning(f"Failed to record push decision: {e}")
```

### 5. 注册路由

修改文件：`backend/app/api/v1/__init__.py`

添加偏好路由：

```python
from app.api.v1.preferences import router as preferences_router

api_router.include_router(preferences_router)
```

## 验收标准

1. [ ] POST /preferences/preview 返回 AI、推送、任务的预览
2. [ ] GET /preferences/effectiveness 返回最近决策记录
3. [ ] 决策记录包含 preference_version 和 preferences_snapshot
4. [ ] AI 响应后正确记录决策
5. [ ] 推送发送后正确记录决策

## 测试方法

1. 调用 POST /preferences/preview 预览不同偏好的效果
2. 进行几次 AI 对话
3. 调用 GET /preferences/effectiveness 查看决策记录
4. 确认记录包含正确的 module、action 和 preference_version
```

---

## 总结

本文档包含 6 个分阶段的 Agent Prompt，按顺序执行可完成用户偏好系统的全链路重构：

| Phase | 核心交付 | 关键文件 |
|-------|---------|---------|
| 1 | 偏好中心 + 事件总线 | `user_preferences.py`, `types.go`, `preference_event_consumer.py` |
| 2 | Personalization Engine | `engine.py`, `profiles.py`, `preference_service.py` |
| 3 | AI 系统集成 | `orchestrator.py`, `prompts.py`, `llm_service.py` |
| 4 | 推送系统升级 | `strategy.py`, `push_service.py`, `push_feedback_service.py` |
| 5 | 任务系统闭环 | `tasks.py`, `galaxy_service.py`, `task_recommendation_service.py` |
| 6 | 可视化与反馈 | `preferences.py`, `decision_record_service.py` |

每个 Phase 独立可验收，完成后系统应该能够：
- 偏好变更 ≤5 秒内全局生效
- 每次 AI/推送/任务决策都可追溯偏好版本
- 用户能预览偏好效果并查看生效证明
