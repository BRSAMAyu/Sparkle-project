# Phase 2: Domain Logic Hardening & Observability Enforcement

## Executive Summary
This phase focuses on maturing the "nervous system" of the Sparkle mobile application. Following the visual upgrades (Luminous Cognition) and initial architecture steps, we will now enforce strict Domain-Driven Design (DDD) principles to decouple business logic from UI, implement a robust Offline-First strategy using the Outbox pattern, and integrate full-stack observability.

## 1. Domain Logic Hardening (DDD)

**Objective:** Move business logic out of Providers and Widgets into pure Dart `UseCases` and `Entities`.

### 1.1 Architecture Components

*   **Entities (`lib/features/{feature}/domain/entities/`)**:
    *   Pure Dart classes, no JSON serialization logic.
    *   Immutable (using `freezed` or `equatable`).
    *   *Example:* `GalaxyEntity` (instead of `GalaxyModel` which has `toJson`).

*   **Use Cases (`lib/features/{feature}/domain/use_cases/`)**:
    *   Single responsibility classes that encapsulate a specific business rule or flow.
    *   Callable classes (implement `call()` method).
    *   *Naming Convention:* `VerbSubjectUseCase` (e.g., `IgniteSparkUseCase`).
    *   *Example:* `GalaxyFocusUseCase` handles the complex logic of starting a focus session, updating local state, and queuing the sync event.

*   **Result Pattern (`lib/core/error/result.dart`)**:
    *   Replace `try-catch` blocks with a functional `Result<T, Failure>` type.
    *   Forces the caller to handle both success and failure cases explicitly.
    *   Integration with `fpdart` or a lightweight custom implementation.

*   **Mappers (`lib/features/{feature}/data/mappers/`)**:
    *   Explicit translators between Data Models (DTOs) and Domain Entities.
    *   Keeps the Domain layer independent of API changes.

### 1.2 Implementation Plan (Example: Knowledge Feature)

1.  **Create Domain Entity**: `KnowledgeNode` (stripped of `toJson`/`fromJson`).
2.  **Define Repository Interface**: `KnowledgeRepository` (returns `Future<Result<KnowledgeNode>>`).
3.  **Implement Use Case**: `GetKnowledgeDetailUseCase`, `ToggleFavoriteUseCase`.
4.  **Refactor Provider**:
    *   `KnowledgeDetailProvider` will now depend on `GetKnowledgeDetailUseCase`.
    *   State updates will be driven by the `Result` returned by the UseCase.

## 2. Offline-First & Sync Engine

**Objective:** Ensure user actions are instant and reliable, regardless of network status.

### 2.1 Outbox Pattern (Global Sync)

*   **Infrastructure**: Enhance `OfflineSyncQueue` (`lib/core/offline/sync_queue.dart`) to be a generic `SyncEngine`.
*   **Storage**: Use `Isar` for the `LocalOutbox` table.
*   **Job Structure**:
    ```dart
    class OutboxItem {
      String id;
      String type; // e.g., 'spark_creation', 'task_update'
      Map<String, dynamic> payload;
      DateTime createdAt;
      int retryCount;
      SyncStatus status; // pending, processing, failed, dead_letter
    }
    ```
*   **Worker**: A background service (using `workmanager` or isolate) that watches the `LocalOutbox` and attempts to process items when online.

### 2.2 Optimistic UI Updates

*   **Standardize Optimistic Pattern**:
    1.  **UI Event**: User clicks "Like".
    2.  **Provider Action**:
        *   Immediately update local state (Provider/Riverpod).
        *   Call UseCase.
    3.  **UseCase**:
        *   Persist change to local DB (Source of Truth for UI).
        *   Enqueue job to `LocalOutbox`.
        *   Return `Success`.
    4.  **Sync Engine (Async)**:
        *   Pick job from Outbox.
        *   Call API.
        *   On Success: Remove from Outbox.
        *   On Failure (Transient): Retry with exponential backoff.
        *   On Failure (Permanent): Mark as 'failed', notify user/UI to revert (Reversion logic needs careful design, potentially via `Undo` actions).

### 2.3 Cache Strategy

*   **TTL Policy**: Implement `SmartCache` enhancements in `core/network`.
    *   *Static Data* (e.g., historical reports): Long TTL (days).
    *   *Dynamic Data* (e.g., social feed): Short TTL (minutes).
    *   *Real-time Data* (e.g., chat): No cache / Stream-based.

## 3. Full-stack Observability

**Objective:** Gain visibility into the mobile app's health and performance in production.

### 3.1 Log Forwarding (Loki)

*   **CoreLogService**:
    *   Intercepts standard logging (currently `logger` package).
    *   Buffers logs locally.
    *   Batches and flushes to the backend `Promtail` endpoint (or a custom API proxying to Loki) periodically or on high-severity events.
    *   **Context**: Attach `userId`, `deviceId`, `appVersion`, `connectivity` to every log entry.

### 3.2 Performance Tracing

*   **Span Collection**:
    *   Wrap critical `UseCases` and `Repository` calls with start/end measurements.
    *   Integrate with `PerformanceService` to capture frame build times and rasterization metrics.
*   **Key Metrics**:
    *   `app_launch_time`
    *   `galaxy_load_time`
    *   `ai_response_latency`
    *   `sync_batch_duration`

### 3.3 Error Boundaries (Sentry/Custom)

*   **Global Error Handler**:
    *   `FlutterError.onError`: Catch UI rendering errors.
    *   `PlatformDispatcher.instance.onError`: Catch async platform errors.
    *   `Zone` guards: Catch unhandled async errors.
*   **Reporting**:
    *   Send stack traces and breadcrumbs to Sentry (if available) or the custom Log Forwarding service.

## 4. Visual Micro-optimizations

### 4.1 Shader Architecture
*   **Abstraction**: Create `CoreShaderComponent` to manage shader loading, compilation, and uniform updates.
*   **Reuse**: Apply the `StarMapPainter`'s efficient shader logic to other areas like "Achievement Badges" or "Profile Headers".

### 4.2 Haptic Feedback
*   **Tiered Feedback**:
    *   `PerformanceTier.ultra`: Rich, variable haptics (using `haptic_feedback` or platform channels for complex patterns).
    *   `PerformanceTier.low`: Basic standard vibration or off.
*   **Events**: "Spark Created" (Heavy), "Selection" (Light), "Error" (Double tap).

## 5. Execution Roadmap

### Week 1: Domain Core & UseCase Migration
*   [ ] Setup `core/domain` (Result, UseCase base classes).
*   [ ] Refactor `Knowledge` feature to DDD.
*   [ ] Create Entities and Mappers for Knowledge feature.
*   [ ] Unit test all new UseCases.

### Week 2: Robust Offline Sync
*   [ ] Upgrade `OfflineSyncQueue` to generic `LocalOutbox` based on Isar.
*   [ ] Implement `SyncWorker` for background processing.
*   [ ] Refactor `GalaxyRepository` to use Outbox for state-changing operations.
*   [ ] Implement Optimistic UI helper in `core/utils`.

### Week 3: Observability & Monitoring
*   [ ] Implement `CoreLogService` with batching and retry logic.
*   [ ] Create backend endpoint (if needed) or configure Loki gateway for mobile logs.
*   [ ] Instrument `PerformanceService` to report metrics.
*   [ ] Setup Global Error Boundary.

### Week 4: Visual Polish & Hardening
*   [ ] Abstract Shader logic.
*   [ ] Implement Tiered Haptics.
*   [ ] Full regression testing.
*   [ ] Integration tests for Sync scenarios (offline -> online).
