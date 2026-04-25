from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, select

from app.core.metrics import (
    ERROR_REPLAN_BRIDGE_BLOCKED_BY_GATE_TOTAL,
    ERROR_REPLAN_BRIDGE_ERROR_TOTAL,
    ERROR_REPLAN_BRIDGE_EVALUATED_TOTAL,
    ERROR_REPLAN_BRIDGE_TRIGGERED_TOTAL,
)
from app.models.card_protocol import InterventionRecord
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.models.card_protocol import DeliveryChannel, DeliveryStrategy, InterventionTriggerType
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.aurora_stage38_kill_switch_service import AuroraStage38KillSwitchService
from app.services.intervention_record_service import InterventionRecordService
from app.services.route_history_service import RouteHistoryService

# Preserve the Stage 34 patch target while Stage 38 owns the live kill-switch path.
AuroraStage34KillSwitchService = AuroraStage38KillSwitchService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BridgeEvaluationError(RuntimeError):
    """Raised when Stage34 bridge evaluation cannot be computed safely."""


class PlanHealthError(RuntimeError):
    """Raised when AdaptiveReplanner evaluation fails for an eligible plan."""


@dataclass(frozen=True)
class ErrorPressureDecision:
    triggered: bool
    threshold: int
    recent_error_count: int


@dataclass(frozen=True)
class MistakeClusterMatch:
    cluster_id: str
    cluster_label: str
    related_nodes: tuple[str, ...]
    related_node_labels: tuple[str, ...]
    source: str
    repair_strategy: str
    task_template_id: str
    pack_id: str | None
    streak_count: int
    matched_keywords: tuple[str, ...]
    matched_node_names: tuple[str, ...]
    db_node_ids: tuple[str, ...]


class ErrorReplanBridge:
    """Separates ErrorCreated -> immediate plan-health evaluation from mastery sync."""

    LOW_MASTERY_THRESHOLD = 50.0
    REPLAN_MASTERY_THRESHOLD = 40.0
    ERROR_PRESSURE_LOOKBACK_DAYS = 7
    ERROR_PRESSURE_TRIGGER_COUNT = 3
    HIGH_SEVERITY_TRIGGER_COUNT = 2
    COOLDOWN_HOURS = 24
    TRIGGERING_ERROR_TYPES = {
        "concept_confusion",
        "repeated_mistake",
        "baseline_gap",
        "comprehension_failure",
        "time_pressure_miss",
        "knowledge_transfer_fail",
        "prerequisite_missing",
        "careless_error",
    }
    REPLAN_ELIGIBLE_ERROR_TYPES = TRIGGERING_ERROR_TYPES - {"careless_error"}
    HIGH_SEVERITY_VALUES = {"high", "critical", "severe", "urgent", "error", "3", "4", "5"}
    SPECIALIZED_REPAIR_DURATION_MINUTES = 30
    SPECIALIZED_REPAIR_SCHEDULE_OPTIONS = ("today", "tomorrow")
    NETWORK_PACK_SUBJECT = "计算机网络"
    NETWORK_PACK_SIGNAL_TOKENS = (
        "计算机网络",
        "计网",
        "network",
        "tcp",
        "udp",
        "ip",
        "三次握手",
        "四次挥手",
        "拥塞控制",
        "滑动窗口",
        "确认号",
        "ack",
        "syn",
        "fin",
    )
    PACK_NODE_HINTS: dict[str, tuple[str, ...]] = {
        "cn.tcp_basics": ("tcp基础", "tcp首部", "端口号", "tcp特点"),
        "cn.tcp_three_way": ("三次握手", "syn", "synack", "建立连接"),
        "cn.tcp_four_way": ("四次挥手", "fin", "timewait", "2msl", "关闭连接"),
        "cn.tcp_reliable_transport": ("ack", "确认号", "累计确认", "序号", "seq", "重传"),
        "cn.tcp_flow_control": ("滑动窗口", "流量控制", "rwnd", "窗口大小"),
        "cn.tcp_congestion_control": (
            "拥塞控制",
            "慢启动",
            "拥塞避免",
            "快重传",
            "快恢复",
            "重复ack",
            "3重复ack",
            "cwnd",
            "ssthresh",
            "超时重传",
        ),
    }
    GENERIC_MISTAKE_FALLBACKS: tuple[dict[str, Any], ...] = (
        {
            "cluster_id": "generic.state_transition",
            "label": "状态变化与流程切换",
            "keywords": (
                "状态变化",
                "状态转换",
                "状态切换",
                "流程变化",
                "流程图",
                "state transition",
                "transition",
            ),
            "repair_strategy": "重画完整状态/流程图，标出每一步的触发条件和切换依据。",
            "task_template_id": "process_trace_card",
        },
        {
            "cluster_id": "generic.unit_conversion",
            "label": "单位换算",
            "keywords": ("单位换算", "bit", "byte", "kb", "mb", "gb", "ms", "秒", "字节", "比特"),
            "repair_strategy": "先列单位换算关系，再做 2 道同型题，把每一步换算依据写出来。",
            "task_template_id": "calculation_drill_card",
        },
        {
            "cluster_id": "generic.formula_application",
            "label": "公式套用与变形",
            "keywords": ("公式", "代入", "变形", "推导", "计算步骤"),
            "repair_strategy": "先写出公式和适用条件，再做 2 道只验证公式选择与代入的同型题。",
            "task_template_id": "calculation_drill_card",
        },
    )

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis

    async def on_error_created(
        self,
        *,
        user_id: UUID,
        error_id: UUID,
        linked_node_ids: list[UUID],
    ) -> dict[str, object]:
        mode = "shadow"
        try:
            mode = await AuroraStage38KillSwitchService().get_feature_mode("err_replan")
            ERROR_REPLAN_BRIDGE_EVALUATED_TOTAL.labels(mode=mode).inc()
            normalized_node_ids = [node_id for node_id in linked_node_ids if node_id]
            if not normalized_node_ids:
                return self._blocked(mode=mode, gate="no_linked_nodes")

            error = await self.db.get(ErrorRecord, error_id)
            if error is None or error.user_id != user_id:
                return self._blocked(mode=mode, gate="error_not_found")

            error_type = self._classify_trigger_type(error)
            if error_type is None:
                return self._blocked(
                    mode=mode,
                    gate="unsupported_error_type",
                    reason=f"unsupported_error_type:{self._extract_error_type(error)}",
                )

            try:
                recent_error_count = await self._count_recent_triggering_errors(
                    user_id=user_id,
                    node_ids=normalized_node_ids,
                    days=self.ERROR_PRESSURE_LOOKBACK_DAYS,
                )
                error_concept = await self._resolve_error_concept(error, normalized_node_ids)
                mastery_update = await self._update_mastery_from_error(
                    user_id=user_id,
                    knowledge_node_id=normalized_node_ids[0],
                    knowledge_node_name=error_concept,
                    error_type=error_type,
                    error_count=recent_error_count,
                )
                await self._record_error_mastery_echo(
                    error=error,
                    mastery_update=mastery_update,
                    fallback_node_id=normalized_node_ids[0],
                )
                node_mastery_scores = await self._get_node_mastery_scores(
                    user_id=user_id,
                    node_ids=normalized_node_ids,
                )
                is_new_user = await self._is_new_user(user_id)
            except Exception as exc:
                raise BridgeEvaluationError("stage34_bridge_evaluation_failed") from exc

            if error_type == "careless_error":
                return self._blocked(
                    mode=mode,
                    gate="careless_error_no_replan",
                    mastery_update=mastery_update,
                    recent_error_count=recent_error_count,
                )

            plan_ids = await self._find_relevant_active_plan_ids(user_id=user_id, node_ids=normalized_node_ids)
            if not plan_ids:
                return self._blocked(
                    mode=mode,
                    gate="no_relevant_active_plan",
                    mastery_update=mastery_update,
                    recent_error_count=recent_error_count,
                )

            eligible_plan_ids = await self._filter_plan_ids_by_cooldown(
                user_id=user_id,
                plan_ids=plan_ids,
                error_type=error_type,
            )
            if not eligible_plan_ids:
                return self._blocked(
                    mode=mode,
                    gate="trigger_cooldown_active",
                    mastery_update=mastery_update,
                    recent_error_count=recent_error_count,
                )

            specialized_match = await self._build_specialized_repair_match(
                user_id=user_id,
                error=error,
                fallback_node_ids=normalized_node_ids,
            )
            if specialized_match is not None and specialized_match.streak_count >= self.ERROR_PRESSURE_TRIGGER_COUNT:
                primary_plan_id = await self._select_primary_plan_id(user_id=user_id, plan_ids=eligible_plan_ids)
                intervention_id, notification_id = await self._create_specialized_repair_intervention(
                    user_id=user_id,
                    error_type=error_type,
                    recent_error_count=recent_error_count,
                    plan_id=primary_plan_id,
                    match=specialized_match,
                    cohort_profile=await self._get_cohort_profile(user_id),
                )
                logger.info(
                    "ErrorReplanBridge: proposed specialized repair for user={} error={} cluster={} streak={} plan={}",
                    user_id,
                    error_id,
                    specialized_match.cluster_id,
                    specialized_match.streak_count,
                    primary_plan_id,
                )
                ERROR_REPLAN_BRIDGE_TRIGGERED_TOTAL.labels(mode=mode).inc()
                return {
                    "triggered": True,
                    "reason": "specialized_error_repair",
                    "plan_ids": [str(primary_plan_id)] if primary_plan_id else [],
                    "recent_error_count": recent_error_count,
                    "same_cluster_streak": specialized_match.streak_count,
                    "repair_cluster_id": specialized_match.cluster_id,
                    "repair_cluster_label": specialized_match.cluster_label,
                    "repair_cluster_source": specialized_match.source,
                    "threshold_applied": self.ERROR_PRESSURE_TRIGGER_COUNT,
                    "is_new_user": is_new_user,
                    "mastery_update": mastery_update,
                    "intervention_id": intervention_id,
                    "notification_id": notification_id,
                    "mode": mode,
                }

            low_mastery_nodes = [
                node_id
                for node_id in normalized_node_ids
                if node_mastery_scores.get(node_id, 100.0) < self.REPLAN_MASTERY_THRESHOLD
            ]
            high_severity_decision = ErrorPressureDecision(
                triggered=self._is_high_severity(error) and recent_error_count >= self.HIGH_SEVERITY_TRIGGER_COUNT,
                threshold=self.HIGH_SEVERITY_TRIGGER_COUNT,
                recent_error_count=recent_error_count,
            )
            legacy_decision = ErrorPressureDecision(
                triggered=bool(low_mastery_nodes) and recent_error_count >= self.ERROR_PRESSURE_TRIGGER_COUNT,
                threshold=self.ERROR_PRESSURE_TRIGGER_COUNT,
                recent_error_count=recent_error_count,
            )
            stage34_threshold = 1 if is_new_user else self.ERROR_PRESSURE_TRIGGER_COUNT
            stage34_decision = ErrorPressureDecision(
                triggered=bool(low_mastery_nodes) and recent_error_count >= stage34_threshold,
                threshold=stage34_threshold,
                recent_error_count=recent_error_count,
            )

            if mode == "shadow":
                await self._record_shadow_decision(
                    user_id=user_id,
                    error_id=error_id,
                    error_type=error_type,
                    plan_ids=eligible_plan_ids,
                    is_new_user=is_new_user,
                    legacy_decision=legacy_decision,
                    stage34_decision=stage34_decision,
                )
                effective_decision = legacy_decision
            elif mode == "live":
                effective_decision = stage34_decision
            else:
                effective_decision = legacy_decision

            mastery_floor_decision = (
                mastery_update is not None
                and float(mastery_update["new_mastery"]) < self.REPLAN_MASTERY_THRESHOLD
                and recent_error_count >= self.ERROR_PRESSURE_TRIGGER_COUNT
            )
            if high_severity_decision.triggered:
                effective_decision = high_severity_decision
            if mastery_floor_decision and not effective_decision.triggered:
                effective_decision = ErrorPressureDecision(
                    triggered=True,
                    threshold=self.ERROR_PRESSURE_TRIGGER_COUNT,
                    recent_error_count=recent_error_count,
                )

            if not effective_decision.triggered:
                gate = (
                    "mastery_not_low"
                    if not low_mastery_nodes and not high_severity_decision.triggered
                    else "insufficient_error_pressure"
                )
                return self._blocked(
                    mode=mode,
                    gate=gate,
                    plan_ids=[],
                    recent_error_count=recent_error_count,
                    threshold_applied=effective_decision.threshold,
                    is_new_user=is_new_user,
                    mastery_update=mastery_update,
                )

            replanner = AdaptiveReplanner(self.db, self.redis)
            triggered_plan_ids: list[str] = []
            for plan_id in sorted(eligible_plan_ids, key=str):
                try:
                    await replanner.evaluate_plan_health_now(
                        user_id=user_id,
                        plan_id=plan_id,
                        trigger="error_created_bridge",
                        feedback_category="concept_gap_repeated",
                    )
                except Exception as exc:
                    raise PlanHealthError(f"plan_health_eval_failed:{plan_id}") from exc
                triggered_plan_ids.append(str(plan_id))

            intervention_id = await self._create_error_intervention_record(
                user_id=user_id,
                low_mastery_nodes=low_mastery_nodes or normalized_node_ids,
                recent_error_count=recent_error_count,
                plan_ids=triggered_plan_ids,
                error_type=error_type,
            )

            await self._notify_plan_adjusted(
                user_id=user_id,
                low_mastery_nodes=low_mastery_nodes or normalized_node_ids,
                recent_error_count=recent_error_count,
                intervention_id=intervention_id,
            )

            logger.info(
                "ErrorReplanBridge: triggered immediate plan-health evaluation for user={} error={} plans={} count={} mode={} threshold={}",
                user_id,
                error_id,
                len(triggered_plan_ids),
                recent_error_count,
                mode,
                effective_decision.threshold,
            )
            ERROR_REPLAN_BRIDGE_TRIGGERED_TOTAL.labels(mode=mode).inc()
            return {
                "triggered": True,
                "reason": "error_pressure_bridge",
                "plan_ids": triggered_plan_ids,
                "recent_error_count": recent_error_count,
                "threshold_applied": effective_decision.threshold,
                "is_new_user": is_new_user,
                "mastery_update": mastery_update,
                "mode": mode,
            }
        except BridgeEvaluationError as exc:
            ERROR_REPLAN_BRIDGE_ERROR_TOTAL.labels(category="BridgeEvaluationError", mode=mode).inc()
            logger.warning("ErrorReplanBridge evaluation failed for user {}: {}", user_id, exc)
            await self._notify_bridge_failure(user_id=user_id, category="BridgeEvaluationError", error=str(exc))
            return {"triggered": False, "reason": "bridge_evaluation_error", "plan_ids": []}
        except PlanHealthError as exc:
            ERROR_REPLAN_BRIDGE_ERROR_TOTAL.labels(category="PlanHealthError", mode=mode).inc()
            logger.warning("ErrorReplanBridge plan-health evaluation failed for user {}: {}", user_id, exc)
            await self._notify_bridge_failure(user_id=user_id, category="PlanHealthError", error=str(exc))
            return {"triggered": False, "reason": "plan_health_error", "plan_ids": []}
        except Exception as exc:
            ERROR_REPLAN_BRIDGE_ERROR_TOTAL.labels(category="UnknownError", mode=mode).inc()
            logger.exception("ErrorReplanBridge unknown failure for user {}", user_id)
            await self._notify_bridge_failure(user_id=user_id, category="UnknownError", error=str(exc))
            return {"triggered": False, "reason": "unknown_error", "plan_ids": []}

    async def _build_specialized_repair_match(
        self,
        *,
        user_id: UUID,
        error: ErrorRecord,
        fallback_node_ids: list[UUID],
    ) -> MistakeClusterMatch | None:
        recent_errors = await self._load_recent_user_errors(
            user_id=user_id,
            days=self.ERROR_PRESSURE_LOOKBACK_DAYS,
            limit=8,
        )
        if not recent_errors:
            recent_errors = [error]

        node_name_map = await self._load_node_name_map_for_errors(recent_errors)
        latest_match = self._match_sprint_pack_cluster(error, node_name_map)
        if latest_match is None:
            latest_match = self._match_generic_cluster(error, node_name_map, fallback_node_ids=fallback_node_ids)
        if latest_match is None:
            return None

        streak = 0
        for recent_error in recent_errors:
            analysis = recent_error.latest_analysis if isinstance(recent_error.latest_analysis, dict) else {}
            if self._classify_trigger_type_from_analysis(analysis) not in self.REPLAN_ELIGIBLE_ERROR_TYPES:
                break

            candidate = self._match_sprint_pack_cluster(recent_error, node_name_map)
            if candidate is None:
                candidate = self._match_generic_cluster(
                    recent_error,
                    node_name_map,
                    fallback_node_ids=[
                        self._coerce_uuid(value)
                        for value in (recent_error.linked_knowledge_node_ids or [])
                        if self._coerce_uuid(value) is not None
                    ],
                )
            if candidate is None or candidate.cluster_id != latest_match.cluster_id:
                break
            streak += 1

        if streak < self.ERROR_PRESSURE_TRIGGER_COUNT:
            return None

        return MistakeClusterMatch(
            cluster_id=latest_match.cluster_id,
            cluster_label=latest_match.cluster_label,
            related_nodes=latest_match.related_nodes,
            related_node_labels=latest_match.related_node_labels,
            source=latest_match.source,
            repair_strategy=latest_match.repair_strategy,
            task_template_id=latest_match.task_template_id,
            pack_id=latest_match.pack_id,
            streak_count=streak,
            matched_keywords=latest_match.matched_keywords,
            matched_node_names=latest_match.matched_node_names,
            db_node_ids=latest_match.db_node_ids,
        )

    async def _load_recent_user_errors(
        self,
        *,
        user_id: UUID,
        days: int,
        limit: int = 8,
    ) -> list[ErrorRecord]:
        cutoff = _utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(ErrorRecord)
            .where(
                ErrorRecord.user_id == user_id,
                ErrorRecord.is_deleted.is_(False),
                ErrorRecord.created_at >= cutoff,
            )
            .order_by(desc(ErrorRecord.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _load_node_name_map_for_errors(self, errors: list[ErrorRecord]) -> dict[str, str]:
        node_ids: set[UUID] = set()
        for error in errors:
            for value in error.linked_knowledge_node_ids or []:
                node_id = self._coerce_uuid(value)
                if isinstance(node_id, UUID):
                    node_ids.add(node_id)

        if not node_ids:
            return {}

        result = await self.db.execute(
            select(KnowledgeNode.id, KnowledgeNode.name).where(KnowledgeNode.id.in_(node_ids))
        )
        return {
            str(node_id): str(node_name or "").strip()
            for node_id, node_name in result.all()
            if node_id is not None and str(node_name or "").strip()
        }

    def _match_sprint_pack_cluster(
        self,
        error: ErrorRecord,
        node_name_map: dict[str, str],
    ) -> MistakeClusterMatch | None:
        feature_bundle = self._extract_error_feature_bundle(error, node_name_map)
        feature_text = str(feature_bundle["raw_text"])
        if not self._looks_like_network_pack_candidate(feature_text):
            return None

        try:
            from app.sprint_packs.sprint_pack_loader import get_task_template, load_pack

            pack = load_pack(self.NETWORK_PACK_SUBJECT)
        except Exception:
            pack = None
            get_task_template = None  # type: ignore[assignment]

        if not pack:
            return None

        matched_pack_nodes = self._match_pack_nodes(pack, feature_bundle)
        if not matched_pack_nodes:
            return None

        pack_nodes_by_id = {
            str(node.get("node_id") or ""): node
            for node in pack.get("knowledge_nodes", [])
            if str(node.get("node_id") or "").strip()
        }
        best_match: MistakeClusterMatch | None = None
        best_score = 0

        for cluster in list(pack.get("mistake_taxonomy") or pack.get("mistake_types") or []):
            related_nodes = tuple(
                str(node_id).strip()
                for node_id in (cluster.get("related_nodes") or [])
                if str(node_id).strip()
            )
            if not related_nodes:
                continue

            overlap = tuple(node_id for node_id in related_nodes if node_id in matched_pack_nodes)
            if not overlap:
                continue

            keyword_hits = tuple(
                self._keyword_hits(
                    feature_text,
                    cluster.get("keywords")
                    or self._keywords_from_free_text(
                        " ".join(
                            filter(
                                None,
                                (
                                    cluster.get("mistake_id"),
                                    cluster.get("label"),
                                    cluster.get("repair_strategy"),
                                ),
                            )
                        )
                    ),
                )
            )
            score = len(overlap) * 10 + len(keyword_hits)
            if score < best_score:
                continue

            template_id = self._template_id_for_cluster(
                cluster_id=str(cluster.get("mistake_id") or cluster.get("id") or ""),
                cluster_label=str(cluster.get("label") or "").strip(),
                repair_strategy=str(cluster.get("repair_strategy") or "").strip(),
                explicit_template_id=(
                    str(cluster.get("repair_card_template_id") or "").strip()
                    or str(cluster.get("template_id") or "").strip()
                    or None
                ),
            )
            related_labels = tuple(
                str((pack_nodes_by_id.get(node_id) or {}).get("label") or node_id)
                for node_id in related_nodes
            )
            template = get_task_template(pack, template_id) if get_task_template else None
            if template is not None:
                template_id = str(template.get("template_id") or template_id)

            best_score = score
            best_match = MistakeClusterMatch(
                cluster_id=str(cluster.get("mistake_id") or cluster.get("id") or "").strip(),
                cluster_label=str(cluster.get("label") or "专项错因").strip(),
                related_nodes=related_nodes,
                related_node_labels=related_labels,
                source="sprint_pack",
                repair_strategy=str(cluster.get("repair_strategy") or "").strip(),
                task_template_id=template_id,
                pack_id=str(pack.get("id") or "").strip() or None,
                streak_count=0,
                matched_keywords=keyword_hits,
                matched_node_names=tuple(str(name) for name in feature_bundle["node_names"]),
                db_node_ids=tuple(str(node_id) for node_id in feature_bundle["db_node_ids"]),
            )

        return best_match

    def _match_generic_cluster(
        self,
        error: ErrorRecord,
        node_name_map: dict[str, str],
        *,
        fallback_node_ids: list[UUID],
    ) -> MistakeClusterMatch | None:
        feature_bundle = self._extract_error_feature_bundle(error, node_name_map)
        feature_text = str(feature_bundle["raw_text"])
        normalized_text = str(feature_bundle["normalized_text"])
        best_rule: dict[str, Any] | None = None
        best_hits: tuple[str, ...] = ()

        for rule in self.GENERIC_MISTAKE_FALLBACKS:
            hits = tuple(
                keyword
                for keyword in rule.get("keywords", ())
                if self._normalize_text(keyword) and self._normalize_text(keyword) in normalized_text
            )
            if len(hits) <= len(best_hits):
                continue
            best_rule = rule
            best_hits = hits

        if best_rule is None or not best_hits:
            return None

        related_node_labels = tuple(str(name) for name in feature_bundle["node_names"]) or tuple(
            str(node_id) for node_id in fallback_node_ids
        )
        related_nodes = tuple(str(node_id) for node_id in fallback_node_ids) or related_node_labels
        return MistakeClusterMatch(
            cluster_id=str(best_rule["cluster_id"]),
            cluster_label=str(best_rule["label"]),
            related_nodes=related_nodes,
            related_node_labels=related_node_labels,
            source="generic_keyword",
            repair_strategy=str(best_rule["repair_strategy"]),
            task_template_id=str(best_rule["task_template_id"]),
            pack_id=None,
            streak_count=0,
            matched_keywords=best_hits,
            matched_node_names=tuple(str(name) for name in feature_bundle["node_names"]),
            db_node_ids=tuple(str(node_id) for node_id in feature_bundle["db_node_ids"]),
        )

    def _extract_error_feature_bundle(
        self,
        error: ErrorRecord,
        node_name_map: dict[str, str],
    ) -> dict[str, object]:
        analysis = error.latest_analysis if isinstance(error.latest_analysis, dict) else {}
        db_node_ids = tuple(
            str(node_id)
            for node_id in (
                self._coerce_uuid(value)
                for value in (error.linked_knowledge_node_ids or [])
            )
            if node_id is not None
        )
        node_names = tuple(
            node_name_map.get(str(node_id), "")
            for node_id in db_node_ids
            if node_name_map.get(str(node_id), "")
        )
        raw_text = " ".join(
            filter(
                None,
                (
                    str(error.subject_code or "").strip(),
                    str(error.chapter or "").strip(),
                    str(error.question_text or "").strip(),
                    str(error.user_answer or "").strip(),
                    str(error.correct_answer or "").strip(),
                    str(error.ai_analysis_summary or "").strip(),
                    " ".join(node_names),
                    " ".join(str(item or "").strip() for item in (error.suggested_concepts or [])),
                    " ".join(
                        str(analysis.get(key) or "").strip()
                        for key in (
                            "knowledge_node_name",
                            "knowledge_node",
                            "error_concept",
                            "concept_name",
                            "concept",
                            "weak_concept",
                            "root_cause",
                            "study_suggestions",
                            "ocr_text",
                        )
                    ),
                ),
            )
        )
        return {
            "raw_text": raw_text,
            "normalized_text": self._normalize_text(raw_text),
            "node_names": node_names,
            "db_node_ids": db_node_ids,
        }

    def _looks_like_network_pack_candidate(self, text: str) -> bool:
        lowered = str(text or "").strip().lower()
        return any(token in lowered for token in self.NETWORK_PACK_SIGNAL_TOKENS)

    def _match_pack_nodes(self, pack: dict[str, Any], feature_bundle: dict[str, object]) -> set[str]:
        matched: set[str] = set()
        feature_text = str(feature_bundle["raw_text"])
        normalized_text = str(feature_bundle["normalized_text"])

        for node in pack.get("knowledge_nodes", []):
            node_id = str(node.get("node_id") or "").strip()
            if not node_id:
                continue
            label = str(node.get("label") or node.get("name") or "").strip()
            normalized_label = self._normalize_text(label)
            if normalized_label and normalized_label in normalized_text:
                matched.add(node_id)
                continue

            hints = tuple(self.PACK_NODE_HINTS.get(node_id, ()))
            if any(self._normalize_text(hint) in normalized_text for hint in hints if self._normalize_text(hint)):
                matched.add(node_id)
                continue

            recommended_action = str(node.get("recommended_action") or "").strip()
            if recommended_action and self._normalize_text(recommended_action) in normalized_text:
                matched.add(node_id)

        return matched

    async def _select_primary_plan_id(self, *, user_id: UUID, plan_ids: set[UUID]) -> UUID | None:
        if not plan_ids:
            return None

        result = await self.db.execute(
            select(Plan.id)
            .where(
                Plan.user_id == user_id,
                Plan.id.in_(plan_ids),
            )
            .order_by(
                Plan.is_primary.desc(),
                Plan.target_date.asc(),
                Plan.created_at.desc(),
            )
        )
        return result.scalars().first()

    async def _create_specialized_repair_intervention(
        self,
        *,
        user_id: UUID,
        error_type: str,
        recent_error_count: int,
        plan_id: UUID | None,
        match: MistakeClusterMatch,
        cohort_profile: dict[str, str] | None,
    ) -> tuple[str | None, str | None]:
        from app.schemas.notification import NotificationCreate
        from app.services.notification_service import NotificationService

        task_payload = self._build_specialized_repair_task_payload(match)
        diagnosis_payload = {
            "node_ids": list(match.db_node_ids),
            "node_name": match.cluster_label,
            "recent_error_count": recent_error_count,
            "same_cluster_streak": match.streak_count,
            "plan_ids": [str(plan_id)] if plan_id else [],
            "target_plan_id": str(plan_id) if plan_id else None,
            "error_type": error_type,
            "cohort_profile": cohort_profile or {},
            "trigger": "error_replan_bridge",
            "specialized_repair": True,
            "cluster_id": match.cluster_id,
            "cluster_label": match.cluster_label,
            "cluster_source": match.source,
            "pack_id": match.pack_id,
            "related_nodes": list(match.related_nodes),
            "related_node_labels": list(match.related_node_labels),
            "matched_keywords": list(match.matched_keywords),
            "matched_node_names": list(match.matched_node_names),
            "weak_concept": match.cluster_label,
            "solution_text": match.repair_strategy,
            "estimated_minutes": task_payload["estimated_minutes"],
            "repair_task": task_payload,
            "suggested_schedule_options": list(self.SPECIALIZED_REPAIR_SCHEDULE_OPTIONS),
        }
        record = await InterventionRecordService(self.db).create_record(
            user_id=user_id,
            trigger_type=InterventionTriggerType.CONCEPT_GAP,
            delivery_strategy=DeliveryStrategy.SUPPORTIVE,
            delivery_channel=DeliveryChannel.IN_APP,
            trigger_source_ref="error_replan_bridge",
            diagnosis_payload=diagnosis_payload,
            outcome_window_days=14,
        )

        title = "专项修复已准备"
        description = (
            f"我注意到你连续 {match.streak_count} 次在「{match.cluster_label}」上出错了。"
            f"先暂停推进新内容，我准备了一个 {task_payload['estimated_minutes']} 分钟的专项修复任务，"
            "你可以选择插到今天或明天。"
        )
        notification = await NotificationService.create(
            self.db,
            user_id,
            NotificationCreate(
                title=title,
                content=description,
                type="intervention",
                data={
                    "record_id": str(record.id),
                    "intervention_id": str(record.id),
                    "trigger": "error_replan_bridge.specialized_repair",
                    "plan_id": str(plan_id) if plan_id else None,
                    "repair_cluster_id": match.cluster_id,
                    "repair_cluster_label": match.cluster_label,
                    "same_cluster_streak": match.streak_count,
                    "schedule_options": [
                        {"label": "插到今天", "action": "accepted", "action_payload": {"schedule": "today"}},
                        {"label": "插到明天", "action": "accepted", "action_payload": {"schedule": "tomorrow"}},
                        {"label": "先不了", "action": "dismissed", "action_payload": {"reason": "user_declined"}},
                    ],
                    "repair_task_preview": task_payload,
                },
            ),
            push_via_websocket=True,
        )
        await InterventionRecordService(self.db).mark_delivered(record.id)
        await self.db.commit()
        return str(record.id), str(notification.id)

    def _build_specialized_repair_task_payload(self, match: MistakeClusterMatch) -> dict[str, Any]:
        template = self._load_repair_template(match)
        template_steps = [
            str(step).strip()
            for step in (template.get("steps") or [])
            if str(step).strip()
        ]
        step_instructions = [
            f"先回看最近 {match.streak_count} 次错误，只写出这类题反复卡住的同一个触发点。",
            *template_steps[:3],
            "最后做 1 道同型检查题，只验证这一个错因簇有没有补到位。",
        ]
        deduped_steps: list[str] = []
        for step in step_instructions:
            if step and step not in deduped_steps:
                deduped_steps.append(step)

        structured_steps = [
            {"index": index, "instruction": step}
            for index, step in enumerate(deduped_steps, start=1)
        ]
        output_action = self._output_action_for_template(match.task_template_id, match.cluster_label)
        success_criteria = str(template.get("done_criteria") or "").strip() or (
            f"能说清「{match.cluster_label}」的判断依据，并完成 1 道同型检查题。"
        )
        objective = f"只攻克「{match.cluster_label}」这一个点，不推进新内容。"

        return {
            "title": f"[专项修复] {match.cluster_label}",
            "objective": objective,
            "steps": structured_steps,
            "method_steps": deduped_steps,
            "time_estimate_minutes": self.SPECIALIZED_REPAIR_DURATION_MINUTES,
            "estimated_minutes": self.SPECIALIZED_REPAIR_DURATION_MINUTES,
            "output_action": output_action,
            "success_criteria": success_criteria,
            "micro_contract": "先暂停推进新内容，只修这一个错因簇；没修清前，不切去第二个主题。",
            "fail_safe_rule": "这张卡只允许处理当前错因簇，不外扩到整章重学。",
            "repair_strategy": match.repair_strategy,
            "repair_cluster_id": match.cluster_id,
            "repair_cluster_label": match.cluster_label,
            "repair_cluster_source": match.source,
            "pack_id": match.pack_id,
            "related_nodes": list(match.related_nodes),
            "related_node_labels": list(match.related_node_labels),
            "matched_keywords": list(match.matched_keywords),
            "matched_node_names": list(match.matched_node_names),
            "sprint_fail_safe": True,
            "specialized_repair": True,
            "schedule_options": list(self.SPECIALIZED_REPAIR_SCHEDULE_OPTIONS),
        }

    def _load_repair_template(self, match: MistakeClusterMatch) -> dict[str, Any]:
        if match.pack_id is None:
            return {}

        try:
            from app.sprint_packs.sprint_pack_loader import get_task_template, load_pack

            pack = load_pack(self.NETWORK_PACK_SUBJECT)
            if not pack:
                return {}
            template = get_task_template(pack, match.task_template_id)
            return dict(template or {})
        except Exception:
            return {}

    def _template_id_for_cluster(
        self,
        *,
        cluster_id: str,
        cluster_label: str,
        repair_strategy: str,
        explicit_template_id: str | None = None,
    ) -> str:
        explicit = str(explicit_template_id or "").strip()
        if explicit:
            return explicit

        haystack = f"{cluster_id} {cluster_label} {repair_strategy}".lower()
        if any(token in haystack for token in ("状态", "握手", "挥手", "流程", "transition", "syn", "fin")):
            return "process_trace_card"
        if any(token in haystack for token in ("ack", "窗口", "window", "计算", "公式", "单位", "seq")):
            return "calculation_drill_card"
        if any(token in haystack for token in ("对比", "混淆", "mapping", "区别")):
            return "comparison_table_card"
        return "concept_recall_card"

    def _output_action_for_template(self, template_id: str, cluster_label: str) -> str:
        normalized = str(template_id or "").strip().lower()
        if normalized == "process_trace_card":
            return f"重画一版「{cluster_label}」的状态/时序图，并完成 1 道同型检查题。"
        if normalized == "calculation_drill_card":
            return f"完成 2 道只验证「{cluster_label}」的同型题，并写出每一步依据。"
        if normalized == "comparison_table_card":
            return f"做 1 张「{cluster_label}」对比表，并用自己的话解释核心区别。"
        return f"闭卷复述「{cluster_label}」的关键判断点，并完成 1 个最小检查。"

    async def materialize_specialized_repair_task_from_record(
        self,
        *,
        user_id: UUID,
        record: InterventionRecord,
        action_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        diagnosis = dict(record.diagnosis_payload or {})
        if not diagnosis.get("specialized_repair"):
            return {}

        existing_payload = dict(record.action_payload or {})
        if existing_payload.get("repair_task_id"):
            return {
                "repair_task_id": existing_payload.get("repair_task_id"),
                "repair_task_created": False,
                "repair_task_due_date": existing_payload.get("repair_task_due_date"),
            }

        task_payload = dict(diagnosis.get("repair_task") or {})
        if not task_payload:
            return {}

        raw_plan_id = diagnosis.get("target_plan_id") or next(iter(diagnosis.get("plan_ids") or []), None)
        plan_id = self._coerce_uuid(raw_plan_id)
        if not isinstance(plan_id, UUID):
            return {}

        due_date = self._repair_due_date_from_action_payload(action_payload)
        anchor_task = await self._find_anchor_task_for_plan(user_id=user_id, plan_id=plan_id)
        cluster_label = str(diagnosis.get("cluster_label") or task_payload.get("repair_cluster_label") or "专项修复").strip()
        priority_boost = await self._next_repair_priority(user_id=user_id, plan_id=plan_id)

        from app.schemas.task import TaskCreate
        from app.services.task_service import TaskService

        db_node_ids = [
            self._coerce_uuid(value)
            for value in (diagnosis.get("node_ids") or [])
        ]
        materialized = await TaskService.create(
            self.db,
            TaskCreate(
                title=str(task_payload.get("title") or f"[专项修复] {cluster_label}"),
                type=TaskType.ERROR_FIX,
                plan_id=plan_id,
                tags=[
                    "specialized_repair",
                    "mistake_cluster",
                    f"cluster:{diagnosis.get('cluster_id')}",
                    f"repair_source:{diagnosis.get('cluster_source')}",
                ],
                estimated_minutes=int(task_payload.get("estimated_minutes") or self.SPECIALIZED_REPAIR_DURATION_MINUTES),
                difficulty=1,
                energy_cost=1,
                guide_content=str(task_payload.get("objective") or f"专项修复：{cluster_label}"),
                priority=priority_boost,
                due_date=due_date,
                knowledge_node_id=next(
                    (node_id for node_id in db_node_ids if isinstance(node_id, UUID)),
                    getattr(anchor_task, "knowledge_node_id", None),
                ),
                guide_json=task_payload,
                ai_prompt=self._build_specialized_repair_ai_prompt(
                    cluster_label=cluster_label,
                    task_payload=task_payload,
                ),
                source_planning_session_id=getattr(anchor_task, "source_planning_session_id", None),
                phase_index=getattr(anchor_task, "phase_index", None),
                success_criteria=str(task_payload.get("success_criteria") or "").strip() or None,
            ),
            user_id=user_id,
        )
        await self._attach_specialized_repair_links(
            task=materialized,
            db_node_ids=[node_id for node_id in db_node_ids if isinstance(node_id, UUID)],
        )

        record.action_payload = {
            **existing_payload,
            "repair_task_id": str(materialized.id),
            "repair_task_due_date": due_date.isoformat(),
            "repair_task_created_at": _utcnow().isoformat(),
            "repair_schedule": self._repair_schedule_label(action_payload),
        }
        await self.db.flush()
        return {
            "repair_task_id": str(materialized.id),
            "repair_task_created": True,
            "repair_task_due_date": due_date.isoformat(),
        }

    async def _find_anchor_task_for_plan(self, *, user_id: UUID, plan_id: UUID) -> Task | None:
        result = await self.db.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.plan_id == plan_id,
            )
            .order_by(
                Task.due_date.asc(),
                Task.order_index.asc(),
                Task.created_at.asc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _attach_specialized_repair_links(self, *, task: Task, db_node_ids: list[UUID]) -> None:
        if not db_node_ids:
            return

        existing_result = await self.db.execute(
            select(TaskKnowledgeLink.knowledge_node_id).where(TaskKnowledgeLink.task_id == task.id)
        )
        existing = set(existing_result.scalars().all())
        for index, node_id in enumerate(db_node_ids):
            if node_id in existing:
                continue
            self.db.add(
                TaskKnowledgeLink(
                    task_id=task.id,
                    knowledge_node_id=node_id,
                    relation_type="repair_focus",
                    is_primary=index == 0,
                )
            )
        await self.db.flush()

    async def _next_repair_priority(self, *, user_id: UUID, plan_id: UUID) -> int:
        result = await self.db.execute(
            select(func.max(Task.priority)).where(
                Task.user_id == user_id,
                Task.plan_id == plan_id,
                Task.status.in_((TaskStatus.PENDING, TaskStatus.IN_PROGRESS)),
            )
        )
        current_max = result.scalar_one_or_none()
        return int(current_max or 0) + 1

    def _repair_due_date_from_action_payload(self, action_payload: dict[str, Any] | None) -> date:
        payload = dict(action_payload or {})
        explicit_due_date = str(payload.get("due_date") or payload.get("target_date") or "").strip()
        if explicit_due_date:
            try:
                return date.fromisoformat(explicit_due_date)
            except ValueError:
                pass

        schedule = self._repair_schedule_label(payload)
        base_date = _utcnow().date()
        if schedule == "tomorrow":
            return base_date + timedelta(days=1)
        return base_date

    def _repair_schedule_label(self, action_payload: dict[str, Any] | None) -> str:
        payload = dict(action_payload or {})
        for key in ("schedule", "schedule_slot", "target_day"):
            value = str(payload.get(key) or "").strip().lower()
            if value in self.SPECIALIZED_REPAIR_SCHEDULE_OPTIONS:
                return value
        return "today"

    def _build_specialized_repair_ai_prompt(self, *, cluster_label: str, task_payload: dict[str, Any]) -> str:
        step_lines = "\n".join(
            f"{index}. {step}"
            for index, step in enumerate(task_payload.get("method_steps") or [], start=1)
        )
        return (
            f"【专项修复主题】{cluster_label}\n"
            f"【任务目标】{task_payload.get('objective')}\n"
            f"【输出动作】{task_payload.get('output_action')}\n"
            f"【完成标准】{task_payload.get('success_criteria')}\n"
            f"【建议步骤】\n{step_lines}\n\n"
            "【请帮我】\n"
            "1. 只围绕这个错因簇做讲解，不扩到整章。\n"
            "2. 先给最短纠偏路径，再给 1 道同型检查题。\n"
            "3. 如果我答错，继续只修这个点，不换题型。"
        )

    @staticmethod
    def _coerce_uuid(value: object) -> UUID | None:
        if isinstance(value, UUID):
            return value
        if value is None:
            return None
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_text(value: object) -> str:
        return re.sub(r"[\s_\-，。；：、,.!?:（）()/\\]+", "", str(value or "").strip().lower())

    def _keywords_from_free_text(self, value: str) -> tuple[str, ...]:
        candidates = (
            "三次握手",
            "四次挥手",
            "状态",
            "状态转换",
            "拥塞控制",
            "流量控制",
            "确认号",
            "ack",
            "窗口",
            "cwnd",
            "rwnd",
            "单位换算",
            "公式",
        )
        normalized_text = self._normalize_text(value)
        return tuple(keyword for keyword in candidates if self._normalize_text(keyword) in normalized_text)

    def _keyword_hits(self, feature_text: str, keywords: Any) -> list[str]:
        normalized_text = self._normalize_text(feature_text)
        if isinstance(keywords, str):
            keyword_pool = [item for item in re.split(r"[|,/，、\s]+", keywords) if item]
        else:
            keyword_pool = [str(item) for item in list(keywords or []) if str(item).strip()]
        return [
            keyword
            for keyword in keyword_pool
            if self._normalize_text(keyword) and self._normalize_text(keyword) in normalized_text
        ]

    async def _create_error_intervention_record(
        self,
        *,
        user_id: UUID,
        low_mastery_nodes: list[UUID],
        recent_error_count: int,
        plan_ids: list[str],
        error_type: str,
    ) -> str | None:
        try:
            node_name = await self._resolve_node_name(low_mastery_nodes)
            cohort_profile = await self._get_cohort_profile(user_id)
            record = await InterventionRecordService(self.db).create_record(
                user_id=user_id,
                trigger_type=InterventionTriggerType.CONCEPT_GAP,
                delivery_strategy=DeliveryStrategy.SUPPORTIVE,
                delivery_channel=DeliveryChannel.CHAT,
                trigger_source_ref="error_replan_bridge",
                diagnosis_payload={
                    "node_ids": [str(node_id) for node_id in low_mastery_nodes],
                    "node_name": node_name,
                    "recent_error_count": recent_error_count,
                    "plan_ids": plan_ids,
                    "error_type": error_type,
                    "cohort_profile": cohort_profile or {},
                    "trigger": "error_replan_bridge",
                },
                outcome_window_days=14,
            )
            await self.db.flush()
            return str(record.id)
        except Exception as exc:
            logger.warning("ErrorReplanBridge: failed to create intervention record: {}", exc)
            return None

    async def _record_error_mastery_echo(
        self,
        *,
        error: ErrorRecord,
        mastery_update: dict | None,
        fallback_node_id: UUID,
    ) -> None:
        """Persist the user-facing link between an error and its primary galaxy node."""
        node_id = fallback_node_id
        if mastery_update and mastery_update.get("node_id"):
            try:
                node_id = UUID(str(mastery_update["node_id"]))
            except (TypeError, ValueError):
                node_id = fallback_node_id

        error.affected_node_id = node_id
        if mastery_update and mastery_update.get("delta") is not None:
            error.mastery_delta = float(mastery_update["delta"])

        await self.db.flush()

    async def _notify_plan_adjusted(
        self,
        *,
        user_id: UUID,
        low_mastery_nodes: list[UUID],
        recent_error_count: int,
        intervention_id: str | None = None,
    ) -> None:
        """Emit a system update so the user sees the plan was adjusted due to errors."""
        try:
            from app.services.system_update_service import SystemUpdateService, build_system_update

            node_name = await self._resolve_node_name(low_mastery_nodes)

            description = (
                f"我注意到你在「{node_name}」上遇到了{recent_error_count}次相似的问题，"
                "已经调整了本周计划，把相关任务移到了更早的时间段。"
                if node_name
                else f"你最近在同一知识点上遇到了{recent_error_count}次问题，我已经微调了本周计划。"
            )

            await SystemUpdateService(self.redis).enqueue(
                user_id,
                build_system_update(
                    update_type="plan_adjusted_from_error",
                    category="evolution",
                    title="计划已根据你的错题调整",
                    description=description,
                    priority="normal",
                    metadata={
                        "evolution_kind": "adjustment",
                        "node_name": node_name,
                        "error_count": recent_error_count,
                        "trigger": "error_replan_bridge",
                        "intervention_id": intervention_id,
                    },
                ),
            )
        except Exception as exc:
            logger.warning("ErrorReplanBridge: failed to enqueue plan_adjusted system update: {}", exc)

    async def _notify_bridge_failure(
        self,
        *,
        user_id: UUID,
        category: str,
        error: str,
    ) -> None:
        try:
            from app.services.system_update_service import SystemUpdateService, build_system_update

            await SystemUpdateService(self.redis).enqueue(
                user_id,
                build_system_update(
                    update_type="error_bridge_failure",
                    category="system",
                    title="计划校准暂时未完成",
                    description="系统识别到了新的错题压力信号，但这次自动校准没有完整执行，稍后会继续重试。",
                    priority="medium",
                    metadata={
                        "trigger": "error_replan_bridge",
                        "error_category": category,
                        "error": error,
                    },
                ),
            )
        except Exception as exc:
            logger.warning("ErrorReplanBridge: failed to enqueue failure update: {}", exc)

    async def _record_shadow_decision(
        self,
        *,
        user_id: UUID,
        error_id: UUID,
        error_type: str,
        plan_ids: set[UUID],
        is_new_user: bool,
        legacy_decision: ErrorPressureDecision,
        stage34_decision: ErrorPressureDecision,
    ) -> None:
        await RouteHistoryService(self.db).record_decision(
            user_id=user_id,
            input_aggregator_snapshot_id="stage38:error_replan_bridge",
            decision_type="stage38_error_replan_bridge_shadow",
            decision_payload={
                "trigger": "error_created_bridge",
                "error_id": str(error_id),
                "error_type": error_type,
                "is_new_user": is_new_user,
                "legacy_threshold": legacy_decision.threshold,
                "legacy_triggered": legacy_decision.triggered,
                "stage34_threshold": stage34_decision.threshold,
                "stage34_triggered": stage34_decision.triggered,
                "recent_error_count": stage34_decision.recent_error_count,
                "plan_ids": [str(plan_id) for plan_id in sorted(plan_ids, key=str)],
            },
            source_state_v2={
                "stage": "38",
                "feature": "error_bridge_shadow",
                "mode": "shadow",
            },
        )

    @staticmethod
    def _blocked(
        *,
        mode: str,
        gate: str,
        reason: str | None = None,
        plan_ids: list[str] | None = None,
        **extra: object,
    ) -> dict[str, object]:
        ERROR_REPLAN_BRIDGE_BLOCKED_BY_GATE_TOTAL.labels(gate=gate, mode=mode).inc()
        payload: dict[str, object] = {
            "triggered": False,
            "reason": reason or gate,
            "plan_ids": list(plan_ids or []),
            "mode": mode,
        }
        payload.update(extra)
        return payload

    async def _is_new_user(self, user_id: UUID) -> bool:
        user = await self.db.get(User, user_id)
        if user is None or getattr(user, "created_at", None) is None:
            return False
        created_at = user.created_at
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        return (_utcnow() - created_at) < timedelta(days=7)

    async def _resolve_node_name(self, node_ids: list[UUID]) -> str:
        if not node_ids:
            return ""

        from app.models.galaxy import KnowledgeNode

        node_result = await self.db.execute(select(KnowledgeNode).where(KnowledgeNode.id == node_ids[0]))
        node = node_result.scalar_one_or_none()
        if node is None:
            return ""
        return str(node.name or "").strip()

    async def _resolve_error_concept(self, error: ErrorRecord, node_ids: list[UUID]) -> str:
        analysis = error.latest_analysis if isinstance(error.latest_analysis, dict) else {}
        for key in (
            "knowledge_node_name",
            "knowledge_node",
            "error_concept",
            "concept_name",
            "concept",
            "weak_concept",
        ):
            value = str(analysis.get(key) or "").strip()
            if value:
                return value

        suggested_concepts = list(error.suggested_concepts or [])
        for concept in suggested_concepts:
            value = str(concept or "").strip()
            if value:
                return value

        return await self._resolve_node_name(node_ids)

    async def _update_mastery_from_error(
        self,
        *,
        user_id: UUID,
        knowledge_node_id: UUID | None,
        knowledge_node_name: str | None,
        error_type: str,
        error_count: int,
    ) -> dict | None:
        from app.services.galaxy_service import GalaxyService

        return await GalaxyService(self.db).update_mastery_from_error(
            self.db,
            user_id=str(user_id),
            knowledge_node_id=str(knowledge_node_id) if knowledge_node_id else None,
            knowledge_node_name=knowledge_node_name,
            error_type=error_type,
            error_count=error_count,
        )

    async def _get_node_mastery_scores(self, *, user_id: UUID, node_ids: list[UUID]) -> dict[UUID, float]:
        if not node_ids:
            return {}

        result = await self.db.execute(
            select(UserNodeStatus.node_id, UserNodeStatus.mastery_score)
            .where(UserNodeStatus.user_id == user_id)
            .where(UserNodeStatus.node_id.in_(node_ids))
        )
        return {node_id: float(mastery_score or 0.0) for node_id, mastery_score in result.all()}

    @staticmethod
    def _extract_error_type(error: ErrorRecord) -> str:
        analysis = error.latest_analysis if isinstance(error.latest_analysis, dict) else {}
        return str(analysis.get("error_type") or "other").strip().lower()

    def _classify_trigger_type(self, error: ErrorRecord) -> str | None:
        analysis = error.latest_analysis if isinstance(error.latest_analysis, dict) else {}
        return self._classify_trigger_type_from_analysis(analysis)

    def _classify_trigger_type_from_analysis(self, analysis: dict[str, object]) -> str | None:
        raw_error_type = str(analysis.get("error_type") or "other").strip().lower()
        if raw_error_type in self.TRIGGERING_ERROR_TYPES:
            return raw_error_type
        if raw_error_type in {"knowledge_gap", "foundation_gap", "basic_gap"}:
            return "baseline_gap"
        if raw_error_type in {"procedural_error", "method_wrong", "understanding_gap"}:
            return "comprehension_failure"
        if raw_error_type in {"careless_mistake", "reading_careless", "calculation_error"}:
            return "careless_error"
        if raw_error_type in {"time_management", "time_pressure", "rushed_miss", "skipped_due_time"}:
            return "time_pressure_miss"
        if raw_error_type in {"strategy_mismatch", "logic_error", "transfer_error"}:
            return "knowledge_transfer_fail"
        if raw_error_type in {"missing_prerequisite", "prereq_missing"}:
            return "prerequisite_missing"

        root_cause = str(analysis.get("root_cause") or "").strip().lower()
        study_suggestions = str(analysis.get("study_suggestions") or "").strip().lower()
        signal_text = f"{root_cause} {study_suggestions}"
        if any(token in signal_text for token in ("time", "rush", "pace", "deadline")):
            return "time_pressure_miss"
        if any(
            token in signal_text
            for token in ("prerequisite", "prereq", "前置", "foundation", "basic knowledge", "基础")
        ):
            return "prerequisite_missing"
        if any(token in signal_text for token in ("strategy", "approach", "method selection", "transfer", "迁移")):
            return "knowledge_transfer_fail"
        return None

    def _is_high_severity(self, error: ErrorRecord) -> bool:
        analysis = error.latest_analysis if isinstance(error.latest_analysis, dict) else {}
        raw_severity = analysis.get("severity")
        if raw_severity is None:
            raw_severity = analysis.get("severity_level")
        if raw_severity is None:
            raw_severity = analysis.get("risk_level")
        return str(raw_severity or "").strip().lower() in self.HIGH_SEVERITY_VALUES

    async def _find_low_mastery_nodes(self, *, user_id: UUID, node_ids: list[UUID]) -> list[UUID]:
        result = await self.db.execute(
            select(UserNodeStatus.node_id)
            .where(UserNodeStatus.user_id == user_id)
            .where(UserNodeStatus.node_id.in_(node_ids))
            .where(UserNodeStatus.mastery_score < self.LOW_MASTERY_THRESHOLD)
        )
        return list(result.scalars().all())

    async def _find_relevant_active_plan_ids(self, *, user_id: UUID, node_ids: list[UUID]) -> set[UUID]:
        today = _utcnow().date()
        result = await self.db.execute(
            select(Task.plan_id)
            .join(Plan, Plan.id == Task.plan_id)
            .join(TaskKnowledgeLink, TaskKnowledgeLink.task_id == Task.id)
            .where(
                Task.user_id == user_id,
                Task.plan_id.is_not(None),
                Task.status.in_((TaskStatus.PENDING, TaskStatus.IN_PROGRESS)),
                Plan.user_id == user_id,
                Plan.is_active.is_(True),
                TaskKnowledgeLink.knowledge_node_id.in_(node_ids),
            )
            .where((Task.due_date.is_(None)) | (Task.due_date >= today))
        )
        return {plan_id for plan_id in result.scalars().all() if plan_id is not None}

    async def _count_recent_triggering_errors(
        self,
        *,
        user_id: UUID,
        node_ids: list[UUID],
        days: int,
    ) -> int:
        cutoff = _utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(
                ErrorRecord.id,
                ErrorRecord.created_at,
                ErrorRecord.latest_analysis,
                ErrorRecord.linked_knowledge_node_ids,
            )
            .where(ErrorRecord.user_id == user_id)
            .where(ErrorRecord.is_deleted.is_(False))
            .order_by(desc(ErrorRecord.created_at))
        )

        seen_error_ids: set[UUID] = set()
        for error_id, created_at, latest_analysis, linked_ids in result.all():
            normalized_created_at = created_at
            if normalized_created_at and normalized_created_at.tzinfo is not None:
                normalized_created_at = normalized_created_at.replace(tzinfo=None)
            if normalized_created_at and normalized_created_at < cutoff:
                continue

            analysis = latest_analysis if isinstance(latest_analysis, dict) else {}
            error_type = self._classify_trigger_type_from_analysis(analysis)
            if error_type not in self.REPLAN_ELIGIBLE_ERROR_TYPES:
                continue

            linked = {str(value) for value in (linked_ids or []) if value is not None}
            if not linked.intersection({str(node_id) for node_id in node_ids}):
                continue
            seen_error_ids.add(error_id)
        return len(seen_error_ids)

    async def _filter_plan_ids_by_cooldown(
        self,
        *,
        user_id: UUID,
        plan_ids: set[UUID],
        error_type: str,
    ) -> set[UUID]:
        if not plan_ids:
            return set()
        cutoff = _utcnow() - timedelta(hours=self.COOLDOWN_HOURS)
        records = list(
            (
                await self.db.execute(
                    select(InterventionRecord).where(
                        InterventionRecord.user_id == user_id,
                        InterventionRecord.trigger_source_ref == "error_replan_bridge",
                        InterventionRecord.created_at >= cutoff,
                    )
                )
            )
            .scalars()
            .all()
        )
        cooled_plan_ids = set(plan_ids)
        for record in records:
            diagnosis = dict(record.diagnosis_payload or {})
            if str(diagnosis.get("error_type") or "").strip().lower() != error_type:
                continue
            recent_plan_ids = {
                UUID(plan_id) for plan_id in (diagnosis.get("plan_ids") or []) if isinstance(plan_id, str)
            }
            cooled_plan_ids -= recent_plan_ids
        return cooled_plan_ids

    async def _get_cohort_profile(self, user_id: UUID) -> dict[str, str] | None:
        try:
            from app.models.user_preferences import UserPreferencesCenter

            result = await self.db.execute(
                select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id)
            )
            prefs = result.scalar_one_or_none()
            if prefs is None:
                return None
            explicit = dict(getattr(prefs, "explicit", None) or getattr(prefs, "explicit_preferences", None) or {})
            goal_mem = dict(prefs.goal_memory or {}) if hasattr(prefs, "goal_memory") else {}
            return {
                "goal_type": str(
                    goal_mem.get("learning_goal_type") or explicit.get("learning_goal_type") or ""
                ).strip(),
                "knowledge_level": str(explicit.get("knowledge_level") or "").strip(),
                "learning_style": str(explicit.get("learning_style") or "").strip(),
            }
        except Exception:
            return None
