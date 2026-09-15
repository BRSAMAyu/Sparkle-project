from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, MessageRole
from app.models.cognitive import BehaviorPattern
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.services.insight_copy import present_pattern_entry
from app.services.llm_fallback_utils import analysis_llm


class LearningReportTools:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def query_mastery_scores(self, user_id: UUID, limit: int = 8) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(KnowledgeNode.id, KnowledgeNode.name, UserNodeStatus.mastery_score)
            .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(UserNodeStatus.user_id == user_id)
            .order_by(UserNodeStatus.mastery_score.asc())
            .limit(limit)
        )
        raw_rows = result.all()
        related_error_counts = await self._derive_related_error_counts(
            user_id=user_id,
            node_refs=[
                {
                    "node_id": str(node_id),
                    "node_name": str(name or "").strip(),
                }
                for node_id, name, _score in raw_rows
                if str(name or "").strip()
            ],
        )
        rows = [
            {
                "node_id": str(node_id),
                "node_name": str(name or "").strip(),
                "mastery_score": float(score or 0.0),
                "related_error_count": related_error_counts.get(
                    str(node_id),
                    related_error_counts.get(str(name or "").strip(), 0),
                ),
            }
            for node_id, name, score in raw_rows
            if str(name or "").strip()
        ]
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
        ] or await self._derive_patterns_from_learning_state(user_id=user_id, limit=limit)

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
                "node_id": str(record.node_id) if getattr(record, "node_id", None) else None,
                "node_name": node_name,
                "study_minutes": int(record.study_minutes or 0),
                "mastery_delta": float(record.mastery_delta or 0.0),
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "days_since_last": (
                    max(0, (datetime.now(UTC) - record.created_at.replace(tzinfo=UTC)).days)
                    if record.created_at
                    else None
                ),
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

    async def infer_learning_state_from_chat(self, user_id: UUID, limit: int = 8) -> dict[str, Any]:
        result = await self.db.execute(
            select(ChatMessage.content, ChatMessage.created_at)
            .where(ChatMessage.user_id == user_id, ChatMessage.role == MessageRole.USER)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        rows = result.all()
        messages = [str(content).strip() for content, _ in rows if str(content).strip()]
        if not messages:
            return {}

        fallback = self._fallback_chat_inference(messages)
        payload = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON with keys topics, frictions, goal_summary, evidence. "
                        "Infer a lightweight learning-state summary from recent user chat messages."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Recent user chat messages: {messages[:6]}\n"
                        "Extract up to 3 likely learning topics, up to 2 frictions, one short goal summary, "
                        "and 1-3 short evidence snippets."
                    ),
                },
            ],
            fallback=fallback,
            temperature=0.2,
        )
        parsed = payload if isinstance(payload, dict) else fallback
        topics = self._clean_chat_inference_list(parsed.get("topics")) or fallback["topics"]
        frictions = self._clean_chat_inference_list(parsed.get("frictions")) or fallback["frictions"]
        evidence = self._clean_chat_inference_list(parsed.get("evidence")) or fallback["evidence"]
        goal_summary = str(parsed.get("goal_summary") or fallback["goal_summary"]).strip()
        return {
            "topics": topics[:3],
            "frictions": frictions[:2],
            "goal_summary": goal_summary,
            "evidence": evidence[:3],
        }

    @staticmethod
    def _clean_chat_inference_list(raw: Any) -> list[str]:
        if isinstance(raw, list):
            items = raw
        elif raw is None:
            items = []
        else:
            items = [raw]
        return [str(item).strip() for item in items if str(item).strip()]

    def _fallback_chat_inference(self, messages: list[str]) -> dict[str, Any]:
        snippets = [message[:60] for message in messages[:3]]
        joined = " ".join(messages)
        topics = self._extract_chat_topic_candidates(messages)
        frictions: list[str] = []
        if any(marker in joined for marker in ("卡", "不会", "搞不懂", "不理解", "总错")):
            frictions.append("核心概念还存在理解卡点")
        if any(marker in joined for marker in ("路径", "怎么学", "计划", "安排", "入门")):
            frictions.append("起步路径还不够清晰")
        if not frictions:
            frictions.append("还需要先把学习目标收敛成一条更清晰的起步线")
        goal_summary = topics[0] if topics else (messages[0][:24] if messages else "当前学习主题")
        return {
            "topics": topics[:3],
            "frictions": frictions[:2],
            "goal_summary": goal_summary,
            "evidence": snippets,
        }

    @staticmethod
    def _extract_chat_topic_candidates(messages: list[str]) -> list[str]:
        filler_markers = (
            "帮我",
            "请帮我",
            "我想",
            "想要",
            "一下",
            "怎么",
            "如何",
            "给我",
            "最近",
            "学习",
            "推演",
            "模拟",
            "报告",
        )
        candidates: list[str] = []
        for message in messages:
            cleaned = message
            for marker in filler_markers:
                cleaned = cleaned.replace(marker, " ")
            for token in re.findall(r"[A-Za-z0-9+#]{3,}|[\u4e00-\u9fff]{2,10}", cleaned):
                term = token.strip()
                if len(term) < 2:
                    continue
                if term not in candidates:
                    candidates.append(term)
        return candidates[:5]

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
                "node_id": None,
                "node_name": str(node_name or title or "").strip(),
                "study_minutes": int(actual_minutes or estimated_minutes or 25),
                "mastery_delta": None,
                "created_at": completed_at.isoformat() if completed_at else None,
                "days_since_last": (
                    max(0, (datetime.now(UTC) - completed_at.replace(tzinfo=UTC)).days)
                    if completed_at
                    else None
                ),
            }
            for title, actual_minutes, estimated_minutes, completed_at, node_name in result.all()
            if str(node_name or title or "").strip()
        ]

    async def _derive_related_error_counts(
        self,
        *,
        user_id: UUID,
        node_refs: list[dict[str, str]],
    ) -> dict[str, int]:
        if not node_refs:
            return {}
        rows = (
            await self.db.execute(
                select(
                    ErrorRecord.chapter,
                    ErrorRecord.suggested_concepts,
                    ErrorRecord.linked_knowledge_node_ids,
                    ErrorRecord.latest_analysis,
                )
                .where(ErrorRecord.user_id == user_id, ErrorRecord.is_deleted.is_(False))
                .order_by(desc(ErrorRecord.updated_at), desc(ErrorRecord.created_at))
                .limit(120)
            )
        ).all()
        if not rows:
            return {}
        counts: dict[str, int] = {}
        refs_by_id = {
            str(item.get("node_id") or "").strip(): str(item.get("node_name") or "").strip()
            for item in node_refs
            if str(item.get("node_id") or "").strip()
        }
        refs_by_name = {
            str(item.get("node_name") or "").strip(): str(item.get("node_id") or "").strip()
            for item in node_refs
            if str(item.get("node_name") or "").strip()
        }
        for chapter, suggested_concepts, linked_node_ids, latest_analysis in rows:
            candidate_names: set[str] = set()
            if str(chapter or "").strip():
                candidate_names.add(str(chapter).strip())
            for concept in list(suggested_concepts or []):
                if str(concept).strip():
                    candidate_names.add(str(concept).strip())
            if isinstance(latest_analysis, dict):
                for concept in list(latest_analysis.get("recommended_knowledge") or []):
                    if str(concept).strip():
                        candidate_names.add(str(concept).strip())
            matched = False
            for node_id in list(linked_node_ids or []):
                normalized_id = str(node_id).strip()
                if normalized_id and normalized_id in refs_by_id:
                    counts[normalized_id] = counts.get(normalized_id, 0) + 1
                    counts[refs_by_id[normalized_id]] = counts.get(refs_by_id[normalized_id], 0) + 1
                    matched = True
            if matched:
                continue
            lowered_candidates = {name.casefold() for name in candidate_names if name}
            for node_name, node_id in refs_by_name.items():
                if node_name and node_name.casefold() in lowered_candidates:
                    counts[node_name] = counts.get(node_name, 0) + 1
                    if node_id:
                        counts[node_id] = counts.get(node_id, 0) + 1
        return counts

    async def _derive_patterns_from_learning_state(self, *, user_id: UUID, limit: int) -> list[dict[str, Any]]:
        pending_tasks = await self.db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
            )
        )
        active_plan = (
            await self.db.execute(
                select(Plan.subject, Plan.name, Plan.progress)
                .where(Plan.user_id == user_id, Plan.is_active.is_(True))
                .order_by(desc(Plan.updated_at))
                .limit(1)
            )
        ).first()

        synthesized: list[dict[str, Any]] = []
        if int(pending_tasks or 0) >= 3:
            synthesized.append(
                {
                    "pattern_name": "起步阻力偏高",
                    "raw_pattern_name": "cold_start_inertia",
                    "confidence": 0.56,
                    "description": f"当前至少有 {int(pending_tasks or 0)} 个待推进任务，说明你更需要先收敛起步动作，而不是继续扩张目标。",
                    "solution_text": "先只保留 1 个最小可执行任务，把第一步压缩到 20-30 分钟可以完成的粒度。",
                }
            )

        if active_plan:
            subject, name, progress = active_plan
            label = str(subject or name or "当前计划").strip()
            synthesized.append(
                {
                    "pattern_name": "目标聚焦待收敛",
                    "raw_pattern_name": "focus_alignment_bootstrap",
                    "confidence": 0.51,
                    "description": f"你已经围绕 {label} 建立了方向，但目前更需要把目标转成清晰的起步路径。",
                    "solution_text": "先把目标拆成一条 3 步内能启动的路径，再决定是否继续扩张任务清单。",
                }
            )

        if not synthesized:
            synthesized.append(
                {
                    "pattern_name": "学习基线尚在建立",
                    "raw_pattern_name": "baseline_building",
                    "confidence": 0.42,
                    "description": "当前高质量学习样本还不够，系统先按启动期来给建议，会优先帮助你建立第一批稳定记录。",
                    "solution_text": "先连续完成 3 次 20-30 分钟学习，并记录每次卡住的位置，下一版报告就会明显更具体。",
                }
            )

        return synthesized[:limit]
