"""
API v1 Router
聚合所有 v1 版本的 API 路由
"""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    users,
    galaxy,
    chat,
    tasks,
    plans,
    subjects,
    statistics,
    notifications,
    capsules,
    community,
    cognitive
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(galaxy.router, prefix="/galaxy", tags=["galaxy"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(statistics.router, prefix="/stats", tags=["statistics"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(capsules.router, prefix="/capsules", tags=["capsules"])
api_router.include_router(community.router, prefix="/community", tags=["community"])
api_router.include_router(cognitive.router, prefix="/cognitive", tags=["cognitive"])


@api_router.get("/")
async def api_root():
    """API v1 root endpoint"""
    return {
        "version": "v1",
        "status": "active",
        "endpoints": [
            "/auth",
            "/users",
            "/tasks",
            "/chat",
            "/plans",
            "/statistics",
            "/subjects",
            "/errors",
            "/health",
            "/community",
            "/capsules",
        ],
    }
