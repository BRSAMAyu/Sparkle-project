"""
API v1 Router
聚合所有 v1 版本的 API 路由
"""

from fastapi import APIRouter

from app.api.v1 import (
    accountability,
    achievements,
    agent_stats,
    calendar,
    analytics,
    assets,
    audit,
    auth,
    background_tasks,
    capsules,
    chat,
    client_telemetry,
    cognitive,
    community,
    dashboard,
    # graph_monitor,
    # graphrag_trace,
    decay_timemachine,
    devices,
    dlq_admin,
    error_book,
    event_bus_health,
    events,
    experiments,
    feedback_admin,
    files,
    focus,
    galaxy,
    graph_monitor,
    graphrag_trace,
    health_production,
    ingestion,
    interventions,
    inventory,
    leaderboards,
    learning_paths,
    memory,
    memory_admin,
    memory_settings,
    monitoring,
    multi_agent,
    multi_intent,
    nightly_reviews,
    notification_center,
    notifications,
    observability,
    omnibar,
    photons,
    plans,
    prediction,
    predictive_analytics,
    preferences,
    profile_transparency,
    push_interaction,
    recommendations,
    seed_libraries,
    shop,
    signals,
    statistics,
    stt,
    subjects,
    subtasks,
    suggestions,  # Vision Item 3
    tasks,
    translation,
    user_persona_batch,
    user_settings,
    users,
    visual_elements,  # Visual Element System
    vocabulary,
)
from app.config import settings

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(suggestions.router, tags=["suggestions"])  # Route already carries /suggestions
api_router.include_router(ingestion.router, prefix="/documents", tags=["ingestion"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(files.router, tags=["files"])
api_router.include_router(interventions.router, tags=["interventions"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(nightly_reviews.router, tags=["nightly_reviews"])
api_router.include_router(feedback_admin.router)
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
api_router.include_router(dlq_admin.router, tags=["DLQ"])
api_router.include_router(event_bus_health.router, prefix="/admin", tags=["Event Bus Health"])
api_router.include_router(galaxy.router, tags=["galaxy"])
api_router.include_router(error_book.router)  # Prefix is defined in router itself (/errors)
api_router.include_router(learning_paths.router)  # Already has prefix /learning-paths
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(client_telemetry.router)
api_router.include_router(signals.router)
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(subtasks.router, tags=["subtasks"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(statistics.router, prefix="/stats", tags=["statistics"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(observability.router)
api_router.include_router(capsules.router, prefix="/capsules", tags=["capsules"])
api_router.include_router(community.router, prefix="/community", tags=["community"])
api_router.include_router(cognitive.router, prefix="/cognitive", tags=["cognitive"])
api_router.include_router(omnibar.router, prefix="/omnibar", tags=["omnibar"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(background_tasks.router, prefix="/background-tasks", tags=["background_tasks"])
api_router.include_router(agent_stats.router)
api_router.include_router(assets.router)
api_router.include_router(stt.router, prefix="/stt", tags=["stt"])
api_router.include_router(focus.router, prefix="/focus", tags=["focus"])
api_router.include_router(vocabulary.router, prefix="/vocabulary", tags=["vocabulary"])
api_router.include_router(translation.router, prefix="/translation", tags=["translation"])
api_router.include_router(health_production.router, prefix="/health", tags=["Health"])
api_router.include_router(memory.router, tags=["memory"])
api_router.include_router(memory_settings.router, tags=["memory"])
api_router.include_router(memory_admin.router)
api_router.include_router(preferences.router)
api_router.include_router(push_interaction.router)
api_router.include_router(seed_libraries.router, tags=["seed-libraries"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
api_router.include_router(achievements.router, prefix="/achievements", tags=["achievements"])
api_router.include_router(multi_intent.router, prefix="/multi-intent", tags=["multi-intent"])
api_router.include_router(prediction.router, prefix="/prediction", tags=["prediction"])
api_router.include_router(predictive_analytics.router, prefix="/predictive", tags=["predictive"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(leaderboards.router, prefix="/leaderboards", tags=["leaderboards"])
api_router.include_router(profile_transparency.router)
api_router.include_router(user_settings.router)
api_router.include_router(user_persona_batch.router)
api_router.include_router(notification_center.router)
# Shop & Photon system
api_router.include_router(shop.router, prefix="/shop", tags=["shop"])
api_router.include_router(photons.router, prefix="/photons", tags=["photons"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
# Visual Element System
api_router.include_router(visual_elements.router, prefix="/visual-elements", tags=["visual-elements"])
# Device Registration (Push Notifications)
api_router.include_router(devices.router, tags=["devices"])
# WebSocket monitoring endpoints
api_router.include_router(monitoring.router, prefix="/ws", tags=["WebSocket Monitoring"])
if settings.ENABLE_GRAPHRAG_MONITOR_API:
    api_router.include_router(graph_monitor.router, prefix="/monitor/graph", tags=["GraphRAG"])
    api_router.include_router(graphrag_trace.router, tags=["GraphRAG Trace"])
api_router.include_router(decay_timemachine.router, tags=["Decay TimeMachine"])
api_router.include_router(multi_agent.router, tags=["Multi-Agent"])
# Calendar Events
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(accountability.router, prefix="/accountability", tags=["accountability"])


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
            "/calendar",
            "/statistics",
            "/subjects",
            "/errors",
            "/health",
            "/community",
            "/capsules",
            "/omnibar",
            "/dashboard",
            "/multi-intent",
            "/prediction",
            "/predictive",
            "/recommendations",
            "/leaderboards",
            "/shop",
            "/photons",
            "/inventory",
            "/ws",
        ],
    }
