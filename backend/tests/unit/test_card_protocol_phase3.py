from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.card_protocol import (
    ArtifactType,
    CardLifecycleStatus,
    CardType,
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionTriggerType,
)
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.services.card_protocol.global_compass_manager import GlobalCompassManager
from app.services.card_protocol.legacy_adapter import PlanAdapter
from app.services.card_protocol.outcome_verifier import InterventionOutcomeVerifier
from app.services.card_protocol.strategy_map_manager import StrategyMapManager
from app.services.card_service import CardService
from app.services.intervention_record_service import InterventionRecordService
from app.services.planning_artifact_service import PlanningArtifactService


@pytest.mark.asyncio
async def test_phase3_plan_projection_initializes_authoritative_artifacts(db_session, test_user):
    plan = Plan(
        user_id=test_user.id,
        name="Phase 3 Long Horizon Plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    plan_card = await PlanAdapter(db_session).plan_to_card(plan)
    await db_session.commit()

    artifact_service = PlanningArtifactService(db_session)
    compass = await artifact_service.get_approved(plan_card.id, ArtifactType.GLOBAL_COMPASS)
    strategy = await artifact_service.get_approved(plan_card.id, ArtifactType.STRATEGY_MAP)

    assert compass is not None
    assert strategy is not None
    assert plan_card.metadata_["global_compass_artifact_id"] == str(compass.id)
    assert plan_card.metadata_["global_compass_version"] == compass.version
    assert plan_card.metadata_["strategy_map_artifact_id"] == str(strategy.id)
    assert plan_card.metadata_["strategy_map_version"] == strategy.version


@pytest.mark.asyncio
async def test_planning_artifact_versions_remain_monotonic_across_unapproved_history(db_session, test_user):
    plan_card = await CardService(db_session).create_card(
        card_type=CardType.PLAN,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"name": "Artifact Version Plan"},
        lifecycle_status=CardLifecycleStatus.ACTIVE,
    )

    service = PlanningArtifactService(db_session)
    first = await service.create_artifact(
        plan_card_id=plan_card.id,
        artifact_type=ArtifactType.STRATEGY_MAP,
        payload={"version_marker": 1},
        created_by_agent="test",
    )
    await service.propose_artifact(first.id)

    second = await service.create_artifact(
        plan_card_id=plan_card.id,
        artifact_type=ArtifactType.STRATEGY_MAP,
        payload={"version_marker": 2},
        created_by_agent="test",
    )

    assert first.version == 1
    assert second.version == 2


@pytest.mark.asyncio
async def test_phase3_default_templates_do_not_leak_state_between_plans(db_session):
    compass_manager = GlobalCompassManager(db_session)
    first_compass = compass_manager._build_initial_payload(
        user_profile={
            "preferences": {
                "preferred_time_slots": ["morning"],
                "max_concurrent_tasks": 2,
            },
            "inferred": {"task_reflection_depth": "deep"},
        },
        plan_context={"goal": "Finish the sprint"},
    )
    second_compass = compass_manager._build_initial_payload(
        user_profile=None,
        plan_context=None,
    )

    assert first_compass["hard_constraints"]["preferred_time_slots"] == ["morning"]
    assert second_compass["hard_constraints"]["preferred_time_slots"] == []
    assert second_compass["hard_constraints"]["max_concurrent_tasks"] == 3
    assert second_compass["learning_style_hints"]["reflection_depth"] == "light"

    strategy_manager = StrategyMapManager(db_session)
    first_strategy = strategy_manager._build_initial_payload(
        {"phase_count": 2, "task_density": 8}
    )
    second_strategy = strategy_manager._build_initial_payload(None)

    assert first_strategy["execution_parameters"]["checkpoint_frequency_days"] == 5
    assert second_strategy["execution_parameters"]["checkpoint_frequency_days"] == 7
    assert second_strategy["execution_parameters"]["max_concurrent_phases"] == 1


@pytest.mark.asyncio
async def test_outcome_verifier_measures_system_applied_interventions(db_session, test_user):
    plan_card = await CardService(db_session).create_card(
        card_type=CardType.PLAN,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"name": "System Applied Plan", "legacy_plan_id": str(uuid4())},
        lifecycle_status=CardLifecycleStatus.ACTIVE,
    )

    record_service = InterventionRecordService(db_session)
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        plan_card_id=plan_card.id,
        outcome_window_days=1,
    )
    record.created_at = datetime.utcnow() - timedelta(days=2)
    record.action_payload = {
        "parameter_compilation": {
            "applied": True,
            "result": "patched",
        }
    }
    await record_service.mark_delivered(record.id)

    plan_card.metadata_ = {
        **(plan_card.metadata_ or {}),
        "latest_adjustment_evidence": {
            "timestamp": (datetime.utcnow() - timedelta(hours=12)).isoformat(),
            "trigger": "intervention",
        },
    }
    await db_session.commit()

    verifier = InterventionOutcomeVerifier(db_session)
    summary = await verifier.verify_all_pending()
    await db_session.refresh(record)

    assert summary["resolved"] == 1
    assert summary["effective"] == 1
    assert record.outcome_status == InterventionOutcomeStatus.EFFECTIVE
    assert record.evidence_payload["evaluation_method"] == "system_applied_and_measured"
