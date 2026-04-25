from __future__ import annotations

__all__: list[str] = []


def _export(*names: str) -> None:
    __all__.extend(names)


try:
    from app.aurora.runtime_v1.control_surface import (
        AuroraHardBounds,
        ControlSurfaceReading,
        ControlSurfaceService,
        DndWindow,
        HarnessUpdateRejectedError,
    )

    _export(
        "AuroraHardBounds",
        "ControlSurfaceReading",
        "ControlSurfaceService",
        "DndWindow",
        "HarnessUpdateRejectedError",
    )
except ModuleNotFoundError:
    pass

try:
    from app.aurora.runtime_v1.state import (
        ActivityProfile,
        AuroraCognitiveSnapshot,
        AuroraIntent,
        AuroraRuntimeMetadata,
        AuroraRuntimeStore,
        AuroraState,
        InformationalTension,
        LatentThread,
        ScheduledWake,
        build_aurora_runtime_metadata,
    )

    _export(
        "ActivityProfile",
        "AuroraCognitiveSnapshot",
        "AuroraIntent",
        "AuroraRuntimeMetadata",
        "AuroraRuntimeStore",
        "AuroraState",
        "InformationalTension",
        "LatentThread",
        "ScheduledWake",
        "build_aurora_runtime_metadata",
    )
except ModuleNotFoundError:
    pass

try:
    from app.aurora.runtime_v1.skills import AuroraSkillRegistry, SkillAffordance

    _export("AuroraSkillRegistry", "SkillAffordance")
except ModuleNotFoundError:
    pass

try:
    from app.aurora.runtime_v1.persistence import (
        AuroraPersistenceStore,
        AuroraScheduledWakeRecord,
        AuroraStateSnapshotRecord,
        PersistedScheduledWake,
    )

    _export(
        "AuroraPersistenceStore",
        "AuroraScheduledWakeRecord",
        "AuroraStateSnapshotRecord",
        "PersistedScheduledWake",
    )
except ModuleNotFoundError:
    pass

try:
    from app.aurora.runtime_v1.wake_scheduler import AuroraWakeScheduler

    _export("AuroraWakeScheduler")
except ModuleNotFoundError:
    pass

try:
    from app.aurora.runtime_v1.checkpoint_runtime import (
        AURORA_CHECKPOINT_SURFACE,
        AuroraCheckpointRuntimeService,
        build_aurora_surface_metadata,
    )

    _export(
        "AURORA_CHECKPOINT_SURFACE",
        "AuroraCheckpointRuntimeService",
        "build_aurora_surface_metadata",
    )
except ModuleNotFoundError:
    pass

try:
    from app.aurora.runtime_v1.planning import (
        AURORA_PLANNING_SURFACE,
        AuroraActivityProfile,
        AuroraLatentThread,
        AuroraRuntimePlanningAdapter,
        AuroraRuntimePlanningState,
        AuroraTension,
    )

    _export(
        "AURORA_PLANNING_SURFACE",
        "AuroraActivityProfile",
        "AuroraLatentThread",
        "AuroraRuntimePlanningAdapter",
        "AuroraRuntimePlanningState",
        "AuroraTension",
    )
except ModuleNotFoundError:
    pass

from app.aurora.runtime_v1.service import (
    AURORA_RUNTIME_MODE_SURFACES,
    AURORA_RUNTIME_STATE_KEY_TEMPLATE,
    AURORA_RUNTIME_STATE_TTL_SECONDS,
    AURORA_SURFACE_MODELING,
    AuroraRuntimeTurnPlan,
    AuroraRuntimeV1Service,
)
from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.dashboard import (
    CORE_MODELING_DOMAINS,
    DashboardReadout,
    DashboardReadoutBuilder,
    canonicalize_runtime_domain,
)
from app.aurora.runtime_v1.decision_loop import AuroraDecision, AuroraDecisionLoop

_export(
    "AURORA_RUNTIME_MODE_SURFACES",
    "AURORA_RUNTIME_STATE_KEY_TEMPLATE",
    "AURORA_RUNTIME_STATE_TTL_SECONDS",
    "AURORA_SURFACE_MODELING",
    "AuroraDecision",
    "AuroraDecisionLoop",
    "ChatLayerAdapter",
    "CORE_MODELING_DOMAINS",
    "DashboardReadout",
    "DashboardReadoutBuilder",
    "AuroraRuntimeTurnPlan",
    "AuroraRuntimeV1Service",
    "canonicalize_runtime_domain",
)
