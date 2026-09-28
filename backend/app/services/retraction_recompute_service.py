"""V4-D03 · 撤回派生影响与投影重算服务面（结果撤回 → 星图能力节点栅栏下重算）。

卡 V4-D03（risk=high，锁 evidence-retraction）。设计真源：
``v4/03_intelligence/DATA_AND_GRAPH.md`` §撤回与重算：

    outcome撤回→依赖索引查受影响节点/insight/experience→标pending_recompute
    →从仍有效事件按确定顺序重新投影→新version发布。

一条主链（全部委托既有权威，零第二权威）：

1. **登记**（:meth:`RetractionRecomputeService.register_retraction`）：
   幂等撤回登记——内容寻址 ``rtr_<...>`` id 重放恒同（重复登记零副作用）；
   依赖索引（G-02 ``oc=`` 分段标记，分号精确分段）找出吸收了该 outcome 的
   ``mastery_audit_log`` 证据行，**钉持久墓碑**（``effect_kind='retracted'``，
   V4-D03 词表成员——任何后续重放结构性跳过，这是"并发旧 job 不能复活已删
   内容"的第二道防御：栅栏之后还有账本本身）；bump **既有** per-user
   ``memory_epoch``（复用 ``_bump_memory_epoch_in_txn`` 单条原子 UPDATE，M-01
   契约——不造第二世代计数器），一切钉 epoch 的读侧门（context 快照 C-07、
   I01 resume freshness、profile context）随之判 stale；写一条 content-free
   ``retraction.registered`` outbox 事件（payload 仅
   retraction_id/kind/target/epoch）；提交后 DEL 派生缓存（复用 M-07 管线
   的键集，DEL 是加速、epoch 门是保证）。
2. **重算**（:meth:`RetractionRecomputeService.recompute_capability_nodes`）：
   逐受影响节点先过**发布栅栏**（:func:`...evaluate_publish_gate`：base_epoch
   落后/排除集不全/目标已删 → 整体丢弃，不部分应用），允许后由 G-01 权威
   ``_load_prior_belief`` 重放（被撤回行已墓碑 → 从仍有效事件按确定顺序前向
   Kalman 回放——**没有任何逆推减分**），写回 ``user_node_status.mastery_score``
   + 逻辑时钟 ``revision`` 严格 +1（新 version 发布）+ 一条 trace-only 审计行
   （``effect_kind='projection'``——重放跳过，不形成新证据）+ 复用
   ``GalaxyService._write_mastery_outbox_event`` 发掌握度更新事件（下游 CQRS
   投影同步，不留陈旧账）。
3. **读门**（:meth:`RetractionRecomputeService.capability_node_read_state`）：
   登记晚于最近一次重算 ⇒ ``pending_recompute`` ⇒ UI 标 ``stale_recomputing``
   且工具 ``suggestions_allowed=False``（:func:`...evaluate_read_gate` 同一门
   两个出口，验收③——UI 与工具不存在分裂态）。

三分类纪律：本服务当前接线 **result_retracted**（结果撤回，依赖边真实存在：
``oc=`` 标记）；material_deleted 的记忆域撤回已是 M-07 权威管线（本服务不重
做、不改写）；inference_retracted 与 insight/strategy 面的具体重算执行体归
消费卡（读时计算面无需持久重算），契约词表已由
``app/core/retraction_recompute.py`` 统一冻结。错误的目标类型/撤回类型组合
在构造期即拒（不静默落错依赖边）。

并发语义（验收①，两层防御）：
- **栅栏**：重算 job 携带 ``base_epoch``；发布时点重读 epoch，不等 ⇒ 丢弃
  （DISCARD_STALE_EPOCH）；
- **持久墓碑**：即使 job 完全不知晓撤回（旧代码路径/绕过栅栏），账本行
  effect_kind='retracted' 使任何重放都拿不回被撤回证据的效果。

幂等语义：register 重放（同 user/kind/target）⇒ 同 retraction_id ⇒ 检出到
已登记事件行 ⇒ 零重复副作用（不双 bump、不双事件、墓碑幂等）；墓碑 UPDATE
本身按 ``effect_kind='evidence'`` 条件更新，二次执行天然零行。
"""

# rule-bj: exempt V4-D03 撤回派生影响与投影重算服务面；生产触发方按卡序接线（结果撤回的 UI/FSM 入口、重算 job 调度）——登记 docs/engineering/KNOWN_CODE_DEBT_LEDGER.md

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_registry import EventSource, build_event_metadata
from app.core.retraction_recompute import (
    RETRACTED_EFFECT_KIND,
    RETRACTION_RECOMPUTE_SCHEMA_VERSION,
    PublishGateVerdict,
    ReadGate,
    RecomputeStatus,
    RetractionKind,
    derive_retraction_id,
    evaluate_publish_gate,
    evaluate_read_gate,
    extract_outcome_marker,
    next_projection_version,
    outcome_marker_hex,
)
from app.core.time_utils import utcnow
from app.services.galaxy.mastery_evidence import MasteryEffectKind
from app.services.memory_invalidation_pipeline import (
    MemoryInvalidationPipeline,
    _bump_memory_epoch_in_txn,
    _next_sequence,
)
from app.services.memory_service import MemoryService

RETRACTION_REGISTERED_EVENT = "retraction.registered"
RETRACTION_AGGREGATE_TYPE = "user_retraction"

#: 重算 trace 审计行 reason（append-only 账本上的留痕；effect_kind=projection，
#: 重放跳过——重算动作本身永远不是证据）。
RECOMPUTE_TRACE_REASON = "retraction_recompute"

#: result_retracted 唯一合法目标类型（依赖边语义钉死：outcome → oc= 标记）。
RESULT_TARGET_TYPE = "outcome"

_VALID_KIND_TARGET: dict[str, frozenset[str]] = {
    RetractionKind.RESULT_RETRACTED.value: frozenset({RESULT_TARGET_TYPE}),
    # material/inference 的具体执行体各归其主（M-07 / 消费卡）；本服务构造期
    # 只放行 result 域，其余显式拒绝（不静默落错依赖边）。
}


class RetractionRecomputeError(ValueError):
    """撤回登记构造期校验失败（类型/词表/组合不合法）。"""


@dataclass(frozen=True)
class RetractionRegistration:
    retraction_id: str
    kind: str
    target_type: str
    target_id: str
    epoch: int
    tombstoned_rows: int
    affected_node_ids: tuple[str, ...]
    event_written: bool
    duplicate: bool


@dataclass(frozen=True)
class NodeRecomputeResult:
    node_id: str
    outcome: str  # "recomputed" | gate decision value（丢弃原因逐节点显式）
    old_mastery: float | None = None
    new_mastery: float | None = None
    detail: str | None = None


class RetractionRecomputeService:
    """结果撤回 → 受影响能力节点的登记/栅栏重算/读门（唯一 IO 入口）。"""

    def __init__(self, db: AsyncSession, redis_client: Any | None = None):
        self.db = db
        self.redis = redis_client

    # ------------------------------------------------------------------
    # 1. 登记撤回（幂等；墓碑 + epoch bump + 事件 同事务）
    # ------------------------------------------------------------------

    async def register_retraction(
        self,
        *,
        user_id: UUID,
        kind: RetractionKind | str,
        target_type: str,
        target_id: str,
        reason_code: str | None = None,
    ) -> RetractionRegistration:
        kind_value = RetractionKind(kind).value
        allowed_targets = _VALID_KIND_TARGET.get(kind_value)
        if allowed_targets is None:
            raise RetractionRecomputeError(
                f"retraction kind '{kind_value}' has no wired executor on this service; "
                "memory-domain retractions go through MemoryInvalidationPipeline (M-07), "
                "inference-domain through their consumer cards"
            )
        if target_type not in allowed_targets:
            raise RetractionRecomputeError(
                f"target_type '{target_type}' is not valid for retraction kind '{kind_value}'"
            )

        retraction_id = derive_retraction_id(str(user_id), kind_value, target_type, target_id)

        # 幂等检出：同 retraction_id 的事件行已存在 ⇒ 重放零副作用。
        if await self._retraction_already_registered(user_id, retraction_id):
            epoch = await MemoryService(self.db).get_memory_epoch(user_id)
            return RetractionRegistration(
                retraction_id=retraction_id,
                kind=kind_value,
                target_type=target_type,
                target_id=target_id,
                epoch=epoch,
                tombstoned_rows=0,
                affected_node_ids=(),
                event_written=False,
                duplicate=True,
            )

        # 依赖索引 + 持久墓碑（幂等条件更新：只钉仍是证据的行）。
        marker = outcome_marker_hex(target_id)
        tombstoned_rows, affected_node_ids = await self._tombstone_evidence_rows(user_id, [marker])

        # 同事务 bump 既有 per-user epoch（C-07/M-07 唯一世代权威；不造第二计数器）。
        epoch = await _bump_memory_epoch_in_txn(self.db, user_id, reason=f"retraction:{kind_value}:{target_type}")

        event_written = await self._write_retraction_event(
            user_id=user_id,
            retraction_id=retraction_id,
            kind_value=kind_value,
            target_type=target_type,
            target_id=target_id,
            epoch=epoch,
            reason_code=reason_code,
        )

        await self.db.commit()

        # 提交后 DEL 派生缓存（M-07 R1-C2-3 同款：DEL 是加速，epoch 门是保证）。
        pipeline = MemoryInvalidationPipeline(self.db, self.redis)
        await pipeline.invalidate_derived_caches(user_id=user_id, kinds=set())

        logger.info(
            "retraction registered user_id={u} retraction_id={r} kind={k} target={t} "
            "tombstoned={n} nodes={nodes} epoch={e}",
            u=user_id,
            r=retraction_id,
            k=kind_value,
            t=target_id,
            n=tombstoned_rows,
            nodes=len(affected_node_ids),
            e=epoch,
        )
        return RetractionRegistration(
            retraction_id=retraction_id,
            kind=kind_value,
            target_type=target_type,
            target_id=target_id,
            epoch=epoch,
            tombstoned_rows=tombstoned_rows,
            affected_node_ids=tuple(str(n) for n in affected_node_ids),
            event_written=event_written,
            duplicate=False,
        )

    # ------------------------------------------------------------------
    # 2. 栅栏下重算受影响能力节点
    # ------------------------------------------------------------------

    async def recompute_capability_nodes(
        self,
        *,
        user_id: UUID,
        outcome_ids: Sequence[str],
        base_epoch: int | None,
    ) -> tuple[NodeRecomputeResult, ...]:
        """对被撤回 outcome 影响的节点做栅栏下重算（逐节点显式结论）。

        ``base_epoch`` = 调用方（重算 job）开始时读到的世代；发布门逐节点判定，
        丢弃不部分应用。
        """
        markers = [outcome_marker_hex(oid) for oid in outcome_ids]
        if not markers:
            return ()

        # 幂等自愈：确保墓碑在位（register 已钉则零行；直呼路径自愈）。
        await self._tombstone_evidence_rows(user_id, markers)

        current_epoch = await MemoryService(self.db).get_memory_epoch(user_id)
        node_ids = await self.find_affected_capability_nodes(user_id=user_id, outcome_ids=outcome_ids)

        results: list[NodeRecomputeResult] = []
        dirty = False
        for node_id in node_ids:
            gate = await self._evaluate_node_gate(
                user_id=user_id,
                node_id=node_id,
                base_epoch=base_epoch,
                current_epoch=current_epoch,
                retracted_markers=markers,
            )
            if not gate.allowed:
                results.append(
                    NodeRecomputeResult(
                        node_id=str(node_id),
                        outcome=gate.decision.value,
                        detail=gate.reason_detail,
                    )
                )
                continue

            from app.services.galaxy.stats_service import GalaxyStatsService

            status = await self._load_node_status(user_id, node_id)
            if status is None:
                results.append(
                    NodeRecomputeResult(
                        node_id=str(node_id),
                        outcome="discard_target_gone",
                        detail="no user_node_status row",
                    )
                )
                continue

            old_mastery = float(status.mastery_score or 0.0)
            belief = await GalaxyStatsService(self.db)._load_prior_belief(user_id, node_id, old_mastery)
            new_mastery = max(0.0, min(100.0, float(belief.mean)))
            value_changed = abs(new_mastery - old_mastery) > 1e-9
            if value_changed:
                # 新 version 发布只在状态真变时发生：重放恒同值不推进逻辑时钟
                # （重算重放幂等，不产生版本抖动）。
                status.mastery_score = new_mastery
                status.revision = next_projection_version(getattr(status, "revision", None))
                dirty = True

            # trace 行恒写（projection，重放跳过）：它是读门「登记 < 重算」
            # 比对的重算时点信号——即使值未变，重算确实发生了。
            await self._write_recompute_trace_row(
                user_id=user_id,
                node_id=node_id,
                old_mastery=old_mastery,
                new_mastery=new_mastery,
                revision=int(getattr(status, "revision", 0) or 0),
            )
            if value_changed:
                await self._write_mastery_update_event(
                    user_id=user_id,
                    node_id=node_id,
                    old_mastery=old_mastery,
                    new_mastery=new_mastery,
                    revision=int(getattr(status, "revision", 0) or 0),
                )
            results.append(
                NodeRecomputeResult(
                    node_id=str(node_id),
                    outcome="recomputed",
                    old_mastery=old_mastery,
                    new_mastery=new_mastery,
                    detail=None if value_changed else "value_unchanged_no_version_bump",
                )
            )

        if dirty:
            await self.db.commit()
        return tuple(results)

    async def find_affected_capability_nodes(
        self,
        *,
        user_id: UUID,
        outcome_ids: Sequence[str],
    ) -> list[UUID]:
        """依赖索引：吸收了任一被撤回 outcome 的节点（精确分段匹配）。"""
        markers = {outcome_marker_hex(oid) for oid in outcome_ids}
        if not markers:
            return []
        like_clauses: list[str] = []
        params: dict[str, object] = {"user_id": str(user_id)}
        for i, marker in enumerate(sorted(markers)):
            # LIKE 只做预过滤（走索引友好）；精确性由 Python 侧分段解析保证，
            # hex 子串不构成同因（G-02 分号精确分段纪律）。
            params[f"m{i}"] = f"%oc={marker}%"
            like_clauses.append(f"request_id LIKE :m{i}")
        stmt = text(
            "SELECT DISTINCT node_id, request_id FROM mastery_audit_log "
            "WHERE user_id = :user_id AND effect_kind IN (:effect_kind, :retracted_kind) "
            f"AND ({' OR '.join(like_clauses)})"
        ).bindparams(
            effect_kind=MasteryEffectKind.EVIDENCE.value,
            retracted_kind=RETRACTED_EFFECT_KIND,
        )
        rows = (await self.db.execute(stmt, params)).fetchall()

        affected: dict[UUID, None] = {}
        for row in rows:
            if extract_outcome_marker(row[1]) in markers:
                affected.setdefault(UUID(str(row[0])), None)
        return list(affected)

    async def capability_node_read_state(self, *, user_id: UUID, node_id: UUID) -> ReadGate:
        """能力节点读门：登记晚于最近重算 ⇒ pending_recompute ⇒ 过期 + 建议禁用。"""
        last_recompute_at = await self._last_recompute_at(user_id, node_id)
        last_retraction_at = await self._last_retraction_at(user_id)
        pending = last_retraction_at is not None and (
            last_recompute_at is None or last_retraction_at > last_recompute_at
        )
        if pending:
            status = RecomputeStatus.PENDING_RECOMPUTE
        elif last_recompute_at is not None:
            status = RecomputeStatus.RECOMPUTED
        else:
            status = RecomputeStatus.FRESH
        return evaluate_read_gate(status=status, computed_epoch=None, current_epoch=None)

    # ------------------------------------------------------------------
    # 内部（全部单权威委托）
    # ------------------------------------------------------------------

    async def _retraction_already_registered(self, user_id: UUID, retraction_id: str) -> bool:
        if not await self._outbox_tables_exist():
            return False
        stmt = text(
            "SELECT payload FROM event_outbox "
            "WHERE aggregate_type = :agg_type AND aggregate_id = :agg_id "
            "AND event_type = :event_type AND payload LIKE :needle"
        )
        row = (
            await self.db.execute(
                stmt,
                {
                    "agg_type": RETRACTION_AGGREGATE_TYPE,
                    "agg_id": str(user_id),
                    "event_type": RETRACTION_REGISTERED_EVENT,
                    "needle": f'%"retraction_id":"{retraction_id}"%',
                },
            )
        ).first()
        return row is not None

    async def _tombstone_evidence_rows(self, user_id: UUID, markers: Sequence[str]) -> tuple[int, list[UUID]]:
        """把仍为 evidence 的被撤回依赖行钉成墓碑（幂等；返回行数与受影响节点）。"""
        like_clauses: list[str] = []
        params: dict[str, object] = {
            "user_id": str(user_id),
            "retracted": RETRACTED_EFFECT_KIND,
            "evidence": MasteryEffectKind.EVIDENCE.value,
        }
        unique_markers = sorted(set(markers))
        if not unique_markers:
            return 0, []
        for i, marker in enumerate(unique_markers):
            params[f"m{i}"] = f"%oc={marker}%"
            like_clauses.append(f"request_id LIKE :m{i}")
        marker_list = set(markers)

        select_stmt = text(
            "SELECT id, node_id, request_id FROM mastery_audit_log "
            "WHERE user_id = :user_id AND effect_kind = :evidence "
            f"AND ({' OR '.join(like_clauses)})"
        )
        rows = (await self.db.execute(select_stmt, params)).fetchall()
        exact_ids: list[str] = []
        node_ids: dict[UUID, None] = {}
        for row in rows:
            if extract_outcome_marker(row[2]) in marker_list:
                exact_ids.append(str(row[0]))
                node_ids.setdefault(UUID(str(row[1])), None)
        if not exact_ids:
            return 0, []

        update_stmt = text(
            "UPDATE mastery_audit_log SET effect_kind = :retracted "
            "WHERE id IN (" + ", ".join(f":id{i}" for i in range(len(exact_ids))) + ")"
        )
        update_params: dict[str, object] = {"retracted": RETRACTED_EFFECT_KIND}
        for i, row_id in enumerate(exact_ids):
            update_params[f"id{i}"] = row_id
        await self.db.execute(update_stmt, update_params)
        return len(exact_ids), list(node_ids)

    async def _write_retraction_event(
        self,
        *,
        user_id: UUID,
        retraction_id: str,
        kind_value: str,
        target_type: str,
        target_id: str,
        epoch: int,
        reason_code: str | None,
    ) -> bool:
        if not await self._outbox_tables_exist():
            logger.warning("retraction.registered skipped: event_outbox tables unavailable user_id={u}", u=user_id)
            return False
        sequence_number = await _next_sequence(self.db, RETRACTION_AGGREGATE_TYPE, user_id)
        # content-free payload：身份/类型/世代（SECURITY_PRIVACY audit-without-exposure，
        # M-07 memory.invalidated 同款纪律）。
        payload = {
            "schema_version": RETRACTION_RECOMPUTE_SCHEMA_VERSION,
            "retraction_id": retraction_id,
            "kind": kind_value,
            "target_type": target_type,
            "target_id": target_id[:64],
            "memory_epoch": epoch,
        }
        metadata = build_event_metadata(
            user_id=user_id,
            source=EventSource.SERVER_SERVICE,
            service="retraction_recompute_service",
            event_name=RETRACTION_REGISTERED_EVENT,
            aggregate_type=RETRACTION_AGGREGATE_TYPE,
            aggregate_id=user_id,
            sequence_number=sequence_number,
            extra={"memory_epoch": epoch, "reason_code": (reason_code or kind_value)[:40]},
        )
        await self.db.execute(
            text(
                "INSERT INTO event_outbox "
                "(aggregate_type, aggregate_id, event_type, event_version, sequence_number, payload, metadata) "
                "VALUES (:aggregate_type, :aggregate_id, :event_type, 1, :sequence_number, :payload, :metadata)"
            ),
            {
                "aggregate_type": RETRACTION_AGGREGATE_TYPE,
                "aggregate_id": str(user_id),
                "event_type": RETRACTION_REGISTERED_EVENT,
                "sequence_number": sequence_number,
                # 紧凑序列化：幂等检出的 LIKE needle（"retraction_id":"<id>"）
                # 按此精确形状匹配（无空格分隔符）。
                "payload": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                "metadata": json.dumps(metadata, ensure_ascii=False),
            },
        )
        return True

    async def _evaluate_node_gate(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        base_epoch: int | None,
        current_epoch: int | None,
        retracted_markers: Sequence[str],
    ) -> PublishGateVerdict:
        status = await self._load_node_status(user_id, node_id)
        return evaluate_publish_gate(
            base_epoch=base_epoch,
            current_epoch=current_epoch,
            excluded_ids=list(retracted_markers),
            retracted_ids=list(retracted_markers),
            target_exists=status is not None,
        )

    async def _load_node_status(self, user_id: UUID, node_id: UUID):
        from sqlalchemy import select

        from app.models.galaxy import UserNodeStatus

        result = await self.db.execute(
            select(UserNodeStatus).where(UserNodeStatus.user_id == user_id, UserNodeStatus.node_id == node_id)
        )
        return result.scalar_one_or_none()

    async def _write_recompute_trace_row(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        old_mastery: float,
        new_mastery: float,
        revision: int,
    ) -> None:
        # trace-only 审计行：effect_kind=projection ⇒ 任何后续重放跳过本行
        # （重算动作本身不是证据，不形成新依赖边）。
        await self.db.execute(
            text(
                "INSERT INTO mastery_audit_log "
                "(node_id, user_id, old_mastery, new_mastery, reason, request_id, revision, effect_kind) "
                "VALUES (:node_id, :user_id, :old_mastery, :new_mastery, :reason, :request_id, :revision, :effect_kind)"
            ),
            {
                "node_id": str(node_id),
                "user_id": str(user_id),
                "old_mastery": int(old_mastery),
                "new_mastery": int(new_mastery),
                "reason": RECOMPUTE_TRACE_REASON,
                "request_id": None,
                "revision": revision,
                "effect_kind": MasteryEffectKind.PROJECTION.value,
            },
        )

    async def _write_mastery_update_event(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        old_mastery: float,
        new_mastery: float,
        revision: int,
    ) -> None:
        # 复用 GalaxyService 唯一 mastery outbox 写面（下游 CQRS 投影同步，
        # 重算不留陈旧账）；失败只告警——账本真源已写，投影靠事件追赶。
        try:
            from app.services.galaxy_service import GalaxyService

            await GalaxyService(self.db)._write_mastery_outbox_event(
                aggregate_id=user_id,
                event_type="galaxy.mastery.updated",
                payload={
                    "user_id": str(user_id),
                    "node_id": str(node_id),
                    "task_id": None,
                    "mastery_score": int(new_mastery),
                    "revision": revision,
                    "reason": RECOMPUTE_TRACE_REASON,
                    "timestamp": utcnow().isoformat(),
                },
            )
        except Exception as exc:  # noqa: BLE001 — 投影事件尽力而为
            logger.warning(
                "mastery update event after recompute failed user_id={u} node={n}: {e}",
                u=user_id,
                n=node_id,
                e=exc,
            )

    async def _last_recompute_at(self, user_id: UUID, node_id: UUID) -> datetime | None:
        stmt = text(
            "SELECT MAX(created_at) FROM mastery_audit_log "
            "WHERE user_id = :user_id AND node_id = :node_id AND reason = :reason"
        )
        row = (
            await self.db.execute(
                stmt,
                {"user_id": str(user_id), "node_id": str(node_id), "reason": RECOMPUTE_TRACE_REASON},
            )
        ).first()
        return row[0] if row else None

    async def _last_retraction_at(self, user_id: UUID) -> datetime | None:
        if not await self._outbox_tables_exist():
            return None
        stmt = text(
            "SELECT MAX(created_at) FROM event_outbox "
            "WHERE aggregate_type = :agg_type AND aggregate_id = :agg_id "
            "AND event_type = :event_type"
        )
        row = (
            await self.db.execute(
                stmt,
                {
                    "agg_type": RETRACTION_AGGREGATE_TYPE,
                    "agg_id": str(user_id),
                    "event_type": RETRACTION_REGISTERED_EVENT,
                },
            )
        ).first()
        return row[0] if row else None

    async def _outbox_tables_exist(self) -> bool:
        connection = await self.db.connection()
        names = await connection.run_sync(lambda sync_conn: frozenset(_inspect_table_names(sync_conn)))
        return "event_outbox" in names


def _inspect_table_names(sync_conn: Any) -> list[str]:
    from sqlalchemy import inspect

    try:
        return list(inspect(sync_conn).get_table_names())
    except Exception:  # noqa: BLE001
        return []
