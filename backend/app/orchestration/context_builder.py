"""Context-building mixin for ChatOrchestrator.

Extracts all ``_build_*_context``, ``_merge_*``, ``_get_*`` helpers that
assemble the rich user / conversation / plan context dict consumed by the
prompt builder and LLM calls.

This is a *mixin* -- it relies on attributes that live on the concrete
``ChatOrchestrator`` instance (``self.redis``, ``self.context_pruner``,
``self.state_manager``, etc.).
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

from google.protobuf.json_format import MessageToDict
from loguru import logger
from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.experience_memory import ExperienceContextQuery
from app.core.i18n import I18n
from app.core.metrics import (
    AURORA_PROFILE_INTEGRATION_FAILURE_TOTAL,
    AURORA_RETURNING_CONTEXT_TIER_TOTAL,
    CONTEXT_CACHE_VERSION_DECISIONS,
)
from app.core.time_utils import utcnow
from app.gen.agent.v1 import agent_service_pb2
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.cognitive import CognitiveFragment
from app.models.plan import Plan
from app.models.task import Task
from app.models.task import TaskStatus as ModelTaskStatus
from app.models.task_feedback import TaskFeedback
from app.orchestration.capability_lane import MEMORY_CLASS_INSTRUCTION, classify_memory_class_message
from app.routing.tool_preference_router import ToolPreferenceRouter
from app.scaffolding.scaffolding_fsm import ScaffoldingFSM
from app.services.aurora_stage34_kill_switch_service import AuroraStage34KillSwitchService
from app.services.aurora_stage39_kill_switch_service import AuroraStage39KillSwitchService
from app.services.context_cache_key import ContextCacheVersionError, resolve_context_cache_versions
from app.services.experience_memory_projector import ExperienceMemoryProjector
from app.services.focus_service import focus_service
from app.services.galaxy_service import GalaxyService
from app.services.insight_copy import canonical_pattern_key, present_pattern_description, present_pattern_name
from app.services.memory_retrieval_prefilter import PURPOSE_LLM_CONTEXT, build_retrieval_context, prefilter_candidates
from app.services.memory_service import MemoryService
from app.services.memory_use_selfcheck import (
    MemoryUseCandidate,
    SelfCheckContext,
    evaluate_memory_use_gate,
)
from app.services.plan_service import PlanService
from app.services.self_evolution_service import UnderstandingDepthService
from app.services.simulation.seed_extractor import SeedExtractor
from app.services.tool_history_service import ToolHistoryService
from app.services.user_service import UserService
from app.state_aggregator.service import StateAggregatorService

# ---------------------------------------------------------------------------
# Helpers (duplicated from orchestrator to avoid circular imports)
# ---------------------------------------------------------------------------


def _collect_aurora_relationship_profile_data(user_id: str, ledger: Any | None = None) -> dict[str, Any]:
    """Derive the Aurora relationship-profile keys for the LLM profile bundle.

    Extracted from ``_build_llm_profile_bundle`` so the attribute contract with
    ``SparkleRelationshipState`` is unit-testable (PROD-LOG2 ②-6: the ghost
    ``rel_state.label`` reference blew up here on every call and the surrounding
    catch reduced the whole integration to one warning line).

    All labels come from the aurora domain's own public derivation
    (``SparkleRelationshipStateManager.derive_view`` → ``maturity_label``:
    exploring/forming/stable/trusted) — never from ad-hoc field guesses on the
    schema.
    """
    from app.aurora.ledger import AppendOnlyLedgerStore
    from app.aurora.profile_translator import ProfileTranslator
    from app.aurora.relationship_state import SparkleRelationshipStateManager
    from app.aurora.schemas.primitives import IdentityEvidence, InsightClaim

    # Instantiate ledger (defaults to memory-based if no storage path is mapped)
    if ledger is None:
        ledger = AppendOnlyLedgerStore(storage_path=settings.AURORA_LEDGER_PATH)
    raw_records = ledger.list_records(user_id=user_id, record_types={"insight_claim", "identity_evidence"})

    claims = []
    for r in raw_records:
        if r["record_type"] == "insight_claim":
            try:
                claims.append(InsightClaim.model_validate(r["payload"]))
            except Exception:
                continue

    evidence = []
    for r in raw_records:
        if r["record_type"] == "identity_evidence":
            try:
                evidence.append(IdentityEvidence.model_validate(r["payload"]))
            except Exception:
                continue

    rel_manager = SparkleRelationshipStateManager()
    # Derive maturity from interaction history count + claims
    interaction_metadata = {"interaction_count": len(raw_records)}
    rel_view = rel_manager.derive_view(
        user_id=uuid.UUID(user_id),
        claims=claims,
        identity_evidence=evidence,
        interaction_metadata=interaction_metadata,
    )
    rel_state = rel_view.state

    translator = ProfileTranslator()
    translation = translator.translate(claims=claims, evidence=evidence, relationship_state=rel_state)

    # Inject into profile context for prompt building. PROD-LOG2 ②-6:
    # ``SparkleRelationshipState`` has no ``label`` field — the collaborator
    # label is the domain-derived maturity label, consumed by
    # prompts._format_aurora_profile_section.
    return {
        "aurora_profile_summary": translation.summary,
        "relationship_maturity": rel_state.relationship_maturity,
        "relationship_label": rel_view.maturity_label,
    }


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------


class ContextBuilderMixin:
    """Mixin providing context building methods for ChatOrchestrator."""

    # FT-LAT-3: per-user short-TTL cache for the expensive user-context payload.
    # The full rebuild costs 1-2s warm (and used to spike 10-30s cold); within a
    # session the payload barely changes between consecutive turns, so later
    # messages reuse it instead of re-paying the whole serial chain.
    #
    # C-07（CONTEXT_COMPILER_V3 §7）：键从裸 ``user_id`` 升级为
    # ``user_id|schema|mepoch|pv|pol|know`` 版本化组合键
    # （``context_cache_key``，单一权威 ``services/context_cache_key.py``）。
    # 删除/纠正/权限收紧 → memory_epoch bump（M-07 管线）→ 键变 → 旧条目
    # 孤儿化，0 stale reuse；跨 user 由键首段 user_id 结构性隔离。
    # 写入/纠偏指令轮（memory_instruction）整轮绕过缓存——旧文本 cache 不得
    # 冒充新推理；版本解析失败 fail-closed 重建（M-07 epoch 读侧门同款）。
    _USER_CONTEXT_CACHE_TTL_SECONDS = 120.0
    _USER_CONTEXT_CACHE_MAX_ENTRIES = 128
    _user_context_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    async def _context_cache_resolve_key(
        self,
        user_id: str,
        active_db: AsyncSession | None,
        user_message: str,
    ) -> tuple[str | None, str]:
        """解析本轮 context cache 键；返回 ``(key, outcome)``。

        - ``("…key…", "ok")``：正常版本键；
        - ``(None, "write_intent_bypass")``：写入/纠偏指令轮，禁用旧文本缓存；
        - ``(None, "version_error_bypass")``：版本解析失败，fail-closed 重建。
        """
        # CONTEXT_COMPILER_V3 §7：写操作与纠偏请求不得用旧文本 cache 冒充新
        # 推理。记忆指令轮（记住/别忘/记下…，capability_lane 零 LLM 判定）
        # 重建后照常写缓存——本轮若真落写，M-07 epoch bump 会让该键孤儿化；
        # 未落写则 TTL 有界。
        if classify_memory_class_message(user_message) == MEMORY_CLASS_INSTRUCTION:
            CONTEXT_CACHE_VERSION_DECISIONS.labels(outcome="write_intent_bypass").inc()
            return None, "write_intent_bypass"

        if active_db is None:
            return None, "version_error_bypass"

        try:
            versions = await resolve_context_cache_versions(active_db, user_id, redis_client=self.redis)
        except ContextCacheVersionError as exc:
            logger.warning(
                "context cache version resolve failed, fail-closed rebuild user_id={} error={}",
                user_id,
                exc,
            )
            CONTEXT_CACHE_VERSION_DECISIONS.labels(outcome="version_error_bypass").inc()
            return None, "version_error_bypass"
        return versions.cache_key(), "ok"

    def _context_cache_lookup(self, cache_key: str) -> dict[str, Any] | None:
        """TTL 内命中返回深拷贝载荷；否则 None（含过期条目惰性清理）。"""
        entry = self._user_context_cache.get(cache_key)
        if entry is None:
            CONTEXT_CACHE_VERSION_DECISIONS.labels(outcome="miss").inc()
            return None
        if (time.monotonic() - entry[0]) > self._USER_CONTEXT_CACHE_TTL_SECONDS:
            self._user_context_cache.pop(cache_key, None)
            CONTEXT_CACHE_VERSION_DECISIONS.labels(outcome="miss").inc()
            return None
        CONTEXT_CACHE_VERSION_DECISIONS.labels(outcome="hit").inc()
        return copy.deepcopy(entry[1])

    def _context_cache_store(self, cache_key: str, payload: dict[str, Any]) -> None:
        """写入版本化条目并做 LRU 容量收敛（键含版本，容量按条目数封顶）。"""
        self._user_context_cache[cache_key] = (time.monotonic(), copy.deepcopy(payload))
        if len(self._user_context_cache) > self._USER_CONTEXT_CACHE_MAX_ENTRIES:
            _oldest_key = min(self._user_context_cache, key=lambda k: self._user_context_cache[k][0])
            self._user_context_cache.pop(_oldest_key, None)

    @staticmethod
    def _extract_seed_library_nodes(examples: list[dict[str, Any]]) -> list[str]:
        seen: set[str] = set()
        node_ids: list[str] = []
        for example in examples:
            for raw in list(example.get("seed_library_nodes") or []):
                node_id = str(raw or "").strip()
                if not node_id or node_id in seen:
                    continue
                seen.add(node_id)
                node_ids.append(node_id)
        return node_ids

    @staticmethod
    def _serialize_stage34_active_goal(plan: Plan) -> dict[str, Any]:
        return {
            "id": str(plan.id),
            "title": str(plan.name or "").strip(),
            "status": "active" if bool(plan.is_active) else "inactive",
            "type": getattr(plan.type, "value", plan.type),
            "plan_stage": getattr(plan.plan_stage, "value", plan.plan_stage),
            "subject": plan.subject,
            "target_date": plan.target_date.isoformat() if plan.target_date else None,
            "progress": float(plan.progress or 0.0),
        }

    @staticmethod
    def _serialize_stage34_episodic_memory(memory: Any) -> dict[str, Any]:
        return {
            "id": str(memory.id),
            "summary": str(memory.summary or "").strip(),
            "subject_type": str(memory.subject_type or "").strip(),
            "source_type": str(memory.source_type or "").strip(),
            "source_lane": str(getattr(memory, "source_lane", "") or "").strip(),
            "occurred_at": memory.occurred_at.isoformat() if memory.occurred_at else None,
            "importance_score": (
                float(memory.importance_score) if getattr(memory, "importance_score", None) is not None else None
            ),
            "confidence": (float(memory.confidence) if getattr(memory, "confidence", None) is not None else None),
            "evidence_score": (
                float(memory.evidence_score) if getattr(memory, "evidence_score", None) is not None else None
            ),
            "correction_count": int(getattr(memory, "correction_count", 0) or 0),
            "user_confirmed": str(getattr(memory, "source_lane", "") or "").strip() != "inferred_extraction",
            "tags": list(memory.tags or []),
        }

    async def _stage34_modes_payload(self) -> dict[str, str]:
        try:
            return await AuroraStage34KillSwitchService().summary()
        except Exception as exc:
            logger.warning(f"Failed to load Stage34 modes, falling back to settings: {exc}")
            return {
                "mode": str(getattr(settings, "AURORA_STAGE34_MODE", "shadow") or "shadow"),
                "error_bridge_mode": str(getattr(settings, "AURORA_STAGE34_ERROR_BRIDGE_MODE", "shadow") or "shadow"),
                "capsule_mode": str(getattr(settings, "AURORA_STAGE34_CAPSULE_MODE", "shadow") or "shadow"),
                "journey_subscribers_enabled": str(
                    getattr(settings, "AURORA_STAGE34_JOURNEY_SUBSCRIBERS_MODE", "live") or "live"
                ),
            }

    async def _stage39_modes_payload(self) -> dict[str, str]:
        try:
            return await AuroraStage39KillSwitchService().summary()
        except Exception as exc:
            logger.warning(f"Failed to load Stage39 modes, falling back to settings: {exc}")
            return {
                "mode": str(getattr(settings, "AURORA_STAGE39_MODE", "live") or "live"),
                "scaffolding_prompt_mode": str(
                    getattr(settings, "AURORA_STAGE39_SCAFFOLDING_PROMPT_MODE", "live") or "live"
                ),
                "cogload_route_mode": str(getattr(settings, "AURORA_STAGE39_COGLOAD_ROUTE_MODE", "shadow") or "shadow"),
                "galaxy_inject_mode": str(getattr(settings, "AURORA_STAGE39_GALAXY_INJECT_MODE", "shadow") or "shadow"),
            }

    @staticmethod
    def _stage39_intervention_intensity(template_support_level: int | float | None) -> str:
        if template_support_level is None:
            return "medium"
        level = float(template_support_level)
        if level >= 3.5:
            return "high"
        if level >= 2.5:
            return "medium"
        return "low"

    async def _build_stage39_scaffolding_snapshot(
        self,
        *,
        user_id: str,
        db_session: AsyncSession,
        mode: str,
    ) -> dict[str, Any] | None:
        try:
            fsm = ScaffoldingFSM(db_session)
            state = await fsm.get_state(uuid.UUID(user_id))
            trait_guidance = await fsm.get_trait_scaffolding_preferences(uuid.UUID(user_id))
            snapshot = fsm.snapshot(
                state,
                consume_mode="off",
                reflection_prompt_style=str(trait_guidance.get("reflection_prompt_style") or "default"),
            )
        except Exception as exc:
            logger.warning(f"Failed to build Stage39 scaffolding snapshot for {user_id}: {exc}")
            return None

        return {
            "mode": mode,
            "current_scaffolding_stage": str(snapshot.get("current_zone") or "flow"),
            "intervention_intensity": self._stage39_intervention_intensity(snapshot.get("template_support_level")),
            "template_support_level": int(snapshot.get("template_support_level") or 0),
            "support_level": round(float(snapshot.get("support_level") or 0.0), 2),
            "capability_level": round(float(snapshot.get("capability_level") or 0.0), 2),
            "reflection_prompt_style": str(snapshot.get("reflection_prompt_style") or "default"),
            "consecutive_successes": int(snapshot.get("consecutive_successes") or 0),
            "consecutive_failures": int(snapshot.get("consecutive_failures") or 0),
            "combine_state": str(snapshot.get("combine_state") or "neutral"),
            "last_intervention_timestamp": snapshot.get("last_intervention_timestamp"),
        }

    async def _attach_stage39_context(
        self,
        payload: dict[str, Any],
        *,
        user_id: str,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        stage39_modes = await self._stage39_modes_payload()
        payload["aurora_stage39_modes"] = dict(stage39_modes)

        scaffolding_snapshot = await self._build_stage39_scaffolding_snapshot(
            user_id=user_id,
            db_session=db_session,
            mode=str(stage39_modes.get("scaffolding_prompt_mode") or "live"),
        )
        if scaffolding_snapshot is not None:
            payload["scaffolding_fsm_snapshot"] = scaffolding_snapshot

        galaxy_snapshot = {
            "mode": str(stage39_modes.get("galaxy_inject_mode") or "shadow"),
            "goal_ids": [],
            "nodes": [],
        }
        raw_active_goals = payload.get("active_goals") or []
        active_goal_ids: list[uuid.UUID] = []
        for item in raw_active_goals:
            if not isinstance(item, dict):
                continue
            try:
                active_goal_ids.append(uuid.UUID(str(item.get("id"))))
            except Exception:
                continue
        galaxy_snapshot["goal_ids"] = [str(item) for item in active_goal_ids]
        if active_goal_ids:
            with contextlib.suppress(Exception):
                galaxy_snapshot["nodes"] = await GalaxyService(db_session).get_goal_context_nodes(
                    user_id=uuid.UUID(user_id),
                    plan_ids=active_goal_ids,
                    limit=5,
                )
        payload["galaxy_snapshot"] = galaxy_snapshot

        cognitive_context = payload.get("cognitive_context")
        if isinstance(cognitive_context, dict):
            cognitive_context["aurora_stage39_modes"] = dict(stage39_modes)
            if scaffolding_snapshot is not None:
                cognitive_context["scaffolding_fsm_snapshot"] = dict(scaffolding_snapshot)
            cognitive_context["galaxy_snapshot"] = dict(galaxy_snapshot)
        return payload

    async def _get_recent_tool_usage_context(
        self,
        *,
        user_id: str,
        db_session: AsyncSession,
    ) -> list[dict[str, Any]]:
        try:
            return await ToolHistoryService(db_session).get_recent_context_effects(
                uuid.UUID(user_id),
                limit=4,
                hours=24,
            )
        except Exception as exc:
            logger.warning(f"Failed to build recent tool usage context for {user_id}: {exc}")
            return []

    # ------------------------------------------------------------------
    # _build_profile_payload
    # ------------------------------------------------------------------

    def _build_profile_payload(
        self,
        user_context_data: dict[str, Any] | None,
        preferences: dict[str, Any] | None,
        llm_profile_data: dict[str, Any] | None,
        preference_version: int,
        experiment_cohort: str | None,
    ) -> dict[str, Any]:
        identity: dict[str, Any] = {}
        if isinstance(user_context_data, dict):
            flame_level = None
            prefs = user_context_data.get("preferences")
            if isinstance(prefs, dict):
                flame_level = prefs.get("flame_level")

            locale = user_context_data.get("language", "zh-CN")
            unknown_text = I18n.t("common.unknown", locale=locale)

            identity = {
                "nickname": user_context_data.get("nickname", unknown_text),
                "timezone": user_context_data.get("timezone", "Asia/Shanghai"),
                "language": locale,
                "is_pro": user_context_data.get("is_pro", False),
                "persona_type": user_context_data.get("persona_type"),
                "flame_level": flame_level,
            }

        prefs = preferences
        if not isinstance(prefs, dict) and isinstance(user_context_data, dict):
            prefs = user_context_data.get("preferences")
        if not isinstance(prefs, dict):
            prefs = {}

        llm_profile = llm_profile_data if isinstance(llm_profile_data, dict) else {}

        return {
            "identity": identity,
            "preferences": prefs,
            "llm_profile": llm_profile,
            "preference_version": preference_version,
            "experiment_cohort": experiment_cohort,
        }

    # ------------------------------------------------------------------
    # _merge_user_contexts
    # ------------------------------------------------------------------

    def _merge_user_contexts(self, local_context: dict[str, Any], grpc_context: dict[str, Any]) -> dict[str, Any]:
        """
        P0: Merge user context from Go Gateway (gRPC) with local context (Python).
        Prioritizes gRPC context as it's more recent (fetched at request time).

        Returns:
            Merged context dict with both sources
        """
        if not grpc_context:
            return local_context

        merged = {}

        # Start with local context as base
        merged.update(local_context)

        # Override with gRPC context (prioritized as more recent)
        if "pending_tasks" in grpc_context:
            merged["next_actions"] = grpc_context["pending_tasks"]  # Normalize field name
        if "active_plans" in grpc_context:
            merged["active_plans"] = grpc_context["active_plans"]
        if "focus_stats" in grpc_context:
            merged["focus_stats"] = grpc_context["focus_stats"]
        if "recent_progress" in grpc_context:
            merged["recent_progress"] = grpc_context["recent_progress"]
        if "seed_library_enabled" in grpc_context:
            merged["seed_library_enabled"] = bool(grpc_context["seed_library_enabled"])

        logger.debug(f"Merged context keys: {list(merged.keys())}")
        return merged

    # ------------------------------------------------------------------
    # _get_task_status_summary
    # ------------------------------------------------------------------

    async def _get_task_status_summary(self, user_id: str, db_session: AsyncSession) -> dict[str, Any]:
        """Get summary of all tasks for user across all plans."""
        try:
            # Pending count
            result = await db_session.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == uuid.UUID(user_id), Task.status == ModelTaskStatus.PENDING
                )
            )
            pending = result.scalar() or 0

            # In progress count
            result = await db_session.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == uuid.UUID(user_id), Task.status == ModelTaskStatus.IN_PROGRESS
                )
            )
            in_progress = result.scalar() or 0

            # Overdue count (pending/in_progress and due_date < now)
            result = await db_session.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == uuid.UUID(user_id),
                    Task.status.in_([ModelTaskStatus.PENDING, ModelTaskStatus.IN_PROGRESS]),
                    Task.due_date < utcnow(),
                )
            )
            overdue = result.scalar() or 0

            return {"pending": pending, "in_progress": in_progress, "overdue": overdue}
        except Exception as e:
            logger.warning(f"Failed to get task status summary: {e}")
            return {"pending": 0, "in_progress": 0, "overdue": 0}

    # ------------------------------------------------------------------
    # _get_cognitive_insights
    # ------------------------------------------------------------------

    async def _get_cognitive_insights(
        self, user_id: str, db_session: AsyncSession, locale: str = "en"
    ) -> dict[str, Any]:
        """获取认知模式摘要，注入 LLM 上下文

        当用户有已识别的行为模式时，LLM 可以在合适时机主动展示认知棱镜。
        """
        try:
            from uuid import UUID

            from app.services.cognitive_service import CognitiveService

            cognitive = CognitiveService(db_session)
            patterns = await cognitive.get_user_patterns(UUID(user_id), min_confidence=0.6)

            if patterns:
                # 按类型分组
                by_type = {"cognitive": [], "emotional": [], "execution": []}
                for p in patterns:
                    by_type.setdefault(p.pattern_type, []).append(p.pattern_name)

                # Map ORM BehaviorPattern → policy_signals via the canonical map
                from app.services.profile_context_service import ProfileContextService

                policy_map = ProfileContextService.PATTERN_POLICY_MAP
                policy_signals = []
                for p in patterns:
                    normalized = str(p.pattern_name or "").strip().lower()
                    policy_signals.extend(policy_map.get(normalized, []))

                top_patterns: list[dict[str, Any]] = []
                for pattern in patterns[:2]:
                    top_patterns.append(
                        {
                            "pattern_name": present_pattern_name(pattern.pattern_name),
                            "raw_pattern_name": str(pattern.pattern_name or "").strip(),
                            "canonical_key": canonical_pattern_key(pattern.pattern_name),
                            "pattern_type": str(pattern.pattern_type or "").strip().lower(),
                            "confidence": round(float(pattern.confidence_score or 0.0), 2),
                            "description": present_pattern_description(pattern.pattern_name, pattern.description),
                            "last_observed_at": (
                                pattern.last_observed_at.isoformat() if pattern.last_observed_at else None
                            ),
                        }
                    )

                recent_observation = None
                most_recent = max(
                    patterns,
                    key=lambda item: item.last_observed_at or item.created_at or datetime.min,
                )
                observed_at = most_recent.last_observed_at or most_recent.created_at
                if observed_at and observed_at >= utcnow() - timedelta(days=7):
                    recent_observation = {
                        "pattern_name": present_pattern_name(most_recent.pattern_name),
                        "observed_at": observed_at.isoformat(),
                        "description": present_pattern_description(
                            most_recent.pattern_name,
                            most_recent.description,
                        ),
                    }

                return {
                    "has_cognitive_patterns": True,
                    "pattern_count": len(patterns),
                    "recent_patterns": [present_pattern_name(p.pattern_name) for p in patterns[:3]],
                    "patterns_by_type": {k: len(v) for k, v in by_type.items()},
                    "policy_signals": list(set(policy_signals)),
                    "top_patterns": top_patterns,
                    "recent_observation": recent_observation,
                    "current_guidance": self._build_cognitive_prompt_guidance(top_patterns, locale=locale),
                }
        except Exception as e:
            logger.warning(f"Failed to get cognitive insights for {user_id}: {e}")

        return {"has_cognitive_patterns": False}

    # ------------------------------------------------------------------
    # _get_seed_library_context
    # ------------------------------------------------------------------

    async def _get_seed_library_context(
        self, user_id: str, db_session: AsyncSession, subject: str | None = None
    ) -> dict[str, Any]:
        """获取用户已订阅种子库的 few-shot 示例，注入 LLM 上下文。"""
        try:
            from app.services.seed_library_service import SeedLibraryService

            service = SeedLibraryService()
            examples = await service.get_few_shot_examples(
                db=db_session,
                user_id=uuid.UUID(user_id),
                subject=subject,
                count=3,
                include_metadata=True,
            )
            if examples:
                seed_library_nodes = self._extract_seed_library_nodes(examples)
                return {
                    "has_seed_library": True,
                    "few_shot_examples": examples,
                    "example_count": len(examples),
                    "seed_library_nodes": seed_library_nodes,
                }
        except Exception as e:
            logger.warning(f"Failed to get seed library context for {user_id}: {e}")

        return {"has_seed_library": False}

    async def _build_learning_gaps_summary(self, user_id: str, db_session: AsyncSession) -> str | None:
        # FT-LAT-1: This hop used to sit directly on the first-token critical path:
        # on seed-cache miss the SeedExtractor runs six serial source queries plus a
        # hidden LLM refine (glm batch, 10-30s observed) just to pick 3 seeds for a
        # <=300 char summary. The heuristic rank order is deterministic, so the LLM
        # refine is skipped here (seed content itself is unchanged), and the final
        # summary is cached per user so only one turn per TTL window pays the DB cost.
        from app.core.cache import cache_service

        _gaps_cache_key = f"sparkle:ctx:learning_gaps_summary:{user_id}"
        try:
            cached_summary = await cache_service.get(_gaps_cache_key)
        except Exception:
            cached_summary = None
        if isinstance(cached_summary, str):
            return cached_summary or None
        try:
            seeds = await SeedExtractor(db_session).get_cached_or_generate(
                uuid.UUID(user_id),
                scenario_key="chat_context",
                limit=3,
                allow_llm_refine=False,
            )
        except Exception as exc:
            logger.warning(f"Failed to build learning gaps summary for {user_id}: {exc}")
            return None

        items: list[str] = []
        for seed in seeds:
            topic = str(seed.topic or "").strip()
            tension = str(seed.tension_point or "").strip()
            if not topic:
                continue
            item = f"{topic}: {tension}" if tension else topic
            items.append(item[:96])
        summary = "；".join(items).strip()
        summary = summary[:300] or ""
        try:
            await cache_service.set(_gaps_cache_key, summary, ttl=300)
        except Exception:
            pass
        return summary or None

    async def _build_stage33_working_memory_snapshot(
        self,
        user_id: str,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        try:
            state = await StateAggregatorService(db_session).get_user_state(
                uuid.UUID(user_id),
                required_fields=("working_memory_snapshot",),
                now=utcnow(),
            )
        except Exception as exc:
            logger.warning(f"Failed to build stage33 working memory snapshot for {user_id}: {exc}")
            return {}

        envelope = getattr(state, "working_memory_snapshot", None)
        if envelope is None or getattr(envelope, "value", None) is None:
            return {}

        items = []
        for item in envelope.value.items:
            summary = str(item.summary or "").strip()
            if not summary:
                continue
            items.append(
                {
                    "summary": summary,
                    "subject_type": item.subject_type,
                    "mention_count": item.mention_count,
                    "consolidated": item.consolidated,
                    "last_seen_at": item.last_seen_at.isoformat() if item.last_seen_at else None,
                }
            )

        return {
            "active_session_id": envelope.value.active_session_id,
            "items": items,
            "freshness_seconds": envelope.freshness_seconds,
        }

    async def _attach_stage34_memory_context(
        self,
        payload: dict[str, Any],
        *,
        user_id: str,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        user_uuid = uuid.UUID(user_id)
        memory_service = MemoryService(db_session, self.redis)

        active_goal_rows = await PlanService.list_active(db_session, user_uuid, limit=3)
        active_goals = [
            self._serialize_stage34_active_goal(plan) for plan in active_goal_rows if str(plan.name or "").strip()
        ]

        episodic_rows = await memory_service.list_recent_episodic(user_uuid, limit=12)
        # M-03 deterministic L0 prefilter (R1-F2): stage34 feeds the main chat
        # payload's episodic_memories, which prompts render into the system
        # prompt — superseded / expired / permission-blocked rows are cut here,
        # before the correction/importance ranking (same law as context_manager
        # and context_pack pull paths; MEMORY_V3 §3 steps 1-5 before semantics).
        retrieval_ctx = await build_retrieval_context(
            db_session,
            user_id=user_uuid,
            purpose=PURPOSE_LLM_CONTEXT,
        )
        # C-08（context-eval）：预筛结果整段捕获（此前 apply_memory_prefilter
        # 只留 allowed、reasons 丢弃）——漏斗 candidates→filtered 段的决策
        # reasons 从这里来。metadata-only（id/reason/计数，无正文）。
        episodic_prefilter = prefilter_candidates(episodic_rows, retrieval_ctx)
        episodic_prefilter_input = list(episodic_rows)
        episodic_rows = episodic_prefilter.allowed
        ranked_episodic_rows = sorted(
            episodic_rows,
            key=lambda memory: (
                int(getattr(memory, "correction_count", 0) or 0),
                float(getattr(memory, "importance_score", 0.0) or 0.0),
                float(getattr(memory, "confidence", 0.0) or 0.0),
            ),
            reverse=True,
        )
        episodic_memories = [
            self._serialize_stage34_episodic_memory(memory)
            for memory in ranked_episodic_rows[:5]
            if str(getattr(memory, "summary", "") or "").strip()
        ]

        # M-05 over-personalization Self-ReCheck —— stage34 输出装配面 final-gate
        # （M-03 R1-F2 同位）：包内近重复 episodic 在 payload["episodic_memories"]
        # （prompts.format_user_context 渲染进系统 prompt 的 section）降档为
        # 内部档。该装配点无本轮 user/assistant 信号 → relevance 与跨轮
        # repetition 休眠（unconstrained 保守放行，M-03 同法），仅 dedup 生效；
        # 话题面的权威 relevance gate 在 context_pack.build（有 query_text）。
        if settings.ENABLE_MEMORY_USE_SELFCHECK and episodic_memories:
            selfcheck = evaluate_memory_use_gate(
                episodic=[
                    MemoryUseCandidate(
                        item_id=str(memory.get("id")),
                        section="episodic",
                        content=str(memory.get("summary") or ""),
                    )
                    for memory in episodic_memories
                ],
                ctx=SelfCheckContext(),
            )
            if selfcheck.internal_only_count:
                surfaced_ids = selfcheck.surfaced_ids("episodic")
                episodic_memories = [memory for memory in episodic_memories if str(memory.get("id")) in surfaced_ids]
                payload["memory_selfcheck"] = {
                    **selfcheck.to_metric_payload(),
                    "internal_only": selfcheck.internal_only_entries(),
                }

        payload["active_goals"] = active_goals
        payload["episodic_memories"] = episodic_memories
        payload.setdefault("aurora_stage34_modes", await self._stage34_modes_payload())

        # C-08（context-eval）：episodic 记忆漏斗——candidates→filtered（M-03
        # 预筛 reasons）→ranked→injected（rank 截断 + M-05 selfcheck 降档）
        # 四段计数 + token + 决策 reasons。metadata-only（id/reason/计数/token，
        # 零正文），供 generation_node 的统一 context funnel 记录消费。
        try:
            from app.orchestration.context_funnel import (
                build_episodic_funnel,
                episodic_ref,
                make_source_ref,
            )

            _selected_ids = {str(memory.get("id")) for memory in episodic_memories}
            _selfcheck_dropped: list[tuple[str, str]] = []
            if isinstance(payload.get("memory_selfcheck"), dict):
                for entry in payload["memory_selfcheck"].get("internal_only") or []:
                    _entry_id = str(entry.get("item_id") or "") if isinstance(entry, dict) else ""
                    if _entry_id and _entry_id not in _selected_ids:
                        _selfcheck_dropped.append((_entry_id, "selfcheck_internal"))
            _memory_funnel = build_episodic_funnel(
                candidate_rows=episodic_prefilter_input,
                prefilter_allowed_count=episodic_prefilter.allowed_count,
                prefilter_reasons=dict(episodic_prefilter.reason_counts),
                prefilter_dropped_refs=[
                    (episodic_ref(rejection.record_id), rejection.reason)
                    for rejection in episodic_prefilter.rejections
                ],
                ranked_rows=ranked_episodic_rows,
                injected_rows=episodic_memories,
                selfcheck_dropped_refs=_selfcheck_dropped,
            )
            payload["context_funnel_memory"] = {
                "surface": _memory_funnel.surface,
                "stages": _memory_funnel.to_payload()["stages"],
                "consistent": _memory_funnel.validate() == [],
                "source_refs": [
                    make_source_ref(
                        kind="episodic",
                        ref_id=episodic_ref(memory.get("id")),
                        content=str(memory.get("summary") or ""),
                        extra={
                            "claim_status": memory.get("claim_status"),
                            "source_lane": memory.get("source_lane"),
                        },
                    )
                    for memory in episodic_memories
                ],
            }
        except Exception as exc:
            logger.debug(f"C-08 memory funnel capture degraded: {exc}")

        # WIRING-1（FIX-33）：M-06 经验记忆检索接入 chat context 装配——
        # 「该用户相似 situation 下何曾与正/负结果共同出现」经真实 M-03 预筛 +
        # M-05 selfcheck 后注入 payload["experience_memories"]（降档面见
        # experience_memory_meta）。失败隔离：检索/门禁异常降级空集，不阻断装配。
        await self._attach_experience_memory_context(payload, user_id=user_id, db_session=db_session)

        last_mood = await memory_service.get_last_session_mood(user_uuid)
        if isinstance(last_mood, dict) and last_mood:
            payload["last_session_mood"] = last_mood

        recent_corrections = await memory_service.list_recent_calibration_receipts(user_uuid, limit=3)
        if recent_corrections:
            payload["recent_corrections"] = recent_corrections

        cognitive_context = payload.get("cognitive_context")
        if isinstance(cognitive_context, dict):
            cognitive_context["active_goals"] = active_goals
            cognitive_context["episodic_memories"] = episodic_memories
            if recent_corrections:
                cognitive_context["recent_corrections"] = recent_corrections
        return payload

    #: M-05 selfcheck 候选 section 标签（experience claims 与 episodic 分批过门，
    #: 独立去重域——batch 内 near-duplicate 归因仍成立）。
    _EXPERIENCE_MEMORY_SECTION = "experience"

    # rule-as: ignore experience_memories=memory 桶 manifest 登记面（context_sources.py USER_CONTEXT_FIELD_BUCKETS，WIRING-1/FIX-33），experience_memory_meta/selfcheck=M-05 观测面由 C-08 统一漏斗消费（agents/standard_workflow.py）——消费者均不在本守卫 routing_engine/prompts/context_builder 三文件渲染面内
    async def _attach_experience_memory_context(
        self,
        payload: dict[str, Any],
        *,
        user_id: str,
        db_session: AsyncSession,
    ) -> None:
        """WIRING-1（FIX-33）：M-06 ``retrieve_context`` 接入 chat context。

        - 检索：unconstrained 查询（情境轴全部放行——装配点尚无本轮诊断标签；
          friction 定向检索由 A-05 ``patched_decision_inputs`` 的证据面在决策
          时执行），双向召回 + 无证据桶，输出已过真实 M-03 预筛（projector
          出口边界执行）；
        - M-05 输出门：经验 claims 经真实 ``evaluate_memory_use_gate``
          （与 episodic_memories 同一 gate 实例语义；``ENABLE_MEMORY_USE_SELFCHECK``
          关闭时全量放行并在 meta 登记）；internal-only 降档不进 payload——
          降档率实测面 = ``experience_memory_meta.m05``（FIX-33 原文要求的
          「词法降档率对经验 claims 的影响」可观测面）；
        - 因果红线：claims 本身是 D-05 非因果关联文案（M-06 投影边界保证），
          本层零改写、零补充断言。
        """
        payload["experience_memories"] = []
        meta: dict[str, Any] = {
            "total_candidates": 0,
            "surfaced": 0,
            "internal_only": 0,
            "truncated_projection": False,
            "m05_downgrade_rate": 0.0,
        }
        payload["experience_memory_meta"] = meta
        try:
            result = await ExperienceMemoryProjector(db_session).retrieve_context(
                ExperienceContextQuery(
                    user_id=user_id,
                    purpose=PURPOSE_LLM_CONTEXT,
                    max_records_per_direction=3,
                )
            )
        except Exception as exc:
            logger.debug(f"M-06 experience context unavailable for chat assembly: {exc}")
            meta["unavailable"] = True
            return

        # 双向桶优先（正向→负向→无证据），同桶内保持 projector 排序（确定性）。
        records = (
            list(result.observed_with_positive) + list(result.observed_with_negative) + list(result.no_outcome_evidence)
        )
        meta["total_candidates"] = len(records)
        meta["truncated_projection"] = bool(result.truncated)
        if not records:
            return

        candidates = [
            MemoryUseCandidate(item_id=record.record_id, section=self._EXPERIENCE_MEMORY_SECTION, content=record.claim)
            for record in records
            if str(record.claim or "").strip()
        ]
        surfaced_ids: set[str] = {candidate.item_id for candidate in candidates}
        if settings.ENABLE_MEMORY_USE_SELFCHECK and candidates:
            selfcheck = evaluate_memory_use_gate(episodic=candidates, ctx=SelfCheckContext())
            surfaced_ids = set(selfcheck.surfaced_ids(self._EXPERIENCE_MEMORY_SECTION))
            meta["internal_only"] = len(candidates) - len(surfaced_ids)
            meta["m05_downgrade_rate"] = round(meta["internal_only"] / len(candidates), 6) if candidates else 0.0
            payload["experience_memory_selfcheck"] = selfcheck.to_metric_payload()

        experience_memories = [
            {
                "id": record.record_id,
                "claim": record.claim,
                "direction": (
                    "positive"
                    if record.has_positive_association_evidence
                    else ("negative" if record.has_negative_association_evidence else "no_outcome_evidence")
                ),
                "evidence_count": record.evidence_count,
                "evidence_strength": record.completeness_adjusted_strength,
                "signature": record.signature.as_dict(),
            }
            for record in records
            if record.record_id in surfaced_ids and str(record.claim or "").strip()
        ]
        payload["experience_memories"] = experience_memories
        meta["surfaced"] = len(experience_memories)
        # C-08（context-eval）：注入 claims 的 token 计量（experience 漏斗
        # injected 段；metadata-only）。
        meta["tokens"] = sum(len(str(entry.get("claim") or "")) // 4 for entry in experience_memories)

    async def _build_aurora_everyday_presence_context(
        self,
        *,
        user_id: str,
        db_session: AsyncSession,
        conversation_id: str | None,
        returning_context: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Summarize Aurora's current judgment for ordinary chat surfaces.

        This is a thin product-facing readout of the existing control surface,
        not a separate Aurora state model.
        """
        try:
            from app.services.aurora_control_surface_service import AuroraControlSurfaceService

            snapshot = await AuroraControlSurfaceService(db_session, self.redis).build_snapshot(
                user_id=uuid.UUID(user_id),
                conversation_id=conversation_id,
            )
        except Exception as exc:
            logger.debug(f"Aurora everyday presence context unavailable: {exc}")
            return None

        if not isinstance(snapshot, dict) or not snapshot:
            return None

        status = str(snapshot.get("overall_status") or "sensing").strip()
        summary = str(snapshot.get("summary") or "").strip()
        scene_alignment = str(snapshot.get("scene_alignment") or "matched").strip()
        evidence = [
            str(item).strip() for item in list(snapshot.get("status_evidence_chain") or [])[:3] if str(item).strip()
        ]
        memory_references = [
            str(item).strip() for item in list(snapshot.get("memory_references") or [])[:2] if str(item).strip()
        ]
        last_correction = (
            snapshot.get("last_correction_effect") if isinstance(snapshot.get("last_correction_effect"), dict) else {}
        )
        return_tier = str((returning_context or {}).get("resume_tier") or "").strip()

        uncertainty_level = "low"
        if status in {"risk_found", "needs_confirm"} or scene_alignment == "fallback":
            uncertainty_level = "high"
        elif status in {"sensing", "calibration_available"}:
            uncertainty_level = "medium"
        if bool(last_correction.get("visible")):
            uncertainty_level = "medium"

        if scene_alignment == "fallback":
            chat_hint = "我可能接的是最近一次上下文，而不是这一轮的完整状态；如果方向不对，你可以直接纠正我。"
        elif bool(last_correction.get("visible")):
            chat_hint = "我已经按你刚才的纠正调整判断；这轮会先保守确认，不直接把旧假设当事实。"
        elif return_tier in {"personalized_return", "checkpoint_debrief"}:
            chat_hint = "你离开了一段时间，我会先接住上次进度和当前未完成项；如果我读错重点，直接告诉我。"
        elif status in {"risk_found", "needs_confirm"}:
            chat_hint = f"我可能在误读当前状态：{summary or '这个判断还需要你确认'}"
        elif status == "calibrated":
            chat_hint = "我会按当前目标、情景和记忆继续帮你推进；重要判断仍然可以随时改。"
        else:
            chat_hint = "我还在轻量感知当前上下文，会先少下结论、多留纠正空间。"

        should_surface = bool(
            status in {"risk_found", "needs_confirm"}
            or scene_alignment == "fallback"
            or bool(last_correction.get("visible"))
            or return_tier in {"personalized_return", "checkpoint_debrief"}
        )

        return {
            "source": "aurora_control_surface",
            "overall_status": status,
            "energy_level": str(snapshot.get("energy_level") or "L0"),
            "summary": summary,
            "chat_hint": chat_hint,
            "uncertainty_level": uncertainty_level,
            "scene_alignment": scene_alignment,
            "evidence_chain": evidence,
            "memory_references": memory_references,
            "next_step_suggestion": str(snapshot.get("next_step_suggestion") or "").strip(),
            "last_correction_effect": last_correction,
            "return_tier": return_tier,
            "should_surface": should_surface,
        }

    # ------------------------------------------------------------------
    # _get_recent_sentiment_distribution
    # ------------------------------------------------------------------

    async def _get_recent_sentiment_distribution(
        self,
        user_id: str,
        db_session: AsyncSession | None,
        window: int = 8,
    ) -> dict[str, int]:
        if not db_session:
            return {}
        try:
            result = await db_session.execute(
                select(CognitiveFragment.sentiment)
                .where(CognitiveFragment.user_id == uuid.UUID(user_id))
                .where(CognitiveFragment.sentiment.isnot(None))
                .order_by(desc(CognitiveFragment.created_at))
                .limit(window)
            )
            rows = result.scalars().all()
            distribution: dict[str, int] = {}
            for raw in rows:
                sentiment = str(raw or "").strip().lower()
                if not sentiment:
                    continue
                distribution[sentiment] = distribution.get(sentiment, 0) + 1
            return distribution
        except Exception as e:
            logger.warning(f"Failed to load recent sentiment distribution: {e}")
            return {}

    # ------------------------------------------------------------------
    # _get_recent_task_feedback_distribution
    # ------------------------------------------------------------------

    async def _get_recent_task_feedback_distribution(
        self,
        user_id: str,
        db_session: AsyncSession | None,
        window: int = 8,
    ) -> dict[str, int]:
        if not db_session:
            return {}
        try:
            result = await db_session.execute(
                select(TaskFeedback.category)
                .where(TaskFeedback.user_id == uuid.UUID(user_id))
                .where(TaskFeedback.category.isnot(None))
                .order_by(desc(TaskFeedback.created_at))
                .limit(window)
            )
            rows = result.scalars().all()
            distribution: dict[str, int] = {}
            for raw in rows:
                category = str(raw or "").strip().lower()
                if not category:
                    continue
                distribution[category] = distribution.get(category, 0) + 1
            return distribution
        except Exception as e:
            logger.warning(f"Failed to load recent task feedback distribution: {e}")
            return {}

    # ------------------------------------------------------------------
    # _build_user_context
    # ------------------------------------------------------------------

    async def _build_user_context(
        self, user_id: str, db_session: AsyncSession, session_id: str | None = None
    ) -> dict[str, Any]:
        """
        Build comprehensive user context from UserService

        Returns:
            Dict containing user context and analytics
        """
        try:
            _uc_marks: list[tuple[str, float]] = []
            _uc_t = time.perf_counter()

            def _uc_mark(name: str) -> None:
                nonlocal _uc_t
                _now = time.perf_counter()
                _uc_marks.append((name, _now - _uc_t))
                _uc_t = _now

            # Pass redis_client to UserService for caching
            user_service = UserService(db_session, self.redis)
            base_user_context = await user_service.get_context(uuid.UUID(user_id))
            base_user_context_data = base_user_context.model_dump() if base_user_context else None
            _uc_mark("user_service.get_context")
            experiment_cohort = self._experiment_cohort_for_user(user_id)

            locale = "zh-CN"
            if base_user_context_data:
                locale = base_user_context_data.get("language", "zh-CN")

            returning_context = await self._build_returning_context(
                user_id=user_id,
                session_id=session_id,
                db_session=db_session,
                locale=locale,
            )
            _uc_mark("build_returning_context")
            understanding_depth = None
            if settings.ENABLE_PERCEPTIBLE_INTELLIGENCE:
                with contextlib.suppress(Exception):
                    depth_service = UnderstandingDepthService(db_session, self.redis)
                    understanding_depth = (await depth_service.evaluate(user_id=uuid.UUID(user_id))).__dict__
            _uc_mark("understanding_depth")

            # P1: Task Status Summary
            task_status_summary = await self._get_task_status_summary(user_id, db_session)
            _uc_mark("task_status_summary")

            # WT295: 显式类型注解——消除 mypy partial-type 内部崩溃（Unexpectedly
            # encountered partial type @ L1277 use-site，由 L1209 嵌套元组解包
            # 重定义触发）。该崩溃令 mypy 全量输出被随机截断（±400 条可见性翻转，
            # wt292 实锤回退），且崩溃时 context_builder 下游 ~500 条存量类型债
            # 被静默隐藏。局部注解为纯编译期元数据，运行时零行为变化。
            llm_profile_data: dict[str, Any] | None = None
            preference_version: int = 0

            async def _build_llm_profile_bundle(session: AsyncSession) -> tuple[dict[str, Any] | None, int]:
                bundle_profile_data = None
                bundle_version = 0
                try:
                    from app.services.personalization import get_personalization_engine

                    engine = get_personalization_engine(session, self.redis)
                    llm_profile = await engine.get_llm_profile(uuid.UUID(user_id))
                    prefs = await engine.pref_service.get_preferences(uuid.UUID(user_id))
                    bundle_version = prefs.version
                    bundle_profile_data = {
                        "system_prompt_additions": llm_profile.system_prompt_additions,
                        "verbosity_target": llm_profile.verbosity_target,
                        "temperature": llm_profile.temperature,
                        "should_ask_clarifying": llm_profile.should_ask_clarifying,
                        "should_provide_examples": llm_profile.should_provide_examples,
                        "exploration_level": llm_profile.exploration_level,
                        "tone": llm_profile.tone,
                    }

                    # --- Aurora Profile Integration ---
                    try:
                        bundle_profile_data.update(_collect_aurora_relationship_profile_data(user_id))
                    except Exception as aurora_err:
                        # PROD-LOG2 ②-6：属性漂移类失败曾只留一行 warning（无
                        # traceback、无计数），AI 静默丢失关系状态维度。失败
                        # 必须可观测：ERROR 级 + 异常栈 + 计数。
                        AURORA_PROFILE_INTEGRATION_FAILURE_TOTAL.inc()
                        logger.opt(exception=True).error(
                            "Failed to integrate Aurora profile context user_id={} error={}",
                            user_id,
                            aurora_err,
                        )
                except Exception as e:
                    logger.warning(f"Failed to build LLM profile: {e}")
                return bundle_profile_data, bundle_version

            # --- Use ContextOrchestrator (P4) ---
            from app.core.context_manager import ContextOrchestrator

            # FT-LAT-4: personalization (DB-backed) and the aggregated cognitive
            # context are independent read-only branches — run them concurrently
            # on separate sessions instead of serially on the shared session.
            from app.db.session import AsyncSessionLocal

            async with AsyncSessionLocal() as _parallel_session:
                cognitive_context, (llm_profile_data, preference_version) = await asyncio.gather(
                    ContextOrchestrator(db_session, self.redis).get_user_context(user_id),
                    _build_llm_profile_bundle(_parallel_session),
                )
            _uc_mark("user_context_parallel_branches")

            profile_context_payload = None

            # Map CognitiveContext to legacy dict format for backward compatibility
            # In future, we should use CognitiveContext object directly in prompt builder

            user_context_data = None
            if cognitive_context:
                # Use data from new orchestrator
                user_context_data = base_user_context_data or {
                    "user_id": user_id,
                    "nickname": I18n.t("common.unknown", locale=locale),
                }

                # Fetch active plans manually if not in cognitive context yet
                # Active plans (latest 3)
                plans_stmt = (
                    select(Plan)
                    .where(and_(Plan.user_id == uuid.UUID(user_id), Plan.is_active))
                    .order_by(desc(Plan.created_at))
                    .limit(3)
                )
                plans_result = await db_session.execute(plans_stmt)
                plans = plans_result.scalars().all()
                active_plans = [
                    {
                        "id": str(plan.id),
                        "title": plan.name,
                        "type": getattr(plan.type, "value", plan.type),
                        "target_date": plan.target_date.isoformat() if plan.target_date else None,
                        "progress": plan.progress or 0,
                    }
                    for plan in plans
                ]

                # P0: 认知棱镜上下文注入 — parallel queries
                async def _timed(name: str, coro):
                    _t = time.perf_counter()
                    try:
                        return await coro
                    finally:
                        logger.info("[LATENCY] prism_query {} took {:.0f}ms", name, (time.perf_counter() - _t) * 1000)

                (
                    cognitive_insights,
                    seed_library_context,
                    learning_gaps_summary,
                    working_memory_snapshot,
                    recent_tool_usage,
                ) = await asyncio.gather(
                    _timed("cognitive_insights", self._get_cognitive_insights(user_id, db_session, locale=locale)),
                    _timed("seed_library_context", self._get_seed_library_context(user_id, db_session)),
                    _timed("learning_gaps_summary", self._build_learning_gaps_summary(user_id, db_session)),
                    _timed("working_memory_snapshot", self._build_stage33_working_memory_snapshot(user_id, db_session)),
                    _timed(
                        "recent_tool_usage", self._get_recent_tool_usage_context(user_id=user_id, db_session=db_session)
                    ),
                )
                _uc_mark("prism_parallel_queries")

                profile_payload = self._build_profile_payload(
                    user_context_data=user_context_data,
                    preferences=cognitive_context.preferences,
                    llm_profile_data=llm_profile_data,
                    preference_version=preference_version,
                    experiment_cohort=experiment_cohort,
                )

                if getattr(cognitive_context, "profile_context", None):
                    profile_context_payload = cognitive_context.profile_context

                cognitive_context_payload = cognitive_context.model_dump(exclude={"user_id", "timestamp"})
                if working_memory_snapshot:
                    cognitive_context_payload["working_memory_snapshot"] = working_memory_snapshot

                payload = {
                    "user_context": user_context_data,  # Legacy field
                    "analytics_summary": cognitive_context.engagement_metrics or {},
                    "preferences": (
                        profile_context_payload.get("preferences")
                        if isinstance(profile_context_payload, dict)
                        else cognitive_context.preferences
                    ),
                    "next_actions": cognitive_context.active_tasks,
                    "active_plans": active_plans,
                    "focus_stats": cognitive_context.focus_stats,
                    "preference_version": preference_version,
                    "llm_profile": llm_profile_data,
                    "experiment_cohort": experiment_cohort,
                    "task_status_summary": task_status_summary,
                    "returning_context": returning_context,
                    "understanding_depth": understanding_depth,
                    "profile": profile_payload,
                    "profile_context": profile_context_payload,
                    "calendar_context": cognitive_context.calendar_context,
                    "working_memory_snapshot": working_memory_snapshot,
                    "recent_tool_usage": recent_tool_usage,
                    "past_session_memory": cognitive_context.past_session_memory,
                    # New field for full context injection
                    "cognitive_context": cognitive_context_payload,
                    # 认知棱镜数据
                    "cognitive_insights": cognitive_insights,
                    # 种子库 few-shot 示例
                    "seed_library": seed_library_context,
                    "learning_gaps_summary": learning_gaps_summary,
                }
                # Self-model: strategy confidence, failure streak, task completion rate
                with contextlib.suppress(Exception):
                    from app.aurora.runtime_v1.self_model import SparkleSelfModelService

                    self_model_summary = await SparkleSelfModelService.get_readout_summary(
                        user_id=user_id,
                        request_extra_context={},
                        user_context_payload=user_context_data or {},
                    )
                    if self_model_summary:
                        payload["self_model"] = self_model_summary
                aurora_presence = await self._build_aurora_everyday_presence_context(
                    user_id=user_id,
                    db_session=db_session,
                    conversation_id=session_id,
                    returning_context=returning_context,
                )
                if aurora_presence is not None:
                    payload["aurora_everyday_presence"] = aurora_presence
                    cognitive_context_payload["aurora_everyday_presence"] = aurora_presence
                payload = await self._attach_stage34_memory_context(
                    payload,
                    user_id=user_id,
                    db_session=db_session,
                )
                _uc_mark("stage34_memory_context")
                _final_payload = await self._attach_stage39_context(
                    payload,
                    user_id=user_id,
                    db_session=db_session,
                )
                _uc_mark("stage39_context")
                # C-02：四类来源标注（不改值，只加 manifest + trace 日志）。
                _final_payload = await self._attach_source_manifest(
                    _final_payload,
                    user_id=user_id,
                    db_session=db_session,
                )
                _uc_mark("source_manifest")
                if _uc_marks:
                    logger.info(
                        "[LATENCY] build_user_context session={} {}",
                        session_id,
                        " ".join(f"{name}={delta * 1000:.0f}ms" for name, delta in _uc_marks),
                    )
                return _final_payload

            # Fallback to legacy logic if new orchestrator returns None (shouldn't happen)
            logger.warning(f"ContextOrchestrator returned None for {user_id}, falling back to legacy")

            # ... Legacy Logic ...
            user_context = base_user_context
            analytics = await user_service.get_analytics_summary(uuid.UUID(user_id))

            if user_context:
                user_context_data = user_context.model_dump()

            # Next actions (top pending tasks)
            tasks_stmt = (
                select(Task)
                .where(and_(Task.user_id == uuid.UUID(user_id), Task.status == ModelTaskStatus.PENDING))
                .order_by(desc(Task.priority), asc(Task.due_date), desc(Task.created_at))
                .limit(3)
            )
            tasks_result = await db_session.execute(tasks_stmt)
            tasks = tasks_result.scalars().all()
            next_actions = [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "type": task.type.value,
                    "estimated_minutes": task.estimated_minutes,
                    "priority": task.priority,
                }
                for task in tasks
            ]

            # Active plans (latest 3)
            plans_stmt = (
                select(Plan)
                .where(and_(Plan.user_id == uuid.UUID(user_id), Plan.is_active))
                .order_by(desc(Plan.created_at))
                .limit(3)
            )
            plans_result = await db_session.execute(plans_stmt)
            plans = plans_result.scalars().all()
            active_plans = [
                {
                    "id": str(plan.id),
                    "title": plan.name,
                    "type": plan.type.value,
                    "target_date": plan.target_date.isoformat() if plan.target_date else None,
                    "progress": plan.progress or 0,
                }
                for plan in plans
            ]

            # Focus stats (today)
            focus_stats = await focus_service.get_today_stats(db_session, uuid.UUID(user_id))

            if user_context_data:
                # Handle preferences: could be dict (from cognitive_context) or object (from base_user_context)
                preferences_dict = {}
                if "preferences" in user_context_data:
                    prefs = user_context_data["preferences"]
                    if isinstance(prefs, dict):
                        preferences_dict = prefs
                    elif hasattr(prefs, "model_dump"):
                        preferences_dict = prefs.model_dump()
                    else:
                        logger.warning(f"Unexpected preferences type: {type(prefs)}")
                elif "user_context" in user_context_data and hasattr(user_context_data["user_context"], "preferences"):
                    # Old structure: preferences is on user_context object
                    prefs = user_context_data["user_context"].preferences
                    if hasattr(prefs, "model_dump"):
                        preferences_dict = prefs.model_dump()
                    else:
                        preferences_dict = {"depth_preference": 0.5, "curiosity_preference": 0.5}

                profile_payload = self._build_profile_payload(
                    user_context_data=user_context_data,
                    preferences=preferences_dict,
                    llm_profile_data=llm_profile_data,
                    preference_version=preference_version,
                    experiment_cohort=experiment_cohort,
                )

                return await self._attach_stage39_context(
                    {
                        "user_context": user_context_data,
                        "analytics_summary": analytics,
                        "preferences": {
                            "depth_preference": preferences_dict.get("depth_preference", 0.5),
                            "curiosity_preference": preferences_dict.get("curiosity_preference", 0.5),
                        },
                        "next_actions": next_actions,
                        "active_plans": active_plans,
                        "focus_stats": focus_stats,
                        "recent_tool_usage": await self._get_recent_tool_usage_context(
                            user_id=user_id,
                            db_session=db_session,
                        ),
                        "preference_version": preference_version,
                        "llm_profile": llm_profile_data,
                        "experiment_cohort": experiment_cohort,
                        "task_status_summary": task_status_summary,
                        "returning_context": returning_context,
                        "understanding_depth": understanding_depth,
                        "profile": profile_payload,
                        "past_session_memory": [],
                        "active_goals": [],
                        "episodic_memories": [],
                        "aurora_stage34_modes": await self._stage34_modes_payload(),
                    },
                    user_id=user_id,
                    db_session=db_session,
                )
            else:
                # Fallback to basic context
                logger.warning(f"User {user_id} not found, using fallback context")
                profile_payload = self._build_profile_payload(
                    user_context_data=None,
                    preferences={"depth_preference": 0.5, "curiosity_preference": 0.5},
                    llm_profile_data=llm_profile_data,
                    preference_version=preference_version,
                    experiment_cohort=experiment_cohort,
                )
                return await self._attach_stage39_context(
                    {
                        "user_context": None,
                        "analytics_summary": {"is_active": True, "engagement_level": "medium"},
                        "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
                        "next_actions": next_actions,
                        "active_plans": active_plans,
                        "focus_stats": focus_stats,
                        "recent_tool_usage": await self._get_recent_tool_usage_context(
                            user_id=user_id,
                            db_session=db_session,
                        ),
                        "preference_version": preference_version,
                        "llm_profile": llm_profile_data,
                        "experiment_cohort": experiment_cohort,
                        "task_status_summary": task_status_summary,
                        "returning_context": returning_context,
                        "understanding_depth": understanding_depth,
                        "profile": profile_payload,
                        "active_goals": [],
                        "episodic_memories": [],
                        "aurora_stage34_modes": await self._stage34_modes_payload(),
                    },
                    user_id=user_id,
                    db_session=db_session,
                )

        except Exception as e:
            logger.error(f"Failed to build user context: {e}")
            # Fallback
            return await self._attach_stage39_context(
                {
                    "user_context": None,
                    "analytics_summary": {"is_active": True, "engagement_level": "medium"},
                    "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
                    "preference_version": 0,
                    "llm_profile": None,
                    "returning_context": None,
                    "understanding_depth": None,
                    "profile": self._build_profile_payload(
                        user_context_data=None,
                        preferences={"depth_preference": 0.5, "curiosity_preference": 0.5},
                        llm_profile_data=None,
                        preference_version=0,
                        experiment_cohort=self._experiment_cohort_for_user(user_id),
                    ),
                    "experiment_cohort": self._experiment_cohort_for_user(user_id),
                    "past_session_memory": [],
                    "active_goals": [],
                    "episodic_memories": [],
                    "aurora_stage34_modes": await self._stage34_modes_payload(),
                },
                user_id=user_id,
                db_session=db_session,
            )

    # rule-as: ignore metadata-only four-category source manifest (C-02); observability face with no prompt/routing consumer by design
    async def _attach_source_manifest(
        self,
        payload: dict[str, Any],
        *,
        user_id: str,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        """C-02：给装配后的 payload 标注四类 source manifest（provider 读 + 分类）。

        D-CTX 迁移第一步：ContextBuilderMixin 的 stage 适配器由此降级为带来源
        标签的数据源（本方法不改任何既有值，只加 metadata["context_sources"]）。
        provider 读：User.registration_source（seed/demo 口径）与 decision_records
        最近 3 条（Events 通道，走 D-01 词表）；任一失败只降级该输入，不阻断装配。
        """
        from app.core.context_pack import estimate_tokens
        from app.orchestration.context_sources import build_payload_source_manifest

        registration_source: str | None = None
        decision_records: list[Any] = []
        try:
            from app.models.user import User as UserModel

            result = await db_session.execute(
                select(UserModel.registration_source).where(UserModel.id == uuid.UUID(user_id))
            )
            registration_source = result.scalar_one_or_none()
        except Exception as exc:
            logger.debug(f"source manifest: registration_source degraded for {user_id}: {exc}")
        try:
            from app.services.decision_record_service import DecisionRecordService

            decision_records = list(
                await DecisionRecordService(db_session).get_recent_records(uuid.UUID(user_id), limit=3)
            )
        except Exception as exc:
            logger.debug(f"source manifest: decision_records degraded for {user_id}: {exc}")

        try:
            payload["context_sources"] = build_payload_source_manifest(
                payload,
                registration_source=registration_source,
                decision_records=decision_records,
                estimate_tokens_fn=estimate_tokens,
            )
            sections = payload["context_sources"]["sections"]
            logger.info(
                "C-02 context sources user={user_id}: state={state} memory={memory} "
                "knowledge={knowledge} events={events} seed_demo_user={seed_user} overrides={overrides}",
                user_id=user_id,
                state=f"{sections['state']['item_count']}i/{sections['state']['token_estimate']}t",
                memory=f"{sections['memory']['item_count']}i/{sections['memory']['token_estimate']}t",
                knowledge=f"{sections['knowledge']['item_count']}i/{sections['knowledge']['token_estimate']}t",
                events=f"{sections['events']['item_count']}i/{sections['events']['token_estimate']}t",
                seed_user=payload["context_sources"].get("user_is_seed_or_demo", False),
                overrides=len(payload["context_sources"].get("overrides") or []),
            )
        except Exception as exc:
            logger.warning(f"Failed to attach source manifest for {user_id}: {exc}")
        return payload

    # ------------------------------------------------------------------
    # _build_returning_context
    # ------------------------------------------------------------------

    async def _build_returning_context(
        self,
        *,
        user_id: str,
        session_id: str | None,
        db_session: AsyncSession,
        locale: str = "en",
    ) -> dict[str, Any] | None:
        if not session_id or not self.redis:
            return None
        try:
            redis_key = f"returning-context:{session_id}"
            if await self.redis.exists(redis_key):
                return None

            user_uuid = uuid.UUID(user_id)
            result = await db_session.execute(
                select(ChatSession.last_message_at)
                .where(ChatSession.user_id == user_uuid, ChatSession.last_message_at.is_not(None))
                .order_by(ChatSession.last_message_at.desc())
                .limit(1)
            )
            last_message_at = result.scalar_one_or_none()
            if last_message_at is None:
                return None

            silence_gap = utcnow() - last_message_at
            if silence_gap < timedelta(minutes=30):
                AURORA_RETURNING_CONTEXT_TIER_TOTAL.labels(tier="silent_resume").inc()
                return {
                    "resume_tier": "silent_resume",
                    "last_active_at": last_message_at.isoformat(),
                    "briefing_text": "",
                    "welcome_back_message": "",
                }

            task_result = await db_session.execute(
                select(Task.title, Task.completed_at)
                .where(
                    Task.user_id == user_uuid,
                    Task.status == ModelTaskStatus.COMPLETED,
                    Task.completed_at.is_not(None),
                    Task.completed_at <= last_message_at,
                )
                .order_by(Task.completed_at.desc())
                .limit(1)
            )
            latest_completed = task_result.first()

            overdue_result = await db_session.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == user_uuid,
                    Task.status.in_([ModelTaskStatus.PENDING, ModelTaskStatus.IN_PROGRESS]),
                    Task.due_date.is_not(None),
                    Task.due_date >= last_message_at.date(),
                    Task.due_date <= utcnow().date(),
                )
            )
            overdue_count = int(overdue_result.scalar() or 0)

            upcoming_result = await db_session.execute(
                select(Task.title, Task.due_date)
                .where(
                    Task.user_id == user_uuid,
                    Task.status.in_([ModelTaskStatus.PENDING, ModelTaskStatus.IN_PROGRESS]),
                    Task.due_date.is_not(None),
                )
                .order_by(Task.due_date.asc())
                .limit(1)
            )
            next_due = upcoming_result.first()

            progress_text = I18n.t("context.no_progress_record", locale=locale)
            if latest_completed:
                progress_text = I18n.t("context.last_progress", locale=locale, step=str(latest_completed[0]))

            due_text = I18n.t("context.overdue_tasks", locale=locale, count=overdue_count)
            if next_due:
                due_text = I18n.t(
                    "context.overdue_tasks_with_next", locale=locale, count=overdue_count, title=str(next_due[0])
                )

            if silence_gap < timedelta(hours=8):
                resume_tier = "light_resume"
                welcome_back = (
                    "我接着刚才的上下文继续。"
                    if locale.startswith("zh")
                    else "I will continue from the recent context."
                )
                briefing_text = welcome_back
            elif silence_gap < timedelta(days=3):
                resume_tier = "personalized_return"
                welcome_back = I18n.t("context.welcome_back", locale=locale, progress=progress_text, due=due_text)
                briefing_text = f"{progress_text}{due_text}"
            else:
                resume_tier = "checkpoint_debrief"
                welcome_back = I18n.t("context.welcome_back", locale=locale, progress=progress_text, due=due_text)
                briefing_text = f"{progress_text}{due_text}"

            payload = {
                "resume_tier": resume_tier,
                "days_away": max(int(silence_gap.days), 0),
                "hours_away": round(silence_gap.total_seconds() / 3600, 1),
                "last_active_at": last_message_at.isoformat(),
                "last_progress": progress_text,
                "overdue_task_count": overdue_count,
                "next_due_task_title": str(next_due[0]) if next_due else "",
                "welcome_back_message": welcome_back,
                "briefing_text": briefing_text,
            }
            AURORA_RETURNING_CONTEXT_TIER_TOTAL.labels(tier=resume_tier).inc()
            await self.redis.setex(redis_key, 24 * 60 * 60, "1")
            return payload
        except Exception as exc:
            logger.warning(f"Failed to build returning context: {exc}")
            return None

    # ------------------------------------------------------------------
    # _build_conversation_context
    # ------------------------------------------------------------------

    async def _build_conversation_context(self, session_id: str, user_id: str) -> dict[str, Any]:
        """
        Build conversation context with ContextPruner

        Returns:
            Dict containing pruned history and summary
        """
        if not self.context_pruner:
            logger.warning("ContextPruner not initialized, returning empty context")
            return {"messages": [], "summary": None}

        try:
            pruned_result = await self.context_pruner.get_pruned_history(session_id=session_id, user_id=user_id)

            logger.debug(
                f"Conversation context for session {session_id}: "
                f"{pruned_result['original_count']} -> {pruned_result['pruned_count']} messages, "
                f"summary_used={pruned_result['summary_used']}"
            )

            return pruned_result

        except Exception as e:
            logger.error(f"Failed to prune conversation history: {e}")
            return {"messages": [], "summary": None}

    # ------------------------------------------------------------------
    # _log_context_injection
    # ------------------------------------------------------------------

    def _log_context_injection(self, user_id: str, context: dict[str, Any] | None) -> None:
        """Log context injection details for observability."""
        if not context or not isinstance(context, dict):
            logger.info("Context injection for user {}: empty", user_id)
            return

        next_actions = context.get("next_actions") or context.get("pending_tasks") or []
        active_plans = context.get("active_plans") or []

        tasks_count = len(next_actions) if isinstance(next_actions, list) else 0
        plans_count = len(active_plans) if isinstance(active_plans, list) else 0

        last_activity = None
        user_ctx = context.get("user_context")
        if isinstance(user_ctx, dict):
            last_activity = user_ctx.get("last_activity_time") or user_ctx.get("last_login")

        if not last_activity and isinstance(context.get("analytics_summary"), dict):
            last_activity = context["analytics_summary"].get("last_login") or context["analytics_summary"].get(
                "last_activity_time"
            )

        logger.info(
            "Context injection for user {}: {} tasks, {} plans, last_activity={}",
            user_id,
            tasks_count,
            plans_count,
            last_activity,
        )

    # ------------------------------------------------------------------
    # _build_full_context
    # ------------------------------------------------------------------

    async def _build_full_context(
        self,
        *,
        request: agent_service_pb2.ChatRequest,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        user_message: str,
        request_id: str,
        tracer,
    ) -> tuple[
        dict[str, Any], uuid.UUID | None, bool, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None
    ]:
        grpc_context = {}
        if request.user_profile and request.user_profile.extra_context:
            try:
                grpc_context = json.loads(request.user_profile.extra_context)
                logger.debug(f"Parsed extra_context from gRPC: {list(grpc_context.keys())}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse extra_context JSON: {e}")

        request_context = {}
        if request.HasField("extra_context"):
            try:
                request_context = MessageToDict(request.extra_context)
                if request_context:
                    logger.debug(f"Parsed request extra_context: {list(request_context.keys())}")
            except Exception as e:
                logger.warning(f"Failed to parse request extra_context: {e}")

        if request_context:
            grpc_context = {**grpc_context, **request_context}

        plan_id = None
        if grpc_context and "plan_id" in grpc_context:
            with contextlib.suppress(ValueError, AttributeError):
                plan_id = uuid.UUID(grpc_context["plan_id"])

        plan_switched = False
        _ctx_probe_marks: list[tuple[str, float]] = []
        _ctx_probe_t = time.perf_counter()
        if not plan_id and user_message and active_db:
            with tracer.start_as_current_span("orchestrator.auto_switch_plan"):
                try:
                    from app.services.plan_matching_service import PlanMatchingService

                    plan_matching = PlanMatchingService(active_db)
                    matched_plan_id = await self.state_manager.auto_switch_plan(
                        session_id=session_id,
                        user_id=uuid.UUID(user_id),
                        task_context={
                            "content": user_message,
                            "type": grpc_context.get("task_type", "chat"),
                        },
                        db_session=active_db,
                        plan_matching_service=plan_matching,
                    )
                    if matched_plan_id:
                        plan_id = matched_plan_id
                        plan_switched = True
                        logger.info(f"Auto-switched to plan {plan_id} based on message content")
                except Exception as e:
                    logger.warning(f"Auto-switch plan failed: {e}")

        overlay_versions = {}
        if grpc_context:
            versions = grpc_context.get("realtime_versions")
            if isinstance(versions, dict):
                overlay_versions = {str(k): str(v) for k, v in versions.items()}
        if overlay_versions:
            await self._self_heal_versions(user_id, overlay_versions, active_db)

        if grpc_context and ("realtime_versions" in grpc_context or "overlay_generated_at" in grpc_context):
            grpc_context = dict(grpc_context)
            grpc_context.pop("realtime_versions", None)
            grpc_context.pop("overlay_generated_at", None)

        user_context_payload = None
        conversation_context = None
        plan_context = None
        with tracer.start_as_current_span("db.build_context"):
            if active_db and user_id:
                _h0 = time.perf_counter()
                # C-07：版本化键解析（write/correction 指令轮与版本解析失败
                # 均得 None → 整轮绕缓存重建，fail-closed）。
                _cache_key, _cache_outcome = await self._context_cache_resolve_key(user_id, active_db, user_message)
                local_context = None
                if _cache_key is not None:
                    local_context = self._context_cache_lookup(_cache_key)
                if local_context is not None:
                    _ctx_probe_marks.append(("build_user_context_cached", time.perf_counter() - _h0))
                else:
                    local_context = await self._build_user_context(user_id, active_db, session_id=session_id)
                    if isinstance(local_context, dict) and _cache_key is not None:
                        self._context_cache_store(_cache_key, local_context)
                    _ctx_probe_marks.append(("build_user_context", time.perf_counter() - _h0))
                user_context_payload = self._merge_user_contexts(local_context, grpc_context)
                logger.info(f"Merged user context: {user_context_payload is not None}")

                # C-02：grpc 合并面的覆盖不再静默——显式登记 + 告警（值语义不变）。
                if isinstance(user_context_payload, dict):
                    from app.orchestration.context_sources import (
                        GRPC_MERGE_KEYS,
                        attach_overrides,
                        detect_merge_overrides,
                    )

                    merge_overrides = detect_merge_overrides(local_context, user_context_payload, GRPC_MERGE_KEYS)
                    if merge_overrides and isinstance(user_context_payload.get("context_sources"), dict):
                        user_context_payload["context_sources"] = attach_overrides(
                            user_context_payload["context_sources"], merge_overrides
                        )

                if plan_id:
                    try:
                        from app.core.plan_context import PlanContextBuilder
                        from app.services.plan_state_service import PlanStateService

                        plan_builder = PlanContextBuilder(active_db, self.redis)
                        plan_context = await plan_builder.build_enriched(uuid.UUID(user_id), plan_id)
                        if plan_context:
                            logger.info(f"Built plan_context for plan_id={plan_id}")
                            if user_context_payload is None:
                                user_context_payload = {}
                            user_context_payload["plan_context"] = plan_context

                            try:
                                plan_state_svc = PlanStateService(active_db, self.redis)
                                normalized_plan_id = uuid.UUID(str(plan_id))
                                plan_state = await plan_state_svc.get_plan_state(uuid.UUID(user_id), normalized_plan_id)
                                if plan_state and plan_state.constraints.get("require_phase_rollback"):
                                    logger.info(f"Phase rollback triggered for plan_id={plan_id}")
                                    await plan_state_svc.upsert_plan_state(
                                        user_id=uuid.UUID(user_id),
                                        plan_id=normalized_plan_id,
                                        patch={"constraints": {"require_phase_rollback": False}},
                                        bump_version=False,
                                    )

                                    locale = (
                                        user_context_payload.get("profile", {})
                                        .get("identity", {})
                                        .get("language", "en")
                                    )
                                    plan_context["mode"] = "phase_rollback"
                                    plan_context["rollback_reason"] = I18n.t("context.rollback_reason", locale=locale)
                                    if plan_state.feedback_log:
                                        plan_context["previous_feedback"] = plan_state.feedback_log[-2:]
                            except Exception as e:
                                logger.warning(f"Failed to check phase rollback: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to build plan context: {e}")

                try:
                    user_uuid = uuid.UUID(user_id)
                    router = ToolPreferenceRouter(active_db, user_uuid, self.redis)
                    preferred_tools = await router.get_preferred_tools(limit=3)
                    if preferred_tools:
                        if user_context_payload is not None:
                            user_context_payload["preferred_tools"] = preferred_tools
                        logger.info(f"Injected tool preferences for user {user_id}: {preferred_tools}")
                except Exception as e:
                    logger.warning(f"Failed to get tool preferences (non-fatal): {e}")
                    if active_db:
                        await active_db.rollback()
            elif grpc_context:
                user_context_payload = grpc_context
                logger.info("Using gRPC context without local DB context")

        self._log_context_injection(user_id, user_context_payload)
        _h1 = time.perf_counter()
        if self.context_pruner:
            with tracer.start_as_current_span("db.build_conversation_context"):
                conversation_context = await self._build_conversation_context(session_id, user_id)
        # C-02 history 语义：会话历史归 events 通道，仅最近必要消息 + compaction
        # 边界（ContextPruner 的 recent window + summary），不替代 state——
        # state 通道没有 conversation_history 写入点（context_sources 铁律）。
        if isinstance(user_context_payload, dict) and isinstance(conversation_context, dict):
            from app.core.context_pack import estimate_tokens
            from app.orchestration.context_sources import attach_conversation_history

            messages = conversation_context.get("messages") or []
            history_stats = {
                "messages": len(messages),
                "original_count": int(conversation_context.get("original_count", len(messages)) or 0),
                "pruned_count": int(conversation_context.get("pruned_count", len(messages)) or 0),
                "summary_used": bool(conversation_context.get("summary_used", False)),
                "recent_window": int(getattr(self.context_pruner, "summary_recent_window", 0) or 0),
            }
            history_tokens = estimate_tokens(json.dumps(messages, ensure_ascii=False, default=str))
            if isinstance(user_context_payload.get("context_sources"), dict):
                user_context_payload["context_sources"] = attach_conversation_history(
                    user_context_payload["context_sources"], history_stats
                )
                events_section = user_context_payload["context_sources"]["sections"]["events"]
                events_section["token_estimate"] = int(events_section.get("token_estimate", 0) or 0) + history_tokens
            logger.info(
                "C-02 conversation history (events channel): messages={messages} original={original} "
                "summary_used={summary_used} tokens={tokens}",
                messages=history_stats["messages"],
                original=history_stats["original_count"],
                summary_used=history_stats["summary_used"],
                tokens=history_tokens,
            )
        _ctx_probe_marks.append(("build_conversation_context", time.perf_counter() - _h1))
        _h2 = time.perf_counter()
        if active_db and user_message:
            await self._persist_user_message(
                active_db=active_db,
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                request_id=request_id,
            )
        _ctx_probe_marks.append(("persist_user_message", time.perf_counter() - _h2))
        if _ctx_probe_marks:
            _chain = " ".join(f"{name}={delta * 1000:.0f}ms" for name, delta in _ctx_probe_marks)
            logger.info(
                "[LATENCY] build_full_context session={} {}",
                session_id,
                _chain,
            )

        return grpc_context, plan_id, plan_switched, user_context_payload, conversation_context, plan_context

    async def _persist_user_message(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        user_message: str,
        request_id: str | None,
    ) -> None:
        """持久化本轮用户消息（R2-09 / RB-06 follow-up）。

        使用 ``flush`` 而非 ``commit``：``active_db`` 是 gRPC 流的共享会话，
        提交所有权在 ``app/services/agent_grpc_service.py``（stream 结束统一
        commit、异常 rollback，:354-399）。中途 commit 会破坏"一轮一事务"
        原子性——用户消息已提交而后续任何环节失败时，外层 rollback 无法回滚它。
        flush 已分配 PK，同会话内后续读取同样可见。
        """
        try:
            # B-01：首条用户消息落库前幂等补建 chat_sessions 头（与消息同事务，
            # 由 agent_grpc_service 流末统一提交）。头行缺失时网关 sessions 列表
            # （getRecentSessionsFromDB 只读 chat_sessions）永远为空，移动端重启
            # 后拿不到 conversationId——V13「发了但看不见」的后端根因。
            # 失败非致命：吞掉告警后继续持久化消息本身（保持本函数既有语义）。
            try:
                from app.orchestration.persistence_layer import ensure_chat_session_header

                await ensure_chat_session_header(
                    active_db,
                    user_id=uuid.UUID(str(user_id)),
                    session_id=self._coerce_session_uuid(session_id),
                )
            except Exception as header_err:
                logger.warning(f"Failed to ensure chat session header (non-fatal): {header_err}")
            user_msg = ChatMessage(
                user_id=uuid.UUID(str(user_id)),
                session_id=self._coerce_session_uuid(session_id),
                role=MessageRole.USER,
                content=user_message,
                message_id=request_id,
            )
            active_db.add(user_msg)
            await active_db.flush()
        except Exception as e:
            logger.warning(f"Failed to persist user chat message: {e}")
            with contextlib.suppress(Exception):
                await active_db.rollback()

    @staticmethod
    def _coerce_session_uuid(session_id: str) -> uuid.UUID:
        try:
            return uuid.UUID(session_id)
        except ValueError:
            return uuid.UUID(int=0)
