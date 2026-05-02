"""Strategy belief migration support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.models.strategy_belief import StrategyBeliefSnapshot


@dataclass(frozen=True)
class StrategyEvidence:
    reason: str
    weight: float = 1.0
    source: str = "counter_evidence"

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "weight": self.weight,
            "source": self.source,
        }


@dataclass(frozen=True)
class AlternativeStrategy:
    strategy_id: str
    title: str
    description: str
    confidence: float
    estimated_lift: float
    why: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "title": self.title,
            "description": self.description,
            "confidence": round(self.confidence, 3),
            "estimated_lift": round(self.estimated_lift, 3),
            "why": self.why,
        }


@dataclass(frozen=True)
class StrategySuggestionBundle:
    goal_id: str
    current_strategy_id: str
    current_strategy_title: str
    confidence: float
    counter_evidence: list[StrategyEvidence]
    alternatives: list[AlternativeStrategy]

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "current_strategy_id": self.current_strategy_id,
            "current_strategy_title": self.current_strategy_title,
            "confidence": round(self.confidence, 3),
            "counter_evidence": [item.to_dict() for item in self.counter_evidence],
            "alternatives": [item.to_dict() for item in self.alternatives],
        }


@dataclass(frozen=True)
class StrategyMigrationResult:
    goal_id: str
    previous_strategy_id: str
    new_strategy_id: str
    new_strategy_title: str
    migrated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "previous_strategy_id": self.previous_strategy_id,
            "new_strategy_id": self.new_strategy_id,
            "new_strategy_title": self.new_strategy_title,
            "migrated_at": self.migrated_at,
        }


class StrategyBeliefService:
    """Suggest and apply replacements when a goal strategy is disproven."""

    _CATALOG: dict[str, dict[str, Any]] = {
        "repair_knowledge_bottleneck": {
            "title": "Repair the blocking knowledge gap",
            "description": "Pause forward progress and practice the weakest prerequisite first.",
            "goal_types": {"academic", "exam", "skill", "general"},
            "default_confidence": 0.76,
        },
        "recover_execution_rhythm": {
            "title": "Recover execution rhythm",
            "description": "Shrink the next actions until completion momentum returns.",
            "goal_types": {"habit", "project", "skill", "general"},
            "default_confidence": 0.72,
        },
        "task_granularity_fit": {
            "title": "Resize tasks to fit the day",
            "description": "Split work into smaller units with clearer stopping points.",
            "goal_types": {"academic", "project", "habit", "skill", "general"},
            "default_confidence": 0.7,
        },
        "activate_material_retrieval": {
            "title": "Use bound learning material first",
            "description": "Anchor the next task in uploaded notes, examples, or references.",
            "goal_types": {"academic", "project", "skill"},
            "default_confidence": 0.68,
        },
        "exam_rescue_sprint": {
            "title": "Switch to minimum-pass sprint",
            "description": "Prioritize short high-yield drills and defer low-return topics.",
            "goal_types": {"academic", "exam"},
            "default_confidence": 0.74,
        },
        "sustain_momentum": {
            "title": "Sustain current momentum",
            "description": "Keep the strategy but reduce intervention intensity.",
            "goal_types": {"habit", "project", "general"},
            "default_confidence": 0.66,
        },
    }

    async def suggest_alternatives(
        self,
        user_id: UUID,
        goal_id: UUID,
        db: AsyncSession,
        limit: int = 3,
    ) -> StrategySuggestionBundle:
        goal = await self._load_goal(user_id=user_id, goal_id=goal_id, db=db)
        current = await self._current_belief(user_id=user_id, goal=goal, db=db)
        current_key = current.strategy_key if current else self._metadata_current_strategy(goal) or "recover_execution_rhythm"
        current_score = current.belief_score if current else 0.35
        counter_evidence = self._counter_evidence(current)

        user_scores = await self._user_strategy_scores(user_id=user_id, db=db)
        alternatives = self._rank_alternatives(
            current_key=current_key,
            current_score=current_score,
            goal_type=goal.goal_type or "general",
            user_scores=user_scores,
            limit=limit,
        )

        return StrategySuggestionBundle(
            goal_id=str(goal.id),
            current_strategy_id=current_key,
            current_strategy_title=self._title(current_key),
            confidence=current_score,
            counter_evidence=counter_evidence,
            alternatives=alternatives,
        )

    async def migrate_strategy(
        self,
        user_id: UUID,
        goal_id: UUID,
        new_strategy_id: str,
        db: AsyncSession,
    ) -> StrategyMigrationResult:
        goal = await self._load_goal(user_id=user_id, goal_id=goal_id, db=db)
        if new_strategy_id not in self._CATALOG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown strategy: {new_strategy_id}",
            )

        current = await self._current_belief(user_id=user_id, goal=goal, db=db)
        previous_key = current.strategy_key if current else self._metadata_current_strategy(goal) or ""
        migrated_at = datetime.now(UTC).isoformat()
        metadata = dict(goal.metadata_payload or {})
        history = list(metadata.get("strategy_migrations") or [])
        history.append(
            {
                "from_strategy_id": previous_key,
                "to_strategy_id": new_strategy_id,
                "migrated_at": migrated_at,
            }
        )
        metadata["current_strategy_id"] = new_strategy_id
        metadata["strategy_migrations"] = history
        goal.metadata_payload = metadata

        belief = await self._belief_by_key(user_id=user_id, strategy_key=new_strategy_id, db=db)
        if belief is None:
            belief = StrategyBeliefSnapshot(
                user_id=str(user_id),
                strategy_key=new_strategy_id,
                alpha=3.0,
                beta=1.0,
                evidence_count=1,
                last_updated=migrated_at,
                counter_evidence=[],
                metadata_payload={"source": "strategy_migration"},
            )
            db.add(belief)
        else:
            belief.last_updated = migrated_at
            belief.metadata_payload = {
                **dict(belief.metadata_payload or {}),
                "source": "strategy_migration",
                "goal_id": str(goal.id),
            }

        await db.flush()
        return StrategyMigrationResult(
            goal_id=str(goal.id),
            previous_strategy_id=previous_key,
            new_strategy_id=new_strategy_id,
            new_strategy_title=self._title(new_strategy_id),
            migrated_at=migrated_at,
        )

    async def _load_goal(self, *, user_id: UUID, goal_id: UUID, db: AsyncSession) -> Goal:
        result = await db.execute(
            select(Goal).where(
                Goal.id == goal_id,
                Goal.user_id == user_id,
                Goal.deleted_at.is_(None),
            )
        )
        goal = result.scalar_one_or_none()
        if goal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
        return goal

    async def _current_belief(
        self,
        *,
        user_id: UUID,
        goal: Goal,
        db: AsyncSession,
    ) -> StrategyBeliefSnapshot | None:
        metadata_key = self._metadata_current_strategy(goal)
        if metadata_key:
            return await self._belief_by_key(user_id=user_id, strategy_key=metadata_key, db=db)

        result = await db.execute(
            select(StrategyBeliefSnapshot)
            .where(
                StrategyBeliefSnapshot.user_id == str(user_id),
                StrategyBeliefSnapshot.deleted_at.is_(None),
            )
            .order_by(StrategyBeliefSnapshot.updated_at.desc())
        )
        beliefs = list(result.scalars().all())
        weak_beliefs = [
            belief
            for belief in beliefs
            if belief.belief_score < 0.4 and bool(self._counter_evidence(belief))
        ]
        if weak_beliefs:
            return sorted(weak_beliefs, key=lambda belief: belief.belief_score)[0]
        return beliefs[0] if beliefs else None

    async def _belief_by_key(
        self,
        *,
        user_id: UUID,
        strategy_key: str,
        db: AsyncSession,
    ) -> StrategyBeliefSnapshot | None:
        result = await db.execute(
            select(StrategyBeliefSnapshot).where(
                StrategyBeliefSnapshot.user_id == str(user_id),
                StrategyBeliefSnapshot.strategy_key == strategy_key,
                StrategyBeliefSnapshot.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _user_strategy_scores(self, *, user_id: UUID, db: AsyncSession) -> dict[str, float]:
        result = await db.execute(
            select(StrategyBeliefSnapshot).where(
                StrategyBeliefSnapshot.user_id == str(user_id),
                StrategyBeliefSnapshot.deleted_at.is_(None),
            )
        )
        return {belief.strategy_key: belief.belief_score for belief in result.scalars().all()}

    def _rank_alternatives(
        self,
        *,
        current_key: str,
        current_score: float,
        goal_type: str,
        user_scores: dict[str, float],
        limit: int,
    ) -> list[AlternativeStrategy]:
        candidates: list[AlternativeStrategy] = []
        normalized_goal_type = goal_type.lower()
        for strategy_id, spec in self._CATALOG.items():
            if strategy_id == current_key:
                continue
            goal_match = normalized_goal_type in spec["goal_types"] or "general" in spec["goal_types"]
            score = user_scores.get(strategy_id, spec["default_confidence"])
            if goal_match:
                score += 0.06
            why = (
                "Matches this goal type and has stronger recent evidence."
                if goal_match
                else "Useful as a fallback when the current strategy is disproven."
            )
            candidates.append(
                AlternativeStrategy(
                    strategy_id=strategy_id,
                    title=spec["title"],
                    description=spec["description"],
                    confidence=min(score, 0.96),
                    estimated_lift=max(0.0, score - current_score),
                    why=why,
                )
            )
        candidates.sort(key=lambda item: (-item.estimated_lift, -item.confidence, item.strategy_id))
        return candidates[: max(1, min(limit, 3))]

    def _counter_evidence(self, belief: StrategyBeliefSnapshot | None) -> list[StrategyEvidence]:
        if belief is None or not isinstance(belief.counter_evidence, list):
            return []
        evidence: list[StrategyEvidence] = []
        for raw in belief.counter_evidence:
            if isinstance(raw, dict):
                reason = str(raw.get("reason") or raw.get("detail") or raw.get("evidence_id") or "").strip()
                if reason:
                    evidence.append(
                        StrategyEvidence(
                            reason=reason,
                            weight=float(raw.get("weight") or 1.0),
                            source=str(raw.get("source") or "counter_evidence"),
                        )
                    )
            elif str(raw).strip():
                evidence.append(StrategyEvidence(reason=str(raw).strip()))
        return evidence

    def _metadata_current_strategy(self, goal: Goal) -> str | None:
        metadata = goal.metadata_payload if isinstance(goal.metadata_payload, dict) else {}
        strategy_id = metadata.get("current_strategy_id") or metadata.get("strategy_key")
        return str(strategy_id).strip() if strategy_id else None

    def _title(self, strategy_id: str) -> str:
        return str(self._CATALOG.get(strategy_id, {}).get("title") or strategy_id.replace("_", " ").title())


strategy_belief_service = StrategyBeliefService()
