import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

class ClientObservabilityService {
  ClientObservabilityService._();
  static final ClientObservabilityService instance =
      ClientObservabilityService._();
  static const String _queuePrefsKey = 'client_observability_offline_queue';
  static const int _maxQueuedEvents = 200;
  static const int _batchSize = 20;

  Dio? _dio;
  bool _flushScheduled = false;
  bool _isFlushing = false;
  SharedPreferences? _prefs;
  Timer? _periodicFlushTimer;

  void attachDio(Dio dio) {
    _dio = dio;
    _periodicFlushTimer ??= Timer.periodic(
      const Duration(seconds: 30),
      (_) => _scheduleFlush(),
    );
    _scheduleFlush();
  }

  void dispose() {
    _periodicFlushTimer?.cancel();
    _periodicFlushTimer = null;
    _dio = null;
  }

  Future<void> recordEvent({
    required String eventType,
    required String category,
    String? route,
    String status = 'ok',
    String severity = 'info',
    int? durationMs,
    Map<String, dynamic>? metadata,
  }) async {
    final payload = <String, dynamic>{
      'event_type': eventType,
      'category': category,
      'route': route,
      'status': status,
      'severity': severity,
      'duration_ms': durationMs,
      'metadata': <String, dynamic>{
        'platform': defaultTargetPlatform.name,
        ...?metadata,
      },
      'occurred_at': DateTime.now().toUtc().toIso8601String(),
    };

    if (_dio == null) {
      await _enqueue(payload);
      return;
    }

    try {
      await _postBatch(<Map<String, dynamic>>[payload]);
    } catch (_) {
      await _enqueue(payload);
      _scheduleFlush();
    }
  }

  Future<void> trackScreenView(String routeName) => recordEvent(
      eventType: 'screen_view',
      category: 'navigation',
      route: routeName,
    );

  Future<void> trackInteraction(
    String interactionName, {
    String? route,
    String status = 'ok',
    int? durationMs,
    Map<String, dynamic>? metadata,
  }) => recordEvent(
      eventType: 'interaction',
      category: 'ux',
      route: route,
      status: status,
      durationMs: durationMs,
      metadata: <String, dynamic>{
        'interaction_name': interactionName,
        ...?metadata,
      },
    );

  Future<void> trackApiRequest({
    required String path,
    required String method,
    required String status,
    required int durationMs,
    int? statusCode,
    String? message,
  }) => recordEvent(
      eventType: 'api_request',
      category: 'network',
      route: path,
      status: status,
      durationMs: durationMs,
      severity: status == 'ok' ? 'info' : 'warning',
      metadata: <String, dynamic>{
        'method': method,
        'status_code': statusCode,
        'message': message,
      },
    );

  Future<void> trackCrash(
    Object error,
    StackTrace stackTrace, {
    String? context,
  }) => recordEvent(
      eventType: 'crash',
      category: 'stability',
      status: 'error',
      severity: 'critical',
      metadata: <String, dynamic>{
        'context': context,
        'error': error.toString(),
        'stack_trace': stackTrace.toString(),
      },
    );

  void _scheduleFlush() {
    if (_flushScheduled || _isFlushing) {
      return;
    }
    _flushScheduled = true;
    unawaited(
      Future<void>.delayed(const Duration(milliseconds: 100), () async {
        _flushScheduled = false;
        if (_dio == null) {
          return;
        }
        _isFlushing = true;
        try {
          final queue = await _readQueue();
          if (queue.isEmpty) {
            return;
          }
          final batch = queue.take(_batchSize).toList();
          await _postBatch(batch);
          final remaining = queue.skip(batch.length).toList();
          await _writeQueue(remaining);
          if (remaining.isNotEmpty) {
            _scheduleFlush();
          }
        } catch (_) {
          // Keep the queue intact and retry on next schedule/attach.
        } finally {
          _isFlushing = false;
        }
      }),
    );
  }

  Future<void> _postBatch(List<Map<String, dynamic>> events) async {
    if (_dio == null || events.isEmpty) {
      return;
    }
    await _dio!.post<void>(
      ApiEndpoints.clientTelemetryEventsBatch,
      data: <String, dynamic>{'events': events},
      options: Options(
        extra: <String, dynamic>{
          'skip_client_telemetry': true,
        },
      ),
    );
  }

  Future<void> _enqueue(Map<String, dynamic> payload) async {
    final queue = await _readQueue();
    queue.add(payload);
    final start = queue.length > _maxQueuedEvents
        ? queue.length - _maxQueuedEvents
        : 0;
    await _writeQueue(queue.sublist(start));
  }

  Future<SharedPreferences> _preferences() async {
    _prefs ??= await SharedPreferences.getInstance();
    return _prefs!;
  }

  Future<List<Map<String, dynamic>>> _readQueue() async {
    final prefs = await _preferences();
    final raw = prefs.getString(_queuePrefsKey);
    if (raw == null || raw.isEmpty) {
      return <Map<String, dynamic>>[];
    }
    try {
      final decoded = jsonDecode(raw);
      if (decoded is List) {
        return decoded
            .whereType<Map<Object?, Object?>>()
            .map(Map<String, dynamic>.from)
            .toList();
      }
    } catch (error) {
      debugPrint('Failed to decode client telemetry offline queue: $error');
    }
    return <Map<String, dynamic>>[];
  }

  Future<void> _writeQueue(List<Map<String, dynamic>> items) async {
    final prefs = await _preferences();
    await prefs.setString(_queuePrefsKey, jsonEncode(items));
  }
}
