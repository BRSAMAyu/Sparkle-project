"""
Phase 4 consumer that keeps the main-chain artifacts fresh.

This consumer does not invent new product logic. It simply ensures that the
approved ACTIVE_PHASE_PACK and REFLECTION_REPORT stay aligned with the actual
execution loop as task/intervention/artifact events flow through the system.
"""
from __future__ import annotations

import asyncio
import os
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.models.card_protocol import ArtifactType, InterventionRecord
from app.models.task import Task
from app.services.card_protocol.main_chain_artifact_service import MainChainArtifactService


class MainChainArtifactConsumer:
    """Refreshes Phase 4 main-chain artifacts from runtime events."""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "main_chain_artifact_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self._subscribed = False
        self.consumer_name = f"main-chain-{os.getpid()}"
        self.session_factory = AsyncSessionLocal

    async def start(self):
        await self.event_bus.connect()
        if self._running:
            return
        self._running = True
        logger.info("MainChainArtifactConsumer started")

        while self._running:
            try:
                if not self._subscribed:
                    await self.event_bus.subscribe(
                        stream=self.STREAM_NAME,
                        group_name=self.GROUP_NAME,
                        consumer_name=self.consumer_name,
                        callback=self._handle_event,
                    )
                    self._subscribed = True
                await asyncio.sleep(1)
            except Exception as exc:
                self._subscribed = False
                logger.error("MainChainArtifactConsumer error: {}", exc)
                await asyncio.sleep(1)

    async def stop(self):
        self._running = False

    async def _handle_event(self, event: dict):
        event_type = event.get("event_type")
        if event_type == "task.completed":
            await self._handle_task_event(event, generated_reason="task_completed", include_reflection=False)
        elif event_type == "task.abandoned":
            await self._handle_task_event(event, generated_reason="task_abandoned", include_reflection=True)
        elif event_type == "task.feedback_submitted":
            await self._handle_task_event(event, generated_reason="task_feedback_submitted", include_reflection=True)
        elif event_type == "intervention_record.status_changed":
            await self._handle_intervention_status_changed(event)
        elif event_type == "planning_artifact.approved":
            await self._handle_artifact_approved(event)

    async def _handle_task_event(
        self,
        event: dict,
        *,
        generated_reason: str,
        include_reflection: bool,
    ) -> None:
        plan_id_raw = event.get("plan_id")
        task_id_raw = event.get("task_id")

        async with self.session_factory() as db:
            service = MainChainArtifactService(db, self.event_bus)
            plan_id = await self._resolve_plan_id(db, plan_id_raw=plan_id_raw, task_id_raw=task_id_raw)
            if not plan_id:
                return
            await service.refresh_for_legacy_plan(
                legacy_plan_id=plan_id,
                generated_reason=generated_reason,
                include_reflection=include_reflection,
                linked_feedback_id=str(event.get("feedback_id") or "") or None,
            )
            await db.commit()

    async def _handle_intervention_status_changed(self, event: dict) -> None:
        record_id_raw = event.get("record_id")
        if not record_id_raw:
            return
        try:
            record_id = UUID(str(record_id_raw))
        except (TypeError, ValueError):
            return

        async with self.session_factory() as db:
            record = await db.get(InterventionRecord, record_id)
            if not record or not record.plan_card_id:
                return
            service = MainChainArtifactService(db, self.event_bus)
            await service.refresh_active_phase_pack(
                plan_card_id=record.plan_card_id,
                generated_reason="intervention_status_changed",
            )
            await service.refresh_reflection_report(
                plan_card_id=record.plan_card_id,
                generated_reason="intervention_status_changed",
                linked_intervention_id=str(record.id),
            )
            await db.commit()

    async def _handle_artifact_approved(self, event: dict) -> None:
        plan_card_id_raw = event.get("plan_card_id")
        artifact_type_raw = event.get("artifact_type")
        if not plan_card_id_raw or not artifact_type_raw:
            return

        try:
            plan_card_id = UUID(str(plan_card_id_raw))
            artifact_type = ArtifactType(str(artifact_type_raw))
        except (TypeError, ValueError):
            return

        async with self.session_factory() as db:
            service = MainChainArtifactService(db, self.event_bus)
            if artifact_type in {
                ArtifactType.GLOBAL_COMPASS,
                ArtifactType.STRATEGY_MAP,
                ArtifactType.ACTIVE_PHASE_PACK,
            }:
                await service.refresh_active_phase_pack(
                    plan_card_id=plan_card_id,
                    generated_reason=f"artifact_approved:{artifact_type.value.lower()}",
                )

            if artifact_type in {
                ArtifactType.DECISION_LOG,
                ArtifactType.RISK_REGISTER,
                ArtifactType.ACTIVE_PHASE_PACK,
            }:
                await service.refresh_reflection_report(
                    plan_card_id=plan_card_id,
                    generated_reason=f"artifact_approved:{artifact_type.value.lower()}",
                )
            await db.commit()

    async def _resolve_plan_id(
        self,
        db,
        *,
        plan_id_raw: str | UUID | None,
        task_id_raw: str | UUID | None,
    ) -> UUID | None:
        if plan_id_raw and str(plan_id_raw) != "None":
            try:
                return UUID(str(plan_id_raw))
            except (TypeError, ValueError):
                pass

        if not task_id_raw:
            return None
        try:
            task_id = UUID(str(task_id_raw))
        except (TypeError, ValueError):
            return None

        result = await db.execute(select(Task.plan_id).where(Task.id == task_id))
        return result.scalar_one_or_none()
