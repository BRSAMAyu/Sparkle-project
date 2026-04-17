from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionRecord,
    InterventionTriggerType,
)
from app.models.plan import Plan, PlanStage, PlanType
from app.orchestration.dynamic_tool_registry import DynamicToolRegistry
from app.tools.base import TOOL_RUNTIME_CONTEXT_KEY
from app.tools.growth_strategy_tools import (
    AdjustUserStrategyStateParams,
    AdjustUserStrategyStateTool,
    GetSituationBriefParams,
    GetSituationBriefTool,
    WriteEpisodeNoteParams,
    WriteEpisodeNoteTool,
)
from app.tools.intervention_tools import (
    GetInterventionTrackRecordParams,
    GetInterventionTrackRecordTool,
    RecordInterventionFeedbackParams,
    RecordInterventionFeedbackTool,
)
from app.tools.material_retrieval_tools import RetrieveUserMaterialParams, RetrieveUserMaterialTool


class _FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self._kv.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._kv[key] = value
        self._ttl[key] = ttl

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._kv.pop(key, None)


@pytest.fixture
async def test_plan(db_session, test_user) -> Plan:
    plan = Plan(
        user_id=test_user.id,
        name="桥接测试计划",
        type=PlanType.SPRINT,
        description="验证 Bridge 3 工具写回",
        plan_stage=PlanStage.SPRINT,
        target_date=date(2026, 4, 20),
        daily_available_minutes=75,
        progress=0.2,
        is_active=True,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


def _set_runtime_context(db_session, payload: dict) -> None:
    sync_session = getattr(db_session, "sync_session", None)
    if sync_session is None:
        db_session.sync_session = SimpleNamespace(info={})
        sync_session = db_session.sync_session
    info = getattr(sync_session, "info", None)
    if not isinstance(info, dict):
        sync_session.info = {}
    sync_session.info[TOOL_RUNTIME_CONTEXT_KEY] = payload


@pytest.mark.asyncio
async def test_growth_tools_register_in_dynamic_registry():
    registry = DynamicToolRegistry()
    registry.clear_all()

    try:
        registry.register_from_module("app.tools.growth_strategy_tools")
        registry.register_from_module("app.tools.material_retrieval_tools")
        registry.register_from_module("app.tools.intervention_tools")

        assert registry.get_tool("get_situation_brief") is not None
        assert registry.get_tool("get_user_strategy_state") is not None
        assert registry.get_tool("adjust_user_strategy_state") is not None
        assert registry.get_tool("retrieve_user_material") is not None
        assert registry.get_tool("get_intervention_track_record") is not None
        assert registry.get_tool("record_intervention_feedback") is not None
        assert registry.get_tool("write_episode_note") is not None

        schema = registry.get_openai_tools_schema()
        assert any(item["function"]["name"] == "retrieve_user_material" for item in schema)
        assert any(item["function"]["name"] == "record_intervention_feedback" for item in schema)
    finally:
        registry.clear_all()
        registry.ensure_package_registered("app.tools")


@pytest.mark.asyncio
async def test_get_situation_brief_tool_prefers_runtime_snapshot():
    tool = GetSituationBriefTool()
    db_session = SimpleNamespace(
        sync_session=SimpleNamespace(
            info={
                TOOL_RUNTIME_CONTEXT_KEY: {
                    "situation_brief": {
                        "focus_question": "What matters most now?",
                        "summary": "Exam week and overload signals are active.",
                        "source_trace": {"freshness": "fresh"},
                    }
                }
            }
        )
    )

    result = await tool.execute(
        GetSituationBriefParams(include_source_trace=False),
        user_id="00000000-0000-0000-0000-000000000000",
        db_session=db_session,
    )

    assert result.success is True
    assert result.data["situation_brief"]["summary"] == "Exam week and overload signals are active."
    assert "source_trace" not in result.data["situation_brief"]


@pytest.mark.asyncio
async def test_adjust_user_strategy_state_tool_writes_effective_state(db_session, test_user, test_plan):
    redis = _FakeRedis()
    _set_runtime_context(
        db_session,
        {
            "session_id": "session-bridge-3",
            "plan_id": str(test_plan.id),
            "redis_client": redis,
        },
    )

    tool = AdjustUserStrategyStateTool()
    result = await tool.execute(
        AdjustUserStrategyStateParams(
            layer="session",
            changes={
                "session_mode": "recovery",
                "retrieval_emphasis": "user_materials",
                "push_vs_support": 0.15,
            },
            reason="user explicitly asked for slower support and tighter grounding",
            evidence={"source": "conversation", "snippet": "slow down and use my notes"},
            confidence=0.91,
        ),
        user_id=str(test_user.id),
        db_session=db_session,
    )

    assert result.success is True
    effective = result.data["effective_state"]
    assert effective["session_mode"] == "recovery"
    assert effective["retrieval_emphasis"] == "user_materials"
    assert effective["push_vs_support"] == 0.15
    assert effective["meta"]["sources"]["session_mode"] == "session"


@pytest.mark.asyncio
async def test_write_episode_note_tool_persists_episode_layer_note(db_session, test_user, test_plan):
    _set_runtime_context(
        db_session,
        {
            "session_id": "session-bridge-3-note",
            "plan_id": str(test_plan.id),
            "redis_client": _FakeRedis(),
        },
    )

    tool = WriteEpisodeNoteTool()
    result = await tool.execute(
        WriteEpisodeNoteParams(
            note="Exam prep week, high stress, keep workload narrow.",
            reason="user described a short-term crunch window",
            evidence={"source": "conversation", "snippet": "I am in exam prep week"},
            confidence=0.87,
        ),
        user_id=str(test_user.id),
        db_session=db_session,
    )

    assert result.success is True
    assert result.data["effective_state"]["current_episode_note"] == "Exam prep week, high stress, keep workload narrow."
    assert result.data["effective_state"]["meta"]["sources"]["current_episode_note"] == "episode"


@pytest.mark.asyncio
async def test_adjust_user_strategy_state_tool_rejects_invalid_episode_plan_id(db_session, test_user):
    _set_runtime_context(
        db_session,
        {
            "session_id": "session-bridge-invalid-plan",
            "plan_id": "not-a-uuid",
            "redis_client": _FakeRedis(),
        },
    )

    tool = AdjustUserStrategyStateTool()
    result = await tool.execute(
        AdjustUserStrategyStateParams(
            layer="episode",
            changes={"retrieval_emphasis": "user_materials"},
            reason="user asked to ground in their uploaded notes",
            evidence={"source": "conversation", "snippet": "use my notes"},
            confidence=0.88,
        ),
        user_id=str(test_user.id),
        db_session=db_session,
    )

    assert result.success is False
    assert result.error_type == "invalid_identifier"


@pytest.mark.asyncio
async def test_adjust_user_strategy_state_tool_requires_session_id_for_session_writes(db_session, test_user):
    _set_runtime_context(
        db_session,
        {
            "plan_id": str(uuid4()),
            "redis_client": _FakeRedis(),
        },
    )

    tool = AdjustUserStrategyStateTool()
    result = await tool.execute(
        AdjustUserStrategyStateParams(
            layer="session",
            changes={"session_mode": "recovery"},
            reason="user asked to slow down",
            evidence={"source": "conversation", "snippet": "slow down"},
            confidence=0.8,
        ),
        user_id=str(test_user.id),
        db_session=db_session,
    )

    assert result.success is False
    assert result.error_type == "missing_identifier"


@pytest.mark.asyncio
async def test_retrieve_user_material_tool_formats_scoped_results(monkeypatch):
    scoped_files = [
        SimpleNamespace(
            id=uuid4(),
            file_name="Thermo Notes.pdf",
            mime_type="application/pdf",
            status="ready",
        )
    ]
    fake_chunk = SimpleNamespace(
        id=uuid4(),
        file_id=scoped_files[0].id,
        chunk_index=3,
        section_title="Entropy",
        page_numbers=[5],
        content="Entropy increases in isolated systems until equilibrium is reached.",
    )
    fake_result = SimpleNamespace(chunk=fake_chunk, file_name="Thermo Notes.pdf", score=0.92)
    fake_retrieval = SimpleNamespace(document_vector_search=AsyncMock(return_value=[fake_result]))
    fake_knowledge = SimpleNamespace(generate_hypothetical_answer=AsyncMock(return_value="expanded thermo query"))

    monkeypatch.setattr(
        "app.tools.material_retrieval_tools._resolve_scoped_files",
        AsyncMock(return_value=scoped_files),
    )
    monkeypatch.setattr(
        "app.tools.material_retrieval_tools.KnowledgeRetrievalService",
        lambda _db: fake_retrieval,
    )
    monkeypatch.setattr(
        "app.tools.material_retrieval_tools.KnowledgeService",
        lambda _db: fake_knowledge,
    )

    tool = RetrieveUserMaterialTool()
    result = await tool.execute(
        RetrieveUserMaterialParams(query="Where do my notes explain entropy?", limit=3),
        user_id=str(uuid4()),
        db_session=SimpleNamespace(sync_session=SimpleNamespace(info={TOOL_RUNTIME_CONTEXT_KEY: {}})),
    )

    assert result.success is True
    assert result.data["vector_query"] == "expanded thermo query"
    assert result.data["scoped_file_count"] == 1
    assert result.data["results"][0]["file_name"] == "Thermo Notes.pdf"
    assert result.data["results"][0]["section_title"] == "Entropy"


@pytest.mark.asyncio
async def test_get_intervention_track_record_tool_reads_recent_history(db_session, test_user):
    record = InterventionRecord(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.STALL_PATTERN,
        delivery_strategy=DeliveryStrategy.MICRO_RESTART,
        delivery_channel=DeliveryChannel.CHAT,
        acceptance_status=InterventionAcceptanceStatus.CREATED,
    )
    db_session.add(record)
    await db_session.commit()

    tool = GetInterventionTrackRecordTool()
    result = await tool.execute(
        GetInterventionTrackRecordParams(days=30, limit=5),
        user_id=str(test_user.id),
        db_session=db_session,
    )

    assert result.success is True
    assert result.data["acceptance_stats"]["total"] >= 1
    assert result.data["recent_records"][0]["trigger_type"] == "STALL_PATTERN"
    assert result.data["response_profile"]["total_samples"] == 0


@pytest.mark.asyncio
async def test_record_intervention_feedback_tool_binds_feedback_to_existing_record(db_session, test_user):
    record = InterventionRecord(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.CONCEPT_GAP,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        acceptance_status=InterventionAcceptanceStatus.DELIVERED,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    tool = RecordInterventionFeedbackTool()
    result = await tool.execute(
        RecordInterventionFeedbackParams(
            intervention_id=str(record.id),
            sentiment="dismissed",
            user_words="The reminder landed badly and felt mistimed.",
            confidence=0.86,
            message_id="msg-42",
        ),
        user_id=str(test_user.id),
        db_session=db_session,
    )
    await db_session.refresh(record)

    assert result.success is True
    assert record.acceptance_status == InterventionAcceptanceStatus.DISMISSED
    feedback_log = (record.action_payload or {}).get("conversation_feedback_log") or []
    assert feedback_log[0]["sentiment"] == "dismissed"
    assert feedback_log[0]["message_id"] == "msg-42"
    assert result.data["last_feedback_binding"]["message_id"] == "msg-42"
