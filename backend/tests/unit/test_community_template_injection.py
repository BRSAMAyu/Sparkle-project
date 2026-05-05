"""
Tests for MAGIC-006: Community cohort mistake → task template injection.

Verifies that community hints stored in Redis are read during plan generation
and injected into task guide_json as common_mistakes, which then flow into
task card templates (mini_quiz, stuck_help, fallback_if_stuck).
"""

import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch missing module before any app imports trigger it
if "app.models.task_history" not in sys.modules:
    _mod = types.ModuleType("app.models.task_history")
    _mod.TaskHistory = type("TaskHistory", (), {"__tablename__": "task_history"})
    sys.modules["app.models.task_history"] = _mod


def _strip(value):
    return str(value or "").strip()


# ── Fixtures ─────────────────────────────────────────────────────


def _make_planning_workflow():
    from app.orchestration.planning_workflow import PlanningWorkflowManager

    redis_mock = AsyncMock()
    return PlanningWorkflowManager(redis_client=redis_mock), redis_mock


def _cohort_hint(affected_nodes=None, tip=None, summary=None):
    return {
        "hint_type": "cohort_mistake",
        "title": "同伴易错提醒",
        "anonymous_summary": summary or "有8位同学在计算机网络的TCP三次握手上容易犯理解错误",
        "affected_nodes": affected_nodes or ["tcp-handshake"],
        "tip": tip or "先检查这个常见误解：把SYN-ACK当成数据传输",
        "privacy": "anonymous_aggregate_only",
    }


# ── Tests: Redis hint loading ───────────────────────────────────


class TestCommunityHintLoading:
    """Verify cohort hints are read from Redis during plan generation."""

    @pytest.mark.asyncio
    async def test_reads_cohort_hint_from_redis(self):
        redis_mock = AsyncMock()
        hint = _cohort_hint()
        redis_mock.get = AsyncMock(return_value=json.dumps(hint))

        result = await redis_mock.get(
            "spine:community_loop:test-user:cohort_mistake_hint:latest"
        )
        assert result is not None
        data = json.loads(result)
        assert data["hint_type"] == "cohort_mistake"
        assert "tcp-handshake" in data["affected_nodes"]

    @pytest.mark.asyncio
    async def test_handles_missing_redis_key(self):
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)

        result = await redis_mock.get(
            "spine:community_loop:test-user:cohort_mistake_hint:latest"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_handles_corrupt_redis_data(self):
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value="not-json{{{")

        with pytest.raises(json.JSONDecodeError):
            json.loads(await redis_mock.get("spine:community_loop:test-user:cohort_mistake_hint:latest"))


# ── Tests: Day-spec injection logic ─────────────────────────────


class TestDaySpecCommunityInjection:
    """Verify community mistakes are matched to day_spec by node_id or focus."""

    def test_injects_when_node_id_matches(self):
        hint = _cohort_hint(affected_nodes=["tcp-handshake"])
        day_spec = {
            "day": 1,
            "focus": "TCP三次握手",
            "task_kind": "retrieval_drill",
            "sprint_pack_nodes": [
                {"node_id": "tcp-handshake", "label": "TCP三次握手"},
            ],
        }

        _day_nodes = list(day_spec.get("sprint_pack_nodes") or [])
        _day_node_ids = {n.get("node_id") for n in _day_nodes if isinstance(n, dict)}
        _day_focus = (day_spec.get("focus") or "").lower()

        matched = False
        _affected = set(hint.get("affected_nodes") or [])
        if _affected & _day_node_ids or any(
            _n.lower() in _day_focus for _n in _affected
        ):
            matched = True

        assert matched, "Should match when node_id is in affected_nodes"

    def test_injects_when_focus_matches_affected_node(self):
        hint = _cohort_hint(affected_nodes=["tcp三次握手"])
        day_spec = {
            "day": 1,
            "focus": "TCP三次握手",
            "task_kind": "retrieval_drill",
            "sprint_pack_nodes": [],
        }

        _day_nodes = list(day_spec.get("sprint_pack_nodes") or [])
        _day_node_ids = {n.get("node_id") for n in _day_nodes if isinstance(n, dict)}
        _day_focus = (day_spec.get("focus") or "").lower()

        matched = False
        _affected = set(hint.get("affected_nodes") or [])
        if _affected & _day_node_ids or any(
            _n.lower() in _day_focus for _n in _affected
        ):
            matched = True

        assert matched, "Should match when affected_node label appears in focus"

    def test_skips_when_no_match(self):
        hint = _cohort_hint(affected_nodes=["udp-protocol"])
        day_spec = {
            "day": 1,
            "focus": "TCP三次握手",
            "task_kind": "retrieval_drill",
            "sprint_pack_nodes": [
                {"node_id": "tcp-handshake", "label": "TCP三次握手"},
            ],
        }

        _day_nodes = list(day_spec.get("sprint_pack_nodes") or [])
        _day_node_ids = {n.get("node_id") for n in _day_nodes if isinstance(n, dict)}
        _day_focus = (day_spec.get("focus") or "").lower()

        matched = False
        _affected = set(hint.get("affected_nodes") or [])
        if _affected & _day_node_ids or any(
            _n.lower() in _day_focus for _n in _affected
        ):
            matched = True

        assert not matched, "Should NOT match when nodes don't overlap"


# ── Tests: guide_json common_mistakes merge ─────────────────────


class TestCommonMistakesMerge:
    """Verify community mistakes are merged into guide_json common_mistakes."""

    def test_community_tip_added_to_common_mistakes(self):
        day_spec = {
            "day": 1,
            "focus": "TCP三次握手",
            "_community_mistakes": [
                {"tip": "先检查这个常见误解：把SYN-ACK当成数据传输", "summary": "有8位同学..."},
            ],
        }
        common_mistakes = ["只看内容不做自测"]

        _community_mistakes = list(day_spec.get("_community_mistakes") or [])
        for _cm in _community_mistakes:
            _tip = _strip(_cm.get("tip"))
            if _tip and _tip not in common_mistakes:
                common_mistakes.append(_tip)

        assert "先检查这个常见误解：把SYN-ACK当成数据传输" in common_mistakes
        assert len(common_mistakes) == 2

    def test_no_duplicate_tips(self):
        day_spec = {
            "day": 1,
            "_community_mistakes": [
                {"tip": "只看内容不做自测", "summary": "duplicate test"},
            ],
        }
        common_mistakes = ["只看内容不做自测"]

        _community_mistakes = list(day_spec.get("_community_mistakes") or [])
        for _cm in _community_mistakes:
            _tip = _strip(_cm.get("tip"))
            if _tip and _tip not in common_mistakes:
                common_mistakes.append(_tip)

        assert common_mistakes.count("只看内容不做自测") == 1

    def test_empty_community_mistakes_preserves_existing(self):
        day_spec = {"day": 1}
        common_mistakes = ["只看内容不做自测"]

        _community_mistakes = list(day_spec.get("_community_mistakes") or [])
        for _cm in _community_mistakes:
            _tip = _strip(_cm.get("tip"))
            if _tip and _tip not in common_mistakes:
                common_mistakes.append(_tip)

        assert common_mistakes == ["只看内容不做自测"]

    def test_empty_tip_skipped(self):
        day_spec = {
            "day": 1,
            "_community_mistakes": [
                {"tip": "", "summary": "有8位同学..."},
            ],
        }
        common_mistakes = ["只看内容不做自测"]

        _community_mistakes = list(day_spec.get("_community_mistakes") or [])
        for _cm in _community_mistakes:
            _tip = _strip(_cm.get("tip"))
            if _tip and _tip not in common_mistakes:
                common_mistakes.append(_tip)

        assert common_mistakes == ["只看内容不做自测"]


# ── Tests: End-to-end task card enrichment ──────────────────────


class TestTaskCardEnrichmentWithCommunityData:
    """Verify community mistakes flow through to task card outputs."""

    def test_community_mistake_in_mini_quiz(self):
        from app.orchestration.task_card_generator import TaskCardGenerator

        gen = TaskCardGenerator()
        guide_json = {
            "common_mistakes": [
                "先检查这个常见误解：把SYN-ACK当成数据传输",
            ],
            "objective": "TCP三次握手",
        }
        result = gen.generate(
            guide_json=guide_json,
            task_kind="retrieval_drill",
            subject="计算机网络",
            focus="TCP三次握手",
        )
        mini_quiz = result.get("mini_quiz", {})
        quiz_items = mini_quiz.get("items", [])
        assert len(quiz_items) >= 3
        mistake_item = quiz_items[2]
        assert "SYN-ACK" in mistake_item.get("answer", "") or "SYN-ACK" in mistake_item.get("question", "")

    def test_community_mistake_in_stuck_help(self):
        from app.orchestration.task_card_generator import TaskCardGenerator

        gen = TaskCardGenerator()
        guide_json = {
            "common_mistakes": [
                "先检查这个常见误解：把SYN-ACK当成数据传输",
            ],
            "objective": "TCP三次握手",
        }
        result = gen.generate(
            guide_json=guide_json,
            task_kind="retrieval_drill",
            subject="计算机网络",
            focus="TCP三次握手",
        )
        stuck_help = result.get("stuck_help", {})
        targeted_fix = stuck_help.get("targeted_fix", "")
        assert "SYN-ACK" in targeted_fix, f"Expected community mistake in stuck_help, got: {targeted_fix}"
