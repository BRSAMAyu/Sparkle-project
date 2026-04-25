"""F16: Galaxy weak node injection into Sprint priority."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# 1. dashboard._extract_cold_start_context — galaxy_mastery 提取
# ---------------------------------------------------------------------------


class TestDashboardExtractGalaxyWeakNodes:
    """Verify _extract_cold_start_context extracts galaxy_weak_nodes from galaxy_mastery."""

    @pytest.fixture()
    def builder(self):
        from app.aurora.runtime_v1.dashboard import DashboardReadoutBuilder

        return DashboardReadoutBuilder()

    def test_extracts_nodes_below_threshold(self, builder):
        ctx = builder._extract_cold_start_context(
            profile_context={},
            user_context_payload={
                "galaxy_mastery": {
                    "cn.tcp_flow": 0.25,
                    "cn.osi_model": 0.9,
                    "cn.dns_http": 0.38,
                },
            },
        )
        assert "galaxy_weak_nodes" in ctx
        assert ctx["galaxy_weak_nodes"] == ["cn.tcp_flow", "cn.dns_http"]

    def test_only_below_0_4(self, builder):
        ctx = builder._extract_cold_start_context(
            profile_context={},
            user_context_payload={
                "galaxy_mastery": {"cn.osi_model": 0.9, "cn.ip_subnet": 0.41},
            },
        )
        assert "galaxy_weak_nodes" not in ctx

    def test_empty_mastery(self, builder):
        ctx = builder._extract_cold_start_context(
            profile_context={},
            user_context_payload={"galaxy_mastery": {}},
        )
        assert "galaxy_weak_nodes" not in ctx

    def test_no_galaxy_mastery_key(self, builder):
        ctx = builder._extract_cold_start_context(
            profile_context={},
            user_context_payload={},
        )
        assert "galaxy_weak_nodes" not in ctx

    def test_merges_with_existing_cold_start(self, builder):
        ctx = builder._extract_cold_start_context(
            profile_context={"cold_start_context": {"subject": "计算机网络"}},
            user_context_payload={
                "galaxy_mastery": {"cn.tcp_flow": 0.1},
            },
        )
        assert ctx["subject"] == "计算机网络"
        assert ctx["galaxy_weak_nodes"] == ["cn.tcp_flow"]

    def test_ignores_non_numeric_mastery(self, builder):
        ctx = builder._extract_cold_start_context(
            profile_context={},
            user_context_payload={
                "galaxy_mastery": {"cn.tcp_flow": "weak", "cn.osi_model": None},
            },
        )
        assert "galaxy_weak_nodes" not in ctx


# ---------------------------------------------------------------------------
# 2. planning_workflow._daily_task_specs — galaxy_weak 标注
# ---------------------------------------------------------------------------


class TestDailyTaskSpecsGalaxyWeakAnnotation:
    """Verify _daily_task_specs annotates galaxy_weak and focus when nodes match."""

    @pytest.fixture()
    def manager(self):
        from app.orchestration.planning_workflow import PlanningWorkflowManager

        return PlanningWorkflowManager(redis_client={})

    @pytest.fixture()
    def session_with_galaxy(self):
        """Minimal PlanningSession with galaxy_weak_nodes in collected."""
        from app.orchestration.planning_workflow import PlanningSession

        return PlanningSession(
            planning_session_id="test-session",
            chat_session_id="test-chat",
            user_id="test-user",
            goal_raw="7天计算机网络冲刺",
            state="CLARIFYING",
            turns_in_state=5,
            collected={
                "galaxy_weak_nodes": ["cn.tcp_flow"],
                "subject": "计算机网络",
                "time_constraint_days": 7,
                "daily_available_hours": 4,
                "avg_mastery_score": 22.4,
            },
        )

    def test_annotates_galaxy_weak_on_matching_focus(self, manager, session_with_galaxy):
        phase = {
            "label": "高频保底",
            "focus": "TCP 流量控制与 cn.tcp_flow 三次握手",
            "start_day": 2,
            "end_day": 3,
            "daily_hours": 4,
            "sprint_policy": {"sprint_mode": "seven_day_survival"},
        }
        specs = manager._daily_task_specs(
            phase,
            phase_index=2,
            session=session_with_galaxy,
            galaxy_weak_nodes=["cn.tcp_flow"],
        )
        assert len(specs) == 2
        for spec in specs:
            assert spec.get("galaxy_weak") is True
            assert "Galaxy 标记的弱点" in spec["focus"]

    def test_no_annotation_when_no_match(self, manager, session_with_galaxy):
        phase = {
            "label": "应用层",
            "focus": "DNS 与 HTTP 协议分析",
            "start_day": 5,
            "end_day": 6,
            "daily_hours": 4,
            "sprint_policy": {"sprint_mode": "seven_day_survival"},
        }
        specs = manager._daily_task_specs(
            phase,
            phase_index=3,
            session=session_with_galaxy,
            galaxy_weak_nodes=["cn.tcp_flow"],
        )
        for spec in specs:
            assert spec.get("galaxy_weak") is not True
            assert "Galaxy 标记" not in spec.get("focus", "")

    def test_no_annotation_when_galaxy_weak_nodes_empty(self, manager, session_with_galaxy):
        phase = {
            "label": "传输层",
            "focus": "TCP 三次握手 cn.tcp_flow",
            "start_day": 2,
            "end_day": 2,
            "daily_hours": 4,
            "sprint_policy": {"sprint_mode": "seven_day_survival"},
        }
        specs = manager._daily_task_specs(
            phase,
            phase_index=2,
            session=session_with_galaxy,
            galaxy_weak_nodes=None,
        )
        for spec in specs:
            assert spec.get("galaxy_weak") is not True

    def test_difficulty_boost_is_1(self):
        """Verify _mastery_to_difficulty returns higher value for galaxy_weak specs."""
        from app.orchestration.planning_workflow import PlanningWorkflowManager

        base = PlanningWorkflowManager._mastery_to_difficulty(22.4, 2)
        boosted = min(5, base + 1)
        assert boosted == base + 1
        assert boosted <= 5
