import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';

import '../p2_10_core_service_test_harness.dart';

void main() {
  late RecordingApiClient apiClient;
  late _FakeAuthRepository authRepository;
  late ProviderContainer container;
  late AppEventStreamService service;

  setUp(() {
    apiClient = RecordingApiClient();
    authRepository = _FakeAuthRepository(accessToken: 'access-token');
    container = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWithValue(apiClient),
        authRepositoryProvider.overrideWithValue(authRepository),
      ],
    );
    service = container.read(appEventStreamServiceProvider);
  });

  tearDown(() => container.dispose());

  test('ingestEvents skips empty batches before reading auth state', () async {
    await service.ingestEvents(const <Map<String, dynamic>>[]);

    expect(authRepository.accessTokenReads, 0);
    expect(apiClient.requests, isEmpty);
  });

  test('ingestEvents skips upload when access token is absent', () async {
    authRepository.accessToken = null;

    await service.ingestEvents(const <Map<String, dynamic>>[
      {'event_type': 'demo', 'source': 'test', 'ts_ms': 1},
    ]);

    expect(authRepository.accessTokenReads, 1);
    expect(apiClient.requests, isEmpty);
  });

  test('ingestEvents posts the batch to the ingest endpoint', () async {
    await service.ingestEvents(const <Map<String, dynamic>>[
      {'event_type': 'demo', 'source': 'test', 'ts_ms': 1},
    ]);

    expect(apiClient.requests.single.path, ApiEndpoints.eventsIngest);
    expect(apiClient.requests.single.data, {
      'events': [
        {'event_type': 'demo', 'source': 'test', 'ts_ms': 1},
      ],
    });
  });

  test('ingestEvents swallows API failures after attempting persistence',
      () async {
    apiClient.onPost = (request) async {
      throw DioException(
        requestOptions: RequestOptions(path: request.path),
        type: DioExceptionType.connectionError,
      );
    };

    await service.ingestEvents(const <Map<String, dynamic>>[
      {'event_type': 'demo', 'source': 'test', 'ts_ms': 1},
    ]);

    expect(apiClient.requests, hasLength(1));
  });

  test('recordPredictionFeedback builds a structured prediction event',
      () async {
    await service.recordPredictionFeedback(
      predictionId: 'prediction-1',
      feedbackType: 'accepted',
      actionType: 'create_task',
      surface: 'today',
      suggestedPrompt: 'Practice vectors',
      entityType: 'task',
      entityId: 'task-1',
      extraPayload: const <String, dynamic>{'rank': 2},
    );

    final payload = apiClient.requests.single.data as Map<String, dynamic>;
    final event =
        (payload['events'] as List<dynamic>).single as Map<String, dynamic>;

    expect(event['event_type'], 'prediction_accepted');
    expect(event['schema_version'], 'event.v1');
    expect(event['source'], 'prediction_surface');
    expect(event['event_id'], startsWith('prediction_accepted:'));
    expect(
      event['entities'],
      containsPair('prediction_id', 'prediction-1'),
    );
    expect(event['entities'], containsPair('entity_id', 'task-1'));
    expect(event['payload'], containsPair('action_type', 'create_task'));
    expect(event['payload'], containsPair('surface', 'today'));
    expect(event['payload'], containsPair('rank', 2));
  });
}

class _FakeAuthRepository implements AuthRepository {
  _FakeAuthRepository({this.accessToken});

  String? accessToken;
  int accessTokenReads = 0;

  @override
  Future<String?> getAccessToken() async {
    accessTokenReads++;
    return accessToken;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
