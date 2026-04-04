from __future__ import annotations

import json

import pytest

from app.orchestration.companion_constitution import COMPANION_CONSTITUTION
from app.orchestration.companion_identity_kernel import SPARKLE_IDENTITY_KERNEL
from app.orchestration.soul_compiler import (
    DEFAULT_COMPANION_STATE,
    SoulCompiler,
    attach_shadow_soul_runtime,
)
from app.orchestration.statechart_engine import WorkflowState


class _AsyncRedisStub:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = payload

    async def get(self, key: str) -> str | None:
        return self.payload.get(key)


def test_soul_compiler_with_minimal_payload_uses_defaults() -> None:
    compiler = SoulCompiler()

    result = compiler.compile(
        user_context={},
        plan_context=None,
        visible_intelligence_context=None,
        dual_core_snapshot=None,
    )

    assert "user flourishing" in result.constitutional_summary
    assert "growth companion" in result.identity_summary
    assert "Balance attunement and execution" in result.companion_stance
    assert result.relationship_context
    assert len(result.no_drift_flags) >= 5
    assert result.evidence_trace["companion_state"]["values"] == DEFAULT_COMPANION_STATE.to_dict()
    assert COMPANION_CONSTITUTION.user_centered_telos in result.constitutional_summary
    assert SPARKLE_IDENTITY_KERNEL.essence in result.identity_summary


def test_soul_compiler_with_rich_payload_captures_visible_and_dual_core_context() -> None:
    compiler = SoulCompiler()

    result = compiler.compile(
        user_context={
            "current_query": "帮我整理今天的复习计划",
            "preferences": {"depth_preference": 0.8},
        },
        plan_context={
            "plan_title": "期中冲刺",
            "constraints": {"time_budget_minutes": 90},
        },
        visible_intelligence_context={
            "proactive_opening_message": "你这两天已经开始稳住节奏了。",
            "pending_observation": "这次调整之后你的压力是不是小了一点？",
            "post_adaptation_question": "",
            "evolution_highlights": ["我把更难的内容往后放了一点。"],
        },
        dual_core_snapshot={
            "source": "state_context",
            "mode": "cognitive_first",
            "reason": "用户当前阻力较高，需要先处理摩擦。",
            "timestamp": "2026-04-04T08:00:00",
        },
    )

    assert "naming the user's friction" in result.companion_stance
    assert "你这两天已经开始稳住节奏了" in result.relationship_context
    assert result.evidence_trace["dual_core"]["mode"] == "cognitive_first"
    assert result.evidence_trace["plan_context"]["active_plan"] == "期中冲刺"


@pytest.mark.asyncio
async def test_attach_shadow_soul_runtime_writes_context_data() -> None:
    state = WorkflowState(context_data={"visible_update_context": {"proactive_opening_message": "最近这一步走稳了。"}})
    redis = _AsyncRedisStub(
        {
            "user:routing:last_dual_core:user-1": json.dumps(
                {
                    "mode": "execution_first",
                    "reason": "任务导向问题优先直答。",
                    "timestamp": "2026-04-04T09:30:00",
                },
                ensure_ascii=False,
            )
        }
    )

    payload = await attach_shadow_soul_runtime(
        target_context=state.context_data,
        redis_client=redis,
        user_id="user-1",
        user_context={"preferences": {"verbosity_target": "concise"}},
        plan_context={"goal": "完成数学复习"},
    )

    assert payload.context.evidence_trace["dual_core"]["source"] == "redis_snapshot"
    assert "soul_runtime_context" in state.context_data
    assert "soul_runtime_debug" in state.context_data
    assert state.context_data["soul_runtime_context"]["relationship_context"]


def test_soul_compiler_summaries_are_derived_from_artifacts() -> None:
    compiler = SoulCompiler()

    result = compiler.compile(
        user_context={},
        plan_context={},
        visible_intelligence_context={},
        dual_core_snapshot={},
    )

    first_constitution_title = COMPANION_CONSTITUTION.non_negotiables[0].title
    first_identity_facet = SPARKLE_IDENTITY_KERNEL.core_facets[0].summary
    assert COMPANION_CONSTITUTION.user_centered_telos in result.constitutional_summary
    assert first_constitution_title in result.constitutional_summary
    assert SPARKLE_IDENTITY_KERNEL.essence in result.identity_summary
    assert first_identity_facet in result.identity_summary


def test_soul_compiler_preserves_zero_value_calibrations() -> None:
    compiler = SoulCompiler()

    result = compiler.compile(
        user_context={},
        plan_context={},
        visible_intelligence_context={},
        dual_core_snapshot={"mode": "balanced"},
        effective_companion_state={
            "warmth_calibration": 0.0,
            "candor_calibration": 0.0,
            "emotional_explicitness": 0.0,
            "challenge_style": "gentle",
            "preferred_truth_style": "direct_structured",
        },
    )

    assert "Warmth stays around 0.00." in result.companion_stance
    assert "Candor stays around 0.00." in result.companion_stance
    assert "Prefer direct, structured truth over affective padding." in result.companion_stance
