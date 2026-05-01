from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.core.metrics import BAYESIAN_RECOMMENDATION_TOTAL, BAYESIAN_SHADOW_DIVERGENCE_TOTAL
from app.learning.persistent_bayesian_learner import PersistentBayesianLearner
from app.orchestration.schemas import RouteDecision
from app.services.aurora_stage23_kill_switch_service import AuroraStage23KillSwitchService

ROUTE_EXECUTION_TARGETS = ("direct", "langgraph", "hybrid")


@dataclass(frozen=True)
class BayesianWireResult:
    mode: str
    source_state_key: str
    fallback_target: str
    recommended_target: str | None
    applied_target: str
    divergence: bool
    scores: tuple[dict[str, float | str | int], ...]


class BayesianRoutingWireService:
    def __init__(self, redis_client=None) -> None:
        self.redis = redis_client
        self.kill_switch = AuroraStage23KillSwitchService()

    async def apply(
        self,
        *,
        user_id: str,
        route_decision: RouteDecision,
        source_state_key: str,
    ) -> tuple[RouteDecision, BayesianWireResult]:
        mode = await self.kill_switch.get_mode()
        if mode == "off":
            return route_decision, BayesianWireResult(
                mode=mode,
                source_state_key=source_state_key,
                fallback_target=route_decision.execution_mode,
                recommended_target=None,
                applied_target=route_decision.execution_mode,
                divergence=False,
                scores=(),
            )
        learner = PersistentBayesianLearner(self.redis, user_id=user_id)
        scores = tuple(await learner.rank_targets(source_state_key, list(ROUTE_EXECUTION_TARGETS)))
        fallback_target = route_decision.execution_mode
        recommended_target = self._pick_recommendation(scores=scores, fallback_target=fallback_target)

        BAYESIAN_RECOMMENDATION_TOTAL.labels(event="made", mode=mode).inc()
        divergence = recommended_target is not None and recommended_target != fallback_target
        applied_target = fallback_target

        if mode == "shadow":
            if divergence:
                BAYESIAN_SHADOW_DIVERGENCE_TOTAL.labels(mode=mode).inc()
            return route_decision, BayesianWireResult(
                mode=mode,
                source_state_key=source_state_key,
                fallback_target=fallback_target,
                recommended_target=recommended_target,
                applied_target=applied_target,
                divergence=divergence,
                scores=scores,
            )

        if mode == "live" and self._in_canary_bucket(user_id):
            if recommended_target and recommended_target != fallback_target:
                route_decision.execution_mode = recommended_target
                route_decision.reason = (
                    f"{route_decision.reason} | bayesian:{recommended_target}"
                    if route_decision.reason
                    else f"bayesian:{recommended_target}"
                )
                applied_target = recommended_target
                BAYESIAN_RECOMMENDATION_TOTAL.labels(event="accepted", mode=mode).inc()

        return route_decision, BayesianWireResult(
            mode=mode,
            source_state_key=source_state_key,
            fallback_target=fallback_target,
            recommended_target=recommended_target,
            applied_target=applied_target,
            divergence=divergence,
            scores=scores,
        )

    @staticmethod
    def _pick_recommendation(
        *,
        scores: tuple[dict[str, float | str | int], ...],
        fallback_target: str,
    ) -> str | None:
        if not scores:
            return None
        best = scores[0]
        fallback = next((item for item in scores if item["target"] == fallback_target), None)
        best_probability = float(best["probability"])
        best_observations = int(best["observations"])
        fallback_probability = float(fallback["probability"]) if fallback is not None else 0.5
        if best_observations < 3:
            return None
        if best_probability < fallback_probability + 0.05:
            return None
        return str(best["target"])

    async def current_mode(self) -> str:
        return await self.kill_switch.get_mode()

    def _in_canary_bucket(self, user_id: str) -> bool:
        percent = self.kill_switch.live_canary_percent()
        if percent >= 100:
            return True
        if percent <= 0:
            return False
        digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 100
        return bucket < percent
