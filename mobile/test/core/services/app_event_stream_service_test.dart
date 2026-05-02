import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';

class _StubApiClient implements ApiClient {
  bool postCalled = false;
  String? lastPath;
  Object? lastData;
  bool shouldThrow = false;

  @override
  Dio get dio => Dio();

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    postCalled = true;
    lastPath = path;
    lastData = data;
    if (shouldThrow) {
      throw DioException(requestOptions: RequestOptions(path: path));
    }
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      statusCode: 200,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StubAuthRepository implements AuthRepository {
  String? _accessToken;

  _StubAuthRepository([this._accessToken = 'valid-token']);

  @override
  Future<String?> getAccessToken() async => _accessToken;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  late _StubApiClient apiClient;
  late _StubAuthRepository authRepository;
  late ProviderContainer container;

  setUp(() {
    apiClient = _StubApiClient();
    authRepository = _StubAuthRepository();
    container = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWithValue(apiClient),
        authRepositoryProvider.overrideWithValue(authRepository),
      ],
    );
  });

  tearDown(() {
    container.dispose();
  });

  test('ingestEvents skips upload when access token is unavailable', () async {
    authRepository = _StubAuthRepository(null);
    final localContainer = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWithValue(apiClient),
        authRepositoryProvider.overrideWithValue(authRepository),
      ],
    );
    addTearDown(localContainer.dispose);

    final service = localContainer.read(appEventStreamServiceProvider);
    await service.ingestEvents([
      {'event_type': 'demo', 'source': 'test', 'ts_ms': 1},
    ]);

    expect(apiClient.postCalled, isFalse);
  });

  test('ingestEvents skips upload when events list is empty', () async {
    final service = container.read(appEventStreamServiceProvider);
    await service.ingestEvents([]);
    expect(apiClient.postCalled, isFalse);
  });

  test('ingestEvents posts events when token is available', () async {
    final service = container.read(appEventStreamServiceProvider);
    await service.ingestEvents([
      {'event_type': 'test', 'source': 'unit', 'ts_ms': 1},
    ]);
    expect(apiClient.postCalled, isTrue);
    expect(apiClient.lastPath, ApiEndpoints.eventsIngest);
  });

  test('ingestEvents swallows exceptions gracefully', () async {
    apiClient.shouldThrow = true;
    final service = container.read(appEventStreamServiceProvider);
    // Should not throw
    await service.ingestEvents([
      {'event_type': 'test', 'source': 'unit', 'ts_ms': 1},
    ]);
    expect(apiClient.postCalled, isTrue);
  });

  test('recordPredictionFeedback posts prediction event', () async {
    final service = container.read(appEventStreamServiceProvider);
    await service.recordPredictionFeedback(
      predictionId: 'pred-1',
      feedbackType: 'accepted',
      actionType: 'click',
      surface: 'chat',
    );
    expect(apiClient.postCalled, isTrue);
    final data = apiClient.lastData as Map<String, dynamic>;
    final events = data['events'] as List;
    expect(events.length, 1);
    expect(events.first['event_type'], 'prediction_accepted');
  });

  test('recordLearningPathGenerated posts learning_path event', () async {
    final service = container.read(appEventStreamServiceProvider);
    await service.recordLearningPathGenerated(
      targetNodeId: 'node-1',
      planId: 'plan-1',
      taskIds: ['t1', 't2'],
    );
    expect(apiClient.postCalled, isTrue);
    final data = apiClient.lastData as Map<String, dynamic>;
    final events = data['events'] as List;
    expect(events.first['payload']['task_count'], 2);
  });

  test('recordEntityExecution posts entity_execution event', () async {
    final service = container.read(appEventStreamServiceProvider);
    await service.recordEntityExecution(
      entityType: 'task',
      entityId: 'task-1',
      actionType: 'complete',
      source: 'task_screen',
    );
    expect(apiClient.postCalled, isTrue);
    final data = apiClient.lastData as Map<String, dynamic>;
    final events = data['events'] as List;
    expect(events.first['event_type'], 'entity_execution');
  });
}
