# Sparkle 质量审计 — 修复规格书

**日期**: 2026-05-02
**用途**: 每个问题提供完整背景、当前代码、修复方案，可直接动手改

---

## FIX-01: Status bar chip minHeight 不符合触摸目标标准

### 问题背景
`status_awareness_bar.dart` 中有 3 处 chip widget 的 `minHeight` 设为 32dp，低于 Apple HIG 和 Material Design 推荐的 44dp 最小触摸目标。同项目中 `contextual_correction_bar.dart` 的 `_CorrectionChip` 已正确使用 44dp，这里是不一致的。

注意：`_BarContainer` 本身已经有 `liveRegion: true`（第 1045 行），所以状态栏的整体状态变化对屏幕阅读器是可见的。但内部 chip 的触摸目标仍然偏小。

### 涉及文件
`mobile/lib/features/chat/presentation/widgets/status_awareness_bar.dart`

### 当前代码（3 处）

**第 1 处 — `_StatusCorrectionChip`（约第 1311 行）:**
```dart
constraints: const BoxConstraints(minHeight: 32, minWidth: 44),
```

**第 2 处 — `_PredictedOptionChip`（约第 1381 行）:**
```dart
constraints: const BoxConstraints(minHeight: 32, minWidth: 44),
```

**第 3 处 — `_StatusPredictedChip`（约第 1437 行）:**
```dart
constraints: const BoxConstraints(minHeight: 32, minWidth: 44),
```

### 修复方案
将 3 处 `minHeight: 32` 改为 `minHeight: 44`。视觉上 chip 会变高一些，但 44dp 是触摸目标的标准下限。

---

## FIX-02: 监控缺失 — 校准环路失败 + 熔断器打开无告警

### 问题背景
当前 `monitoring/sparkle_slo_alerts.yml` 有 11 条告警覆盖基础设施（Gateway/Backend 宕机、5xx 率、延迟、事件队列积压等），但没有针对 Aurora 用户侧故障的告警：

1. **校准环路**: 当 Aurora 的 correction 连续失败时（例如 `aurora_correction_failed_total` 持续增长），用户校正操作完全无效，但没有告警通知运维
2. **熔断器**: Go Gateway 的 gRPC 客户端有完整的熔断器实现（`health_checker.go`），当熔断器打开时所有请求被直接拒绝，但没有 Prometheus 告警

Go 侧已经暴露了相关指标（`health_checker.go` 中的 metrics），只是没有对应的告警规则。

### 涉及文件
`monitoring/sparkle_slo_alerts.yml`（或新建 `monitoring/sparkle_aurora_alerts.yml`）

### 当前状态
文件中没有 `aurora_correction`、`circuit_breaker`、`circuit_open` 相关的任何规则。

### 修复方案
在 `sparkle_slo_alerts.yml` 末尾添加 2 条规则：

```yaml
      - alert: SparkleCircuitBreakerOpen
        expr: sparkle_grpc_circuit_breaker_state{state="open"} == 1
        for: 1m
        labels:
          severity: warning
          tier: P2
          service: gateway
        annotations:
          summary: "gRPC circuit breaker is open"
          description: "The gRPC agent client circuit breaker has been open for more than 1 minute. All agent requests are being rejected."
          runbook: "monitoring/runbooks/incident_response.md#p2-circuitbreakeropen"

      - alert: SparkleAuroraCorrectionLoopStuck
        expr: increase(sparkle_aurora_correction_failed_total[10m]) > 5
        for: 5m
        labels:
          severity: warning
          tier: P3
          service: backend
        annotations:
          summary: "Aurora correction loop failing"
          description: "More than 5 Aurora correction failures in the last 10 minutes. Users may be unable to calibrate Aurora."
          runbook: "monitoring/runbooks/incident_response.md#p3-correctionloopstuck"
```

**注意**: 需要先确认 Prometheus 中实际的 metric 名称。在 Go 侧搜索 `prometheus.NewGauge` 或 `promauto.NewCounter` 中与 circuit breaker 和 correction 相关的指标名。如果 metric 名称不同，调整 `expr` 中的名称。

---

## FIX-03: CalibrationReceiptChip 关闭状态不持久

### 问题背景
`calibration_receipt_chip.dart` 有一个关闭按钮（IconButton with Icons.close_rounded），点击后 `setState(() => _dismissed = true)`，chip 变为 `SizedBox.shrink()`。

但 `_dismissed` 是 `State` 的本地变量。当用户滚动聊天列表导致 widget 被回收重建（Flutter 的常规行为），或者 Riverpod provider 触发重建时，`_dismissed` 重置为 `false`，已关闭的收据会重新出现。

### 涉及文件
`mobile/lib/features/chat/presentation/widgets/calibration_receipt_chip.dart`

### 当前代码（第 25 行 & 第 136 行）:
```dart
// 第 25 行
bool _dismissed = false;

// 第 136 行（关闭按钮回调）
setState(() => _dismissed = true);
```

### 修复方案
有两种选择：

**方案 A（推荐 — Provider 管理）:**
创建一个简单的 StateNotifier 或用 `Set<String>` provider 管理已关闭的收据 ID：

```dart
// 在 chat provider 文件中
final dismissedCalibrationReceiptsProvider = StateProvider<Set<String>>((ref) => {});
```

在 `_CalibrationReceiptChipState` 中：
```dart
// 读取
final dismissed = ref.watch(dismissedCalibrationReceiptsProvider);
if (dismissed.contains(widget.receipt.correctionId)) return const SizedBox.shrink();

// 关闭时
ref.read(dismissedCalibrationReceiptsProvider.notifier).update(
  (s) => {...s, widget.receipt.correctionId},
);
```

**方案 B（简单 — SharedPreferences）:**
直接用 `shared_preferences` 持久化到磁盘，适合跨会话也不希望看到相同收据的场景。

---

## FIX-04: AuroraReceiptChip 无关闭机制

### 问题背景
`aurora_receipt_chip.dart` 是一个展示 Aurora 推理依据的收据 widget（显示引用的记忆、来源、工具结果等）。与 `CalibrationReceiptChip` 不同，它没有任何关闭/收起按钮。

用户在聊天流中看到这些收据后，如果想清理视觉空间，没有办法去掉它们。`CalibrationReceiptChip` 有关闭按钮，这里不一致。

### 涉及文件
`mobile/lib/features/chat/presentation/widgets/aurora_receipt_chip.dart`

### 当前代码
整个文件没有 `dismiss`、`close`、`IconButton` 或任何关闭机制。widget 始终渲染为可见状态。

### 修复方案
参照 `CalibrationReceiptChip` 的模式：

1. 将 `AuroraReceiptChip` 从 `StatelessWidget` 改为 `StatefulWidget`（或使用相同的 provider 方案）
2. 在 chip 的右上角添加关闭按钮（与 CalibrationReceiptChip 风格一致）
3. 关闭状态与 FIX-03 使用同一个 `dismissedCalibrationReceiptsProvider`
4. 收据的唯一标识可以用 `receipt['response_id']` 或 `receiptType` + 内容 hash

---

## FIX-05: Home 模块 Colors.white 硬编码

### 问题背景
Chat 模块已 100% 使用 `DS.*` 设计 token，但 Home 模块仍有 23 处 `Colors.white` 硬编码。这会导致暗色模式下颜色可能不正确（取决于 `Colors.white` 的使用场景）。

### 涉及文件和具体位置

**核心违规（应优先修复）:**

| 文件 | 行数 | 当前代码 | 建议替换 |
|------|------|---------|---------|
| `exam_sprint_dashboard_card.dart` | 9 处 | `Colors.white` | 背景用 `DS.surfacePrimary`，文字用 `DS.textOnPrimary`（如果在 primary 色背景上） |
| `openclaw_automation_panel.dart` | 第 164、324 行 | `Colors.white`（background） | `DS.surfacePrimary` |
| `openclaw_node_management_panel.dart` | 第 220 行 | `Colors.white`（background） | `DS.surfacePrimary` |
| `openclaw_hub_card.dart` | 第 149 行 | `Colors.white`（icon color） | `DS.textOnPrimary` |
| `insight_hub_card.dart` | 第 323 行 | `Colors.white`（color） | `DS.textOnPrimary` |

**可接受的用法（视觉特效层，Colors.white 作为混合色使用）:**

| 文件 | 说明 |
|------|------|
| `particle_layer.dart` | 粒子效果，Colors.white 是混合色不是 UI token |
| `background_layer.dart` | 背景渐变 |
| `weather_presentation.dart` | 天气动画 |

这些视觉特效层中的 `Colors.white` 是作为颜色混合的物理值使用，不是 UI 设计 token，可以不改。

### 修复方案
逐个文件替换。每个替换需要根据上下文判断是背景色、文字色还是图标色：
- 背景色 → `DS.surfacePrimary`
- 在 primary 色背景上的文字/图标 → `DS.textOnPrimary`（如果 DS 中有定义）
- 在深色背景上的文字 → `DS.textOnDarkSurface` 或检查 DS 中可用的 token

---

## FIX-06: 限流器 Redis 不可用时硬拒绝

### 问题背景
Go Gateway 的 `DistributedRateLimiter` 使用 Redis 滑动窗口实现分布式限流。当 Redis 不可用时，`Allow()` 方法返回 `(false, 0, err)`——即所有请求被限流拒绝。

代码中已存在 `HybridRateLimitMiddlewareSimple`（`distributed_rate_limiter.go`），它同时设置了 Redis 和本地限流器，但主路径的 `DistributedRateLimiter.Allow()` 方法没有 fallback 逻辑。

### 涉及文件
`backend/gateway/internal/middleware/distributed_rate_limiter.go`

### 当前行为
`Allow()` 方法中 Redis 操作失败 → 返回 `(false, 0, err)` → 请求被拒绝。

### 修复方案
在 `Allow()` 方法中，当 Redis 返回 error 时，fallback 到本地限流器：

```go
func (d *DistributedRateLimiter) Allow(ctx context.Context, key string) (bool, int, error) {
    result, err := d.redisAllow(ctx, key)
    if err != nil {
        // Redis failed — fallback to local limiter
        d.metrics.RedisFallback(ctx)
        return d.localLimiter.Allow(), 0, nil  // 不要返回 error
    }
    return result, 0, nil
}
```

需要确认：
1. `DistributedRateLimiter` 是否已有 `localLimiter` 字段（可能需要添加）
2. fallback 到本地限流是否会导致限流过于宽松（单机 vs 分布式的差异）
3. 是否需要记录 fallback 事件到 Prometheus

---

## FIX-07: Aurora 核心会话状态仅 Redis 持久化

### 问题背景
Aurora 的核心会话状态（8 阶段 FSM）存储在 Redis 中，TTL 30 分钟。如果 Redis 重启或故障，所有进行中的会话状态丢失，用户需要重新开始。

### 涉及文件
- `backend/app/orchestration/orchestrator.py` — FSM 状态管理
- `backend/app/services/session_state_manager.py` — Redis 状态存取

### 当前行为
- 状态写入 Redis，30min TTL
- 无 PostgreSQL 备份
- Redis 宕机 = 会话状态全部丢失

### 修复方案（工作量较大，建议分期）
1. **短期**: 在 session state 写入 Redis 后，异步写入 PostgreSQL 的 `aurora_state_snapshots` 表（表结构可参考已有的 `AuroraStateSnapshot` model）
2. **中期**: Redis 不可用时从 PostgreSQL 恢复最近的状态快照
3. **长期**: 考虑 Redis Streams + PostgreSQL 双写的 event sourcing 模式

---

## 优先级和依赖关系

```
FIX-01 (chip minHeight) ─── 独立，5 分钟
FIX-02 (监控告警) ─────────── 独立，需确认 metric 名称，30 分钟
FIX-03 (receipt dismiss) ─── FIX-04 依赖同一个 provider，建议一起做
FIX-04 (receipt close) ───── 依赖 FIX-03 的 provider
FIX-05 (Colors.white) ────── 独立，逐文件替换，1-2 小时
FIX-06 (限流器 fallback) ─── 独立，需要理解 Go 限流器结构，1 小时
FIX-07 (Aurora 持久化) ───── 独立，工作量大，建议分期
```
