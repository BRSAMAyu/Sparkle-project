"""
Core: execution
Phase: execute→reflect
Stage: Signal-to-Action Spine P2-8 PartnerCommitmentLoop

Partners make commitments to each other. This loop:
1. Tracks partner commitments with deadlines
2. Triggers Spine signals when deadlines approach or pass
3. Records commitment outcomes for accountability
4. Feeds back into the relationship model
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from loguru import logger

_COMMITMENT_KEY = "spine:partner_commitment:{commitment_id}"
_USER_COMMITMENTS_KEY = "spine:partner_commitments:{user_id}"
_PARTNER_PAIR_KEY = "spine:partner_pair:{user_id}:{partner_id}"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class PartnerCommitment:
    commitment_id: str
    user_id: str
    partner_id: str
    description: str
    deadline: datetime
    created_at: datetime
    status: str = "pending"  # pending | fulfilled | missed | cancelled
    outcome_note: str | None = None
    resolved_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "commitment_id": self.commitment_id,
            "user_id": self.user_id,
            "partner_id": self.partner_id,
            "description": self.description,
            "deadline": self.deadline.isoformat(),
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "outcome_note": self.outcome_note,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PartnerCommitment:
        return cls(
            commitment_id=data["commitment_id"],
            user_id=data["user_id"],
            partner_id=data["partner_id"],
            description=data["description"],
            deadline=datetime.fromisoformat(data["deadline"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            status=data.get("status", "pending"),
            outcome_note=data.get("outcome_note"),
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
        )


class PartnerCommitmentLoop:
    """Manages the partner commitment lifecycle and Spine integration."""

    def __init__(self, redis: Any):
        self.redis = redis

    async def create_commitment(
        self,
        *,
        user_id: str,
        partner_id: str,
        description: str,
        deadline: datetime,
    ) -> PartnerCommitment:
        from app.signals.types import _uid
        commitment = PartnerCommitment(
            commitment_id=_uid("pc"),
            user_id=user_id,
            partner_id=partner_id,
            description=description,
            deadline=deadline,
            created_at=_now(),
        )
        key = _COMMITMENT_KEY.format(commitment_id=commitment.commitment_id)
        await self.redis.set(key, json.dumps(commitment.to_dict()))
        await self.redis.expire(key, 86400 * 30)  # 30 day TTL

        user_key = _USER_COMMITMENTS_KEY.format(user_id=user_id)
        await self.redis.lpush(user_key, commitment.commitment_id)
        await self.redis.expire(user_key, 86400 * 30)

        logger.info("PartnerCommitment: created {} user={} partner={} deadline={}",
                     commitment.commitment_id, user_id, partner_id, deadline.isoformat())
        return commitment

    async def resolve_commitment(
        self,
        *,
        commitment_id: str,
        status: str,
        outcome_note: str | None = None,
    ) -> PartnerCommitment | None:
        if status not in ("fulfilled", "missed", "cancelled"):
            raise ValueError(f"Invalid resolution status: {status}")

        key = _COMMITMENT_KEY.format(commitment_id=commitment_id)
        raw = await self.redis.get(key)
        if not raw:
            return None

        commitment = PartnerCommitment.from_dict(json.loads(raw))
        commitment.status = status
        commitment.outcome_note = outcome_note
        commitment.resolved_at = _now()

        await self.redis.set(key, json.dumps(commitment.to_dict()))
        logger.info("PartnerCommitment: resolved {} as {}", commitment_id, status)
        return commitment

    async def get_pending_commitments(self, user_id: str) -> list[PartnerCommitment]:
        import json
        user_key = _USER_COMMITMENTS_KEY.format(user_id=user_id)
        raw_ids = await self.redis.lrange(user_key, 0, -1)
        if not raw_ids:
            return []

        commitments: list[PartnerCommitment] = []
        for cid in raw_ids:
            key = _COMMITMENT_KEY.format(commitment_id=cid)
            raw = await self.redis.get(key)
            if raw:
                c = PartnerCommitment.from_dict(json.loads(raw))
                if c.status == "pending":
                    commitments.append(c)
        return commitments

    async def check_deadline_approaching(
        self,
        user_id: str,
        hours_ahead: int = 24,
    ) -> list[PartnerCommitment]:
        now = _now()
        from datetime import timedelta
        threshold = now + timedelta(hours=hours_ahead)

        pending = await self.get_pending_commitments(user_id)
        approaching = [c for c in pending if now <= c.deadline <= threshold]
        return approaching

    async def check_overdue(self, user_id: str) -> list[PartnerCommitment]:
        now = _now()
        pending = await self.get_pending_commitments(user_id)
        overdue = [c for c in pending if c.deadline < now]
        return overdue

    async def build_commitment_signal_payload(
        self,
        user_id: str,
    ) -> dict[str, Any] | None:
        approaching = await self.check_deadline_approaching(user_id)
        overdue = await self.check_overdue(user_id)

        if not approaching and not overdue:
            return None

        return {
            "approaching_count": len(approaching),
            "overdue_count": len(overdue),
            "approaching": [c.to_dict() for c in approaching[:3]],
            "overdue": [c.to_dict() for c in overdue[:3]],
        }
