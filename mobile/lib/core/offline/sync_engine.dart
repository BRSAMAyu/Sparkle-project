import 'dart:async';
import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:fixnum/fixnum.dart';
import 'package:isar/isar.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/network/proto/websocket.pb.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/services/websocket_service.dart';
import 'package:sparkle/core/tracing/tracing_service.dart';

class SyncEngine {
  SyncEngine(this._localDb, this._wsService);

  final LocalDatabase _localDb;
  final WebSocketService _wsService;
  final Logger _logger = Logger();
  
  StreamSubscription<void>? _subscription;
  bool _isProcessing = false;

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
    Connectivity().onConnectivityChanged.listen((result) {
      if (!result.contains(ConnectivityResult.none)) {
        _processOutbox();
      }
    });
  }

  void stop() {
    _subscription?.cancel();
  }

  Future<void> enqueue(String type, Map<String, dynamic> payload) async {
    final item = OutboxItem()
      ..type = type
      ..payloadJson = jsonEncode(payload)
      ..createdAt = DateTime.now()
      ..status = SyncStatus.pending;

    await _localDb.isar.writeTxn(() async {
      await _localDb.isar.outboxItems.put(item);
    });
    
    // Trigger processing immediately just in case watch doesn't catch it instantly
    _processOutbox();
  }

  Future<void> _processOutbox() async {
    if (_isProcessing) return;
    
    // Check connectivity
    final connectivity = await Connectivity().checkConnectivity();
    if (connectivity.contains(ConnectivityResult.none)) return;

    _isProcessing = true;

    try {
      while (true) {
        final item = await _localDb.isar.outboxItems
            .filter()
            .statusEqualTo(SyncStatus.pending)
            .sortByCreatedAt()
            .findFirst();

        if (item == null) break;

        await _processItem(item);
      }
    } finally {
      _isProcessing = false;
    }
  }

  Future<void> _processItem(OutboxItem item) async {
    try {
      // Mark as processing (optional, depends on if we want a separate status)
      // For now, keep as pending but maybe increment retryCount if failed before?

      final payload = jsonDecode(item.payloadJson) as Map<String, dynamic>;
      
      _logger.d('Processing outbox item: ${item.type} (${item.id})');

      switch (item.type) {
        case 'mastery_update':
          await _sendMasteryUpdate(payload, item);
          break;
        case 'crdt_update':
          await _sendCrdtUpdate(payload);
          break;
        case 'chat_message':
           // TODO: Implement chat message sync
           break;
        default:
          _logger.w('Unknown outbox item type: ${item.type}');
      }

      // Success: delete or mark synced
      await _localDb.isar.writeTxn(() async {
        item.status = SyncStatus.synced;
        // Option A: Delete to keep table small
        // await _localDb.isar.outboxItems.delete(item.id);
        // Option B: Keep for history (with TTL cleaner)
        await _localDb.isar.outboxItems.put(item);
      });

    } catch (e) {
      _logger.e('Failed to process outbox item ${item.id}: $e');
      
      await _localDb.isar.writeTxn(() async {
        item.retryCount++;
        item.error = e.toString();
        if (item.retryCount > 5) {
          item.status = SyncStatus.failed;
        } else {
          // Keep pending, maybe add backoff delay logic here or in loop
        }
        await _localDb.isar.outboxItems.put(item);
      });
    }
  }

  Future<void> _sendMasteryUpdate(Map<String, dynamic> payload, OutboxItem item) async {
    // P3: Use Protobuf Binary Protocol
    final traceId = TracingService.instance.createTraceId();
    final request = UpdateNodeMasteryRequest(
      nodeId: payload['nodeId'] as String,
      mastery: payload['mastery'] as int,
      timestamp: Int64(DateTime.now().millisecondsSinceEpoch),
      requestId: item.id.toString(), // Use local ID for tracking? Or generated UUID
      // revision: payload['revision'] as int? ?? 0, 
    );

    final wsMsg = WebSocketMessage(
      version: '2.0',
      type: 'update_node_mastery',
      payload: request.writeToBuffer(),
      timestamp: Int64(DateTime.now().millisecondsSinceEpoch),
      requestId: item.id.toString(),
      traceId: traceId,
    );

    _wsService.send(wsMsg);
    
    // ideally wait for ACK via a completer mapped to requestId
    await Future.delayed(const Duration(milliseconds: 100)); 
  }
  
  Future<void> _sendCrdtUpdate(Map<String, dynamic> payload) async {
      final traceId = TracingService.instance.createTraceId();
      _wsService.send({
        'type': 'crdt_update',
        'trace_id': traceId,
        'payload': payload,
      });
  }
}
