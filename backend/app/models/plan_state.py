"""
PlanState Model - 计划级状态存储
Plan-level state storage for tracking plan execution context.

See: docs/state/plan_state_spec.md for design details.
"""
import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

# Use JSONB for PostgreSQL, fallback to JSON for SQLite
try:
    from sqlalchemy import JSON
    JSONBCompat = JSONB().with_variant(JSON(), "sqlite")
except ImportError:
    from sqlalchemy import JSON
    JSONBCompat = JSON()


class PlanStateStatus(str, enum.Enum):
    """Plan state status enum"""
    ACTIVE = "active"
    ARCHIVED = "archived"


class PlanState(BaseModel):
    """
    PlanState Model - 计划级状态

    Stores plan-specific context including:
    - facts: Learned facts during plan execution
    - milestones: Achievement records
    - task_index: Task completion statistics
    - task_summaries: Recent task summaries for quick reference
    - feedback_log: User feedback history
    - constraints: Runtime constraints

    Fields:
        plan_id: Associated plan ID (unique, indexed)
        user_id: Owner user ID (for permission isolation)
        facts: JSON object storing plan-specific facts
        milestones: JSON array of milestone records
        task_index: JSON object with task completion stats
        task_summaries: JSON array of recent task summaries
        feedback_log: JSON array of feedback entries
        constraints: JSON object with runtime constraints
        version: Optimistic locking version number
        status: 'active' or 'archived'
        archived_at: When the plan state was archived

    Relations:
        plan: Associated Plan record
        user: Owner User record
    """

    __tablename__ = "plan_states"

    # Foreign keys
    plan_id = Column(
        GUID(),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # State fields (JSONB for efficient querying)
    facts = Column(JSONBCompat, nullable=False, default=dict)
    milestones = Column(JSONBCompat, nullable=False, default=list)
    task_index = Column(JSONBCompat, nullable=False, default=dict)
    task_summaries = Column(JSONBCompat, nullable=False, default=list)
    feedback_log = Column(JSONBCompat, nullable=False, default=list)
    constraints = Column(JSONBCompat, nullable=False, default=dict)

    # Version control (optimistic locking)
    version = Column(Integer, nullable=False, default=1)

    # P0-2: Rejection tracking for phase rollback
    consecutive_rejection_count = Column(Integer, nullable=False, default=0)

    # Multi-plan coordination fields
    is_focus = Column(Boolean, nullable=False, default=False, index=True)
    last_focus_time = Column(DateTime, nullable=True, index=True)
    parallel_priority = Column(Integer, nullable=False, default=0, index=True)

    # Status management
    status = Column(
        String(20),
        nullable=False,
        default=PlanStateStatus.ACTIVE.value,
        index=True,
    )
    archived_at = Column(DateTime, nullable=True)

    # Relationships
    plan = relationship("Plan", backref="plan_state", uselist=False)
    user = relationship("User", backref="plan_states")

    def __repr__(self):
        return f"<PlanState(plan_id={self.plan_id}, status={self.status}, version={self.version})>"

    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "id": str(self.id),
            "plan_id": str(self.plan_id),
            "user_id": str(self.user_id),
            "facts": self.facts or {},
            "milestones": self.milestones or [],
            "task_index": self.task_index or {},
            "task_summaries": self.task_summaries or [],
            "feedback_log": self.feedback_log or [],
            "constraints": self.constraints or {},
            "version": self.version,
            "consecutive_rejection_count": self.consecutive_rejection_count or 0,
            "is_focus": self.is_focus,
            "last_focus_time": self.last_focus_time.isoformat() if self.last_focus_time else None,
            "parallel_priority": self.parallel_priority,
            "status": self.status,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlanState":
        """Create from dictionary (for cache deserialization)"""
        from datetime import datetime
        from uuid import UUID

        def parse_datetime(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(val)

        def parse_uuid(val):
            if val is None:
                return None
            if isinstance(val, UUID):
                return val
            return UUID(val)

        return cls(
            id=parse_uuid(data.get("id")),
            plan_id=parse_uuid(data.get("plan_id")),
            user_id=parse_uuid(data.get("user_id")),
            facts=data.get("facts", {}),
            milestones=data.get("milestones", []),
            task_index=data.get("task_index", {}),
            task_summaries=data.get("task_summaries", []),
            feedback_log=data.get("feedback_log", []),
            constraints=data.get("constraints", {}),
            version=data.get("version", 1),
            consecutive_rejection_count=data.get("consecutive_rejection_count", 0),
            is_focus=data.get("is_focus", False),
            last_focus_time=parse_datetime(data.get("last_focus_time")),
            parallel_priority=data.get("parallel_priority", 0),
            status=data.get("status", PlanStateStatus.ACTIVE.value),
            archived_at=parse_datetime(data.get("archived_at")),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
        )


# Indexes for common query patterns
Index("idx_plan_states_user_status", PlanState.user_id, PlanState.status)
Index("idx_plan_states_updated_at", PlanState.updated_at)
