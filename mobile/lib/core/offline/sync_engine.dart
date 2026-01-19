import 'dart:async';
import 'dart:convert';

import 'dart:math';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:dio/dio.dart';
import 'package:fixnum/fixnum.dart';
import 'package:isar/isar.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/proto/websocket.pb.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/sync_metadata.dart';
import 'package:sparkle/core/offline/sync_metadata.dart';
import 'package:sparkle/core/services/websocket_service.dart';
import 'package:sparkle/core/tracing/tracing_service.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

class SyncEngine {
  SyncEngine(this._localDb, this._wsService, this._apiClient);

  final LocalDatabase _localDb;
  final WebSocketService _wsService;
  final ApiClient _apiClient;
  final Logger _logger = Logger();
  final Uuid _uuid = const Uuid();
  final Random _random = Random();
  Future<SharedPreferences>? _prefsFuture;
  final Connectivity _connectivity = Connectivity();
  
  StreamSubscription<void>? _subscription;
  bool _isProcessing = false;
  static const int _batchSize = 20;
  static const int _maxAttempts = 5;
  static const int _baseBackoffMs = 800;
  static const int _maxBackoffMs = 30000;
  static const Duration _waitingAckTtl = Duration(seconds: 30);

  void start() {
    // Listen for new outbox items
    final outboxStream = _localDb.isar.outboxItems
        .filter()
        .statusEqualTo(SyncStatus.pending)
        .watch(fireImmediately: true);

    _subscription = outboxStream.listen((_) {
      _processOutbox();
    });
    
    // Also listen for connectivity changes
    _connectivity.onConnectivityChanged.listen((result) {
      if (!result.contains(ConnectivityResult.none)) {
        _processOutbox();
      }
    });
  }

  void stop() {
    _subscription?.cancel();
  }

  Future<void> enqueue({
    required String topic,
    required String opType,
    required Map<String, dynamic> payload,
    String? entityType,
    String? entityId,
    String? dedupeKey,
    int priority = 0,
    bool requiresAuth = true,
    String? traceId,
  }) async {
    final item = OutboxItem()
      ..uuid = _uuid.v4()
      ..type = '$topic:$opType'
      ..topic = topic
      ..opType = opType
      ..entityType = entityType
      ..entityId = entityId
      ..payloadJson = jsonEncode(payload)
      ..dedupeKey = dedupeKey
      ..createdAt = DateTime.now()
      ..priority = priority
      ..requiresAuth = requiresAuth
      ..traceId = traceId
      ..status = SyncStatus.pending;

    await _localDb.isar.writeTxn(() async {
      await _localDb.isar.outboxItems.put(item);
    });
    
    // Trigger processing immediately just in case watch doesn't catch it instantly
    _processOutbox();
  }

  @Deprecated('Use enqueue with topic/opType.')
  Future<void> enqueueLegacy(String type, Map<String, dynamic> payload) async {
    await enqueue(
      topic: 'legacy',
      opType: type,
      payload: payload,
      entityType: null,
      entityId: null,
      dedupeKey: null,
    );
  }

  Future<void> processNow({bool force = false, bool skipConnectivity = false}) async {
    await _processOutbox(force: force, skipConnectivity: skipConnectivity);
  }

  Future<void> _processOutbox({bool force = false, bool skipConnectivity = false}) async {
    if (_isProcessing) return;
    
    // Check connectivity
    if (!skipConnectivity) {
      final connectivity = await _connectivity.checkConnectivity();
      if (connectivity.contains(ConnectivityResult.none)) return;
    }

    _isProcessing = true;

    try {
      await _requeueStuckWaitingAck();
      while (true) {
        final now = DateTime.now();
        final QueryBuilder<OutboxItem, OutboxItem, QAfterFilterCondition>
            baseQuery = force
                ? _localDb.isar.outboxItems.filter().group(
                      (q) => q
                          .statusEqualTo(SyncStatus.pending)
                          .or()
                          .statusEqualTo(SyncStatus.failed),
                    )
                : _localDb.isar.outboxItems
                    .filter()
                    .statusEqualTo(SyncStatus.pending);

        var itemsQuery = baseQuery;
        if (!force) {
          itemsQuery = itemsQuery
              .and()
              .group(
                (q) => q
                    .nextAttemptAtIsNull()
                    .or()
                    .nextAttemptAtLessThan(now),
              );
        }

        var items = await itemsQuery.findAll()
          ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
        if (items.length > _batchSize) {
          items = items.sublist(0, _batchSize);
        }

        if (items.isEmpty) break;

        for (final item in items) {
          await _processItem(item);
        }
      }
    } finally {
      _isProcessing = false;
    }
  }

  Future<void> _processItem(OutboxItem item) async {
    try {
      final sendTime = DateTime.now();
      await _localDb.isar.writeTxn(() async {
        item.status = SyncStatus.waitingAck;
        item.lastSentAt = sendTime;
        item.nextAttemptAt = sendTime.add(_waitingAckTtl);
        await _localDb.isar.outboxItems.put(item);
      });

      final payloadJson = item.payloadJson ?? '{}';
      final payload = jsonDecode(payloadJson) as Map<String, dynamic>;
      
      final descriptor = _describeItem(item);
      _logger.d(
        'Processing outbox item: ${descriptor.topic}/${descriptor.opType} (${item.id})',
      );

      switch (descriptor.topic) {
        case 'knowledge':
          await _sendMasteryUpdate(payload, item);
          break;
        case 'crdt':
          await _sendCrdtUpdate(payload);
          break;
        case 'cognitive':
          await _sendCognitiveFragmentCreate(payload, item);
          break;
        case 'intervention_requests':
          await _sendInterventionRequest(payload);
          break;
        case 'intervention_feedback':
          await _sendInterventionFeedback(payload);
          break;
        case 'intervention_passive_signals':
          await _sendInterventionPassiveSignal(payload);
          break;
        case 'intervention_outcomes':
          await _sendInterventionOutcome(payload);
          break;
        default:
          _logger.w(
            'Unknown outbox item: ${descriptor.topic}/${descriptor.opType}',
          );
      }

      final current = await _localDb.isar.outboxItems.get(item.id);
      if (current == null) {
        _logger.w('Outbox item missing after send: ${item.id}');
        return;
      }
      if (current.status != SyncStatus.waitingAck ||
          current.lastSentAt != sendTime) {
        _logger.w(
          'Ack ignored for item ${item.id}; status=${current.status.name}',
        );
        return;
      }

      // Success: delete or mark synced
      await _localDb.isar.writeTxn(() async {
        current.status = SyncStatus.synced;
        // Option A: Delete to keep table small
        // await _localDb.isar.outboxItems.delete(item.id);
        // Option B: Keep for history (with TTL cleaner)
        await _localDb.isar.outboxItems.put(current);
      });
      await _recordSuccess();

    } catch (e) {
      _logger.e('Failed to process outbox item ${item.id}: $e');
      
      await _localDb.isar.writeTxn(() async {
        item.attemptCount++;
        item.retryCount = item.attemptCount;
        item.error = e.toString();
        item.lastErrorCode = _errorCode(e);
        item.nextAttemptAt = _nextAttempt(item.attemptCount);

        if (item.attemptCount >= _maxAttempts) {
          item.status = SyncStatus.failed;
        } else {
          item.status = SyncStatus.pending;
        }
        await _localDb.isar.outboxItems.put(item);
      });
    }
  }

  Future<void> _sendMasteryUpdate(Map<String, dynamic> payload, OutboxItem item) async {
    // P3: Use Protobuf Binary Protocol
    final traceId = item.traceId ?? TracingService.instance.createTraceId();
    final requestId = item.uuid ?? item.id.toString();
    final request = UpdateNodeMasteryRequest(
      nodeId: payload['nodeId'] as String,
      mastery: payload['mastery'] as int,
      timestamp: Int64(DateTime.now().millisecondsSinceEpoch),
      requestId: requestId,
      // revision: payload['revision'] as int? ?? 0, 
    );

    final wsMsg = WebSocketMessage(
      version: '2.0',
      type: 'update_node_mastery',
      payload: request.writeToBuffer(),
      timestamp: Int64(DateTime.now().millisecondsSinceEpoch),
      requestId: requestId,
      traceId: traceId,
    );

    _wsService.send(wsMsg);

    await _waitForAck(requestId).timeout(
      const Duration(seconds: 5),
      onTimeout: () => throw SyncFailure('ACK_TIMEOUT', 'Ack timeout'),
    );
  }
  
  Future<void> _sendCrdtUpdate(Map<String, dynamic> payload) async {
      final traceId = TracingService.instance.createTraceId();
      _wsService.send({
        'type': 'crdt_update',
        'trace_id': traceId,
        'payload': payload,
      });
  }

  Future<void> _sendCognitiveFragmentCreate(
    Map<String, dynamic> payload,
    OutboxItem item,
  ) async {
    try {
      await _apiClient.post<dynamic>(
        ApiEndpoints.cognitiveFragments,
        data: payload,
      );
    } on DioException catch (e) {
      rethrow;
    }
  }

  Future<void> _sendInterventionRequest(Map<String, dynamic> payload) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.interventionsRequest,
      data: payload,
    );
  }

  Future<void> _sendInterventionFeedback(Map<String, dynamic> payload) async {
    final interventionId = payload['intervention_id'] as String?;
    if (interventionId == null || interventionId.isEmpty) {
      throw SyncFailure('MISSING_INTERVENTION_ID', 'Missing intervention_id');
    }
    await _apiClient.post<dynamic>(
      ApiEndpoints.interventionFeedback(interventionId),
      data: {
        'feedback_type': payload['feedback_type'] ?? 'ignore',
        'extra_data': payload,
      },
    );
  }

  Future<void> _sendInterventionPassiveSignal(Map<String, dynamic> payload) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.interventionsPassiveSignals,
      data: payload,
    );
  }

  Future<void> _sendInterventionOutcome(Map<String, dynamic> payload) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.interventionsOutcomes,
      data: payload,
    );
  }

  _OutboxDescriptor _describeItem(OutboxItem item) {
    if (item.topic != null && item.opType != null) {
      return _OutboxDescriptor(item.topic!, item.opType!);
    }

    final legacyType = item.type ?? 'unknown';
    switch (legacyType) {
      case 'mastery_update':
        return _OutboxDescriptor('knowledge', 'update');
      case 'crdt_update':
        return _OutboxDescriptor('crdt', 'update');
      default:
        return _OutboxDescriptor('legacy', legacyType);
    }
  }

  DateTime _nextAttempt(int attemptCount) {
    final backoffMs = min(_baseBackoffMs * pow(2, attemptCount), _maxBackoffMs);
    final jitterMs = _random.nextInt(250);
    return DateTime.now()
        .add(Duration(milliseconds: backoffMs.toInt() + jitterMs));
  }

  String? _errorCode(Object error) {
    if (error is SyncFailure) {
      return error.code;
    }
    if (error is DioException) {
      final status = error.response?.statusCode;
      if (status != null) {
        if (status == 401) {
          return 'AUTH_401';
        }
        if (status == 429) {
          return 'RATE_429';
        }
        if (status >= 500) {
          return 'SERVER_5XX';
        }
        return 'HTTP_$status';
      }
      switch (error.type) {
        case DioExceptionType.connectionTimeout:
        case DioExceptionType.receiveTimeout:
        case DioExceptionType.sendTimeout:
          return 'TIMEOUT';
        case DioExceptionType.connectionError:
        case DioExceptionType.unknown:
          return 'NETWORK';
        default:
          return error.type.name;
      }
    }
    return error.runtimeType.toString();
  }

  Future<void> _waitForAck(String requestId) {
    final completer = Completer<void>();
    late final StreamSubscription<dynamic> subscription;

    subscription = _wsService.stream.listen((message) {
      if (message is Map) {
        final type = message['type'];
        final payload = message['payload'];
        if (payload is! Map || payload['requestId'] != requestId) return;

        if (type == 'ack_node_mastery') {
          completer.complete();
        } else if (type == 'error_node_mastery') {
          completer.completeError(
            SyncFailure(
              'ACK_ERROR',
              (payload['error'] as String?) ?? 'Ack error',
            ),
          );
        }
      }
    });

    return completer.future.whenComplete(subscription.cancel);
  }

  @visibleForTesting
  Future<void> requeueStuckWaitingAckForTest() => _requeueStuckWaitingAck();

  Future<void> _requeueStuckWaitingAck() async {
    final now = DateTime.now();
    final candidates = await _localDb.isar.outboxItems
        .filter()
        .statusEqualTo(SyncStatus.waitingAck)
        .and()
        .group(
          (q) => q.nextAttemptAtLessThan(now).or().nextAttemptAtIsNull(),
        )
        .findAll();

    final stuckItems = candidates.where((item) {
      final lastSentAt = item.lastSentAt;
      if (lastSentAt == null) return false;
      return lastSentAt.isBefore(now.subtract(_waitingAckTtl));
    }).toList();

    if (stuckItems.isEmpty) return;

    await _localDb.isar.writeTxn(() async {
      for (final item in stuckItems) {
        item.attemptCount++;
        item.retryCount = item.attemptCount;
        item.status = SyncStatus.pending;
        item.lastErrorCode = 'ACK_TIMEOUT';
        item.error = 'Ack timeout';
        item.nextAttemptAt = _nextAttempt(item.attemptCount);
        await _localDb.isar.outboxItems.put(item);
      }
    });
  }

  Future<void> _recordSuccess() async {
    final prefs = await _getPrefs();
    await prefs.setString(
      SyncMetadataKeys.lastSuccessAt,
      DateTime.now().toIso8601String(),
    );
  }

  Future<SharedPreferences> _getPrefs() {
    _prefsFuture ??= SharedPreferences.getInstance();
    return _prefsFuture!;
  }
}

class _OutboxDescriptor {
  _OutboxDescriptor(this.topic, this.opType);
  final String topic;
  final String opType;
}

class SyncFailure implements Exception {
  SyncFailure(this.code, this.message);
  final String code;
  final String message;

  @override
  String toString() => message;
}
