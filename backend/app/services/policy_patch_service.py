"""A-05 · Policy Patch 服务层 —— 生命周期写路径 + 真源证据门 + 版本化决策输入。

形态（契约 = ``app/core/policy_patch.py``）：

- **propose（fail-closed 写门）**：``propose_patch`` 先过 core
  ``validate_patch_request``——violations 非空 → **零写路径**（不落行、不降级
  为「宽容接受」）；合法才落 ``aurora_policy_patches`` 行（state=candidate，
  patch_id 内容寻址幂等：同内容重提议返回既有行）。
- **admit_evidence（真实证据门，非自报）**：evidence_refs 逐条对真源核验——
  ``memory://experience/<id>`` 对 **M-06 ExperienceMemoryProjector 投影记录**
  （其内即 D-05 ``association_summary`` 的保守统计），``decision://aurora_<id>``
  对 **D-05 ``intervention_lifecycle_events`` 的 outcome_observed 行**。解析
  计数为 0 / 方向不满足 / 档位 insufficient → rejected（G 码，终态留审计）；
  通过 → evidenced，档位 ≥ repeated 自动激活（T2），single_observation 等待
  用户确认（confirm(若需)，T3）。
- **revoke（用户纠正，即时生效 + 审计）**：candidate/evidenced/active →
  revoked（T4）——effective 集**立刻**排除（读路径按 state 过滤，无延迟窗口），
  transition_history append-only 永久保留；revoked 是终态，复活需新 patch
  （M-01 supersede 哲学）。
- **版本与缓存失效（卡面 Work 3）**：``policy_version`` = active 集内容寻址
  （core ``compute_policy_patch_version``）；``patched_decision_inputs`` 进程内
  缓存以 **(输入摘要, policy_version)** 为键——active 集任何变化（激活/撤销/
  过期）→ 版本必然变化 → **缓存不命中**（M-06 (cache_key, watermark) 同款
  契约；消费方自建缓存用 core ``patch_cache_key`` 并入版本）。
- **决策输入集成面**：``patched_decision_inputs`` 产出 A-02 提名重排 + X-02
  allocation 因子 + proactive 门覆盖 + explanation 风格 + 归因 annotations
  （``policy_patch_version`` 进决策载荷；A-01 annotations extend-only 消费）。
  重排证据链来自真实 M-06 投影记录（同 scope 历史），**绝不 mock**。

边界（不重建、不清重）：
- 证据真源：M-06 projector + D-05 lifecycle（本层只读消费；档位判定复用
  D-05 ``association_evidence_tier`` 语义——decision refs 逐条 = 1 观察）；
- A-02：patch 只重排 ``nominated``（feasible set/守卫/inert 地板不变）；
- X-02/A-04：allocation_preference 走 ``AllocationFactors.user_preference``
  既有入参（J 码联合约束照常，学习守卫可压过偏好——偏好不高于结构边界）；
- 词表 39 零新名：零事件、零 outbox、零 registry 变更（审计自包含于行内
  transition_history）。
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.intervention_lifecycle import (
    EVIDENCE_TIER_INSUFFICIENT,
    LifecycleEventType,
    association_evidence_tier,
)
from app.core.policy_patch import (
    ALLOCATION_PREFERENCE_VALUES,
    MEMORY_EVIDENCE_PREFIX,
    POLICY_PATCH_EMPTY_VERSION,
    PolicyPatch,
    RankingMove,
    TransitionOutcome,
    admit_decision,
    apply_transition,
    compute_policy_patch_version,
    derive_policy_patch_id,
    highest_tier,
    may_auto_activate,
    reorder_nominations,
    validate_patch_request,
)
from app.core.policy_patch import (
    allocation_user_preference as _allocation_preference_value,
)
from app.core.policy_patch import (
    explanation_style as _explanation_style_value,
)
from app.core.policy_patch import (
    proactive_gate_overrides as _proactive_overrides,
)
from app.core.time_utils import ensure_naive_utc, utcnow
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.models.policy_patch import PolicyPatchRecord
from app.services.experience_memory_projector import ExperienceMemoryProjector

POLICY_PATCH_SERVICE_VERSION = "aurora_policy_patch_service.a05.v1"

#: X-02 词表互检（import 期 fail-fast）：allocation_preference 值域漂移即红。
from app.services.action_allocation_policy import USER_PREFERENCES as _X02_USER_PREFERENCES

assert set(ALLOCATION_PREFERENCE_VALUES) == set(
    _X02_USER_PREFERENCES
), "ALLOCATION_PREFERENCE_VALUES must exactly mirror X-02 USER_PREFERENCES"

#: 决策输入缓存 TTL（秒）：版本失效主钩 + 时间迁移（过期读时门）兜底。
INPUTS_CACHE_TTL_SECONDS = 120.0
#: 进程内缓存条目上限（per-user 键，LRU 淘汰）。
INPUTS_CACHE_MAX_ENTRIES = 256


def _naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return ensure_naive_utc(value)


# ---------------------------------------------------------------------------
# 证据需求（面的方向语义；纯函数）
# ---------------------------------------------------------------------------


#: 非重排面的证据目标（interventions, required_direction, modes）。
#: proactive_cadence：minimal/reduced 需 remind 族负向共同出现（被打扰的
#: 真实代价）；increased 需正向。allocation_preference：偏好 mode 的正向
#: 共同出现（M-06 记录的 execution_mode 维度）。explanation：explain 正向。
def evidence_requirements_for_patch(patch: PolicyPatch) -> tuple[frozenset[str], str, frozenset[str]] | None:
    """patch → (目标干预集, 所需方向, 目标执行 mode 集)；None = 无需求面。

    返回值语义：patch 要过证据门，须在其目标干预集（可选限定 mode）上存在
    **所需方向**的真实共同出现证据。
    """
    all_modes: frozenset[str] = frozenset({"human", "agent", "hybrid"})
    if patch.surface == "intervention_preference":
        intervention = str(patch.payload.get("intervention", ""))
        direction = str(patch.payload.get("direction", ""))
        if direction not in {"prefer", "demote"}:
            return None
        return (frozenset({intervention}), "positive" if direction == "prefer" else "negative", all_modes)
    if patch.surface == "granularity":
        adjustment = str(patch.payload.get("adjustment", ""))
        target = {"finer": "split", "coarser": "split"}.get(adjustment)
        if target is None:
            return None
        return (frozenset({target}), "positive" if adjustment == "finer" else "negative", all_modes)
    if patch.surface == "clarification":
        mode = str(patch.payload.get("mode", ""))
        target = {"ask_more": "clarify", "ask_less": "clarify"}.get(mode)
        if target is None:
            return None
        return (frozenset({target}), "positive" if mode == "ask_more" else "negative", all_modes)
    if patch.surface == "explanation":
        return (frozenset({"explain"}), "positive", all_modes)
    if patch.surface == "proactive_cadence":
        cadence = str(patch.payload.get("cadence", ""))
        if cadence in {"minimal", "reduced"}:
            return (frozenset({"remind", "connect_peer"}), "negative", all_modes)
        if cadence == "increased":
            return (frozenset({"remind", "connect_peer"}), "positive", all_modes)
        return None
    if patch.surface == "allocation_preference":
        preference = str(patch.payload.get("preference", ""))
        mode_map = {"prefer_agent": "agent", "prefer_human": "human", "prefer_mixed": "hybrid"}
        mode = mode_map.get(preference)
        if mode is None:
            return None
        # 目标干预不限（步绑定族皆可），mode 精确限定。
        return (frozenset(), "positive", frozenset({mode}))
    return None


# ---------------------------------------------------------------------------
# 决策输入集成面（冻结形状）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PatchedDecisionInputs:
    """patch 应用后的决策输入投影（A-02/A-02 因子面 + 归因 + 版本）。

    消费契约（决策环装配处）：
    - ``nominated`` → ``InterventionPolicyFactors.nominated``（重排后序）；
    - ``allocation_user_preference`` → ``AllocationFactors.user_preference``
      （X-02 既有入参；A-04 联合约束照常）；
    - ``proactive_gate_overrides`` → 因子覆盖（如 minimal cadence →
      ``proactive_budget_available=False``；A-02 X1 显式请求豁免不变）；
    - ``annotations()`` → 并入 ``AuroraDecisionContract.annotations``；
    - ``context_component()`` → 并入决策上下文/``input_context_hash`` 输入
      （策略版本是决策输入的一部分——版本变 → 上下文哈希变）。
    """

    nominated: tuple[str, ...]
    policy_patch_version: str
    applied_patch_ids: tuple[str, ...] = ()
    moves: tuple[RankingMove, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    allocation_user_preference: str | None = None
    proactive_gate_overrides: Mapping[str, bool] | None = None
    explanation_style: str | None = None
    skipped: tuple[tuple[str, str], ...] = ()

    def annotations(self) -> dict[str, Any]:
        """决策载荷归因（policy_patch_version + 生效 patch 引用 + 重排归因）。"""
        return {
            "policy_patch_version": self.policy_patch_version,
            "policy_patch_refs": list(self.applied_patch_ids),
            "policy_patch_moves": [
                {
                    "patch_id": move.patch_id,
                    "surface": move.surface,
                    "intervention": move.intervention,
                    "direction": move.direction,
                    "from_rank": move.from_rank,
                    "to_rank": move.to_rank,
                    "evidence_refs": list(move.evidence_refs),
                }
                for move in self.moves
            ],
            "policy_patch_skipped": [{"patch_id": patch_id, "reason": reason} for patch_id, reason in self.skipped],
        }

    def context_component(self) -> dict[str, Any]:
        """决策上下文组件（进 Context 装配与 input_context_hash 输入）。"""
        return {
            "policy_patch_version": self.policy_patch_version,
            "policy_patch_refs": list(self.applied_patch_ids),
            "allocation_user_preference": self.allocation_user_preference,
            "proactive_gate_overrides": dict(self.proactive_gate_overrides or {}),
            "explanation_style": self.explanation_style,
        }


# ---------------------------------------------------------------------------
# 服务
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PatchOpResult:
    """一次 patch 操作的结果（record=None + reasons 非空 = 拒绝/失败；不 raise）。"""

    record: PolicyPatchRecord | None
    reasons: tuple[str, ...]
    idempotent: bool = False


class PolicyPatchService:
    """policy patch 生命周期服务（一个 AsyncSession 一个实例）。"""

    # 进程级决策输入缓存（跨实例共享；(输入摘要, 版本) 键 + TTL）。
    _inputs_cache: OrderedDict[str, tuple[str, PatchedDecisionInputs, float]] = OrderedDict()

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 1. propose（fail-closed 写门 + 内容寻址幂等）
    # ------------------------------------------------------------------

    async def propose_patch(
        self,
        user_id: UUID | str,
        *,
        surface: Any,
        payload: Any,
        evidence_refs: Any,
        provenance: str = "decision_loop",
        scope_goal_type: Any = None,
        scope_friction_tag: Any = None,
        expires_at: datetime | None = None,
        now: datetime | None = None,
    ) -> PatchOpResult:
        """提议 patch（candidate）：violations 非空 → 零写路径（fail-closed）。

        - 白名单/scope/证据 ref 形态/provenance 全在 core 验证；
        - patch_id 内容寻址：同内容重提议幂等返回既有行（idempotent=True）；
        - ``expires_at`` 可选（缺省 = 永不过期，读时门恒放行）。
        """
        refs = tuple(evidence_refs) if isinstance(evidence_refs, (list, tuple)) else ()
        violations = validate_patch_request(
            surface=surface,
            payload=payload,
            evidence_refs=refs,
            scope_goal_type=scope_goal_type,
            scope_friction_tag=scope_friction_tag,
            provenance=provenance,
        )
        if violations:
            return PatchOpResult(None, violations)

        user_uuid = UUID(str(user_id))
        patch_id = derive_policy_patch_id(
            user_id=str(user_uuid),
            surface=str(surface),
            payload=dict(payload),
            evidence_refs=refs,
            scope_goal_type=scope_goal_type,
            scope_friction_tag=scope_friction_tag,
            provenance=provenance,
        )
        existing = await self._get_by_patch_id(patch_id)
        if existing is not None:
            return PatchOpResult(existing, (), idempotent=True)

        record = PolicyPatchRecord(
            user_id=user_uuid,
            patch_id=patch_id,
            surface=str(surface),
            payload=dict(payload),
            scope_goal_type=scope_goal_type,
            scope_friction_tag=scope_friction_tag,
            state="candidate",
            provenance=provenance,
            evidence_refs=list(refs),
            expires_at=_naive(expires_at),
            transition_history=[],
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return PatchOpResult(record, ())

    # ------------------------------------------------------------------
    # 2. admit_evidence（真实证据门）
    # ------------------------------------------------------------------

    async def admit_evidence(
        self,
        user_id: UUID | str,
        patch_id: str,
        *,
        now: datetime | None = None,
    ) -> PatchOpResult:
        """证据门：candidate → evidenced/rejected（+ 档位达标自动激活）。

        证据核验（``_verify_evidence``）只读真源：
        - M-06 ``ExperienceMemoryProjector.project``（内含 D-05 保守摘要）；
        - D-05 ``intervention_lifecycle_events`` 的 ``outcome_observed`` 行。

        结果（G 码封闭；rejected 是终态、审计保留）：
        - 无可解析证据 → G1 rejected；
        - 方向不满足 → G3 rejected；
        - 档位 insufficient → G2 rejected；
        - 通过 → evidenced（T1）；档位 ∈ AUTO_ACTIVATE_TIERS → 连续迁移
          active（T2）；single_observation → 留 evidenced 待 confirm（若需）。
        """
        record = await self._get_by_patch_id(patch_id)
        if record is None or record.user_id != UUID(str(user_id)):
            return PatchOpResult(None, ("T6.illegal_transition",))
        if record.state != "candidate":
            return PatchOpResult(record, ("T6.illegal_transition",))

        now_naive = _naive(now) or utcnow()
        patch = _row_to_patch(record)
        requirements = evidence_requirements_for_patch(patch)
        target_interventions, required_direction, target_modes = requirements or (frozenset(), "positive", frozenset())

        verified = await self._verify_evidence(
            user_id=UUID(str(user_id)),
            patch=patch,
            target_interventions=target_interventions,
            required_direction=required_direction,
            target_modes=target_modes,
            now=now_naive,
        )
        admitted, gate_reasons = admit_decision(
            resolved_ref_count=verified.resolved_ref_count,
            direction_satisfied=verified.direction_satisfied,
            tier=verified.tier,
        )
        if not admitted:
            await self._apply(
                record,
                "admit_evidence",
                now_naive,
                actor="evidence_gate",
                reasons_extra=gate_reasons,
                force_target="rejected",
            )
            return PatchOpResult(record, gate_reasons)

        record.evidence_tier = verified.tier
        record.evidence_verified_at = now_naive
        await self._apply(record, "admit_evidence", now_naive, actor="evidence_gate", reasons_extra=gate_reasons)
        if may_auto_activate(verified.tier):
            await self._apply(record, "auto_activate", now_naive, actor="evidence_gate")
            record.activated_at = now_naive  # DELTA-3：迁移成功后才写旁列
            await self.db.commit()
            logger.info("policy patch {} auto-activated at tier {}", patch_id, verified.tier)
        else:
            logger.info("policy patch {} evidenced at tier {} (awaiting user confirmation)", patch_id, verified.tier)
        return PatchOpResult(record, gate_reasons)

    # ------------------------------------------------------------------
    # 3. confirm（用户确认激活；confirm(若需)）
    # ------------------------------------------------------------------

    async def confirm_patch(
        self,
        user_id: UUID | str,
        patch_id: str,
        *,
        now: datetime | None = None,
    ) -> PatchOpResult:
        """用户确认激活：evidenced → active（T3；single_observation 档的必经路径）。

        DELTA-3（结构性根治）：旁列（user_confirmed/confirmed_at/activated_at）
        只在 ``_apply`` 迁移成功后赋值——拒绝路径（锁下见终态 T6）下旁列
        从未被写，revoked 行零激活痕迹；不依赖 rollback 时机。
        """
        record = await self._get_by_patch_id(patch_id)
        if record is None or record.user_id != UUID(str(user_id)):
            return PatchOpResult(None, ("T6.illegal_transition",))
        if record.state != "evidenced":
            return PatchOpResult(record, ("T6.illegal_transition",))
        now_naive = _naive(now) or utcnow()
        outcome = await self._apply(record, "confirm", now_naive, actor="user")
        if not outcome.transitioned:
            return PatchOpResult(record, outcome.reasons)
        record.user_confirmed = True
        record.confirmed_at = now_naive
        record.activated_at = now_naive
        await self.db.commit()
        await self.db.refresh(record)
        return PatchOpResult(record, ())

    # ------------------------------------------------------------------
    # 4. revoke（用户纠正；即时生效 + 审计）
    # ------------------------------------------------------------------

    async def revoke_patch(
        self,
        user_id: UUID | str,
        patch_id: str,
        *,
        reason: str = "user_correction",
        now: datetime | None = None,
    ) -> PatchOpResult:
        """用户纠正撤销：candidate/evidenced/active → revoked（T4）。

        即时生效：本提交后的任何 ``effective_patches`` / ``policy_version`` /
        ``patched_decision_inputs`` 读取立即排除该 patch（读路径按 state 过滤，
        无延迟窗口；进程缓存经版本 bump 失效）。审计：transition_history 保留
        T4 条目 + revoke_reason；revoked 是终态（复活需新 patch）。
        """
        record = await self._get_by_patch_id(patch_id)
        if record is None or record.user_id != UUID(str(user_id)):
            return PatchOpResult(None, ("T6.illegal_transition",))
        if record.state not in {"candidate", "evidenced", "active"}:
            return PatchOpResult(record, ("T6.illegal_transition",))
        now_naive = _naive(now) or utcnow()
        record.revoked_at = now_naive
        record.revoke_reason = str(reason)[:200]
        await self._apply(record, "revoke", now_naive, actor="user", reasons_extra=())
        return PatchOpResult(record, ())

    # ------------------------------------------------------------------
    # 5. expire（显式 sweep；读时门之外的收敛面）
    # ------------------------------------------------------------------

    async def expire_sweep(
        self,
        user_id: UUID | str,
        *,
        now: datetime | None = None,
    ) -> int:
        """active → expired 收敛（读时门之外的持久化结算；幂等可重跑）。"""
        now_naive = _naive(now) or utcnow()
        rows = list(
            (
                await self.db.execute(
                    select(PolicyPatchRecord).where(
                        PolicyPatchRecord.user_id == UUID(str(user_id)),
                        PolicyPatchRecord.state == "active",
                        PolicyPatchRecord.expires_at.isnot(None),
                        PolicyPatchRecord.expires_at <= now_naive,
                    )
                )
            )
            .scalars()
            .all()
        )
        for record in rows:
            await self._apply(record, "expire", now_naive, actor="system")
        return len(rows)

    # ------------------------------------------------------------------
    # 6. 读面：effective 集 / 版本 / 决策输入
    # ------------------------------------------------------------------

    async def effective_patches(
        self,
        user_id: UUID | str,
        *,
        now: datetime | None = None,
    ) -> tuple[PolicyPatch, ...]:
        """生效 patch 集（state=active 且未过期；过期行顺手收敛为 expired）。"""
        now_naive = _naive(now) or utcnow()
        rows = list(
            (
                await self.db.execute(
                    select(PolicyPatchRecord).where(
                        PolicyPatchRecord.user_id == UUID(str(user_id)),
                        PolicyPatchRecord.state == "active",
                    )
                )
            )
            .scalars()
            .all()
        )
        effective: list[PolicyPatch] = []
        stale = [row for row in rows if row.expires_at is not None and row.expires_at <= now_naive]
        for row in stale:
            await self._apply(row, "expire", now_naive, actor="system")
        for row in rows:
            if row.expires_at is not None and row.expires_at <= now_naive:
                continue
            effective.append(_row_to_patch(row))
        return tuple(sorted(effective, key=lambda p: p.patch_id))

    async def policy_version(
        self,
        user_id: UUID | str,
        *,
        now: datetime | None = None,
    ) -> str:
        """active 集内容寻址版本（空集 = ``polpatch_none`` 常量）。"""
        return compute_policy_patch_version(await self.effective_patches(user_id, now=now))

    async def patched_decision_inputs(
        self,
        user_id: UUID | str,
        nominated: Sequence[str],
        *,
        goal_type: str | None = None,
        friction_tag: str | None = None,
        now: datetime | None = None,
        use_cache: bool = True,
    ) -> PatchedDecisionInputs:
        """patch 应用后的决策输入（A-02 提名重排 + 因子面 + 归因 + 版本）。

        缓存契约：进程内 LRU，键 = (user, 提名摘要, 情境摘要)，命中条件 =
        **存储版本与缓存版本一致** 且未过 TTL——active 集变化（激活/撤销/过期）
        → 版本变 → **缓存不命中**（变异守卫：去掉版本比对必红）。重排证据链
        每次未命中重算时从真实 M-06 投影读取（同 scope 历史有效干预的真实
        证据，非 mock）。
        """
        now_naive = _naive(now) or utcnow()
        nominated_tuple = tuple(str(n) for n in nominated)
        base_key = self._inputs_cache_key(user_id, nominated_tuple, goal_type, friction_tag)
        patches = await self.effective_patches(user_id, now=now_naive)
        version = compute_policy_patch_version(patches)
        if use_cache:
            cached = self._cache_get(base_key, version)
            if cached is not None:
                return cached

        # 同 scope 真实证据：M-06 投影记录（内含 D-05 保守关联摘要）。
        evidence_records = await self._situation_evidence_records(
            user_id=UUID(str(user_id)),
            goal_type=goal_type,
            friction_tag=friction_tag,
            now=now_naive,
        )
        # P2-1（R2 PROBE_A）：**全部消费面**共用同一 scope 谓词——因子投影
        # （allocation/proactive/explanation）与提名重排一致，只看「本情境
        # 生效」的 patch。scope 是绑定语义不是装饰：exam-scoped 的
        # prefer_agent/minimal cadence 在 project 情境必须零影响（否则
        # 「只在考试周」的偏好全局泄漏）。reorder_nominations 内部同谓词
        # 过滤（幂等，双保险）。
        situation_patches = [p for p in patches if p.scope_matches(goal_type=goal_type, friction_tag=friction_tag)]
        ranking = reorder_nominations(
            nominated_tuple,
            patches,
            goal_type=goal_type,
            friction_tag=friction_tag,
            now=now_naive,
            evidence_records=evidence_records,
        )
        inputs = PatchedDecisionInputs(
            nominated=ranking.nominated,
            policy_patch_version=version,
            applied_patch_ids=tuple(p.patch_id for p in patches),
            moves=ranking.moves,
            evidence_refs=ranking.evidence_refs,
            allocation_user_preference=_allocation_preference_value(situation_patches),
            proactive_gate_overrides=_proactive_overrides(situation_patches),
            explanation_style=_explanation_style_value(situation_patches),
            skipped=ranking.skipped,
        )
        if use_cache:
            self._cache_put(base_key, version, inputs)
        return inputs

    # ------------------------------------------------------------------
    # 内部：证据核验（只读真源；M-06 投影 + D-05 lifecycle 行）
    # ------------------------------------------------------------------

    async def _verify_evidence(
        self,
        *,
        user_id: UUID,
        patch: PolicyPatch,
        target_interventions: frozenset[str],
        required_direction: str,
        target_modes: frozenset[str],
        now: datetime,
    ) -> _EvidenceVerification:
        """逐条核验 evidence_refs 对真实证据源（非自报）。

        - ``memory://experience/<id>``：M-06 投影记录 record_id 精确匹配，且
          ``evidence_count > 0``（无 outcome 的记录不构成证据——M-06 红线 1
          的消费侧同律）；
        - ``decision://aurora_<id>``：D-05 ``outcome_observed`` 行精确匹配
          （未删）；
        - 方向/干预/mode 匹配按 ``evidence_requirements_for_patch`` 的需求：
          目标干预集空 = 不限干预（mode 需求仍适用）；mode 集 = 全集 = 不限；
        - **scope 一致性（P3-4，R2 PROBE_C）**：patch 的已约束 scope 维度
          （goal_type/friction_tag）必须与证据的切片维度精确相等——
          exam-scoped patch 用 project 证据不解析（resolved=0 → G1），
          ``memory://`` 与 ``decision://`` 两通道同律。scope 是绑定语义：
          局部偏好必须由**同 scope** 的历史支撑，不接受跨 scope 证据
          （防「全局证据支撑局部偏好」的静默放行）。
        """
        projection = await ExperienceMemoryProjector(self.db).project(user_id=user_id, now=now)
        record_by_id = {record.record_id: record for record in projection.records}

        resolved: int = 0
        direction_hits: int = 0
        tiers: list[str] = []
        decision_ids: list[str] = []

        for ref in patch.evidence_refs:
            if ref.startswith(MEMORY_EVIDENCE_PREFIX):
                record = record_by_id.get(ref[len(MEMORY_EVIDENCE_PREFIX) :])
                if record is None or not record.has_outcome_evidence:
                    continue  # 不解析 / 无方向证据 → 不计入
                if target_interventions and record.intervention not in target_interventions:
                    continue
                # P3-7 上游不变式钉（R2）：``unattributed`` 逃生口看似多孔，但
                # A-01 契约强制 actionable 干预必带 execution_mode、inert 不可
                # exposure——生产写路径下 mode-less 证据结构性不可达。若 A-01
                # 将来放松 mode 强制，此门会静默变虚：届时必须收紧（拒收
                # unattributed）而非依赖本注释。
                if record.execution_mode not in target_modes and record.execution_mode != "unattributed":
                    continue
                signature = record.signature.as_dict()
                if patch.scope_goal_type is not None and signature.get("goal_type") != patch.scope_goal_type:
                    continue  # 证据 scope 与 patch scope 不一致 → 不解析（P3-4）
                if patch.scope_friction_tag is not None and signature.get("friction_tag") != patch.scope_friction_tag:
                    continue
                resolved += 1
                tiers.append(record.completeness_adjusted_strength)
                if required_direction == "positive" and record.has_positive_association_evidence:
                    direction_hits += 1
                if required_direction == "negative" and record.has_negative_association_evidence:
                    direction_hits += 1
            elif ref.startswith("decision://"):
                decision_ids.append(ref[len("decision://") :])

        if decision_ids:
            rows = list(
                (
                    await self.db.execute(
                        select(InterventionLifecycleEvent).where(
                            InterventionLifecycleEvent.not_deleted_filter(),
                            InterventionLifecycleEvent.user_id == user_id,
                            InterventionLifecycleEvent.decision_id.in_(decision_ids),
                            InterventionLifecycleEvent.event_type == LifecycleEventType.OUTCOME_OBSERVED.value,
                        )
                    )
                )
                .scalars()
                .all()
            )
            for row in rows:
                intervention_ok = not target_interventions or row.intervention_type in target_interventions
                mode_ok = (row.execution_mode in target_modes) if row.execution_mode is not None else True
                # scope 一致性（P3-4）：decision:// 通道同律——D-05 行记录时点
                # 固化 goal_type/friction_tag，已约束维度与 patch scope 精确
                # 相等才解析（exam-scoped patch 不接受 project 证据）。
                if patch.scope_goal_type is not None and row.goal_type != patch.scope_goal_type:
                    continue
                if patch.scope_friction_tag is not None and row.friction_tag != patch.scope_friction_tag:
                    continue
                if not (intervention_ok and mode_ok):
                    continue
                resolved += 1
                if required_direction == "positive" and row.outcome_polarity == "positive":
                    direction_hits += 1
                if required_direction == "negative" and row.outcome_polarity == "negative":
                    direction_hits += 1
            if resolved:
                # DELTA-1：档位只计过滤后（scope/intervention/mode 全过）的
                # 有效观察数——未过滤 len(rows) 会让跨 scope 行数把单条同
                # scope 观察顶到 repeated，绕过用户确认门自动激活。
                tiers.append(association_evidence_tier(resolved))

        tier = highest_tier(tiers) if resolved > 0 else EVIDENCE_TIER_INSUFFICIENT
        return _EvidenceVerification(
            resolved_ref_count=resolved,
            direction_satisfied=direction_hits > 0,
            tier=tier,
        )

    async def _situation_evidence_records(
        self,
        *,
        user_id: UUID,
        goal_type: str | None,
        friction_tag: str | None,
        now: datetime,
    ) -> tuple[Any, ...]:
        """同 scope 的 M-06 投影记录（已约束维度精确匹配；含方向证据的子集）。

        这是「同 scope 历史有效 intervention 改变 ranking」的证据来源——
        真实投影（D-05 保守关联摘要的派生视图），非 mock/seed。
        """
        projection = await ExperienceMemoryProjector(self.db).project(user_id=user_id, now=now)
        matched = []
        for record in projection.records:
            if not record.has_outcome_evidence:
                continue  # 无 outcome 不参与方向证据（M-06 红线 1）
            signature = record.signature.as_dict()
            if goal_type is not None and signature.get("goal_type") != goal_type:
                continue
            if friction_tag is not None and signature.get("friction_tag") != friction_tag:
                continue
            matched.append(record)
        return tuple(matched)

    # ------------------------------------------------------------------
    # 内部：行映射 / 迁移执行 / 缓存
    # ------------------------------------------------------------------

    async def _get_by_patch_id(self, patch_id: str) -> PolicyPatchRecord | None:
        return (
            (
                await self.db.execute(
                    select(PolicyPatchRecord).where(PolicyPatchRecord.patch_id == str(patch_id)).limit(1)
                )
            )
            .scalars()
            .first()
        )

    async def _apply(
        self,
        record: PolicyPatchRecord,
        action: str,
        now: datetime,
        *,
        actor: str,
        reasons_extra: tuple[str, ...] = (),
        force_target: str | None = None,
    ) -> TransitionOutcome:
        """执行一次状态迁移（append 审计历史 + 提交；非法迁移零写）。

        并发守卫（P2-3，M-01/M-07 同构）：写前以 ``FOR UPDATE`` 行锁重读
        （PG 生效——锁等待后见到最新已提交版本；sqlite 单写者天然串行，
        ``with_for_update`` 为 no-op）+ ``populate_existing`` 穿透 identity
        map 刷新属性。锁下状态与调用方所见不一致（并发 revoke×activate 的
        后到者）→ ``T6.illegal_transition`` 拒绝、零写——终态不可回退、
        审计不丢失（丢失更新窗口关闭）。

        DELTA-3：查询+守卫包进 SAVEPOINT——FOR UPDATE 查询触发的 autoflush
        会把调用方先前对旁列（user_confirmed/activated_at 等）的赋值刷库；
        T6 拒绝时回滚到 savepoint 只丢弃这部分盲写，不全 session 回滚
        （全回滚会 expire 调用方持有的全部 ORM 对象，异步惰性加载即炸，
        X-03 同坑）。
        """
        sp = await self.db.begin_nested()
        fresh = (
            (
                await self.db.execute(
                    select(PolicyPatchRecord)
                    .where(PolicyPatchRecord.id == record.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .first()
        )
        if fresh is None:
            await sp.rollback()  # DELTA-3：旁列盲写随拒绝丢弃（savepoint 作用域）
            return TransitionOutcome(record.state, ("T6.illegal_transition",))
        # 锁下守卫：以数据库当前状态为准（record 可能是证据核验 await 期间的
        # 陈旧快照——并发迁移已落则本迁移让位，不覆盖）。
        outcome = apply_transition(state=fresh.state, action=action, now=now, actor=actor, reasons_extra=reasons_extra)
        if not outcome.transitioned:
            await sp.rollback()  # DELTA-3：同上
            return outcome
        target = force_target or outcome.new_state
        history = list(fresh.transition_history or [])
        if outcome.history_entry is not None:
            entry = dict(outcome.history_entry)
            if force_target:
                entry["to"] = force_target
                entry["reason"] = reasons_extra[0] if reasons_extra else entry["reason"]
            history.append(entry)
        fresh.state = target
        fresh.transition_history = history
        await self.db.commit()
        await self.db.refresh(fresh)
        return outcome

    @staticmethod
    def _inputs_cache_key(
        user_id: UUID | str,
        nominated: Sequence[str],
        goal_type: str | None,
        friction_tag: str | None,
    ) -> str:
        payload = json.dumps(
            {
                "user": str(user_id),
                "nominated": list(nominated),
                "goal_type": goal_type,
                "friction_tag": friction_tag,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return "a05:inputs:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

    @classmethod
    def _cache_get(cls, key: str, version: str) -> PatchedDecisionInputs | None:
        entry = cls._inputs_cache.get(key)
        if entry is None:
            return None
        cached_version, inputs, computed_at = entry
        if cached_version != version:
            return None  # 版本 bump → 缓存不命中（卡面 Work 3 的机制化）
        if time.monotonic() - computed_at > INPUTS_CACHE_TTL_SECONDS:
            cls._inputs_cache.pop(key, None)
            return None
        cls._inputs_cache.move_to_end(key)
        return inputs

    @classmethod
    def _cache_put(cls, key: str, version: str, inputs: PatchedDecisionInputs) -> None:
        cls._inputs_cache[key] = (version, inputs, time.monotonic())
        cls._inputs_cache.move_to_end(key)
        while len(cls._inputs_cache) > INPUTS_CACHE_MAX_ENTRIES:
            cls._inputs_cache.popitem(last=False)

    @classmethod
    def reset_cache(cls) -> None:
        """测试钩：清空进程级决策输入缓存。"""
        cls._inputs_cache.clear()


@dataclass(frozen=True)
class _EvidenceVerification:
    """一次证据门核验的只读结果（计数/方向/档位）。"""

    resolved_ref_count: int
    direction_satisfied: bool
    tier: str


def _row_to_patch(record: PolicyPatchRecord) -> PolicyPatch:
    """ORM 行 → core 冻结投影（payload/evidence_refs 防御性拷贝）。"""
    return PolicyPatch(
        patch_id=record.patch_id,
        user_id=str(record.user_id),
        surface=record.surface,
        payload=dict(record.payload or {}),
        state=record.state,
        scope_goal_type=record.scope_goal_type,
        scope_friction_tag=record.scope_friction_tag,
        evidence_refs=tuple(record.evidence_refs or ()),
        evidence_tier=record.evidence_tier,
        evidence_verified_at=record.evidence_verified_at,
        user_confirmed=bool(record.user_confirmed),
        provenance=record.provenance,
        created_at=record.created_at,
        activated_at=record.activated_at,
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
        revoke_reason=record.revoke_reason,
        transition_history=tuple(record.transition_history or ()),
    )


__all__ = [
    "POLICY_PATCH_SERVICE_VERSION",
    "INPUTS_CACHE_TTL_SECONDS",
    "INPUTS_CACHE_MAX_ENTRIES",
    "POLICY_PATCH_EMPTY_VERSION",
    "PatchOpResult",
    "PatchedDecisionInputs",
    "PolicyPatchService",
    "evidence_requirements_for_patch",
]
