"""
Personalization 模块
"""
from sqlalchemy.ext.asyncio import AsyncSession

from .engine import PersonalizationEngine
from .preference_service import PreferenceService
from .profiles import LLMProfile, PushPolicyProfile, TaskPlanProfile
from .runtime_context_service import RuntimeContextService


def get_personalization_engine(db: AsyncSession, redis=None) -> PersonalizationEngine:
    """工厂函数：创建 PersonalizationEngine 实例"""
    pref_service = PreferenceService(db, redis)
    ctx_service = RuntimeContextService(db, redis)
    return PersonalizationEngine(pref_service, ctx_service)


__all__ = [
    "PersonalizationEngine",
    "PreferenceService",
    "RuntimeContextService",
    "LLMProfile",
    "PushPolicyProfile",
    "TaskPlanProfile",
    "get_personalization_engine",
]
