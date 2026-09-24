from datetime import date
from typing import Any

from sqlalchemy import JSON, Date, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class LtmDailySnapshot(BaseModel):
    __tablename__ = "ltm_daily_snapshots"

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False)


Index("idx_ltm_daily_snapshots_date", LtmDailySnapshot.snapshot_date, unique=True)
