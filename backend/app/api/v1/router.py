"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

API v1 Router
聚合所有 v1 版本的 API 路由
"""

import importlib.util
from pathlib import Path

from fastapi import APIRouter

from app.api.v1 import (
    accountability,
    achievements,
    admin_dashboard,
    agent_stats,
    analytics,
    assets,
    audit,
    aurora,
    aurora_status,
    auth,
    background_tasks,
    calendar,
    capsules,
    cards,
    chat,
    client_telemetry,
    cognitive,
    community,
    community_aggregates,
    community_strategy_outcomes,
    counterfactual,
    dashboard,
    data_export,
    # graph_monitor,
    # graphrag_trace,
    decay_timemachine,
    devices,
    dlq_admin,
    documents,
    error_book,
    event_bus_health,
    events,
    exam_sprint,
    executions,
    executions_admin,
    experience,
    experiments,
    feedback_admin,
    files,
    focus,
    galaxy,
    goals,
    graph_monitor,
    graphrag_trace,
    growth,
    health_production,
    ingestion,
    insights,
    interventions,
    inventory,
    leaderboards,
    learning_paths,
    learning_reports,
    marketplace,
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
    release_approvals,
    research,
    research_consent,
    safe_experiments,
    seed_libraries,
    shop,
    signals,
    simulation,
    skills,
    sources,
    statistics,
    stt,
    subjects,
    subtasks,
    suggestions,  # Vision Item 3
    tasks,
    theater,
    tool_history,
    translation,
    user_persona_batch,
    user_settings,
    users,
    visual_elements,  # Visual Element System
    vocabulary,
)
from app.config import settings

api_router = APIRouter()


def _route_key(route: object) -> tuple[str, frozenset[str]]:
    path = getattr(route, "path", "")
    methods = frozenset(getattr(route, "methods", None) or [])
    return path, methods


def _include_router_if_new(router: APIRouter) -> None:
    existing = {_route_key(route) for route in api_router.routes}
    incoming = {_route_key(route) for route in router.routes}
    if existing.isdisjoint(incoming):
        api_router.include_router(router)


def _include_experience_routers() -> None:
    """Register BFF experience routers created by parallel closeout agents."""
    experience_dir = Path(__file__).resolve().parent / "experience"
    if not experience_dir.is_dir():
        return

    for router_file in sorted(experience_dir.glob("*_router.py")):
        module_name = f"app.api.v1.experience_closeout_{router_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, router_file)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        router = getattr(module, "router", None)
        if router is not None:
            _include_router_if_new(router)


api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(data_export.router, prefix="/users", tags=["users"])
api_router.include_router(suggestions.router, tags=["suggestions"])  # Route already carries /suggestions
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(ingestion.router, prefix="/documents", tags=["ingestion"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(files.router, tags=["files"])
api_router.include_router(sources.router)
api_router.include_router(interventions.router, tags=["interventions"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(nightly_reviews.router, tags=["nightly_reviews"])
api_router.include_router(feedback_admin.router)
api_router.include_router(audit.router, tags=["Audit"])
api_router.include_router(dlq_admin.router, tags=["DLQ"])
api_router.include_router(event_bus_health.router, prefix="/admin", tags=["Event Bus Health"])
api_router.include_router(galaxy.router, tags=["galaxy"])
api_router.include_router(goals.router, prefix="/goals", tags=["goals"])
api_router.include_router(error_book.router)  # Prefix is defined in router itself (/errors)
api_router.include_router(error_book.error_book_router)  # Prefix is defined in router itself (/error-book)
api_router.include_router(learning_paths.router)  # Already has prefix /learning-paths
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(aurora.router)
api_router.include_router(client_telemetry.router)
api_router.include_router(signals.router)
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(cards.router, prefix="/cards", tags=["cards"])
api_router.include_router(executions.router)
api_router.include_router(executions_admin.router)
api_router.include_router(subtasks.router, tags=["subtasks"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(statistics.router, prefix="/stats", tags=["statistics"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(observability.router)
api_router.include_router(capsules.router, prefix="/capsules", tags=["capsules"])
api_router.include_router(community.router, prefix="/community", tags=["community"])
api_router.include_router(community_aggregates.router)
api_router.include_router(community_strategy_outcomes.router)
api_router.include_router(cognitive.router, prefix="/cognitive", tags=["cognitive"])
api_router.include_router(counterfactual.router)
api_router.include_router(omnibar.router, prefix="/omnibar", tags=["omnibar"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(growth.router, prefix="/growth", tags=["growth"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
api_router.include_router(experience.router)
_include_experience_routers()
api_router.include_router(exam_sprint.router, prefix="/exam-sprint", tags=["exam-sprint"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(background_tasks.router, prefix="/background-tasks", tags=["background_tasks"])
api_router.include_router(simulation.router)
api_router.include_router(theater.router)
api_router.include_router(learning_reports.router)
api_router.include_router(agent_stats.router)
api_router.include_router(assets.router)
api_router.include_router(stt.router, prefix="/stt", tags=["stt"])
api_router.include_router(focus.router, prefix="/focus", tags=["focus"])
api_router.include_router(tool_history.router)
api_router.include_router(vocabulary.router, prefix="/vocabulary", tags=["vocabulary"])
api_router.include_router(translation.router, prefix="/translation", tags=["translation"])
api_router.include_router(health_production.router, prefix="/health", tags=["Health"])
api_router.include_router(memory.router, tags=["memory"])
api_router.include_router(memory_settings.router, tags=["memory"])
api_router.include_router(memory_admin.router)
api_router.include_router(skills.router)
api_router.include_router(preferences.router)
api_router.include_router(research.router)
api_router.include_router(research_consent.router)
api_router.include_router(push_interaction.router)
api_router.include_router(seed_libraries.router, tags=["seed-libraries"])
api_router.include_router(marketplace.router, tags=["marketplace"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
api_router.include_router(safe_experiments.router, prefix="/safe-experiments", tags=["safe-experiments"])
api_router.include_router(achievements.router, prefix="/achievements", tags=["achievements"])
api_router.include_router(multi_intent.router, prefix="/multi-intent", tags=["multi-intent"])
api_router.include_router(prediction.router, prefix="/prediction", tags=["prediction"])
api_router.include_router(predictive_analytics.router, prefix="/predictive", tags=["predictive"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(release_approvals.router)
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
api_router.include_router(admin_dashboard.router)
api_router.include_router(aurora_status.router)


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
            "/exam-sprint",
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
