"""
Core: execution
Phase: adapt
Stage: T3.1.5 L4 Async Deep Learning — background analysis producing policy candidates.

L4 is the background system. It does NOT block user dialogue.
It runs asynchronously (Celery/GLM Batch) and produces PolicyUpdateCandidate
objects that must go through shadow → simulation → guardrail before live.

L4 responsibilities:
- Cross-day behavior analysis
- Achievement outcome feedback
- Recall effectiveness evaluation
- Strategy effectiveness assessment
- Mistake clustering
- Skill extraction candidates

Output: PolicyUpdateCandidate — never directly modifies live state.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.signals.types import _uid


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ── L4 analysis types ───────────────────────────────────────────────

L4_ANALYSIS_TYPES: dict[str, dict[str, Any]] = {
    "behavior_trend": {
        "description": "Cross-day behavior pattern analysis",
        "min_episodes": 5,
        "default_domain": "behavior",
    },
    "achievement_feedback": {
        "description": "Achievement outcome → strategy feedback",
        "min_episodes": 3,
        "default_domain": "achievement",
    },
    "recall_effectiveness": {
        "description": "Recall scheduling effectiveness evaluation",
        "min_episodes": 3,
        "default_domain": "recall",
    },
    "strategy_effectiveness": {
        "description": "Strategy A/B outcome comparison",
        "min_episodes": 5,
        "default_domain": "strategy",
    },
    "mistake_cluster": {
        "description": "Error pattern clustering",
        "min_episodes": 3,
        "default_domain": "knowledge",
    },
    "skill_extraction": {
        "description": "Skill candidate extraction from outcomes",
        "min_episodes": 3,
        "default_domain": "skill",
    },
}

# Redis keys
_CANDIDATE_KEY = "aurora:l4_candidate:{candidate_id}"
_USER_CANDIDATES_KEY = "aurora:l4_candidates:{user_id}"
_CANDIDATE_TTL = 7 * 24 * 3600  # 7 days


# ── L4Candidate ─────────────────────────────────────────────────────

class L4PolicyCandidate:
    """A candidate produced by L4 async analysis.

    Follows PolicyUpdateCandidate pattern: shadow-only, must be promoted
    through guardrails before affecting live state.
    """

    def __init__(
        self,
        *,
        candidate_id: str = "",
        user_id: str = "",
        analysis_type: str = "",
        current_policy: str = "",
        proposed_policy: str = "",
        domain: str = "",
        evidence_summary: dict[str, Any] | None = None,
        confidence: float = 0.0,
        episode_count: int = 0,
    ):
        self.candidate_id = candidate_id or _uid("l4c")
        self.user_id = user_id
        self.analysis_type = analysis_type
        self.current_policy = current_policy
        self.proposed_policy = proposed_policy
        self.domain = domain
        self.evidence_summary = evidence_summary or {}
        self.confidence = max(0.0, min(1.0, confidence))
        self.episode_count = episode_count
        self.status = "shadow"  # shadow → simulation → promoted | rejected
        self.created_at = _utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "user_id": self.user_id,
            "analysis_type": self.analysis_type,
            "current_policy": self.current_policy,
            "proposed_policy": self.proposed_policy,
            "domain": self.domain,
            "evidence_summary": self.evidence_summary,
            "confidence": self.confidence,
            "episode_count": self.episode_count,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> L4PolicyCandidate:
        c = cls(
            candidate_id=data.get("candidate_id", ""),
            user_id=data.get("user_id", ""),
            analysis_type=data.get("analysis_type", ""),
            current_policy=data.get("current_policy", ""),
            proposed_policy=data.get("proposed_policy", ""),
            domain=data.get("domain", ""),
            evidence_summary=data.get("evidence_summary", {}),
            confidence=data.get("confidence", 0.0),
            episode_count=data.get("episode_count", 0),
        )
        c.status = data.get("status", "shadow")
        c.created_at = data.get("created_at", c.created_at)
        return c


# ── L4AsyncEngine ───────────────────────────────────────────────────

class L4AsyncEngine:
    """L4 Async Deep Learning — produces policy candidates from background analysis.

    L4 never writes to live state. All output goes through PolicyUpdateCandidate
    pattern: shadow → simulation → guardrail → (human review) → live.
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    def create_candidate(
        self,
        *,
        user_id: str,
        analysis_type: str,
        current_policy: str,
        proposed_policy: str,
        domain: str = "",
        evidence_summary: dict[str, Any] | None = None,
        confidence: float = 0.0,
        episode_count: int = 0,
    ) -> L4PolicyCandidate | None:
        """Create a policy candidate from L4 analysis.

        Validates analysis_type and enforces min_episodes before creating.
        Returns None if validation fails.
        """
        type_config = L4_ANALYSIS_TYPES.get(analysis_type)
        if not type_config:
            logger.warning("L4: unknown analysis_type={}", analysis_type)
            return None

        min_episodes = type_config["min_episodes"]
        if episode_count < min_episodes:
            logger.debug(
                "L4: insufficient episodes for {} (have {}, need {})",
                analysis_type, episode_count, min_episodes,
            )
            return None

        candidate = L4PolicyCandidate(
            user_id=user_id,
            analysis_type=analysis_type,
            current_policy=current_policy,
            proposed_policy=proposed_policy,
            domain=domain or type_config["default_domain"],
            evidence_summary=evidence_summary,
            confidence=confidence,
            episode_count=episode_count,
        )

        return candidate

    async def store_candidate(self, candidate: L4PolicyCandidate) -> bool:
        """Persist a candidate to Redis."""
        try:
            key = _CANDIDATE_KEY.format(candidate_id=candidate.candidate_id)
            await self.redis.set(key, json.dumps(candidate.to_dict()), ex=_CANDIDATE_TTL)

            user_key = _USER_CANDIDATES_KEY.format(user_id=candidate.user_id)
            await self.redis.lpush(user_key, candidate.candidate_id)
            await self.redis.ltrim(user_key, 0, 49)  # keep last 50

            logger.info(
                "L4: stored candidate={} user={} type={} status={}",
                candidate.candidate_id, candidate.user_id,
                candidate.analysis_type, candidate.status,
            )
            return True
        except Exception:
            logger.warning("L4: store_candidate failed", exc_info=True)
            return False

    async def get_candidate(self, candidate_id: str) -> L4PolicyCandidate | None:
        """Retrieve a candidate by ID."""
        try:
            raw = await self.redis.get(_CANDIDATE_KEY.format(candidate_id=candidate_id))
            if not raw:
                return None
            data = json.loads(raw)
            return L4PolicyCandidate.from_dict(data)
        except Exception:
            return None

    async def get_user_candidates(
        self,
        user_id: str,
        *,
        status: str | None = None,
        limit: int = 10,
    ) -> list[L4PolicyCandidate]:
        """Get candidates for a user, optionally filtered by status."""
        try:
            user_key = _USER_CANDIDATES_KEY.format(user_id=user_id)
            ids = await self.redis.lrange(user_key, 0, limit - 1)
            candidates = []
            for cid in ids:
                raw = await self.redis.get(_CANDIDATE_KEY.format(candidate_id=cid))
                if not raw:
                    continue
                try:
                    c = L4PolicyCandidate.from_dict(json.loads(raw))
                except (json.JSONDecodeError, TypeError):
                    continue
                if status and c.status != status:
                    continue
                candidates.append(c)
            return candidates
        except Exception:
            return []

    async def promote_candidate(
        self,
        candidate_id: str,
        *,
        promoted_by: str = "auto",
    ) -> L4PolicyCandidate | None:
        """Promote a candidate from shadow to simulation status.

        Shadow → Simulation is automatic. Simulation → Live requires human review.
        """
        candidate = await self.get_candidate(candidate_id)
        if not candidate:
            return None

        if candidate.status == "shadow":
            candidate.status = "simulation"
        elif candidate.status == "simulation":
            candidate.status = "promoted"
        else:
            return None

        try:
            key = _CANDIDATE_KEY.format(candidate_id=candidate_id)
            await self.redis.set(key, json.dumps(candidate.to_dict()), ex=_CANDIDATE_TTL)
        except Exception:
            logger.warning("L4: promote_candidate persist failed", exc_info=True)
            return None

        logger.info(
            "L4: promoted candidate={} to status={} by={}",
            candidate_id, candidate.status, promoted_by,
        )
        return candidate

    async def reject_candidate(
        self,
        candidate_id: str,
        reason: str = "",
    ) -> L4PolicyCandidate | None:
        """Reject a candidate."""
        candidate = await self.get_candidate(candidate_id)
        if not candidate:
            return None

        candidate.status = "rejected"
        try:
            key = _CANDIDATE_KEY.format(candidate_id=candidate_id)
            await self.redis.set(key, json.dumps(candidate.to_dict()), ex=_CANDIDATE_TTL)
        except Exception:
            return None

        return candidate
