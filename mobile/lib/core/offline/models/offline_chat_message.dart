import 'package:isar/isar.dart';

part 'offline_chat_message.g.dart';

/// Message status for offline queue
enum OfflineMessageStatus {
  pending, // 等待发送
  sent, // 已发送到服务器
  acked, // 已收到服务器 ACK
  failed, // 发送失败
}

/// Offline chat message stored locally for reliable delivery
/// Used when network is unavailable to queue messages for later sending
@collection
class OfflineChatMessage {
  Id id = Isar.autoIncrement;

  /// Unique request ID for deduplication and ACK matching
  @Index(unique: true)
  late String requestId;

  /// Session ID this message belongs to
  @Index()
  late String sessionId;

  /// Message content
  late String message;

  /// User ID who sent the message
  @Index()
  late String userId;

  /// When this message was created locally
  @Index()
  late DateTime createdAt;

  /// Current status of the message
  @enumerated
  late OfflineMessageStatus status;

  /// Number of retry attempts
  int retryCount = 0;

  /// Last error message if failed
  String? lastError;

  /// Last send attempt timestamp
  DateTime? lastSendAttempt;

  /// Server timestamp when ACK received
  DateTime? ackedAt;

  /// Server message ID from ACK
  String? serverMessageId;

  /// Additional context (JSON serialized)
  String? extraContext;

  /// File IDs attached to this message (JSON array)
  String? fileIds;

  /// Chat mode (e.g., 'normal', 'focus', 'planning')
  String? chatMode;

  /// Nickname for display
  String? nickname;

  /// Priority for send queue (higher = more important)
  int priority = 0;
}

extension OfflineChatMessageExtension on OfflineChatMessage {
  /// Create a new pending message
  static OfflineChatMessage create({
    required String requestId,
    required String sessionId,
    required String message,
    required String userId,
    String? extraContext,
    List<String>? fileIds,
    String? chatMode,
    String? nickname,
    int priority = 0,
  }) {
    return OfflineChatMessage()
      ..requestId = requestId
      ..sessionId = sessionId
      ..message = message
      ..userId = userId
      ..createdAt = DateTime.now()
      ..status = OfflineMessageStatus.pending
      ..retryCount = 0
      ..extraContext = extraContext
      ..fileIds = fileIds != null ? fileIds.join(',') : null
      ..chatMode = chatMode
      ..nickname = nickname
      ..priority = priority;
  }

  /// Mark message as sent
  void markAsSent() {
    status = OfflineMessageStatus.sent;
    lastSendAttempt = DateTime.now();
  }

  /// Mark message as ACKed by server
  void markAsAcked(String messageId) {
    status = OfflineMessageStatus.acked;
    ackedAt = DateTime.now();
    serverMessageId = messageId;
  }

  /// Mark message as failed
  void markAsFailed(String error) {
    status = OfflineMessageStatus.failed;
    lastError = error;
    retryCount++;
    lastSendAttempt = DateTime.now();
  }

  /// Reset for retry
  void resetForRetry() {
    if (status == OfflineMessageStatus.failed) {
      status = OfflineMessageStatus.pending;
      lastError = null;
    }
  }

  /// Check if message can be retried
  bool get canRetry =>
      status == OfflineMessageStatus.failed && retryCount < 5;

  /// Check if message is in a terminal state
  bool get isTerminal =>
      status == OfflineMessageStatus.acked;

  /// Get parsed file IDs
  List<String> get parsedFileIds =>
      fileIds?.split(',').where((id) => id.isNotEmpty).toList() ?? [];

  /// Get age of message in seconds
  int get ageSeconds =>
      DateTime.now().difference(createdAt).inSeconds;
}
