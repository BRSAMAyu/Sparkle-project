"""
学科标准模型
Subject Model - 用于规范化错误档案中的学科分类
"""
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now():
    """返回当前 UTC 时间 (timezone-aware)"""
    return datetime.now(UTC)


class Subject(Base):
    """
    学科标准表 - 解决数据污染问题

    用于规范化错误档案中的学科分类
    注意：此表使用 Integer 自增主键而非 UUID
    """
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 标准名称（显示用）
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # 例如: "数据结构与算法"

    # 别名（JSON 数组，用于 AI 映射）
    aliases: Mapped[Any] = mapped_column(JSON, default=list, nullable=True)
    # 例如: '["数据结构", "Data Structure", "DS", "算法"]'

    # 分类
    category: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    # 例如: "计算机科学", "数学", "物理"

    # 星域代码 (Knowledge Galaxy)
    # 枚举: COSMOS, TECH, ART, CIVILIZATION, LIFE, WISDOM, VOID
    sector_code: Mapped[str] = mapped_column(String(20), default="VOID", nullable=False, server_default="VOID")

    # 星域色调 (Hex Color)
    hex_color: Mapped[str] = mapped_column(String(7), nullable=True)
    # 例如: "#FF5733"

    # 星域辉光色 (Glow Color)
    glow_color: Mapped[str] = mapped_column(String(7), nullable=True)

    # 星域基准角度 (0-360)
    position_angle: Mapped[float] = mapped_column(Float, nullable=True)

    # 星域图标
    icon_name: Mapped[str] = mapped_column(String(50), nullable=True)

    # 是否启用
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=True)

    # 排序权重
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=True)

    # 时间戳 (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False
    )

    def __repr__(self):
        return f"<Subject(id={self.id}, name={self.name})>"
