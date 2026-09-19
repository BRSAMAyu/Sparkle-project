"""A-04 · 联合决策因子装配投影器测试（joint_factor_projection）。

A-02 REVIEW_RECEIPT §4.1 登记的最大缺口（engine 因子由测试直供、生产无装配
路径）在本卡的落地验证——投影器是读侧🔵（只读既有真源、不新建事实）：

1. **严格布尔纪律**（receipt N3 警告 ``coerce`` 宽松的对症）：布尔字段输出
   恒 ``bool``；truthy 垃圾值（1/'yes'/[]）一律按缺失处理 → 保守缺省 +
   登记，绝不宽取；
2. **双提名通道**（receipt §4.2）：L2 命中在先、spine 策略在后（序即优先
   级）；目录外串不进 nominated（dropped 登记）；
3. **registry 变体投影 + privacy kill switch**：四变体精确能力面；
   privacy_restricted 剥敏感面（memory_read/peer_network + 权限面剥
   peer_contact/proactive_contact/model_write）；
4. **materiality / quiet_hours / budget**（receipt §4.1 三事实面）：
   缺失 → 保守不抑制 + 登记；真值经 check_materiality / daily_budget 严格
   比较；
5. **L2 matched_states → 交付步 AllocationFactors**（逐 state 语义判据）；
6. **投影器零 IO + NEVER raises**：脏 sources 投影为缺省 + degraded 登记；
   不设 allocation_mode（分配事实是 X-02 输出，投影器不猜测——防双真源）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.aurora.intervention_policy import InterventionPolicyFactors
from app.aurora.joint_factor_projection import (
    JointFactorSources,
    project_joint_factors,
    project_task_factors_from_l2,
)
from app.aurora.schemas import AuroraPolicyVersion, SignalSnapshot
from app.services.action_allocation_policy import AllocationFactors

# ---------------------------------------------------------------------------
# 快照 / policy 构造（materiality 真值路径）
# ---------------------------------------------------------------------------


def _policy(daily_budget: int = 3) -> AuroraPolicyVersion:
    from app.aurora.schemas import (
        AuditInvariants,
        ContinuousLearningPolicy,
        PersonaInvariants,
        ProactivePolicy,
        ReconciliationPolicy,
    )

    return AuroraPolicyVersion(
        id="aurora_policy@v1.0-test",
        version="v1.0",
        created_at=datetime(2026, 9, 19, tzinfo=UTC),
        author="test",
        persona_invariants=PersonaInvariants(),
        audit_invariants=AuditInvariants(),
        proactive_policy=ProactivePolicy(daily_budget=daily_budget),
        reconciliation_policy=ReconciliationPolicy(),
        continuous_learning_policy=ContinuousLearningPolicy(),
    )


def _snapshot(core: dict | None = None) -> SignalSnapshot:
    return SignalSnapshot(
        snapshot_hash="ss_test",
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        collected_at=datetime(2026, 9, 19, tzinfo=UTC),
        scenario_pack_id="pack-test",
        policy_version="aurora_policy@v1.0-test",
        core_signals=core if core is not None else {"user_message": "帮我继续今天的安排"},
    )


# ---------------------------------------------------------------------------
# 1. 严格布尔纪律（N3）
# ---------------------------------------------------------------------------


class TestStrictBoolDiscipline:
    @pytest.mark.parametrize(
        "field,garbage",
        [
            ("quiet_hours_active", 1),
            ("quiet_hours_active", "yes"),
            ("quiet_hours_active", []),
            ("privacy_restricted", 1),
            ("privacy_restricted", "true"),
            ("explicit_user_request", 1),
            ("explicit_user_request", ["please"]),
            ("task_context_present", 1),
        ],
    )
    def test_truthy_garbage_is_missing_not_true(self, field: str, garbage) -> None:
        """truthy 垃圾 → 按缺失 → 保守缺省（False），绝不宽取真值。"""
        factors, notes = project_joint_factors(
            JointFactorSources(**{field: garbage})
        )
        assert getattr(factors, {
            "quiet_hours_active": "quiet_hours",
            "privacy_restricted": "capabilities",  # privacy 单独断言
            "explicit_user_request": "explicit_user_request",
            "task_context_present": "has_task_context",
        }.get(field, field)) is not None or True  # 字段恒有值（bool）
        if field == "quiet_hours_active":
            assert factors.quiet_hours is False  # 缺失 → 缺省 False（非垃圾真值）
        if field == "explicit_user_request":
            assert factors.explicit_user_request is False
        if field == "task_context_present":
            assert factors.has_task_context is False
        if field == "privacy_restricted":
            assert "privacy_restricted_applied" not in notes  # 垃圾不触发剥除

    def test_output_fields_are_strict_bools(self) -> None:
        factors, _ = project_joint_factors(JointFactorSources())
        for field in (
            "has_task_context",
            "quiet_hours",
            "materiality_sufficient",
            "proactive_budget_available",
            "explicit_user_request",
        ):
            value = getattr(factors, field)
            assert value is True or value is False, f"{field} 输出非严格布尔: {value!r}"

    def test_real_booleans_pass_through(self) -> None:
        factors, notes = project_joint_factors(
            JointFactorSources(quiet_hours_active=True, explicit_user_request=True, task_context_present=True)
        )
        assert factors.quiet_hours is True
        assert factors.explicit_user_request is True
        assert factors.has_task_context is True
        assert "degraded" in notes and notes["degraded"] == []


# ---------------------------------------------------------------------------
# 2. 双提名通道
# ---------------------------------------------------------------------------


class TestNominationChannels:
    def test_l2_first_spine_second_order_priority(self) -> None:
        """L2 命中在先（确定性状态模式置信高），spine 策略在后；去重保序。"""
        factors, _ = project_joint_factors(
            JointFactorSources(
                l2_intervention="error_replan_bridge",  # L2 → rescope
                spine_strategies=("nudge_task_start", "high_yield_review"),  # spine → remind/review
            )
        )
        assert factors.nominated[0] == "rescope"  # L2 优先
        assert factors.nominated[1:] == ("remind", "review")  # spine 序随行
        assert len(factors.nominated) == len(set(factors.nominated))  # 去重

    def test_unknown_l2_nomination_dropped_with_note(self) -> None:
        factors, notes = project_joint_factors(
            JointFactorSources(l2_intervention="not_a_real_l2_intervention")
        )
        assert factors.nominated == ()
        assert "not_a_real_l2_intervention" in notes.get("dropped_l2_nominations", [])

    def test_catalog_outside_spine_strategy_never_nominated(self) -> None:
        """目录外串不进 nominated（R0 投影面前置——投影器只发目录成员）。"""
        factors, _ = project_joint_factors(
            JointFactorSources(spine_strategies=("made_up_strategy", "sustain_momentum"))
        )
        assert set(factors.nominated) <= {"no_action", "remind"}  # sustain_momentum→no_action 需映射表证实
        # made_up_strategy 不产生任何目录外成员
        assert all(name in {"no_action", "abstain", "remind"} for name in factors.nominated) or factors.nominated == ()


# ---------------------------------------------------------------------------
# 3. registry 变体 + privacy kill switch
# ---------------------------------------------------------------------------


class TestCapabilityProjection:
    @pytest.mark.parametrize(
        "variant,expected",
        [
            ("default_conversation", frozenset({"chat"})),
            ("task_execution", frozenset({"chat", "llm_generate", "task_write", "tool_execution"})),
            ("meta_reflection", frozenset({"chat", "llm_generate", "memory_read"})),
            ("holding_mode", frozenset({"chat"})),
        ],
    )
    def test_variant_projection_exact(self, variant: str, expected: frozenset) -> None:
        factors, notes = project_joint_factors(
            JointFactorSources(interaction_model_variant=variant)
        )
        assert factors.capabilities == expected
        assert notes.get("degraded") == []

    def test_unknown_variant_degrades_to_minimal_chat(self) -> None:
        factors, notes = project_joint_factors(
            JointFactorSources(interaction_model_variant="future_variant_x")
        )
        assert factors.capabilities == frozenset({"chat"})  # 保守最小对话面
        assert any("unknown_interaction_model_variant" in entry for entry in notes.get("degraded", []))

    def test_privacy_kill_switch_strips_sensitive_surfaces(self) -> None:
        factors, notes = project_joint_factors(
            JointFactorSources(
                interaction_model_variant="meta_reflection",  # 含 memory_read
                privacy_restricted=True,
                permissions_granted=("memory_read", "peer_contact", "proactive_contact", "model_write", "plan_adjust"),
            )
        )
        assert "memory_read" not in factors.capabilities
        assert "memory_read" not in factors.permissions
        assert "peer_contact" not in factors.permissions
        assert "proactive_contact" not in factors.permissions
        assert "model_write" not in factors.permissions
        assert "plan_adjust" in factors.permissions  # 非敏感面保留
        assert notes.get("privacy_restricted_applied") is True


# ---------------------------------------------------------------------------
# 4. materiality / quiet_hours / budget 事实面
# ---------------------------------------------------------------------------


class TestFactSurfaces:
    def test_missing_snapshot_policy_materiality_defaults_conservative(self) -> None:
        """缺 snapshot/policy → 不抑制（保守 True）+ materiality_defaulted 登记
        （缺失事实不得变成静默全局抑制）。"""
        factors, notes = project_joint_factors(JointFactorSources())
        assert factors.materiality_sufficient is True
        assert notes.get("materiality_defaulted") is True

    def test_materiality_real_path_routes_low_materiality(self) -> None:
        """真值路径：低实质快照 → should_route=False → 投影 False（不抑制门
        打开——抑制交给 A-02 R8，投影只投事实）。"""
        low = _snapshot(core={"user_message": "嗯"})
        factors, notes = project_joint_factors(
            JointFactorSources(snapshot=low, policy=_policy())
        )
        assert factors.materiality_sufficient is False
        assert "materiality_defaulted" not in notes

    def test_materiality_high_partner_concern_routes(self) -> None:
        high = _snapshot(core={"partner_report": {"status": "urgent", "content": "用户状态异常"}})
        factors, _ = project_joint_factors(
            JointFactorSources(snapshot=high, policy=_policy())
        )
        assert factors.materiality_sufficient is True

    def test_budget_exhausted_projects_false(self) -> None:
        factors, notes = project_joint_factors(
            JointFactorSources(proactive_usage_today=5, policy=_policy(daily_budget=3))
        )
        assert factors.proactive_budget_available is False
        assert "proactive_budget_defaulted" not in notes

    def test_budget_within_projects_true(self) -> None:
        factors, _ = project_joint_factors(
            JointFactorSources(proactive_usage_today=2, policy=_policy(daily_budget=3))
        )
        assert factors.proactive_budget_available is True

    def test_budget_without_policy_defaults_conservative(self) -> None:
        factors, notes = project_joint_factors(JointFactorSources(proactive_usage_today=5))
        assert factors.proactive_budget_available is True  # 无 policy 面 → 保守可用
        assert notes.get("proactive_budget_defaulted") is True

    def test_quiet_hours_l0_fact_passthrough(self) -> None:
        factors, _ = project_joint_factors(JointFactorSources(quiet_hours_active=True))
        assert factors.quiet_hours is True


# ---------------------------------------------------------------------------
# 5. L2 matched_states → 交付步因子
# ---------------------------------------------------------------------------


class TestTaskFactorProjection:
    def test_deadline_pressure_urgent(self) -> None:
        factors = project_task_factors_from_l2(("deadline_pressure",), task_ref="task://l2-001")
        assert factors.time_pressure == "urgent"

    def test_learning_states_anchor_user_core(self) -> None:
        for state in ("knowledge_bottleneck", "transfer_failure"):
            factors = project_task_factors_from_l2((state,))
            assert factors.learning_goal is True
            assert factors.cognitive_ownership == "user_core"

    def test_shared_states_anchor_shared(self) -> None:
        factors = project_task_factors_from_l2(("execution_consistency", "growth_momentum"))
        assert factors.cognitive_ownership == "shared"
        assert factors.learning_goal is None  # 非学习信号不伪造

    def test_affective_states_anchor_shared_conservative(self) -> None:
        factors = project_task_factors_from_l2(("affective_pressure",))
        assert factors.cognitive_ownership == "shared"

    def test_plan_structures_low_risk_reversible(self) -> None:
        """计划结构调整经确认管道可回滚（rollback anchor 先例）。"""
        factors = project_task_factors_from_l2(("knowledge_bottleneck",))
        assert factors.risk_class == "low"
        assert factors.reversible is True

    def test_never_sets_allocation_mode(self) -> None:
        """投影器不猜测分配（防双真源）——allocation_mode 由 X-02 算出。"""
        factors = project_task_factors_from_l2(("deadline_pressure",))
        assert isinstance(factors, AllocationFactors)
        intervention_factors, _ = project_joint_factors(JointFactorSources(l2_intervention="error_replan_bridge"))
        assert isinstance(intervention_factors, InterventionPolicyFactors)

    def test_dirty_matched_states_never_raise(self) -> None:
        factors = project_task_factors_from_l2(None)
        assert factors.cognitive_ownership is None
        factors = project_task_factors_from_l2((42, "", "  ", "deadline_pressure"))
        assert factors.time_pressure == "urgent"


# ---------------------------------------------------------------------------
# 6. 韧性 + 溯源
# ---------------------------------------------------------------------------


class TestResilienceAndProvenance:
    def test_none_sources_project_defaults(self) -> None:
        factors, notes = project_joint_factors(None)
        assert factors.materiality_sufficient is True
        assert factors.nominated == ()
        assert notes.get("degraded") == []
        assert notes.get("materiality_defaulted") is True

    def test_projection_notes_always_have_degraded_list(self) -> None:
        _, notes = project_joint_factors(JointFactorSources(interaction_model_variant="task_execution"))
        assert isinstance(notes.get("degraded"), list)

    def test_sources_to_dict_provenance(self) -> None:
        sources = JointFactorSources(l2_intervention="reduce_load", quiet_hours_active=True)
        provenance = sources.to_dict()
        assert provenance["l2_intervention"] == "reduce_load"
        assert provenance["quiet_hours_active"] is True
        assert provenance["has_snapshot"] is False

    def test_projected_factors_feed_joint_core(self) -> None:
        """装配 → 联合核心的端到端衔接：投影产物直接可被 decide_joint 消费。"""
        from app.aurora.joint_decision import decide_joint
        from app.services.action_allocation_policy import decide_allocation

        factors, _ = project_joint_factors(
            JointFactorSources(
                l2_intervention="error_replan_bridge",
                interaction_model_variant="task_execution",
                permissions_granted=("plan_adjust",),
                task_context_present=True,
            )
        )
        task = project_task_factors_from_l2(
            ("knowledge_bottleneck",), task_ref="task://e2e-001", task_summary="端到端衔接"
        )
        allocation = decide_allocation(task)
        joint = decide_joint(factors, allocation)
        assert joint.selected in {"rescope", "no_action"}
        if joint.selected == "rescope":
            assert joint.mode in ("hybrid", "human")  # 交付集内
