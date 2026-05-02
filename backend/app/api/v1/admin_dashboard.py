"""
Core: infra
Phase: none
Stage: 40

Unified admin dashboard — aggregates all admin/QA/control surfaces into a single
overview. Gives reviewers and operators a one-stop view of system health, Aurora
state, kill switch modes, moderation queue, and operational metrics.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db
from app.config import settings
from app.core.cache import cache_service
from app.middleware.admin_audit import audit_admin_action
from app.models.user import User

router = APIRouter(
    prefix="/admin",
    tags=["admin-dashboard"],
    dependencies=[Depends(get_current_active_superuser)],
)

_START_TIME = time.time()


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _redis_health() -> dict[str, Any]:
    if not cache_service.redis:
        return {"status": "disabled"}
    try:
        start = time.time()
        await cache_service.redis.ping()
        latency_ms = round((time.time() - start) * 1000, 2)
        info = await cache_service.redis.info(section="memory")
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "used_memory_human": info.get("used_memory_human"),
        }
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


async def _db_health(db: AsyncSession) -> dict[str, Any]:
    try:
        start = time.time()
        await db.execute(text("SELECT 1"))
        latency_ms = round((time.time() - start) * 1000, 2)
        return {"status": "healthy", "latency_ms": latency_ms}
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


async def _user_counts(db: AsyncSession) -> dict[str, Any]:
    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar() or 0
    active_result = await db.execute(
        select(func.count(User.id)).where(User.is_active.is_(True))
    )
    active = active_result.scalar() or 0
    superuser_result = await db.execute(
        select(func.count(User.id)).where(User.is_superuser.is_(True))
    )
    return {
        "total": total,
        "active": active,
        "superusers": superuser_result.scalar() or 0,
    }


async def _kill_switch_summary() -> dict[str, Any]:
    """Aggregate all Aurora stage kill switch modes from settings."""
    stage_keys = {
        "stage18_aggregator": getattr(settings, "AURORA_STAGE18_AGGREGATOR_MODE", None),
        "stage19_working_memory": getattr(settings, "AURORA_STAGE19_WM_MODE", None),
        "stage21_skill_system": getattr(settings, "AURORA_STAGE21_SKILL_MODE", None),
        "stage23_bayesian": getattr(settings, "AURORA_BAYESIAN_MODE", None),
        "stage24_policy": getattr(settings, "AURORA_STAGE24_POLICY_MODE", None),
        "stage25_reflection": getattr(settings, "AURORA_STAGE25_REFLECTION_MODE", None),
        "stage26_scene": getattr(settings, "AURORA_STAGE26_SCENE_MODE", None),
        "stage27_foresight": getattr(settings, "AURORA_STAGE27_FORESIGHT_MODE", None),
        "stage28_traits": getattr(settings, "AURORA_STAGE28_TRAITS_MODE", None),
        "stage29_srl": getattr(settings, "AURORA_STAGE29_SRL_MODE", None),
        "stage30_metacognition": getattr(settings, "AURORA_STAGE30_METACOGNITION_MODE", None),
        "stage31_idiographic": getattr(settings, "AURORA_STAGE31_IDIOGRAPHIC_MODE", None),
        "stage33_journey": getattr(settings, "AURORA_STAGE33_JOURNEY_MODE", None),
    }
    flags: dict[str, dict[str, Any]] = {}
    live_count = 0
    shadow_count = 0
    off_count = 0
    unknown_count = 0

    for key, raw in stage_keys.items():
        mode = str(raw or "").strip().lower()
        if mode not in ("live", "shadow", "off"):
            mode = "unknown"
        flags[key] = {"mode": mode, "settings_key": key}
        if mode == "live":
            live_count += 1
        elif mode == "shadow":
            shadow_count += 1
        elif mode == "off":
            off_count += 1
        else:
            unknown_count += 1

    return {
        "flags": flags,
        "summary": {
            "total": len(flags),
            "live": live_count,
            "shadow": shadow_count,
            "off": off_count,
            "unknown": unknown_count,
        },
    }


async def _recent_telemetry_errors() -> dict[str, Any]:
    if not cache_service.redis:
        return {"available": False}
    try:
        raw_events = await cache_service.redis.lrange("client_telemetry:recent", 0, 49)
        import json

        errors: list[dict[str, Any]] = []
        for raw in raw_events:
            try:
                evt = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if evt.get("status") not in ("ok", "success"):
                errors.append(evt)
        return {
            "available": True,
            "recent_error_count": len(errors),
            "recent_errors": errors[:10],
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


async def _queue_health() -> dict[str, Any]:
    if not cache_service.redis:
        return {"available": False}
    try:
        queues = {
            "graph_sync": "queue:graph_sync",
            "summarization": "queue:summarization",
        }
        result: dict[str, dict[str, Any]] = {}
        total = 0
        for name, key in queues.items():
            length = await cache_service.redis.llen(key)
            result[name] = {"length": length, "healthy": length < 500}
            total += length
        return {"available": True, "queues": result, "total_pending": total}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


# route-tier: internal
@router.get("/dashboard")
@audit_admin_action(category="admin_dashboard", risk="medium", action="view_admin_dashboard")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Unified admin overview — system health, Aurora flags, metrics, and queues."""
    redis_h = await _redis_health()
    db_h = await _db_health(db)
    users = await _user_counts(db)
    kill_switches = await _kill_switch_summary()
    telemetry = await _recent_telemetry_errors()
    queues = await _queue_health()

    system_healthy = (
        redis_h.get("status") == "healthy"
        and db_h.get("status") == "healthy"
    )

    return {
        "generated_at": _utcnow().isoformat(),
        "system": {
            "healthy": system_healthy,
            "uptime_seconds": round(time.time() - _START_TIME, 2),
            "environment": "production" if not settings.DEBUG else "development",
            "version": getattr(settings, "APP_VERSION", "unknown"),
        },
        "components": {
            "redis": redis_h,
            "database": db_h,
        },
        "users": users,
        "aurora_kill_switches": kill_switches,
        "client_telemetry": telemetry,
        "queues": queues,
    }


# route-tier: internal
@router.get("/dashboard/kill-switches")
@audit_admin_action(category="kill_switch", risk="medium", action="audit_kill_switches")
async def admin_kill_switch_audit() -> dict[str, Any]:
    """Detailed kill switch audit — all Aurora stage modes with readiness evaluation."""
    from app.services.kill_switch_readiness_service import KillSwitchReadinessService

    svc = KillSwitchReadinessService()
    readiness = await svc.get_readiness_report(settings)

    flags = []
    for key, feature in readiness.items():
        flags.append({
            "feature": key,
            "current_mode": feature.current_mode,
            "target_mode": feature.target_mode,
            "ready_for_promotion": feature.ready_for_promotion,
            "blocking_reasons": feature.blocking_reasons,
            "promotion_criteria": feature.promotion_criteria,
            "evidence": feature.evidence,
        })

    live = sum(1 for f in flags if f["current_mode"] == "live")
    shadow = sum(1 for f in flags if f["current_mode"] == "shadow")
    off = sum(1 for f in flags if f["current_mode"] == "off")
    ready = sum(1 for f in flags if f["ready_for_promotion"])

    return {
        "generated_at": _utcnow().isoformat(),
        "summary": {
            "total": len(flags),
            "live": live,
            "shadow": shadow,
            "off": off,
            "ready_for_promotion": ready,
        },
        "flags": flags,
    }


# route-tier: internal
@router.get("/dashboard/aurora/user/{user_id}")
async def admin_inspect_aurora_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Admin inspection of a specific user's Aurora cognitive state."""
    from uuid import UUID

    from app.aurora.runtime_v1.persistence import AuroraPersistenceStore
    from app.aurora.runtime_v1.state import AuroraEnergyStore, AuroraRuntimeStore

    try:
        parsed_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user_id format",
        )

    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == parsed_id))
    user = user_result.scalar()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    redis = cache_service.redis

    # Aurora energy state
    energy = None
    if redis:
        try:
            energy_store = AuroraEnergyStore(redis)
            energy = await energy_store.load_energy(parsed_id)
        except Exception:
            pass

    # Persisted cognitive snapshot
    snapshot = None
    try:
        store = AuroraPersistenceStore(db, enabled=True)
        snapshot = await store.load_cognitive_snapshot(parsed_id)
    except Exception:
        pass

    # Runtime state (latest across surfaces)
    runtime_states = {}
    if redis:
        runtime_store = AuroraRuntimeStore(redis, enabled=True)
        for surface in ("aurora_modeling", "aurora_planning", "aurora_checkpoint"):
            try:
                state = await runtime_store.load_latest_surface_state(
                    user_id=str(parsed_id), surface=surface
                )
                if state:
                    runtime_states[surface] = {
                        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
                        "band_status": getattr(state, "band_status", None),
                        "surface": getattr(state, "surface", None),
                    }
            except Exception:
                pass

    # Recent corrections
    corrections = []
    if redis:
        try:
            raw = await redis.lrange(f"aurora:correction_telemetry:{user_id}", 0, 9)
            import json

            for item in raw:
                try:
                    corrections.append(json.loads(item))
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

    return {
        "user": {
            "id": str(user.id),
            "username": user.username,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "aurora": {
            "energy": {
                "current_level": energy.current_level if energy else "unknown",
                "is_cooling_down": energy.is_cooling_down if energy else None,
                "last_l3_at": energy.last_l3_session_at.isoformat() if energy and energy.last_l3_session_at else None,
            },
            "persisted_snapshot_available": snapshot is not None,
            "runtime_surfaces": runtime_states,
            "recent_corrections": corrections,
        },
        "generated_at": _utcnow().isoformat(),
    }


# route-tier: internal
@router.get("/dashboard/routing/user/{user_id}")
async def admin_inspect_routing_history(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Admin inspection of a specific user's routing decision history."""
    from uuid import UUID

    try:
        parsed_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user_id format",
        )

    if not cache_service.redis:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis unavailable")

    import json

    from app.signals.causal_trace_store import CausalTraceStore

    store = CausalTraceStore(cache_service.redis)
    traces = await store.get_user_traces(str(parsed_id), limit=limit)

    entries = []
    for trace in traces:
        signal_summary = None
        if trace.signal_ids:
            raw = await cache_service.redis.get(f"spine:signal:{trace.signal_ids[0]}")
            if raw:
                try:
                    signal_summary = json.loads(raw)
                except json.JSONDecodeError:
                    pass

        policy_summary = None
        if trace.policy_decision_id:
            raw = await cache_service.redis.get(f"spine:policy:{trace.policy_decision_id}")
            if raw:
                try:
                    policy_summary = json.loads(raw)
                except json.JSONDecodeError:
                    pass

        entries.append({
            "trace_id": trace.trace_id,
            "created_at": trace.created_at,
            "signal_ids": trace.signal_ids,
            "directive_ids": trace.directive_ids,
            "policy_decision_id": trace.policy_decision_id,
            "receipt_ids": trace.receipt_ids,
            "signal": signal_summary,
            "policy": policy_summary,
        })

    return {
        "user_id": user_id,
        "total_traces": len(entries),
        "traces": entries,
        "generated_at": _utcnow().isoformat(),
    }
