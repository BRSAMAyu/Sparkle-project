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
            active_constraints=active_constraints
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
        active_constraints: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        contradictions = []
        
        # Case B: Difficulty preference vs Perfectionism Paralysis
        difficulty = str(stable_traits.get("difficulty") or "").strip().lower()
        has_paralysis = any(self._looks_like_start_friction(c) for c in active_constraints)
        
        if difficulty == "hard" and has_paralysis:
            contradictions.append({
                "id": "conflict:difficulty_vs_paralysis",
                "severity": "high",
                "description": "User requests high difficulty (hard) but shows perfectionism paralysis.",
                "signals": ["preference.difficulty", "cognitive.active_patterns"]
            })
            
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
