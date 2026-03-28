from __future__ import annotations

import pytest

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
from app.services.execution_quality_service import ExecutionQualityService
from app.services.execution_service import ExecutionService
from app.services.execution_template_service import ExecutionTemplateService


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


@pytest.fixture
def mute_execution_side_effects(monkeypatch):
    async def _publish(*args, **kwargs):
        return None

    async def _progress(*args, **kwargs):
        return {}

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.execution_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_service.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.services.execution_ingestor.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_ingestor.task_monitor_service.publish_progress", _progress)
    monkeypatch.setattr("app.services.execution_learning_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.profile_write_service.event_bus.publish", _publish)
    monkeypatch.setattr("app.services.execution_learning_service.ExecutionLearningService.handle_trusted_execution", _noop)
    monkeypatch.setattr("app.services.execution_learning_service.ExecutionLearningService.handle_handed_back", _noop)


def test_execution_template_service_matches_browser_and_hybrid_templates() -> None:
    service = ExecutionTemplateService()
    task = Task(
        user_id=None,
        title="搜索并整理目标网站的申请表单字段",
        type=TaskType.PLANNING,
        tags=["browser", "approval"],
        estimated_minutes=20,
        difficulty=1,
        energy_cost=1,
    )

    matches = service.list_templates(task=task)

    assert matches
    assert matches[0].definition.template_id in {
        "browser_form_prepare",
        "web_research_brief",
    }


@pytest.mark.asyncio
async def test_create_intent_applies_template_strategy_and_node_policy(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    async def _list_nodes(self, *, connected_only=True, last_connected=None):
        return {
            "items": [
                {
                    "nodeId": "node-shell",
                    "name": "Mac Mini",
                    "platform": "macos",
                    "connected": True,
                    "commands": ["system.run"],
                    "caps": ["system.run"],
                }
            ]
        }

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.list_nodes", _list_nodes)

    user = User(username="phase4intent", email="phase4intent@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="运行终端诊断检查仓库状态",
        type=TaskType.PLANNING,
        tags=["shell", "ops"],
        estimated_minutes=15,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    service = ExecutionService(db=db_session)
    intent = await service.create_intent(
        task_id=task.id,
        user_id=user.id,
        template_id="shell_diagnostics",
    )

    assert intent.execution_mode == ExecutionMode.AGENT
    assert intent.policy["template_metadata"]["template_id"] == "shell_diagnostics"
    assert intent.policy["quality_strategy"]["variant_name"]
    assert intent.policy["target_node_id"] == "node-shell"
    assert intent.policy["target_node_command"] == "system.run"


@pytest.mark.asyncio
async def test_hybrid_template_forces_waiting_approval_even_without_remote_signal(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    async def _execute(self, request_body, *, timeout_seconds=None, event_callback=None):
        return {
            "id": "resp_phase4_hybrid",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": (
                                '{"draft":"已整理草稿","fields_to_confirm":["姓名","邮箱"],'
                                '"final_action":"提交表单"}'
                            ),
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(username="phase4hybrid", email="phase4hybrid@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="填写并提交报名表单",
        type=TaskType.SOCIAL,
        tags=["browser", "approval"],
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
        template_id="browser_form_prepare",
    )
    record = await service.get_execution_record(intent_id=intent.id, user_id=user.id)

    assert intent.status == ExecutionIntentStatus.WAITING_APPROVAL
    assert intent.execution_mode == ExecutionMode.HYBRID
    assert record is not None
    assert record.approval_requested == 1
    assert record.trust_level == TrustLevel.VALIDATED.value


@pytest.mark.asyncio
async def test_quality_summary_records_metrics(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    async def _list_nodes(self, *, connected_only=True, last_connected=None):
        return {"items": []}

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.list_nodes", _list_nodes)

    user = User(username="phase4quality", email="phase4quality@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="整理调研资料并输出简报",
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
    intent = await service.create_intent(
        task_id=task.id,
        user_id=user.id,
        template_id="web_research_brief",
    )

    record = ExecutionRecord(
        execution_intent_id=intent.id,
        user_id=user.id,
        task_id=task.id,
        executor_type="openclaw",
        raw_response={"id": "quality-run"},
        parsed_output={"summary": "done"},
        artifacts=[],
        trust_level=TrustLevel.TRUSTED.value,
        quality_score=0.93,
        duration_ms=1200,
        approval_requested=0,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    intent.status = ExecutionIntentStatus.SUCCEEDED
    intent.trust_level = TrustLevel.TRUSTED
    db_session.add(intent)
    await db_session.commit()

    quality_service = ExecutionQualityService(db_session)
    await quality_service.record_outcome(intent=intent, record=record, outcome="succeeded")
    summary = await quality_service.get_summary()

    assert summary["experiment_name"] == "openclaw_execution_strategy_v1"
    assert summary["sample_size_collected"] >= 1
    assert any(variant["sample_size"] >= 1 for variant in summary["variants"])


@pytest.mark.asyncio
async def test_create_intent_fails_closed_when_required_node_missing(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    async def _list_nodes(self, *, connected_only=True, last_connected=None):
        return {"items": []}

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.list_nodes", _list_nodes)

    user = User(
        username="phase4missingnode",
        email="phase4missingnode@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="运行终端诊断检查仓库状态",
        type=TaskType.PLANNING,
        tags=["shell", "ops"],
        estimated_minutes=15,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    service = ExecutionService(db=db_session)
    with pytest.raises(ValueError, match="requires a node with system.run capability"):
        await service.create_intent(
            task_id=task.id,
            user_id=user.id,
            template_id="shell_diagnostics",
        )


@pytest.mark.asyncio
async def test_handback_rejects_terminal_intent(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
) -> None:
    user = User(
        username="phase4terminal",
        email="phase4terminal@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="整理调研资料",
        type=TaskType.OCR,
        tags=["research"],
        estimated_minutes=10,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.COMPLETED,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    intent = ExecutionIntent(
        task_id=task.id,
        user_id=user.id,
        plan_id=task.plan_id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="整理调研资料",
        instructions=["输出摘要"],
        target_env=ExecutionTargetEnv.BROWSER,
        policy={"quality_strategy": {"variant_name": "balanced_control"}},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=60,
        status=ExecutionIntentStatus.SUCCEEDED,
        trust_level=TrustLevel.TRUSTED,
        idempotency_key=f"terminal-{task.id}",
    )
    db_session.add(intent)
    await db_session.commit()
    await db_session.refresh(intent)

    service = ExecutionService(db=db_session)
    with pytest.raises(ValueError, match="already terminal"):
        await service.handback(intent_id=intent.id, user_id=user.id, reason="too late")


@pytest.mark.asyncio
async def test_classify_task_uses_short_ttl_cache(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    user = User(
        username="phase4cache",
        email="phase4cache@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="搜索并整理调研资料",
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
    second_service = ExecutionService(db=db_session)
    calls = 0
    original = ExecutionService._classify_task_entity

    def spy(self, task):
        nonlocal calls
        calls += 1
        return original(self, task)

    monkeypatch.setattr(ExecutionService, "_classify_task_entity", spy)
    ExecutionService._shared_classify_cache.clear()

    first = await service.classify_task(task_id=task.id, user_id=user.id)
    second = await second_service.classify_task(task_id=task.id, user_id=user.id)

    assert first.execution_mode == second.execution_mode
    assert calls == 1
