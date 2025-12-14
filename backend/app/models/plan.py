"""
�!�
Plan Model - �:���
"""
import enum
from sqlalchemy import (
    Column, String, Integer, Float, Text, Enum,
    ForeignKey, Date, Boolean, Index
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class PlanType(str, enum.Enum):
    """�{��>"""
    SPRINT = "sprint"  # �:����	
    GROWTH = "growth"  # ����G	


class Plan(BaseModel):
    """
    �!�

    W�:
        user_id: @^(7ID
        name: ��
        type: �{��:/	
        description: ���
        target_date: ���:�(	
        subject: f�/�
        daily_available_minutes: ���(���	
        total_estimated_hours: ;����	
        mastery_level: SM�� (0-1)
        progress: �ۦ (0-1)
        is_active: /&�;

    s�:
        user: @^(7
        tasks: ��@	��
    """

    __tablename__ = "plans"

    # sTs�
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # ��,�o
    name = Column(String(255), nullable=False)
    type = Column(Enum(PlanType), nullable=False)
    description = Column(Text, nullable=True)

    # ���s
    target_date = Column(Date, nullable=True)  # �:����
    daily_available_minutes = Column(Integer, default=60, nullable=False)
    total_estimated_hours = Column(Float, nullable=True)

    # f�/�
    subject = Column(String(100), nullable=True)

    # ۦ�*
    mastery_level = Column(Float, default=0.0, nullable=False)  # �� 0-1
    progress = Column(Float, default=0.0, nullable=False)        # �ۦ 0-1

    # �
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # s��I
    user = relationship("User", back_populates="plans")
    tasks = relationship(
        "Task",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<Plan(name={self.name}, type={self.type}, progress={self.progress})>"


# �"
Index("idx_plans_user_id", Plan.user_id)
Index("idx_plans_is_active", Plan.is_active)
Index("idx_plans_type", Plan.type)
Index("idx_plans_target_date", Plan.target_date)
