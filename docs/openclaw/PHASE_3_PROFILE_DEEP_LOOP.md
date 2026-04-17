# Phase 3: 用户画像深度闭环 — "执行让AI更懂你"

> **交给Coding Agent执行的完整指令**
> **预计改动**: 2个新文件, 5个修改文件 (全部Python后端)
> **依赖**: Phase 2 已完成

---

## 背景

Phase 2 打通了对话→执行链路。本阶段让每次执行不仅完成任务, 还加深AI对用户的理解。当前 `ExecutionLearningService` 已有3条学习信号(trust building / aversion / time learning), 但信号维度太粗, 且未与认知棱镜(CognitiveService)深度整合。

### 关键现有代码

- `ExecutionLearningService` (backend/app/services/execution_learning_service.py) — 3条学习信号
- `CognitiveService` (backend/app/services/cognitive_service.py) — 认知片段+行为模式
- `ProfileContextService` (backend/app/services/profile_context_service.py) — 画像→策略映射
- `AdaptiveReplanner` (backend/app/orchestration/adaptive_replanner.py) — 计划自适应调整
- `ProfileWriteService` (backend/app/services/profile_write_service.py) — 画像写入
- `ExecutionIngestor` (backend/app/services/execution_ingestor.py) — 摄取入口

---

## 任务 3.1: 扩展ExecutionLearningService的信号维度

**修改文件**: `backend/app/services/execution_learning_service.py`

### 修改目标

在现有3条信号基础上, 新增4条细粒度信号, 使画像从"信不信任AI"进化为"什么场景下信任AI做什么"。

### 精确修改

#### 1. 新增类常量

在类定义顶部(约line 29-37, 现有常量附近), 添加:

```python
# Phase 3: 扩展信号
APPROVAL_SPEED_FAST_THRESHOLD_SECONDS = 15  # 确认耗时<15s视为"快速确认"
APPROVAL_SPEED_SLOW_THRESHOLD_SECONDS = 120  # 确认耗时>120s视为"长时间审查"
TASK_TYPE_DELEGATION_WINDOW = 20  # 统计最近20次执行
QUALITY_SATISFACTION_WINDOW = 10  # 统计最近10次确认/拒绝
```

#### 2. 新增方法: 审批速度信号

```python
async def handle_approval_speed_signal(
    self,
    *,
    intent: "ExecutionIntent",
    record: "ExecutionRecord",
    waiting_started_at: datetime | None,
    decided_at: datetime | None,
    decision: str,  # "confirmed" | "rejected"
) -> None:
    """Learn from how quickly user reviews AI results.

    Fast confirmation → high trust for this task type.
    Slow review → user is cautious, needs more detail next time.
    """
    if not waiting_started_at or not decided_at:
        return

    review_seconds = (decided_at - waiting_started_at).total_seconds()

    if review_seconds < self.APPROVAL_SPEED_FAST_THRESHOLD_SECONDS and decision == "confirmed":
        # 快速确认 — 高信任信号
        await self.cognitive_service.create_cognitive_fragment(
            user_id=str(intent.user_id),
            content=f"用户在{review_seconds:.0f}秒内确认了AI执行结果(任务类型: {intent.target_env}), 表现出高度信任",
            fragment_type="behavior_auto",
            source="execution_approval_speed",
            context={"task_type": intent.target_env, "review_seconds": review_seconds},
        )
    elif review_seconds > self.APPROVAL_SPEED_SLOW_THRESHOLD_SECONDS:
        # 长时间审查 — 谨慎信号
        await self.cognitive_service.create_cognitive_fragment(
            user_id=str(intent.user_id),
            content=f"用户花了{review_seconds:.0f}秒审查AI执行结果(任务类型: {intent.target_env}), 可能需要更详细的结果展示",
            fragment_type="behavior_auto",
            source="execution_approval_speed",
            context={"task_type": intent.target_env, "review_seconds": review_seconds},
        )
        # 写入偏好: 该任务类型需要更详细的结果
        await self.profile_write_service.update_inferred_preference(
            user_id=str(intent.user_id),
            key=f"execution.{intent.target_env}.detail_level",
            value="verbose",
            confidence=min(0.6, review_seconds / 300),  # 审查越久, 置信度越高, 上限0.6
            source="approval_speed_learning",
        )
```

#### 3. 新增方法: 任务类型委派倾向

```python
async def handle_task_type_delegation_tendency(
    self,
    *,
    user_id: str,
    task_type: str,  # target_env: BROWSER/SHELL/API/DOCUMENT
    outcome: str,  # "confirmed" | "rejected" | "handed_back"
) -> None:
    """Track delegation success per task type.

    Builds per-type trust profile:
    - User trusts AI for BROWSER tasks but not SHELL
    - User always rejects DOCUMENT results
    """
    from sqlalchemy import select, func, and_
    from app.models.execution_intent import ExecutionIntent
    from app.models.execution_record import ExecutionRecord

    # 查询该用户该类型最近N次执行的结果分布
    stmt = (
        select(
            ExecutionRecord.trust_level,
            func.count().label("cnt"),
        )
        .join(ExecutionIntent, ExecutionRecord.execution_intent_id == ExecutionIntent.id)
        .where(
            and_(
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.target_env == task_type,
                ExecutionIntent.deleted_at.is_(None),
            )
        )
        .group_by(ExecutionRecord.trust_level)
        .limit(self.TASK_TYPE_DELEGATION_WINDOW)
    )

    result = await self.db.execute(stmt)
    rows = result.all()

    total = sum(r.cnt for r in rows)
    if total < 3:
        return  # 样本太少, 不做判断

    trusted_count = sum(r.cnt for r in rows if r.trust_level == "TRUSTED")
    trust_rate = trusted_count / total

    # 写入按类型的委派偏好
    await self.profile_write_service.update_inferred_preference(
        user_id=user_id,
        key=f"execution.{task_type}.delegate_preference",
        value=round(trust_rate, 2),
        confidence=min(0.8, total / 15),  # 越多数据越有信心
        source="task_type_delegation_tendency",
    )

    # 如果某类型信任率特别低, 创建认知片段
    if trust_rate < 0.3 and total >= 5:
        await self.cognitive_service.create_cognitive_fragment(
            user_id=user_id,
            content=f"用户对{task_type}类型任务的AI执行信任度较低({trust_rate:.0%}), 建议该类型任务优先推荐手动完成",
            fragment_type="behavior_auto",
            source="task_type_delegation_tendency",
            context={"task_type": task_type, "trust_rate": trust_rate, "sample_size": total},
        )
```

#### 4. 新增方法: 质量敏感度检测

```python
async def handle_quality_satisfaction_signal(
    self,
    *,
    user_id: str,
    quality_score: float | None,
    decision: str,  # "confirmed" | "rejected"
) -> None:
    """Learn user's quality tolerance threshold.

    Some users accept 70-score results. Others need 95+.
    """
    if quality_score is None:
        return

    from sqlalchemy import select, and_
    from app.models.execution_record import ExecutionRecord

    # 查询最近N次有quality_score的决策
    # 简化实现: 直接根据本次决策更新阈值
    if decision == "confirmed":
        # 用户接受了这个分数 — 该分数在用户容忍范围内
        await self.profile_write_service.update_inferred_preference(
            user_id=user_id,
            key="execution.quality_acceptance_floor",
            value=quality_score,
            confidence=0.4,  # 单次信号置信度低
            source="quality_satisfaction",
        )
    elif decision == "rejected" and quality_score > 0:
        # 用户拒绝了这个分数 — 该分数不够
        await self.profile_write_service.update_inferred_preference(
            user_id=user_id,
            key="execution.quality_rejection_ceiling",
            value=quality_score,
            confidence=0.4,
            source="quality_satisfaction",
        )
```

#### 5. 新增方法: 拒绝理由分析

```python
async def handle_rejection_reason_analysis(
    self,
    *,
    user_id: str,
    intent: "ExecutionIntent",
    reason: str | None,
) -> None:
    """Analyze rejection reason to understand severity and type.

    Feeds into delegation_aversion with weighted severity.
    """
    if not reason:
        return

    # 简单关键词分类 (后续可接入LLM分析)
    severity = "mild"  # default
    category = "preference"

    negative_indicators = ["不准确", "错误", "有问题", "不对", "wrong", "incorrect", "inaccurate"]
    safety_indicators = ["安全", "危险", "隐私", "泄露", "security", "privacy", "dangerous"]
    incomplete_indicators = ["不完整", "缺少", "没有包含", "incomplete", "missing"]

    reason_lower = reason.lower()

    if any(ind in reason_lower for ind in safety_indicators):
        severity = "critical"
        category = "safety"
    elif any(ind in reason_lower for ind in negative_indicators):
        severity = "moderate"
        category = "accuracy"
    elif any(ind in reason_lower for ind in incomplete_indicators):
        severity = "mild"
        category = "completeness"

    # 创建带分类的认知片段
    await self.cognitive_service.create_cognitive_fragment(
        user_id=user_id,
        content=f"用户拒绝了AI执行结果, 原因: {reason} [严重程度: {severity}, 类别: {category}]",
        fragment_type="delegation_takeback",
        source="rejection_reason_analysis",
        context={
            "task_type": intent.target_env,
            "severity": severity,
            "category": category,
            "reason": reason,
        },
    )

    # 安全类拒绝需要强化aversion
    if severity == "critical":
        await self.profile_write_service.update_inferred_preference(
            user_id=user_id,
            key="execution.safety_concern_count",
            value=1,  # 累加型, ProfileWriteService应处理
            confidence=0.9,
            source="rejection_safety_concern",
        )
```

---

## 任务 3.2: 在ExecutionIngestor中调用新信号

**修改文件**: `backend/app/services/execution_ingestor.py`

### 修改目标

在confirm/reject/ingest三条路径中调用Phase 3新增的学习信号方法。

### 精确修改

#### 1. 在 `confirm_result()` 方法中

找到confirm_result方法(搜索 `async def confirm_result` 或 `def confirm_result`), 在执行成功确认后(trust_level被设置之后, return之前), 添加:

```python
# Phase 3: 扩展学习信号
try:
    # 审批速度信号
    await self._learning_service.handle_approval_speed_signal(
        intent=intent,
        record=record,
        waiting_started_at=intent.updated_at if intent.status == "WAITING_APPROVAL" else None,
        decided_at=datetime.utcnow(),
        decision="confirmed",
    )
    # 任务类型委派倾向
    await self._learning_service.handle_task_type_delegation_tendency(
        user_id=str(intent.user_id),
        task_type=intent.target_env or "unknown",
        outcome="confirmed",
    )
    # 质量敏感度
    await self._learning_service.handle_quality_satisfaction_signal(
        user_id=str(intent.user_id),
        quality_score=record.quality_score,
        decision="confirmed",
    )
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Phase 3 learning signal failed on confirm: {e}")
```

#### 2. 在 `reject_result()` 方法中

找到reject_result方法, 在拒绝处理完成后(状态更新之后, return之前), 添加:

```python
# Phase 3: 扩展学习信号
try:
    # 审批速度信号
    await self._learning_service.handle_approval_speed_signal(
        intent=intent,
        record=record,
        waiting_started_at=intent.updated_at if hasattr(intent, 'updated_at') else None,
        decided_at=datetime.utcnow(),
        decision="rejected",
    )
    # 任务类型委派倾向
    await self._learning_service.handle_task_type_delegation_tendency(
        user_id=str(intent.user_id),
        task_type=intent.target_env or "unknown",
        outcome="rejected",
    )
    # 质量敏感度
    await self._learning_service.handle_quality_satisfaction_signal(
        user_id=str(intent.user_id),
        quality_score=record.quality_score if record else None,
        decision="rejected",
    )
    # 拒绝理由分析 (reason参数需要从调用链传入)
    # 注意: 当前reject_result的签名可能不包含reason参数
    # 如果是这样, 需要在方法签名中增加 reason: str | None = None
    # 并从API层传入
    if hasattr(record, '_rejection_reason'):
        await self._learning_service.handle_rejection_reason_analysis(
            user_id=str(intent.user_id),
            intent=intent,
            reason=record._rejection_reason,
        )
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Phase 3 learning signal failed on reject: {e}")
```

**关键注意**: 你需要确保rejection reason能从API层传递到Ingestor。检查:
1. `executions.py` 的 `reject_execution_result` endpoint 是否接收reason
2. `ExecutionService.reject_result()` 是否传递reason
3. `ExecutionIngestor.reject_result()` 是否接收reason

如果链路中reason丢失了, 需要补齐传递。具体做法: 在Ingestor的reject_result方法签名中增加 `reason: str | None = None`, 然后沿调用链反向补齐。

---

## 任务 3.3: ProfileContextService增加执行画像策略

**修改文件**: `backend/app/services/profile_context_service.py`

### 修改目标

将Phase 3的新信号(任务类型偏好、质量敏感度)纳入PATTERN_POLICY_MAP, 使画像能驱动执行行为。

### 精确修改

找到 `PATTERN_POLICY_MAP` dict(Phase 0已经添加了delegation_aversion/delegation_trust_building/execution_time_learning三条), 在其中追加:

```python
# Phase 3: 扩展执行画像策略
"execution_type_preference": [
    "execution.delegate.per_type_routing",      # 按类型调整路由偏好
    "task.execution.type_aware_suggestion",      # 建议时考虑类型偏好
],
"execution_quality_sensitivity": [
    "execution.result.detail_level_adjust",      # 结果展示详细度自适应
    "execution.trust.quality_threshold_adjust",  # 信任晋升阈值自适应
],
"execution_safety_concern": [
    "execution.delegate.require_manual_review",  # 强制人工审核
    "execution.route.prefer_hybrid",             # 路由偏向HYBRID模式
],
```

---

## 任务 3.4: AdaptiveReplanner增加执行模式自适应

**修改文件**: `backend/app/orchestration/adaptive_replanner.py`

### 修改目标

让Replanner根据新画像信号自动调整计划中任务的默认执行模式。

### 精确修改

找到 `_map_pattern()` 方法(Phase 0已添加了Delegation Aversion/Trust/Time Learning三条映射), 在其中追加:

```python
# Phase 3: 扩展模式映射
if "execution_type_preference" in pattern_name.lower() or "type_preference" in pattern_name.lower():
    # 从pattern的context中提取各类型偏好
    context = pattern.get("context", {})
    adjustments = {}
    for env_type in ["BROWSER", "SHELL", "API", "DOCUMENT"]:
        pref_key = f"execution.{env_type}.delegate_preference"
        pref_value = context.get(pref_key)
        if pref_value is not None:
            if float(pref_value) < 0.3:
                adjustments[env_type] = "human_preferred"
            elif float(pref_value) > 0.7:
                adjustments[env_type] = "agent_preferred"
    if adjustments:
        return {"type_delegation_routing": adjustments}

if "safety_concern" in pattern_name.lower():
    return {
        "require_manual_review": True,
        "prefer_hybrid_mode": True,
        "auto_delegate": False,
    }

if "quality_sensitivity" in pattern_name.lower():
    context = pattern.get("context", {})
    floor = context.get("quality_acceptance_floor")
    if floor is not None:
        return {"quality_threshold_override": float(floor)}
```

**注意**: 上述代码需要适配 `_map_pattern()` 的实际签名和返回值格式。阅读现有的三条映射了解返回值结构, 保持一致。

---

## 任务 3.5: 创建执行画像聚合查询

**创建文件**: `backend/app/services/execution_profile_service.py`

### 设计规格

提供一个服务层方法, 聚合用户的执行画像数据, 供Orchestrator和前端使用。

```python
"""Aggregate execution profile for a user — read-only query service."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution_intent import ExecutionIntent
from app.models.execution_record import ExecutionRecord


class ExecutionProfileService:
    """Read-only service that aggregates execution behavior into a profile snapshot."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_execution_profile(self, user_id: UUID, days: int = 30) -> dict[str, Any]:
        """Build execution profile for user over the last N days.

        Returns:
            {
                "total_executions": int,
                "success_rate": float,
                "by_type": {
                    "BROWSER": {"count": int, "success_rate": float, "avg_duration_ms": float},
                    ...
                },
                "trust_distribution": {"RAW": int, "VALIDATED": int, "TRUSTED": int},
                "delegation_trend": "increasing" | "stable" | "decreasing",
                "avg_review_time_seconds": float | None,
                "most_used_template": str | None,
                "estimated_time_saved_minutes": float,
            }
        """
        since = datetime.utcnow() - timedelta(days=days)

        # 基础统计
        base_filter = and_(
            ExecutionIntent.user_id == str(user_id),
            ExecutionIntent.created_at >= since,
            ExecutionIntent.deleted_at.is_(None),
        )

        # 总数和成功率
        total_stmt = select(
            func.count().label("total"),
            func.sum(case((ExecutionIntent.status == "SUCCEEDED", 1), else_=0)).label("succeeded"),
        ).where(base_filter)
        total_result = await self._db.execute(total_stmt)
        total_row = total_result.one()

        total_executions = total_row.total or 0
        success_rate = (total_row.succeeded or 0) / total_executions if total_executions > 0 else 0.0

        # 按类型统计
        type_stmt = select(
            ExecutionIntent.target_env,
            func.count().label("count"),
            func.sum(case((ExecutionIntent.status == "SUCCEEDED", 1), else_=0)).label("succeeded"),
        ).where(base_filter).group_by(ExecutionIntent.target_env)
        type_result = await self._db.execute(type_stmt)
        by_type = {}
        for row in type_result.all():
            env = row.target_env or "unknown"
            count = row.count or 0
            by_type[env] = {
                "count": count,
                "success_rate": (row.succeeded or 0) / count if count > 0 else 0.0,
            }

        # 信任分布
        trust_stmt = select(
            ExecutionIntent.trust_level,
            func.count().label("cnt"),
        ).where(base_filter).group_by(ExecutionIntent.trust_level)
        trust_result = await self._db.execute(trust_stmt)
        trust_distribution = {row.trust_level: row.cnt for row in trust_result.all()}

        # 耗时统计 (从record)
        duration_stmt = select(
            func.avg(ExecutionRecord.duration_ms).label("avg_duration"),
        ).join(
            ExecutionIntent, ExecutionRecord.execution_intent_id == ExecutionIntent.id
        ).where(base_filter)
        duration_result = await self._db.execute(duration_stmt)
        avg_duration = duration_result.scalar()

        # 最常用模板
        template_stmt = select(
            ExecutionIntent.policy["template_id"].astext.label("template_id"),
            func.count().label("cnt"),
        ).where(
            and_(base_filter, ExecutionIntent.policy["template_id"].isnot(None))
        ).group_by("template_id").order_by(func.count().desc()).limit(1)

        try:
            template_result = await self._db.execute(template_stmt)
            template_row = template_result.first()
            most_used_template = template_row.template_id if template_row else None
        except Exception:
            most_used_template = None

        # 估算节省时间 (假设人工完成平均需要执行时间的3倍)
        estimated_time_saved = 0.0
        if avg_duration and total_row.succeeded:
            avg_duration_minutes = (avg_duration / 1000) / 60
            estimated_time_saved = avg_duration_minutes * 2 * (total_row.succeeded or 0)

        return {
            "total_executions": total_executions,
            "success_rate": round(success_rate, 3),
            "by_type": by_type,
            "trust_distribution": trust_distribution,
            "delegation_trend": self._compute_trend(user_id, since),
            "avg_duration_ms": avg_duration,
            "most_used_template": most_used_template,
            "estimated_time_saved_minutes": round(estimated_time_saved, 1),
        }

    def _compute_trend(self, user_id: UUID, since: datetime) -> str:
        """Simplified trend: compare first half vs second half of the period."""
        # 简化实现, 返回stable
        # 完整实现需要额外查询, 可在后续迭代中补充
        return "stable"
```

---

## 任务 3.6: 暴露执行画像API

**修改文件**: `backend/app/api/v1/executions.py`

### 精确修改

在现有endpoint列表末尾, 添加:

```python
@router.get("/profile/summary")
async def get_execution_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    days: int = 30,
):
    """Get user's execution behavior profile summary."""
    from app.services.execution_profile_service import ExecutionProfileService

    service = ExecutionProfileService(db)
    profile = await service.get_execution_profile(
        user_id=current_user.id,
        days=min(days, 90),  # 最多90天
    )
    return profile
```

---

## 验收标准

### 后端验收

```bash
cd backend && python -m pytest tests/ -x -q
```

所有现有测试仍通过。

### 新增测试

**创建文件**: `backend/tests/unit/test_openclaw_phase3_extended.py`

```python
"""Phase 3 extended learning signal tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


class TestApprovalSpeedSignal:
    """Test that approval speed is correctly classified."""

    @pytest.mark.asyncio
    async def test_fast_confirmation_creates_trust_fragment(self):
        """Confirming in <15s should create a high-trust cognitive fragment."""
        # Setup mock learning service
        # Call handle_approval_speed_signal with 5-second review time
        # Assert cognitive_service.create_cognitive_fragment was called
        # Assert fragment content mentions "高度信任"
        pass  # Agent: implement this test

    @pytest.mark.asyncio
    async def test_slow_review_updates_detail_preference(self):
        """Reviewing for >120s should update detail_level preference to verbose."""
        # Setup mock learning service
        # Call handle_approval_speed_signal with 180-second review time
        # Assert profile_write_service.update_inferred_preference called
        # Assert key contains "detail_level" and value is "verbose"
        pass  # Agent: implement this test


class TestTaskTypeDelegationTendency:
    """Test per-type delegation tracking."""

    @pytest.mark.asyncio
    async def test_low_trust_rate_creates_warning_fragment(self):
        """When trust rate < 30% over 5+ executions, should create warning fragment."""
        # Mock DB query to return low trust rate
        # Assert cognitive fragment created with appropriate content
        pass  # Agent: implement this test


class TestQualitySatisfaction:
    """Test quality threshold learning."""

    @pytest.mark.asyncio
    async def test_confirmed_score_updates_acceptance_floor(self):
        """Confirming a result should update quality_acceptance_floor preference."""
        pass  # Agent: implement this test

    @pytest.mark.asyncio
    async def test_rejected_score_updates_rejection_ceiling(self):
        """Rejecting should update quality_rejection_ceiling preference."""
        pass  # Agent: implement this test


class TestRejectionReasonAnalysis:
    """Test rejection reason classification."""

    @pytest.mark.asyncio
    async def test_safety_reason_marked_critical(self):
        """Reasons mentioning safety/privacy should be classified as critical."""
        pass  # Agent: implement this test

    @pytest.mark.asyncio
    async def test_accuracy_reason_marked_moderate(self):
        """Reasons about accuracy should be classified as moderate."""
        pass  # Agent: implement this test


class TestExecutionProfileService:
    """Test profile aggregation."""

    @pytest.mark.asyncio
    async def test_profile_returns_expected_shape(self):
        """Profile response should have all expected keys."""
        pass  # Agent: implement this test
```

Agent需要实现这些测试的具体逻辑, 使用与现有test_openclaw_phase3.py相同的mock模式。

### 功能验收 (人工)

1. [ ] 快速确认(<15s)后, 对应task_type的认知片段被创建
2. [ ] 长时间审查(>120s)后, detail_level偏好被更新
3. [ ] 多次拒绝同一类型任务后, 该类型的delegate_preference降低
4. [ ] 拒绝理由中包含安全关键词时, safety_concern被标记
5. [ ] GET /executions/profile/summary 返回正确的聚合数据
6. [ ] AdaptiveReplanner正确响应新的pattern映射
