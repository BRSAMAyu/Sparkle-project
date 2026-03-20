import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/client_observability_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('ClientObservabilityService flushes offline queue in batch', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'client_observability_offline_queue': jsonEncode([
        <String, dynamic>{
          'event_type': 'screen_view',
          'category': 'navigation',
          'route': '/chat',
          'status': 'ok',
          'severity': 'info',
          'duration_ms': 18,
          'metadata': <String, dynamic>{'platform': 'ios'},
          'occurred_at': DateTime.utc(2026, 3, 21, 0, 0, 0).toIso8601String(),
        },
      ]),
    });

    final adapter = _RecordingAdapter();
    final dio = Dio()
      ..httpClientAdapter = adapter
      ..options.baseUrl = 'https://example.test';

    ClientObservabilityService.instance.attachDio(dio);
    await Future<void>.delayed(const Duration(milliseconds: 350));

    final prefs = await SharedPreferences.getInstance();
    final queueRaw = prefs.getString('client_observability_offline_queue');
    final decoded = jsonDecode(queueRaw ?? '[]') as List<dynamic>;

    expect(adapter.requests, hasLength(1));
    expect(adapter.requests.single.path, ApiEndpoints.clientTelemetryEventsBatch);
    expect(adapter.requests.single.payload['events'], hasLength(1));
    expect(decoded, isEmpty);
  });
}

class _RecordedRequest {
  const _RecordedRequest({
    required this.path,
    required this.payload,
  });

  final String path;
  final Map<String, dynamic> payload;
}

class _RecordingAdapter implements HttpClientAdapter {
  final List<_RecordedRequest> requests = <_RecordedRequest>[];

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final chunks = <int>[];
    if (requestStream != null) {
      await for (final chunk in requestStream) {
        chunks.addAll(chunk);
      }
    }
    final payload = chunks.isEmpty
        ? <String, dynamic>{}
        : Map<String, dynamic>.from(
            jsonDecode(utf8.decode(chunks)) as Map<String, dynamic>,
          );
    requests.add(
      _RecordedRequest(
        path: options.path,
        payload: payload,
      ),
    );
    return ResponseBody.fromString(
      '{"accepted":true,"storage":"redis","accepted_count":1,"events":[]}',
      200,
      headers: <String, List<String>>{
        Headers.contentTypeHeader: <String>['application/json'],
      },
    );
  }
}
