from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.aurora.predicted_reply_engine import PredictedReplyOptionEngine
from app.aurora.runtime_v1.control_surface import ControlSurfaceService
from app.aurora.runtime_v1.persistence import AuroraPersistenceStore
from app.aurora.runtime_v1.self_model import SparkleSelfModelService
from app.aurora.runtime_v1.state import AuroraCognitiveSnapshot, AuroraEnergyStore, AuroraRuntimeStore, AuroraState
from app.core.profile_context import ProfileContext
from app.core.user_insight_state import UserInsightState
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_context_service import ProfileContextService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _strip(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp_unit(value: Any, *, default: float = 0.0) -> float:
    numeric = _safe_float(value)
    if numeric is None:
        numeric = default
    return round(max(0.0, min(1.0, numeric)), 4)


def _freshness_from_iso(value: Any) -> int | None:
    text = _strip(value)
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return max(0, int((_utcnow() - parsed).total_seconds()))


class AuroraControlSurfaceService:
    """Aggregate Aurora's live cognitive state into a product-facing control surface."""

    _SURFACES: tuple[str, ...] = (
        "aurora_modeling",
        "aurora_planning",
        "aurora_checkpoint",
    )
    _FACET_LABELS: dict[str, str] = {
        "user_model": "用户建模",
        "self_model": "自我建模",
        "scene_model": "情景建模",
        "goal_model": "目标建模",
    }

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis

    async def build_snapshot(
        self,
        *,
        user_id: UUID,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        profile_context = await ProfileContextService(self.db, self.redis).get_profile_context(user_id)
        profile_payload = profile_context.to_prompt_context()
        runtime_state = await self._load_runtime_state(user_id=user_id, conversation_id=conversation_id)
        persisted_snapshot = await self._load_persisted_snapshot(user_id=user_id)
        self_model = await SparkleSelfModelService(self.redis).get_readout_summary(
            user_id=str(user_id),
            user_context_payload={"profile_context": profile_payload},
        )
        control_surface = await ControlSurfaceService(
            self.db,
            self.redis,
            preference_service=PreferenceService(self.db, self.redis),
            enabled=True,
        ).read_control_surface(user_id)

        facets = [
            self._build_user_model_facet(profile_context=profile_context),
            self._build_self_model_facet(self_model=self_model),
            self._build_scene_model_facet(
                profile_context=profile_context,
                runtime_state=runtime_state,
                persisted_snapshot=persisted_snapshot,
                control_surface=control_surface.model_dump(mode="json"),
                requested_conversation_id=conversation_id,
            ),
            self._build_goal_model_facet(
                profile_context=profile_context,
                runtime_state=runtime_state,
                persisted_snapshot=persisted_snapshot,
            ),
        ]

        ready_count = sum(1 for item in facets if item["status"] == "ready")
        recalibrating = any(item["status"] == "recalibrating" for item in facets)
        active_count = sum(1 for item in facets if item["status"] != "missing")
        aurora_active = bool(profile_context.user_insight_state or runtime_state or persisted_snapshot)

        # Resolve energy level and wake eligibility
        energy_store = AuroraEnergyStore(self.redis)
        has_risk = recalibrating or any(
            item.get("meta", {}).get("needs_recalibration") for item in facets if item["key"] == "self_model"
        )
        energy = await energy_store.resolve_energy_level(
            user_id,
            aurora_active=aurora_active,
            overall_status="recalibrating" if recalibrating else ("ready" if ready_count == len(facets) else "partial"),
            ready_count=ready_count,
            total_count=len(facets),
            has_risk=has_risk,
        )
        wake_eligibility = energy_store.compute_wake_eligibility(
            energy,
            wake_reasons=self._collect_wake_reasons(facets, recalibrating),
        )

        # 6-state model: sensing | calibrated | risk_found | needs_confirm | calibration_available | cooling_down
        band_status = self._resolve_band_status(
            energy=energy,
            aurora_active=aurora_active,
            ready_count=ready_count,
            total_count=len(facets),
            recalibrating=recalibrating,
            active_count=active_count,
        )
        summary = self._band_status_summary(band_status, facets)

        matched_conversation_id = _strip(getattr(runtime_state, "conversation_id", None))
        normalized_requested = _strip(conversation_id)
        scene_alignment = "matched"
        if normalized_requested:
            scene_alignment = (
                "matched"
                if matched_conversation_id and matched_conversation_id == normalized_requested
                else "fallback"
            )

        # Build predicted reply options from current Aurora state
        tensions_payload = [
            t.model_dump() if hasattr(t, "model_dump") else dict(t)
            for t in getattr(runtime_state, "informational_tensions", []) or []
        ]
        user_model_meta = self._extract_user_model_meta(profile_context)
        predicted_reply_options = PredictedReplyOptionEngine().generate(
            band_status=band_status,
            facets=facets,
            informational_tensions=tensions_payload,
            energy_level=energy.current_level,
            wake_eligibility=wake_eligibility.model_dump(),
            user_model_meta=user_model_meta,
        )

        return {
            "aurora_active": aurora_active,
            "runtime_enabled": bool(control_surface.runtime_enabled),
            "overall_status": band_status,
            "legacy_status": "recalibrating" if recalibrating else ("ready" if ready_count == len(facets) else "partial"),
            "energy_level": energy.current_level,
            "summary": summary,
            "progress": {
                "ready_count": ready_count,
                "active_count": active_count,
                "total": len(facets),
            },
            "wake_eligibility": wake_eligibility.model_dump(),
            "predicted_reply_options": predicted_reply_options,
            "conversation_id": matched_conversation_id or normalized_requested or None,
            "requested_conversation_id": normalized_requested or None,
            "scene_alignment": scene_alignment,
            "surface": _strip(getattr(runtime_state, "surface", None))
            or _strip(getattr(persisted_snapshot, "last_surface", None))
            or None,
            "updated_at": (
                getattr(runtime_state, "updated_at", None)
                or getattr(persisted_snapshot, "updated_at", None)
                or _utcnow()
            ).isoformat(),
            "facets": facets,
        }

    async def _load_runtime_state(
        self,
        *,
        user_id: UUID,
        conversation_id: str | None,
    ) -> AuroraState | None:
        store = AuroraRuntimeStore(self.redis, enabled=True)
        normalized_conversation_id = _strip(conversation_id)

        if normalized_conversation_id:
            matched: list[AuroraState] = []
            for surface in self._SURFACES:
                state = await store.load_runtime_state(
                    user_id=str(user_id),
                    surface=surface,
                    conversation_id=normalized_conversation_id,
                )
                if state is not None:
                    matched.append(state)
            if matched:
                matched.sort(key=lambda item: item.updated_at, reverse=True)
                return matched[0]

        fallback: list[AuroraState] = []
        for surface in self._SURFACES:
            state = await store.load_latest_surface_state(
                user_id=str(user_id),
                surface=surface,
            )
            if state is not None:
                fallback.append(state)
        if not fallback:
            return None
        fallback.sort(key=lambda item: item.updated_at, reverse=True)
        return fallback[0]

    async def _load_persisted_snapshot(
        self,
        *,
        user_id: UUID,
    ) -> AuroraCognitiveSnapshot | None:
        try:
            return await AuroraPersistenceStore(self.db, enabled=True).load_cognitive_snapshot(user_id)
        except Exception:
            return None

    def _build_user_model_facet(
        self,
        *,
        profile_context: ProfileContext,
    ) -> dict[str, Any]:
        insight_state = profile_context.user_insight_state or UserInsightState()
        active_patterns = list(profile_context.cognitive_summary.active_patterns or [])
        weak_spots = list(profile_context.knowledge_summary.weak_spots or [])
        bottlenecks = list(insight_state.active_bottlenecks or [])
        contradictions = list(insight_state.active_contradictions or [])
        recent_pain_points = list(insight_state.recent_pain_points or [])

        signals: list[str] = []
        if bottlenecks:
            label = _strip(bottlenecks[0].get("label"))
            if label:
                signals.append(f"瓶颈: {label}")
        if weak_spots:
            signals.append(f"薄弱点: {weak_spots[0].node_name}")
        if active_patterns:
            signals.append(f"模式: {active_patterns[0].pattern_name}")
        if recent_pain_points:
            pain = _strip(recent_pain_points[0].get("label"))
            if pain:
                signals.append(f"痛点: {pain}")

        signal_count = sum(
            1
            for present in (
                bool(insight_state.stable_preferences),
                bool(insight_state.current_state),
                bool(active_patterns),
                bool(weak_spots),
                bool(bottlenecks),
                bool(contradictions),
            )
            if present
        )
        confidence_values = [
            float(value)
            for value in _as_dict(insight_state.confidence_metadata).values()
            if _safe_float(value) is not None
        ]
        confidence = round(
            sum(confidence_values) / len(confidence_values),
            4,
        ) if confidence_values else round(min(signal_count / 5.0, 1.0), 4)
        status = "ready" if signal_count >= 3 else ("partial" if signal_count >= 1 else "missing")

        summary = "Aurora 还没有形成稳定的用户画像。"
        if bottlenecks:
            label = _strip(bottlenecks[0].get("label"))
            summary = f"当前最突出的用户瓶颈是“{label}”。" if label else summary
        elif weak_spots:
            summary = f"当前知识薄弱点集中在「{weak_spots[0].node_name}」。"
        elif active_patterns:
            summary = f"Aurora 已识别出行为模式「{active_patterns[0].pattern_name}」。"

        freshness_candidates = self._collect_user_state_freshness(profile_context)
        return self._facet_payload(
            key="user_model",
            status=status,
            summary=summary,
            confidence=confidence,
            freshness_seconds=min(freshness_candidates) if freshness_candidates else None,
            signal_count=signal_count,
            signals=signals,
            meta={
                "active_pattern_count": len(active_patterns),
                "weak_spot_count": len(weak_spots),
                "bottleneck_count": len(bottlenecks),
                "contradiction_count": len(contradictions),
            },
        )

    def _build_self_model_facet(
        self,
        *,
        self_model: dict[str, Any],
    ) -> dict[str, Any]:
        confidence = _clamp_unit(self_model.get("strategy_confidence"), default=0.0)
        assumptions = _as_list(self_model.get("known_assumptions"))
        harness = _as_dict(self_model.get("harness_effectiveness"))
        recalibration = bool(self_model.get("needs_recalibration"))
        reasons = [str(item).strip() for item in _as_list(self_model.get("recalibration_reasons")) if str(item).strip()]

        signals: list[str] = []
        if harness.get("task_completion_rate") is not None:
            signals.append(
                f"任务完成率 {round(_clamp_unit(harness.get('task_completion_rate')) * 100):.0f}%"
            )
        if harness.get("context_hit_rate") is not None:
            signals.append(
                f"策略命中率 {round(_clamp_unit(harness.get('context_hit_rate')) * 100):.0f}%"
            )
        if recalibration and reasons:
            signals.append(reasons[0])

        if recalibration:
            status = "recalibrating"
            summary = reasons[0] if reasons else "Aurora 检测到自身策略需要重新校准。"
        elif assumptions:
            status = "ready" if confidence >= 0.65 else "partial"
            summary = f"Aurora 当前对自身策略把握度约为 {round(confidence * 100):.0f}%。"
        else:
            status = "missing"
            summary = "Aurora 还没有形成稳定的自我校准读数。"

        freshness_candidates = self._collect_assumption_freshness(assumptions)
        return self._facet_payload(
            key="self_model",
            status=status,
            summary=summary,
            confidence=confidence,
            freshness_seconds=min(freshness_candidates) if freshness_candidates else None,
            signal_count=len(assumptions),
            signals=signals,
            meta={
                "task_failure_streak": int(self_model.get("task_failure_streak") or 0),
                "needs_recalibration": recalibration,
            },
        )

    def _build_scene_model_facet(
        self,
        *,
        profile_context: ProfileContext,
        runtime_state: AuroraState | None,
        persisted_snapshot: AuroraCognitiveSnapshot | None,
        control_surface: dict[str, Any],
        requested_conversation_id: str | None,
    ) -> dict[str, Any]:
        insight_state = profile_context.user_insight_state or UserInsightState()
        current_state = _as_dict(insight_state.current_state)
        readiness = _as_dict(insight_state.readiness)
        runtime_snapshot = _as_dict(getattr(runtime_state, "user_model_snapshot", None))
        runtime_surface_state = _as_dict(runtime_snapshot.get("surface_state"))
        tensions = list(getattr(runtime_state, "informational_tensions", None) or [])
        if not tensions and persisted_snapshot is not None:
            tensions = list(persisted_snapshot.informational_tensions or [])
        latent_threads = list(getattr(runtime_state, "latent_threads", None) or [])
        requested = _strip(requested_conversation_id)
        actual = _strip(getattr(runtime_state, "conversation_id", None))

        signal_count = sum(
            1
            for present in (
                bool(current_state),
                bool(readiness),
                bool(runtime_surface_state),
                bool(tensions),
                bool(latent_threads),
                bool(getattr(runtime_state, "current_intent", None)),
            )
            if present
        )

        confidence = round(min(signal_count / 5.0, 1.0), 4)
        status = "ready" if signal_count >= 3 else ("partial" if signal_count >= 1 else "missing")

        summary = "Aurora 还没有读到足够稳定的当前情景。"
        overload = _strip(current_state.get("predicted_overload_risk"))
        if requested and actual and requested != actual:
            summary = "当前情景读数回退到了最近一次 Aurora 运行快照。"
        elif overload:
            summary = f"当前情景判断显示过载风险为「{overload}」。"
        elif runtime_surface_state.get("in_detour") is True:
            summary = "当前对话处在偏航分支里，Aurora 正在保持原线索并处理临时岔题。"
        elif tensions:
            top_tension = tensions[0]
            description = _strip(getattr(top_tension, "description", None) or _as_dict(top_tension).get("description"))
            if description:
                summary = f"当前情景的主张力是“{description}”。"
        elif readiness:
            level = _strip(readiness.get("predicted_level") or readiness.get("recommended_action"))
            if level:
                summary = f"当前规划就绪度判断为「{level}」。"

        signals: list[str] = []
        if actual:
            signals.append(f"会话: {actual}")
        if _strip(getattr(runtime_state, "surface", None)):
            signals.append(f"表面: {runtime_state.surface}")
        if overload:
            signals.append(f"过载风险: {overload}")
        if runtime_surface_state.get("in_detour") is True:
            signals.append("处于 detour 分支")
        intent_type = _strip(getattr(getattr(runtime_state, "current_intent", None), "intent_type", None))
        if intent_type:
            signals.append(f"当前意图: {intent_type}")

        freshness = (
            _freshness_from_iso(getattr(runtime_state, "updated_at", None))
            or _freshness_from_iso(getattr(persisted_snapshot, "updated_at", None))
        )
        return self._facet_payload(
            key="scene_model",
            status=status,
            summary=summary,
            confidence=confidence,
            freshness_seconds=freshness,
            signal_count=signal_count,
            signals=signals,
            meta={
                "conversation_match": not requested or (actual and requested == actual),
                "latent_thread_count": len(latent_threads),
                "tension_count": len(tensions),
                "runtime_enabled": bool(_as_dict(control_surface).get("runtime_enabled")),
            },
        )

    def _build_goal_model_facet(
        self,
        *,
        profile_context: ProfileContext,
        runtime_state: AuroraState | None,
        persisted_snapshot: AuroraCognitiveSnapshot | None,
    ) -> dict[str, Any]:
        insight_state = profile_context.user_insight_state or UserInsightState()
        goals = list(insight_state.goals or [])
        runtime_snapshot = _as_dict(getattr(runtime_state, "user_model_snapshot", None))
        persisted_snapshot_payload = _as_dict(getattr(persisted_snapshot, "user_model_snapshot", None))
        cold_start = (
            _as_dict(runtime_snapshot.get("cold_start_context"))
            or _as_dict(persisted_snapshot_payload.get("cold_start_context"))
            or _as_dict(profile_context.preferences.get("cold_start_context"))
        )

        goal_label = ""
        for goal in goals:
            goal_label = _strip(goal.get("label") or goal.get("goal") or goal.get("summary"))
            if goal_label:
                break
        if not goal_label:
            goal_label = _strip(
                cold_start.get("goal")
                or cold_start.get("goal_summary")
                or cold_start.get("goal_raw")
                or cold_start.get("subject")
                or cold_start.get("exam_scope")
            )

        scope_text = _strip(cold_start.get("exam_scope") or cold_start.get("subject") or cold_start.get("scope"))
        time_text = _strip(
            cold_start.get("time_constraint_days")
            or cold_start.get("days_left")
            or cold_start.get("time_available")
            or cold_start.get("daily_available_hours")
        )
        motivation_text = _strip(cold_start.get("motivation") or cold_start.get("motivation_context"))

        signal_count = sum(
            1
            for present in (
                bool(goal_label),
                bool(scope_text),
                bool(time_text),
                bool(motivation_text),
                bool(goals),
            )
            if present
        )
        confidence = round(min(signal_count / 4.0, 1.0), 4)
        status = "ready" if signal_count >= 3 else ("partial" if signal_count >= 1 else "missing")

        if goal_label:
            summary = f"当前目标锚点是“{goal_label}”。"
        else:
            summary = "Aurora 还没有抓到稳定的目标锚点。"

        signals: list[str] = []
        if scope_text:
            signals.append(f"范围: {scope_text}")
        if time_text:
            signals.append(f"时间: {time_text}")
        if motivation_text:
            signals.append(f"动机: {motivation_text}")
        if goal_label and goal_label not in signals:
            signals.insert(0, f"目标: {goal_label}")

        freshness = (
            _freshness_from_iso(getattr(runtime_state, "updated_at", None))
            or _freshness_from_iso(getattr(persisted_snapshot, "updated_at", None))
            or min(self._collect_user_state_freshness(profile_context), default=None)
        )
        return self._facet_payload(
            key="goal_model",
            status=status,
            summary=summary,
            confidence=confidence,
            freshness_seconds=freshness,
            signal_count=signal_count,
            signals=signals,
            meta={
                "goal_count": len(goals),
                "has_time_constraint": bool(time_text),
                "has_scope": bool(scope_text),
            },
        )

    def _facet_payload(
        self,
        *,
        key: str,
        status: str,
        summary: str,
        confidence: float | None,
        freshness_seconds: int | None,
        signal_count: int,
        signals: list[str],
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "key": key,
            "label": self._FACET_LABELS[key],
            "status": status,
            "summary": summary,
            "confidence": confidence,
            "freshness_seconds": freshness_seconds,
            "signal_count": signal_count,
            "signals": [item for item in signals if _strip(item)][:3],
            "meta": meta or {},
        }

    def _collect_user_state_freshness(self, profile_context: ProfileContext) -> list[int]:
        payload = _as_dict(profile_context.user_state_v1)
        freshness_values: list[int] = []
        for value in payload.values():
            field_payload = _as_dict(value)
            freshness = field_payload.get("freshness_seconds")
            try:
                if freshness is not None:
                    freshness_values.append(int(freshness))
            except (TypeError, ValueError):
                continue
        return freshness_values

    def _collect_assumption_freshness(self, assumptions: list[Any]) -> list[int]:
        results: list[int] = []
        for item in assumptions:
            assumption = _as_dict(item)
            for evidence in _as_list(assumption.get("evidence")):
                freshness = _freshness_from_iso(_as_dict(evidence).get("observed_at"))
                if freshness is not None:
                    results.append(freshness)
        return results

    def _resolve_band_status(
        self,
        *,
        energy,
        aurora_active: bool,
        ready_count: int,
        total_count: int,
        recalibrating: bool,
        active_count: int,
    ) -> str:
        from app.aurora.runtime_v1.state import AuroraEnergyState

        if not isinstance(energy, AuroraEnergyState):
            return "sensing"
        if energy.is_cooling_down:
            return "cooling_down"
        if not aurora_active:
            return "sensing"
        if recalibrating:
            return "risk_found"
        # Check if any facet has a judgment needing confirmation
        if ready_count >= 3 and energy.can_user_wake:
            return "calibration_available"
        if ready_count == total_count:
            return "calibrated"
        if active_count >= 2:
            return "needs_confirm"
        return "sensing"

    def _band_status_summary(self, band_status: str, facets: list[dict]) -> str:
        summaries = {
            "sensing": "Aurora 正在轻量感知，参考当前上下文优化回复。",
            "calibrated": "Aurora 的四层感知已对齐，当前策略可以直接执行。",
            "risk_found": "Aurora 发现策略风险，建议确认或调整当前方向。",
            "needs_confirm": "Aurora 有一个判断需要你确认。",
            "calibration_available": "Aurora 深度校准可用，适合在关键时刻重新校准理解。",
            "cooling_down": "Aurora 深度校准刚完成，正在冷却中。可以先做快速校准。",
        }
        return summaries.get(band_status, summaries["sensing"])

    def _extract_user_model_meta(self, profile_context: ProfileContext) -> dict[str, Any]:
        """Extract lightweight user model metadata for predicted reply option generation."""
        insight = profile_context.user_insight_state
        if not insight:
            return {}
        return {
            "available_time_confirmed": bool(
                _as_dict(getattr(insight, "current_state", None)).get("available_time")
            ),
            "goal_type_confirmed": bool(
                _as_list(
                    profile_context.user_insight_state.goals
                    if profile_context.user_insight_state
                    else None
                )
            ),
        }

    def _collect_wake_reasons(self, facets: list[dict], recalibrating: bool) -> list[str]:
        reasons: list[str] = []
        if recalibrating:
            reasons.append("self_model_recalibrating")
        for facet in facets:
            meta = _as_dict(facet.get("meta"))
            if meta.get("needs_recalibration"):
                reasons.append("strategy_confidence_drop")
            if facet.get("status") == "recalibrating":
                reasons.append(f"{facet.get('key')}_recalibrating")
        return reasons[:5]
