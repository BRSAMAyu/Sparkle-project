from __future__ import annotations

from uuid import uuid4

import pytest

from app.adapters.openclaw.intent_translator import IntentTranslator
from app.adapters.openclaw.result_parser import ResultParser
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
from app.services.execution_result_validator import ExecutionResultValidator
from app.services.execution_service import ExecutionService


@pytest.fixture
def openclaw_settings():
    from app.config import settings

    original = {
        "OPENCLAW_ENABLED": settings.OPENCLAW_ENABLED,
        "OPENCLAW_GATEWAY_URL": settings.OPENCLAW_GATEWAY_URL,
        "OPENCLAW_AUTH_TOKEN": settings.OPENCLAW_AUTH_TOKEN,
        "OPENCLAW_DEFAULT_AGENT_ID": settings.OPENCLAW_DEFAULT_AGENT_ID,
    }
    settings.OPENCLAW_ENABLED = True
    settings.OPENCLAW_GATEWAY_URL = "http://openclaw.local"
    settings.OPENCLAW_AUTH_TOKEN = "token"
    settings.OPENCLAW_DEFAULT_AGENT_ID = "default"
    try:
        yield settings
    finally:
        settings.OPENCLAW_ENABLED = original["OPENCLAW_ENABLED"]
        settings.OPENCLAW_GATEWAY_URL = original["OPENCLAW_GATEWAY_URL"]
        settings.OPENCLAW_AUTH_TOKEN = original["OPENCLAW_AUTH_TOKEN"]
        settings.OPENCLAW_DEFAULT_AGENT_ID = original["OPENCLAW_DEFAULT_AGENT_ID"]


def test_intent_translator_builds_response_request() -> None:
    translator = IntentTranslator()
    intent = ExecutionIntent(
        id=uuid4(),
        task_id=uuid4(),
        user_id=uuid4(),
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="整理网页资料",
        instructions=["只访问公开网页"],
        target_env=ExecutionTargetEnv.BROWSER,
        policy={"allow_exec": False, "allowed_tools": ["browser"]},
        success_criteria={"type": "structured_output", "required_fields": ["summary"]},
        result_contract={"artifact_types": ["json"]},
        timeout_seconds=120,
        status=ExecutionIntentStatus.READY,
        trust_level=TrustLevel.RAW,
        idempotency_key="x",
    )

    payload = translator.translate(intent, agent_id="worker")

    assert payload["model"] == "openclaw/worker"
    assert "Task Goal" in payload["input"]
    assert "ONLY use these tools: browser" in payload["instructions"]
    assert payload["stream"] is False


def test_result_parser_parses_text_and_json() -> None:
    parser = ResultParser()

    parsed = parser.parse(
        {
            "id": "resp_123",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"done","items":["a","b"]}',
                        }
                    ],
                }
            ],
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
    )

    assert parsed["success"] is True
    assert parsed["parsed_output"] == {"summary": "done", "items": ["a", "b"]}
    assert parsed["tool_calls_count"] == 0


def test_execution_result_validator_builds_warnings_and_replay() -> None:
    validator = ExecutionResultValidator()

    warnings = validator.validate(
        parsed={
            "success": True,
            "output": "ok",
            "parsed_output": None,
            "artifacts": [],
            "tool_calls_count": 0,
        },
        result_contract={
            "required_fields": ["summary"],
            "artifact_types": ["image"],
        },
    )
    replay_steps = validator.build_replay_steps_from_raw_response(
        {
            "output": [
                {
                    "type": "function_call",
                    "name": "browser.search",
                    "arguments": {"query": "sparkle"},
                },
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"done"}',
                        }
                    ],
                },
            ]
        }
    )

    assert any(item["code"] == "missing_artifacts" for item in warnings)
    assert any(item["code"] == "thin_output" for item in warnings)
    assert len(replay_steps) == 2
    assert replay_steps[0]["kind"] == "tool_call"
    assert replay_steps[1]["kind"] == "message"


def test_execution_result_validator_builds_comparison_summary() -> None:
    validator = ExecutionResultValidator()

    class _Record:
        def __init__(self, *, quality_score, tool_calls_count, trust_level):
            self.quality_score = quality_score
            self.tool_calls_count = tool_calls_count
            self.trust_level = trust_level

    summary = validator.build_comparison_summary(
        current_record=_Record(
            quality_score=0.91,
            tool_calls_count=2,
            trust_level="validated",
        ),
        previous_record=_Record(
            quality_score=0.76,
            tool_calls_count=4,
            trust_level="raw",
        ),
    )

    assert summary is not None
    assert summary["quality_delta"] > 0
    assert "更稳" in summary["headline"]


@pytest.mark.asyncio
async def test_execution_service_handoff_creates_record_and_completes_task(
    db_session,
    openclaw_settings,
    monkeypatch,
) -> None:
    async def _publish(*args, **kwargs):
        return None

    async def _progress(*args, **kwargs):
        return {}

    async def _execute(self, request_body, *, timeout_seconds=None):
        return {
            "id": "resp_test_1",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"整理完成","sources":["https://example.com"]}',
                        }
                    ],
                }
            ],
            "usage": {"input_tokens": 12, "output_tokens": 34},
        }

    monkeypatch.setattr("app.services.execution_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_service.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(username="phase1user", email="phase1@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="整理网页资料",
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

    service = ExecutionService(db=db_session)
    intent = await service.handoff_to_openclaw(
        task_id=task.id,
        user_id=user.id,
        success_criteria={"type": "structured_output", "required_fields": ["summary", "sources"]},
        result_contract={"required_fields": ["output", "parsed_output"]},
    )

    await db_session.refresh(task)

    assert intent.status == ExecutionIntentStatus.SUCCEEDED
    assert intent.trust_level == TrustLevel.VALIDATED
    assert task.status == TaskStatus.COMPLETED
    assert task.execution_mode == ExecutionMode.AGENT.value
    assert task.actual_minutes == 0

    record = await service.get_execution_record(intent_id=intent.id, user_id=user.id)
    assert record is not None
    assert record.external_run_id == "resp_test_1"
    assert record.trust_level == TrustLevel.VALIDATED.value
    assert record.parsed_output == {"summary": "整理完成", "sources": ["https://example.com"]}


@pytest.mark.asyncio
async def test_execution_service_handback_marks_intent_and_task_human(
    db_session,
    openclaw_settings,
    monkeypatch,
) -> None:
    async def _publish(*args, **kwargs):
        return None

    async def _progress(*args, **kwargs):
        return {}

    monkeypatch.setattr("app.services.execution_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_service.task_monitor_service.publish_progress", _progress)

    user = User(username="handbackuser", email="handback@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="整理 OCR 文档",
        type=TaskType.OCR,
        tags=[],
        estimated_minutes=15,
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
        target_env=ExecutionTargetEnv.DOCUMENT,
        policy={},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.RUNNING,
        trust_level=TrustLevel.RAW,
        idempotency_key=f"manual:{task.id}",
    )
    db_session.add(intent)
    task.execution_mode = ExecutionMode.AGENT.value
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(intent)

    service = ExecutionService(db=db_session)
    updated = await service.handback(intent_id=intent.id, user_id=user.id, reason="用户取回")
    await db_session.refresh(task)

    assert updated.status == ExecutionIntentStatus.HANDED_BACK
    assert updated.error_category == "handed_back"
    assert task.execution_mode == ExecutionMode.HUMAN.value
