"""Schemas Package - Export all Pydantic Schemas"""

# Common schemas
from app.schemas.common import (
    Response,
    ErrorResponse,
    PaginationParams,
    PaginationMeta,
    PaginatedResponse,
    BaseSchema,
    TokenResponse,
)

# User schemas
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserUpdate,
    PasswordChange,
    RefreshTokenRequest,
    UserBase,
    UserProfile,
    UserFlameStatus,
    UserPreferences,
)

# Task schemas
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskStart,
    TaskComplete,
    TaskAbandon,
    TaskBase,
    TaskDetail,
    TaskSummary,
    TaskListQuery,
)

# Plan schemas
from app.schemas.plan import (
    PlanCreate,
    PlanUpdate,
    PlanActivate,
    GenerateTasksRequest,
    PlanBase,
    PlanDetail,
    PlanProgress,
    PlanSummary,
)

# Chat schemas
from app.schemas.chat import (
    ChatMessageSend,
    ChatSessionCreate,
    ChatMessageBase,
    ChatMessageDetail,
    ChatSession,
    ChatHistory,
    AIResponse,
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
