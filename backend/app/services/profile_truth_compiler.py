from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from app.core.profile_context import ProfileContext
from app.orchestration.schemas import CompiledInsightState

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

class ProfileTruthCompiler:
    """
    Profile Truth Compiler - Phase A1
    Reconciles multiple profile signals into a single coherent truth model.
    """

    async def compile(
        self,
        *,
        profile_context: ProfileContext,
        user_strategy_state: dict[str, Any] | None = None,
        companion_state: dict[str, Any] | None = None,
        turn_signals: dict[str, Any] | None = None,
    ) -> CompiledInsightState:
        """Compile a unified insight state from multiple sources."""
        
        stable_traits = self._extract_stable_traits(profile_context)
        current_state = self._extract_current_state(profile_context, user_strategy_state)
        
        # Initial extraction of constraints and bottlenecks
        active_constraints = self._extract_constraints(profile_context)
        active_bottlenecks = self._extract_bottlenecks(profile_context)
        
        # Map signal confidence and freshness
        confidence_map = self._build_confidence_map(profile_context)
        freshness_map = self._build_freshness_map(profile_context)
        
        # Detect contradictions between sources
        contradictions = self._detect_contradictions(
            profile_context=profile_context,
            stable_traits=stable_traits,
            current_state=current_state,
            active_constraints=active_constraints,
            turn_signals=turn_signals or {},
        )

        return CompiledInsightState(
            stable_traits=stable_traits,
            current_state=current_state,
            active_constraints=active_constraints,
            active_bottlenecks=active_bottlenecks,
            confidence_map=confidence_map,
            freshness_map=freshness_map,
            contradiction_map=contradictions,
            generated_at=_utcnow_iso()
        )

    def _extract_stable_traits(self, pc: ProfileContext) -> dict[str, Any]:
        """Traits that don't change frequently (personality, base preferences)."""
        traits = {}
        # Explicit preferences are high-signal traits
        traits.update(pc.preferences or {})
        return traits

    def _extract_current_state(self, pc: ProfileContext, strategy: dict[str, Any] | None) -> dict[str, Any]:
        """Transient state (current mastery, active focus, active strategy)."""
        state = {
            "overall_mastery": pc.knowledge_summary.overall_mastery,
            "active_subjects": pc.knowledge_summary.active_learning_subjects,
        }
        if strategy:
            for source_key, target_key in (
                ("session_mode", "strategy_mode"),
                ("active_mode", "strategy_mode"),
                ("push_vs_support", "push_vs_support"),
                ("intervention_intensity", "intervention_intensity"),
                ("explanation_style", "explanation_style"),
                ("retrieval_emphasis", "retrieval_emphasis"),
            ):
                value = strategy.get(source_key)
                if value is not None and target_key not in state:
                    state[target_key] = value
        return state

    def _extract_constraints(self, pc: ProfileContext) -> list[dict[str, Any]]:
        """Known behavioral or system-imposed constraints."""
        constraints = []
        for pattern in pc.cognitive_summary.active_patterns:
            if pattern.confidence >= 0.7:
                constraints.append({
                    "id": f"cognitive:{pattern.pattern_name}",
                    "label": pattern.pattern_name,
                    "type": "behavioral",
                    "origin": "cognitive_summary",
                    "policy_signals": pattern.policy_signals
                })
        return constraints

    def _extract_bottlenecks(self, pc: ProfileContext) -> list[dict[str, Any]]:
        """Active obstacles blocking progress."""
        bottlenecks = []
        # Weak spots are primary knowledge bottlenecks
        for spot in pc.knowledge_summary.weak_spots:
            bottlenecks.append({
                "id": f"knowledge:{spot.node_id}",
                "label": spot.node_name,
                "type": "knowledge_gap",
                "mastery": spot.mastery,
                "last_attempt": spot.last_attempt_at.isoformat() if spot.last_attempt_at else None
            })
        
        # High-risk cognitive patterns
        for signal in pc.cognitive_summary.risk_signals:
            bottlenecks.append({
                "id": f"risk:{signal}",
                "label": signal,
                "type": "behavioral_risk"
            })
            
        return bottlenecks

    def _build_confidence_map(self, pc: ProfileContext) -> dict[str, float]:
        conf = {}
        for pattern in pc.cognitive_summary.active_patterns:
            conf[f"cognitive:{pattern.pattern_name}"] = pattern.confidence
        return conf

    def _build_freshness_map(self, pc: ProfileContext) -> dict[str, str]:
        # Currently we don't have explicit timestamps for many signals,
        # but we can tag sources.
        return {
            "preferences": "high",  # Stored explicitly
            "knowledge": "high" if pc.knowledge_summary.recent_mastery_changes else "medium",
            "cognitive": "medium"
        }

    def _detect_contradictions(
        self, 
        profile_context: ProfileContext,
        stable_traits: dict[str, Any],
        current_state: dict[str, Any],
        active_constraints: list[dict[str, Any]],
        turn_signals: dict[str, Any],
    ) -> list[dict[str, Any]]:
        contradictions: list[dict[str, Any]] = []

        for rule in (
            self._rule_difficulty_vs_start_friction,
            self._rule_push_vs_recovery_state,
            self._rule_self_report_mastery_vs_profile_mastery,
            self._rule_maximal_pace_vs_available_capacity,
        ):
            contradiction = rule(
                profile_context=profile_context,
                stable_traits=stable_traits,
                current_state=current_state,
                active_constraints=active_constraints,
                turn_signals=turn_signals,
            )
            if contradiction:
                contradictions.append(contradiction)

        return contradictions

    @staticmethod
    def _looks_like_start_friction(constraint: dict[str, Any]) -> bool:
        label = str(constraint.get("label") or "").strip().lower()
        policy_signals = [
            str(item).strip().lower()
            for item in (constraint.get("policy_signals") or [])
            if str(item).strip()
        ]
        friction_markers = (
            "perfectionism",
            "paralysis",
            "avoid",
            "回避",
            "拖延",
            "启动困难",
            "开始不了",
        )
        if any(marker in label for marker in friction_markers):
            return True
        return any("start_easy" in signal or "reduce_friction" in signal for signal in policy_signals)

    def _rule_difficulty_vs_start_friction(
        self,
        *,
        profile_context: ProfileContext,
        stable_traits: dict[str, Any],
        current_state: dict[str, Any],
        active_constraints: list[dict[str, Any]],
        turn_signals: dict[str, Any],
    ) -> dict[str, Any] | None:
        del profile_context, current_state
        difficulty = str(
            turn_signals.get("requested_difficulty")
            or stable_traits.get("difficulty")
            or ""
        ).strip().lower()
        has_paralysis = any(self._looks_like_start_friction(c) for c in active_constraints)
        if difficulty not in {"hard", "challenging", "high"} or not has_paralysis:
            return None
        return self._build_contradiction(
            contradiction_id="conflict:difficulty_vs_start_friction",
            severity="high",
            description="User is asking for higher difficulty or more challenging work while current signals show start-friction or paralysis.",
            signals=["preference.difficulty", "turn.requested_difficulty", "cognitive.active_patterns"],
            evidence=[
                self._evidence_item("difficulty_signal", f"requested difficulty={difficulty}"),
                self._evidence_item("constraint_signal", "active constraints indicate start-friction or paralysis"),
            ],
        )

    def _rule_push_vs_recovery_state(
        self,
        *,
        profile_context: ProfileContext,
        stable_traits: dict[str, Any],
        current_state: dict[str, Any],
        active_constraints: list[dict[str, Any]],
        turn_signals: dict[str, Any],
    ) -> dict[str, Any] | None:
        del profile_context, stable_traits, active_constraints
        strategy_mode = str(current_state.get("strategy_mode") or "").strip().lower()
        wants_push = bool(turn_signals.get("wants_push")) or str(
            turn_signals.get("requested_difficulty") or ""
        ).strip().lower() in {"hard", "challenging", "high"}
        if strategy_mode != "recovery" or not wants_push:
            return None
        return self._build_contradiction(
            contradiction_id="conflict:push_vs_recovery_state",
            severity="medium",
            description="User is asking for a stronger push while the current session mode is explicitly recovery-oriented.",
            signals=["strategy.session_mode", "turn.push_request"],
            evidence=[
                self._evidence_item("strategy_mode", f"session_mode={strategy_mode}"),
                self._evidence_item("turn_signal", "turn asks for stronger push or harder pacing"),
            ],
        )

    def _rule_self_report_mastery_vs_profile_mastery(
        self,
        *,
        profile_context: ProfileContext,
        stable_traits: dict[str, Any],
        current_state: dict[str, Any],
        active_constraints: list[dict[str, Any]],
        turn_signals: dict[str, Any],
    ) -> dict[str, Any] | None:
        del stable_traits, current_state, active_constraints
        if not bool(turn_signals.get("self_report_high_mastery")):
            return None
        overall_mastery = float(profile_context.knowledge_summary.overall_mastery or 0.0)
        weak_spot = next(
            (
                spot
                for spot in profile_context.knowledge_summary.weak_spots
                if float(spot.mastery or 0.0) <= 0.5
            ),
            None,
        )
        if overall_mastery > 0.45 and weak_spot is None:
            return None
        evidence = [self._evidence_item("self_report", "turn claims baseline is already strong or not a problem")]
        evidence.append(self._evidence_item("profile_mastery", f"overall_mastery={overall_mastery:.2f}"))
        if weak_spot is not None:
            evidence.append(
                self._evidence_item("weak_spot", f"{weak_spot.node_name} mastery={float(weak_spot.mastery or 0.0):.2f}")
            )
        return self._build_contradiction(
            contradiction_id="conflict:self_report_mastery_vs_profile_mastery",
            severity="high",
            description="User says the baseline is already fine, but profile evidence still shows weak mastery or active weak spots.",
            signals=["turn.self_report_mastery", "profile.knowledge_summary"],
            evidence=evidence,
        )

    def _rule_maximal_pace_vs_available_capacity(
        self,
        *,
        profile_context: ProfileContext,
        stable_traits: dict[str, Any],
        current_state: dict[str, Any],
        active_constraints: list[dict[str, Any]],
        turn_signals: dict[str, Any],
    ) -> dict[str, Any] | None:
        del profile_context, active_constraints
        aggressive_pace = bool(turn_signals.get("aggressive_pace"))
        low_capacity = bool(turn_signals.get("low_capacity_language")) or str(
            current_state.get("strategy_mode") or ""
        ).strip().lower() == "recovery"
        has_known_capacity = any(
            stable_traits.get(key) is not None
            for key in ("available_hours", "daily_cap", "focus_time", "study_window", "weekly_hours")
        )
        if not aggressive_pace or not low_capacity:
            return None
        severity = "medium" if has_known_capacity else "high"
        evidence = [self._evidence_item("pace_request", "turn asks for urgent or maximal pacing")]
        if str(current_state.get("strategy_mode") or "").strip():
            evidence.append(
                self._evidence_item("strategy_mode", f"session_mode={current_state.get('strategy_mode')}")
            )
        if turn_signals.get("low_capacity_language"):
            evidence.append(self._evidence_item("capacity_signal", "turn language indicates overload or low capacity"))
        return self._build_contradiction(
            contradiction_id="conflict:maximal_pace_vs_available_capacity",
            severity=severity,
            description="User is asking for a very aggressive pace while current signals indicate limited capacity or overload.",
            signals=["turn.aggressive_pace", "strategy.session_mode", "turn.capacity_language"],
            evidence=evidence,
        )

    @staticmethod
    def _evidence_item(source: str, detail: str) -> dict[str, str]:
        return {
            "source": str(source).strip(),
            "detail": str(detail).strip(),
        }

    @staticmethod
    def _build_contradiction(
        *,
        contradiction_id: str,
        severity: str,
        description: str,
        signals: list[str],
        evidence: list[dict[str, str]],
    ) -> dict[str, Any]:
        return {
            "id": contradiction_id,
            "severity": severity,
            "description": description,
            "signals": list(signals),
            "evidence": [item for item in evidence if item.get("detail")],
        }
