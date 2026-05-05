# GAP-P3-3: RecoveryModeOrchestrator — Implementation Spec

> **Mode**: spec→you | **Level**: L3 | **Effort**: L (8-12 days)
> **Source**: 03 号报告 STAB-013 — 多依赖故障一致性恢复
> **Status**: 📋 Spec ready for user implementation

---

## 1. 目标 (Objectives)

为 Sparkle 构建统一的 RecoveryModeOrchestrator：当基础设施依赖（Redis/PostgreSQL/MinIO/gRPC）发生故障并恢复时，自动协调：事件回放 → 状态恢复 → 一致性校验。

### 核心目标
1. 实现 `RecoveryModeOrchestrator`: 统一编排多依赖故障恢复
2. 依赖健康监控：周期性探活 + 状态机 (healthy/degraded/down/recovering)
3. 故障期间事件缓冲：将无法处理的事件写入 DLQ，恢复后回放
4. 恢复流程编排：检测恢复 → 回放事件 → 恢复状态 → 校验一致性
5. 与现有基础设施集成：CircuitBreaker、redis_resilience、health endpoints

---

## 2. 现状评估 (Current State Assessment)

### 已实现

| 能力 | 文件 | 状态 |
|------|------|------|
| CircuitBreaker (orchestration) | `backend/app/orchestration/circuit_breaker.py` | ✅ 完整 — CLOSED/OPEN/HALF_OPEN + sliding window |
| Redis CircuitBreaker (3 named) | `backend/app/signals/redis_resilience.py` | ✅ 完整 — spine_pipeline/state_register/chronicle |
| 工具调用补偿 | `backend/app/orchestration/executor.py:180-603` | ✅ 完整 — _parse_compensation_call + _maybe_execute_compensation |
| 状态快照恢复 | `backend/app/signals/spine_orchestrator.py:3826-3857` | ✅ 完整 — recover_from_snapshot() |
| Chronicle 持久化回退 | `backend/app/signals/growth_chronicle.py:425-433` | ✅ 完整 — PostgreSQL fallback |
| DLQ 管理端点 | `backend/app/api/v1/dlq_admin.py` | ✅ 完整 — replay_dlq_events() |
| Event Bus DLQ replay | `backend/app/api/v1/event_bus_health.py` | ✅ 完整 — replay_event_bus_dlq() |
| Health check endpoints | `backend/app/api/v1/health.py` | ✅ 完整 — DB latency + Redis status |
| SSE missed event replay | `backend/app/core/sse.py` | ✅ 完整 — replay since last_event_id |
| 规划 fallback | `backend/app/orchestration/lang_graph_planner.py` | ✅ 完整 — build_fallback_plan() |

### 实际缺口

| # | 缺口 | 严重程度 | 描述 |
|---|------|---------|------|
| G1 | **无统一恢复编排器** | 🔴 High | 各组件有独立恢复逻辑，无统一协调 |
| G2 | **无依赖恢复后事件回放** | 🔴 High | 依赖恢复时，无 replay queue 回补丢失事件 |
| G3 | **无恢复后一致性校验** | 🟡 Medium | 恢复后无 checksum/verify 机制 |
| G4 | **MinIO 无 circuit breaker** | 🟡 Medium | document_upload_storage 无重试/熔断 |
| G5 | **gRPC 无统一故障处理** | 🟡 Medium | 4 个 gRPC 服务无统一 circuit breaker |

---

## 3. 架构设计

### 3.1 依赖状态模型

```python
class DependencyStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"      # 响应慢但可用
    DOWN = "down"              # 完全不可用
    RECOVERING = "recovering"  # 恢复中，正在回放

class DependencyKind(str, Enum):
    REDIS = "redis"
    POSTGRESQL = "postgresql"
    MINIO = "minio"
    GRPC_GATEWAY = "grpc_gateway"

@dataclass
class DependencyHealth:
    kind: DependencyKind
    status: DependencyStatus
    last_check: datetime
    consecutive_failures: int
    last_error: str | None
    latency_ms: float | None
```

### 3.2 RecoveryModeOrchestrator

```python
class RecoveryModeOrchestrator:
    """
    Coordinates multi-dependency fault recovery.

    Lifecycle:
    1. Health Monitor (periodic probe) → detects DOWN
    2. Event Buffer (during outage) → DLQ overflow buffer
    3. Recovery Trigger → dependency returns to HEALTHY/DEGRADED
    4. Replay Phase → replay buffered events in order
    5. Restore Phase → rebuild state from snapshots
    6. Verify Phase → consistency check
    """

    def __init__(self, redis: Redis):
        self.redis = redis
        self._health_states: dict[DependencyKind, DependencyHealth] = {}
        self._recovery_locks: dict[str, asyncio.Lock] = {}  # per user_id

    # --- Health Monitoring ---
    async def check_dependency_health(self, kind: DependencyKind) -> DependencyHealth
    async def run_health_monitor_loop(self) -> None  # Celery periodic

    # --- Event Buffering ---
    async def buffer_event(self, event: dict, target: str) -> None  # Write to recovery DLQ
    async def get_buffered_events(self, target: str, limit: int = 100) -> list[dict]

    # --- Recovery Orchestration ---
    async def on_dependency_recovered(self, kind: DependencyKind) -> None
    async def _replay_phase(self, kind: DependencyKind) -> int  # Returns events replayed
    async def _restore_phase(self, kind: DependencyKind) -> None
    async def _verify_phase(self, kind: DependencyKind) -> VerifyResult

    # --- Consistency Check ---
    async def verify_consistency(self, user_id: str) -> ConsistencyReport
```

### 3.3 Event Buffer (Redis Stream)

```
Key: recovery:buffer:{dependency_kind}
Format: Redis Stream entry
Fields: event_type, event_data (JSON), timestamp, source, target_queue
TTL: 7 days
Max length: 10000 entries (auto-trim)
```

### 3.4 Recovery Flow

```
Dependency DOWN detected
  → Mark status = DOWN
  → Event producers check: if DOWN → buffer_event() instead of direct publish
  → Circuit breakers open (existing mechanism)

Dependency UP detected (health check passes)
  → on_dependency_recovered()
  → Phase 1: REPLAY
      → Read buffered events from recovery:buffer:{kind}
      → Replay in timestamp order to original target queues
      → Track replay count + errors
  → Phase 2: RESTORE
      → For Redis: call SpineOrchestrator.recover_from_snapshot() for affected users
      → For PostgreSQL: verify connection pool, run integrity queries
      → For MinIO: check bucket accessibility
      → For gRPC: verify service endpoints
  → Phase 3: VERIFY
      → Cross-check: Redis state count vs PostgreSQL plan count
      → Verify recent event processing completeness
      → Report ConsistencyReport (pass/warnings/failures)
  → Mark status = HEALTHY
  → Emit recovery_complete event to event bus
```

---

## 4. 文件清单

### 新文件

| # | 文件 | 描述 |
|---|------|------|
| 1 | `backend/app/services/recovery_orchestrator.py` | RecoveryModeOrchestrator 主服务 |
| 2 | `backend/app/services/recovery_health_monitor.py` | 依赖健康探活 + 状态机 |
| 3 | `backend/app/services/recovery_event_buffer.py` | 故障期间事件缓冲 (Redis Stream) |
| 4 | `backend/app/services/recovery_consistency.py` | 恢复后一致性校验 |
| 5 | `backend/app/tasks/recovery_monitor_task.py` | Celery 周期健康检查任务 |
| 6 | `backend/tests/unit/test_recovery_orchestrator.py` | 单元测试 |

### 修改文件

| # | 文件 | 改动 |
|---|------|------|
| 7 | `backend/app/core/celery_app.py` | 添加 recovery-monitor 到 beat_schedule + include |
| 8 | `backend/app/services/document_upload_storage.py` | 添加 MinIO circuit breaker |
| 9 | `backend/app/signals/redis_resilience.py` | 暴露 `is_circuit_open()` 给 RecoveryOrchestrator 查询 |

---

## 5. 实现步骤

### Phase 1: 基础模型 + 健康探活 (2-3 days)

1. **创建 `recovery_health_monitor.py`**
   - `DependencyHealth` dataclass
   - `DependencyKind` enum
   - `DependencyStatus` enum
   - `RecoveryHealthMonitor` class with probe methods for each dependency:
     - Redis: `PING` command
     - PostgreSQL: `SELECT 1` with latency
     - MinIO: `HeadBucket` API call
     - gRPC: `grpc_health_v1.HealthCheck`

2. **创建 `recovery_monitor_task.py`**
   - Celery `shared_task` running every 60s
   - Calls `RecoveryHealthMonitor.check_all()`
   - Updates Redis state `recovery:health:{kind}`
   - On status transition DOWN→UP: calls `RecoveryModeOrchestrator.on_dependency_recovered()`

3. **注册 Celery beat**
   - Add `recovery-monitor` to `beat_schedule` (60s interval)
   - Add `app.tasks.recovery_monitor_task` to `include` list

### Phase 2: 事件缓冲 (2-3 days)

4. **创建 `recovery_event_buffer.py`**
   - `RecoveryEventBuffer` class
   - `buffer_event()`: writes to Redis Stream `recovery:buffer:{kind}`
   - `get_buffered_events()`: reads from stream with XREAD
   - `trim_buffer()`: XTRIM to max 10000 entries
   - `clear_buffer()`: DEL key after successful replay

5. **集成到 event_bus.py**
   - Before `publish()`: check if target dependency is DOWN
   - If DOWN: `buffer_event()` instead of direct publish
   - If UP: normal publish (no overhead)

### Phase 3: 恢复编排 (3-4 days)

6. **创建 `recovery_orchestrator.py`**
   - `RecoveryModeOrchestrator` class
   - `on_dependency_recovered()` → orchestrate 3 phases
   - `_replay_phase()`: read buffer → replay events → count
   - `_restore_phase()`: per-dependency restore logic
   - `_verify_phase()`: delegate to `recovery_consistency.py`

7. **创建 `recovery_consistency.py`**
   - `ConsistencyReport` dataclass
   - `verify_consistency()`:
     - Redis: state register count vs DB active plans
     - PostgreSQL: stale connection pool detection
     - Event bus: consumer lag check
   - Return pass/warning/fail with details

### Phase 4: MinIO Circuit Breaker + 测试 (1-2 days)

8. **MinIO circuit breaker**
   - Add to `document_upload_storage.py`
   - Use existing `CircuitBreaker` from `orchestration/circuit_breaker.py`
   - On failure: open breaker, future calls return graceful error
   - On recovery: half-open → probe → close

9. **暴露 redis_resilience 状态**
   - Add `is_circuit_open(breaker_name: str) -> bool` to `redis_resilience.py`
   - Used by health monitor to report Redis status

10. **单元测试 `test_recovery_orchestrator.py`**
    - Test health probe for each dependency (mock)
    - Test event buffer write/read/trim
    - Test recovery flow: DOWN → buffer → UP → replay → restore → verify
    - Test consistency check with mismatched counts
    - Target: 12+ tests

---

## 6. 接口契约

### RecoveryModeOrchestrator API

```python
# Health check result
@dataclass
class DependencyHealth:
    kind: DependencyKind
    status: DependencyStatus
    last_check: datetime
    consecutive_failures: int
    last_error: str | None
    latency_ms: float | None

# Consistency verification result
@dataclass
class ConsistencyReport:
    dependency: DependencyKind
    passed: bool
    warnings: list[str]
    failures: list[str]
    checked_at: datetime

# Recovery result
@dataclass
class RecoveryResult:
    dependency: DependencyKind
    events_replayed: int
    events_failed: int
    restore_duration_ms: int
    verify_report: ConsistencyReport
    recovered_at: datetime
```

### Redis Keys

```
recovery:health:{kind}            → JSON DependencyHealth, TTL 120s
recovery:buffer:{kind}            → Redis Stream, MAXLEN 10000
recovery:status                    → Hash of {kind: status}
recovery:last_recovery:{kind}     → JSON RecoveryResult, TTL 7 days
```

### Celery Tasks

```
recovery.health-monitor    → 60s interval, probe all dependencies
recovery.trigger-recovery  → On-demand, trigger recovery for specific kind
```

---

## 7. 验收标准

| # | 标准 | 验证方式 |
|---|------|---------|
| AC1 | 健康探活周期运行 (60s)，状态转换正确 | Unit test + Redis state check |
| AC2 | 依赖 DOWN 时事件被缓冲到 Redis Stream | Unit test: buffer_event + get_buffered_events |
| AC3 | 依赖恢复后事件被完整回放 | Unit test: DOWN → buffer → UP → replay count |
| AC4 | Redis 恢复后调用 recover_from_snapshot | Integration test with mock SpineOrchestrator |
| AC5 | 一致性校验检测到不一致并报告 | Unit test: mismatched counts → failure |
| AC6 | MinIO 有 circuit breaker 保护 | Unit test: consecutive failures → open breaker |
| AC7 | 12+ 单元测试全部通过 | pytest |
| AC8 | Celery beat 注册正确 | Check celery_app.py beat_schedule + include |
| AC9 | 无 OWASP / 无 hardcoded secrets | Rule guard check |

---

## 8. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 回放大规模事件可能造成负载尖峰 | Rate limit replay: 100 events/s max + batch processing |
| 恢复期间又有依赖故障 | 使用 per-user asyncio.Lock + 超时保护 |
| 缓冲区溢出丢失事件 | MAXLEN 10000 + Prometheus counter `recovery_buffer_dropped_total` |
| 健康检查误报 (网络抖动) | 连续 3 次失败才标记 DOWN，1 次成功就恢复 |

---

## 9. 依赖关系

```
RecoveryModeOrchestrator
  ├── RecoveryHealthMonitor (new)
  │     └── Health endpoints (existing)
  ├── RecoveryEventBuffer (new)
  │     └── Redis Streams (existing)
  ├── RecoveryConsistency (new)
  │     ├── SpineOrchestrator.recover_from_snapshot() (existing)
  │     ├── StateRegister (existing)
  │     └── Database queries (existing)
  ├── CircuitBreaker (existing, orchestration/)
  ├── redis_resilience (existing, modify to expose is_circuit_open)
  └── document_upload_storage (existing, add MinIO breaker)
```

---

## 10. 时间估算

| Phase | 天数 | 描述 |
|-------|------|------|
| Phase 1 | 2-3 | 基础模型 + 健康探活 + Celery 注册 |
| Phase 2 | 2-3 | 事件缓冲 + event_bus 集成 |
| Phase 3 | 3-4 | 恢复编排 + 一致性校验 |
| Phase 4 | 1-2 | MinIO breaker + 测试 |
| **Total** | **8-12** | |
