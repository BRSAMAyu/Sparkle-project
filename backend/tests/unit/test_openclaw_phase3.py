from __future__ import annotations

from datetime import timedelta
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
from app.services.execution_profile_service import ExecutionProfileService
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
async def test_execution_learning_recomputes_delegate_preference_from_recent_outcomes(
    db_session,
    mute_learning_side_effects,
) -> None:
    user = User(username="phase3delegate", email="phase3delegate@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = ExecutionLearningService(db_session)
    latest_success_intent = None
    latest_success_record = None

    for index in range(5):
        task = Task(
            user_id=user.id,
            title=f"可信任务 {index}",
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
            idempotency_key=f"recompute-success:{task.id}",
        )
        db_session.add(intent)
        await db_session.commit()
        await db_session.refresh(intent)

        record = ExecutionRecord(
            execution_intent_id=intent.id,
            user_id=user.id,
            task_id=task.id,
            executor_type="openclaw",
            raw_response={"id": f"recompute-{index}"},
            parsed_output={"summary": "done"},
            artifacts=[],
            trust_level=TrustLevel.TRUSTED.value,
            duration_ms=20 * 60 * 1000,
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)
        latest_success_intent = intent
        latest_success_record = record

    assert latest_success_intent is not None
    assert latest_success_record is not None

    await service.handle_trusted_execution(
        intent=latest_success_intent,
        record=latest_success_record,
        parsed={"success": True},
    )

    prefs = await PreferenceService(db_session).get_preferences(user.id)
    initial_preference = prefs.inferred.get("ai_delegate_preference")
    assert initial_preference == 0.9

    for index in range(5):
        task = Task(
            user_id=user.id,
            title=f"失败任务 {index}",
            type=TaskType.OCR,
            tags=["research"],
            estimated_minutes=20,
            difficulty=1,
            energy_cost=1,
            status=TaskStatus.PENDING,
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
            status=ExecutionIntentStatus.FAILED,
            trust_level=TrustLevel.RAW,
            idempotency_key=f"recompute-failed:{task.id}",
        )
        db_session.add(intent)
        await db_session.commit()

    recovery_task = Task(
        user_id=user.id,
        title="恢复任务",
        type=TaskType.OCR,
        tags=["research"],
        estimated_minutes=20,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.COMPLETED,
    )
    db_session.add(recovery_task)
    await db_session.commit()
    await db_session.refresh(recovery_task)

    recovery_intent = ExecutionIntent(
        user_id=user.id,
        task_id=recovery_task.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal=recovery_task.title,
        instructions=[],
        target_env=ExecutionTargetEnv.BROWSER,
        policy={},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.SUCCEEDED,
        trust_level=TrustLevel.TRUSTED,
        idempotency_key=f"recompute-recovery:{recovery_task.id}",
    )
    db_session.add(recovery_intent)
    await db_session.commit()
    await db_session.refresh(recovery_intent)

    recovery_record = ExecutionRecord(
        execution_intent_id=recovery_intent.id,
        user_id=user.id,
        task_id=recovery_task.id,
        executor_type="openclaw",
        raw_response={"id": "recompute-recovery"},
        parsed_output={"summary": "done"},
        artifacts=[],
        trust_level=TrustLevel.TRUSTED.value,
        duration_ms=20 * 60 * 1000,
    )
    db_session.add(recovery_record)
    await db_session.commit()
    await db_session.refresh(recovery_record)

    await service.handle_trusted_execution(
        intent=recovery_intent,
        record=recovery_record,
        parsed={"success": True},
    )

    refreshed = await PreferenceService(db_session).get_preferences(user.id)
    assert refreshed.inferred["ai_delegate_preference"] < initial_preference
    assert refreshed.inferred["ai_delegate_preference"] == 0.5


@pytest.mark.asyncio
async def test_execution_learning_safety_concern_count_decreases_after_trusted_success(
    db_session,
    mute_learning_side_effects,
) -> None:
    user = User(username="phase3safety", email="phase3safety@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = ExecutionLearningService(db_session)

    rejection_task = Task(
        user_id=user.id,
        title="敏感操作",
        type=TaskType.OCR,
        tags=["research"],
        estimated_minutes=10,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(rejection_task)
    await db_session.commit()
    await db_session.refresh(rejection_task)

    rejection_intent = ExecutionIntent(
        user_id=user.id,
        task_id=rejection_task.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal=rejection_task.title,
        instructions=[],
        target_env=ExecutionTargetEnv.BROWSER,
        policy={},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.HANDED_BACK,
        trust_level=TrustLevel.RAW,
        idempotency_key=f"safety-reject:{rejection_task.id}",
    )
    db_session.add(rejection_intent)
    await db_session.commit()
    await db_session.refresh(rejection_intent)

    await service.handle_rejection_sentiment(
        intent=rejection_intent,
        record=None,
        reason="这个操作有安全风险",
    )
    await service.handle_rejection_sentiment(
        intent=rejection_intent,
        record=None,
        reason="unsafe for this account",
    )

    prefs = await PreferenceService(db_session).get_preferences(user.id)
    assert prefs.inferred["execution.safety_concern_count"] == 2

    success_task = Task(
        user_id=user.id,
        title="低风险操作",
        type=TaskType.OCR,
        tags=["research"],
        estimated_minutes=10,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.COMPLETED,
    )
    db_session.add(success_task)
    await db_session.commit()
    await db_session.refresh(success_task)

    success_intent = ExecutionIntent(
        user_id=user.id,
        task_id=success_task.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal=success_task.title,
        instructions=[],
        target_env=ExecutionTargetEnv.BROWSER,
        policy={},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.SUCCEEDED,
        trust_level=TrustLevel.TRUSTED,
        idempotency_key=f"safety-success:{success_task.id}",
    )
    db_session.add(success_intent)
    await db_session.commit()
    await db_session.refresh(success_intent)

    success_record = ExecutionRecord(
        execution_intent_id=success_intent.id,
        user_id=user.id,
        task_id=success_task.id,
        executor_type="openclaw",
        raw_response={"id": "safety-success"},
        parsed_output={"summary": "done"},
        artifacts=[],
        trust_level=TrustLevel.TRUSTED.value,
        duration_ms=10 * 60 * 1000,
    )
    db_session.add(success_record)
    await db_session.commit()
    await db_session.refresh(success_record)

    await service.handle_trusted_execution(
        intent=success_intent,
        record=success_record,
        parsed={"success": True},
    )

    refreshed = await PreferenceService(db_session).get_preferences(user.id)
    assert refreshed.inferred["execution.safety_concern_count"] == 1


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


@pytest.mark.asyncio
async def test_execution_learning_approval_speed_updates_detail_preference(
    db_session,
    mute_learning_side_effects,
) -> None:
    user = User(
        username="phase3speed",
        email="phase3speed@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="快速确认研究结果",
        type=TaskType.OCR,
        tags=["research"],
        estimated_minutes=15,
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
        dispatched_at=task.created_at,
        completed_at=task.created_at + timedelta(seconds=10),
        idempotency_key=f"speed:{task.id}",
    )
    db_session.add(intent)
    await db_session.commit()
    await db_session.refresh(intent)

    record = ExecutionRecord(
        execution_intent_id=intent.id,
        user_id=user.id,
        task_id=task.id,
        executor_type="openclaw",
        raw_response={"id": "speed-run"},
        parsed_output={"summary": "done"},
        artifacts=[],
        trust_level=TrustLevel.TRUSTED.value,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    service = ExecutionLearningService(db_session)
    await service.handle_approval_speed_signal(
        intent=intent,
        record=record,
        approved=True,
    )

    prefs = await PreferenceService(db_session).get_preferences(user.id)
    inferred = prefs.inferred or {}
    assert inferred.get("execution.browser.detail_level") == "concise"


@pytest.mark.asyncio
async def test_execution_learning_quality_signal_persists_acceptance_floor(
    db_session,
    mute_learning_side_effects,
) -> None:
    user = User(
        username="phase3quality",
        email="phase3quality@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="质量阈值学习",
        type=TaskType.OCR,
        tags=["research"],
        estimated_minutes=15,
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
        target_env=ExecutionTargetEnv.DOCUMENT,
        policy={},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.SUCCEEDED,
        trust_level=TrustLevel.TRUSTED,
        idempotency_key=f"quality:{task.id}",
    )
    db_session.add(intent)
    await db_session.commit()
    await db_session.refresh(intent)

    record = ExecutionRecord(
        execution_intent_id=intent.id,
        user_id=user.id,
        task_id=task.id,
        executor_type="openclaw",
        raw_response={"id": "quality-run"},
        parsed_output={"summary": "done"},
        artifacts=[],
        trust_level=TrustLevel.TRUSTED.value,
        quality_score=0.91,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    service = ExecutionLearningService(db_session)
    await service.handle_quality_sensitivity(
        intent=intent,
        record=record,
        approved=True,
    )

    prefs = await PreferenceService(db_session).get_preferences(user.id)
    inferred = prefs.inferred or {}
    assert inferred.get("execution.quality_acceptance_floor") == 0.91


@pytest.mark.asyncio
async def test_execution_profile_service_aggregates_recent_summary(db_session) -> None:
    user = User(
        username="phase3profile",
        email="phase3profile@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    browser_task = Task(
        user_id=user.id,
        title="网页调研",
        type=TaskType.OCR,
        tags=["research"],
        estimated_minutes=20,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.COMPLETED,
    )
    document_task = Task(
        user_id=user.id,
        title="文档整理",
        type=TaskType.OCR,
        tags=["document"],
        estimated_minutes=20,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add_all([browser_task, document_task])
    await db_session.commit()
    await db_session.refresh(browser_task)
    await db_session.refresh(document_task)

    intent_1 = ExecutionIntent(
        user_id=user.id,
        task_id=browser_task.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal=browser_task.title,
        instructions=[],
        target_env=ExecutionTargetEnv.BROWSER,
        policy={"template_metadata": {"template_id": "web_research_brief"}},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.SUCCEEDED,
        trust_level=TrustLevel.TRUSTED,
        idempotency_key=f"profile:{browser_task.id}",
    )
    intent_2 = ExecutionIntent(
        user_id=user.id,
        task_id=document_task.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal=document_task.title,
        instructions=[],
        target_env=ExecutionTargetEnv.DOCUMENT,
        policy={"template_metadata": {"template_id": "document_digest"}},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.FAILED,
        trust_level=TrustLevel.RAW,
        idempotency_key=f"profile:{document_task.id}",
    )
    db_session.add_all([intent_1, intent_2])
    await db_session.commit()
    await db_session.refresh(intent_1)
    await db_session.refresh(intent_2)

    db_session.add_all(
        [
            ExecutionRecord(
                execution_intent_id=intent_1.id,
                user_id=user.id,
                task_id=browser_task.id,
                executor_type="openclaw",
                raw_response={"id": "profile-run-1"},
                parsed_output={"summary": "done"},
                artifacts=[],
                trust_level=TrustLevel.TRUSTED.value,
                approval_requested=1,
            ),
            ExecutionRecord(
                execution_intent_id=intent_2.id,
                user_id=user.id,
                task_id=document_task.id,
                executor_type="openclaw",
                raw_response={"id": "profile-run-2"},
                parsed_output={"summary": "failed"},
                artifacts=[],
                trust_level=TrustLevel.RAW.value,
                approval_requested=0,
            ),
        ]
    )
    await db_session.commit()

    payload = await ExecutionProfileService(db_session).get_execution_profile(user.id, days=30)

    assert payload["total_executions"] == 2
    assert payload["success_rate"] == 0.5
    assert payload["by_type"]["browser"]["success_rate"] == 1.0
    assert payload["trust_distribution"]["trusted"] == 1
    assert payload["approval_request_count"] == 1
    assert payload["estimated_time_saved_minutes"] > 0
    assert {item[0] for item in payload["top_templates"]} == {
        "web_research_brief",
        "document_digest",
    }
