"""Aurora self-calibration: detect strategy failure and suggest calibration questions."""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_book import ErrorRecord

_CONSECUTIVE_ERROR_THRESHOLD = 3
_CALIBRATION_WINDOW_DAYS = 7
_CALIBRATION_QUESTIONS = {
    "default": "I notice you've had some trouble with this topic recently. Is the material not clear, or is the concept itself difficult?",
    "reading_issue": "It seems the study material isn't helping as expected. Would you like me to try a different explanation approach?",
    "concept_gap": "There might be a foundational gap. Should we step back and review the prerequisites first?",
}


class AuroraCalibrationService:
    """Detects when the current strategy is failing (consecutive errors)
    and generates a calibration question for the user."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check_calibration_needed(
        self,
        user_id: UUID,
        knowledge_node_id: UUID | None = None,
    ) -> tuple[bool, str]:
        """Returns (calibration_needed, calibration_question)."""
        since = datetime.utcnow() - timedelta(days=_CALIBRATION_WINDOW_DAYS)

        query = (
            select(ErrorRecord.knowledge_node_id, func.count(ErrorRecord.id).label("error_count"))
            .where(
                ErrorRecord.user_id == user_id,
                ErrorRecord.created_at >= since,
                ErrorRecord.deleted_at.is_(None),
            )
            .group_by(ErrorRecord.knowledge_node_id)
            .order_by(desc("error_count"))
        )

        if knowledge_node_id:
            query = query.where(ErrorRecord.knowledge_node_id == knowledge_node_id)

        rows = await self.db.execute(query)
        for row in rows:
            if row.error_count >= _CONSECUTIVE_ERROR_THRESHOLD:
                question = _CALIBRATION_QUESTIONS["default"]
                if row.error_count >= 5:
                    question = _CALIBRATION_QUESTIONS["concept_gap"]
                elif row.error_count >= 4:
                    question = _CALIBRATION_QUESTIONS["reading_issue"]
                logger.info(f"Calibration triggered for user {user_id}: {row.error_count} errors on node {row.knowledge_node_id}")
                return True, question

        return False, ""
