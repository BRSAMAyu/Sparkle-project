"""
用户偏好中心 - Single Source of Truth
"""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class UserPreferencesCenter(BaseModel):
    """统一用户偏好中心"""

    __tablename__ = "user_preferences_center"

    user_id = Column(GUID(), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    schema_version = Column(Integer, default=1, nullable=False)

    explicit = Column(JSONBCompat, nullable=False, default=dict)
    inferred = Column(JSONBCompat, nullable=False, default=dict)

    last_explicit_update = Column(DateTime, nullable=True)
    last_inferred_update = Column(DateTime, nullable=True)

    def increment_version(self) -> int:
        self.version += 1
        return self.version
