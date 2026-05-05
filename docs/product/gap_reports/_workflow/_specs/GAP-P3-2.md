# GAP-P3-2: FatigueGuard Independent Service

> **Source**: STAB-010 (Stability Layer Audit)
> **Date**: 2026-05-06
> **Author**: Claude Opus Plan Agent
> **Level**: L3 (Cross-Boundary — Python backend service)
> **Effort**: M (3-5 days)
> **Status**: Draft

---

## 1. Objectives

### 1.1 Why This Exists

Fatigue signal detection is currently scattered across 15+ locations in the codebase with no unified service:

- `SpineOrchestrator.check_fatigue()` (line 3904) — inline method, not a standalone service
- `SpineOrchestrator._detect_affective_pressure()` (line 4037) — generates `burnout_risk` signal but lives inside orchestrator
- `DualCoreRouter` (line 431) — reads spine states for `fatigue_accumulated` / `affective_pressure` / `cognitive_load` / `notification_fatigue`
- `orchestrator_production.py` (line 1128) — fetches `spine:fatigue:{user_id}:latest` from Redis directly
- `orchestrator.py` (line 2425) — calls `_spine.check_fatigue()` inline
- `domain_pack.py` — `burnout` risk patterns hardcoded per domain
- `policy_engine.py` — `burnout_risk` strategy mapped to `prevent_burnout`
- `policy_experiments.py` — `prevent_burnout` shadow experiment
- `safe_experiment_platform.py` — fatigue guardrail as experiment safety check
- `crisis_mode_fsm.py` — fatigue as crisis trigger input
- `recall_opportunity.py` — gates on `current_fatigue > 0.7`
- `intervention_episode.py` — fatigue as guardrail metric
- `prompts.py` — fatigue context modulates tone
- `residual_diagnosis.py` — fatigue keyword matching
- `scaffolding/intent_generator.py` — fatigue -> suggest_break mapping

This fragmentation causes three concrete problems:

1. **No single source of truth for fatigue state** — Each consumer reads from different places (spine states, Redis keys, method calls) with no consistency guarantee.
2. **Missing detection dimensions** — High-frequency use (>50 msgs/day), declining accuracy trends, and repeated help-seeking patterns are not implemented as triggers.
3. **No observability** — Fatigue detection has zero Prometheus metrics. Cannot monitor how often fatigue states fire, what levels, or what responses they trigger.

### 1.2 Goals

- Create a standalone `FatigueGuard` service class that consolidates all fatigue signal detection
- Add 3 missing detection dimensions: high-frequency use, declining accuracy, repeated help-seeking
- Expose unified Redis-backed state for all consumers
- Add full Prometheus observability
- Provide Celery tasks for background decay and batch evaluation
- Wire into existing consumers without breaking current behavior
- Add comprehensive tests

### 1.3 Non-Goals

- **Not changing the DualCoreRouter's fatigue routing logic** — only changing _how_ it reads fatigue signals
- **Not changing the prompt templates** — only the context data structure passed to them
- **Not adding a new database table** — Fatigue is ephemeral state (Redis only, scoped to session/day)
- **Not building a UI component** — Backend-only service

---

## 2. Current State Assessment

### 2.1 Existing `check_fatigue()` Method

Located at `backend/app/signals/spine_orchestrator.py` lines 3904-3959. Takes parameters:

```python
async def check_fatigue(
    self,
    *,
    user_id: str,
    interactions_last_24h: int = 0,
    consecutive_hours: float = 0.0,
    accuracy_trend: list[float] | None = None,
    is_late_night: bool = False,
) -> dict[str, Any]:
```

Returns dict with: `fatigue_level` (low|medium|high|critical), `evidence`, `recommended_policy`, `hard_constraints`.

**Thresholds (hardcoded)**:
- 15+ interactions/24h -> medium
- 30+ interactions/24h -> high
- 4+ consecutive hours -> high (or critical if already high)
- 3+ declining accuracy -> medium
- Late night -> medium
- Accuracy only checked if `len(accuracy_trend) >= 3` and all decreasing

### 2.2 Existing `_detect_affective_pressure()` Method

Located at lines 4037-4075. Generates `ActionableSignal` for `affective_pressure` state key. Triggers:
- 2+ consecutive abandons
- Error density > 0.6
- Late night study
- Streak broken

Generates `burnout_risk` claim when 3+ consecutive abandons or deadline <= 2 days with 2+ triggers.

### 2.3 Existing Consumers (7 call sites)

| Consumer | File | How It Reads Fatigue |
|----------|------|---------------------|
| `SpineOrchestrator._enrich_pipeline_post_policy` | `spine_orchestrator.py:3080-3095` | Gets interaction count from Redis, calls `check_fatigue()`, stores to `spine:fatigue:{user_id}:latest` with 6h TTL |
| `orchestrator.py` (v1 FSM) | `orchestrator.py:2425-2439` | Calls `_spine.check_fatigue()`, passes as `spine_fatigue_context` into request_extra_context |
| `orchestrator_production.py` (v2) | `orchestrator_production.py:1128-1141` | Reads `spine:fatigue:{user_id}:latest` Redis key directly |
| `DualCoreRouter.route()` | `dual_core_router.py:431-450` | Reads from `routing_input.spine_active_states` for fatigue keys |
| `build_system_prompt()` | `prompts.py:1634-1651` | Receives `spine_fatigue_context` dict, injects tone guidance |
| `_detect_affective_pressure()` | `spine_orchestrator.py:4037-4075` | Called during pipeline, writes `affective_pressure` to StateRegister |
| `PolicyEngine.evaluate()` | `policy_engine.py:762-764` | Fatigue beats all other signals in precedence |

### 2.4 Existing Redis Keys

| Key Pattern | TTL | Created By |
|-------------|-----|-----------|
| `spine:interaction_count:{user_id}:24h` | 24h (set on first incr) | `spine_orchestrator.py:1277` |
| `spine:fatigue:{user_id}:latest` | 6h | `spine_orchestrator.py:3089-3093` |
| `spine:fatigue:{user_id}:history` | N/A | _Does not exist yet_ |

### 2.5 Existing Tests

Located in `backend/tests/unit/test_signal_spine.py`:

| Test | Lines | What It Covers |
|------|-------|---------------|
| `test_fatigue_guard_low` | 9352-9365 | Low fatigue level with normal usage (5 interactions, 1h) |
| `test_fatigue_guard_critical` | 9368-9383 | Critical fatigue (40 interactions, 6h, declining accuracy, late night) |
| `test_pipeline_fatigue_detection_on_task_completion` | 9470-9492 | Pipeline integration: interaction counter -> fatigue check -> Redis storage |
| `test_fatigue_levels_correct` | 9520-9545 | All levels (low, medium, high) produce correct policy mapping |
| `test_fatigue_injects_into_prompt` | 10269-10277 | Fatigue context modulates system prompt |
| `test_crisis_injects_into_prompt` | 10279-10287 | Crisis context modulates system prompt |

### 2.6 Existing Fatigue-Linked Configuration

| File | Key | Value |
|------|-----|-------|
| `settings.py:586` | `NEXT_STEP_FATIGUE_HIGH_THRESHOLD` | 1.5 |
| `settings.py:587` | `NEXT_STEP_FATIGUE_EXTREME_THRESHOLD` | 2.0 |
| `routing_parameter_registry.py:45` | `spine_fatigue` precedence weight | 4.0 |
| `routing_parameter_registry.py:60` | `spine_fatigue_confidence_min` | 0.6 |

### 2.7 Gap Details from STAB-010

1. **No dedicated FatigueGuard class** — Fatigue is a method on SpineOrchestrator (4449 lines), not a standalone service
2. **High-frequency use detection** (>50 messages/day) not explicitly implemented as a fatigue trigger
3. **Declining accuracy detection** — exists in `check_fatigue()` but only fires on 3+ consecutive decreases; no help-seeking pattern detection
4. **Repeated help-seeking** pattern detection is not implemented anywhere

---

## 3. File Inventory

### Files to Create

| File | Purpose |
|------|---------|
| `backend/app/signals/fatigue_guard.py` | New FatigueGuard service class |
| `backend/app/tests/unit/signals/test_fatigue_guard.py` | Dedicated test file for FatigueGuard (move from test_signal_spine.py) |

### Files to Modify

| File | Change Description |
|------|-------------------|
| `backend/app/signals/spine_orchestrator.py` | Extract `check_fatigue()`, `_detect_affective_pressure()`, interaction counter logic. Delegate to FatigueGuard. Keep thin wrapper for backward compat. |
| `backend/app/signals/__init__.py` | Add `FatigueGuard` to exports |
| `backend/app/orchestration/orchestrator.py` | Replace `_spine.check_fatigue()` with `FatigueGuard` call |
| `backend/app/orchestration/orchestrator_production.py` | Replace direct Redis read with `FatigueGuard` method |
| `backend/app/orchestration/dual_core_router.py` | No change needed if signal format is backward-compatible (read from spine states already) |
| `backend/app/core/celery_schedule.py` | Add fatigue decay/scan periodic task |
| `backend/app/core/celery_tasks.py` | Add `scan_fatigue_states` batch task |
| `backend/app/core/metrics.py` | Add fatigue Prometheus metrics |
| `backend/app/config/settings.py` | Add FatigueGuard configuration constants |
| `backend/tests/unit/test_signal_spine.py` | Remove migrated fatigue tests (or keep as integration) |

### Files Not Modified (Consumers That Don't Change)

| File | Reason |
|------|--------|
| `prompts.py` | Receives same dict structure; no change needed |
| `dual_core_router.py` | Reads from spine states list; no change if state keys stay same |
| `policy_engine.py` | Already handles burnout_risk signal; no change |
| `domain_pack.py` | Risk patterns are domain metadata, not detection logic |
| `crisis_mode_fsm.py` | Receives fatigue level as string; interface unchanged |
| `recall_opportunity.py` | Gates on `current_fatigue` float; interface unchanged |
| `safe_experiment_platform.py` | Computes fatigue rate from outcomes independently |
| `intervention_episode.py` | Fatigue guardrail is experiment-scoped, unrelated |

---

## 4. Implementation Steps

### Phase 1: Create FatigueGuard Service Class

**Step 1.1 — Define configuration and types**

Create `backend/app/signals/fatigue_guard.py` with the following structure:

```python
"""
Core: execution
Phase: sense
Stage: GAP-P3-2 FatigueGuard Independent Service

FatigueGuard — 疲劳信号统一检测服务。
Consolidates all fatigue signal detection, tracking, and response.

Users see: break suggestions, shorter tasks, lower-pressure tone when fatigued.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from loguru import logger
from prometheus_client import Counter, Gauge, Histogram

from app.core.metrics import get_or_create_metric
from app.signals.types import ActionableSignal, _uid


class FatigueLevel(str, Enum):
    NORMAL = "normal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FatigueDimension(str, Enum):
    INTERACTION_VOLUME = "interaction_volume"          # msgs/24h
    CONSECUTIVE_USAGE = "consecutive_usage"             # hours without break
    ACCURACY_DECLINE = "accuracy_decline"               # diminishing task success
    REPEATED_HELP_SEEKING = "repeated_help_seeking"     # repeated "I'm stuck/tired"
    LATE_NIGHT = "late_night"                           # usage during quiet hours
    ABANDON_STREAK = "abandon_streak"                   # consecutive task abandons
    HIGH_ERROR_DENSITY = "high_error_density"            # error_rate > threshold


@dataclass
class FatigueSignal:
    """Structured fatigue signal output."""
    user_id: str
    fatigue_level: FatigueLevel
    dimensions_triggered: list[FatigueDimension]
    evidence: list[str]
    recommended_policy: str
    hard_constraints: dict[str, Any]
    confidence: float
    detected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    signal_id: str = field(default_factory=lambda: _uid("fg"))


# Default thresholds (overridable via settings)
_DEFAULT_INTERACTION_THRESHOLDS = {
    "high": 30,    # >= 30 interactions/24h -> high
    "medium": 15,  # >= 15 interactions/24h -> medium
}

_DEFAULT_CONSECUTIVE_HOURS_THRESHOLD = 4  # >= 4h -> elevate

_DEFAULT_ACCURACY_DECLINE_WINDOW = 3      # check last N tasks
_DEFAULT_HELP_SEEKING_WINDOW = 5           # check last N messages
_DEFAULT_HELP_SEEKING_RATIO = 0.4          # >= 40% help-seeking -> detect

# Redis keys
_REDIS_FATIGUE_LATEST = "fg:fatigue:{user_id}:latest"
_REDIS_FATIGUE_HISTORY = "fg:fatigue:{user_id}:history"
_REDIS_INTERACTION_COUNT = "fg:interaction_count:{user_id}:24h"
_REDIS_HELP_SEEKING_COUNT = "fg:help_seeking:{user_id}:recent"
_REDIS_CONSECUTIVE_TRACKER = "fg:consecutive:{user_id}:tracker"

# TTLs
_LATEST_TTL = 6 * 3600            # 6 hours
_HISTORY_TTL = 7 * 24 * 3600      # 7 days
_HISTORY_MAX = 50                  # max history entries
_INTERACTION_TTL = 24 * 3600      # 24 hours
_CONSECUTIVE_IDLE_TTL = 2 * 3600  # 2 hours without activity resets
```

**Step 1.2 — Implement core detection methods**

```python
class FatigueGuard:
    """独立疲劳信号检测服务。

    Replaces SpineOrchestrator.check_fatigue() and
    SpineOrchestrator._detect_affective_pressure().
    """

    def __init__(
        self,
        redis_client: Any,
        interaction_threshold_high: int = _DEFAULT_INTERACTION_THRESHOLDS["high"],
        interaction_threshold_medium: int = _DEFAULT_INTERACTION_THRESHOLDS["medium"],
        consecutive_hours_threshold: float = _DEFAULT_CONSECUTIVE_HOURS_THRESHOLD,
        accuracy_decline_window: int = _DEFAULT_ACCURACY_DECLINE_WINDOW,
        help_seeking_window: int = _DEFAULT_HELP_SEEKING_WINDOW,
        help_seeking_ratio: float = _DEFAULT_HELP_SEEKING_RATIO,
    ):
        self.redis = redis_client
        self._interaction_high = interaction_threshold_high
        self._interaction_medium = interaction_threshold_medium
        self._consecutive_hours = consecutive_hours_threshold
        self._accuracy_window = accuracy_decline_window
        self._help_window = help_seeking_window
        self._help_ratio = help_seeking_ratio

    async def detect(
        self,
        *,
        user_id: str,
        interactions_last_24h: int | None = None,
        consecutive_hours: float | None = None,
        accuracy_trend: list[float] | None = None,
        is_late_night: bool = False,
        consecutive_abandons: int = 0,
        error_density: float = 0.0,
        streak_broken: bool = False,
        recent_messages: list[str] | None = None,
    ) -> FatigueSignal:
```

Method should:
1. Check all 7 dimensions against thresholds
2. Combine into a single fatigue level (highest triggered dimension wins)
3. Generate evidence list for audit trail
4. Return `FatigueSignal` with policy recommendations

**Step 1.3 — Implement dimension detection methods**

Each dimension should be a private method:

- `_check_interaction_volume(count)` -> (level_contribution, evidence)
- `_check_consecutive_usage(hours)` -> (level_contribution, evidence)
- `_check_accuracy_decline(trend)` -> (level_contribution, evidence)
- `_check_repeated_help_seeking(messages)` -> (level_contribution, evidence)
- `_check_late_night(is_late_night)` -> (level_contribution, evidence)
- `_check_abandon_streak(count)` -> (level_contribution, evidence)
- `_check_error_density(density)` -> (level_contribution, evidence)

Level combination algorithm:
- Each dimension returns `(delta: int, evidence: str)` where delta is 0-3 (none to critical)
- Final level = max of all dimension deltas, clamped to FatigueLevel range
- Hard constraints are additive across dimensions

**Step 1.4 — Implement Redis persistence and retrieval**

```python
    async def save_fatigue_state(self, user_id: str, signal: FatigueSignal) -> None:
        """Save latest fatigue state + append to history."""
        payload = {
            "fatigue_level": signal.fatigue_level.value,
            "dimensions": [d.value for d in signal.dimensions_triggered],
            "evidence": signal.evidence,
            "recommended_policy": signal.recommended_policy,
            "hard_constraints": signal.hard_constraints,
            "confidence": signal.confidence,
            "detected_at": signal.detected_at,
        }
        # Latest state (consumed by orchestrator, dual_core_router)
        await self.redis.set(
            _REDIS_FATIGUE_LATEST.format(user_id=user_id),
            json.dumps(payload),
            ex=_LATEST_TTL,
        )
        # History for trend analysis
        history_key = _REDIS_FATIGUE_HISTORY.format(user_id=user_id)
        await self.redis.lpush(history_key, json.dumps(payload))
        await self.redis.ltrim(history_key, 0, _HISTORY_MAX - 1)
        await self.redis.expire(history_key, _HISTORY_TTL)

    async def get_latest_fatigue(
        self, user_id: str
    ) -> dict[str, Any] | None:
        """Get latest fatigue state for a user."""
        raw = await self.redis.get(_REDIS_FATIGUE_LATEST.format(user_id=user_id))
        if raw:
            return json.loads(raw if isinstance(raw, str) else raw.decode())
        return None
    
    async def get_fatigue_history(
        self, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get recent fatigue history for trend analysis."""
        raw_list = await self.redis.lrange(
            _REDIS_FATIGUE_HISTORY.format(user_id=user_id), 0, limit - 1
        )
        return [
            json.loads(r if isinstance(r, str) else r.decode()) for r in raw_list
            if r
        ]
```

**Step 1.5 — Implement interaction tracking**

```python
    async def record_interaction(self, user_id: str) -> int:
        """Increment 24h interaction counter. Returns current count."""
        key = _REDIS_INTERACTION_COUNT.format(user_id=user_id)
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, _INTERACTION_TTL)
        return count

    async def get_interaction_count(self, user_id: str) -> int:
        """Get current 24h interaction count."""
        raw = await self.redis.get(_REDIS_INTERACTION_COUNT.format(user_id=user_id))
        return int(raw) if raw else 0
```

**Step 1.6 — Implement help-seeking detection**

```python
    async def record_message(self, user_id: str, message: str) -> None:
        """Record user message for help-seeking pattern detection."""
        key = _REDIS_HELP_SEEKING_COUNT.format(user_id=user_id)
        entry = json.dumps({"text": message[:200], "ts": datetime.now(UTC).isoformat()})
        await self.redis.lpush(key, entry)
        await self.redis.ltrim(key, 0, _HELP_SEEKING_WINDOW * 2)
        await self.redis.expire(key, _INTERACTION_TTL)
    
    async def _check_repeated_help_seeking(
        self, user_id: str
    ) -> tuple[int, str | None]:
        """Check if user is repeatedly seeking help (fatigue signal)."""
        key = _REDIS_HELP_SEEKING_COUNT.format(user_id=user_id)
        raw_list = await self.redis.lrange(key, 0, _HELP_SEEKING_WINDOW - 1)
        if not raw_list:
            return 0, None
        
        decoded = []
        for r in raw_list:
            try:
                decoded.append(json.loads(r if isinstance(r, str) else r.decode()))
            except (json.JSONDecodeError, TypeError):
                continue
        
        if len(decoded) < 3:
            return 0, None
        
        # Check for fatigue/help-seeking keywords in recent messages
        fatigue_keywords = {
            "tired", "exhausted", "burnout", "overwhelmed", "stuck",
            "too hard", "too much", "can't", "cannot", "help",
            "累", "疲劳", "扛不住", "坚持不下去", "太难",
        }
        help_seeking_count = sum(
            1 for entry in decoded
            if any(kw in entry.get("text", "").lower() for kw in fatigue_keywords)
        )
        ratio = help_seeking_count / len(decoded)
        if ratio >= self._help_ratio:
            return 2, f"Detected {help_seeking_count}/{len(decoded)} recent messages with help-seeking/fatigue markers"
        return 0, None
```

**Step 1.7 — Implement backward-compatible wrapper**

```python
    async def to_actionable_signal(
        self, user_id: str, signal: FatigueSignal
    ) -> ActionableSignal:
        """Convert FatigueSignal to ActionableSignal for the spine pipeline."""
        return ActionableSignal(
            signal_id=signal.signal_id,
            source_event_ids=[f"fg:{user_id}"],
            source_system="fatigue_guard",
            state_key="fatigue_accumulated",
            claim=signal.fatigue_level.value,
            confidence=signal.confidence,
            scope="session",
            ttl_hours=_LATEST_TTL // 3600,
            evidence_summary="; ".join(signal.evidence),
            possible_effects=(
                ["suggest_break", "reduce_load"]
                if signal.fatigue_level in (FatigueLevel.HIGH, FatigueLevel.CRITICAL)
                else ["reduce_pace", "monitor"]
            ),
            priority="high" if signal.fatigue_level in (FatigueLevel.HIGH, FatigueLevel.CRITICAL) else "medium",
        )
    
    async def to_context_dict(self, user_id: str) -> dict[str, Any] | None:
        """Backward-compatible dict for prompt injection. Replaces direct Redis read.
        
        Returns same shape as old SpineOrchestrator.check_fatigue().
        """
        latest = await self.get_latest_fatigue(user_id)
        if not latest:
            return None
        return {
            "fatigue_level": latest["fatigue_level"],
            "evidence": latest["evidence"],
            "recommended_policy": latest.get("recommended_policy", "normal"),
            "hard_constraints": latest.get("hard_constraints", {}),
        }
```

### Phase 2: Add Observability

**Step 2.1 — Add Prometheus metrics**

Add to `backend/app/core/metrics.py`:

```python
# GAP-P3-2: FatigueGuard metrics
FATIGUE_DETECTED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_fatigue_detected_total",
    "Total fatigue detections by level",
    ["level"],
)

FATIGUE_CURRENT_LEVEL = get_or_create_metric(
    Gauge,
    "sparkle_fatigue_current_level",
    "Current fatigue level per user (0=normal, 1=low, 2=medium, 3=high, 4=critical)",
    ["user_id"],
)

FATIGUE_DIMENSION_TRIGGERED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_fatigue_dimension_triggered_total",
    "Total fatigue dimension triggers",
    ["dimension"],
)

FATIGUE_DETECTION_DURATION = get_or_create_metric(
    Histogram,
    "sparkle_fatigue_detection_duration_seconds",
    "Fatigue detection latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
)
```

**Step 2.2 — Emit metrics from detect()**

```python
import time
from app.core.metrics import (
    FATIGUE_DETECTED_TOTAL,
    FATIGUE_CURRENT_LEVEL,
    FATIGUE_DIMENSION_TRIGGERED_TOTAL,
    FATIGUE_DETECTION_DURATION,
)

# Inside FatigueGuard.detect():
start = time.monotonic()
try:
    # ... detection logic ...
    return signal
finally:
    duration = time.monotonic() - start
    FATIGUE_DETECTION_DURATION.observe(duration)
    
# After computing level:
level_map = {"normal": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
FATIGUE_CURRENT_LEVEL.labels(user_id=user_id).set(level_map[final_level])
FATIGUE_DETECTED_TOTAL.labels(level=final_level).inc()

# For each triggered dimension:
for dim in dimensions_triggered:
    FATIGUE_DIMENSION_TRIGGERED_TOTAL.labels(dimension=dim.value).inc()
```

WARNING: The Gauge with `user_id` label risks cardinality explosion. Use a summary/gauge without user_id for aggregate level tracking, and only use the labeled gauge in `FATIGUE_DETECTED_TOTAL` counter (which is bounded by fatigue levels, not user IDs). Remove the `user_id` label from `FATIGUE_CURRENT_LEVEL` or use it only in debug mode.

**Design Decision** (per feedback from rubric): Remove `user_id` label from Prometheus gauges to prevent cardinality explosion. Use `fatigue_level` as label instead:

```python
FATIGUE_CURRENT_LEVEL = get_or_create_metric(
    Gauge,
    "sparkle_fatigue_current_level",
    "Current count of users at each fatigue level (0=normal, ..., 4=critical)",
    ["level"],
)
```

### Phase 3: Wire FatigueGuard into Consumers

**Step 3.1 — Replace in `SpineOrchestrator`**

Modify `SpineOrchestrator.__init__` to accept an optional `FatigueGuard` instance:

```python
from app.signals.fatigue_guard import FatigueGuard

class SpineOrchestrator:
    def __init__(self, redis_client: Any, fatigue_guard: FatigueGuard | None = None):
        self.redis = redis_client
        self.fatigue_guard = fatigue_guard or FatigueGuard(redis_client)
        # ... existing init ...
```

Replace the interaction counter logic (lines 1275-1283):
```python
# STAB-006 interaction counter → delegated to FatigueGuard
try:
    _count = await self.fatigue_guard.record_interaction(str(user_id))
except Exception as _count_err:
    _ce = classify_error(_count_err, component="fatigue_guard_interaction_counter", ...)
```

Replace pipeline fatigue check (lines 3080-3095):
```python
# 6. fatigue check via FatigueGuard
try:
    interaction_count = await self.fatigue_guard.get_interaction_count(str(user_id))
    fatigue = await self.fatigue_guard.detect(
        user_id=str(user_id),
        interactions_last_24h=interaction_count,
    )
    if fatigue.fatigue_level in (FatigueLevel.HIGH, FatigueLevel.CRITICAL):
        await self.fatigue_guard.save_fatigue_state(str(user_id), fatigue)
        
        # Also generate ActionableSignal for spine pipeline
        signal = await self.fatigue_guard.to_actionable_signal(str(user_id), fatigue)
        # ... existing signal handling ...
except Exception:
    logger.warning("FatigueGuard check failed", exc_info=True)
```

Replace `check_fatigue()` method (lines 3904-3959) with thin delegation:
```python
async def check_fatigue(self, user_id: str, **kwargs) -> dict[str, Any]:
    """Delegated to FatigueGuard. Kept for backward compatibility."""
    signal = await self.fatigue_guard.detect(user_id=user_id, **kwargs)
    return {
        "fatigue_level": signal.fatigue_level.value,
        "evidence": signal.evidence,
        "recommended_policy": signal.recommended_policy,
        "hard_constraints": signal.hard_constraints,
    }
```

**Step 3.2 — Replace in `orchestrator_production.py`**

Replace the direct Redis read (lines 1128-1141):
```python
# Fatigue + crisis → inject tone modulation (via FatigueGuard)
try:
    fg = FatigueGuard(self.redis)
    fatigue_ctx = await fg.to_context_dict(str(user_id))
    if fatigue_ctx:
        _spine_fatigue_context = fatigue_ctx
    _crisis_raw = await self.redis.get(f"spine:crisis:{user_id}:latest")
    if _crisis_raw:
        if not _spine_fatigue_context:
            _spine_fatigue_context = {}
        _spine_fatigue_context["crisis_mode"] = True
except Exception as exc:
    logger.debug("FatigueGuard context enrichment skipped for user={}: {}", user_id, exc)
```

**Step 3.3 — Replace in `orchestrator.py`**

Replace the inline `_spine.check_fatigue()` call (lines 2425-2439):
```python
# Track interaction count for fatigue detection
_fatigue = None
try:
    fg = FatigueGuard(_redis_client)
    await fg.record_interaction(str(user_id))
    _fatigue_signal = await fg.detect(user_id=str(user_id))
    if _fatigue_signal.fatigue_level in (FatigueLevel.HIGH, FatigueLevel.CRITICAL, FatigueLevel.MEDIUM):
        _fatigue = await fg.to_context_dict(str(user_id))
        request_extra_context["spine_fatigue_context"] = _fatigue
except Exception:
    logger.warning("FatigueGuard check failed", exc_info=True)
```

### Phase 4: Add Celery Tasks

**Step 4.1 — Add batch decay task**

Add to `backend/app/core/celery_tasks.py`:

```python
def scan_fatigue_decay(self, limit: int = 500):
    """Scan for stale fatigue states and apply decay."""
    async def _run():
        # Find active fatigue states by scanning Redis keys
        # For each user: if latest fatigue older than 4h and level > low,
        #   apply one-step decay (critical->high, high->medium, medium->low)
        #   and re-save
        pass
    return _run()
```

**Step 4.2 — Register in celery_schedule.py**

```python
# GAP-P3-2: FatigueGuard decay scan — every 6 hours
from app.core.celery_tasks import scan_fatigue_decay
sender.add_periodic_task(
    21600.0,
    scan_fatigue_decay.s(),
    name='scan-fatigue-decay-every-6h'
)
```

### Phase 5: Update SpineOrchestrator._detect_affective_pressure()

**Step 5.1 — Extract to FatigueGuard**

Add the affective pressure dimension to FatigueGuard:
```python
async def _check_affective_pressure(
    self,
    consecutive_abandons: int,
    error_density: float,
    is_late_night: bool,
    streak_broken: bool,
    days_to_deadline: int | None = None,
) -> tuple[int, str | None]:
    """Detect emotional/affective pressure. Returns (delta, evidence)."""
    triggers = []
    if consecutive_abandons >= 2:
        triggers.append("consecutive_abandonment")
    if error_density > 0.6:
        triggers.append("high_error_density")
    if is_late_night:
        triggers.append("late_night_study")
    if streak_broken:
        triggers.append("streak_broken")
    if not triggers:
        return 0, None
    
    # burnout_risk = 3+ abandons OR deadline <= 2 days with 2+ triggers
    is_burnout = consecutive_abandons >= 3 or (
        days_to_deadline is not None and days_to_deadline <= 2 and len(triggers) >= 2
    )
    delta = 3 if is_burnout else 2  # burnout -> critical, otherwise high
    return delta, f"Emotional pressure: {', '.join(triggers)}"
```

**Step 5.2 — Keep backward-compat wrapper in SpineOrchestrator**

```python
async def _detect_affective_pressure(self, **kwargs) -> ActionableSignal | None:
    """Delegated to FatigueGuard. Kept for backward compatibility.
    
    Generates ActionableSignal for affective_pressure state key.
    """
    fg = self.fatigue_guard
    delta, evidence = await fg._check_affective_pressure(**kwargs)
    if delta == 0:
        return None
    
    # Reconstruct ActionableSignal matching old output
    # ... (details in implementation) ...
```

### Phase 6: Configuration

Add to `backend/app/config/settings.py`:

```python
# ── FatigueGuard (GAP-P3-2) ───────────────────────────────────────────
FATIGUE_GUARD_ENABLED: bool = True
FATIGUE_INTERACTION_HIGH_THRESHOLD: int = 30
FATIGUE_INTERACTION_MEDIUM_THRESHOLD: int = 15
FATIGUE_CONSECUTIVE_HOURS_THRESHOLD: float = 4.0
FATIGUE_ACCURACY_DECLINE_WINDOW: int = 3
FATIGUE_HELP_SEEKING_WINDOW: int = 5
FATIGUE_HELP_SEEKING_RATIO: float = 0.4
FATIGUE_LATEST_TTL_SECONDS: int = 21600      # 6 hours
FATIGUE_HISTORY_TTL_SECONDS: int = 604800    # 7 days
FATIGUE_HISTORY_MAX_ENTRIES: int = 50
FATIGUE_DECAY_SCHEDULE_SECONDS: int = 21600   # 6 hours
```

Remove old NEXT_STEP_FATIGUE thresholds (586-587) if they are no longer consumed by other code. Add a transition note.

---

## 5. Test Plan

### 5.1 Unit Tests (new file: `backend/tests/unit/signals/test_fatigue_guard.py`)

**Test Class 1: Dimension Detection**

| Test | Coverage |
|------|----------|
| `test_interaction_volume_low` | 5 interactions -> no fatigue |
| `test_interaction_volume_medium` | 20 interactions -> medium |
| `test_interaction_volume_high` | 40 interactions -> high |
| `test_consecutive_usage_elevates` | 5h consecutive + 20 interactions -> high to critical |
| `test_accuracy_decline_trigger` | [0.9, 0.7, 0.5] -> medium |
| `test_accuracy_decline_insufficient` | [0.8] -> no trigger (< 3 points) |
| `test_accuracy_decline_not_monotonic` | [0.5, 0.7, 0.6] -> no trigger |
| `test_late_night_elevation` | late night only -> medium |
| `test_abandon_streak_burnout` | 3 abandons -> critical |
| `test_error_density_high` | 0.7 error density -> high |
| `test_help_seeking_trigger` | 3/5 messages contain fatigue keywords -> medium |
| `test_help_seeking_below_threshold` | 1/5 messages -> no trigger |
| `test_multiple_dimensions_combine` | 25 interactions + accuracy decline -> high |

**Test Class 2: Level Combination**

| Test | Coverage |
|------|----------|
| `test_highest_dimension_wins` | medium + low + none = medium |
| `test_critical_overrides_all` | critical + any = critical |
| `test_no_dimensions_returns_normal` | All dimensions clear -> normal |
| `test_boundary_15_interactions` | Exactly 15 -> medium |
| `test_boundary_30_interactions` | Exactly 30 -> high |

**Test Class 3: Persistence**

| Test | Coverage |
|------|----------|
| `test_save_and_retrieve_latest` | Save -> get back exact state |
| `test_history_append` | Multiple saves -> history grows |
| `test_history_max_cap` | 60 saves -> only 50 in history |
| `test_latest_ttl` | After TTL -> None |
| `test_to_context_dict_none_when_empty` | No saved state -> None |
| `test_to_context_dict_format` | Matches old dict format |

**Test Class 4: Interaction Tracking**

| Test | Coverage |
|------|----------|
| `test_record_interaction_increments` | First incr = 1, second = 2 |
| `test_record_sets_expiry` | First incr sets TTL |
| `test_get_interaction_count_zero` | No records -> 0 |

**Test Class 5: Backward Compatibility**

| Test | Coverage |
|------|----------|
| `test_check_fatigue_returns_same_shape` | Same dict keys as old method |
| `test_to_actionable_signal_format` | Valid ActionableSignal |
| `test_spine_orchestrator_delegation` | Thin wrapper returns correct result |
| `test_old_consumers_still_work` | orchestrator.py still gets context |

**Test Class 6: Prometheus Metrics**

| Test | Coverage |
|------|----------|
| `test_metrics_emitted_on_detect` | Counter incremented for each detection |
| `test_metrics_dimension_tracked` | Dimension counter incremented |
| `test_metrics_no_cardinality_explosion` | No user_id label on gauges |

### 5.2 Integration Tests (in existing test_signal_spine.py)

| Test | Coverage |
|------|----------|
| `test_pipeline_fatigue_detection_on_task_completion` | Update to use FatigueGuard |
| `test_fatigue_injects_into_prompt` | No change (tests prompt, not backend) |
| `test_crisis_injects_into_prompt` | No change |

### 5.3 Migration Verification

| Check | Method |
|-------|--------|
| Old Redis keys still readable during transition | Read from `spine:fatigue:{user_id}:latest` in addition to `fg:fatigue:{user_id}:latest` |
| Dual write during migration period | Both old and new keys written for 2 weeks |
| No regression in prompt injection | Integration test validates prompt output same |
| No regression in dual_core_router routing | Existing routing tests pass |

---

## 6. Acceptance Criteria

### P0 — Must Have (Blocking)

- [ ] **AC1**: `FatigueGuard` class exists in `backend/app/signals/fatigue_guard.py` with all 7 dimension detection methods
- [ ] **AC2**: All 3 missing detection dimensions are implemented (high-frequency, accuracy decline, repeated help-seeking)
- [ ] **AC3**: All existing consumers read fatigue state from the unified service, not from scattered locations
- [ ] **AC4**: `to_context_dict()` returns same dict shape as old `check_fatigue()` (backward compatible dict format)
- [ ] **AC5**: All existing fatigue tests pass without modification (except migration notice)
- [ ] **AC6**: New test file `backend/tests/unit/signals/test_fatigue_guard.py` has >=80% coverage of new code
- [ ] **AC7**: Interaction counter tracking (24h window) works through FatigueGuard

### P1 — Should Have

- [ ] **AC8**: Prometheus counters for fatigue detection by level and dimension are emitted
- [ ] **AC9**: Celery task `scan_fatigue_decay` exists and is registered in `celery_schedule.py`
- [ ] **AC10**: Fatigue configuration constants are added to `settings.py`
- [ ] **AC11**: `SpineOrchestrator.check_fatigue()` delegates to `FatigueGuard` (thin wrapper retained)
- [ ] **AC12**: `SpineOrchestrator._detect_affective_pressure()` delegates to `FatigueGuard`

### P2 — Nice to Have

- [ ] **AC13**: Dual-write migration: both old (`spine:fatigue:*`) and new (`fg:fatigue:*`) Redis keys written during transition
- [ ] **AC14**: Redis key migration period documented with removal date
- [ ] **AC15**: Logging with fatigue level and triggered dimensions at INFO level

### Verification Method

```
# Automated:
cd backend && pytest tests/unit/signals/test_fatigue_guard.py -v --cov=app.signals.fatigue_guard

# Integration:
cd backend && pytest tests/unit/test_signal_spine.py -v -k "fatigue" --no-header

# Manual test via REPL:
python -c "
import asyncio
from app.signals.fatigue_guard import FatigueGuard
from fakeredis import FakeRedis
fg = FatigueGuard(FakeRedis())
result = asyncio.run(fg.detect(user_id='test', interactions_last_24h=40))
print(result.fatigue_level, result.dimensions_triggered)
"

# Metrics check:
curl localhost:8000/metrics | grep sparkle_fatigue
```

---

## 7. Design Decisions

### DD1: New Redis Key Namespace
- **Decision**: Use `fg:*` prefix for all FatigueGuard keys (e.g., `fg:fatigue:{user_id}:latest`)
- **Rationale**: Clear namespace separation from `spine:*` keys. Easier to monitor, expire, and migrate. Avoids collision with existing keys.
- **Trade-off**: Dual-write needed during migration. Old consumers reading `spine:fatigue:*` will miss new writes until migrated.

### DD2: Standalone Class (Not a Mixin)
- **Decision**: `FatigueGuard` is a standalone class instantiated independently, not a mixin or parent class
- **Rationale**: Follows existing pattern used by `MistakeSignalDetector`, `MaterialSignalDetector`, `RecallOpportunityDetector` — all standalone classes taking `redis_client` in constructor. Does not need SpineOrchestrator context.
- **Trade-off**: Requires constructing a separate instance in orchestrator_production.py (already done for `SpineOrchestrator`).

### DD3: Backward-Compatible Shape
- **Decision**: `to_context_dict()` returns exactly the same dict as old `check_fatigue()`
- **Rationale**: Minimizes change scope. Consumers (prompts.py, dual_core_router.py) do not need modifications.
- **Trade-off**: Perpetuates dict-based interface. Future refactor can add typed interface as a secondary method.

### DD4: FatigueSignal Dataclass as Internal Representation
- **Decision**: Use a typed dataclass `FatigueSignal` internally, convert to dict for serialization
- **Rationale**: Type safety for detection logic. Dict conversion only at serialization boundary (Redis write).
- **Trade-off**: Extra conversion step. Worth it for maintainability.

### DD5: No user_id Label on Prometheus Gauges
- **Decision**: Use `fatigue_level` label instead of `user_id` on gauges
- **Rationale**: Prevents cardinality explosion in Prometheus. User-level tracking can be done via Redis queries if needed.
- **Trade-off**: Loss of per-user granularity in Grafana. Counter for `fatigue_detected_total` uses `level` label which has bounded cardinality (5 values).

### DD6: Phase-In Migration (2-Week Dual Write)
- **Decision**: During migration, write to both old (`spine:fatigue:*`) and new (`fg:fatigue:*`) Redis keys
- **Rationale**: Allows gradual consumer migration without a big-bang deployment. Old consumers continue reading from old keys until migrated.
- **Trade-off**: Double write overhead (negligible — two Redis SETs). Tracked for removal after all consumers migrated.

### DD7: Retain Thin Wrapper Methods
- **Decision**: `SpineOrchestrator.check_fatigue()` and `_detect_affective_pressure()` remain as thin wrappers delegating to FatigueGuard
- **Rationale**: Backward compatibility for any code that imports `SpineOrchestrator` and calls these methods. Prevents cascading import errors.
- **Trade-off**: Keeps dead code paths. Mark with `# DEPRECATED: use FatigueGuard directly` and scheduled removal.

### DD8: Help-Seeking Ratio Over Raw Count
- **Decision**: Use ratio-based threshold (>=40% of recent messages contain fatigue markers) rather than raw count
- **Rationale**: Ratio adapts to different usage patterns. A quiet user sending 3/5 help messages is more significant than a chatty user sending 5/50.
- **Trade-off**: Requires storing message text (truncated to 200 chars). Risk-mitigated by TTL (24h) and list trim (max 10 entries).

---

## 8. Dependencies

### 8.1 Internal Dependencies

| Dependency | Why | Risk |
|------------|-----|------|
| `ActionableSignal` from `app.signals.types` | Signal generation for spine pipeline | Low — stable dataclass |
| `_uid` from `app.signals.types` | Signal ID generation | Low — stable utility |
| `get_or_create_metric` from `app.core.metrics` | Prometheus metric registration | Low — stable pattern |
| `FakeRedis` in tests | Redis mock for unit tests | Low — existing fixture |
| `AsyncMock` in tests | Mock for unit tests | Low — existing fixture |

### 8.2 External Dependencies

| Dependency | Why | Risk |
|------------|-----|------|
| Redis | Required for all state storage | Low — already in stack |
| Prometheus client | Required for metrics | Low — already in stack |

### 8.3 No New Dependencies

This project does not require any new pip dependencies. All tools (Redis, Prometheus, asyncio) are already in the project.

---

## 9. Open Questions

### Q1: Should affective pressure (burnout_risk) live in FatigueGuard or stay in SpineOrchestrator?
- **Context**: `_detect_affective_pressure()` generates an `ActionableSignal` for the `affective_pressure` state key, which is consumed by the spine pipeline. Moving it to FatigueGuard means FatigueGuard needs to know about `ActionableSignal` (already a dependency) and the spine state key schema.
- **Proposed**: Move the detection logic, keep the signal generation in SpineOrchestrator as a thin caller. This keeps FatigueGuard focused on fatigue detection, not spine integration.

### Q2: What is the exact retirement plan for old Redis keys?
- **Context**: Current consumers read from `spine:fatigue:{user_id}:latest`. New service writes to `fg:fatigue:{user_id}:latest`. Both must work during transition.
- **Proposed**: 2-week dual-write. After 2 weeks, remove old key writes, update all consumers to read from new keys. Document in the code with `# TODO(GAP-P3-2): remove after 2026-05-20` markers.

### Q3: Should we add a `FatigueLevel.NORMAL` level?
- **Context**: The current `check_fatigue()` returns `low` as the minimum. But conceptually, "no fatigue detected" is different from "low fatigue."
- **Proposed**: Add `NORMAL` as the default level when no dimensions trigger. `LOW` becomes the first elevated level (e.g., 1 dimension triggered weakly). Backward-compat: `LOW` maps to old `low` behavior, `NORMAL` is new.

### Q4: Does the repeated help-seeking pattern need persistent storage?
- **Context**: Help-seeking detection requires storing recent message text. This could leak PII if retained too long.
- **Proposed**: Store only truncated messages (200 chars max), with 24h TTL and max 10 entries per user. No persistent storage. This is ephemeral state only, consistent with other Redis-backed patterns.

### Q5: Should FatigueGuard emit its own ActionableSignal, or should the caller do it?
- **Context**: `MistakeSignalDetector` creates its own `ActionableSignal`. But `FatigueGuard` also needs to produce a context dict for non-spine consumers.
- **Proposed**: Both. `FatigueGuard` provides `to_actionable_signal()` for spine integration and `to_context_dict()` for direct consumer use. The caller (SpineOrchestrator) decides which to use.

### Q6: What interaction counts as an "interaction"?
- **Context**: The current counter at `spine:interaction_count:{user_id}:24h` is incremented every pipeline run. But not all pipeline runs are user interactions (some are system-triggered).
- **Proposed**: Clarify that only user-triggered events increment the counter. System events (Celery tasks, background scans) should not count. Add a parameter `is_user_triggered: bool = True` to `record_interaction()`.

### Q7: Should the fatigue decay Celery task scan all users, or only active ones?
- **Context**: Scanning all users in Redis is expensive. Scanning only active users (those with a recent `fg:fatigue:*` key) is cheaper but misses stale entries.
- **Proposed**: Scan only users with existing `fg:fatigue:*:latest` keys. The absolute count of users with fatigue state is bounded by active user count, not total user count. Use Redis SCAN (not KEYS) for production safety.

---

## Appendix A: Consumer Migration Map

| Current Consumer | Current Interface | New Interface | Migration Priority |
|-----------------|-------------------|---------------|-------------------|
| `SpineOrchestrator._enrich_pipeline_post_policy` | `check_fatigue()` method | `FatigueGuard.detect()` + `.save_fatigue_state()` | P0 (same PR) |
| `SpineOrchestrator.on_pipeline_event` (line 1277) | `redis.incr()` inline | `FatigueGuard.record_interaction()` | P0 (same PR) |
| `SpineOrchestrator.check_fatigue()` external callers | `check_fatigue()` method | Thin wrapper (no change for callers) | P0 (same PR) |
| `SpineOrchestrator._detect_affective_pressure()` | Inline logic | `FatigueGuard._check_affective_pressure()` + wrapper | P1 (same PR) |
| `orchestrator_production.py` (fatigue context) | Direct `redis.get("spine:fatigue:*")` | `FatigueGuard.to_context_dict()` | P1 (same PR) |
| `orchestrator.py` (v1 FSM) | `_spine.check_fatigue()` | `FatigueGuard.detect()` + `.to_context_dict()` | P1 (same PR) |

## Appendix B: Architecture Diagram

```
                    ┌─────────────────────────────────────────────────┐
                    │                 FatigueGuard                    │
                    │  ┌───────────┐  ┌──────────┐  ┌─────────────┐  │
                    │  │  detect() │  │record_   │  │ save/load   │  │
                    │  │           │  │interact()│  │ state       │  │
                    │  │ 7 dims    │  │record_   │  │             │  │
                    │  │ checker   │  │message() │  │ Redis I/O   │  │
                    │  └─────┬─────┘  └────┬─────┘  └──────┬──────┘  │
                    │        │             │               │         │
                    │  ┌─────┴─────────────┴───────────────┴──────┐  │
                    │  │         Prometheus Metrics              │  │
                    │  │  Counter("fatigue_detected_total")      │  │
                    │  │  Gauge("fatigue_current_level")         │  │
                    │  └─────────────────────────────────────────┘  │
                    └────────────────────────────────────────────────┘
                                  │              │
                    ┌─────────────┴──┐    ┌───────┴──────────────┐
                    │  Redis Keys    │    │  Consumers           │
                    │  fg:fatigue:*  │    │  ┌────────────────┐  │
                    │  fg:interact:* │    │  │ orchestrator.py│  │
                    │  fg:help:*     │    │  │ orch_prod.py   │  │
                    │  ┌──────────┐  │    │  │ dual_core_     │  │
                    │  │spine:*   │  │    │  │ router.py      │  │
                    │  │(old,dual)│  │    │  │ SpineOrch.py   │  │
                    │  └──────────┘  │    │  │ prompts.py     │  │
                    └───────────────┘    │  (via context dict)│  │
                                         └────────────────────┘  │
                                         │ policy_engine.py       │
                                         │ crisis_mode_fsm.py     │
                                         │ recall_opportunity.py  │
                                         └────────────────────────┘
```

## Appendix C: Redis Key Schema (Final State)

| Key | Value Type | TTL | Purpose |
|-----|-----------|-----|---------|
| `fg:fatigue:{uid}:latest` | JSON string | 6h | Latest fatigue state for prompt injection |
| `fg:fatigue:{uid}:history` | JSON list | 7d | Fatigue history for trend analysis (max 50) |
| `fg:interaction_count:{uid}:24h` | Int | 24h | Rolling 24h interaction counter |
| `fg:help_seeking:{uid}:recent` | JSON list | 24h | Recent messages for help-seeking detection (max 10) |
| `fg:consecutive:{uid}:tracker` | JSON | 2h idle | Tracks session start for consecutive hour calculation |
| (legacy) `spine:fatigue:{uid}:latest` | JSON string | 6h | Dual-write during migration, remove after 2 weeks |
| (legacy) `spine:interaction_count:{uid}:24h` | Int | 24h | Dual-write during migration, remove after 2 weeks |

---

*End of spec.*
