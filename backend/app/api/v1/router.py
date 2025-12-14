"""
API v1 Router
聚合所有 v1 版本的 API 路由
"""
from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# TODO: Include individual routers when implemented
# from app.api.v1 import auth, users, tasks, chat, plans, statistics

# api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
# api_router.include_router(users.router, prefix="/users", tags=["用户"])
# api_router.include_router(tasks.router, prefix="/tasks", tags=["任务"])
# api_router.include_router(chat.router, prefix="/chat", tags=["对话"])
# api_router.include_router(plans.router, prefix="/plans", tags=["计划"])
# api_router.include_router(statistics.router, prefix="/statistics", tags=["统计"])


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
        ],
    }
