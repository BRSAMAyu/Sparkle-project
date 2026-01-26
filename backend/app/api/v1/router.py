"""
API v1 Router
聚合所有 v1 版本的 API 路由
"""
from fastapi import APIRouter
from app.config import settings

from app.api.v1 import (
    assets,
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
    cognitive,
    omnibar,
    dashboard,
    analytics,
    stt,
    focus,
    vocabulary,
    translation,
    audit,
    dlq_admin,
    health_production,
   # graph_monitor,
   # graphrag_trace,
    decay_timemachine,
    multi_agent,
    learning_paths,
    error_book,
    ingestion,
    files,
    interventions,
    events,
    nightly_reviews,
    feedback_admin,
    memory,
    memory_settings,
    memory_admin,
    preferences,
    seed_libraries,
    achievements,
    multi_intent,
    recommendations,
    leaderboards,
    monitoring,
    suggestions, # Vision Item 3
    profile_transparency,
)
from app.api.v1 import graph_monitor, graphrag_trace

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"]) # Vision Item 3
api_router.include_router(ingestion.router, prefix="/documents", tags=["ingestion"])
api_router.include_router(files.router, tags=["files"])
api_router.include_router(interventions.router, tags=["interventions"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(nightly_reviews.router, tags=["nightly_reviews"])
api_router.include_router(feedback_admin.router)
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
api_router.include_router(dlq_admin.router, tags=["DLQ"])
api_router.include_router(galaxy.router, prefix="/galaxy", tags=["galaxy"])
api_router.include_router(error_book.router) # Prefix is defined in router itself (/errors)
api_router.include_router(learning_paths.router)  # Already has prefix /learning-paths
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(statistics.router, prefix="/stats", tags=["statistics"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(capsules.router, prefix="/capsules", tags=["capsules"])
api_router.include_router(community.router, prefix="/community", tags=["community"])
api_router.include_router(cognitive.router, prefix="/cognitive", tags=["cognitive"])
api_router.include_router(omnibar.router, prefix="/omnibar", tags=["omnibar"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(stt.router, prefix="/stt", tags=["stt"])
api_router.include_router(focus.router, prefix="/focus", tags=["focus"])
api_router.include_router(vocabulary.router, prefix="/vocabulary", tags=["vocabulary"])
api_router.include_router(translation.router, prefix="/translation", tags=["translation"])
api_router.include_router(health_production.router, prefix="/health", tags=["Health"])
api_router.include_router(memory.router, tags=["memory"])
api_router.include_router(memory_settings.router, tags=["memory"])
api_router.include_router(memory_admin.router)
api_router.include_router(preferences.router)
api_router.include_router(seed_libraries.router, tags=["seed-libraries"])
api_router.include_router(achievements.router, prefix="/achievements", tags=["achievements"])
api_router.include_router(multi_intent.router, prefix="/multi-intent", tags=["multi-intent"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(leaderboards.router, prefix="/leaderboards", tags=["leaderboards"])
api_router.include_router(profile_transparency.router)
# WebSocket monitoring endpoints
api_router.include_router(monitoring.router, prefix="/ws", tags=["WebSocket Monitoring"])
if settings.ENABLE_GRAPHRAG_MONITOR_API:
    api_router.include_router(graph_monitor.router, prefix="/monitor/graph", tags=["GraphRAG"])
    api_router.include_router(graphrag_trace.router, tags=["GraphRAG Trace"])
api_router.include_router(decay_timemachine.router, tags=["Decay TimeMachine"])
api_router.include_router(multi_agent.router, tags=["Multi-Agent"])


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
            "/omnibar",
            "/dashboard",
            "/multi-intent",
            "/recommendations",
            "/leaderboards",
            "/ws",
        ],
    }
