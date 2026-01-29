"""Schemas Package - Export all Pydantic Schemas"""

# Common schemas
# Chat schemas
from app.schemas.chat import (
    AIResponse,
    ChatHistory,
    ChatMessageBase,
    ChatMessageDetail,
    ChatMessageSend,
    ChatSession,
    ChatSessionCreate,
)
from app.schemas.common import (
    BaseSchema,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    Response,
    TokenResponse,
)

# Plan schemas
from app.schemas.plan import (
    GenerateTasksRequest,
    PlanActivate,
    PlanBase,
    PlanCreate,
    PlanDetail,
    PlanProgress,
    PlanSummary,
    PlanUpdate,
)

# Task schemas
from app.schemas.task import (
    TaskAbandon,
    TaskBase,
    TaskComplete,
    TaskCreate,
    TaskDetail,
    TaskListQuery,
    TaskStart,
    TaskSummary,
    TaskUpdate,
)

# User schemas
from app.schemas.user import (
    PasswordChange,
    RefreshTokenRequest,
    UserBase,
    UserFlameStatus,
    UserLogin,
    UserPreferences,
    UserProfile,
    UserRegister,
    UserUpdate,
)

__all__ = [
    # Common
    "Response",
    "ErrorResponse",
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    "BaseSchema",
    "TokenResponse",
    # User
    "UserRegister",
    "UserLogin",
    "UserUpdate",
    "PasswordChange",
    "RefreshTokenRequest",
    "UserBase",
    "UserProfile",
    "UserFlameStatus",
    "UserPreferences",
    # Task
    "TaskCreate",
    "TaskUpdate",
    "TaskStart",
    "TaskComplete",
    "TaskAbandon",
    "TaskBase",
    "TaskDetail",
    "TaskSummary",
    "TaskListQuery",
    # Plan
    "PlanCreate",
    "PlanUpdate",
    "PlanActivate",
    "GenerateTasksRequest",
    "PlanBase",
    "PlanDetail",
    "PlanProgress",
    "PlanSummary",
    # Chat
    "ChatMessageSend",
    "ChatSessionCreate",
    "ChatMessageBase",
    "ChatMessageDetail",
    "ChatSession",
    "ChatHistory",
    "AIResponse",
]
