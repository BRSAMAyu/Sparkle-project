from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.cognitive import BehaviorPattern
from app.models.execution_intent import (
    ExecutionIntent,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionTargetEnv,
    ExecutorType,
    TrustLevel,
)
from app.models.execution_record import ExecutionRecord
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.orchestration.adaptive_replanner import CognitivePatternTrigger
from app.services.execution_learning_service import ExecutionLearningService
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_context_service import ProfileContextService


@pytest.fixture
def mute_learning_side_effects(monkeypatch):
    async def _publish(*args, **kwargs):
        return None

    async def _create_fragment(self, *args, **kwargs):
        class _Fragment:
            id = uuid4()

        return _Fragment()

    monkeypatch.setattr("app.services.execution_learning_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.profile_write_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.cognitive_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.cognitive_service.CognitiveService.create_fragment", _create_fragment)


@pytest.mark.asyncio
async def test_execution_learning_creates_patterns_and_inferred_preferences(
    db_session,
    mute_learning_side_effects,
) -> None:
    user = User(username="phase3trust", email="phase3trust@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    latest_intent = None
    latest_record = None
    for index in range(5):
        task = Task(
            user_id=user.id,
            title=f"整理资料 {index}",
            type=TaskType.OCR,
            tags=["research"],
            estimated_minutes=20,
            difficulty=1,
            energy_cost=1,
            status=TaskStatus.COMPLETED,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        intent = ExecutionIntent(
            user_id=user.id,
            task_id=task.id,
            execution_mode=ExecutionMode.AGENT,
            executor=ExecutorType.OPENCLAW,
            goal=task.title,
            instructions=[],
            target_env=ExecutionTargetEnv.BROWSER,
            policy={},
            success_criteria={"type": "non_empty"},
            result_contract={},
            timeout_seconds=300,
            status=ExecutionIntentStatus.SUCCEEDED,
            trust_level=TrustLevel.TRUSTED,
            idempotency_key=f"trusted:{task.id}",
        )
        db_session.add(intent)
        await db_session.commit()
        await db_session.refresh(intent)

        record = ExecutionRecord(
            execution_intent_id=intent.id,
            user_id=user.id,
            task_id=task.id,
            executor_type="openclaw",
            external_run_id=f"run-{index}",
            raw_response={"id": f"run-{index}"},
            parsed_output={"summary": "done"},
            artifacts=[],
            trust_level=TrustLevel.TRUSTED.value,
            duration_ms=30 * 60 * 1000,
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)
        latest_intent = intent
        latest_record = record

    assert latest_intent is not None
    assert latest_record is not None

    service = ExecutionLearningService(db_session)
    await service.handle_trusted_execution(
        intent=latest_intent,
        record=latest_record,
        parsed={"success": True, "parsed_output": {"summary": "done"}},
    )

    prefs = await PreferenceService(db_session).get_preferences(user.id)
    inferred = prefs.inferred or {}
    assert inferred.get("ai_delegate_preference") is not None
    assert inferred.get("ai_duration_multiplier") == 1.5

    trust_pattern = (
        await db_session.execute(
            select(BehaviorPattern).where(
                BehaviorPattern.user_id == user.id,
                BehaviorPattern.pattern_name == "Delegation Trust Building",
            )
        )
    ).scalar_one_or_none()
    duration_pattern = (
        await db_session.execute(
            select(BehaviorPattern).where(
                BehaviorPattern.user_id == user.id,
                BehaviorPattern.pattern_name == "Execution Time Learning",
            )
        )
    ).scalar_one_or_none()

    assert trust_pattern is not None
    assert duration_pattern is not None
    assert "multiplier=1.50" in str(duration_pattern.description or "")


@pytest.mark.asyncio
async def test_execution_learning_handed_back_creates_aversion_pattern(
    db_session,
    mute_learning_side_effects,
) -> None:
    user = User(username="phase3takeback", email="phase3takeback@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    latest_intent = None
    for index in range(10):
        task = Task(
            user_id=user.id,
            title=f"任务 {index}",
            type=TaskType.OCR,
            tags=[],
            estimated_minutes=10,
            difficulty=1,
            energy_cost=1,
            status=TaskStatus.PENDING,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        status = ExecutionIntentStatus.HANDED_BACK if index < 7 else ExecutionIntentStatus.SUCCEEDED
        trust_level = TrustLevel.RAW if status == ExecutionIntentStatus.HANDED_BACK else TrustLevel.TRUSTED
        intent = ExecutionIntent(
            user_id=user.id,
            task_id=task.id,
            execution_mode=ExecutionMode.AGENT,
            executor=ExecutorType.OPENCLAW,
            goal=task.title,
            instructions=[],
            target_env=ExecutionTargetEnv.BROWSER,
            policy={},
            success_criteria={"type": "non_empty"},
            result_contract={},
            timeout_seconds=300,
            status=status,
            trust_level=trust_level,
            error_category="user_rejected" if status == ExecutionIntentStatus.HANDED_BACK else None,
            idempotency_key=f"takeback:{task.id}",
        )
        db_session.add(intent)
        await db_session.commit()
        await db_session.refresh(intent)
        latest_intent = intent

    assert latest_intent is not None
    service = ExecutionLearningService(db_session)
    await service.handle_handed_back(intent=latest_intent, reason="用户不想委派")

    prefs = await PreferenceService(db_session).get_preferences(user.id)
    inferred = prefs.inferred or {}
    assert inferred.get("ai_delegate_preference") is not None
    assert inferred.get("ai_approval_preference") is not None

    aversion_pattern = (
        await db_session.execute(
            select(BehaviorPattern).where(
                BehaviorPattern.user_id == user.id,
                BehaviorPattern.pattern_name == "Delegation Aversion",
            )
        )
    ).scalar_one_or_none()
    assert aversion_pattern is not None
    assert float(aversion_pattern.confidence_score or 0.0) >= 0.7


@pytest.mark.asyncio
async def test_profile_context_merges_explicit_and_inferred_preferences(db_session) -> None:
    user = User(username="phase3context", email="phase3context@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    pref_service = PreferenceService(db_session)
    await pref_service.update_inferred(user.id, {"ai_delegate_preference": 0.82, "depth_preference": 0.2})

    context = await ProfileContextService(db_session).get_profile_context(user.id)
    assert context.preferences["ai_delegate_preference"] == 0.82
    assert context.preferences["depth_preference"] == 0.5


@pytest.mark.asyncio
async def test_cognitive_pattern_trigger_maps_execution_patterns(db_session) -> None:
    user = User(username="phase3trigger", email="phase3trigger@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    db_session.add_all(
        [
            BehaviorPattern(
                user_id=user.id,
                pattern_name="Delegation Aversion",
                pattern_type="execution",
                confidence_score=0.82,
                description="takeback_rate=0.70",
                frequency=3,
            ),
            BehaviorPattern(
                user_id=user.id,
                pattern_name="Execution Time Learning",
                pattern_type="execution",
                confidence_score=0.78,
                description="AI delegated tasks usually take multiplier=1.40 of the estimated task duration.",
                frequency=3,
            ),
        ]
    )
    await db_session.commit()

    trigger = CognitivePatternTrigger(db_session)
    adjustments = await trigger.build_adjustments(user_id=user.id, existing_constraints={})
    by_param = {item.parameter: item.value for item in adjustments}

    assert by_param["auto_delegate_suggestion"] is False
    assert by_param["require_human_confirmation"] is True
    assert by_param["ai_duration_multiplier"] == 1.4
