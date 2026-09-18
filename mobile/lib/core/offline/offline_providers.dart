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

/// 队列横幅阶段（N-1/N-3）。
enum OfflineQueuePhase { hidden, queued, sending }

/// 排队横幅状态机（纯函数核心，可单测）。
///
/// N-1：横幅计数只含**未投递**消息（pending + sent/in-flight）。
/// 此前用 `max(pendingCount, activeCount)`，而 activeCount 把永久失败
/// 的行也计入 —— 出网成功/失败后计数纹丝不动。
/// N-3：只剩失败项时横幅必须隐藏（气泡自带「发送失败·重试」可见态），
/// 不再出现「气泡失败可重试」与「横幅正在发送」并存的矛盾。
class OfflineQueueIndicatorModel {
  const OfflineQueueIndicatorModel({
    required this.phase,
    required this.count,
  });

  const OfflineQueueIndicatorModel.hidden()
      : phase = OfflineQueuePhase.hidden,
        count = 0;

  final OfflineQueuePhase phase;
  final int count;

  static OfflineQueueIndicatorModel resolve({
    required int pendingCount,
    required int sendingCount,
    required int failedCount,
    required bool wsConnected,
  }) {
    final deliverable = pendingCount + sendingCount;
    if (deliverable <= 0) {
      return const OfflineQueueIndicatorModel.hidden();
    }
    final isSending = wsConnected || sendingCount > 0;
    return OfflineQueueIndicatorModel(
      phase: isSending ? OfflineQueuePhase.sending : OfflineQueuePhase.queued,
      count: deliverable,
    );
  }
}

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
