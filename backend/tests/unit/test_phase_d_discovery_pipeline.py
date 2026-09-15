from __future__ import annotations

import pytest
from uuid import UUID

from app.models.card_protocol import ArtifactStatus, ArtifactType, CardLifecycleStatus
from app.orchestration.discovery_manager import DiscoveryManager
from app.orchestration.phase_sketch_service import PhaseSketchService
from app.services.card_protocol.global_compass_manager import GlobalCompassManager
from app.services.card_protocol.phase_service import PhaseService
from app.services.planning_artifact_service import PlanningArtifactService


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "phase-d-test"


@pytest.mark.asyncio
async def test_discovery_requires_multi_turn_sufficiency(db_session, test_user):
    manager = DiscoveryManager(db_session, FakeEventBus())
    started = await manager.start_discovery(
        user_id=test_user.id,
        initial_message="我想在1年内学好机器学习。",
    )

    assert started["ready"] is False
    assert "current_situation" in started["missing_dimensions"]
    assert started["next_question"] is not None

    progressed = await manager.process_discovery_turn(
        user_id=test_user.id,
        session_id=started["session_id"],
        user_message="我现在有 Python 基础，但数学一般，工作很忙，每天1小时，之前学过几次都半途而废。",
    )

    assert progressed["ready"] is True
    assert progressed["sufficiency_score"] >= 0.7
    assert progressed["compass_preview"]["north_star"] == "我想在1年内学好机器学习。"


@pytest.mark.asyncio
async def test_finalize_discovery_creates_dossier_and_reviewable_compass(db_session, test_user):
    manager = DiscoveryManager(db_session, FakeEventBus())
    started = await manager.start_discovery(
        user_id=test_user.id,
        initial_message="我想在1年内系统学好机器学习，为了完成职业转型。",
    )
    await manager.process_discovery_turn(
        user_id=test_user.id,
        session_id=started["session_id"],
        user_message="我现在在职，基础还可以，但时间有限，每天1小时，之前试过自学但总是坚持不下来。",
    )

    finalized = await manager.finalize_discovery(
        user_id=test_user.id,
        session_id=started["session_id"],
        plan_overrides={"name": "ML Career Shift"},
    )

    assert finalized["workflow_state"] == "COMPASS_REVIEW"
    assert finalized["plan_id"] is not None
    assert finalized["dossier_artifact_id"] is not None
    assert finalized["compass_artifact_id"] is not None
    assert finalized["compass_preview"]["north_star"] == "我想在1年内系统学好机器学习，为了完成职业转型。"

    plan_card = await PhaseService(db_session, FakeEventBus()).get_plan_card_by_legacy_plan(
        finalized["plan_id"],
        test_user.id,
    )
    assert plan_card is not None
    assert (plan_card.metadata_ or {}).get("workflow_state") == "COMPASS_REVIEW"

    artifact_service = PlanningArtifactService(db_session, FakeEventBus())
    dossier = await artifact_service.get_artifact(UUID(finalized["dossier_artifact_id"]))
    compass = await artifact_service.get_artifact(UUID(finalized["compass_artifact_id"]))
    assert dossier is not None
    assert dossier.artifact_type == ArtifactType.DISCOVERY_DOSSIER
    assert dossier.status == ArtifactStatus.APPROVED
    assert compass is not None
    assert compass.artifact_type == ArtifactType.GLOBAL_COMPASS
    assert compass.status == ArtifactStatus.PROPOSED


@pytest.mark.asyncio
async def test_phase_d_full_flow_builds_reviewed_compass_and_materializes_phases(db_session, test_user):
    fake_bus = FakeEventBus()
    discovery = DiscoveryManager(db_session, fake_bus)
    started = await discovery.start_discovery(
        user_id=test_user.id,
        initial_message="我想在1年内把机器学习真正学扎实，并完成职业转型。",
    )
    await discovery.process_discovery_turn(
        user_id=test_user.id,
        session_id=started["session_id"],
        user_message="我目前有一些 Python 基础，但数学一般，工作很忙，每天1小时，过去试过几次但坚持不好。",
    )
    finalized = await discovery.finalize_discovery(
        user_id=test_user.id,
        session_id=started["session_id"],
        plan_overrides={"name": "Machine Learning Growth"},
    )

    artifact_service = PlanningArtifactService(db_session, fake_bus)
    compass_review = await GlobalCompassManager(db_session, fake_bus).present_compass_for_review(
        plan_card_id=UUID(finalized["plan_card_id"]),
        user_id=test_user.id,
    )
    approved_compass = await GlobalCompassManager(db_session, fake_bus).user_approve_compass(
        artifact_id=UUID(compass_review["artifact_id"]),
        user_id=test_user.id,
        edits={"values": ["career", "mastery"]},
    )

    assert approved_compass.status == ArtifactStatus.APPROVED
    assert approved_compass.payload["north_star"] == "我想在1年内把机器学习真正学扎实，并完成职业转型。"
    assert approved_compass.payload["values"] == ["career", "mastery"]

    dossier = await artifact_service.get_artifact(UUID(finalized["dossier_artifact_id"]))
    sketch = await PhaseSketchService(db_session, fake_bus).generate_sketch(
        plan_card_id=UUID(finalized["plan_card_id"]),
        compass=approved_compass,
        dossier=dossier,
        user_id=test_user.id,
    )
    assert sketch.status == ArtifactStatus.PROPOSED
    assert len((sketch.payload or {}).get("phases") or []) >= 3

    phases = await PhaseSketchService(db_session, fake_bus).materialize_sketch(
        plan_card_id=UUID(finalized["plan_card_id"]),
        sketch=sketch,
        user_id=test_user.id,
    )
    assert len(phases) == len((sketch.payload or {}).get("phases") or [])
    assert phases[0].lifecycle_status == CardLifecycleStatus.ACTIVE

    plan_card = await PhaseService(db_session, fake_bus).get_plan_card_by_legacy_plan(
        finalized["plan_id"],
        test_user.id,
    )
    assert plan_card is not None
    assert (plan_card.metadata_ or {}).get("workflow_state") == "PHASE_DESIGN"
