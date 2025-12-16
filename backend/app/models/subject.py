"""
学科标准模型
Subject Model - 用于规范化错误档案中的学科分类
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, JSON, DateTime

from app.db.session import Base


class Subject(Base):
    """
    学科标准表 - 解决数据污染问题

    用于规范化错误档案中的学科分类
    注意：此表使用 Integer 自增主键而非 UUID
    """
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 标准名称（显示用）
    name = Column(String(100), unique=True, nullable=False, index=True)
    # 例如: "数据结构与算法"

    # 别名（JSON 数组，用于 AI 映射）
    aliases = Column(JSON, default=list, nullable=True)
    # 例如: '["数据结构", "Data Structure", "DS", "算法"]'

    # 分类
    category = Column(String(50), nullable=True, index=True)
    # 例如: "计算机科学", "数学", "物理"

    # 是否启用
    is_active = Column(Boolean, default=True, index=True)

    # 排序权重
    sort_order = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f"<Subject(id={self.id}, name={self.name})>"
