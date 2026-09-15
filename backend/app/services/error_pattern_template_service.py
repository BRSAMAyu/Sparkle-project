"""Convert repeated ErrorBook patterns into actionable repair task templates."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode
from app.models.task import Task, TaskType
from app.schemas.error_book import RemediablePattern, StructuredRemediationStep, TaskTemplate
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


ERROR_TYPE_LABELS = {
    "concept_confusion": "概念边界",
    "knowledge_gap": "知识缺口",
    "method_wrong": "解法选择",
    "logic_error": "推理链路",
    "calculation_error": "计算过程",
    "reading_careless": "审题细节",
    "memory_lapse": "记忆提取",
    "time_pressure": "限时策略",
    "other": "错因模式",
}


class ErrorPatternTemplateService:
    """Find remediable mistake clusters and turn them into task templates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def identify_remediable_patterns(
        self,
        user_id: UUID,
        *,
        lookback_days: int = 14,
        min_confidence: float = 0.6,
        limit: int = 10,
    ) -> list[RemediablePattern]:
        """Scan recent ErrorBook records and return high-confidence repair patterns."""

        now = _utcnow()
        cutoff = now - timedelta(days=max(1, lookback_days))
        result = await self.db.execute(
            select(ErrorRecord)
            .where(
                and_(
                    ErrorRecord.user_id == user_id,
                    ErrorRecord.is_deleted.is_(False),
                    ErrorRecord.created_at >= cutoff,
                )
            )
            .order_by(ErrorRecord.created_at.desc())
            .limit(200)
        )
        records = list(result.scalars().all())
        if not records:
            return []

        node_names = await self._load_node_names(records)
        patterns = self._build_patterns(user_id=user_id, records=records, node_names=node_names, now=now)
        patterns = [pattern for pattern in patterns if pattern.confidence >= min_confidence]
        patterns.sort(key=lambda item: (item.confidence, item.error_count, item.last_seen_at), reverse=True)
        return patterns[: max(1, limit)]

    def generate_task_template(self, pattern: RemediablePattern) -> TaskTemplate:
        """Generate an ExecutablePlan v5.0-compatible task template preview."""

        focus = pattern.knowledge_node_name or pattern.chapter or self._error_type_label(pattern.error_type)
        error_label = self._error_type_label(pattern.error_type)
        title = f"补救练习：{focus} · {error_label}"
        objective = (
            f"针对近 14 天出现 {pattern.error_count} 次的「{error_label}」模式，" f"用一组小练习修复 {focus} 的薄弱点。"
        )
        minimum_output = f"完成 1 张错因对照卡，并独立做对 1 道 {focus} 同类题。"
        success_criteria = [
            f"能说清 {focus} 中「{error_label}」的触发条件。",
            "能把代表错题的错误步骤改写为正确步骤。",
            "至少完成 1 道同类题并写下验算或自检依据。",
        ]
        structured_steps = self._structured_steps(pattern=pattern, focus=focus, error_label=error_label)
        guide_json = {
            "type": "error_remediation_template",
            "pattern_id": pattern.id,
            "why_this_task": objective,
            "materials_protocol": [
                "打开本模式关联的代表错题。",
                "准备草稿纸或可编辑笔记用于写错因对照卡。",
            ],
            "structured_steps": [step.model_dump() for step in structured_steps],
            "steps": [step.instruction for step in structured_steps],
            "stuck_protocol": "如果 5 分钟内无法解释错因，先只写出题干限制词和第一步判断依据。",
            "success_criteria": success_criteria,
            "minimum_output": minimum_output,
            "updates_after_completion": [
                "更新错题复习表现。",
                "把仍然模糊的知识点回流到 Knowledge Galaxy。",
            ],
            "fallback_if_failed": "降级为复述代表错题的正确解法，并标记明天复盘。",
            "source": "error_book_remediable_pattern",
            "source_error_ids": [str(error_id) for error_id in pattern.error_ids],
        }
        task_payload: dict[str, Any] = {
            "title": title,
            "type": TaskType.ERROR_FIX.value,
            "tags": ["error_book", pattern.error_type, pattern.subject_code or "unknown"],
            "estimated_minutes": pattern.suggested_duration_minutes,
            "difficulty": self._difficulty_for_pattern(pattern),
            "energy_cost": 2,
            "guide_content": objective,
            "guide_json": guide_json,
            "success_criteria": "\n".join(success_criteria),
            "knowledge_node_id": str(pattern.knowledge_node_id) if pattern.knowledge_node_id else None,
            "priority": min(100, 40 + pattern.error_count * 8),
        }
        return TaskTemplate(
            pattern_id=pattern.id,
            title=title,
            objective=objective,
            estimated_minutes=pattern.suggested_duration_minutes,
            difficulty=self._difficulty_for_pattern(pattern),
            knowledge_node_id=pattern.knowledge_node_id,
            error_type=pattern.error_type,
            success_criteria=success_criteria,
            minimum_output=minimum_output,
            structured_steps=structured_steps,
            guide_json=guide_json,
            task_payload=task_payload,
        )

    async def accept_template(self, user_id: UUID, pattern_id: str) -> Task:
        """Instantiate a previewed remedial template as a real pending task."""

        patterns = await self.identify_remediable_patterns(user_id, min_confidence=0.0, limit=50)
        pattern = next((item for item in patterns if item.id == pattern_id), None)
        if pattern is None:
            raise ValueError("Remediable pattern not found or no longer active")

        template = self.generate_task_template(pattern)
        payload = dict(template.task_payload)
        task_create = TaskCreate(**payload)
        return await TaskService.create(self.db, task_create, user_id)

    async def _load_node_names(self, records: list[ErrorRecord]) -> dict[UUID, str]:
        node_ids = {node_id for node_id in (self._primary_node_id(record) for record in records) if node_id is not None}
        if not node_ids:
            return {}

        result = await self.db.execute(select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids)))
        nodes = result.scalars().all()
        return {node.id: node.name for node in nodes if getattr(node, "id", None) is not None}

    def _build_patterns(
        self,
        *,
        user_id: UUID,
        records: list[ErrorRecord],
        node_names: dict[UUID, str],
        now: datetime,
    ) -> list[RemediablePattern]:
        grouped: dict[tuple[str, str], list[ErrorRecord]] = defaultdict(list)
        for record in records:
            error_type = self._analysis_value(record, "error_type") or "other"
            node_id = self._primary_node_id(record)
            node_key = str(node_id) if node_id else f"unlinked:{record.subject_code}:{record.chapter or ''}"
            grouped[(node_key, error_type)].append(record)

        patterns: list[RemediablePattern] = []
        for (node_key, error_type), items in grouped.items():
            if len(items) < 2:
                continue
            items.sort(key=lambda item: item.created_at or now, reverse=True)
            representative = items[0]
            node_id = self._primary_node_id(representative)
            avg_mastery = sum(float(item.mastery_level or 0.0) for item in items) / len(items)
            avg_analysis_confidence = sum(self._analysis_confidence(item) for item in items) / len(items)
            last_seen_at = max((item.created_at or now for item in items), default=now)
            confidence = self._pattern_confidence(
                error_count=len(items),
                average_mastery=avg_mastery,
                average_analysis_confidence=avg_analysis_confidence,
                last_seen_at=last_seen_at,
                now=now,
            )
            pattern_id = self._pattern_id(user_id=user_id, node_key=node_key, error_type=error_type)
            patterns.append(
                RemediablePattern(
                    id=pattern_id,
                    knowledge_node_id=node_id,
                    knowledge_node_name=node_names.get(node_id) if node_id else None,
                    error_type=error_type,
                    error_type_label=self._error_type_label(error_type),
                    subject_code=representative.subject_code,
                    chapter=representative.chapter,
                    error_count=len(items),
                    confidence=confidence,
                    average_mastery=round(max(0.0, min(avg_mastery, 1.0)), 3),
                    suggested_duration_minutes=20 + min(25, len(items) * 4),
                    root_cause_summary=self._root_cause_summary(items),
                    representative_error_id=representative.id,
                    error_ids=[item.id for item in items],
                    last_seen_at=last_seen_at,
                )
            )
        return patterns

    @staticmethod
    def _primary_node_id(record: ErrorRecord) -> UUID | None:
        value = getattr(record, "affected_node_id", None)
        if isinstance(value, UUID):
            return value
        if value:
            try:
                return UUID(str(value))
            except (TypeError, ValueError):
                pass

        linked_ids = getattr(record, "linked_knowledge_node_ids", None) or []
        if linked_ids:
            candidate = linked_ids[0]
            if isinstance(candidate, UUID):
                return candidate
            try:
                return UUID(str(candidate))
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _analysis_value(record: ErrorRecord, key: str) -> str | None:
        analysis = getattr(record, "latest_analysis", None)
        if not isinstance(analysis, dict):
            return None
        value = analysis.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _analysis_confidence(record: ErrorRecord) -> float:
        analysis = getattr(record, "latest_analysis", None)
        if not isinstance(analysis, dict):
            return 0.6
        raw = analysis.get("confidence", analysis.get("confidence_score", 0.6))
        try:
            return max(0.0, min(float(raw), 1.0))
        except (TypeError, ValueError):
            return 0.6

    @staticmethod
    def _pattern_confidence(
        *,
        error_count: int,
        average_mastery: float,
        average_analysis_confidence: float,
        last_seen_at: datetime,
        now: datetime,
    ) -> float:
        age_days = max((now - last_seen_at).total_seconds() / 86400.0, 0.0)
        recency = max(0.0, 1.0 - min(age_days, 14.0) / 14.0)
        confidence = (
            0.22
            + min(error_count, 5) * 0.11
            + max(0.0, 1.0 - average_mastery) * 0.22
            + average_analysis_confidence * 0.18
            + recency * 0.05
        )
        return round(max(0.0, min(confidence, 0.99)), 3)

    @staticmethod
    def _pattern_id(*, user_id: UUID, node_key: str, error_type: str) -> str:
        raw = f"{user_id}:{node_key}:{error_type}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _error_type_label(error_type: str | None) -> str:
        return ERROR_TYPE_LABELS.get(str(error_type or ""), ERROR_TYPE_LABELS["other"])

    @staticmethod
    def _difficulty_for_pattern(pattern: RemediablePattern) -> int:
        if pattern.error_count >= 5 or pattern.average_mastery < 0.35:
            return 4
        if pattern.error_count >= 3 or pattern.average_mastery < 0.55:
            return 3
        return 2

    def _structured_steps(
        self,
        *,
        pattern: RemediablePattern,
        focus: str,
        error_label: str,
    ) -> list[StructuredRemediationStep]:
        middle_instruction = self._middle_step_instruction(pattern.error_type, focus)
        return [
            StructuredRemediationStep(
                order=1,
                title="定位错因",
                instruction=f"选 1 道代表错题，标出发生「{error_label}」的具体一步。",
                duration_minutes=5,
                checkpoint="能指出错误开始的位置。",
            ),
            StructuredRemediationStep(
                order=2,
                title="重建规则",
                instruction=middle_instruction,
                duration_minutes=max(8, pattern.suggested_duration_minutes // 3),
                checkpoint=f"能用自己的话讲清 {focus} 的判断依据。",
            ),
            StructuredRemediationStep(
                order=3,
                title="同类练习",
                instruction=f"完成 1-2 道 {focus} 同类题，做完后写一句自检依据。",
                duration_minutes=max(10, pattern.suggested_duration_minutes // 2),
                checkpoint="至少 1 道同类题独立正确。",
            ),
            StructuredRemediationStep(
                order=4,
                title="沉淀反例",
                instruction="把本次错因写成一条“下次看到什么就先检查什么”的提醒。",
                duration_minutes=4,
                checkpoint="产出一条可复用的错因提醒。",
            ),
        ]

    @staticmethod
    def _middle_step_instruction(error_type: str, focus: str) -> str:
        if error_type in {"concept_confusion", "knowledge_gap"}:
            return f"为 {focus} 写 2 个正例和 1 个反例，比较边界条件。"
        if error_type in {"calculation_error", "method_wrong"}:
            return f"把 {focus} 的解题过程拆成公式、代入、单位、验算四栏。"
        if error_type in {"reading_careless", "time_pressure"}:
            return f"重读题干并圈出 {focus} 的限制词，再设计一个 30 秒检查点。"
        return f"把 {focus} 的正确解法拆成三步，并说明每一步为什么成立。"

    @staticmethod
    def _root_cause_summary(items: list[ErrorRecord]) -> str | None:
        causes: list[str] = []
        for item in items:
            cause = ErrorPatternTemplateService._analysis_value(item, "root_cause")
            if cause and cause not in causes:
                causes.append(cause)
        if not causes:
            return None
        return "；".join(causes[:3])[:240]


async def identify_remediable_patterns(user_id: UUID, db: AsyncSession) -> list[RemediablePattern]:
    """Functional wrapper kept for task-level integration points."""

    return await ErrorPatternTemplateService(db).identify_remediable_patterns(user_id)


async def generate_task_template(pattern: RemediablePattern, db: AsyncSession) -> TaskTemplate:
    """Functional wrapper matching the KG-005 service contract."""

    return ErrorPatternTemplateService(db).generate_task_template(pattern)


async def accept_template(user_id: UUID, pattern_id: str, db: AsyncSession) -> Task:
    """Functional wrapper matching the KG-005 service contract."""

    return await ErrorPatternTemplateService(db).accept_template(user_id, pattern_id)
