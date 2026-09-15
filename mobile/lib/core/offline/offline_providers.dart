import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/crdt_sync_manager.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/offline_chat_message.dart';
import 'package:sparkle/core/offline/offline_message_queue_service.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/core/services/websocket_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';

final webSocketServiceProvider =
    Provider<WebSocketService>((ref) => WebSocketService());

final offlineMessageQueueServiceProvider = Provider<OfflineMessageQueueService>(
  (ref) => OfflineMessageQueueService(ref.watch(localDatabaseProvider)),
);

final offlineQueueCurrentUserIdProvider = FutureProvider<String>((ref) async {
  final user = ref.watch(authProvider).user;
  if (user != null) {
    return user.id;
  }
  return ref.watch(guestServiceProvider).getGuestId();
});

class OfflineQueueEntry {
  const OfflineQueueEntry({
    required this.requestId,
    required this.sessionId,
    required this.message,
    required this.status,
    required this.createdAt,
  });

  final String requestId;
  final String sessionId;
  final String message;
  final OfflineMessageStatus status;
  final DateTime createdAt;

  bool get isPending => status == OfflineMessageStatus.pending;
  bool get isSending => status == OfflineMessageStatus.sent;
  bool get isFailed => status == OfflineMessageStatus.failed;
}

class OfflineQueueSnapshot {
  const OfflineQueueSnapshot({
    required this.entries,
    int? pendingCount,
  }) : _pendingCount = pendingCount;

  static const empty = OfflineQueueSnapshot(entries: <OfflineQueueEntry>[]);

  final List<OfflineQueueEntry> entries;
  final int? _pendingCount;

  int get pendingCount =>
      _pendingCount ??
      entries.where((OfflineQueueEntry entry) => entry.isPending).length;
  int get sendingCount =>
      entries.where((OfflineQueueEntry entry) => entry.isSending).length;
  int get failedCount =>
      entries.where((OfflineQueueEntry entry) => entry.isFailed).length;
  int get activeCount => entries.length;
  bool get hasActiveQueue => activeCount > 0;
}

final offlineQueueSnapshotProvider =
    StreamProvider.family<OfflineQueueSnapshot, String>((ref, userId) async* {
  final service = ref.watch(offlineMessageQueueServiceProvider);

  Future<OfflineQueueSnapshot> load() async {
    if (userId.trim().isEmpty) {
      return OfflineQueueSnapshot.empty;
    }
    final pendingCount = await service.pendingCount(userId);
    final messages = await service.loadActiveForUser(userId);
    return OfflineQueueSnapshot(
      pendingCount: pendingCount,
      entries: messages
          .map(
            (message) => OfflineQueueEntry(
              requestId: message.requestId,
              sessionId: message.sessionId,
              message: message.message,
              status: message.status,
              createdAt: message.createdAt,
            ),
          )
          .toList(growable: false),
    );
  }

  yield await load();
  yield* Stream<void>.periodic(const Duration(seconds: 1))
      .asyncMap((_) => load());
});

final syncEngineProvider = Provider<SyncEngine>((ref) {
  final localDb = ref.watch(localDatabaseProvider);
  final wsService = ref.watch(webSocketServiceProvider);
  final apiClient = ref.watch(apiClientProvider);
  final engine = SyncEngine(localDb, wsService, apiClient)..start();
  ref.onDispose(engine.stop);
  return engine;
});

final crdtSyncManagerProvider = Provider<CRDTSyncManager>((ref) {
  final manager = CRDTSyncManager(
    ref.watch(localDatabaseProvider),
    ref.watch(syncEngineProvider),
  )..initialize();
  ref.onDispose(manager.dispose);
  return manager;
});
