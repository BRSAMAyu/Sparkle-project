from __future__ import annotations

import pytest

from app.adapters.openclaw.result_parser import ResultParser
from app.models.execution_intent import (
    ExecutionIntent,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionTargetEnv,
    ExecutorType,
    TrustLevel,
)
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.execution_ingestor import ExecutionIngestor
from app.services.execution_service import ExecutionService


@pytest.fixture
def openclaw_settings():
    from app.config import settings

    original = {
        "OPENCLAW_ENABLED": settings.OPENCLAW_ENABLED,
        "OPENCLAW_GATEWAY_URL": settings.OPENCLAW_GATEWAY_URL,
        "OPENCLAW_AUTH_TOKEN": settings.OPENCLAW_AUTH_TOKEN,
        "OPENCLAW_DEFAULT_AGENT_ID": settings.OPENCLAW_DEFAULT_AGENT_ID,
        "OPENCLAW_TRANSPORT": settings.OPENCLAW_TRANSPORT,
        "OPENCLAW_WS_URL": settings.OPENCLAW_WS_URL,
        "OPENCLAW_WS_ALLOW_INSECURE_AUTH": settings.OPENCLAW_WS_ALLOW_INSECURE_AUTH,
    }
    settings.OPENCLAW_ENABLED = True
    settings.OPENCLAW_GATEWAY_URL = "http://openclaw.local"
    settings.OPENCLAW_AUTH_TOKEN = "token"
    settings.OPENCLAW_DEFAULT_AGENT_ID = "default"
    settings.OPENCLAW_TRANSPORT = "responses_http"
    settings.OPENCLAW_WS_URL = "ws://openclaw.local"
    settings.OPENCLAW_WS_ALLOW_INSECURE_AUTH = True
    try:
        yield settings
    finally:
        settings.OPENCLAW_ENABLED = original["OPENCLAW_ENABLED"]
        settings.OPENCLAW_GATEWAY_URL = original["OPENCLAW_GATEWAY_URL"]
        settings.OPENCLAW_AUTH_TOKEN = original["OPENCLAW_AUTH_TOKEN"]
        settings.OPENCLAW_DEFAULT_AGENT_ID = original["OPENCLAW_DEFAULT_AGENT_ID"]
        settings.OPENCLAW_TRANSPORT = original["OPENCLAW_TRANSPORT"]
        settings.OPENCLAW_WS_URL = original["OPENCLAW_WS_URL"]
        settings.OPENCLAW_WS_ALLOW_INSECURE_AUTH = original["OPENCLAW_WS_ALLOW_INSECURE_AUTH"]


def test_result_parser_detects_waiting_approval() -> None:
    parser = ResultParser()

    parsed = parser.parse(
        {
            "id": "resp_approval_1",
            "status": "requires_action",
            "required_action": {"type": "approval"},
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"draft ready"}',
                        }
                    ],
                }
            ],
        }
    )

    assert parsed["requires_approval"] is True
    assert parsed["approval_requests"] == 1
    assert parsed["success"] is False


@pytest.mark.asyncio
async def test_execution_service_handoff_waiting_approval(
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
            "id": "resp_waiting_approval",
            "status": "requires_action",
            "required_action": {"type": "approval"},
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"ready for approval","sources":["https://example.com"]}',
                        }
                    ],
                }
            ],
            "usage": {"input_tokens": 9, "output_tokens": 18},
        }

    monkeypatch.setattr("app.services.execution_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_service.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.services.execution_ingestor.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_ingestor.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(username="phase2wait", email="phase2wait@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="调用 API 更新任务状态",
        type=TaskType.PLANNING,
        tags=["api"],
        estimated_minutes=15,
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
        result_contract={"required_fields": ["summary", "sources"]},
    )

    await db_session.refresh(task)
    record = await service.get_execution_record(intent_id=intent.id, user_id=user.id)

    assert intent.status == ExecutionIntentStatus.WAITING_APPROVAL
    assert intent.execution_mode == ExecutionMode.HYBRID
    assert intent.trust_level == TrustLevel.VALIDATED
    assert task.status == TaskStatus.PENDING
    assert record is not None
    assert record.approval_requested == 1
    assert record.trust_level == TrustLevel.VALIDATED.value


@pytest.mark.asyncio
async def test_confirm_result_promotes_to_trusted_and_completes_task(
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
            "id": "resp_confirm_1",
            "status": "requires_action",
            "required_action": {"type": "approval"},
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"approved result","sources":["https://example.com"]}',
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr("app.services.execution_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_service.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.services.execution_ingestor.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_ingestor.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(username="phase2confirm", email="phase2confirm@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="调用 API 更新任务状态",
        type=TaskType.PLANNING,
        tags=["api"],
        estimated_minutes=10,
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
        result_contract={"required_fields": ["summary", "sources"]},
    )
    record = await service.get_execution_record(intent_id=intent.id, user_id=user.id)
    assert record is not None

    updated_record = await service.confirm_result(record_id=record.id, user_id=user.id)
    updated_intent = await service.get_intent(intent_id=intent.id, user_id=user.id)
    await db_session.refresh(task)

    assert updated_record.trust_level == TrustLevel.TRUSTED.value
    assert updated_intent.status == ExecutionIntentStatus.SUCCEEDED
    assert updated_intent.trust_level == TrustLevel.TRUSTED
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_reject_result_hands_back_and_restores_task(
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
            "id": "resp_reject_1",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"done","sources":["https://example.com"]}',
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr("app.services.execution_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_service.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.services.execution_ingestor.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_ingestor.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(username="phase2reject", email="phase2reject@example.com", hashed_password="hashed", photon_balance=0)
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
        result_contract={"required_fields": ["summary", "sources"]},
    )
    record = await service.get_execution_record(intent_id=intent.id, user_id=user.id)
    assert record is not None
    assert task.status == TaskStatus.COMPLETED

    updated_record = await service.reject_result(
        record_id=record.id,
        user_id=user.id,
        reason="结果不符合预期",
    )
    updated_intent = await service.get_intent(intent_id=intent.id, user_id=user.id)
    await db_session.refresh(task)

    assert updated_record.trust_level == TrustLevel.RAW.value
    assert updated_record.error_category == "user_rejected"
    assert updated_intent.status == ExecutionIntentStatus.HANDED_BACK
    assert updated_intent.error_category == "user_rejected"
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.execution_mode == ExecutionMode.HUMAN.value


@pytest.mark.asyncio
async def test_create_intent_blocks_second_active_execution(
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

    user = User(username="phase2active", email="phase2active@example.com", hashed_password="hashed", photon_balance=0)
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
    intent = await service.create_intent(task_id=task.id, user_id=user.id)
    assert intent.status == ExecutionIntentStatus.READY

    with pytest.raises(ValueError, match="Active execution already exists"):
        await service.create_intent(task_id=task.id, user_id=user.id)


@pytest.mark.asyncio
async def test_ingestor_invalid_parsed_output_schema_blocks_completion(
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
            "id": "resp_schema_invalid",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary": 123}',
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr("app.services.execution_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_service.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.services.execution_ingestor.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_ingestor.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(username="phase2schema", email="phase2schema@example.com", hashed_password="hashed", photon_balance=0)
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
        success_criteria={"type": "structured_output", "required_fields": ["summary"]},
        result_contract={
            "required_fields": ["summary"],
            "parsed_output_schema": {
                "required": ["summary"],
                "properties": {
                    "summary": {"type": "string"},
                },
            },
        },
    )
    await db_session.refresh(task)
    record = await service.get_execution_record(intent_id=intent.id, user_id=user.id)

    assert intent.status == ExecutionIntentStatus.FAILED
    assert task.status == TaskStatus.PENDING
    assert record is not None
    assert record.error_message is not None
    assert record.error_message.startswith("parsed_output_schema_invalid")


def test_execution_ingestor_accepts_union_schema_types(db_session) -> None:
    ingestor = ExecutionIngestor(db=db_session)
    parsed = {
        "success": True,
        "output": '{"summary":"ok","key_output":"pwd output","next_steps":"none"}',
        "parsed_output": {
            "summary": "ok",
            "key_output": "pwd output",
            "next_steps": "none",
        },
        "artifacts": [],
        "tool_calls_count": 0,
        "token_usage": None,
        "requires_approval": False,
        "approval_requests": 0,
        "error_message": None,
        "raw_status": "completed",
    }

    updated = ingestor._validate_parsed_output_contract(
        parsed=parsed,
        result_contract={
            "parsed_output_schema": {
                "required": ["summary", "key_output", "next_steps"],
                "properties": {
                    "summary": {"type": "string"},
                    "key_output": {"type": ["array", "string"]},
                    "next_steps": {"type": ["array", "string"]},
                },
            }
        },
    )

    assert updated["success"] is True
    assert updated["parsed_output"]["key_output"] == "pwd output"


@pytest.mark.asyncio
async def test_confirm_result_uses_gateway_approval_resolution(
    db_session,
    openclaw_settings,
    monkeypatch,
) -> None:
    from app.config import settings

    settings.OPENCLAW_TRANSPORT = "gateway_ws"

    async def _publish(*args, **kwargs):
        return None

    async def _progress(*args, **kwargs):
        return {}

    async def _execute(self, request_body, *, timeout_seconds=None, event_callback=None):
        return {
            "id": "run_gateway_approval",
            "status": "requires_action",
            "approval": {"id": "approval-123"},
            "required_action": {"type": "approval", "approval_id": "approval-123"},
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"summary":"awaiting approval"}'}],
                }
            ],
            "session_key": request_body.get("sessionKey"),
            "transport": "gateway_ws",
        }

    async def _resolve_approval(
        self,
        *,
        approval_id,
        decision,
        run_id,
        session_key,
        timeout_seconds=None,
        event_callback=None,
    ):
        assert approval_id == "approval-123"
        assert decision == "allow-once"
        assert run_id == "run_gateway_approval"
        assert session_key.startswith("sparkle:default:")
        return {
            "id": run_id,
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"approved result","sources":["https://example.com"]}',
                        }
                    ],
                }
            ],
            "session_key": session_key,
            "transport": "gateway_ws",
        }

    monkeypatch.setattr("app.services.execution_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_service.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.services.execution_ingestor.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_ingestor.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)
    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.resolve_approval", _resolve_approval)

    user = User(
        username="phase2gatewayconfirm",
        email="phase2gatewayconfirm@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="调用 API 更新任务状态",
        type=TaskType.PLANNING,
        tags=["api"],
        estimated_minutes=10,
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
        result_contract={"required_fields": ["summary", "sources"]},
    )
    record = await service.get_execution_record(intent_id=intent.id, user_id=user.id)
    assert record is not None
    assert intent.status == ExecutionIntentStatus.WAITING_APPROVAL

    updated_record = await service.confirm_result(record_id=record.id, user_id=user.id)
    updated_intent = await service.get_intent(intent_id=intent.id, user_id=user.id)
    await db_session.refresh(task)

    assert updated_record.trust_level == TrustLevel.TRUSTED.value
    assert updated_intent.status == ExecutionIntentStatus.SUCCEEDED
    assert updated_intent.trust_level == TrustLevel.TRUSTED
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_cancel_uses_gateway_abort_when_transport_enabled(
    db_session,
    openclaw_settings,
    monkeypatch,
) -> None:
    from app.config import settings

    settings.OPENCLAW_TRANSPORT = "gateway_ws"

    async def _publish(*args, **kwargs):
        return None

    async def _progress(*args, **kwargs):
        return {}

    captured: dict[str, str | None] = {}

    async def _cancel_run(self, *, session_key, run_id=None):
        captured["session_key"] = session_key
        captured["run_id"] = run_id

    monkeypatch.setattr("app.services.execution_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_service.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.cancel_run", _cancel_run)

    user = User(
        username="phase2gatewaycancel",
        email="phase2gatewaycancel@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
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
        status=ExecutionIntentStatus.RUNNING,
        trust_level=TrustLevel.RAW,
        idempotency_key=f"gateway:{task.id}",
        external_run_id="run-cancel-1",
    )
    db_session.add(intent)
    await db_session.commit()
    await db_session.refresh(intent)

    service = ExecutionService(db=db_session)
    updated = await service.cancel(intent_id=intent.id, user_id=user.id)

    assert updated.status == ExecutionIntentStatus.CANCELED
    assert captured["run_id"] == "run-cancel-1"
    assert captured["session_key"].startswith("sparkle:default:")
