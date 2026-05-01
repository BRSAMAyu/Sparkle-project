"""Galaxy execution consumer for OpenClaw result -> knowledge graph sync."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.adapters.openclaw.result_parser import ResultParser
from app.core.event_bus import EventBus
from app.core.event_types import EXECUTION_RESULT_INGESTED
from app.db.session import AsyncSessionLocal
from app.models.execution_intent import ExecutionIntent, ExecutorType
from app.models.execution_record import ExecutionRecord
from app.models.task import Task
from app.models.task_resources import TaskKnowledgeLink
from app.services.expansion_service import ExpansionService
from app.services.galaxy.graph_structure_service import GraphStructureEvolutionService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class GalaxyExecutionConsumer:
    """Promote successful delegated executions into user-owned knowledge nodes."""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "galaxy_execution_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self._parser = ResultParser()

    async def start(self):
        await self.event_bus.connect()
        self._running = True
        logger.info("GalaxyExecutionConsumer started, listening on {}", self.STREAM_NAME)

        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"galaxy-exec-{_utcnow().timestamp()}",
                    callback=self.handle_event,
                )
                break
            except Exception as exc:
                logger.error("GalaxyExecutionConsumer error: {}", exc)
                await asyncio.sleep(1)

    async def handle_event(self, event: dict):
        if str(event.get("event_type") or "").strip() != EXECUTION_RESULT_INGESTED:
            return
        if not bool(event.get("success")):
            return

        try:
            await self._handle_execution_result(event)
        except Exception as exc:
            logger.error("Failed to process execution.result_ingested for galaxy sync: {}", exc)

    async def _handle_execution_result(self, event: dict) -> None:
        intent_id = self._parse_uuid(event.get("execution_intent_id"))
        record_id = self._parse_uuid(event.get("execution_record_id"))
        user_id = self._parse_uuid(event.get("user_id"))
        if intent_id is None or record_id is None or user_id is None:
            return

        async with AsyncSessionLocal() as db:
            intent = await db.get(ExecutionIntent, intent_id)
            record = await db.get(ExecutionRecord, record_id)
            if intent is None or record is None:
                return
            if intent.executor != ExecutorType.OPENCLAW:
                return

            task = await db.get(Task, intent.task_id) if intent.task_id else None
            if task is not None and task.knowledge_node_id and not self._is_chat_control_intent(intent):
                return
            if task is not None and not self._is_chat_control_intent(intent):
                existing_link = await db.execute(
                    select(TaskKnowledgeLink).where(TaskKnowledgeLink.task_id == task.id).limit(1)
                )
                if existing_link.scalar_one_or_none() is not None:
                    return

            summary = self._build_summary(intent=intent, record=record)
            if not summary:
                return

            expansion = ExpansionService(db)
            node, _ = await expansion.upsert_node_from_candidate(
                user_id=user_id,
                candidate={
                    "name": self._build_node_title(intent.goal),
                    "description": summary,
                    "importance_level": 2 if self._is_chat_control_intent(intent) else 3,
                    "keywords": self._build_keywords(intent),
                    "relation_to_trigger": "derived_from_execution",
                    "relation_strength": 0.62,
                },
                source_type="openclaw_execution",
                generate_embedding=False,
                unlock_for_user=True,
                commit=False,
            )

            if task is not None and task.knowledge_node_id is None:
                task.knowledge_node_id = node.id
                db.add(task)

            if task is not None:
                link_result = await db.execute(
                    select(TaskKnowledgeLink).where(
                        TaskKnowledgeLink.task_id == task.id,
                        TaskKnowledgeLink.knowledge_node_id == node.id,
                    )
                )
                if link_result.scalar_one_or_none() is None:
                    db.add(
                        TaskKnowledgeLink(
                            task_id=task.id,
                            knowledge_node_id=node.id,
                            relation_type="derived_from_execution",
                            strength=0.72,
                            notes="Auto-linked from delegated OpenClaw execution",
                            is_primary=bool(task.knowledge_node_id == node.id),
                        )
                    )

            await db.commit()

            minutes = max(1, int((record.duration_ms or 0) / 60000))
            await GraphStructureEvolutionService(db).record_engagement(
                user_id=user_id,
                node_id=node.id,
                minutes=minutes,
            )
            logger.info(
                "Promoted delegated execution {} into knowledge node {} for user {}",
                intent.id,
                node.id,
                user_id,
            )

    @staticmethod
    def _parse_uuid(value: object) -> UUID | None:
        try:
            return UUID(str(value))
        except Exception:
            return None

    @staticmethod
    def _is_chat_control_intent(intent: ExecutionIntent) -> bool:
        return bool((intent.policy or {}).get("chat_control"))

    def _build_summary(self, *, intent: ExecutionIntent, record: ExecutionRecord) -> str:
        parsed_output = record.parsed_output if isinstance(record.parsed_output, dict) else {}
        structured_candidates = (
            parsed_output.get("summary"),
            parsed_output.get("result_summary"),
            parsed_output.get("analysis"),
            parsed_output.get("answer"),
            parsed_output.get("output_summary"),
        )
        for candidate in structured_candidates:
            text = str(candidate or "").strip()
            if text:
                return text[:800]

        parsed = self._parser.parse(record.raw_response or {})
        output = str(parsed.get("output") or "").strip()
        if output:
            return output[:800]

        return str(intent.goal or "").strip()[:200]

    @staticmethod
    def _build_node_title(goal: str) -> str:
        normalized = " ".join(str(goal or "").strip().split())
        if not normalized:
            return "OpenClaw 执行沉淀"
        return f"OpenClaw 执行沉淀：{normalized[:48]}"

    @staticmethod
    def _build_keywords(intent: ExecutionIntent) -> list[str]:
        keywords = ["openclaw", "delegated_execution", "execution_note"]
        if intent.target_env:
            keywords.append(f"env:{intent.target_env.value}")
        if intent.execution_mode:
            keywords.append(f"mode:{intent.execution_mode.value}")
        if GalaxyExecutionConsumer._is_chat_control_intent(intent):
            keywords.append("chat_control")
        return keywords

    def stop(self):
        self._running = False
