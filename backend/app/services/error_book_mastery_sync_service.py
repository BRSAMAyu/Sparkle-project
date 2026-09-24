"""
ErrorBookMasterySyncService — Bridges error evidence to knowledge node mastery.

This is断点2: 让错题证据正式写回知识节点掌握度。

Before this service:
  - Error book knows what the user got wrong (error_type, root_cause, linked nodes)
  - Galaxy knows what the user studied (task completion)
  - They never talked to each other in a meaningful way

After this service:
  - Error diagnosis → node mastery evidence-based decrease
  - Error review → node mastery recovery
  - Both flow into StudyRecord主干 and node_mastery_updated events

See: docs/product/implementation/ERROR_BOOK_TO_KNOWLEDGE_MASTERY_IMPLEMENTATION_2026-04-02.md
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from loguru import logger
from sqlalchemy import String, bindparam, func, select, text

from app.core.event_bus import NodeMasteryUpdatedEvent
from app.models.base import GUID
from app.models.card_protocol import Card, CardEdge, CardType, EdgeType
from app.models.error_book import ErrorRecord
from app.models.galaxy import StudyRecord, UserNodeStatus
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.galaxy.stats_service import GalaxyStatsService

# ---------------------------------------------------------------------------
# Error type → mastery impact weights
# ---------------------------------------------------------------------------

ERROR_TYPE_IMPACT: dict[str, int] = {
    "concept_confusion": -8,
    "knowledge_gap": -10,
    "method_wrong": -6,
    "logic_error": -5,
    "calculation_error": -3,
    "reading_careless": -2,
    "other": -3,
}

# Multi-node decay: how much of the base impact to apply per node rank
NODE_RANK_WEIGHTS = [1.0, 0.6, 0.3]

# Review performance → node mastery recovery
REVIEW_PERFORMANCE_IMPACT: dict[str, int] = {
    "remembered": 4,
    "fuzzy": 1,
    "forgotten": -2,
    "forgot": -2,
}
NO_LINKED_NODE_HINT = {
    "code": "missing_knowledge_links",
    "message": (
        "暂时没有关联到知识节点。补充学科/章节，或先到 Galaxy 关联课程后再分析，"
        "星图就能同步这道错题。"
    ),
    "action": "add_subject_or_link_course",
}

# Safety limits
MAX_SINGLE_ERROR_IMPACT = 10  # 单次错题最多对单节点扣10分
MIN_MASTERY_SCORE = 0
MAX_MASTERY_SCORE = 100
LOW_MASTERY_REPLAN_THRESHOLD = 50
ERROR_PRESSURE_LOOKBACK_DAYS = 7
ERROR_PRESSURE_TRIGGER_COUNT = 3

# ---------------------------------------------------------------------------
# ERR-IDEM · re-analyze 幂等键（吸收侧）
#
# 同一道错题再次触发分析（POST /errors/{id}/analyze → analyze_and_link →
# apply_error_diagnosis）此前会把 error_diagnosis 负反馈**再次**写进星图
# ——同一错题扣两次，直接损害「星图诚实反映掌握度」（期末一周里反复看
# 错题是正常行为）。CP-03 回执诚实申报的既有属性，本块负责去重：
#
# 天然键 = mastery_audit_log.request_id（每次成功的掌握度同步必留一行
# 审计，见 galaxy_service.update_node_mastery 第 B 步），键内容确定性
# 构造：record_type + error_id + 诊断内容指纹（+ review 表现）+ node_id。
# 内容未变的重复分析/复盘 → 命中已有键 → 跳过；内容变了（用户改了题目/
# 答案/图片）→ 指纹变化 → 作为新证据生效。
#
# 键采用紧凑编码（uuid 去连字符 + 8 位指纹段），满足 mastery_audit_log
# request_id 的 VARCHAR(100) 列宽：edi ≤ 78、erv ≤ 89 字符。
# ---------------------------------------------------------------------------

DIAGNOSIS_SYNC_KEY_PREFIX = "edi"
REVIEW_SYNC_KEY_PREFIX = "erv"
CONTENT_FINGERPRINT_LENGTH = 8


def _uuid_hex(value: Any) -> str:
    """UUID → 32 位无连字符 hex（列宽预算内的紧凑身份段）。"""
    return str(value).replace("-", "").lower()


def _normalize_fingerprint_part(value: Any) -> str:
    """指纹归一化：仅折叠空白，不做大小写折叠（改内容要能改出指纹）。"""
    return re.sub(r"\s+", " ", str(value or "").strip())


def diagnostic_content_fingerprint(error_record: Any) -> str:
    """诊断输入的内容指纹：题目/图片/作答/标准答案未变 → 指纹不变。

    question_image_url 参与指纹：图片错题的 OCR 文本可能有非确定性微扰，
    图片未换（引用未变）即视为内容未变；question_text 在首次分析后被
    OCR 回填（仅空时回填、一次性），不会造成重分析间的指纹漂移。
    """
    parts = [
        _normalize_fingerprint_part(getattr(error_record, "question_text", None)),
        _normalize_fingerprint_part(getattr(error_record, "question_image_url", None)),
        _normalize_fingerprint_part(getattr(error_record, "user_answer", None)),
        _normalize_fingerprint_part(getattr(error_record, "correct_answer", None)),
    ]
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest[:CONTENT_FINGERPRINT_LENGTH]


def diagnosis_request_key(error_id: Any, fingerprint: str, node_id: Any) -> str:
    """error_diagnosis 幂等键：``edi:<error_hex>:<fp>:<node_hex>``。

    刻意**不含** error_type：LLM/兜底对同一内容可能给出不同错因分类，
    分类抖动不应绕过幂等门造成二次扣分。
    """
    return f"{DIAGNOSIS_SYNC_KEY_PREFIX}:{_uuid_hex(error_id)}:{fingerprint}:{_uuid_hex(node_id)}"


def review_request_key(error_id: Any, fingerprint: str, performance: str, node_id: Any) -> str:
    """error_review 幂等键：``erv:<error_hex>:<fp>:<perf>:<node_hex>``。

    表现（remembered/fuzzy/forgotten）是键的一部分：不同表现是不同的
    逻辑证据，各自允许生效一次；同一表现重复提交（双击/重试）只生效
    一次。内容指纹变化开启新代际（改题后可再次回升）。
    """
    return (
        f"{REVIEW_SYNC_KEY_PREFIX}:{_uuid_hex(error_id)}:{fingerprint}:"
        f"{_normalize_fingerprint_part(performance)}:{_uuid_hex(node_id)}"
    )


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ErrorBookMasterySyncService:
    """Syncs error evidence to knowledge node mastery scores."""

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.stats_service = GalaxyStatsService(db)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def apply_error_diagnosis(
        self,
        user_id: UUID,
        error_record: Any,  # ErrorRecord from error_book models
    ) -> list[dict]:
        """Apply error diagnosis to linked knowledge nodes.

        Called after analyze_and_link() successfully writes linked_knowledge_node_ids.

        For each linked node:
        1. Calculate mastery delta based on error_type
        2. Update UserNodeStatus.mastery_score
        3. Write StudyRecord(record_type='error_diagnosis')
        4. Publish node_mastery_updated event

        Returns list of {node_id, old_mastery, new_mastery, delta} dicts.
        """
        linked_ids = getattr(error_record, "linked_knowledge_node_ids", None) or []
        if not linked_ids:
            self._attach_no_linked_node_hint(error_record)
            return []

        error_id = getattr(error_record, "id", None)
        error_type = self._extract_error_type(error_record)
        base_impact = ERROR_TYPE_IMPACT.get(error_type, -3)
        # ERR-IDEM：内容指纹一次计算，循环内按 (error, fp, node) 构键去重
        fingerprint = diagnostic_content_fingerprint(error_record) if error_id else ""

        results: list[dict] = []
        impacted_plan_ids: set[UUID] = set()
        for rank, node_id in enumerate(linked_ids[:3]):  # Max 3 nodes
            weight = NODE_RANK_WEIGHTS[rank] if rank < len(NODE_RANK_WEIGHTS) else 0.3
            delta = self._clamp_impact(round(base_impact * weight))

            node_result = await self._update_node_mastery(
                user_id=user_id,
                node_id=node_id,
                delta=delta,
                record_type="error_diagnosis",
                reason=f"error_diagnosis:{error_type}",
                error_id=error_id,
                request_key=(
                    diagnosis_request_key(error_id, fingerprint, node_id)
                    if error_id and fingerprint
                    else None
                ),
            )
            if node_result:
                results.append(node_result)
                impacted_plan_ids.update(
                    await self._identify_error_pressure_impacted_plans(
                        user_id=user_id,
                        node_id=node_id,
                        new_mastery=int(node_result["new_mastery"]),
                    )
                )

        if results:
            logger.info(
                "ErrorBookMasterySync: applied diagnosis for error {}, " "type={}, affected {} nodes",
                getattr(error_record, "id", "?"),
                error_type,
                len(results),
            )

        if impacted_plan_ids:
            await self._evaluate_impacted_plans(
                user_id=user_id,
                plan_ids=impacted_plan_ids,
                trigger="error_pressure",
                feedback_category="concept_gap_repeated",
            )

        return results

    async def apply_review_feedback(
        self,
        user_id: UUID,
        error_record: Any,
        performance: str,
    ) -> list[dict]:
        """Apply review feedback to linked knowledge nodes.

        Called after submit_review() updates error_record.mastery_level.

        Maps review performance to node mastery recovery:
        - remembered → +4
        - fuzzy → +1
        - forgot → -2

        Returns list of {node_id, old_mastery, new_mastery, delta} dicts.
        """
        linked_ids = getattr(error_record, "linked_knowledge_node_ids", None) or []
        if not linked_ids:
            self._attach_no_linked_node_hint(error_record)
            return []

        delta = REVIEW_PERFORMANCE_IMPACT.get(performance, 0)
        if delta == 0:
            return []

        error_id = getattr(error_record, "id", None)
        # ERR-IDEM：同一表现重复提交只生效一次；内容指纹开启新代际
        fingerprint = diagnostic_content_fingerprint(error_record) if error_id else ""

        results: list[dict] = []
        impacted_plan_ids: set[UUID] = set()
        for node_id in linked_ids[:3]:
            node_result = await self._update_node_mastery(
                user_id=user_id,
                node_id=node_id,
                delta=delta,
                record_type="error_review",
                reason=f"error_review:{performance}",
                error_id=error_id,
                request_key=(
                    review_request_key(error_id, fingerprint, performance, node_id)
                    if error_id and fingerprint
                    else None
                ),
            )
            if node_result:
                results.append(node_result)
                if performance in {"forgotten", "forgot", "fuzzy"}:
                    impacted_plan_ids.update(
                        await self._identify_error_pressure_impacted_plans(
                            user_id=user_id,
                            node_id=node_id,
                            new_mastery=int(node_result["new_mastery"]),
                        )
                    )

        if results:
            logger.info(
                "ErrorBookMasterySync: applied review feedback for error {}, " "performance={}, affected {} nodes",
                getattr(error_record, "id", "?"),
                performance,
                len(results),
            )

        if impacted_plan_ids:
            await self._evaluate_impacted_plans(
                user_id=user_id,
                plan_ids=impacted_plan_ids,
                trigger="error_review_pressure",
                feedback_category=f"review_{performance}",
            )

        return results

    # -----------------------------------------------------------------------
    # Core mastery update
    # -----------------------------------------------------------------------

    @staticmethod
    def _attach_no_linked_node_hint(error_record: Any) -> None:
        """Attach a response-visible hint when an error cannot affect Galaxy yet.

        latest_analysis 是 ErrorRecordResponse.latest_analysis (ErrorAnalysisResult)
        的数据源，必填字段缺失会让该错题的所有响应 500（round2 基线双 500 之一）。
        因此这里在注入 linking_hint 的同时补齐 schema 必填字段，保证落库的
        JSONB 永远是 schema-complete 的。
        """
        latest_analysis = getattr(error_record, "latest_analysis", None)
        if not isinstance(latest_analysis, dict):
            latest_analysis = {}
        updated_analysis = dict(latest_analysis)
        # Schema-complete defaults (matches ErrorAnalysisResult required fields).
        updated_analysis.setdefault("error_type", "other")
        updated_analysis.setdefault("error_type_label", "其他")
        updated_analysis.setdefault("root_cause", "暂无错因分析")
        updated_analysis.setdefault("correct_approach", "暂无解题思路")
        updated_analysis.setdefault("study_suggestion", "暂无学习建议")
        updated_analysis["linking_hint"] = dict(NO_LINKED_NODE_HINT)
        error_record.latest_analysis = updated_analysis

    async def _update_node_mastery(
        self,
        user_id: UUID,
        node_id: UUID,
        delta: int,
        record_type: str,
        reason: str,
        error_id: UUID | None = None,
        request_key: str | None = None,
    ) -> dict | None:
        """Update a single node's mastery and record the change.

        ERR-IDEM：``request_key`` 非空时先查 mastery_audit_log 幂等门，
        该键的同步已落账 → 直接跳过（不更新、不写 StudyRecord、不发事件、
        不触发计划压力评估），返回 None 由调用方按「本次无变化」处理。
        """
        if await self._sync_already_applied(user_id, node_id, request_key):
            logger.info(
                "ErrorBookMasterySync: duplicate {} skipped for error {}/node {} "
                "(idempotency key already in mastery_audit_log)",
                record_type,
                error_id,
                node_id,
            )
            return None

        status = await self._get_or_create_node_status(
            user_id,
            node_id,
            create_if_missing=False,
        )
        old_mastery = int(status.mastery_score or 0) if status else 0
        new_mastery = self._clamp_mastery(old_mastery + delta)

        if status is None and new_mastery == old_mastery:
            return None

        if status is None:
            status = await self._get_or_create_node_status(
                user_id,
                node_id,
                create_if_missing=True,
            )
            if not status:
                logger.warning(
                    "ErrorBookMasterySync: could not create status for user={}/node={}",
                    user_id,
                    node_id,
                )
                return None

        if new_mastery == old_mastery:
            return None

        revision = getattr(status, "revision", None)
        # request_id：幂等键优先（审计行即天然去重账本）；无键时保持旧格式
        request_id = request_key or (
            f"{record_type}:{error_id}:{node_id}" if error_id else f"{record_type}:{node_id}"
        )
        update_result = await self._write_node_mastery_via_galaxy(
            user_id=user_id,
            node_id=node_id,
            new_mastery=new_mastery,
            reason=reason,
            request_id=request_id,
            revision=int(revision) if revision is not None else None,
        )
        if not update_result or update_result.get("success") is False:
            if update_result and update_result.get("reason") == "duplicate":
                # ERR-IDEM-CONCUR：写侧唯一索引仲裁的败者——毫秒窗口内另一
                # 个同键并发请求先落账。与读侧门命中同一结局：返回 None，
                # 调用方按「本次无变化」处理（掌握度已由胜者写定）。
                logger.info(
                    "ErrorBookMasterySync: {} lost write-side idempotency race for "
                    "error {}/node {} (audit unique index already holds the key)",
                    record_type,
                    error_id,
                    node_id,
                )
            else:
                logger.warning(
                    "ErrorBookMasterySync: GalaxyService rejected mastery update for user={}/node={}, reason={}",
                    user_id,
                    node_id,
                    (update_result or {}).get("reason"),
                )
            return None

        old_mastery = int(round(float(update_result.get("old_mastery", old_mastery) or 0)))
        new_mastery = int(round(float(update_result.get("new_mastery", new_mastery) or 0)))

        refreshed_status = await self._get_or_create_node_status(
            user_id,
            node_id,
            create_if_missing=False,
        )
        if refreshed_status is not None:
            refreshed_status.study_count = (refreshed_status.study_count or 0) + 1
            refreshed_status.next_review_at = self.stats_service._calculate_next_review(float(new_mastery))

        # 4. Write StudyRecord
        study_record = StudyRecord(
            user_id=user_id,
            node_id=node_id,
            study_minutes=0,
            mastery_delta=float(new_mastery - old_mastery),
            initial_mastery=float(old_mastery),
            record_type=record_type,
        )
        self.db.add(study_record)

        # 5. Defer event publish — caller commits then flushes pending events (fix #1)
        pending_event = {
            "topic": "node_mastery_updated",
            "payload": NodeMasteryUpdatedEvent(
                user_id=str(user_id),
                node_id=str(node_id),
                old_mastery=old_mastery,
                new_mastery=new_mastery,
                reason=reason,
            ).to_dict(),
        }

        return {
            "node_id": str(node_id),
            "error_id": str(error_id) if error_id else None,
            "old_mastery": old_mastery,
            "new_mastery": new_mastery,
            "delta": new_mastery - old_mastery,
            "record_type": record_type,
            "_pending_event": pending_event,
        }

    async def _write_node_mastery_via_galaxy(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        new_mastery: int,
        reason: str,
        request_id: str,
        revision: int | None,
    ) -> dict | None:
        from app.services.galaxy_service import GalaxyService

        return cast("dict[Any, Any] | None", (await GalaxyService(self.db).update_node_mastery(
            user_id=user_id,
            node_id=node_id,
            new_mastery=new_mastery,
            reason=reason,
            request_id=request_id,
            revision=revision,
        )))

    async def _sync_already_applied(self, user_id: UUID, node_id: UUID, request_key: str | None) -> bool:
        """ERR-IDEM 幂等门：该 (user, node, request_key) 的同步是否已落账。

        天然键 = mastery_audit_log.request_id——每次成功的掌握度同步都会
        经 galaxy_service.update_node_mastery 追加一行带 request_id 的
        append-only 审计行，键由 (record_type, error_id, 内容指纹
        [, review 表现], node_id) 确定性构成，重放同键即同一次同步。

        键为空 → 不设门（无 error_id 的合成调用保持旧行为）；门不可读
        （表未建/查询异常）→ **fail-open 放行**并告警：宁可放行一次重复、
        不可让门故障把掌握度同步整体静默吞掉（与 outcome_absorber
        「audit 写失败不阻断吸收」同一降级方向）。
        """
        if not request_key:
            return False
        try:
            stmt = text(
                "SELECT request_id FROM mastery_audit_log "
                "WHERE user_id = :user_id AND node_id = :node_id AND request_id = :request_key LIMIT 1"
            ).bindparams(
                bindparam("user_id", type_=GUID),
                bindparam("node_id", type_=GUID),
                bindparam("request_key", type_=String),
            )
            result = await self.db.execute(
                stmt,
                {"user_id": user_id, "node_id": node_id, "request_key": request_key},
            )
            return result.scalar_one_or_none() is not None
        except Exception as exc:  # noqa: BLE001 — 门不可读时 fail-open（见 docstring）
            logger.warning(
                "ErrorBookMasterySync: idempotency gate unreadable, failing open: {}", exc
            )
            return False

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    async def _get_or_create_node_status(
        self,
        user_id: UUID,
        node_id: UUID,
        *,
        create_if_missing: bool = True,
    ) -> UserNodeStatus | None:
        """Get existing UserNodeStatus or create a new one."""
        try:
            result = await self.db.execute(
                select(UserNodeStatus).where(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.node_id == node_id,
                )
            )
            status = result.scalar_one_or_none()
            if status:
                return cast("UserNodeStatus | None", (status))
            if not create_if_missing:
                return None

            # Create new — but do NOT auto-unlock (fix #2):
            # A node linked via error diagnosis with 0 mastery has no evidence yet.
            # It enters the user's awareness via the StudyRecord but stays locked
            # until positive evidence (task completion or review recovery) unlocks it.
            status = UserNodeStatus(
                user_id=user_id,
                node_id=node_id,
                mastery_score=0,
                is_unlocked=False,
                study_count=0,
                bkt_mastery_prob=0.0,
            )
            self.db.add(status)
            # Flush to get the object into session
            await self.db.flush()
            return status
        except Exception as exc:
            logger.warning(
                "ErrorBookMasterySync: get/create failed for {}/{}: {}",
                user_id,
                node_id,
                exc,
            )
            return None

    def _extract_error_type(self, error_record: Any) -> str:
        """Extract error_type from the error record's latest_analysis."""
        analysis = getattr(error_record, "latest_analysis", None) or {}
        if isinstance(analysis, dict):
            return cast("str", (analysis.get("error_type", "other")))
        return "other"

    async def _identify_error_pressure_impacted_plans(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        new_mastery: int,
    ) -> set[UUID]:
        """Return active plan ids that should be evaluated immediately."""
        if new_mastery >= LOW_MASTERY_REPLAN_THRESHOLD:
            return set()

        recent_error_count = await self._count_recent_errors_for_node(
            user_id=user_id,
            node_id=node_id,
            days=ERROR_PRESSURE_LOOKBACK_DAYS,
        )
        if recent_error_count < ERROR_PRESSURE_TRIGGER_COUNT:
            return set()

        impacted_plan_ids = await self._find_impacted_active_plans(user_id=user_id, node_id=node_id)
        if impacted_plan_ids:
            logger.info(
                "ErrorBookMasterySync: node {} crossed repeated-error pressure "
                "(mastery={}, errors_{}d={}) -> {} impacted plan(s)",
                node_id,
                new_mastery,
                ERROR_PRESSURE_LOOKBACK_DAYS,
                recent_error_count,
                len(impacted_plan_ids),
            )
        return impacted_plan_ids

    async def _count_recent_errors_for_node(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        days: int,
    ) -> int:
        cutoff = _utcnow() - timedelta(days=days)
        try:
            stmt = (
                select(func.count(ErrorRecord.id))
                .where(ErrorRecord.user_id == user_id)
                .where(ErrorRecord.is_deleted.is_(False))
                .where(ErrorRecord.created_at >= cutoff)
                .where(ErrorRecord.linked_knowledge_node_ids.contains([node_id]))
            )
            result = await self.db.execute(stmt)
            return int(result.scalar() or 0)
        except Exception:
            result = await self.db.execute(
                select(ErrorRecord.created_at, ErrorRecord.linked_knowledge_node_ids)
                .where(ErrorRecord.user_id == user_id)
                .where(ErrorRecord.is_deleted.is_(False))
            )
            count = 0
            for created_at, linked_ids in result.all():
                normalized_created_at = created_at
                if normalized_created_at and normalized_created_at.tzinfo is not None:
                    normalized_created_at = normalized_created_at.replace(tzinfo=None)
                if normalized_created_at and normalized_created_at < cutoff:
                    continue
                if str(node_id) in [str(value) for value in (linked_ids or []) if value is not None]:
                    count += 1
            return count

    async def _find_impacted_active_plans(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
    ) -> set[UUID]:
        plan_ids = await self._find_impacted_active_plans_via_cards(user_id=user_id, node_id=node_id)
        if plan_ids:
            return plan_ids
        return await self._find_impacted_active_plans_via_tasks(user_id=user_id, node_id=node_id)

    async def _find_impacted_active_plans_via_cards(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
    ) -> set[UUID]:
        stmt = select(Card.id).where(
            Card.card_type == CardType.KNOWLEDGE,
            Card.owner_id == user_id,
            Card.metadata_["knowledge_node_id"].as_string() == str(node_id),
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        knowledge_card_ids = list(result.scalars().all())
        if not knowledge_card_ids:
            return set()

        edge_stmt = (
            select(Card.metadata_["legacy_task_id"].as_string())
            .select_from(CardEdge)
            .join(Card, Card.id == CardEdge.from_card_id)
            .where(
                CardEdge.edge_type == EdgeType.REFERENCES,
                CardEdge.active.is_(True),
                CardEdge.to_card_id.in_(knowledge_card_ids),
                Card.card_type == CardType.TASK,
                Card.owner_id == user_id,
                Card.not_deleted_filter(),
            )
        )
        edge_result = await self.db.execute(edge_stmt)
        legacy_task_ids = [value for value in edge_result.scalars().all() if value]
        if not legacy_task_ids:
            return set()

        return await self._active_plan_ids_for_task_ids(user_id=user_id, legacy_task_ids=legacy_task_ids)

    async def _find_impacted_active_plans_via_tasks(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
    ) -> set[UUID]:
        today = date.today()
        stmt = (
            select(Task.plan_id)
            .join(Plan, Plan.id == Task.plan_id)
            .where(
                Task.user_id == user_id,
                Task.knowledge_node_id == node_id,
                Task.plan_id.is_not(None),
                Task.status.in_((TaskStatus.PENDING, TaskStatus.IN_PROGRESS)),
                Plan.user_id == user_id,
                Plan.is_active.is_(True),
            )
            .where((Task.due_date.is_(None)) | (Task.due_date >= today))
        )
        result = await self.db.execute(stmt)
        return {plan_id for plan_id in result.scalars().all() if plan_id is not None}

    async def _active_plan_ids_for_task_ids(
        self,
        *,
        user_id: UUID,
        legacy_task_ids: list[str],
    ) -> set[UUID]:
        task_ids: list[UUID] = []
        for raw_task_id in legacy_task_ids:
            try:
                task_ids.append(UUID(str(raw_task_id)))
            except (TypeError, ValueError):
                continue
        if not task_ids:
            return set()

        today = date.today()
        stmt = (
            select(Task.plan_id)
            .join(Plan, Plan.id == Task.plan_id)
            .where(
                Task.id.in_(task_ids),
                Task.user_id == user_id,
                Task.plan_id.is_not(None),
                Task.status.in_((TaskStatus.PENDING, TaskStatus.IN_PROGRESS)),
                Plan.user_id == user_id,
                Plan.is_active.is_(True),
            )
            .where((Task.due_date.is_(None)) | (Task.due_date >= today))
        )
        result = await self.db.execute(stmt)
        return {plan_id for plan_id in result.scalars().all() if plan_id is not None}

    async def _evaluate_impacted_plans(
        self,
        *,
        user_id: UUID,
        plan_ids: set[UUID],
        trigger: str,
        feedback_category: str | None = None,
    ) -> None:
        replanner = AdaptiveReplanner(self.db, self.redis)
        for plan_id in sorted(plan_ids, key=str):
            try:
                await replanner.evaluate_plan_health_now(
                    user_id=user_id,
                    plan_id=plan_id,
                    trigger=trigger,
                    feedback_category=feedback_category,
                )
            except Exception as exc:
                logger.warning(
                    "ErrorBookMasterySync: immediate plan health evaluation failed " "for user={}/plan={}: {}",
                    user_id,
                    plan_id,
                    exc,
                )

    @staticmethod
    def _clamp_impact(value: int) -> int:
        """Clamp single-impact to safety range."""
        return max(-MAX_SINGLE_ERROR_IMPACT, min(MAX_SINGLE_ERROR_IMPACT, value))

    @staticmethod
    def _clamp_mastery(value: int) -> int:
        """Clamp mastery to 0-100 range."""
        return max(MIN_MASTERY_SCORE, min(MAX_MASTERY_SCORE, value))
