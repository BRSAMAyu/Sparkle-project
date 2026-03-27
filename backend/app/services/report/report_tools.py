from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cognitive import BehaviorPattern
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.services.insight_copy import present_pattern_entry


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
        rows = [{"node_name": name, "mastery_score": float(score or 0.0)} for name, score in result.all()]
        if rows:
            return rows

        fallback_rows = await self._derive_mastery_from_error_records(user_id=user_id, limit=limit)
        if fallback_rows:
            return fallback_rows

        return await self._derive_mastery_from_tasks_and_plans(user_id=user_id, limit=limit)

    async def query_error_patterns(self, user_id: UUID, limit: int = 5) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(
                BehaviorPattern.pattern_name,
                BehaviorPattern.confidence_score,
                BehaviorPattern.description,
                BehaviorPattern.solution_text,
            )
            .where(BehaviorPattern.user_id == user_id)
            .order_by(desc(BehaviorPattern.confidence_score))
            .limit(limit)
        )
        return [
            present_pattern_entry(
                name=name,
                confidence=float(score or 0.0),
                description=description,
                solution_text=solution_text,
            )
            for name, score, description, solution_text in result.all()
        ]

    async def query_study_timeline(self, user_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(StudyRecord, KnowledgeNode.name)
            .join(KnowledgeNode, KnowledgeNode.id == StudyRecord.node_id)
            .where(StudyRecord.user_id == user_id)
            .order_by(desc(StudyRecord.created_at))
            .limit(limit)
        )
        rows = [
            {
                "node_name": node_name,
                "study_minutes": int(record.study_minutes or 0),
                "mastery_delta": float(record.mastery_delta or 0.0),
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
            for record, node_name in result.all()
        ]
        if rows:
            return rows
        return await self._derive_timeline_from_tasks(user_id=user_id, limit=limit)

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

    async def _derive_mastery_from_error_records(self, *, user_id: UUID, limit: int) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(
                ErrorRecord.chapter,
                ErrorRecord.suggested_concepts,
                ErrorRecord.linked_knowledge_node_ids,
                ErrorRecord.latest_analysis,
                ErrorRecord.mastery_level,
            )
            .where(ErrorRecord.user_id == user_id, ErrorRecord.is_deleted.is_(False))
            .order_by(desc(ErrorRecord.updated_at), desc(ErrorRecord.created_at))
            .limit(max(limit * 3, 6))
        )
        rows = result.all()
        linked_ids = {
            str(node_id)
            for _, _, linked_node_ids, _, _ in rows
            for node_id in list(linked_node_ids or [])
            if str(node_id).strip()
        }

        node_names_by_id: dict[str, str] = {}
        if linked_ids:
            node_rows = await self.db.execute(
                select(KnowledgeNode.id, KnowledgeNode.name).where(
                    KnowledgeNode.id.in_([UUID(node_id) for node_id in linked_ids])
                )
            )
            node_names_by_id = {str(node_id): str(name) for node_id, name in node_rows.all() if str(name).strip()}

        synthesized: dict[str, float] = {}
        for chapter, suggested_concepts, linked_node_ids, latest_analysis, mastery_level in rows:
            base_score = float(mastery_level or 0.0) * 100.0
            score = max(18.0, min(base_score if base_score > 0 else 38.0, 58.0))
            candidate_names: list[str] = []
            if str(chapter or "").strip():
                candidate_names.append(str(chapter).strip())
            for concept in list(suggested_concepts or []):
                if str(concept).strip():
                    candidate_names.append(str(concept).strip())
            if isinstance(latest_analysis, dict):
                for item in list(latest_analysis.get("recommended_knowledge") or []):
                    if str(item).strip():
                        candidate_names.append(str(item).strip())
            for node_id in list(linked_node_ids or []):
                node_name = node_names_by_id.get(str(node_id))
                if node_name:
                    candidate_names.append(node_name)

            for name in candidate_names:
                synthesized[name] = min(score, synthesized.get(name, score))

        return [
            {"node_name": name, "mastery_score": score}
            for name, score in sorted(synthesized.items(), key=lambda item: item[1])[:limit]
        ]

    async def _derive_mastery_from_tasks_and_plans(self, *, user_id: UUID, limit: int) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(Task.title, Task.status, KnowledgeNode.name)
            .outerjoin(KnowledgeNode, KnowledgeNode.id == Task.knowledge_node_id)
            .where(Task.user_id == user_id)
            .order_by(desc(Task.priority), desc(Task.updated_at))
            .limit(max(limit * 2, 6))
        )
        synthesized: dict[str, float] = {}
        for task_title, status, node_name in result.all():
            label = str(node_name or task_title or "").strip()
            if not label:
                continue
            score = 72.0 if status == TaskStatus.COMPLETED else (58.0 if status == TaskStatus.IN_PROGRESS else 48.0)
            synthesized[label] = min(score, synthesized.get(label, score))
        if synthesized:
            return [
                {"node_name": name, "mastery_score": score}
                for name, score in sorted(synthesized.items(), key=lambda item: item[1])[:limit]
            ]

        plan_rows = await self.db.execute(
            select(Plan.subject, Plan.name, Plan.progress)
            .where(Plan.user_id == user_id, Plan.is_active.is_(True))
            .order_by(desc(Plan.updated_at))
            .limit(limit)
        )
        return [
            {
                "node_name": str(subject or name or "").strip(),
                "mastery_score": max(35.0, min(float(progress or 0.0) * 100.0, 68.0)),
            }
            for subject, name, progress in plan_rows.all()
            if str(subject or name or "").strip()
        ][:limit]

    async def _derive_timeline_from_tasks(self, *, user_id: UUID, limit: int) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(Task.title, Task.actual_minutes, Task.estimated_minutes, Task.completed_at, KnowledgeNode.name)
            .outerjoin(KnowledgeNode, KnowledgeNode.id == Task.knowledge_node_id)
            .where(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.is_not(None),
            )
            .order_by(desc(Task.completed_at))
            .limit(limit)
        )
        return [
            {
                "node_name": str(node_name or title or "").strip(),
                "study_minutes": int(actual_minutes or estimated_minutes or 25),
                "mastery_delta": 6.0,
                "created_at": completed_at.isoformat() if completed_at else None,
            }
            for title, actual_minutes, estimated_minutes, completed_at, node_name in result.all()
            if str(node_name or title or "").strip()
        ]
