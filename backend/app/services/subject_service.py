"""
学科服务
Subject Service - 管理学科标准和映射 (v2.1)
"""
import json
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.subject import Subject

class SubjectService:
    """学科标准化服务"""
    
    # 内存缓存
    _cache: Dict[str, str] = {}
    _aliases_map: Dict[str, str] = {}
    _loaded: bool = False
    
    async def load_cache(self, db: AsyncSession) -> None:
        """加载学科缓存"""
        logger.info("Loading subject cache...")
        result = await db.execute(
            select(Subject).where(Subject.is_active == True)
        )
        subjects = result.scalars().all()
        
        self._cache = {s.name: s.name for s in subjects}
        self._aliases_map = {}
        
        for subject in subjects:
            # 别名映射到标准名
            if subject.aliases:
                try:
                    # aliases 是 JSON 类型，SQLAlchemy 会自动反序列化
                    aliases = subject.aliases if isinstance(subject.aliases, list) else json.loads(subject.aliases)
                    for alias in aliases:
                        self._aliases_map[alias.lower()] = subject.name
                except Exception as e:
                    logger.error(f"Failed to parse aliases for subject {subject.name}: {e}")
        
        self._loaded = True
        logger.info(f"Subject cache loaded. {len(subjects)} subjects, {len(self._aliases_map)} aliases.")
    
    def normalize(self, raw_subject: str) -> str:
        """
        将 AI 输出或用户输入的学科名映射到标准名
        
        示例:
        - "Data Structure" -> "数据结构与算法"
        - "DS" -> "数据结构与算法"
        - "数据结构" -> "数据结构与算法"
        """
        if not raw_subject:
            return "其他"
            
        # 1. 精确匹配
        if raw_subject in self._cache:
            return raw_subject
        
        # 2. 别名匹配（不区分大小写）
        normalized = self._aliases_map.get(raw_subject.lower())
        if normalized:
            return normalized
        
        # 3. 无法匹配，返回"其他"
        return "其他"
    
    async def get_all_subjects(self, db: AsyncSession) -> List[Subject]:
        """获取所有启用的学科（供前端下拉选择）"""
        result = await db.execute(
            select(Subject)
            .where(Subject.is_active == True)
            .order_by(Subject.sort_order, Subject.name)
        )
        return result.scalars().all()
