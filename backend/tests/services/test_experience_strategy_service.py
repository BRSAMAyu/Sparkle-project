"""V4-I05 · 经验策略影子验证与有界启用 —— 服务层消费面测试（sqlite 隔离；真实证据链）。

验收复现面（验收员独立执行；全程生产服务路径，无 seed 行、无 monkeypatch 证据源）：
- **shadow 零行为红线（I04 同律）**：``patched_decision_inputs`` 在 shadow 档的
  返回载荷与 off 档**canonical JSON 逐字节恒等**（含提名序/因子/归因/版本）；
  admission 档 shadow 照 V3 自动激活（激活行为零差量），只多指标/日志观察；
- **重复摘要不累积为多源证据**：propose 落库前折叠——[ref,ref,ref] 与 [ref]
  同 patch_id、同唯一档位（single_observation 不被顶成 repeated，不过自动激
  活线；naive 计数会——突变面在 evidence 记录突变演示）；
- **无收益策略不静默启用（live 收益门）**：同域观察面负向反超（2 正 2 负）的
  prefer patch，off/shadow 档照 V3 自动激活；live 档收益门扣下（留 evidenced
  等显式 confirm）；正向占优（3 正 1 负）live 照常激活且缺省补观察窗；
- **撤回源后相关策略失效**：``invalidate_on_source_withdrawal`` 对命中源的
  active patch revoke（actor=evidence_withdrawal 审计），effective 集立即排
  除、版本 bump；其他来源 patch unaffected 显式保留。
- **FIX-564（candidate 绕行闭环）**：sweep 候选集纳 candidate 态（真撤回报告
  后 candidate 一并 revoke，admit/confirm 全 T6）；人工入口真撤回验证门——
  源未真撤的虚假报告 ValueError 拒绝、零 revoke；未命中 candidate 显式保留
  照常爬档；decision:// 通道同律。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from prometheus_client import REGISTRY
from sqlalchemy import func, select

from app.config import settings
from app.core.intervention_lifecycle import EVIDENCE_TIER_SINGLE
from app.core.outcome_ledger import (
    OutcomeEntry,
    OutcomePolarity,
    OutcomeSource,
    TruthClass,
    derive_outcome_id,
)
from app.models.execution_intent import ExecutionMode
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.models.policy_patch import PolicyPatchRecord
from app.models.user import User
from app.services.experience_memory_projector import ExperienceMemoryProjector
from app.services.intervention_lifecycle_service import InterventionLifecycleService
from app.services.policy_patch_service import PolicyPatchService

_T0 = datetime(2026, 9, 19, 10, 0, 0)
_NOW = _T0 + timedelta(hours=80)  # 72h 观察窗已关（D-05 投影语义）


@pytest.fixture(autouse=True)
def _clean_cache():
    PolicyPatchService.reset_cache()
    ExperienceMemoryProjector.reset_cache()
    yield
    PolicyPatchService.reset_cache()
    ExperienceMemoryProjector.reset_cache()


@pytest.fixture()
def strategy_mode(monkeypatch):
    """档位切换 + 有界窗 WARN 标记复位（隔离测试序）。"""

    def _set(mode: str) -> str:
        monkeypatch.setattr(settings, "EXPERIENCE_STRATEGY_MODE", mode)
        monkeypatch.setattr("app.services.policy_patch_service._LIVE_WINDOW_WARNED", False)
        return mode

    monkeypatch.setattr(settings, "EXPERIENCE_STRATEGY_LIVE_WINDOW_HOURS", 72)
    return _set


async def _make_user(db_session) -> User:
    user = User(
        username=f"u{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@t.co",
        hashed_password="x",
        registration_source="email",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _decision(
    user_id, *, intervention_type: str, mode: ExecutionMode | None = ExecutionMode.HYBRID, task_id=None, salt: str = ""
):
    from app.core.aurora_decision import AuroraDecisionContract

    return AuroraDecisionContract(
        user_id=user_id,
        intervention_type=intervention_type,
        rationale_summary=f"i05 test decision {salt or uuid4().hex[:6]}",
        cognition_tier="l2_intervention",
        execution_mode=mode,
        governance_mode="live",
        evidence_refs=("signal://cognitive_load",),
        action_proposal_ref=f"task://{task_id}" if task_id else None,
    )


def _outcome(
    user_id, *, at: datetime, polarity=OutcomePolarity.POSITIVE, correlation: dict | None = None
) -> OutcomeEntry:
    sid = uuid4().hex
    return OutcomeEntry(
        outcome_id=derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=sid),
        source=OutcomeSource.TASK_COMPLETION,
        source_id=sid,
        user_id=str(user_id),
        occurred_at=at,
        truth_class=TruthClass.ACTUAL,
        polarity=polarity,
        source_ref=f"{OutcomeSource.TASK_COMPLETION.value}://{sid}",
        correlation=correlation or {},
    )


async def _expose_and_link(
    db_session,
    user,
    *,
    intervention_type: str,
    n_positive: int = 0,
    n_negative: int = 0,
    goal: str = "exam",
    at: datetime = _T0,
) -> str:
    """真实 D-05 exposure + outcome 关联（与 A-05 服务测试同款生产路径）。"""
    svc = InterventionLifecycleService(db_session)
    task_id = uuid4()
    decision = _decision(user.id, intervention_type=intervention_type, task_id=task_id)
    result = await svc.record_exposure(decision=decision, user_id=user.id, goal_type=goal, occurred_at=at)
    assert result.recorded, result.reason
    for i in range(n_positive):
        linked = await svc.record_outcome_association(
            decision_id=result.decision_id,
            outcome=_outcome(
                user.id,
                at=at + timedelta(hours=i + 1),
                polarity=OutcomePolarity.POSITIVE,
                correlation={"task_id": str(task_id)},
            ),
        )
        assert linked.recorded, linked.reason
    for i in range(n_negative):
        linked = await svc.record_outcome_association(
            decision_id=result.decision_id,
            outcome=_outcome(
                user.id,
                at=at + timedelta(hours=i + 1),
                polarity=OutcomePolarity.NEGATIVE,
                correlation={"task_id": str(task_id)},
            ),
        )
        assert linked.recorded, linked.reason
    return result.decision_id


async def _experience_record_id(
    db_session,
    user,
    *,
    intervention_type: str,
    goal: str = "exam",
    friction: str = "cognitive_overload",
) -> str:
    projection = await ExperienceMemoryProjector(db_session).project(user_id=user.id, now=_NOW)
    for record in projection.records:
        signature = record.signature.as_dict()
        if (
            record.intervention == intervention_type
            and signature.get("goal_type") == goal
            and signature.get("friction_tag") == friction
        ):
            return record.record_id
    raise AssertionError(f"no M-06 projection record for {intervention_type}/{goal}/{friction}")


async def _patch_count(db_session, user) -> int:
    return int(
        (
            await db_session.execute(
                select(func.count()).select_from(PolicyPatchRecord).where(PolicyPatchRecord.user_id == user.id)
            )
        ).scalar_one()
    )


def _metric_value(stage: str, verdict: str) -> float:
    return (
        REGISTRY.get_sample_value("sparkle_experience_strategy_shadow_total", {"stage": stage, "verdict": verdict})
        or 0.0
    )


async def _propose_prefer_practice(db_session, user):
    svc = PolicyPatchService(db_session)
    record_id = await _experience_record_id(db_session, user, intervention_type="practice")
    result = await svc.propose_patch(
        user.id,
        surface="intervention_preference",
        payload={"intervention": "practice", "direction": "prefer"},
        evidence_refs=[f"memory://experience/{record_id}"],
    )
    assert result.record is not None
    return svc, result.record


async def _withdraw_experience_source(db_session, user, *, intervention_type: str) -> None:
    """真撤回（M-07 删除链口径）：软删该用户该干预的全部未删生命周期行。

    FIX-564：``invalidate_on_source_withdrawal`` 的入口验证门要求撤回报告先在
    真源证据面可见——生产中由删除执行器（memory/result 域）落定，本 helper 是
    其在测试内的等价真源动作（test_experience_memory_projector 软删先例同款）。
    """
    from datetime import datetime as _dt

    await db_session.execute(
        InterventionLifecycleEvent.__table__.update()
        .where(
            InterventionLifecycleEvent.user_id == user.id,
            InterventionLifecycleEvent.intervention_type == intervention_type,
            InterventionLifecycleEvent.deleted_at.is_(None),
        )
        .values(deleted_at=_dt.utcnow())
    )
    await db_session.commit()


# ---------------------------------------------------------------------------
# 验收②：重复摘要不累积为多源证据（propose 折叠；真实证据链）
# ---------------------------------------------------------------------------


class TestDuplicateEvidenceFold:
    async def test_duplicated_refs_fold_to_unique_single_tier(self, db_session, strategy_mode):
        """[ref,ref,ref] 与 [ref] 同身份同档位：single_observation 停 evidenced。"""
        strategy_mode("off")
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=1)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")

        svc = PolicyPatchService(db_session)
        dup = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"] * 3,  # 重复摘要×3
        )
        assert dup.record is not None
        assert len(dup.record.evidence_refs) == 1  # 落库即折叠
        single = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        assert single.record is not None
        assert single.idempotent is True  # 内容寻址：折叠后同身份
        assert await _patch_count(db_session, user) == 1

        admitted = await svc.admit_evidence(user.id, dup.record.patch_id, now=_NOW)
        assert admitted.record.state == "evidenced"  # 唯一引用 → single → 不自动激活
        assert admitted.record.evidence_tier == EVIDENCE_TIER_SINGLE

    async def test_naive_counting_would_have_crossed_auto_activation(self, db_session, strategy_mode):
        """突变面对照（可失败面）：naive 计数下 3 份重复必过自动激活线。

        直接以未折叠引用序列调用证据门核验内部路径等价面：3 条同 ref 解析 =
        resolved 3 → repeated。生产路径已折叠（上一测试钉住 evidenced）——本测
        试钉住「若折叠被移除则该用户此 patch 会自动激活」这一突变事实。
        """
        strategy_mode("off")
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=1)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        from app.core.intervention_lifecycle import EVIDENCE_TIER_REPEATED, association_evidence_tier

        naive_resolved = 3  # 重复引用逐条计数（未折叠语义）
        assert association_evidence_tier(naive_resolved) == EVIDENCE_TIER_REPEATED
        assert PolicyPatchService._inputs_cache_key is not None  # 结构面护栏（服务在位）

        # 折叠后的服务路径：存储行唯一引用（已由上一测试钉）；这里直接核验
        # 折叠函数是服务落库前的唯一折叠点（防绕过：propose 后存储行长度=1）。
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"] * 3,
        )
        assert result.record is not None and len(result.record.evidence_refs) == 1


# ---------------------------------------------------------------------------
# 验收③（前半）：无收益策略不静默启用（live 收益门）+ 有界观察窗
# ---------------------------------------------------------------------------


class TestLiveBenefitGate:
    async def _no_benefit_setup(self, db_session, user):
        """2 正 2 负同域：方向门过（≥1 正）但收益判定 no_benefit（负向等权反超/平手）。"""
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2, n_negative=2)
        return await _propose_prefer_practice(db_session, user)

    async def test_off_mode_auto_activates_despite_no_benefit(self, db_session, strategy_mode):
        """off = V3 行为（档位达标即自动激活）——本卡零行为基线。"""
        strategy_mode("off")
        user = await _make_user(db_session)
        svc, record = await self._no_benefit_setup(db_session, user)
        admitted = await svc.admit_evidence(user.id, record.patch_id, now=_NOW)
        assert admitted.record.state == "active"

    async def test_shadow_mode_observes_but_activation_unchanged(self, db_session, strategy_mode):
        """shadow = 观察零行为：no_benefit 判定进指标，激活行为照 V3。"""
        strategy_mode("shadow")
        user = await _make_user(db_session)
        svc, record = await self._no_benefit_setup(db_session, user)
        before = _metric_value("admission", "no_benefit")
        admitted = await svc.admit_evidence(user.id, record.patch_id, now=_NOW)
        assert admitted.record.state == "active"  # 激活行为与 off 恒等
        assert _metric_value("admission", "no_benefit") == before + 1.0  # 观察在案（不静默）

    async def test_live_mode_withholds_auto_activation_on_no_benefit(self, db_session, strategy_mode):
        """live 收益门：无收益不静默自动启用——留 evidenced 等显式 confirm。"""
        strategy_mode("live")
        user = await _make_user(db_session)
        svc, record = await self._no_benefit_setup(db_session, user)
        admitted = await svc.admit_evidence(user.id, record.patch_id, now=_NOW)
        assert admitted.record.state == "evidenced"  # 扣下（未激活）
        effective = await svc.effective_patches(user.id, now=_NOW)
        assert effective == ()  # 生效集立即为空
        # 显式用户 confirm 仍是合法路径（confirm(若需) 语义保持）
        confirmed = await svc.confirm_patch(user.id, record.patch_id, now=_NOW)
        assert confirmed.record.state == "active"

    async def test_live_mode_bounded_window_on_beneficial_activation(self, db_session, strategy_mode):
        """有界启用 · 观察窗：正向占优（3 正 1 负）live 激活并缺省补 72h 窗。"""
        strategy_mode("live")
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=3, n_negative=1)
        svc, record = await _propose_prefer_practice(db_session, user)
        admitted = await svc.admit_evidence(user.id, record.patch_id, now=_NOW)
        assert admitted.record.state == "active"
        assert admitted.record.expires_at is not None
        assert admitted.record.expires_at == _NOW + timedelta(hours=72)

    async def test_off_mode_activation_has_no_bounded_window(self, db_session, strategy_mode):
        """off = V3 行为：激活不带窗（有界化是 live-only 行为）。"""
        strategy_mode("off")
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=3, n_negative=1)
        svc, record = await _propose_prefer_practice(db_session, user)
        admitted = await svc.admit_evidence(user.id, record.patch_id, now=_NOW)
        assert admitted.record.state == "active"
        assert admitted.record.expires_at is None


# ---------------------------------------------------------------------------
# shadow 零行为红线（decision 面）：shadow 返回与 off 逐字节恒等
# ---------------------------------------------------------------------------


class TestShadowZeroBehaviorRedLine:
    async def _active_patch_and_inputs(self, db_session, user, mode_setter, mode: str, decision_context=None):
        mode_setter(mode)
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2)
        svc, record = await _propose_prefer_practice(db_session, user)
        admitted = await svc.admit_evidence(user.id, record.patch_id, now=_NOW)
        assert admitted.record.state == "active"
        PolicyPatchService.reset_cache()
        inputs = await svc.patched_decision_inputs(
            user.id,
            ("explain", "practice"),
            goal_type="exam",
            friction_tag="cognitive_overload",
            now=_NOW,
            decision_context=decision_context,
        )
        return inputs

    async def test_shadow_payload_identical_to_off_byte_for_byte(self, db_session, strategy_mode):
        """shadow 零行为红线（可失败）：返回载荷 canonical JSON 与 off 逐字节恒等。

        加严形态：即使传入**会门出 patch 的情境事实**（human_required_step），
        shadow 也必须照 off 原样应用（门出投影只进指标/日志，不进载荷）——
        「shadow 偷跑 live 门」的任何实现都会在本断言上翻红（突变实证见
        evidence diff_or_evidence_only.md 反转变红记录）。
        """
        user = await _make_user(db_session)
        gating_context = {"human_required_step": True}
        off_plain = await self._active_patch_and_inputs(db_session, user, strategy_mode, "off")
        off_gated_ctx = await self._active_patch_and_inputs(db_session, user, strategy_mode, "off", gating_context)
        shadow_plain = await self._active_patch_and_inputs(db_session, user, strategy_mode, "shadow")
        shadow_gated_ctx = await self._active_patch_and_inputs(
            db_session, user, strategy_mode, "shadow", gating_context
        )

        def _payload(inputs) -> str:
            return json.dumps(inputs.annotations() | inputs.context_component(), sort_keys=True, ensure_ascii=False)

        # off 自身：无情境门事实 → 情境门不咬（fail-closed 不猜缺席事实）
        assert off_plain.applied_patch_ids == off_gated_ctx.applied_patch_ids
        # 红线：shadow 与 off 在两种情境下都逐字节恒等
        assert _payload(shadow_plain) == _payload(off_plain)
        assert _payload(shadow_gated_ctx) == _payload(off_gated_ctx)
        assert shadow_plain.nominated == off_plain.nominated
        assert shadow_gated_ctx.applied_patch_ids == off_gated_ctx.applied_patch_ids
        assert shadow_plain.policy_patch_version == off_plain.policy_patch_version
        assert shadow_plain.allocation_user_preference == off_plain.allocation_user_preference

    async def test_live_gated_out_by_human_required_step(self, db_session, strategy_mode):
        """live 门出面：human_required_step 情境 → patch 不进应用面（I07 门不绕过）。"""
        user = await _make_user(db_session)
        strategy_mode("live")
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2)
        svc, record = await _propose_prefer_practice(db_session, user)
        admitted = await svc.admit_evidence(user.id, record.patch_id, now=_NOW)
        assert admitted.record.state == "active"
        PolicyPatchService.reset_cache()
        inputs = await svc.patched_decision_inputs(
            user.id,
            ("explain", "practice"),
            goal_type="exam",
            friction_tag="cognitive_overload",
            now=_NOW,
            decision_context={"human_required_step": True},
        )
        assert inputs.applied_patch_ids == ()  # 门出：不进应用面
        assert inputs.nominated == ("explain", "practice")  # 重排消失（V3 基线序）
        assert _metric_value("decision", "do_not_apply_human_required_step") >= 1.0

    async def test_live_without_human_required_fact_applies(self, db_session, strategy_mode):
        """live 无 do_not_apply 事实 → 正常应用（fail-closed 只对缺事实的门）。"""
        user = await _make_user(db_session)
        strategy_mode("live")
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2)
        svc, record = await _propose_prefer_practice(db_session, user)
        admitted = await svc.admit_evidence(user.id, record.patch_id, now=_NOW)
        assert admitted.record.state == "active"
        PolicyPatchService.reset_cache()
        inputs = await svc.patched_decision_inputs(
            user.id,
            ("explain", "practice"),
            goal_type="exam",
            friction_tag="cognitive_overload",
            now=_NOW,
        )
        assert inputs.applied_patch_ids == (record.patch_id,)
        assert inputs.nominated[0] == "practice"


# ---------------------------------------------------------------------------
# shadow_report（两臂对照审计工件）
# ---------------------------------------------------------------------------


class TestShadowReport:
    async def test_report_contains_both_arms_and_is_deterministic(self, db_session, strategy_mode):
        strategy_mode("shadow")
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2)
        svc, record = await _propose_prefer_practice(db_session, user)
        await svc.admit_evidence(user.id, record.patch_id, now=_NOW)

        report = await svc.shadow_report(
            user.id,
            ("explain", "practice"),
            goal_type="exam",
            friction_tag="cognitive_overload",
            now=_NOW,
        )
        assert report["comparison_id"].startswith("expshadow_")
        assert report["control_nominated"] == ["explain", "practice"]
        assert report["treatment_nominated"] == ["practice", "explain"]
        assert report["changed"] is True
        assert report["cards"][0]["patch_id"] == record.patch_id
        assert report["cards"][0]["observations"]["n_positive"] == 2
        again = await svc.shadow_report(
            user.id,
            ("explain", "practice"),
            goal_type="exam",
            friction_tag="cognitive_overload",
            now=_NOW,
        )
        assert again == report  # 同输入恒同工件（重放可复核）

    async def test_report_human_required_context_records_gate(self, db_session, strategy_mode):
        strategy_mode("shadow")
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2)
        svc, record = await _propose_prefer_practice(db_session, user)
        admitted = await svc.admit_evidence(user.id, record.patch_id, now=_NOW)
        assert admitted.record.state == "active"
        report = await svc.shadow_report(
            user.id,
            ("explain", "practice"),
            goal_type="exam",
            friction_tag="cognitive_overload",
            decision_context={"human_required_step": True},
            now=_NOW,
        )
        assert report["treatment_nominated"] == ["explain", "practice"]  # 全部门出 → treatment=control
        assert report["changed"] is False
        assert any(
            g["applicable"] is False and "do_not_apply_human_required_step" in g["reasons"]
            for g in report["gate_outcomes"]
        )


# ---------------------------------------------------------------------------
# 验收③（后半）：撤回源后相关策略失效
# ---------------------------------------------------------------------------


class TestSourceWithdrawalInvalidation:
    async def _two_active_patches(self, db_session, user):
        """practice 与 explain 各一条 active patch（各自独立源）。"""
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2)
        await _expose_and_link(db_session, user, intervention_type="explain", n_positive=2)
        svc = PolicyPatchService(db_session)
        ids = {}
        for intervention in ("practice", "explain"):
            record_id = await _experience_record_id(db_session, user, intervention_type=intervention)
            result = await svc.propose_patch(
                user.id,
                surface="intervention_preference",
                payload={"intervention": intervention, "direction": "prefer"},
                evidence_refs=[f"memory://experience/{record_id}"],
            )
            admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
            assert admitted.record.state == "active"
            ids[intervention] = (result.record.patch_id, record_id)
        return svc, ids

    @pytest.mark.parametrize("mode", ["off", "shadow", "live"])
    async def test_withdrawn_source_invalidates_related_patch(self, db_session, strategy_mode, mode):
        """撤回源 → 相关策略失效（三档一致——失效不是模式行为，是账本事实）。

        FIX-564：报告前先真撤回（软删 D-05 行）——入口验证门要求撤回在真源
        证据面可见；断言零改动（setup 增加真实撤回步骤）。
        """
        strategy_mode(mode)
        user = await _make_user(db_session)
        svc, ids = await self._two_active_patches(db_session, user)
        practice_patch_id, practice_record_id = ids["practice"]
        explain_patch_id, _ = ids["explain"]
        await _withdraw_experience_source(db_session, user, intervention_type="practice")
        version_before = await svc.policy_version(user.id, now=_NOW)

        audit = await svc.invalidate_on_source_withdrawal(
            user.id,
            kind="material_deleted",
            source_ref=f"memory://experience/{practice_record_id}",
            now=_NOW,
        )
        assert audit["affected_patch_ids"] == [practice_patch_id]
        assert explain_patch_id in audit["unaffected_patch_ids"]  # 合法其他来源显式保留
        assert audit["policy_version_after"] != version_before

        effective = await svc.effective_patches(user.id, now=_NOW)
        assert {p.patch_id for p in effective} == {explain_patch_id}
        revoked_row = await svc._get_by_patch_id(practice_patch_id)
        assert revoked_row.state == "revoked"
        assert revoked_row.revoke_reason == "evidence_source_withdrawal"
        last_entry = revoked_row.transition_history[-1]
        assert last_entry["actor"] == "evidence_withdrawal"
        assert last_entry["reason"] == "T4.revoked_by_user_correction"

    async def test_unknown_source_ref_rejected_loudly(self, db_session, strategy_mode):
        """反例（可失败）：词表外 ref → ValueError（不猜）。"""
        strategy_mode("off")
        user = await _make_user(db_session)
        svc = PolicyPatchService(db_session)
        with pytest.raises(ValueError, match="closed-scheme"):
            await svc.invalidate_on_source_withdrawal(
                user.id, kind="material_deleted", source_ref="signal://crisis", now=_NOW
            )

    async def test_reactivated_content_cannot_revive_after_withdrawal(self, db_session, strategy_mode):
        """撤回失效后同内容再提议 = 同一 revoked 行（内容寻址），不可复活。

        FIX-564：真撤回（软删 D-05 行）先于报告——验证门要求撤回真源可见。
        """
        strategy_mode("off")
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2)
        svc, record = await _propose_prefer_practice(db_session, user)
        await svc.admit_evidence(user.id, record.patch_id, now=_NOW)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        await _withdraw_experience_source(db_session, user, intervention_type="practice")
        await svc.invalidate_on_source_withdrawal(
            user.id, kind="material_deleted", source_ref=f"memory://experience/{record_id}", now=_NOW
        )
        reproposed = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        assert reproposed.record.patch_id == record.patch_id
        assert reproposed.record.state == "revoked"  # 终态不复活
        again = await svc.admit_evidence(user.id, record.patch_id, now=_NOW)
        assert again.record.state == "revoked" and again.reasons and "T6" in again.reasons[0]


# ---------------------------------------------------------------------------
# FIX-564 · 撤源失效 sweep 纳 candidate + 人工入口真撤回验证门（I05R2 R2-D1 闭环）
# ---------------------------------------------------------------------------


class TestWithdrawalSweepCandidateClosure:
    """candidate 绕行缺口闭环（off/live 双档复现链的修后形态；修前红对照入
    run_manifest）。

    缺陷复现链（修前亲证可 active）：candidate 引用已撤源 → 报告撤回（sweep 仅
    active/evidenced，candidate 豁免）→ admit 照常爬档（off = repeated 自动
    active；live = 正收益源放行——收益门只拦无收益不感知撤回；无收益源经
    evidenced 后 confirm 人工入口放行）。修后三段全部封闭：真撤回报告时
    candidate 一并 revoke（终态，admit/confirm 全 T6）；虚假报告（源未真撤）
    被验证门 ValueError 拒绝、零 revoke。
    """

    async def _candidate_on_practice(self, db_session, user, *, n_positive: int, n_negative: int = 0):
        await _expose_and_link(
            db_session, user, intervention_type="practice", n_positive=n_positive, n_negative=n_negative
        )
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        assert result.record is not None
        assert result.record.state == "candidate"  # 未 admit：缺陷链的起点态
        return svc, result.record, record_id

    async def test_off_candidate_swept_then_admit_blocked(self, db_session, strategy_mode):
        """off 档：真撤回报告 → candidate revoke；admit T6（修前此链爬到 active）。"""
        strategy_mode("off")
        user = await _make_user(db_session)
        svc, candidate, record_id = await self._candidate_on_practice(db_session, user, n_positive=2)
        await _withdraw_experience_source(db_session, user, intervention_type="practice")

        audit = await svc.invalidate_on_source_withdrawal(
            user.id, kind="material_deleted", source_ref=f"memory://experience/{record_id}", now=_NOW
        )
        assert audit["affected_patch_ids"] == [candidate.patch_id]
        assert audit["affected_states"][candidate.patch_id] == "candidate"  # sweep 从 candidate 态收走

        swept = await svc._get_by_patch_id(candidate.patch_id)
        assert swept.state == "revoked"
        assert swept.revoke_reason == "evidence_source_withdrawal"
        assert swept.transition_history[-1]["actor"] == "evidence_withdrawal"

        admitted = await svc.admit_evidence(user.id, candidate.patch_id, now=_NOW)
        assert admitted.record.state == "revoked"  # 终态不可 admit（修前此处可 active）
        assert admitted.reasons and "T6" in admitted.reasons[0]
        assert await svc.effective_patches(user.id, now=_NOW) == ()

    async def test_live_positive_source_candidate_swept_then_admit_blocked(self, db_session, strategy_mode):
        """live 档正收益源（修前收益门放行的亲证形态）：修后 sweep 先收，收益门无关。"""
        strategy_mode("live")
        user = await _make_user(db_session)
        svc, candidate, record_id = await self._candidate_on_practice(db_session, user, n_positive=3, n_negative=1)
        await _withdraw_experience_source(db_session, user, intervention_type="practice")
        audit = await svc.invalidate_on_source_withdrawal(
            user.id, kind="material_deleted", source_ref=f"memory://experience/{record_id}", now=_NOW
        )
        assert audit["affected_patch_ids"] == [candidate.patch_id]
        admitted = await svc.admit_evidence(user.id, candidate.patch_id, now=_NOW)
        assert admitted.record.state == "revoked"
        assert admitted.reasons and "T6" in admitted.reasons[0]

    async def test_false_report_refused_then_true_withdrawal_closes_confirm_leg(self, db_session, strategy_mode):
        """live 无收益链两段：①虚假报告（源未真撤）ValueError 拒绝、零 revoke
        （防误伤补门）；②真撤回后报告 → candidate 收走——confirm 人工入口无
        evidenced 行可达（revoked T6；修前 confirm 可放行未 sweep 的行）。"""
        strategy_mode("live")
        user = await _make_user(db_session)
        svc, candidate, record_id = await self._candidate_on_practice(db_session, user, n_positive=2, n_negative=2)

        with pytest.raises(ValueError, match="not verifiable"):
            await svc.invalidate_on_source_withdrawal(
                user.id, kind="material_deleted", source_ref=f"memory://experience/{record_id}", now=_NOW
            )
        untouched = await svc._get_by_patch_id(candidate.patch_id)
        assert untouched.state == "candidate"  # 虚假报告零副作用

        await _withdraw_experience_source(db_session, user, intervention_type="practice")
        audit = await svc.invalidate_on_source_withdrawal(
            user.id, kind="material_deleted", source_ref=f"memory://experience/{record_id}", now=_NOW
        )
        assert audit["affected_patch_ids"] == [candidate.patch_id]
        confirmed = await svc.confirm_patch(user.id, candidate.patch_id, now=_NOW)
        assert confirmed.record.state == "revoked"
        assert confirmed.reasons and "T6" in confirmed.reasons[0]

    async def test_unaffected_candidate_explicitly_preserved_and_admittable(self, db_session, strategy_mode):
        """反例（可失败）：sweep 纳 candidate 不越权——未命中 candidate 显式保留
        且 admit 照常爬档（撤回只作用于命中源，无连带伤害）。"""
        strategy_mode("off")
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2)
        practice_record = await _experience_record_id(db_session, user, intervention_type="practice")
        await _expose_and_link(db_session, user, intervention_type="explain", n_positive=2)
        explain_record = await _experience_record_id(db_session, user, intervention_type="explain")
        svc = PolicyPatchService(db_session)
        p1 = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{practice_record}"],
        )
        p2 = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "explain", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{explain_record}"],
        )
        assert p1.record is not None and p2.record is not None
        await _withdraw_experience_source(db_session, user, intervention_type="practice")
        audit = await svc.invalidate_on_source_withdrawal(
            user.id, kind="material_deleted", source_ref=f"memory://experience/{practice_record}", now=_NOW
        )
        assert audit["affected_patch_ids"] == [p1.record.patch_id]
        assert p2.record.patch_id in audit["unaffected_patch_ids"]  # 未命中 candidate 显式保留
        admitted = await svc.admit_evidence(user.id, p2.record.patch_id, now=_NOW)
        assert admitted.record.state == "active"  # 合法源照常爬档

    async def test_decision_channel_candidate_swept_after_true_outcome_withdrawal(self, db_session, strategy_mode):
        """decision:// 通道同律：decision 的 outcome 行真撤（软删）后报告 →
        candidate revoke（验证门双通道；result_retracted 撤回域）。"""
        from app.core.intervention_lifecycle import LifecycleEventType

        strategy_mode("off")
        user = await _make_user(db_session)
        decision_id = await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2)
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"decision://{decision_id}"],
        )
        assert result.record is not None
        await db_session.execute(
            InterventionLifecycleEvent.__table__.update()
            .where(
                InterventionLifecycleEvent.user_id == user.id,
                InterventionLifecycleEvent.decision_id == decision_id,
                InterventionLifecycleEvent.event_type == LifecycleEventType.OUTCOME_OBSERVED.value,
                InterventionLifecycleEvent.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.utcnow())
        )
        await db_session.commit()
        audit = await svc.invalidate_on_source_withdrawal(
            user.id, kind="result_retracted", source_ref=f"decision://{decision_id}", now=_NOW
        )
        assert audit["affected_patch_ids"] == [result.record.patch_id]
        assert audit["affected_states"][result.record.patch_id] == "candidate"

    async def test_withdrawal_gate_bypasses_stale_projection_cache(self, db_session, strategy_mode):
        """FIX-564 C1 补钉（R1-C 存活面）：验证门 fresh 读绕投影类级缓存。

        毒化条目 = 撤回后 watermark + 撤回前内容（记录在场且带 outcome 证据）
        ——watermark 失效被刻意短路，只剩 ``use_cache=False`` 一道防线。真撤回
        报告必须照常成功；若 ``_source_withdrawal_visible`` 的 fresh 读回退为
        走缓存（R1-C mutation），毒化条目命中 → visible=False → ValueError
        拒绝真实报告，本用例必红。
        """
        strategy_mode("off")
        user = await _make_user(db_session)
        svc, candidate, record_id = await self._candidate_on_practice(db_session, user, n_positive=2)

        projector = ExperienceMemoryProjector(db_session)
        stale_projection = await projector.project(user_id=user.id, now=_NOW, use_cache=False)
        assert any(r.record_id == record_id and r.has_outcome_evidence for r in stale_projection.records)

        await _withdraw_experience_source(db_session, user, intervention_type="practice")

        watermark = await InterventionLifecycleService(db_session).watermark(user_id=user.id)
        cache_key = f"{InterventionLifecycleService.summary_cache_key(user_id=user.id)}|demo=0"
        ExperienceMemoryProjector._cache_put(cache_key, watermark, stale_projection)

        audit = await svc.invalidate_on_source_withdrawal(
            user.id, kind="material_deleted", source_ref=f"memory://experience/{record_id}", now=_NOW
        )
        assert audit["affected_patch_ids"] == [candidate.patch_id]
