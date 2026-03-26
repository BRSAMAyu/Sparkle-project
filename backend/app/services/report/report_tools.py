from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cognitive import BehaviorPattern
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus


class LearningReportTools:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def query_mastery_scores(self, user_id: UUID, limit: int = 8) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(KnowledgeNode.name, UserNodeStatus.mastery_score)
            .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(UserNodeStatus.user_id == user_id)
            .order_by(UserNodeStatus.mastery_score.asc())
            .limit(limit)
        )
        return [{"node_name": name, "mastery_score": float(score or 0.0)} for name, score in result.all()]

    async def query_error_patterns(self, user_id: UUID, limit: int = 5) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(BehaviorPattern.pattern_name, BehaviorPattern.confidence_score)
            .where(BehaviorPattern.user_id == user_id)
            .order_by(desc(BehaviorPattern.confidence_score))
            .limit(limit)
        )
        return [{"pattern_name": name, "confidence": float(score or 0.0)} for name, score in result.all()]

    async def query_study_timeline(self, user_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(StudyRecord, KnowledgeNode.name)
            .join(KnowledgeNode, KnowledgeNode.id == StudyRecord.node_id)
            .where(StudyRecord.user_id == user_id)
            .order_by(desc(StudyRecord.created_at))
            .limit(limit)
        )
        return [
            {
                "node_name": node_name,
                "study_minutes": int(record.study_minutes or 0),
                "mastery_delta": float(record.mastery_delta or 0.0),
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
            for record, node_name in result.all()
        ]

    async def interview_learner(self, user_id: UUID) -> dict[str, Any]:
        mastery = await self.query_mastery_scores(user_id, limit=3)
        patterns = await self.query_error_patterns(user_id, limit=3)
        timeline = await self.query_study_timeline(user_id, limit=3)

        weak_names = [item["node_name"] for item in mastery if item.get("node_name")]
        pattern_names = [item["pattern_name"] for item in patterns if item.get("pattern_name")]
        improving = [item["node_name"] for item in timeline if float(item.get("mastery_delta") or 0.0) > 0]

        learner_voice_parts: list[str] = []
        if weak_names:
            learner_voice_parts.append(f"你最近最需要先补的是 {weak_names[0]} 这一类前置薄弱点。")
        if improving:
            learner_voice_parts.append(f"{improving[0]} 已经开始出现正向提升，适合继续加深。")
        if pattern_names:
            learner_voice_parts.append(f"当前最值得留意的学习模式是 {pattern_names[0]}。")
        if not learner_voice_parts:
            learner_voice_parts.append("你当前学习数据还不够密集，建议先连续记录 2-3 次学习行为再看趋势。")

        return {
            "learner_voice": " ".join(learner_voice_parts),
            "top_weak_spots": mastery,
            "dominant_patterns": patterns,
            "recent_positive_shifts": improving,
        }
