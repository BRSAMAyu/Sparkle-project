import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/offline_chat_message.dart';

/// Persists outgoing chat messages to Isar when the WebSocket is disconnected,
/// and replays them on reconnect. Closes R3 audit finding O-01.
class OfflineMessageQueueService {
  OfflineMessageQueueService(this._localDb);

  final LocalDatabase _localDb;

  Isar? get _isar => _localDb.isarOrNull;

  bool get _isReady => _isar?.isOpen == true;

  /// Persist a message to the offline queue (status = pending).
  Future<void> enqueue({
    required String requestId,
    required String sessionId,
    required String message,
    required String userId,
    String? extraContext,
    List<String>? fileIds,
    String? chatMode,
    String? nickname,
  }) async {
    final db = _isar;
    if (db == null || !db.isOpen) return;
    final msg = OfflineChatMessageExtension.create(
      requestId: requestId,
      sessionId: sessionId,
      message: message,
      userId: userId,
      extraContext: extraContext,
      fileIds: fileIds,
      chatMode: chatMode,
      nickname: nickname,
    );
    await db.writeTxn(() async {
      await db.offlineChatMessages.putByRequestId(msg);
    });
  }

  /// Mark a message as sent (sink accepted it, waiting for server ACK).
  Future<void> markSent(String requestId) async {
    final db = _isar;
    if (db == null || !db.isOpen) return;
    final msg = await db.offlineChatMessages.getByRequestId(requestId);
    if (msg != null) {
      msg.markAsSent();
      await db.writeTxn(() async {
        await db.offlineChatMessages.putByRequestId(msg);
      });
    }
  }

  /// Mark a message as acked by server.
  Future<void> markAcked(String requestId, {String? serverMessageId}) async {
    final db = _isar;
    if (db == null || !db.isOpen) return;
    final msg = await db.offlineChatMessages.getByRequestId(requestId);
    if (msg != null) {
      msg.markAsAcked(serverMessageId ?? requestId);
      await db.writeTxn(() async {
        await db.offlineChatMessages.putByRequestId(msg);
      });
    }
  }

  /// Load all pending messages (not yet sent), ordered by creation time.
  Future<List<OfflineChatMessage>> loadPending() async {
    final db = _isar;
    if (db == null || !db.isOpen) return <OfflineChatMessage>[];
    final results = await db.offlineChatMessages
        .filter()
        .statusEqualTo(OfflineMessageStatus.pending)
        .findAll();
    results.sort((OfflineChatMessage a, OfflineChatMessage b) =>
        a.createdAt.compareTo(b.createdAt));
    return results;
  }

  /// Remove a message from the offline queue.
  Future<void> remove(String requestId) async {
    final db = _isar;
    if (db == null || !db.isOpen) return;
    await db.offlineChatMessages.deleteByRequestId(requestId);
  }

  /// Count pending messages for the given user.
  Future<int> pendingCount(String userId) async {
    final db = _isar;
    if (db == null || !db.isOpen) return 0;
    return db.offlineChatMessages
        .filter()
        .userIdEqualTo(userId)
        .and()
        .statusEqualTo(OfflineMessageStatus.pending)
        .count();
  }

  /// Delete acked messages older than 24 hours.
  Future<void> cleanupOldAcked() async {
    final db = _isar;
    if (db == null || !db.isOpen) return;
    final cutoff = DateTime.now().subtract(const Duration(hours: 24));
    final old = await db.offlineChatMessages
        .filter()
        .statusEqualTo(OfflineMessageStatus.acked)
        .and()
        .ackedAtIsNotNull()
        .ackedAtLessThan(cutoff)
        .findAll();
    if (old.isNotEmpty) {
      await db.writeTxn(() async {
        await db.offlineChatMessages.deleteAll(
          old.map((OfflineChatMessage e) => e.id).toList(),
        );
      });
    }
  }
}
