"""G-02 · Outcome → Galaxy 吸收 —— 「真实成果自动成为图谱证据与用户可见成长」.

定位（stream=GALAXY, gate=V3-3, lock=galaxy-model）：消费 X-08 广播的
``outcome.recorded`` 事件，把**真实成果**幂等地吸收进 Galaxy 图：

1. **不重建真源（卡面 forbidden #1）**：本模块是图谱侧的**证据消费者**，
   mastery 真源仍走 G-01 证据账本（``mastery_audit_log`` + Kalman 重放，
   ``GalaxyStatsService._load_prior_belief``），溯源面仍走
   ``UserNodeStatus.learning_path_snapshot.graph_event_sources``
   （``provenance.append_graph_event_source``）。零新表、零 schema 变更。
2. **幂等是灵魂（acceptance「不重复点亮」）**：
   - POSITIVE 点亮的硬门 = mastery_audit_log 追加行的 ``request_id`` 内嵌
     ``outcome=<outc_id>`` 标记（与 X-08 账本幂等 id 同源，append-only、
     无界、重放安全）；同 outcome 重放直接跳过融合。
   - 同因合并：任务完成 outcome 与其 agent run receipt outcome 是**同一逻辑
     outcome 的两个事件面**（D-02：receipt 是 task_completion 条目上的附着
     证据），``task=<task_id>`` 标记让 receipt 事件只补溯源、不二次融合。
   - NEGATIVE 弱点标记天然幂等（keywords 集合语义）；溯源条目按
     (event_type, source_type, reference_id) 去重（provenance 既有语义）。
3. **失败/撤销正确处理（卡面 work 3）**：NEGATIVE（ABANDONED / FAILED /
   TIMED_OUT receipt）**永不点亮**——不融合任何掌握度证据、不写 evidence
   行；只做可解释溯源 + ``signal:weak_at`` 弱点标记（供 Review now 消费）。
   **裁决：NEGATIVE 不做掌握度降级**——放弃/失败可能源于计划噪声而非知识
   回退，降级语义归错题路径（ErrorBookMasterySyncService）所有；NEUTRAL
   （PARTIAL/CANCELLED receipt）只留溯源，既不点亮也不标记。
4. **撤销（同 id 极性翻转）**：任务 FSM 中 COMPLETED/ABANDONED 均为吸收态
   （``task_service._VALID_TRANSITIONS``），同一 outcome id 的极性翻转在上游
   结构性不可达；消费侧仍防御：检测到已吸收极性与新极性不一致时记录
   **纠正溯源**（不二次点亮、不降级），保证图谱与账本可对账。

与既有 ``task.completed`` 消费路径的关系（防双计裁决）：TaskEventListener /
GraphEvolutionService 已在完成点击时做时长型 spark（legacy 封顶）与邻居边
+0.03 强化。本模块是**证据型**吸收（TASK_OUTCOME Kalman 融合），**刻意不
再动关系强度边**——同一完成若再 +0.03 即边权双计，违反「不重复点亮」。
POSITIVE 高掌握度时清除弱点标记（与 handle_mastery_updated 语义一致）。

事件纪律：payload content-free（ids/极性/引用），本模块读到的全部是身份面；
节点解析只走确定性链（correlation_node_id → task.knowledge_node_id →
TaskKnowledgeLink 前置链接 → DF-5 任务标题确定性锚），**不做**关键词模糊
匹配（完成事件不得凭模糊猜测点亮任意节点）。标题锚与完成管线
``GalaxyService.ensure_task_node`` 同源（exact-title 命中优先，否则
uuid5(title) 确定性任务星），保证吸收与 legacy spark 落在**同一颗星**。
零 LLM、零 Redis 依赖（传输层由消费者包装持有）。NBP-4 注记：吸收**真源**
路径仍零 Redis；唯一例外是事务提交后的读面缓存失效（`invalidate_galaxy_graph_view_cache`，
best-effort 删除 ``view:get_galaxy_graph`` 视图键，失败只降级不回滚）——
没有它，「学完 → 星图长大」被读面 ttl=600 吞成分钟级延迟。
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import DateTime, String, bindparam, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.core.time_utils import utcnow as _utcnow
from app.models.base import GUID
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task
from app.models.task_resources import TaskKnowledgeLink
from app.services.galaxy.graph_evolution_service import GraphEvolutionService
from app.services.galaxy.mastery_evidence import (
    EVIDENCE_REASON_PREFIX,
    EvidenceObservation,
    MasteryEvidenceType,
    fuse_mastery,
)
from app.services.galaxy.provenance import append_graph_event_source
from app.services.galaxy.stats_service import GalaxyStatsService
from app.services.outcome_capture_service import OUTCOME_RECORDED_EVENT

# ---------------------------------------------------------------------------
# Deterministic evidence mapping (transparent, testable — GALAXY.md contract)
# ---------------------------------------------------------------------------

#: POSITIVE task completion → mastery-equivalent observation. 60 sits above
#: the legacy time cap (40) — a *real completed outcome* proves more than
#: exposure — but below the mastered threshold (80): completions alone can
#: never claim mastery (Kalman converges toward 60 asymptotically; quiz-grade
#: evidence at weight 1.0 dominates the posterior).
TASK_OUTCOME_EVIDENCE_VALUE = 60.0

#: Confidence of the completion observation (weight 0.6 × 0.8 = 0.48 effective
#: → first completion on a fresh node moves it to 30, second to 40, …).
TASK_OUTCOME_EVIDENCE_CONFIDENCE = 0.8

#: mastery_audit_log reason for outcome-absorbed evidence rows (replayed by
#: GalaxyStatsService._load_prior_belief via classify_audit_reason).
OUTCOME_EVIDENCE_AUDIT_REASON = f"{EVIDENCE_REASON_PREFIX}{MasteryEvidenceType.TASK_OUTCOME.value}"

#: Snapshot provenance source_type stamped on every absorbed outcome.
OUTCOME_PROVENANCE_SOURCE_TYPE = "outcome_ledger"

#: Node-status snapshot key holding absorbed-outcome markers (O(1) polarity
#: flip detection without unbounded growth of the bounded provenance ring).
ABSORBED_OUTCOMES_SNAPSHOT_KEY = "absorbed_outcomes"

#: Snapshot marker map cap (LRU-ish: oldest entries evicted; the append-only
#: mastery_audit_log row remains the hard replay gate for POSITIVE lighting).
ABSORBED_OUTCOMES_SNAPSHOT_CAP = 64


@dataclass
class OutcomeAbsorptionResult:
    """What the absorber did with one outcome.recorded event."""

    outcome_id: str
    polarity: str
    node_ids: list[str] = field(default_factory=list)
    #: "lit" (POSITIVE fused) / "duplicate" (replay or same-cause receipt) /
    #: "flagged" (NEGATIVE weak-signal) / "recorded_only" (NEUTRAL) /
    #: "corrected" (polarity flip defense) / "no_target" (nothing resolved)
    action: str = "no_target"
    mastery_by_node: dict[str, float] = field(default_factory=dict)


class GalaxyOutcomeAbsorber:
    """Absorb outcome.recorded payloads into Galaxy nodes (idempotent)."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._stats = GalaxyStatsService(db)
        self._evolution = GraphEvolutionService(db)

    # -- entry point -------------------------------------------------------

    async def absorb_outcome(self, payload: dict) -> OutcomeAbsorptionResult | None:
        """Consume one ``outcome.recorded`` payload (content-free identity face)."""
        outcome_id = str(payload.get("outcome_id") or "").strip()
        polarity = str(payload.get("polarity") or "").strip().lower()
        user_raw = payload.get("user_id")
        if not outcome_id or not polarity or not user_raw:
            logger.debug("outcome.recorded payload missing identity fields; skipped")
            return None
        try:
            user_id = UUID(str(user_raw))
        except (ValueError, AttributeError):
            logger.warning("outcome.recorded payload has non-UUID user_id {}; skipped", user_raw)
            return None

        node_ids = await self._resolve_node_ids(payload)
        result = OutcomeAbsorptionResult(outcome_id=outcome_id, polarity=polarity, node_ids=[str(n) for n in node_ids])
        if not node_ids:
            result.action = "no_target"
            return result

        for node_id in node_ids:
            if polarity == "positive":
                action, mastery = await self._absorb_positive(user_id, node_id, payload)
                result.action = action if result.action == "no_target" else result.action
                if mastery is not None:
                    result.mastery_by_node[str(node_id)] = mastery
            elif polarity == "negative":
                action = await self._absorb_negative(user_id, node_id, payload)
                result.action = action if result.action == "no_target" else result.action
            else:  # neutral (PARTIAL/CANCELLED receipt): traceable, never lights
                action = await self._absorb_neutral(user_id, node_id, payload)
                result.action = action if result.action == "no_target" else result.action
        await self.db.commit()
        # NBP-4 写后即时投影：可见变化（点亮 / 弱点标记）→ 立即失效星图读面
        # 视图缓存，让「学完 → 看到星图长大」不受读面 ttl=600 分钟级窗口吞掉
        # 爽点。与 ``GalaxyService.update_mastery`` 提交后失效同款同键。
        # best-effort：缓存面不可达只降级不回滚——吸收真源恒在 DB（事件纪律）。
        if result.action in _READ_MODEL_VISIBLE_ACTIONS:
            try:
                await invalidate_galaxy_graph_view_cache(user_id)
            except Exception as exc:  # noqa: BLE001 — 读投影失效失败不阻断吸收
                logger.warning("galaxy graph view cache invalidation failed for user {}: {}", user_id, exc)
        return result

    # -- polarity paths ----------------------------------------------------

    async def _absorb_positive(self, user_id: UUID, node_id: UUID, payload: dict) -> tuple[str, float | None]:
        """POSITIVE：证据融合点亮（幂等门 = append-only audit 行标记）。"""
        outcome_id = str(payload["outcome_id"])
        task_marker = _task_marker(payload)

        status = await self._get_or_create_status(user_id, node_id)
        if await self._already_absorbed(user_id, node_id, outcome_id, task_marker):
            append_graph_event_source(
                status,
                event_type=OUTCOME_RECORDED_EVENT,
                source_type=OUTCOME_PROVENANCE_SOURCE_TYPE,
                reference_id=outcome_id,
                label=str(payload.get("polarity")),
                payload=_provenance_payload(payload, replay=True),
            )
            _stamp_absorbed_marker(status, outcome_id, payload, action="duplicate")
            return "duplicate", float(status.mastery_score)

        # G-01 ledger replay → prior belief → Kalman fusion (no legacy time path)
        prior = await self._stats._load_prior_belief(user_id, node_id, float(status.mastery_score))
        observation = EvidenceObservation(
            evidence_type=MasteryEvidenceType.TASK_OUTCOME,
            value=TASK_OUTCOME_EVIDENCE_VALUE,
            confidence=TASK_OUTCOME_EVIDENCE_CONFIDENCE,
            observed_at=_parse_occurred_at(payload.get("occurred_at")) or _utcnow(),
        )
        fused = fuse_mastery(prior.mean, prior.variance, [observation])
        old_mastery = float(status.mastery_score)
        status.mastery_score = min(max(fused.mean, 0.0), 100.0)
        status.is_unlocked = True
        if status.first_unlock_at is None:
            status.first_unlock_at = _utcnow()

        # GJ08 溯源：图谱变化行可追到 outcome id（账本同源幂等键）
        append_graph_event_source(
            status,
            event_type=OUTCOME_RECORDED_EVENT,
            source_type=OUTCOME_PROVENANCE_SOURCE_TYPE,
            reference_id=outcome_id,
            label=str(payload.get("polarity")),
            payload=_provenance_payload(payload),
        )
        _stamp_absorbed_marker(status, outcome_id, payload, action="lit")
        self.db.add(status)

        # append-only evidence row: replay gate + ledger persistence in one
        # (GUID-typed bindparams: asyncpg binds UUID natively, aiosqlite binds str)
        try:
            from sqlalchemy import text as sa_text

            stmt = sa_text(
                "INSERT INTO mastery_audit_log (node_id, user_id, old_mastery, new_mastery, reason, request_id, revision, created_at) "
                "VALUES (:node_id, :user_id, :old_mastery, :new_mastery, :reason, :request_id, :revision, :created_at)"
            ).bindparams(
                bindparam("node_id", type_=GUID),
                bindparam("user_id", type_=GUID),
                bindparam("reason", type_=String),
                bindparam("request_id", type_=String),
                bindparam("created_at", type_=DateTime),
            )
            await self.db.execute(
                stmt,
                {
                    "node_id": node_id,
                    "user_id": user_id,
                    "old_mastery": int(old_mastery),
                    "new_mastery": int(status.mastery_score),
                    "reason": OUTCOME_EVIDENCE_AUDIT_REASON,
                    "request_id": _evidence_request_id(
                        TASK_OUTCOME_EVIDENCE_VALUE, TASK_OUTCOME_EVIDENCE_CONFIDENCE, outcome_id, task_marker
                    ),
                    "revision": getattr(status, "revision", 0),
                    "created_at": _utcnow(),
                },
            )
        except Exception as exc:  # noqa: BLE001 — audit 失败不阻断吸收（与 spark_node 同款降级）
            logger.warning("outcome evidence audit row failed for node {}: {}", node_id, exc)

        # Edge-signal consistency: real outcomes clear the weak flag at high
        # mastery (mirrors GraphEvolutionService.handle_mastery_updated).
        if status.mastery_score >= 60:
            await self._evolution.structure.tag_node_signal(
                node_id, GraphEvolutionService.WEAK_SIGNAL_TAG, active=False
            )
        logger.info(
            "outcome {} absorbed into node {}: mastery {} → {}",
            outcome_id,
            node_id,
            round(old_mastery, 2),
            round(status.mastery_score, 2),
        )
        return "lit", float(status.mastery_score)

    async def _absorb_negative(self, user_id: UUID, node_id: UUID, payload: dict) -> str:
        """NEGATIVE：永不点亮——弱点标记 + 可解释溯源（天然幂等）。"""
        outcome_id = str(payload["outcome_id"])
        status = await self._get_or_create_status(user_id, node_id)
        prior_action = _absorbed_marker_action(status, outcome_id)
        append_graph_event_source(
            status,
            event_type=OUTCOME_RECORDED_EVENT,
            source_type=OUTCOME_PROVENANCE_SOURCE_TYPE,
            reference_id=outcome_id,
            label=str(payload.get("polarity")),
            payload=_provenance_payload(payload, replay=prior_action is not None),
        )
        # 撤销防御：同一 outcome id 曾以 POSITIVE 吸收、现到 NEGATIVE →
        # 结构上不可达（FSM 吸收态），到达即记录纠正，绝不降级、绝不重复点亮。
        action = "corrected" if prior_action == "lit" else "flagged"
        _stamp_absorbed_marker(status, outcome_id, payload, action=action)
        self.db.add(status)
        # 弱点标记：keywords 集合语义，重放幂等；不做掌握度降级（裁决见模块 docstring）。
        await self._evolution.structure.tag_node_signal(node_id, GraphEvolutionService.WEAK_SIGNAL_TAG, active=True)
        return action

    async def _absorb_neutral(self, user_id: UUID, node_id: UUID, payload: dict) -> str:
        """NEUTRAL（PARTIAL/CANCELLED receipt）：只留溯源，不点亮不标记。"""
        outcome_id = str(payload["outcome_id"])
        status = await self._get_or_create_status(user_id, node_id)
        append_graph_event_source(
            status,
            event_type=OUTCOME_RECORDED_EVENT,
            source_type=OUTCOME_PROVENANCE_SOURCE_TYPE,
            reference_id=outcome_id,
            label=str(payload.get("polarity")),
            payload=_provenance_payload(payload),
        )
        _stamp_absorbed_marker(status, outcome_id, payload, action="recorded_only")
        self.db.add(status)
        return "recorded_only"

    # -- helpers -----------------------------------------------------------

    async def _resolve_node_ids(self, payload: dict) -> list[UUID]:
        """确定性节点解析：correlation_node_id → task.knowledge_node_id →
        TaskKnowledgeLink 前置链接。无模糊匹配（完成不得凭猜测点亮）。"""
        resolved: list[UUID] = []

        # GHOST-OUTCOME 守卫：outcome 的任务主体已被删除（生产硬删路径
        # TaskService.delete 无 outcome 回收联动；探针账号清理同样级联删
        # 任务）时，捕获后广播的事件成为幽灵——D-02 账本读模型从 tasks
        # 重算、已删任务直接消失，若仍凭 correlation_node_id 点亮，星图
        # 与真源漂移（mastery 被不存在任务的事件拨动）。诚实动作 =
        # no_target，与账本对账面保持一致。
        raw_subject = payload.get("correlation_task_id")
        if raw_subject:
            try:
                subject_id = UUID(str(raw_subject))
            except (ValueError, AttributeError):
                subject_id = None
            if subject_id is not None and await self.db.get(Task, subject_id) is None:
                logger.warning(
                    "outcome {} references deleted task {}; skipped (ghost guard)",
                    payload.get("outcome_id"),
                    subject_id,
                )
                return []

        raw_node = payload.get("correlation_node_id")
        if raw_node:
            try:
                resolved.append(UUID(str(raw_node)))
            except (ValueError, AttributeError):
                pass

        raw_task = payload.get("correlation_task_id")
        if not resolved and raw_task:
            try:
                task_id = UUID(str(raw_task))
            except (ValueError, AttributeError):
                task_id = None
            if task_id is not None:
                task = await self.db.get(Task, task_id)
                if task is not None and task.knowledge_node_id:
                    resolved.append(UUID(str(task.knowledge_node_id)))
                else:
                    links = await self.db.execute(
                        select(TaskKnowledgeLink.knowledge_node_id)
                        .where(
                            TaskKnowledgeLink.task_id == task_id,
                            TaskKnowledgeLink.relation_type == "prerequisite",
                        )
                        .distinct()
                    )
                    resolved.extend(UUID(str(row[0])) for row in links.all())
                # DF-5 通用映射锚（第 4 环，P1-5）：任务与星图无显式关联
                # （无 knowledge_node_id、无 TaskKnowledgeLink）时，复用完成
                # 管线 ``GalaxyService.ensure_task_node`` 的**同一确定性映射**：
                # 归一化标题精确命中既有节点，否则物化 uuid5(title) 任务星。
                # 与完成点击时的 legacy spark 写同一颗星，完成事件才能在
                # 用户可见面生长。仍无任何关键词模糊匹配（纪律不变）。
                if task is not None and not resolved:
                    try:
                        from app.services.galaxy_service import GalaxyService

                        anchor_id = await GalaxyService(self.db).ensure_task_node(
                            task.title, task_id=task.id
                        )
                        resolved.append(anchor_id)
                    except Exception as exc:  # noqa: BLE001 — 锚不可得时诚实 no_target
                        logger.warning(
                            "outcome {} task-title anchor failed for task {}: {}",
                            payload.get("outcome_id"),
                            task_id,
                            exc,
                        )

        # dedupe, preserve order
        seen: set[UUID] = set()
        unique = [nid for nid in resolved if not (nid in seen or seen.add(nid))]
        # only keep nodes that actually exist (protects against stale refs)
        existing: list[UUID] = []
        for node_id in unique:
            if await self.db.get(KnowledgeNode, node_id) is not None:
                existing.append(node_id)
        return existing

    async def _already_absorbed(self, user_id: UUID, node_id: UUID, outcome_id: str, task_marker: str | None) -> bool:
        """Append-only audit 门：该 outcome（或其同因任务面）已有 evidence 行？

        GUID-typed bindparams 让同一语句在 asyncpg（UUID 原生）与 aiosqlite
        （str 序列化）上都正确绑定——门不可读时 fail-closed（防双计优先）。
        """
        from sqlalchemy import text as sa_text

        try:
            stmt = sa_text(
                "SELECT request_id FROM mastery_audit_log "
                "WHERE user_id = :user_id AND node_id = :node_id AND reason = :reason"
            ).bindparams(
                bindparam("user_id", type_=GUID),
                bindparam("node_id", type_=GUID),
                bindparam("reason", type_=String),
            )
            result = await self.db.execute(
                stmt,
                {"user_id": user_id, "node_id": node_id, "reason": OUTCOME_EVIDENCE_AUDIT_REASON},
            )
            rows = list(result.fetchall() or [])
        except Exception as exc:  # noqa: BLE001 — 门不可读时 fail-closed（视为已吸收，防双计）
            logger.warning("absorption gate unreadable for node {}: {}", node_id, exc)
            return True
        outcome_marker = f"oc={_outcome_hex(outcome_id)}"
        task_hex = f"tk={_uuid_hex(task_marker)}" if task_marker else None
        for (request_id,) in rows:
            segments = _request_id_segments(request_id)
            if outcome_marker in segments:
                return True
            if task_hex is not None and task_hex in segments:
                # 同因合并：任务完成 outcome 与其 receipt outcome 是同一逻辑 outcome
                return True
        return False

    async def _get_or_create_status(self, user_id: UUID, node_id: UUID) -> UserNodeStatus:
        status = await self.db.get(UserNodeStatus, (user_id, node_id))
        if status is None:
            status = UserNodeStatus(
                user_id=user_id,
                node_id=node_id,
                mastery_score=0.0,
                is_unlocked=False,
            )
            self.db.add(status)
            await self.db.flush()
        return status


# ---------------------------------------------------------------------------
# Stream consumer wrapper (transport only; absorption logic is DB-real)
# ---------------------------------------------------------------------------


class OutcomeAbsorptionConsumer:
    """Subscribe to ``sparkle_events`` and route outcome.recorded → absorber.

    Same shape as ``TaskEventListener`` (session_factory + event_bus, own
    consumer group so Galaxy absorption is an independent delivery cursor).
    """

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "galaxy_outcome_absorber"

    def __init__(self, session_factory, event_bus: EventBus):
        self.session_factory = session_factory
        self.event_bus = event_bus
        self._running = False

    async def start(self):
        await self.event_bus.connect()
        self._running = True
        logger.info("OutcomeAbsorptionConsumer started on {}", self.STREAM_NAME)
        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"galaxy-outcome-absorber-{os.getpid()}",
                    callback=self._on_event,
                )
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("OutcomeAbsorptionConsumer subscribe error: {}", exc)
                await asyncio.sleep(1)

    async def _on_event(self, event_data: dict):
        """EVENT-ACK：吸收失败必须上抛——``EventBus._process_stream_message``
        会「不 ack（留 pending）→ 有界重试 → DLQ」。此前 blanket-except 把
        失败事件恒 ack（静默丢失——幂等门只防重复，救不回从未到达的吸收）；
        「单事件失败不拖垮消费循环」由总线 per-message 异常隔离保证，不在此
        处吞。吸收幂等（mastery_audit_log 行 + absorbed_outcomes 标记）保证
        重投递安全（at-least-once）。"""
        if event_data.get("event_type") != OUTCOME_RECORDED_EVENT:
            return
        async with self.session_factory() as db:
            absorber = GalaxyOutcomeAbsorber(db)
            result = await absorber.absorb_outcome(event_data)
            if result is not None:
                logger.info(
                    "outcome {} absorbed: action={} nodes={}",
                    result.outcome_id,
                    result.action,
                    result.node_ids,
                )

    def stop(self):
        self._running = False


# ---------------------------------------------------------------------------
# Payload/marker codecs (pure, unit-testable)
# ---------------------------------------------------------------------------


def _task_marker(payload: dict) -> str | None:
    raw = payload.get("correlation_task_id")
    return str(raw) if raw else None


def _num(value: float) -> str:
    """Compact numeric encoding: 60.0 → '60', 0.8 → '0.8'（float() 可逆）。"""
    text_value = f"{round(float(value), 2):g}"
    return text_value


def _outcome_hex(outcome_id: str) -> str:
    """``outc_<sha256[:32]>`` → 32 位 hex 段（request_id ≤100 列宽约束）。"""
    hex_part = outcome_id[len("outc_") :] if outcome_id.startswith("outc_") else outcome_id
    return hex_part[:32]


def _evidence_request_id(value: float, confidence: float, outcome_id: str, task_marker: str | None) -> str:
    """audit 行 request_id：G-01 观察负载（``obs=``/``conf=`` 键名固定，供
    ``parse_observation_payload`` 回放）+ 幂等标记段（``oc=``/``tk=``）。

    列宽 VARCHAR(100) 约束下的紧凑编码：``obs=60;conf=0.8;oc=<32hex>;tk=<32hex>``
    ≤ 88 字符；``oc`` 段 = outcome id 去掉 ``outc_`` 前缀的 32 位 hex（可逆：
    ``outc_<oc>``），``tk`` 段 = 任务 UUID 去连字符 hex。段匹配按 ``;`` 精确
    分段，不做子串包含（防 hex 碰撞误判同因）。
    """
    segments = [f"obs={_num(value)}", f"conf={_num(confidence)}", f"oc={_outcome_hex(outcome_id)}"]
    if task_marker:
        segments.append(f"tk={_uuid_hex(task_marker)}")
    return ";".join(segments)[:100]


def _uuid_hex(value: str) -> str:
    return str(value).replace("-", "").lower()


def _request_id_segments(request_id: str | None) -> list[str]:
    return str(request_id or "").split(";") if request_id else []


def _provenance_payload(payload: dict, *, replay: bool = False) -> dict:
    """溯源 payload：content-free（ids/极性/引用），与事件同构。"""
    data = {
        "outcome_id": payload.get("outcome_id"),
        "outcome_key": payload.get("outcome_key"),
        "source": payload.get("source"),
        "source_id": payload.get("source_id"),
        "source_ref": payload.get("source_ref"),
        "polarity": payload.get("polarity"),
    }
    task_marker = _task_marker(payload)
    if task_marker:
        data["task_id"] = task_marker
    if replay:
        data["replay"] = True
    return data


def _stamp_absorbed_marker(status: UserNodeStatus, outcome_id: str, payload: dict, *, action: str) -> None:
    """O(1) 极性翻转检测标记（snapshot 内，非真源；账本仍是点亮硬门）。

    snapshot 顶层**拷贝后**再赋值：JSON 列对同对象原地变更不产生 UPDATE
    （与 PlanStateService.facts / known_gaps 同款拷贝纪律），拷贝保证
    append_graph_event_source 的溯源行与本标记一起落库。
    """
    snapshot = getattr(status, "learning_path_snapshot", None)
    snapshot = dict(snapshot) if isinstance(snapshot, dict) else {}
    markers = snapshot.get(ABSORBED_OUTCOMES_SNAPSHOT_KEY)
    markers = dict(markers) if isinstance(markers, dict) else {}
    markers[outcome_id] = {
        "polarity": str(payload.get("polarity")),
        "action": action,
        "absorbed_at": _utcnow().isoformat(),
    }
    if len(markers) > ABSORBED_OUTCOMES_SNAPSHOT_CAP:
        for key in sorted(markers, key=lambda k: markers[k].get("absorbed_at") or "")[
            : len(markers) - ABSORBED_OUTCOMES_SNAPSHOT_CAP
        ]:
            markers.pop(key, None)
    snapshot[ABSORBED_OUTCOMES_SNAPSHOT_KEY] = markers
    status.learning_path_snapshot = snapshot


def _absorbed_marker_action(status: UserNodeStatus, outcome_id: str) -> str | None:
    snapshot = getattr(status, "learning_path_snapshot", None)
    if not isinstance(snapshot, dict):
        return None
    markers = snapshot.get(ABSORBED_OUTCOMES_SNAPSHOT_KEY)
    if not isinstance(markers, dict):
        return None
    marker = markers.get(outcome_id)
    return str(marker.get("action")) if isinstance(marker, dict) else None


def _parse_occurred_at(raw) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# NBP-4 · 读模型即时投影（写后失效；与吸收逻辑解耦的纯失效面）
# ---------------------------------------------------------------------------

#: 触发读面失效的吸收动作：``lit``（mastery/is_unlocked 变化——星图节点长大）
#: 与 ``flagged``（弱点标记变化——图读 review_signal 可见）。duplicate /
#: recorded_only / corrected / no_target 读面零变化，不产生失效流量。
_READ_MODEL_VISIBLE_ACTIONS = frozenset({"lit", "flagged"})


async def invalidate_galaxy_graph_view_cache(user_id: UUID) -> int:
    """失效星图读面视图缓存（NBP-4 写后即时投影的失效面）。

    读面 = ``GalaxyService.get_galaxy_graph`` 的 ``@cached`` 视图（键面前缀
    ``{APP_NAME}:view:get_galaxy_graph:{user_id}:*``，ttl=600）。吸收真源在
    DB，本函数只删缓存：失败由调用方降级（最坏退回 TTL 自然过期），不回滚
    吸收事务。返回删除的键数（观测用；Redis 不可达时为 0）。
    """
    from app.core.cache import cache_service
    from app.config import settings

    pattern = f"{settings.APP_NAME}:view:get_galaxy_graph:{user_id}:*"
    return await cache_service.delete_pattern(pattern)


__all__ = [
    "ABSORBED_OUTCOMES_SNAPSHOT_CAP",
    "ABSORBED_OUTCOMES_SNAPSHOT_KEY",
    "GalaxyOutcomeAbsorber",
    "OUTCOME_EVIDENCE_AUDIT_REASON",
    "OUTCOME_PROVENANCE_SOURCE_TYPE",
    "OutcomeAbsorptionConsumer",
    "OutcomeAbsorptionResult",
    "TASK_OUTCOME_EVIDENCE_CONFIDENCE",
    "TASK_OUTCOME_EVIDENCE_VALUE",
    "invalidate_galaxy_graph_view_cache",
]
