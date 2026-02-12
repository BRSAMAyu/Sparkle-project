from sqlalchemy import JSON, Column, Date, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class LtmDailySnapshot(BaseModel):
    __tablename__ = "ltm_daily_snapshots"

    snapshot_date = Column(Date, nullable=False, unique=True, index=True)
    payload = Column(JSONBCompat, nullable=False)


Index("idx_ltm_daily_snapshots_date", LtmDailySnapshot.snapshot_date, unique=True)
