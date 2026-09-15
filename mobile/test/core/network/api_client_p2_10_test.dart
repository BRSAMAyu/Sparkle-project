import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_interceptor.dart';
import 'package:sparkle/features/auth/data/models/token_model.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show sharedPreferencesProvider;
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';

import '../p2_10_core_service_test_harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late _FakeAuthRepository authRepository;
  late _SequenceAdapter adapter;
  late _SequenceAdapter retryAdapter;
  late Dio retryDio;
  late ProviderContainer container;
  late ApiClient client;

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final prefs = await SharedPreferences.getInstance();
    authRepository = _FakeAuthRepository(
      accessToken: 'old-access',
      refreshTokenValue: 'refresh-token',
    );
    adapter = _SequenceAdapter();
    retryAdapter = _SequenceAdapter();
    retryDio = Dio(BaseOptions(baseUrl: 'https://api.example.test'))
      ..httpClientAdapter = retryAdapter;
    container = ProviderContainer(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        authRepositoryProvider.overrideWithValue(authRepository),
        activeGoalHeaderProvider.overrideWithValue('goal-1'),
        authInterceptorProvider.overrideWith(
          (ref) => AuthInterceptor(ref, retryDioForTesting: retryDio),
        ),
      ],
    );
    client = container.read(apiClientProvider);
    client.dio.httpClientAdapter = adapter;
  });

  tearDown(() => container.dispose());

  test('GET attaches auth device and active-goal headers', () async {
    adapter.enqueue(
      statusCode: 200,
      data: const <String, dynamic>{'ok': true},
    );

    final response = await client.get<Map<String, dynamic>>('/profile');

    expect(response.data, containsPair('ok', true));
    expect(
      adapter.records.single.headers['Authorization'],
      'Bearer old-access',
    );
    expect(adapter.records.single.headers['X-Current-Goal-ID'], 'goal-1');
    expect(adapter.records.single.headers['X-Device-Id'], isNotEmpty);
    expect(adapter.records.single.headers['X-Device-Platform'], isNotEmpty);
  });

  test('POST forwards JSON body and query parameters', () async {
    adapter.enqueue(
      statusCode: 200,
      data: const <String, dynamic>{'ok': true},
    );

    await client.post<Map<String, dynamic>>(
      '/events',
      data: const <String, dynamic>{'event': 'tap'},
      queryParameters: const <String, dynamic>{'dry_run': true},
    );

    expect(adapter.records.single.method, 'POST');
    expect(adapter.records.single.path, '/events');
    expect(
      adapter.records.single.queryParameters,
      containsPair('dry_run', true),
    );
    expect(adapter.records.single.body, {'event': 'tap'});
  });

  test('RetryInterceptor retries transient 503 responses', () async {
    adapter
      ..enqueue(statusCode: 503, data: const <String, dynamic>{'error': 'busy'})
      ..enqueue(statusCode: 200, data: const <String, dynamic>{'ok': true});

    final response = await client.get<Map<String, dynamic>>('/retry-me');

    expect(response.data, containsPair('ok', true));
    expect(adapter.records, hasLength(2));
    expect(
      adapter.records.map((record) => record.path),
      everyElement('/retry-me'),
    );
  });

  test('401 responses refresh the token and retry with new Authorization',
      () async {
    adapter.enqueue(
      statusCode: 401,
      data: const <String, dynamic>{'detail': 'expired'},
    );
    retryAdapter.enqueue(
      statusCode: 200,
      data: const <String, dynamic>{'ok': true},
    );

    final response = await client.get<Map<String, dynamic>>('/protected');

    expect(response.data, containsPair('ok', true));
    expect(authRepository.refreshCalls, 1);
    expect(
      adapter.records.single.headers['Authorization'],
      'Bearer old-access',
    );
    expect(
      retryAdapter.records.single.headers['Authorization'],
      'Bearer refreshed-access',
    );
  });

  test('connection timeouts surface as DioException timeouts', () async {
    adapter.enqueueException(
      (options) => DioException(
        requestOptions: options,
        type: DioExceptionType.connectionTimeout,
      ),
    );

    expect(
      client.get<Map<String, dynamic>>('/timeout'),
      throwsA(
        isA<DioException>().having(
          (error) => error.type,
          'type',
          DioExceptionType.connectionTimeout,
        ),
      ),
    );
  });
}

class _FakeAuthRepository implements AuthRepository {
  _FakeAuthRepository({
    required this.accessToken,
    required this.refreshTokenValue,
  });

  String? accessToken;
  String? refreshTokenValue;
  int refreshCalls = 0;
  int logoutCalls = 0;

  @override
  Future<String?> getAccessToken() async => accessToken;

  @override
  Future<String?> getToken() async => accessToken;

  @override
  Future<String?> getRefreshToken() async => refreshTokenValue;

  @override
  Future<TokenResponse> refreshToken() async {
    refreshCalls++;
    accessToken = 'refreshed-access';
    return TokenResponse(
      accessToken: 'refreshed-access',
      refreshToken: refreshTokenValue,
    );
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {
    logoutCalls++;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _AdapterRecord {
  const _AdapterRecord({
    required this.method,
    required this.path,
    required this.headers,
    required this.queryParameters,
    required this.body,
  });

  final String method;
  final String path;
  final Map<String, dynamic> headers;
  final Map<String, dynamic> queryParameters;
  final Map<String, dynamic> body;
}

class _QueuedAdapterStep {
  const _QueuedAdapterStep.response({
    required this.statusCode,
    required this.data,
  }) : exceptionBuilder = null;

  const _QueuedAdapterStep.exception(this.exceptionBuilder)
      : statusCode = 0,
        data = null;

  final int statusCode;
  final Object? data;
  final DioException Function(RequestOptions options)? exceptionBuilder;
}

class _SequenceAdapter implements HttpClientAdapter {
  final List<_QueuedAdapterStep> _steps = <_QueuedAdapterStep>[];
  final List<_AdapterRecord> records = <_AdapterRecord>[];

  void enqueue({required int statusCode, Object? data}) {
    _steps.add(_QueuedAdapterStep.response(statusCode: statusCode, data: data));
  }

  void enqueueException(DioException Function(RequestOptions options) builder) {
    _steps.add(_QueuedAdapterStep.exception(builder));
  }

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    records.add(
      _AdapterRecord(
        method: options.method,
        path: options.path,
        headers: Map<String, dynamic>.from(options.headers),
        queryParameters: Map<String, dynamic>.from(options.queryParameters),
        body: await readJsonRequestBody(requestStream),
      ),
    );
    if (_steps.isEmpty) {
      throw StateError('No queued adapter response for ${options.path}');
    }
    final step = _steps.removeAt(0);
    final exceptionBuilder = step.exceptionBuilder;
    if (exceptionBuilder != null) {
      throw exceptionBuilder(options);
    }
    final body =
        step.data is String ? step.data! as String : jsonEncode(step.data);
    return ResponseBody.fromString(
      body,
      step.statusCode,
      headers: <String, List<String>>{
        Headers.contentTypeHeader: <String>['application/json'],
      },
    );
  }
}
