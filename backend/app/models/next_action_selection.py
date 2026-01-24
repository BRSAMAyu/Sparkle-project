"""
Next Action Selection Model

追踪用户对任务完成后的next_action建议的选择行为，
用于个性化推荐和偏好学习。
"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, Boolean, DateTime, TypeDecorator, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import BaseModel, GUID


class JSONCompat(TypeDecorator):
    """
    跨数据库兼容的 JSON 类型

    - PostgreSQL: 使用 JSONB 类型
    - SQLite/其他: 使用 TEXT 存储 JSON 字符串
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB(astext_type=Text))
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            return json.loads(value)
        return value


class NextActionSelection(BaseModel):
    """
    Next Action Selection 追踪模型

    记录用户对next_action建议的交互行为：
    - selected: 用户点击了该action
    - skipped: 用户跳过了所有建议（隐式）
    """
    __tablename__ = "next_action_selections"

    user_id = Column(GUID(), nullable=False, index=True)
    task_id = Column(GUID(), nullable=False, index=True)

    # Action信息
    action_type = Column(String(50), nullable=False, index=True)  # quick_review, light_expand, etc.
    action_title = Column(String(255), nullable=False)

    # 用户行为
    selected = Column(Boolean, nullable=False, default=False)
    skipped = Column(Boolean, nullable=False, default=False)

    # 显示上下文
    display_position = Column(Integer, nullable=True)  # 在列表中的位置 (0-based)
    displayed_actions_count = Column(Integer, nullable=True)  # 总共显示了多少个建议

    # 额外上下文信息
    context = Column(JSONCompat, nullable=True)  # 扩展信息

    def __repr__(self):
        return f"<NextActionSelection(user_id={self.user_id}, action_type={self.action_type}, selected={self.selected})>"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "task_id": str(self.task_id),
            "action_type": self.action_type,
            "action_title": self.action_title,
            "selected": self.selected,
            "skipped": self.skipped,
            "display_position": self.display_position,
            "displayed_actions_count": self.displayed_actions_count,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
