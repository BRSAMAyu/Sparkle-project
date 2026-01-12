from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_book import ErrorRecord
from app.models.nightly_review import NightlyReview
from app.models.user_state import UserStateSnapshot


class NightlyReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_for_user(
        self,
        user_id: UUID,
        timezone_name: Optional[str],
        review_date: Optional[date] = None,
    ) -> NightlyReview:
        target_date, window_start, window_end = self._review_window(timezone_name, review_date)

        errors = await self._get_errors_in_window(user_id, window_start, window_end)
        summary = self._build_summary(errors, target_date)
        todo_items = self._build_todos(errors)
        evidence_refs = self._build_evidence_refs(errors)

        latest_state = await self._latest_state(user_id)
        if latest_state:
            evidence_refs.append(
                {"type": "user_state", "id": str(latest_state.id), "schema_version": "user_state.v1"}
            )

        review = await self._get_or_create(user_id, target_date)
        review.summary_text = summary
        review.todo_items = todo_items
        review.evidence_refs = evidence_refs
        review.model_version = "nightly_v1"
        review.status = "generated"

        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def get_latest(self, user_id: UUID) -> Optional[NightlyReview]:
        result = await self.db.execute(
            select(NightlyReview)
            .where(NightlyReview.user_id == user_id)
            .order_by(NightlyReview.review_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def mark_reviewed(self, review_id: UUID, user_id: UUID) -> Optional[NightlyReview]:
        result = await self.db.execute(
            select(NightlyReview).where(
                NightlyReview.id == review_id,
                NightlyReview.user_id == user_id,
            )
        )
        review = result.scalar_one_or_none()
        if not review:
            return None

        review.status = "reviewed"
        review.reviewed_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def _get_or_create(self, user_id: UUID, review_date: date) -> NightlyReview:
        result = await self.db.execute(
            select(NightlyReview).where(
                NightlyReview.user_id == user_id,
                NightlyReview.review_date == review_date,
            )
        )
        review = result.scalar_one_or_none()
        if review:
            return review

        review = NightlyReview(
            user_id=user_id,
            review_date=review_date,
            summary_text=None,
            todo_items=[],
            evidence_refs=[],
        )
        self.db.add(review)
        await self.db.flush()
        return review

    def _review_window(
        self,
        timezone_name: Optional[str],
        review_date: Optional[date],
    ):
        tz = None
        if timezone_name:
            try:
                tz = ZoneInfo(timezone_name)
            except Exception:
                tz = None
        now_local = datetime.utcnow().astimezone(tz) if tz else datetime.utcnow()
        target_date = review_date or (now_local.date() - timedelta(days=1))
        start_local = datetime.combine(target_date, datetime.min.time())
        end_local = datetime.combine(target_date, datetime.max.time())
        if tz:
            start_utc = start_local.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
            end_utc = end_local.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
        else:
            start_utc = start_local
            end_utc = end_local
        return target_date, start_utc, end_utc

    async def _get_errors_in_window(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
    ) -> List[ErrorRecord]:
        result = await self.db.execute(
            select(ErrorRecord).where(
                and_(
                    ErrorRecord.user_id == user_id,
                    ErrorRecord.is_deleted == False,
                    ErrorRecord.created_at >= start,
                    ErrorRecord.created_at <= end,
                )
            )
        )
        return list(result.scalars().all())

    def _build_summary(self, errors: List[ErrorRecord], target_date: date) -> str:
        if not errors:
            return f"{target_date.isoformat()} 没有新错题，保持节奏。"

        subjects = sorted({e.subject_code for e in errors})
        return (
            f"{target_date.isoformat()} 共记录 {len(errors)} 道错题，"
            f"主要集中在 {', '.join(subjects)}。"
        )

    def _build_todos(self, errors: List[ErrorRecord]):
        if not errors:
            return []
        items = []
        for error in errors[:5]:
            items.append(
                {
                    "type": "review_error",
                    "payload": {
                        "error_id": str(error.id),
                        "subject_code": error.subject_code,
                        "title": f"{error.subject_code} 错题复盘",
                    },
                }
            )
        return items

    def _build_evidence_refs(self, errors: List[ErrorRecord]):
        refs = []
        for error in errors:
            refs.append({"type": "error", "id": str(error.id), "schema_version": "error.v1"})
        return refs

    async def _latest_state(self, user_id: UUID) -> Optional[UserStateSnapshot]:
        result = await self.db.execute(
            select(UserStateSnapshot)
            .where(UserStateSnapshot.user_id == user_id)
            .order_by(UserStateSnapshot.snapshot_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
