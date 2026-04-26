"""
Core: bridge
Phase: sense
Stage: 40

Aurora status endpoint -- modeling domain coverage for status awareness bar.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.aurora.runtime_v1.state import CORE_MODELING_DOMAINS
from app.core.cache import cache_service
from app.models.user import User

router = APIRouter(prefix="/aurora", tags=["aurora"])

# Domain label mapping (Chinese)
_DOMAIN_LABELS: dict[str, str] = {
    "goal": "\u76ee\u6807\u5efa\u6a21",
    "scope": "\u8303\u56f4\u5efa\u6a21",
    "baseline": "\u57fa\u7ebf\u5efa\u6a21",
    "time": "\u65f6\u95f4\u5efa\u6a21",
    "motivation": "\u52a8\u673a\u5efa\u6a21",
}


@router.get("/modeling-status")
async def get_modeling_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current Aurora modeling domain coverage for the status awareness bar.

    Reads the latest cognitive snapshot from the persistence layer (PostgreSQL)
    and derives domain coverage from informational tensions.
    """
    from app.aurora.runtime_v1.persistence import AuroraPersistenceStore

    redis_client = cache_service.redis

    domains: dict[str, dict[str, str | bool]] = {}
    modeling_complete = False
    aurora_active = False

    # Initialise every core domain to "missing" so the response is always
    # well-formed even when Aurora has never run for this user.
    for domain in CORE_MODELING_DOMAINS:
        domains[domain] = {
            "label": _DOMAIN_LABELS.get(domain, domain),
            "status": "missing",
            "has_tension": False,
        }

    persistence = AuroraPersistenceStore(db)
    try:
        snapshot = await persistence.load_cognitive_snapshot(user_id=current_user.id)
    except Exception:
        snapshot = None

    if snapshot is not None:
        aurora_active = True

        # Derive coverage from informational tensions -- a domain with at
        # least one tension (any status) is considered "covered" because it
        # means Aurora has observed and modelled that aspect.
        covered: set[str] = set()
        tensions = snapshot.informational_tensions or []
        for t in tensions:
            domain_name = getattr(t, "domain", None)
            if domain_name:
                covered.add(domain_name)

        for domain in CORE_MODELING_DOMAINS:
            is_covered = domain in covered
            domains[domain] = {
                "label": _DOMAIN_LABELS.get(domain, domain),
                "status": "covered" if is_covered else "missing",
                "has_tension": any(
                    getattr(t, "domain", None) == domain for t in tensions
                ),
            }

        modeling_complete = len(covered) >= 4

    # As a secondary source, try to load the latest runtime state from Redis
    # (fresher, per-conversation).  This augments -- never overwrites --
    # persistence data.
    if redis_client is not None:
        try:
            from app.aurora.runtime_v1.state import AuroraRuntimeStore

            store = AuroraRuntimeStore(redis_client)
            # Try the modeling surface first, then fall back to any surface.
            for surface in ("aurora_modeling", "aurora_planning", "aurora_checkpoint"):
                runtime_state = await store.load_latest_surface_state(
                    user_id=str(current_user.id),
                    surface=surface,
                )
                if runtime_state is not None:
                    if not aurora_active:
                        aurora_active = True
                    rt_tensions = runtime_state.informational_tensions or []
                    for t in rt_tensions:
                        d = getattr(t, "domain", None)
                        if d and domains.get(d, {}).get("status") == "missing":
                            domains[d] = {
                                "label": _DOMAIN_LABELS.get(d, d),
                                "status": "covered",
                                "has_tension": any(
                                    getattr(tt, "domain", None) == d
                                    for tt in rt_tensions
                                ),
                            }
                    break  # first hit is enough
        except Exception:
            pass

    return {
        "aurora_active": aurora_active,
        "modeling_complete": modeling_complete,
        "domains": domains,
    }
