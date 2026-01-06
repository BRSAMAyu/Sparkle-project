from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
import asyncio
import json
from loguru import logger
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.galaxy_service import GalaxyService
from app.services.error_book_service import ErrorBookService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.services.focus_service import focus_service
from app.schemas.task import TaskListQuery, TaskStatus
from app.schemas.error_book import ErrorQueryParams

class CognitiveContext(BaseModel):
    """
    User's aggregated cognitive context for LLM injection.
    Reflects the 'Learning Profile' of the user.
    """
    user_id: str
    timestamp: datetime
    
    # Knowledge State (Galaxy)
    knowledge_stats: Dict[str, Any] = Field(default_factory=dict, description="Overall mastery and stats")
    recent_mastery_changes: List[Dict[str, Any]] = Field(default_factory=list, description="Recently mastered nodes")
    
    # Problem Areas (Error Book)
    error_summary: Dict[str, Any] = Field(default_factory=dict, description="Review stats and weak subjects")
    recent_errors: List[Dict[str, Any]] = Field(default_factory=list, description="Recent error records for context")
    
    # Task & Goals (Task/Plan)
    active_tasks: List[Dict[str, Any]] = Field(default_factory=list, description="Current pending tasks")
    focus_stats: Dict[str, Any] = Field(default_factory=dict, description="Today's focus performance")
    
    # User Profile (User)
    preferences: Dict[str, Any] = Field(default_factory=dict, description="Learning preferences")
    engagement_metrics: Dict[str, Any] = Field(default_factory=dict, description="Engagement level and patterns")

    def to_llm_system_prompt_context(self) -> str:
        """Convert to a string representation suitable for System Prompt injection"""
        # Compact representation
        return json.dumps(self.model_dump(mode='json', exclude={'user_id', 'timestamp'}), ensure_ascii=False)


class ContextOrchestrator:
    """
    Orchestrates the gathering of user context from multiple services.
    Uses Redis for caching snapshots to ensure low latency for Chat API.
    """
    
    CACHE_TTL_SECONDS = 300  # 5 minutes cache
    
    def __init__(self, db_session: AsyncSession, redis_client):
        self.db = db_session
        self.redis = redis_client
        
        # Initialize Services
        self.galaxy_service = GalaxyService(db_session)
        self.error_book_service = ErrorBookService(db_session)
        # TaskService is static, but we can wrap if needed. Using static methods directly in _get_task_profile
        # UserService needs instance
        self.user_service = UserService(db_session, redis_client)

    async def get_user_context(self, user_id: str, force_refresh: bool = False) -> CognitiveContext:
        """
        Get aggregated user context.
        Tries cache first, then gathers from services in parallel.
        """
        if not force_refresh:
            cached = await self._get_cached_context(user_id)
            if cached:
                return cached
        
        uid = UUID(user_id)
        
        # Parallel Execution of independent context gathering
        # We protect against individual service failures to return at least partial context
        results = await asyncio.gather(
            self._get_knowledge_profile(uid),
            self._get_error_profile(uid),
            self._get_task_profile(uid),
            self._get_user_profile(uid),
            return_exceptions=True
        )
        
        # Unpack results
        knowledge_data = self._handle_result(results[0], "knowledge", {})
        error_data = self._handle_result(results[1], "error", {})
        task_data = self._handle_result(results[2], "task", {})
        user_data = self._handle_result(results[3], "user", {})
        
        # Construct Context Object
        context = CognitiveContext(
            user_id=user_id,
            timestamp=datetime.utcnow(),
            
            knowledge_stats=knowledge_data.get("stats", {}),
            recent_mastery_changes=knowledge_data.get("recent", []),
            
            error_summary=error_data.get("summary", {}),
            recent_errors=error_data.get("recent", []),
            
            active_tasks=task_data.get("tasks", []),
            focus_stats=task_data.get("focus", {}),
            
            preferences=user_data.get("preferences", {}),
            engagement_metrics=user_data.get("metrics", {})
        )
        
        # Cache the result
        await self._cache_context(user_id, context)
        
        return context

    def _handle_result(self, result, name: str, default: Any) -> Any:
        if isinstance(result, Exception):
            logger.error(f"Failed to gather {name} context: {result}")
            return default
        return result

    async def _get_cached_context(self, user_id: str) -> Optional[CognitiveContext]:
        if not self.redis:
            return None
        try:
            key = f"user:context:snapshot:{user_id}"
            data = await self.redis.get(key)
            if data:
                json_data = json.loads(data)
                return CognitiveContext(**json_data)
        except Exception as e:
            logger.warning(f"Cache get failed for user context: {e}")
        return None

    async def _cache_context(self, user_id: str, context: CognitiveContext):
        if not self.redis:
            return
        try:
            key = f"user:context:snapshot:{user_id}"
            data = context.model_dump_json()
            await self.redis.setex(key, self.CACHE_TTL_SECONDS, data)
        except Exception as e:
            logger.warning(f"Cache set failed for user context: {e}")

    # --- Sub-fetchers ---

    async def _get_knowledge_profile(self, user_id: UUID) -> Dict[str, Any]:
        """Fetch Galaxy stats and recent mastery"""
        # 1. Stats
        stats_model = await self.galaxy_service.stats.calculate_user_stats(user_id)
        stats = stats_model.dict() if stats_model else {}
        
        # 2. Recent Mastery (This might require a specialized query in GalaxyService or StatsService)
        # For now, we can infer or leave empty if not easily available without custom query.
        # Assuming we might want to add a method to GalaxyService later for "recent updates".
        recent = [] 
        
        return {
            "stats": stats,
            "recent": recent
        }

    async def _get_error_profile(self, user_id: UUID) -> Dict[str, Any]:
        """Fetch Error Book stats and recent errors"""
        # 1. Stats
        stats = await self.error_book_service.get_review_stats(user_id)
        
        # 2. Recent Errors (Top 5 pending review or just created)
        # We want "Recent High Frequency Errors" or just "Recent Errors"
        errors, _ = await self.error_book_service.list_errors(
            user_id, 
            ErrorQueryParams(page=1, page_size=5, need_review=False) # Just latest
        )
        
        recent_errors_data = []
        for e in errors:
            recent_errors_data.append({
                "id": str(e.id),
                "question_preview": e.question_text[:50] if e.question_text else "Image Question",
                "subject": e.subject_code,
                "error_type": e.latest_analysis.get("error_type_label") if e.latest_analysis else "Unknown",
                "mastery": e.mastery_level
            })
            
        return {
            "summary": stats,
            "recent": recent_errors_data
        }

    async def _get_task_profile(self, user_id: UUID) -> Dict[str, Any]:
        """Fetch Active Tasks and Focus Stats"""
        # 1. Active Tasks
        tasks, _ = await TaskService.get_multi(
            self.db, 
            user_id, 
            TaskListQuery(page=1, page_size=5, status=TaskStatus.PENDING)
        )
        
        active_tasks_data = []
        for t in tasks:
            active_tasks_data.append({
                "id": str(t.id),
                "title": t.title,
                "priority": t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "type": t.type.value
            })
            
        # 2. Focus Stats
        focus = await focus_service.get_today_stats(self.db, user_id)
        
        return {
            "tasks": active_tasks_data,
            "focus": focus
        }

    async def _get_user_profile(self, user_id: UUID) -> Dict[str, Any]:
        """Fetch User Context and Analytics"""
        # 1. Context
        user_ctx = await self.user_service.get_context(user_id)
        preferences = {}
        if user_ctx and user_ctx.preferences:
            preferences = user_ctx.preferences
            
        # 2. Analytics
        analytics = await self.user_service.get_analytics_summary(user_id)
        
        return {
            "preferences": preferences,
            "metrics": analytics
        }
