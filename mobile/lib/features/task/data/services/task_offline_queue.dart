import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/offline_providers.dart';
import 'package:sparkle/core/offline/sync_engine.dart';

/// TASK-013: Offline-first queue for task lifecycle operations.
///
/// When the network is down (or the request fails with a connection error),
/// the UI calls into this service to enqueue the operation in the SyncEngine
/// outbox. SyncEngine replays it once connectivity returns. Each task op type
/// is idempotent server-side (409 = already in target state = success).
class TaskOfflineQueue {
  TaskOfflineQueue(this._engine, this._localDb);

  final SyncEngine _engine;
  final LocalDatabase _localDb;

  Future<void> enqueueStart(String taskId, {String? traceId}) async {
    await _engine.enqueue(
      topic: 'task',
      opType: 'start',
      payload: {'task_id': taskId},
      entityType: 'task',
      entityId: taskId,
      dedupeKey: 'task:$taskId:start',
      priority: 1,
      traceId: traceId,
    );
  }

  Future<void> enqueuePause(
    String taskId, {
    String? reason,
    String? traceId,
  }) async {
    await _engine.enqueue(
      topic: 'task',
      opType: 'pause',
      payload: {
        'task_id': taskId,
        if (reason != null && reason.isNotEmpty) 'reason': reason,
      },
      entityType: 'task',
      entityId: taskId,
      dedupeKey: 'task:$taskId:pause',
      priority: 1,
      traceId: traceId,
    );
  }

  Future<void> enqueueResume(String taskId, {String? traceId}) async {
    await _engine.enqueue(
      topic: 'task',
      opType: 'resume',
      payload: {'task_id': taskId},
      entityType: 'task',
      entityId: taskId,
      dedupeKey: 'task:$taskId:resume',
      priority: 1,
      traceId: traceId,
    );
  }

  Future<void> enqueueComplete(
    String taskId, {
    Map<String, dynamic>? completion,
    String? traceId,
  }) async {
    await _engine.enqueue(
      topic: 'task',
      opType: 'complete',
      payload: {
        'task_id': taskId,
        if (completion != null && completion.isNotEmpty) 'completion': completion,
      },
      entityType: 'task',
      entityId: taskId,
      dedupeKey: 'task:$taskId:complete',
      priority: 2,
      traceId: traceId,
    );
  }

  Future<void> enqueueAbandon(
    String taskId, {
    String? reason,
    String? traceId,
  }) async {
    await _engine.enqueue(
      topic: 'task',
      opType: 'abandon',
      payload: {
        'task_id': taskId,
        if (reason != null && reason.isNotEmpty) 'reason': reason,
      },
      entityType: 'task',
      entityId: taskId,
      dedupeKey: 'task:$taskId:abandon',
      priority: 1,
      traceId: traceId,
    );
  }

  /// Count pending task operations awaiting sync.
  Future<int> pendingTaskOpsCount() async {
    final db = _localDb.isarOrNull;
    if (db == null || !db.isOpen) return 0;
    return db.outboxItems
        .filter()
        .topicEqualTo('task')
        .and()
        .group(
          (q) => q
              .statusEqualTo(SyncStatus.pending)
              .or()
              .statusEqualTo(SyncStatus.waitingAck)
              .or()
              .statusEqualTo(SyncStatus.failed),
        )
        .count();
  }
}

final taskOfflineQueueProvider = Provider<TaskOfflineQueue>((ref) {
  final engine = ref.watch(syncEngineProvider);
  final localDb = ref.watch(localDatabaseProvider);
  return TaskOfflineQueue(engine, localDb);
});

/// Reactive count of pending task operations for UI badges.
final pendingTaskOpsCountProvider = StreamProvider<int>((ref) async* {
  final localDb = ref.watch(localDatabaseProvider);
  final db = localDb.isarOrNull;
  if (db == null || !db.isOpen) {
    yield 0;
    return;
  }

  final stream = db.outboxItems
      .filter()
      .topicEqualTo('task')
      .watch(fireImmediately: true);

  await for (final items in stream) {
    final pending = items
        .where(
          (item) =>
              item.status == SyncStatus.pending ||
              item.status == SyncStatus.waitingAck ||
              item.status == SyncStatus.failed,
        )
        .length;
    yield pending;
  }
});
