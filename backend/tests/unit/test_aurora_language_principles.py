from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.aurora.core_session import AuroraCoreSessionService
from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.control_surface import AuroraHardBounds
from app.aurora.runtime_v1.dashboard import DashboardReadout
from app.aurora.runtime_v1.decision_loop import AuroraDecision
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.skills import AuroraSkillRegistry
from app.orchestration.aurora_language_principles import (
    AURORA_LANGUAGE_PRINCIPLES,
    FORBIDDEN_EXPRESSIONS,
    assert_aurora_language_text,
    get_aurora_language_profile,
    render_aurora_language_contract,
    validate_aurora_language_text,
)
from app.orchestration.prompts import build_system_prompt
from app.services.checkpoint_nudge_service import CheckpointNudgeService
from app.services.push_policy_compiler import PushPolicyCompiler
from app.signals.aurora_core_session import AuroraCoreSessionEntryReason


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def setex(self, key: str, _ttl: int, value: str) -> bool:
        self.data[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def delete(self, key: str) -> int:
        self.data.pop(key, None)
        return 1


def _readout(*, surface: str = "aurora_modeling") -> DashboardReadout:
    return DashboardReadout(
        surface=surface,
        user_id="user-1",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="我今天学不进去了。",
        activity_profile={
            "conversation_style": "warm",
            "expression": {
                "tone_warmth": 0.78,
                "directness": 0.32,
                "brevity": 0.44,
                "friendliness": 0.82,
                "challenge_intensity": 0.28,
            },
        },
        hard_bounds=AuroraHardBounds(),
        candidate_affordances=AuroraSkillRegistry().load_candidate_affordances("aurora_modeling"),
        cold_start_context={"goal_type": "exam"},
        covered_domains=["goal"],
        missing_domains=["scope"],
        task_state={"stage": "triage"},
        checkpoint_state={"status": "behind", "specific_lagging_domain": "TCP 状态转换"},
    )


def test_language_contract_defines_principles_examples_and_blacklist() -> None:
    assert len(AURORA_LANGUAGE_PRINCIPLES) >= 7
    assert all(item.positive_example and item.negative_example for item in AURORA_LANGUAGE_PRINCIPLES)
    assert len(FORBIDDEN_EXPRESSIONS) >= 5

    contract = render_aurora_language_contract("core_session", include_examples=True)

    assert "Aurora 语言契约" in contract
    assert "真实观察、可纠正判断、低成本下一步" in contract
    assert "Core Session" in contract
    assert "我相信你" in contract
    assert "你又失败了" in contract


def test_system_prompt_uses_shared_language_contract() -> None:
    prompt = build_system_prompt(
        user_context={"preferences": {"depth_preference": 0.5}},
        conversation_history={"messages": []},
        chat_mode="standard",
    )

    assert "## Aurora 语言契约 [L1 表达护栏]" in prompt
    assert "每次 Aurora 介入都必须尽量包含" in prompt
    assert "禁用表达黑名单" in prompt
    assert "如果这些原则与局部 tone 指令冲突" in prompt


def test_runtime_chat_adapter_prompt_uses_checkpoint_profile() -> None:
    prompt = ChatLayerAdapter()._build_prompt(AuroraDecision(action="emit_message"), _readout(surface="aurora_checkpoint"))
    system = prompt[0]["content"]

    assert "Aurora 语言契约" in system
    assert "checkpoint 复盘" in system
    assert "问一个会改变下一步的问题" in system


@pytest.mark.asyncio
async def test_chat_fallback_copy_matches_language_contract() -> None:
    decision = AuroraDecision(
        action="emit_message",
        chat_directive={"standard_layer_contract": {"response_type": "emotional_support"}},
    )
    messages = await ChatLayerAdapter()._fallback_messages(decision, _readout())

    assert messages
    for message in messages:
        assert_aurora_language_text(message)
    assert any("下一步" in message or "发我" in message for message in messages)


def test_checkpoint_opening_copy_matches_language_contract() -> None:
    service = CheckpointNudgeService(db=None, redis=None)  # type: ignore[arg-type]
    opening, variant = service._checkpoint_opening(
        plan=SimpleNamespace(name="计网 7 天冲刺"),
        checkpoint_day=3,
        checkpoint_description="中段检查点",
        previous_summary="上次还没闭合的是 TCP 状态转换",
        open_threads=[],
        unclosed_questions=[],
        progress_facts=["完成了 3/8 个任务", "最需要留意的是「TCP」"],
        previous_openings=[],
    )

    assert variant
    assert "完成了 3/8 个任务" in opening
    assert_aurora_language_text(opening)


@pytest.mark.asyncio
async def test_core_session_opening_copy_matches_language_contract() -> None:
    service = AuroraCoreSessionService(FakeRedis())
    session = await service.start_session(
        user_id="u1",
        conversation_id="c1",
        entry_reason=AuroraCoreSessionEntryReason(
            trigger_source="status_bar",
            observed_signals=["两张任务卡都超时", "计划偏离目标"],
            suggested_agenda_preview=["确认观察", "校准策略"],
            why_now="继续推进前需要先校准任务颗粒度",
            estimated_minutes=4,
        ),
    )

    opening = session.messages[0].content
    assert "我注意到" in opening
    assert "这大概需要 4 分钟" in opening
    assert_aurora_language_text(opening)


def test_daily_startup_copy_matches_language_contract() -> None:
    service = AuroraRuntimeV1Service()
    message = service._daily_startup_message(
        plan=SimpleNamespace(subject="计算机网络", name="计网冲刺"),
        day_index=2,
        today_focus="TCP 流量控制",
        estimated_minutes=45,
        completion_rate=0.9,
        adjustment_reason="",
    )

    assert "推进很顺利" in message
    assert "做得很好" not in message
    assert_aurora_language_text(message)


def test_push_templates_match_language_contract() -> None:
    compiler = PushPolicyCompiler()
    rendered_templates = []
    for template in compiler.templates.values():
        title = str(template["title"])
        body = str(template["body"]).replace("{due_label}", "今天 18:00").replace("{streak_days}", "4")
        rendered_templates.append(f"{title} {body}")

    assert rendered_templates
    for text in rendered_templates:
        assert_aurora_language_text(text)


def test_language_validator_catches_forbidden_copy_and_internal_tokens() -> None:
    bad_text = "你真棒，我相信你一定能成功。risk_found runtime policy 已触发。"
    violations = validate_aurora_language_text(bad_text)

    assert "forbidden:blind_cheerleading" in violations
    assert "forbidden:empty_praise" in violations
    assert any(item.startswith("internal_token:") for item in violations)


def test_ux_language_profile_is_parameterized_by_scenario() -> None:
    profile = get_aurora_language_profile("push")

    assert profile["scenario"] == "push"
    assert "克制" in profile["degree"]
    assert "2-5 分钟" in profile["next_step_shape"]
