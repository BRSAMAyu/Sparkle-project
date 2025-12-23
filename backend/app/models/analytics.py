"""
Analytics Models
数据分析相关模型
"""
from sqlalchemy import Column, Integer, Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID

class UserDailyMetric(BaseModel):
    """
    用户每日指标表 (User Daily Metrics)
    每日聚合用户的各项关键指标，用于长期趋势分析
    """
    __tablename__ = "user_daily_metrics"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # 参与度指标 (Engagement)
    total_focus_minutes = Column(Integer, default=0) # 当日总专注时间
    tasks_completed = Column(Integer, default=0) # 完成任务数
    tasks_created = Column(Integer, default=0) # 创建任务数
    
    # 学习指标 (Learning)
    nodes_studied = Column(Integer, default=0) # 学习的不同节点数
    mastery_gained = Column(Float, default=0.0) # 当日获得的掌握度增量总和
    review_count = Column(Integer, default=0) # 复习次数

    # 认知/情绪指标 (Cognitive/Emotional)
    # 基于 CognitiveFragment 的聚合
    average_mood = Column(Float, nullable=True) # 平均情绪值 (如果有量化)
    anxiety_score = Column(Float, default=0.0) # 焦虑指数 (0-1)
    
    # 系统交互 (System)
    chat_messages_count = Column(Integer, default=0) # 发送的消息数
    
    # 关系
    user = relationship("User", backref="daily_metrics")

    # 唯一约束: 每个用户每天只有一条记录
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_user_daily_metric'),
    )

    def __repr__(self):
        return f"<UserDailyMetric(user_id={self.user_id}, date={self.date})>"
