from __future__ import annotations

import pytest
from sqlalchemy import select

from app.adapters.openclaw.client import OpenClawError
from app.models.execution_audit_log import ExecutionAuditLog
from app.models.execution_intent import (
    ExecutionIntent,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionTargetEnv,
    ExecutorType,
    TrustLevel,
)
from app.models.execution_schedule import ExecutionScheduleTriggerType
from app.models.execution_record import ExecutionRecord
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.execution_quality_service import ExecutionQualityService
from app.services.execution_preference_service import ExecutionPreferenceService
from app.services.execution_schedule_service import ExecutionScheduleService
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
        "OPENCLAW_DEFAULT_WORKDIR": settings.OPENCLAW_DEFAULT_WORKDIR,
        "OPENCLAW_MAX_CONCURRENT_RUNS": settings.OPENCLAW_MAX_CONCURRENT_RUNS,
    }
    settings.OPENCLAW_ENABLED = True
    settings.OPENCLAW_GATEWAY_URL = "http://openclaw.local"
    settings.OPENCLAW_AUTH_TOKEN = "token"
    settings.OPENCLAW_DEFAULT_AGENT_ID = "default"
    settings.OPENCLAW_TRANSPORT = "responses_http"
    settings.OPENCLAW_WS_URL = "ws://openclaw.local"
    settings.OPENCLAW_WS_ALLOW_INSECURE_AUTH = True
    settings.OPENCLAW_DEFAULT_WORKDIR = ""
    settings.OPENCLAW_MAX_CONCURRENT_RUNS = 3
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
        settings.OPENCLAW_DEFAULT_WORKDIR = original["OPENCLAW_DEFAULT_WORKDIR"]
        settings.OPENCLAW_MAX_CONCURRENT_RUNS = original["OPENCLAW_MAX_CONCURRENT_RUNS"]


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
async def test_create_intent_applies_default_shell_workdir(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    from app.config import settings

    settings.OPENCLAW_DEFAULT_WORKDIR = "/tmp/sparkle-demo"

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

    user = User(username="phase4workdir", email="phase4workdir@example.com", hashed_password="hashed", photon_balance=0)
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

    assert intent.policy["working_directory"] == "/tmp/sparkle-demo"


@pytest.mark.asyncio
async def test_create_intent_applies_cautious_execution_preferences(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
) -> None:
    user = User(
        username="phase4prefs",
        email="phase4prefs@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    await ExecutionPreferenceService(db_session).save_preferences(
        user_id=user.id,
        payload={"mode": "cautious"},
    )

    task = Task(
        user_id=user.id,
        title="搜索并整理目标网站的申请表单字段",
        type=TaskType.PLANNING,
        tags=["browser", "research"],
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

    assert intent.policy["approval_policy"] == "require_for_side_effects"
    assert intent.policy["execution_preferences"]["mode"] == "cautious"
    assert intent.policy["execution_preferences"]["rule_key"] == "browser_read"


@pytest.mark.asyncio
async def test_create_intent_prefers_affinity_node_for_shell_tasks(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    async def _list_nodes(self, *, connected_only=True, last_connected=None):
        return {
            "items": [
                {
                    "nodeId": "node-browser",
                    "name": "MacBook Air",
                    "platform": "macos",
                    "connected": True,
                    "status": "idle",
                    "commands": ["browser.open"],
                    "caps": ["browser"],
                },
                {
                    "nodeId": "node-shell",
                    "name": "Workstation",
                    "platform": "macos",
                    "connected": True,
                    "status": "idle",
                    "activeRuns": 1,
                    "commands": ["system.run"],
                    "caps": ["system.run"],
                },
            ]
        }

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.list_nodes", _list_nodes)

    user = User(username="phase4affinity", email="phase4affinity@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    await ExecutionPreferenceService(db_session).save_preferences(
        user_id=user.id,
        payload={
            "mode": "balanced",
            "node_affinity": {
                "shell": "node-shell",
            },
        },
    )

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

    assert intent.policy["target_node_id"] == "node-shell"
    assert intent.policy["execution_preferences"]["node_affinity"]["shell"] == "node-shell"
    assert intent.policy["node_selection"]["affinity_node_id"] == "node-shell"
    assert intent.policy["node_selection"]["fallback_applied"] is False


@pytest.mark.asyncio
async def test_create_intent_falls_back_when_affinity_node_is_offline(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    async def _list_nodes(self, *, connected_only=True, last_connected=None):
        return {
            "items": [
                {
                    "nodeId": "node-shell-preferred",
                    "name": "Workstation",
                    "platform": "macos",
                    "connected": False,
                    "status": "offline",
                    "commands": ["system.run"],
                    "caps": ["system.run"],
                },
                {
                    "nodeId": "node-shell-backup",
                    "name": "Mac Mini",
                    "platform": "macos",
                    "connected": True,
                    "status": "idle",
                    "commands": ["system.run"],
                    "caps": ["system.run"],
                },
            ]
        }

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.list_nodes", _list_nodes)

    user = User(username="phase4fallback", email="phase4fallback@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    await ExecutionPreferenceService(db_session).save_preferences(
        user_id=user.id,
        payload={
            "mode": "balanced",
            "node_affinity": {
                "shell": "node-shell-preferred",
            },
        },
    )

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

    assert intent.policy["target_node_id"] == "node-shell-backup"
    assert intent.policy["node_selection"]["fallback_applied"] is True
    assert intent.policy["node_selection"]["fallback_from_node_id"] == "node-shell-preferred"
    assert intent.policy["node_selection"]["selected_node_id"] == "node-shell-backup"


@pytest.mark.asyncio
async def test_create_intent_blocks_irreversible_high_risk_commands(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
) -> None:
    user = User(
        username="phase4risk",
        email="phase4risk@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    await ExecutionPreferenceService(db_session).save_preferences(
        user_id=user.id,
        payload={"mode": "autonomous"},
    )

    task = Task(
        user_id=user.id,
        title="在终端执行 rm -rf /tmp/old-build",
        type=TaskType.PLANNING,
        tags=["shell", "ops"],
        estimated_minutes=5,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    service = ExecutionService(db=db_session)
    with pytest.raises(ValueError, match="已被 Sparkle 拦截"):
        await service.create_intent(
            task_id=task.id,
            user_id=user.id,
            template_id="shell_diagnostics",
        )


@pytest.mark.asyncio
async def test_create_intent_marks_sensitive_data_warning_in_policy(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    async def _list_nodes(self, *, connected_only=True, last_connected=None):
        return {
            "items": [
                {
                    "nodeId": "node-shell-sensitive",
                    "name": "Secure Shell Node",
                    "platform": "macos",
                    "connected": True,
                    "commands": ["system.run"],
                    "caps": ["system.run"],
                }
            ]
        }

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.list_nodes", _list_nodes)

    user = User(
        username="phase4sensitive",
        email="phase4sensitive@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="帮我在终端检查这个 token 是否还能用：sk-abcdef1234567890abcdef",
        type=TaskType.PLANNING,
        tags=["shell", "ops"],
        estimated_minutes=5,
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

    assert intent.policy["contains_sensitive_data"] is True
    assert intent.policy["_risk_assessment"]["contains_sensitive_data"] is True
    labels = [
        item["label"]
        for item in intent.policy["_risk_assessment"]["sensitive_signals"]
    ]
    assert "OpenAI 风格密钥" in labels


@pytest.mark.asyncio
async def test_create_intent_attaches_duration_estimate_from_history(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
) -> None:
    user = User(
        username="phase4duration",
        email="phase4duration@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    prior_task = Task(
        user_id=user.id,
        title="整理网页资料",
        type=TaskType.OCR,
        tags=["browser"],
        estimated_minutes=20,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.COMPLETED,
    )
    db_session.add(prior_task)
    await db_session.commit()
    await db_session.refresh(prior_task)

    prior_intent = ExecutionIntent(
        plan_id=None,
        task_id=prior_task.id,
        user_id=user.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="搜索并整理网页资料",
        instructions=[],
        target_env=ExecutionTargetEnv.BROWSER,
        policy={},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.SUCCEEDED,
        trust_level=TrustLevel.TRUSTED,
        idempotency_key="phase4-duration-prior",
    )
    db_session.add(prior_intent)
    await db_session.commit()
    await db_session.refresh(prior_intent)

    prior_record = ExecutionRecord(
        execution_intent_id=prior_intent.id,
        user_id=user.id,
        task_id=prior_task.id,
        executor_type="openclaw",
        raw_response={},
        parsed_output={"summary": "done"},
        artifacts=[],
        trust_level=TrustLevel.TRUSTED.value,
        duration_ms=180000,
    )
    db_session.add(prior_record)
    await db_session.commit()

    task = Task(
        user_id=user.id,
        title="搜索并整理目标网站的申请表单字段",
        type=TaskType.PLANNING,
        tags=["browser", "research"],
        estimated_minutes=10,
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

    assert intent.policy["duration_estimate"]["estimated_seconds"] == 180
    assert intent.policy["duration_estimate"]["estimated_minutes"] == 3
    assert intent.policy["duration_estimate"]["source"] == "history"


@pytest.mark.asyncio
async def test_dispatch_queues_when_concurrency_limit_is_reached(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    from app.config import settings

    settings.OPENCLAW_MAX_CONCURRENT_RUNS = 1

    async def _execute(self, request_body, *, timeout_seconds=None):
        raise AssertionError("execute should not be called when intent is queued")

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(
        username="phase4concurrency",
        email="phase4concurrency@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    first_task = Task(
        user_id=user.id,
        title="任务一",
        type=TaskType.PLANNING,
        tags=["api"],
        estimated_minutes=5,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    second_task = Task(
        user_id=user.id,
        title="任务二",
        type=TaskType.PLANNING,
        tags=["api"],
        estimated_minutes=5,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(first_task)
    db_session.add(second_task)
    await db_session.commit()
    await db_session.refresh(first_task)
    await db_session.refresh(second_task)

    active_intent = ExecutionIntent(
        plan_id=None,
        task_id=first_task.id,
        user_id=user.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="任务一",
        instructions=[],
        target_env=ExecutionTargetEnv.API,
        policy={},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.RUNNING,
        trust_level=TrustLevel.RAW,
        idempotency_key="phase4-concurrency-running",
    )
    db_session.add(active_intent)
    await db_session.commit()

    service = ExecutionService(db=db_session)
    queued_intent = await service.handoff_to_openclaw(
        task_id=second_task.id,
        user_id=user.id,
    )

    assert queued_intent.status == ExecutionIntentStatus.QUEUED
    assert queued_intent.error_category == "concurrency_limited"
    assert "第 1 位" in str(queued_intent.error_message or "")
    assert queued_intent.policy["queue_state"]["position"] == 1


@pytest.mark.asyncio
async def test_dispatch_blocks_when_token_budget_is_exhausted(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    async def _execute(self, request_body, *, timeout_seconds=None):
        raise AssertionError("execute should not run when token budget is exhausted")

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(
        username="phase4budget",
        email="phase4budget@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    await ExecutionPreferenceService(db_session).save_preferences(
        user_id=user.id,
        payload={
            "execution_budget": {
                "daily_token_limit": 100,
                "daily_used": 100,
            }
        },
    )

    task = Task(
        user_id=user.id,
        title="预算受限任务",
        type=TaskType.PLANNING,
        tags=["browser"],
        estimated_minutes=5,
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
    )

    assert intent.status == ExecutionIntentStatus.FAILED
    assert intent.error_category == "daily_token_limit_exceeded"
    assert "预算已用完" in str(intent.error_message or "")


@pytest.mark.asyncio
async def test_record_token_usage_updates_execution_budget(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
) -> None:
    user = User(
        username="phase4budgetusage",
        email="phase4budgetusage@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    preference_service = ExecutionPreferenceService(db_session)
    await preference_service.save_preferences(
        user_id=user.id,
        payload={
            "execution_budget": {
                "daily_token_limit": 500,
                "monthly_token_limit": 5000,
            }
        },
    )

    payload = await preference_service.record_token_usage(
        user_id=user.id,
        token_usage={"total_tokens": 123},
    )

    assert payload["execution_budget"]["daily_used"] == 123
    assert payload["execution_budget"]["monthly_used"] == 123


@pytest.mark.asyncio
async def test_cancel_promotes_next_queued_intent(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    from app.config import settings

    settings.OPENCLAW_MAX_CONCURRENT_RUNS = 1

    async def _execute(self, request_body, *, timeout_seconds=None):
        return {
            "id": "resp-promoted-1",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"queued task finished"}',
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(
        username="phase4queuepromote",
        email="phase4queuepromote@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    first_task = Task(
        user_id=user.id,
        title="任务一",
        type=TaskType.PLANNING,
        tags=["api"],
        estimated_minutes=5,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    second_task = Task(
        user_id=user.id,
        title="任务二",
        type=TaskType.PLANNING,
        tags=["api"],
        estimated_minutes=5,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(first_task)
    db_session.add(second_task)
    await db_session.commit()
    await db_session.refresh(first_task)
    await db_session.refresh(second_task)

    active_intent = ExecutionIntent(
        plan_id=None,
        task_id=first_task.id,
        user_id=user.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="任务一",
        instructions=[],
        target_env=ExecutionTargetEnv.API,
        policy={},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.RUNNING,
        trust_level=TrustLevel.RAW,
        idempotency_key="phase4-queue-active",
    )
    db_session.add(active_intent)
    await db_session.commit()

    service = ExecutionService(db=db_session)
    queued_intent = await service.handoff_to_openclaw(
        task_id=second_task.id,
        user_id=user.id,
    )
    assert queued_intent.status == ExecutionIntentStatus.QUEUED

    await service.cancel(intent_id=active_intent.id, user_id=user.id)

    promoted = await service.get_intent(intent_id=queued_intent.id, user_id=user.id)
    assert promoted.status == ExecutionIntentStatus.SUCCEEDED
    assert promoted.error_category is None


@pytest.mark.asyncio
async def test_dispatch_and_cancel_write_execution_audit_logs(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    async def _execute(self, request_body, *, timeout_seconds=None):
        return {
            "id": "resp-audit-phase4",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": '{"summary":"done"}'},
                    ],
                }
            ],
        }

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(
        username="phase4audit",
        email="phase4audit@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="执行一次 API 调用并返回摘要",
        type=TaskType.PLANNING,
        tags=["api"],
        estimated_minutes=5,
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
    )

    running_task = Task(
        user_id=user.id,
        title="另一个任务",
        type=TaskType.PLANNING,
        tags=["api"],
        estimated_minutes=5,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(running_task)
    await db_session.commit()
    await db_session.refresh(running_task)

    active_intent = ExecutionIntent(
        plan_id=None,
        task_id=running_task.id,
        user_id=user.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="另一个任务",
        instructions=[],
        target_env=ExecutionTargetEnv.API,
        policy={},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.RUNNING,
        trust_level=TrustLevel.RAW,
        idempotency_key="phase4-audit-cancel",
    )
    db_session.add(active_intent)
    await db_session.commit()

    await service.cancel(intent_id=active_intent.id, user_id=user.id)

    result = await db_session.execute(
        select(ExecutionAuditLog)
        .where(ExecutionAuditLog.user_id == user.id)
        .order_by(ExecutionAuditLog.created_at)
    )
    logs = list(result.scalars().all())

    assert any(log.intent_id == intent.id and log.action == "dispatch" for log in logs)
    assert any(log.intent_id == active_intent.id and log.action == "cancel" for log in logs)


@pytest.mark.asyncio
async def test_retry_intent_reuses_previous_task_parameters(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    user = User(username="retryuser", email="retry@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="检查仓库状态",
        type=TaskType.PLANNING,
        tags=["shell"],
        estimated_minutes=5,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    previous_intent = ExecutionIntent(
        task_id=task.id,
        user_id=user.id,
        plan_id=None,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="在终端运行 git status",
        instructions=["Use the project terminal"],
        target_env=ExecutionTargetEnv.SHELL,
        policy={"template_metadata": {"template_id": "shell_diagnostics"}},
        success_criteria={"type": "non_empty"},
        result_contract={},
        timeout_seconds=60,
        status=ExecutionIntentStatus.FAILED,
        trust_level=TrustLevel.RAW,
        idempotency_key="retry-source",
        error_category="timeout",
        error_message="timeout",
    )
    db_session.add(previous_intent)
    await db_session.commit()
    await db_session.refresh(previous_intent)

    async def _fake_handoff(self, **kwargs):
        retried = ExecutionIntent(
            task_id=task.id,
            user_id=user.id,
            plan_id=None,
            execution_mode=ExecutionMode.AGENT,
            executor=ExecutorType.OPENCLAW,
            goal=kwargs["goal"],
            instructions=kwargs["instructions"],
            target_env=ExecutionTargetEnv.SHELL,
            policy=kwargs["policy"],
            success_criteria=kwargs["success_criteria"],
            result_contract=kwargs["result_contract"],
            timeout_seconds=60,
            status=ExecutionIntentStatus.RUNNING,
            trust_level=TrustLevel.RAW,
            idempotency_key="retry-target",
        )
        self._db.add(retried)
        await self._db.commit()
        await self._db.refresh(retried)
        return retried

    monkeypatch.setattr(ExecutionService, "handoff_to_openclaw", _fake_handoff)

    service = ExecutionService(db=db_session)
    retried = await service.retry_intent(intent_id=previous_intent.id, user_id=user.id)

    assert retried.goal == "在终端运行 git status"
    assert retried.instructions == ["Use the project terminal"]
    assert retried.status == ExecutionIntentStatus.RUNNING


@pytest.mark.asyncio
async def test_dispatch_batch_returns_batch_summary(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    user = User(username="batchuser", email="batch@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task_a = Task(
        user_id=user.id,
        title="查网页资料",
        type=TaskType.PLANNING,
        tags=["browser"],
        estimated_minutes=5,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    task_b = Task(
        user_id=user.id,
        title="运行终端检查",
        type=TaskType.PLANNING,
        tags=["shell"],
        estimated_minutes=5,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add_all([task_a, task_b])
    await db_session.commit()
    await db_session.refresh(task_a)
    await db_session.refresh(task_b)

    intent_a = ExecutionIntent(
        task_id=task_a.id,
        user_id=user.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="搜索文档",
        instructions=[],
        target_env=ExecutionTargetEnv.BROWSER,
        policy={},
        success_criteria={},
        result_contract={},
        timeout_seconds=60,
        status=ExecutionIntentStatus.READY,
        trust_level=TrustLevel.RAW,
        idempotency_key="batch-a",
    )
    intent_b = ExecutionIntent(
        task_id=task_b.id,
        user_id=user.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="运行命令",
        instructions=[],
        target_env=ExecutionTargetEnv.SHELL,
        policy={},
        success_criteria={},
        result_contract={},
        timeout_seconds=60,
        status=ExecutionIntentStatus.READY,
        trust_level=TrustLevel.RAW,
        idempotency_key="batch-b",
    )
    db_session.add_all([intent_a, intent_b])
    await db_session.commit()
    await db_session.refresh(intent_a)
    await db_session.refresh(intent_b)

    async def _fake_dispatch(self, *, intent_id, user_id):  # noqa: ARG001
        intent = await self._get_user_intent(intent_id=intent_id, user_id=user.id)
        intent.status = (
            ExecutionIntentStatus.SUCCEEDED
            if intent.id == intent_a.id
            else ExecutionIntentStatus.QUEUED
        )
        return intent

    monkeypatch.setattr(ExecutionService, "dispatch", _fake_dispatch)

    payload = await ExecutionService(db=db_session).dispatch_batch(
        intent_ids=[intent_a.id, intent_b.id],
        user_id=user.id,
        execution_strategy="sequential",
    )

    assert payload["resolved_strategy"] == "sequential"
    assert payload["completed_count"] == 1
    assert payload["queued_count"] == 1


@pytest.mark.asyncio
async def test_schedule_service_creates_and_ticks_cron_schedule(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    user = User(username="scheduser", email="sched@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="每天检查 GitHub 通知",
        type=TaskType.PLANNING,
        tags=["browser"],
        estimated_minutes=5,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    async def _fake_handoff(self, **kwargs):  # noqa: ARG001
        intent = ExecutionIntent(
            task_id=task.id,
            user_id=user.id,
            execution_mode=ExecutionMode.AGENT,
            executor=ExecutorType.OPENCLAW,
            goal="检查 GitHub 通知",
            instructions=[],
            target_env=ExecutionTargetEnv.BROWSER,
            policy={},
            success_criteria={},
            result_contract={},
            timeout_seconds=60,
            status=ExecutionIntentStatus.SUCCEEDED,
            trust_level=TrustLevel.RAW,
            idempotency_key="schedule-run",
        )
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        return intent

    monkeypatch.setattr(ExecutionService, "handoff_to_openclaw", _fake_handoff)

    schedule_service = ExecutionScheduleService(db_session)
    schedule = await schedule_service.create_schedule(
        user_id=user.id,
        task_id=task.id,
        intent_template={"goal": "检查 GitHub 通知"},
        trigger_type=ExecutionScheduleTriggerType.CRON.value,
        trigger_config={"cron": "0 8 * * *"},
    )

    assert schedule.next_run_at is not None

    tick_result = await schedule_service.tick_due_schedules(now=schedule.next_run_at)

    assert tick_result["dispatched_count"] == 1
    refreshed = await schedule_service._get_user_schedule(schedule_id=schedule.id, user_id=user.id)
    assert refreshed.last_run_at is not None


@pytest.mark.asyncio
async def test_handoff_chat_control_creates_hidden_task_and_stable_session_key(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    from app.config import settings

    settings.OPENCLAW_TRANSPORT = "gateway_ws"
    settings.OPENCLAW_DEFAULT_WORKDIR = "/tmp/sparkle-demo"

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

    async def _execute(self, request_body, *, timeout_seconds=None, event_callback=None):
        return {
            "id": "resp_chat_control_1",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"workspace clean"}',
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.list_nodes", _list_nodes)
    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(
        username="phase4chatcontrol",
        email="phase4chatcontrol@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = ExecutionService(db=db_session)
    intent, record = await service.handoff_chat_control(
        session_id="chat-session-1",
        user_id=user.id,
        message="在我的电脑上运行 git status",
        request_id="chat-req-1",
    )

    hidden_task = await db_session.get(Task, intent.task_id)

    assert hidden_task is not None
    assert hidden_task.deleted_at is not None
    assert intent.status == ExecutionIntentStatus.SUCCEEDED
    assert intent.error_message is None
    assert intent.policy["session_key"] == f"sparkle:chat:default:{user.id}:chat-session-1"
    assert intent.policy["working_directory"] == "/tmp/sparkle-demo"
    assert intent.policy["chat_control"] is True
    assert record is not None
    assert record.parsed_output == {"summary": "workspace clean"}
    assert record.error_message is None


@pytest.mark.asyncio
async def test_handoff_surfaces_pairing_required_when_node_discovery_fails(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    async def _list_nodes(self, *, connected_only=True, last_connected=None):
        raise OpenClawError("pairing required")

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.list_nodes", _list_nodes)

    user = User(username="phase4pairing", email="phase4pairing@example.com", hashed_password="hashed", photon_balance=0)
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
    with pytest.raises(ValueError, match="pairing required"):
        await service.handoff_to_openclaw(
            task_id=task.id,
            user_id=user.id,
            template_id="shell_diagnostics",
        )


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


@pytest.mark.asyncio
async def test_consecutive_failures_trigger_degraded_manual_mode(
    db_session,
    openclaw_settings,
    mute_execution_side_effects,
    monkeypatch,
) -> None:
    async def _execute(self, request_body, *, timeout_seconds=None, event_callback=None):
        raise OpenClawError("openclaw unavailable")

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.execute", _execute)

    user = User(
        username="phase4degraded",
        email="phase4degraded@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = ExecutionService(db=db_session)
    ExecutionService._failure_counts.clear()
    ExecutionService._degraded_users.clear()

    for index in range(3):
        task = Task(
            user_id=user.id,
            title=f"调研任务 {index}",
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

        intent = await service.handoff_to_openclaw(
            task_id=task.id,
            user_id=user.id,
            template_id="web_research_brief",
        )
        assert intent.status == ExecutionIntentStatus.FAILED

    snapshot = service.get_degradation_snapshot()
    assert snapshot["degraded_user_count"] == 1
    assert snapshot["failure_counts"][str(user.id)] >= 3

    blocked_task = Task(
        user_id=user.id,
        title="第 4 个任务",
        type=TaskType.OCR,
        tags=["research"],
        estimated_minutes=20,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(blocked_task)
    await db_session.commit()
    await db_session.refresh(blocked_task)

    decision = await service.classify_task(task_id=blocked_task.id, user_id=user.id)
    assert decision.execution_mode == ExecutionMode.HUMAN
    with pytest.raises(ValueError, match="temporarily degraded"):
        await service.create_intent(task_id=blocked_task.id, user_id=user.id)
