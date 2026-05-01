"""
Core: execution
Phase: plan→execute
Stage: Signal-to-Action Spine P3-2 Agenda Queue

Multi-message queue for AuroraAgenda items — persists pending items to Redis
so the frontend can poll for messages that need user interaction.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.signals.types import AuroraAgenda, AuroraAgendaItem, _uid

_AGENDA_KEY = "spine:agenda:{session_id}"
_USER_AGENDAS_KEY = "spine:agendas:{user_id}"
_PENDING_KEY = "spine:agenda_pending:{user_id}"


class AgendaQueueService:
    """Manage AuroraAgenda persistence and pending item retrieval."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def save_agenda(self, user_id: str, agenda: AuroraAgenda) -> None:
        """Persist an agenda to Redis."""
        key = _AGENDA_KEY.format(session_id=agenda.session_id)
        await self.redis.set(key, json.dumps(agenda.to_dict()), ex=24 * 3600)

        user_key = _USER_AGENDAS_KEY.format(user_id=user_id)
        await self.redis.sadd(user_key, agenda.session_id)
        await self.redis.expire(user_key, 7 * 24 * 3600)

    async def get_agenda(self, session_id: str) -> AuroraAgenda | None:
        """Load an agenda from Redis."""
        raw = await self.redis.get(_AGENDA_KEY.format(session_id=session_id))
        if not raw:
            return None
        return AuroraAgenda.from_dict(json.loads(raw))

    async def get_user_agendas(self, user_id: str) -> list[AuroraAgenda]:
        """Get all active agendas for a user."""
        user_key = _USER_AGENDAS_KEY.format(user_id=user_id)
        session_ids = await self.redis.smembers(user_key)
        if not session_ids:
            return []

        agendas = []
        for sid in session_ids:
            sid_str = sid if isinstance(sid, str) else sid.decode()
            agenda = await self.get_agenda(sid_str)
            if agenda and agenda.status == "active":
                agendas.append(agenda)
        return agendas

    async def get_pending_items(self, user_id: str) -> list[dict[str, Any]]:
        """Get all items across agendas that need user interaction.

        Frontend polls this to show pending questions/confirmations.
        """
        agendas = await self.get_user_agendas(user_id)
        pending = []
        for agenda in agendas:
            for item in agenda.agenda_items:
                if item.status in ("pending", "waiting_user"):
                    pending.append({
                        "session_id": agenda.session_id,
                        "item": item.to_dict(),
                        "scope": agenda.scope,
                    })
        return pending

    async def update_item_status(
        self,
        session_id: str,
        item_id: str,
        new_status: str,
    ) -> AuroraAgendaItem | None:
        """Update the status of a specific agenda item."""
        agenda = await self.get_agenda(session_id)
        if not agenda:
            return None

        for item in agenda.agenda_items:
            if item.item_id == item_id:
                item.status = new_status
                await self.save_agenda(agenda.session_id.split(":")[-1] if ":" in agenda.session_id else "unknown", agenda)
                # Re-derive user_id from agenda for proper save
                logger.debug(
                    "AgendaQueue: updated item={} status={}",
                    item_id, new_status,
                )
                return item
        return None

    async def add_item_to_agenda(
        self,
        user_id: str,
        session_id: str,
        item_type: str,
        payload: dict[str, Any] | None = None,
    ) -> AuroraAgendaItem | None:
        """Add a new item to an existing agenda."""
        agenda = await self.get_agenda(session_id)
        if not agenda:
            return None

        item = AuroraAgendaItem(
            item_id=_uid("ai"),
            item_type=item_type,
            status="pending",
            payload=payload or {},
        )
        agenda.agenda_items.append(item)
        await self.save_agenda(user_id, agenda)
        return item
