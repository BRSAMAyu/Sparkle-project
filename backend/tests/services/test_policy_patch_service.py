"""A-05 · PolicyPatchService 服务层测试（sqlite 隔离，不触 dev DB；真实证据链）。

验收复现面（验收员独立执行）：
- **非法 patch field 被拒绝**（验收 ①）：非白名单 surface / 未知 payload 键 /
  词表外值 → ``propose_patch`` 零写路径（行数不增，fail-closed）；
- **用户纠正可撤销**（验收 ②）：revoke 后同 scope 决策输入**不再引用**该
  patch（重排消失 / applied_patch_ids 排除 / 版本 bump）；审计历史保留 T4；
- **同 scope 历史有效 intervention 可改变 ranking 且带 evidence refs**
  （验收 ③）：证据链 = 真实 D-05 ``record_exposure`` + ``record_outcome_association``
  → 真实 M-06 ``ExperienceMemoryProjector`` 投影 → 证据门 → active patch →
  ``patched_decision_inputs`` 重排提名 + ``memory://experience/...`` refs →
  A-02 引擎按重排后提名选中 → A-01 契约 evidence_refs 合法（非 mock：全程
  走生产服务，无 seed 行、无 monkeypatch 证据源）；
- **policy version 缓存失效语义**（验收 ④）：版本 bump（revoke/激活）→
  进程缓存不命中（重算）；``_cache_get`` 版本比对单测钉死。

证据门：single_observation → confirm(若需)（不自动激活）；repeated → 自动
激活；不可解析证据 / 方向不匹配 → rejected 终态（审计保留）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.aurora_decision import AuroraDecisionContract
from app.core.intervention_lifecycle import EVIDENCE_TIER_REPEATED, EVIDENCE_TIER_SINGLE
from app.core.outcome_ledger import (
    OutcomeEntry,
    OutcomePolarity,
    OutcomeSource,
    TruthClass,
    derive_outcome_id,
)
from app.models.execution_intent import ExecutionMode
from app.models.policy_patch import PolicyPatchRecord
from app.models.user import User
from app.services.experience_memory_projector import ExperienceMemoryProjector
from app.services.intervention_lifecycle_service import InterventionLifecycleService
from app.services.policy_patch_service import PolicyPatchService

_T0 = datetime(2026, 9, 19, 10, 0, 0)
_NOW = _T0 + timedelta(hours=80)  # 72h 观察窗已关


@pytest.fixture(autouse=True)
def _clean_cache():
    PolicyPatchService.reset_cache()
    ExperienceMemoryProjector.reset_cache()
    yield
    PolicyPatchService.reset_cache()
    ExperienceMemoryProjector.reset_cache()


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
    user_id,
    *,
    intervention_type: str = "practice",
    mode: ExecutionMode | None = ExecutionMode.HYBRID,
    task_id=None,
    evidence=("signal://cognitive_load",),
    salt: str = "",
) -> AuroraDecisionContract:
    return AuroraDecisionContract(
        user_id=user_id,
        intervention_type=intervention_type,
        rationale_summary=f"a05 test decision {salt or uuid4().hex[:6]}",
        cognition_tier="l2_intervention",
        execution_mode=mode,
        governance_mode="live",
        evidence_refs=tuple(evidence),
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
    mode: ExecutionMode | None,
    n_positive: int = 0,
    n_negative: int = 0,
    goal: str = "exam",
    evidence=("signal://cognitive_load",),
    at: datetime = _T0,
) -> str:
    """落一条真实 exposure + N 条真实 outcome 关联（D-05 生产服务路径）。"""
    svc = InterventionLifecycleService(db_session)
    task_id = uuid4()
    decision = _decision(user.id, intervention_type=intervention_type, mode=mode, task_id=task_id, evidence=evidence)
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
    """真实 M-06 投影中该情境切片的 record_id（证据 ref 的锚）。"""
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


# ---------------------------------------------------------------------------
# 1. fail-closed 写门（验收 ①）
# ---------------------------------------------------------------------------


class TestFailClosedPropose:
    async def test_illegal_surface_writes_nothing(self, db_session):
        user = await _make_user(db_session)
        svc = PolicyPatchService(db_session)
        for surface in ("system_prompt", "temperature", "prompt_override", "code"):
            result = await svc.propose_patch(
                user.id,
                surface=surface,
                payload={"adjustment": "finer"},
                evidence_refs=["memory://experience/expmem_0123456789abcdef"],
            )
            assert result.record is None
            assert result.reasons[0].startswith("V1.surface_not_whitelisted")
        assert await _patch_count(db_session, user) == 0  # 零写路径

    async def test_illegal_payload_writes_nothing(self, db_session):
        user = await _make_user(db_session)
        svc = PolicyPatchService(db_session)
        bad_payloads = [
            {"adjustment": "finer", "hidden_prompt": "x"},  # 未知键
            {"adjustment": "maximal"},  # 词表外值
            {"intervention": "practice", "direction": "prefer"},  # granularity 面的错键
        ]
        for payload in bad_payloads:
            result = await svc.propose_patch(
                user.id,
                surface="granularity",
                payload=payload,
                evidence_refs=["memory://experience/expmem_0123456789abcdef"],
            )
            assert result.record is None and result.reasons
        assert await _patch_count(db_session, user) == 0

    async def test_propose_idempotent_by_content(self, db_session):
        user = await _make_user(db_session)
        svc = PolicyPatchService(db_session)
        first = await svc.propose_patch(
            user.id,
            surface="granularity",
            payload={"adjustment": "finer"},
            evidence_refs=["decision://aurora_" + "1" * 32],
        )
        assert first.record is not None and first.idempotent is False
        second = await svc.propose_patch(
            user.id,
            surface="granularity",
            payload={"adjustment": "finer"},
            evidence_refs=["decision://aurora_" + "1" * 32],
        )
        assert second.idempotent is True and second.record.patch_id == first.record.patch_id
        assert await _patch_count(db_session, user) == 1

    async def test_propose_legal_patch_lands_candidate(self, db_session):
        user = await _make_user(db_session)
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=["memory://experience/expmem_0123456789abcdef"],
        )
        assert result.record is not None and result.record.state == "candidate"


# ---------------------------------------------------------------------------
# 2. 证据门（真实证据链：D-05 → M-06 → gate）
# ---------------------------------------------------------------------------


class TestEvidenceGateRealChain:
    async def test_repeated_evidence_auto_activates(self, db_session):
        """2 条正向 outcome（D-05 真实关联）→ M-06 记录 repeated → 自动 active。"""
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=2)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")

        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        assert result.record is not None
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record is not None
        assert admitted.record.state == "active"  # tier=repeated → T2 自动激活
        assert admitted.record.evidence_tier == EVIDENCE_TIER_REPEATED
        # P2-2（R2）：有序全史钉死（长度 + 序列，非 any()——历史重写/丢早期
        # 条目的变异在此必红；append-only 是「用户纠正可撤销」的审计依据）。
        assert [entry["reason"] for entry in admitted.record.transition_history] == [
            "T1.evidence_admitted",
            "T2.auto_activated",
        ]

    async def test_single_observation_requires_confirm(self, db_session):
        """1 条 outcome → single_observation → 停在 evidenced，confirm 后 active。"""
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=1)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")

        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "evidenced"  # 不自动激活
        assert admitted.record.evidence_tier == EVIDENCE_TIER_SINGLE

        confirmed = await svc.confirm_patch(user.id, result.record.patch_id, now=_NOW)
        assert confirmed.record.state == "active" and confirmed.record.user_confirmed is True
        assert [entry["reason"] for entry in confirmed.record.transition_history] == [
            "T1.evidence_admitted",
            "T3.user_confirmed_activated",
        ]

    async def test_unresolvable_evidence_rejected(self, db_session):
        """伪造 ref（不存在的 expmem id）→ G1 rejected 终态（审计保留）。"""
        user = await _make_user(db_session)
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="granularity",
            payload={"adjustment": "finer"},
            evidence_refs=["memory://experience/expmem_0000000000000bad"],
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "rejected"
        assert any(r.startswith("G1.no_resolved_evidence") for r in admitted.reasons)
        # 终态不可复活
        again = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert again.record.state == "rejected" and "T6" in again.reasons[0]

    async def test_direction_mismatch_rejected(self, db_session):
        """prefer patch 引用的记录只有负向证据 → G3（相关性方向不是自报的）。"""
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="remind", mode=ExecutionMode.AGENT, n_negative=2)
        record_id = await _experience_record_id(db_session, user, intervention_type="remind")

        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "remind", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "rejected"
        assert any(r.startswith("G3.evidence_direction_mismatch") for r in admitted.reasons)

    async def test_no_outcome_record_is_not_evidence(self, db_session):
        """只有 exposure 无 outcome 的 M-06 记录不构成证据（M-06 红线 1 同律）。"""
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=0)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")

        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "rejected"
        assert any(r.startswith("G1") for r in admitted.reasons)

    async def test_decision_ref_resolves_against_d05_rows(self, db_session):
        """decision:// ref 对 D-05 outcome_observed 行核验（第二真源通道）。"""
        user = await _make_user(db_session)
        decision_id = await _expose_and_link(
            db_session,
            user,
            intervention_type="explain",
            mode=ExecutionMode.AGENT,
            n_positive=2,
            goal="project",
            evidence=(),
        )

        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="explanation",
            payload={"style": "examples_first"},
            evidence_refs=[f"decision://{decision_id}"],
        )
        assert result.record is not None
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "active"
        assert admitted.record.evidence_tier == EVIDENCE_TIER_REPEATED


# ---------------------------------------------------------------------------
# 3. ranking 改变 + evidence refs（验收 ③；同 scope 真实证据链）
# ---------------------------------------------------------------------------


class TestRankingWithRealEvidence:
    async def _active_prefer_practice(self, db_session, user):
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=2)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "active"
        return svc, admitted.record

    async def test_same_scope_history_changes_ranking_with_evidence_refs(self, db_session):
        """同 scope（exam+cognitive_overload）practice 2 正向 → 提名重排到首。"""
        user = await _make_user(db_session)
        svc, patch = await self._active_prefer_practice(db_session, user)

        inputs = await svc.patched_decision_inputs(
            user.id,
            ("explain", "practice"),
            goal_type="exam",
            friction_tag="cognitive_overload",
            now=_NOW,
        )
        # 重排：practice 升至首位（explain 让位——A-02 D1 取第一个合法提名）
        assert inputs.nominated[0] == "practice"
        assert "explain" in inputs.nominated
        # 归因：哪个 patch、动了谁、证据 refs（memory://experience/…，A-01 合法 scheme）
        assert inputs.moves and inputs.moves[0].patch_id == patch.patch_id
        assert inputs.moves[0].intervention == "practice" and inputs.moves[0].direction == "prefer"
        assert inputs.evidence_refs and all(
            ref.startswith("memory://experience/expmem_") for ref in inputs.evidence_refs
        )
        assert patch.patch_id in inputs.applied_patch_ids

    async def test_patched_nominees_flow_through_a02_and_a01_contract(self, db_session):
        """全链路：重排提名 → A-02 选中 practice → A-01 契约 evidence_refs 合法。"""
        from app.aurora.intervention_policy import (
            InterventionPolicyFactors,
            build_decision_contract,
            evaluate_intervention_policy,
        )
        from app.core.aurora_decision import AURORA_DECISION_REF_SCHEMES

        user = await _make_user(db_session)
        svc, _ = await self._active_prefer_practice(db_session, user)
        inputs = await svc.patched_decision_inputs(
            user.id, ("explain", "practice"), goal_type="exam", friction_tag="cognitive_overload", now=_NOW
        )

        evaluation = evaluate_intervention_policy(
            InterventionPolicyFactors(
                nominated=inputs.nominated,
                has_task_context=True,
                allocation_mode="hybrid",
                capabilities={"chat", "llm_generate", "task_write", "plan_adjust"},
                permissions={"chat", "llm_generate", "task_write", "plan_adjust"},
            )
        )
        assert evaluation.selected == "practice"  # patch 决定的排序被 A-02 采纳
        contract, violations = build_decision_contract(
            evaluation,
            user.id,
            cognition_tier="l2_intervention",
            evidence_refs=inputs.evidence_refs,
        )
        assert contract is not None, violations
        assert contract.validate() == ()
        assert all(ref.split("://", 1)[0] in AURORA_DECISION_REF_SCHEMES for ref in contract.evidence_refs)
        # 归因随行：patch 版本可并入契约 annotations（A-01 annotations 自由面）
        merged_annotations = {**contract.annotations, **inputs.annotations()}
        assert merged_annotations["policy_patch_version"] == inputs.policy_patch_version

    async def test_scope_mismatch_does_not_rank(self, db_session):
        """patch 无 scope 约束时证据面按情境过滤：不同 goal 的情境不受影响。

        P3-8（R2）：goal 用词表真值（exam vs project）——词表外值（如
        coursework）会被 D-05 归一为 unknown，测的实际是 unknown 错配。
        """
        user = await _make_user(db_session)
        svc, _ = await self._active_prefer_practice(db_session, user)  # 证据在 exam 切片
        # 情境 = project（词表真值；无该 scope 的正向证据记录）→ 不重排
        inputs = await svc.patched_decision_inputs(
            user.id, ("explain", "practice"), goal_type="project", friction_tag="cognitive_overload", now=_NOW
        )
        assert inputs.nominated == ("explain", "practice")  # 无 move
        assert inputs.moves == ()

    async def test_patch_cannot_make_illegal_intervention_legal(self, db_session):
        """patch 只调序不越守卫：无任务锚点时 practice 仍被 R3 剔除 → no_action。"""
        from app.aurora.intervention_policy import InterventionPolicyFactors, evaluate_intervention_policy

        user = await _make_user(db_session)
        svc, _ = await self._active_prefer_practice(db_session, user)
        inputs = await svc.patched_decision_inputs(
            user.id, ("explain", "practice"), goal_type="exam", friction_tag="cognitive_overload", now=_NOW
        )
        evaluation = evaluate_intervention_policy(
            InterventionPolicyFactors(nominated=inputs.nominated, has_task_context=False)  # 缺任务锚点
        )
        assert evaluation.selected == "no_action"  # 结构性守卫不被 patch 绕过


# ---------------------------------------------------------------------------
# 4. revoke 即时生效（验收 ②）
# ---------------------------------------------------------------------------


class TestRevokeImmediate:
    async def test_revoke_excludes_from_same_scope_decisions_immediately(self, db_session):
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=2)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        patch_id = result.record.patch_id
        admitted = await svc.admit_evidence(user.id, patch_id, now=_NOW)
        assert admitted.record.state == "active"

        before = await svc.patched_decision_inputs(
            user.id, ("explain", "practice"), goal_type="exam", friction_tag="cognitive_overload", now=_NOW
        )
        assert before.nominated[0] == "practice" and patch_id in before.applied_patch_ids

        revoked = await svc.revoke_patch(user.id, patch_id, reason="user_correction", now=_NOW)
        assert revoked.record.state == "revoked"

        after = await svc.patched_decision_inputs(
            user.id, ("explain", "practice"), goal_type="exam", friction_tag="cognitive_overload", now=_NOW
        )
        # 同 scope 决策不再引用该 patch：排序回基线、归因排除、版本已变
        assert after.nominated == ("explain", "practice")
        assert patch_id not in after.applied_patch_ids
        assert after.moves == ()
        assert after.policy_patch_version != before.policy_patch_version
        # 审计：T4 条目 + revoke_reason 永久保留（P2-2：有序全史 [T1,T2,T4]，
        # 长度与序列钉死——重写为仅末条目的变异在此必红）
        assert [entry["reason"] for entry in revoked.record.transition_history] == [
            "T1.evidence_admitted",
            "T2.auto_activated",
            "T4.revoked_by_user_correction",
        ]
        assert revoked.record.revoke_reason == "user_correction"
        # revoked 是终态：confirm/re-admit 均拒绝
        assert (await svc.confirm_patch(user.id, patch_id, now=_NOW)).reasons[0].startswith("T6")

    async def test_revoke_from_evidenced_state(self, db_session):
        """evidenced（待确认）态也可被用户纠正撤销。"""
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=1)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "evidenced"
        revoked = await svc.revoke_patch(user.id, result.record.patch_id, now=_NOW)
        assert revoked.record.state == "revoked"


# ---------------------------------------------------------------------------
# 5. 版本与缓存失效（验收 ④）
# ---------------------------------------------------------------------------


class TestVersionCacheInvalidation:
    async def test_version_bump_invalidates_inputs_cache(self, db_session):
        """revoke → 版本 bump → 进程缓存不命中（重算；变异：忽略版本比对必红）。"""
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=2)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)

        args = {"goal_type": "exam", "friction_tag": "cognitive_overload", "now": _NOW}
        first = await svc.patched_decision_inputs(user.id, ("explain", "practice"), **args)
        assert first.nominated[0] == "practice"
        assert len(PolicyPatchService._inputs_cache) == 1  # 已入缓存

        await svc.revoke_patch(user.id, result.record.patch_id, now=_NOW)
        second = await svc.patched_decision_inputs(user.id, ("explain", "practice"), **args)
        assert second.nominated == ("explain", "practice")  # 缓存未命中 → 重算 → 无 patch
        assert second.policy_patch_version != first.policy_patch_version

    def test_cache_get_version_mismatch_returns_none(self):
        from app.services.policy_patch_service import PatchedDecisionInputs

        PolicyPatchService.reset_cache()
        key = "a05:inputs:test"
        inputs = PatchedDecisionInputs(nominated=("a",), policy_patch_version="polpatch_v1")
        PolicyPatchService._cache_put(key, "polpatch_v1", inputs)
        assert PolicyPatchService._cache_get(key, "polpatch_v1") is inputs  # 版本一致命中
        assert PolicyPatchService._cache_get(key, "polpatch_v2") is None  # 版本 bump → 不命中

    async def test_version_empty_without_active_patches(self, db_session):
        from app.core.policy_patch import POLICY_PATCH_EMPTY_VERSION

        user = await _make_user(db_session)
        svc = PolicyPatchService(db_session)
        assert await svc.policy_version(user.id, now=_NOW) == POLICY_PATCH_EMPTY_VERSION

    async def test_expiry_read_time_gate_and_sweep(self, db_session):
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=2)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
            expires_at=_NOW + timedelta(hours=1),
        )
        await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert (await svc.effective_patches(user.id, now=_NOW)) != ()

        later = _NOW + timedelta(hours=2)
        # 读时门：过期即刻排除（无需先 sweep）；读取顺手把状态收敛为 expired
        assert await svc.effective_patches(user.id, now=later) == ()
        inputs = await svc.patched_decision_inputs(
            user.id, ("explain", "practice"), goal_type="exam", friction_tag="cognitive_overload", now=later
        )
        assert inputs.nominated == ("explain", "practice")
        refreshed = await svc._get_by_patch_id(result.record.patch_id)
        assert refreshed.state == "expired"  # 读路径已收敛持久状态
        # sweep 幂等：已收敛后重跑为 0（可安全重复）
        assert await svc.expire_sweep(user.id, now=later) == 0


# ---------------------------------------------------------------------------
# 6. 非重排面：allocation/proactive/explanation + 用户隔离
# ---------------------------------------------------------------------------


class TestNonRankingSurfaces:
    async def test_allocation_preference_feeds_x02_factor(self, db_session):
        """prefer_agent patch → AllocationFactors.user_preference（X-02 既有入参）。"""
        from app.services.action_allocation_policy import AllocationFactors, decide_allocation

        user = await _make_user(db_session)
        # agent 执行的历史干预 + 2 正向（真实证据：execution_mode=agent 切片）
        await _expose_and_link(db_session, user, intervention_type="execute", mode=ExecutionMode.AGENT, n_positive=2)
        projection = await ExperienceMemoryProjector(db_session).project(user_id=user.id, now=_NOW)
        agent_record = next(
            r for r in projection.records if r.execution_mode == "agent" and r.has_positive_association_evidence
        )

        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="allocation_preference",
            payload={"preference": "prefer_agent"},
            evidence_refs=[f"memory://experience/{agent_record.record_id}"],
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "active"

        inputs = await svc.patched_decision_inputs(user.id, ("explain",), now=_NOW)
        assert inputs.allocation_user_preference == "prefer_agent"

        # X-02 消费（既有入参面）：偏好出现在分配归因（agent 在可行集内时 U1 命中）
        allocation = decide_allocation(
            AllocationFactors(user_preference=inputs.allocation_user_preference, tool_advantage="high")
        )
        assert "U1.user_preference_agent" in allocation.why
        assert allocation.mode == "agent"

    async def test_allocation_preference_cannot_bypass_joint_constraints(self, db_session):
        """偏好不高于结构边界：prefer_agent 使分配为 agent，但 practice 步绑定
        hybrid——A-02 R5 在政策面确定性剔除，patch 无法把非法组合变合法。"""
        from app.aurora.intervention_policy import InterventionPolicyFactors
        from app.aurora.joint_decision import decide_joint
        from app.services.action_allocation_policy import AllocationFactors, decide_allocation

        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="execute", mode=ExecutionMode.AGENT, n_positive=2)
        projection = await ExperienceMemoryProjector(db_session).project(user_id=user.id, now=_NOW)
        agent_record = next(
            r for r in projection.records if r.execution_mode == "agent" and r.has_positive_association_evidence
        )
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="allocation_preference",
            payload={"preference": "prefer_agent"},
            evidence_refs=[f"memory://experience/{agent_record.record_id}"],
        )
        await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        inputs = await svc.patched_decision_inputs(user.id, ("practice",), now=_NOW)

        # 偏好经既有入参进入 X-02 → 分配为 agent（学习守卫未触发的常规步）
        task_factors = AllocationFactors(user_preference=inputs.allocation_user_preference, tool_advantage="high")
        allocation = decide_allocation(task_factors)
        assert allocation.mode == "agent"

        joint = decide_joint(
            InterventionPolicyFactors(
                nominated=("practice",),
                has_task_context=True,
                capabilities={"llm_generate"},
            ),
            allocation,
        )
        # practice 步绑定 hybrid 交付（A-04 J1）；agent 分配下被联合层确定性
        # 剔除——偏好经 X-02 既有入参进入，但不可越联合约束层
        assert joint.selected != "practice"
        assert any(
            entry.reason == "J1.delivery_mode_incompatible" and entry.target == "practice" for entry in joint.exclusions
        )

    async def test_proactive_cadence_minimal_gate_override(self, db_session):
        user = await _make_user(db_session)
        # remind 族 2 条负向（被打扰的真实代价）→ minimal cadence patch 过门
        await _expose_and_link(db_session, user, intervention_type="remind", mode=ExecutionMode.AGENT, n_negative=2)
        record_id = await _experience_record_id(db_session, user, intervention_type="remind")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="proactive_cadence",
            payload={"cadence": "minimal"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "active"
        inputs = await svc.patched_decision_inputs(user.id, ("explain",), now=_NOW)
        assert inputs.proactive_gate_overrides == {"proactive_budget_available": False}
        # A-02 消费：proactive 干预被 R9 剔除（显式请求仍可豁免——X1 不变）
        from app.aurora.intervention_policy import InterventionPolicyFactors, evaluate_intervention_policy

        remind_factors = {
            "nominated": ("remind",),
            "has_task_context": True,
            "capabilities": {"scheduler"},
            "permissions": {"proactive_contact"},
        }
        suppressed = evaluate_intervention_policy(
            InterventionPolicyFactors(
                **remind_factors,
                proactive_budget_available=inputs.proactive_gate_overrides["proactive_budget_available"],
            )
        )
        assert "R9.proactive_budget_exhausted" in [reason for _, reason in suppressed.exclusions if _ == "remind"]
        explicit = evaluate_intervention_policy(
            InterventionPolicyFactors(
                **remind_factors,
                proactive_budget_available=False,
                explicit_user_request=True,
            )
        )
        assert explicit.selected == "remind"  # 用户主权不受 patch 压制

    async def test_explanation_style_surface(self, db_session):
        user = await _make_user(db_session)
        await _expose_and_link(
            db_session,
            user,
            intervention_type="explain",
            mode=ExecutionMode.AGENT,
            n_positive=2,
            goal="project",
            evidence=(),
        )
        projection = await ExperienceMemoryProjector(db_session).project(user_id=user.id, now=_NOW)
        record = next(r for r in projection.records if r.intervention == "explain")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="explanation",
            payload={"style": "examples_first"},
            evidence_refs=[f"memory://experience/{record.record_id}"],
        )
        await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        inputs = await svc.patched_decision_inputs(user.id, ("explain",), now=_NOW)
        assert inputs.explanation_style == "examples_first"
        assert inputs.annotations()["policy_patch_version"].startswith("polpatch_")

    async def test_user_isolation(self, db_session):
        user_a = await _make_user(db_session)
        user_b = await _make_user(db_session)
        await _expose_and_link(
            db_session, user_a, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=2
        )
        record_id = await _experience_record_id(db_session, user_a, intervention_type="practice")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user_a.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        await svc.admit_evidence(user_a.id, result.record.patch_id, now=_NOW)

        inputs_b = await svc.patched_decision_inputs(
            user_b.id, ("explain", "practice"), goal_type="exam", friction_tag="cognitive_overload", now=_NOW
        )
        assert inputs_b.nominated == ("explain", "practice")  # B 不受 A 的 patch 影响
        assert inputs_b.applied_patch_ids == ()


# ---------------------------------------------------------------------------
# 7. P2-1（R2 PROBE_A）：scope 对三个非重排面的绑定语义
# ---------------------------------------------------------------------------


class TestScopedNonRankingSurfaces:
    """exam-scoped 的因子面 patch 在 project 情境**零影响**、exam 情境生效。

    R2 实测缺陷（PROBE_A）：`patched_decision_inputs` 曾把未过 scope 的全量
    effective 集直接喂给三个因子投影——「只在考试周偏好 agent 执行」会泄漏到
    所有情境。修复后因子投影与提名重排共用同一 `scope_matches` 谓词；本组
    测试双向钉死（非匹配情境 → None/{} + 匹配情境 → 生效）。
    """

    async def _scoped_active_patch(
        self,
        db_session,
        user,
        *,
        surface: str,
        payload: dict,
        intervention_type: str,
        mode: ExecutionMode,
        n_positive: int = 2,
        n_negative: int = 0,
    ) -> tuple[PolicyPatchService, object]:
        """激活一条 exam-scoped patch（证据同 scope：P3-4 门要求同切片支撑）。"""
        await _expose_and_link(
            db_session,
            user,
            intervention_type=intervention_type,
            mode=mode,
            n_positive=n_positive,
            n_negative=n_negative,
            goal="exam",
        )
        record_id = await _experience_record_id(db_session, user, intervention_type=intervention_type, goal="exam")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface=surface,
            payload=payload,
            evidence_refs=[f"memory://experience/{record_id}"],
            scope_goal_type="exam",
        )
        assert result.record is not None, result.reasons
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "active", admitted.reasons
        return svc, admitted.record

    async def test_scoped_allocation_preference_binds_to_goal_scope(self, db_session):
        """PROBE_A 原场景：exam-scoped prefer_agent 不泄漏到 project 情境。"""
        user = await _make_user(db_session)
        svc, _ = await self._scoped_active_patch(
            db_session,
            user,
            surface="allocation_preference",
            payload={"preference": "prefer_agent"},
            intervention_type="execute",
            mode=ExecutionMode.AGENT,
        )
        in_exam = await svc.patched_decision_inputs(user.id, ("explain",), goal_type="exam", now=_NOW)
        assert in_exam.allocation_user_preference == "prefer_agent"  # 匹配情境生效
        in_project = await svc.patched_decision_inputs(user.id, ("explain",), goal_type="project", now=_NOW)
        assert in_project.allocation_user_preference is None  # 非匹配情境零影响
        assert in_project.proactive_gate_overrides == {} and in_project.explanation_style is None

    async def test_scoped_proactive_cadence_binds_to_goal_scope(self, db_session):
        """「只在考试周别主动打扰我」不在 project 情境关掉 proactive 预算。"""
        user = await _make_user(db_session)
        svc, _ = await self._scoped_active_patch(
            db_session,
            user,
            surface="proactive_cadence",
            payload={"cadence": "minimal"},
            intervention_type="remind",
            mode=ExecutionMode.AGENT,
            n_positive=0,
            n_negative=2,
        )
        in_exam = await svc.patched_decision_inputs(user.id, ("explain",), goal_type="exam", now=_NOW)
        assert in_exam.proactive_gate_overrides == {"proactive_budget_available": False}
        in_project = await svc.patched_decision_inputs(user.id, ("explain",), goal_type="project", now=_NOW)
        assert in_project.proactive_gate_overrides == {}  # project 情境预算不受考试周偏好压制

    async def test_scoped_explanation_style_binds_to_goal_scope(self, db_session):
        user = await _make_user(db_session)
        svc, _ = await self._scoped_active_patch(
            db_session,
            user,
            surface="explanation",
            payload={"style": "examples_first"},
            intervention_type="explain",
            mode=ExecutionMode.AGENT,
        )
        in_exam = await svc.patched_decision_inputs(user.id, ("explain",), goal_type="exam", now=_NOW)
        assert in_exam.explanation_style == "examples_first"
        in_project = await svc.patched_decision_inputs(user.id, ("explain",), goal_type="project", now=_NOW)
        assert in_project.explanation_style is None


# ---------------------------------------------------------------------------
# 8. P3-4（R2 PROBE_C）：admit 门的 patch scope × 证据 scope 一致性
# ---------------------------------------------------------------------------


class TestAdmitScopeConsistency:
    """exam-scoped patch 只接受 exam 切片证据；跨 scope 证据 → G1 rejected。

    无此门时 exam patch 用 project 证据即可激活（R2 PROBE_C 实测 active）——
    scope 维度全程装饰性。修复后两通道（memory:// / decision://）同律。
    """

    async def test_cross_scope_memory_evidence_rejected(self, db_session):
        """PROBE_C 钉死：exam-scoped patch + project 切片正向证据 → G1。

        无 scope 一致性门时该证据全绿（resolved=2、方向正、档位 repeated）。
        """
        user = await _make_user(db_session)
        await _expose_and_link(
            db_session, user, intervention_type="execute", mode=ExecutionMode.AGENT, n_positive=2, goal="project"
        )
        record_id = await _experience_record_id(db_session, user, intervention_type="execute", goal="project")

        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="allocation_preference",
            payload={"preference": "prefer_agent"},
            evidence_refs=[f"memory://experience/{record_id}"],
            scope_goal_type="exam",
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "rejected"
        assert any(r.startswith("G1.no_resolved_evidence") for r in admitted.reasons)

    async def test_cross_scope_decision_evidence_rejected(self, db_session):
        """decision:// 通道同律：project 情境的 outcome 不支撑 exam-scoped patch。"""
        user = await _make_user(db_session)
        decision_id = await _expose_and_link(
            db_session,
            user,
            intervention_type="explain",
            mode=ExecutionMode.AGENT,
            n_positive=2,
            goal="project",
            evidence=(),
        )
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="explanation",
            payload={"style": "examples_first"},
            evidence_refs=[f"decision://{decision_id}"],
            scope_goal_type="exam",
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "rejected"
        assert any(r.startswith("G1.no_resolved_evidence") for r in admitted.reasons)

    async def test_same_scope_decision_evidence_admits(self, db_session):
        """正控制：exam 情境的 decision 证据支撑 exam-scoped patch（不过拒）。"""
        user = await _make_user(db_session)
        decision_id = await _expose_and_link(
            db_session,
            user,
            intervention_type="explain",
            mode=ExecutionMode.AGENT,
            n_positive=2,
            goal="exam",
            evidence=(),
        )
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="explanation",
            payload={"style": "examples_first"},
            evidence_refs=[f"decision://{decision_id}"],
            scope_goal_type="exam",
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "active", admitted.reasons
        inputs = await svc.patched_decision_inputs(user.id, ("explain",), goal_type="exam", now=_NOW)
        assert inputs.explanation_style == "examples_first"

    async def test_tier_counts_only_in_scope_rows(self, db_session):
        """DELTA-1 钉死：档位只计过滤后（scope 全过）的有效观察数。

        exam-scoped patch 配 [exam×1, project×1] 混合 refs：跨 scope 行不得
        把单条同 scope 观察顶到 repeated 绕过用户确认门（旧代码取未过滤
        len(rows)=2 → repeated → 自动激活）。修复后 resolved=1 → single 档
        → 停 evidenced 待 confirm。"""
        user = await _make_user(db_session)
        await _expose_and_link(
            db_session, user, intervention_type="execute", mode=ExecutionMode.AGENT, n_positive=1, goal="exam"
        )
        await _expose_and_link(
            db_session, user, intervention_type="execute", mode=ExecutionMode.AGENT, n_positive=1, goal="project"
        )
        exam_id = await _experience_record_id(db_session, user, intervention_type="execute", goal="exam")
        project_id = await _experience_record_id(db_session, user, intervention_type="execute", goal="project")

        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="allocation_preference",
            payload={"preference": "prefer_agent"},
            evidence_refs=[f"memory://experience/{exam_id}", f"memory://experience/{project_id}"],
            scope_goal_type="exam",
        )
        admitted = await svc.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "evidenced", admitted.reasons


# ---------------------------------------------------------------------------
# 9. P2-2（R2 M8）：transition_history append-only 全史钉死
# ---------------------------------------------------------------------------


class TestTransitionHistoryAppendOnly:
    """审计依据是**有序全史**：长度单调不减 + 早期条目逐字节不可变。

    M8 变异（``_apply`` 把 append 改写为重写 ``[entry]``）在 R2 复演时 25/25
    全绿——当时所有断言都是 any()。本组按「每步迁移后取快照」钉死前缀保持
    与长度单调；重写/丢早期条目在此必红。
    """

    async def _single_tier_patch(self, db_session, user):
        """1 条正向 outcome → single_observation → 停在 evidenced（待 confirm）。"""
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=1)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        return svc, result.record.patch_id

    async def test_history_grows_monotonically_and_early_entries_immutable(self, db_session):
        user = await _make_user(db_session)
        svc, patch_id = await self._single_tier_patch(db_session, user)

        admitted = await svc.admit_evidence(user.id, patch_id, now=_NOW)
        assert [e["reason"] for e in admitted.record.transition_history] == ["T1.evidence_admitted"]
        snapshot_after_admit = [dict(e) for e in admitted.record.transition_history]

        confirmed = await svc.confirm_patch(user.id, patch_id, now=_NOW)
        history_after_confirm = list(confirmed.record.transition_history)
        assert len(history_after_confirm) == 2  # 长度单调 +1，非重写
        assert history_after_confirm[0] == snapshot_after_admit[0]  # 早期条目不可变
        assert history_after_confirm[1]["reason"] == "T3.user_confirmed_activated"
        snapshot_after_confirm = [dict(e) for e in history_after_confirm]

        revoked = await svc.revoke_patch(user.id, patch_id, now=_NOW)
        history_after_revoke = list(revoked.record.transition_history)
        assert len(history_after_revoke) == 3
        assert history_after_revoke[:2] == snapshot_after_confirm  # 前缀保持
        assert history_after_revoke[2]["reason"] == "T4.revoked_by_user_correction"
        # 迁移链自洽：from = 前一条 to；全史覆盖 candidate→evidenced→active→revoked
        states = [history_after_revoke[0]["from"], *(e["to"] for e in history_after_revoke)]
        assert states == ["candidate", "evidenced", "active", "revoked"]

    async def test_audit_entries_carry_full_fields(self, db_session):
        """每条审计条目带完整 {at, action, from, to, reason, actor}（可审计面）。"""
        user = await _make_user(db_session)
        svc, patch_id = await self._single_tier_patch(db_session, user)
        await svc.admit_evidence(user.id, patch_id, now=_NOW)
        confirmed = await svc.confirm_patch(user.id, patch_id, now=_NOW)
        for entry in confirmed.record.transition_history:
            assert set(entry) == {"at", "action", "from", "to", "reason", "actor"}
            assert entry["at"] == _NOW.isoformat()


# ---------------------------------------------------------------------------
# 10. P3-6（R2 M7）：终态不可复活——幂等 re-propose 不动终态行
# ---------------------------------------------------------------------------


class TestTerminalStateNotResurrected:
    """revoke 后同内容 re-propose 返回终态行**原样**（M7 变异：幂等分支把
    state 复活为 candidate —— R2 复演 67/67 全绿无测试锁；本组钉死）。"""

    async def test_repropose_after_revoke_returns_terminal_row_unchanged(self, db_session):
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=2)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        svc = PolicyPatchService(db_session)
        args = {
            "surface": "intervention_preference",
            "payload": {"intervention": "practice", "direction": "prefer"},
            "evidence_refs": [f"memory://experience/{record_id}"],
        }
        first = await svc.propose_patch(user.id, **args)
        await svc.admit_evidence(user.id, first.record.patch_id, now=_NOW)
        revoked = await svc.revoke_patch(user.id, first.record.patch_id, now=_NOW)
        assert revoked.record.state == "revoked"
        history_len = len(revoked.record.transition_history)

        # 同内容 re-propose：内容寻址命中既有行 → 幂等返回，**不复活**
        reproposed = await svc.propose_patch(user.id, **args)
        assert reproposed.idempotent is True
        assert reproposed.record.patch_id == first.record.patch_id
        assert reproposed.record.state == "revoked"  # 终态保持（M7 变异在此红）
        assert reproposed.record.revoked_at == revoked.record.revoked_at
        assert len(reproposed.record.transition_history) == history_len  # 审计不动
        assert await _patch_count(db_session, user) == 1  # 不双写
        # 复活需新 patch：新内容 → 新 patch_id 新行（M-01 supersede 哲学）
        successor = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=["decision://aurora_" + "2" * 32],
        )
        assert successor.idempotent is False and successor.record.patch_id != first.record.patch_id
        assert successor.record.state == "candidate"


# ---------------------------------------------------------------------------
# 11. P2-3（R2）：_apply 并发守卫——迟到的迁移对终态让位（零写、不丢审计）
# ---------------------------------------------------------------------------


class TestApplyConcurrencyGuard:
    """构造性交错测试：另一事务的 revoke 已提交后，迟到的 confirm 让位。

    sqlite 单连接无真并发，以直接 SQL 提交「并发 revoke」终局模拟 R2 指出的
    交错（revoke 提交先落、activate 后到覆盖 → 终态 active + T4 审计丢失）。
    `_apply` 写前 ``FOR UPDATE`` 重读 + ``populate_existing``（PG 生效行锁；
    sqlite 下重读语义不变）→ 见 revoked → confirm 非法（T6）→ 不覆盖、不丢审计。
    """

    async def test_apply_yields_to_concurrent_terminal_transition(self, db_session):
        from sqlalchemy import update

        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=1)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        patch_id = result.record.patch_id
        admitted = await svc.admit_evidence(user.id, patch_id, now=_NOW)
        assert admitted.record.state == "evidenced"
        stale = await svc._get_by_patch_id(patch_id)  # 调用方快照（state=evidenced）

        # 模拟并发事务已提交 revoke（绕过 ORM 对象直写行 + 追加 T4 审计）
        concurrent_t4 = {
            "at": _NOW.isoformat(),
            "action": "revoke",
            "from": "evidenced",
            "to": "revoked",
            "reason": "T4.revoked_by_user_correction",
            "actor": "user",
        }
        await db_session.execute(
            update(PolicyPatchRecord)
            .where(PolicyPatchRecord.id == stale.id)
            .values(state="revoked", transition_history=[concurrent_t4])
        )
        await db_session.commit()

        # 迟到的 confirm（持陈旧 evidenced 快照）：让位而非覆盖
        outcome = await svc._apply(stale, "confirm", _NOW, actor="user")
        assert outcome.transitioned is False
        assert outcome.reasons == ("T6.illegal_transition",)

        fresh = (
            (
                await db_session.execute(
                    select(PolicyPatchRecord)
                    .where(PolicyPatchRecord.id == stale.id)
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .one()
        )
        assert fresh.state == "revoked"  # 终态未被覆盖
        assert list(fresh.transition_history) == [concurrent_t4]  # 审计零丢失（无伪造 T3）

    async def test_t6_rejection_leaves_no_side_column_traces(self, db_session, monkeypatch):
        """DELTA-3 钉死：陈旧 evidenced 快照的迟到 confirm 走到 _apply 锁下
        才见 revoked（T6 让位）——结构性根治下旁列（user_confirmed/
        confirmed_at/activated_at）只在迁移成功后赋值，revoked 行零激活痕迹。
        变异（旁列赋值恢复到 _apply 之前）时 autoflush 落痕迹 → 本测试红。"""
        from sqlalchemy import update

        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", mode=ExecutionMode.HYBRID, n_positive=1)
        record_id = await _experience_record_id(db_session, user, intervention_type="practice")
        svc = PolicyPatchService(db_session)
        result = await svc.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "practice", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        patch_id = result.record.patch_id
        admitted = await svc.admit_evidence(user.id, patch_id, now=_NOW)
        assert admitted.record.state == "evidenced"
        stale = await svc._get_by_patch_id(patch_id)  # evidenced 快照

        # 并发 revoke 以直接 SQL 落库（同事务内对后续 FOR UPDATE 可见），
        # **不 commit**——保持 stale 不过期，L401 的快照检查读到 evidenced，
        # 完整复现「调用方持陈旧快照越过前置检查」的竞态时序。
        concurrent_t4 = {
            "at": _NOW.isoformat(),
            "action": "revoke",
            "from": "evidenced",
            "to": "revoked",
            "reason": "T4.revoked_by_user_correction",
            "actor": "user",
        }
        await db_session.execute(
            update(PolicyPatchRecord)
            .where(PolicyPatchRecord.id == stale.id)
            .values(state="revoked", transition_history=[concurrent_t4])
        )

        # 陈旧快照注入（复现并发时序：调用方在 revoke 落库前已读到 evidenced）
        async def stale_get(pid):
            return stale

        monkeypatch.setattr(svc, "_get_by_patch_id", stale_get)
        result = await svc.confirm_patch(user.id, patch_id, now=_NOW)
        assert "T6" in result.reasons[0]
        # 结构不变式（DELTA-3）：拒绝路径上旁列从未被赋值——对象级断言
        # 不依赖 DB autoflush 机制（测试 fixture autoflush=False，生产为
        # True；变异恢复前置赋值时对象带脏、本断言红）。
        assert result.record.user_confirmed is not True
        assert result.record.activated_at is None
        assert result.record.confirmed_at is None

        fresh = (
            (
                await db_session.execute(
                    select(PolicyPatchRecord)
                    .where(PolicyPatchRecord.id == stale.id)
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .one()
        )
        assert fresh.state == "revoked"
        assert fresh.user_confirmed is not True  # 激活痕迹零残留
        assert fresh.activated_at is None
        assert fresh.confirmed_at is None
        assert list(fresh.transition_history) == [concurrent_t4]
