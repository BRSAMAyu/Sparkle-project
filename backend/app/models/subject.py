"""
学科标准模型
Subject Model - 用于规范化错误档案中的学科分类
"""
from sqlalchemy import Column, String, Boolean, Integer, JSON
from app.models.base import Base

class Subject(Base):
    """
    🆕 学科标准表 - 解决数据污染问题 (v2.1)
    
    用于规范化错误档案中的学科分类
    """
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 标准名称（显示用）
    name = Column(String(100), unique=True, nullable=False)
    # 例如: "数据结构与算法"
    
    # 别名（JSON 数组，用于 AI 映射）
    aliases = Column(JSON, default=list, nullable=True)
    # 例如: '["数据结构", "Data Structure", "DS", "算法"]'
    
    # 分类
    category = Column(String(50), nullable=True)
    # 例如: "计算机科学", "数学", "物理"
    
    # 是否启用
    is_active = Column(Boolean, default=True)
    
    # 排序权重
    sort_order = Column(Integer, default=0)
    
    # 创建时间等基础字段不需要继承 BaseModel 因为 ID 是 Integer 不是 UUID
    created_at = Column(String, nullable=True) # Placeholder if needed, or stick to Base. 
    # Actually Base usually has created_at if it inherits from BaseModel. 
    # But here I am inheriting from Base directly as per doc snippet `from app.models.base import Base`.
    # Let's check app/models/base.py to see what Base is.
    
    def __repr__(self):
        return f"<Subject(name={self.name})>"
