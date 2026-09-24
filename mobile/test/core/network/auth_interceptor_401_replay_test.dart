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

/// F-11（WT324 实测）· 401 → 刷新 → 重放两分支拦截器级回归。
///
/// 现场证据：任务列表「部分数据刷新失败」横幅 transient 出现，与 token
/// 过期窗口重合。契约：401 触发 refresh 后必须用新 token 重放原请求，
/// 只有重放仍失败才允许错误冒泡到业务层（横幅）。
///
/// 分支覆盖（fake dio adapter，无网络）：
///   A. 401 → refresh 成功 → 重放 200 → 调用方拿到 200（横幅无条件不出现）；
///   B. 401 → refresh 成功 → 重放仍 401 → 错误冒泡（横幅允许），但
///      refresh 恰好一次（无循环），会话有效不登出；
///   C. 重放 5xx 同 B（错误冒泡 + 单次刷新 + 不登出）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late _StorageBackedAuthRepository authRepository;
  late _EnqueueAdapter adapter;
  late _EnqueueAdapter retryAdapter;
  late Dio retryDio;
  late ProviderContainer container;
  late ApiClient client;

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final prefs = await SharedPreferences.getInstance();
    authRepository = _StorageBackedAuthRepository();
    adapter = _EnqueueAdapter();
    retryAdapter = _EnqueueAdapter();
    retryDio = Dio(BaseOptions(baseUrl: 'https://api.example.test'))
      ..httpClientAdapter = retryAdapter;
    container = ProviderContainer(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        authRepositoryProvider.overrideWithValue(authRepository),
        activeGoalHeaderProvider.overrideWithValue(null),
        authInterceptorProvider.overrideWith(
          (ref) => AuthInterceptor(ref, retryDioForTesting: retryDio),
        ),
      ],
    );
    client = container.read(apiClientProvider);
    client.dio.httpClientAdapter = adapter;
  });

  tearDown(() => container.dispose());

  test('A: 401 → refresh → replay succeeds, caller never sees the 401',
      () async {
    authRepository
      ..storedAccessToken = 'stale-access'
      ..storedRefreshToken = 'refresh-token';
    adapter.enqueue(
      statusCode: 401,
      data: const <String, dynamic>{'detail': 'token expired'},
    );
    retryAdapter.enqueue(
      statusCode: 200,
      data: const <String, dynamic>{
        'data': [<String, dynamic>{'id': 'task-1'}],
      },
    );

    final response = await client.get<dynamic>('/api/v1/tasks');

    expect(
      (response.data as Map<String, dynamic>)['data'],
      isA<List<dynamic>>(),
    );
    expect(authRepository.refreshCalls, 1);
    // 原请求带旧 token 出门，重放带新 token。
    expect(
      adapter.records.single.headers['Authorization'],
      'Bearer stale-access',
    );
    expect(
      retryAdapter.records.single.headers['Authorization'],
      'Bearer refreshed-access',
    );
    expect(retryAdapter.records.single.path, contains('/api/v1/tasks'),
        reason: '重放的是原请求（同 path），不是别的调用',);
    expect(authRepository.logoutCalls, 0);
  });

  test('B: replay still 401 → error surfaces (banner allowed), refresh '
      'exactly once, no logout loop', () async {
    authRepository
      ..storedAccessToken = 'stale-access'
      ..storedRefreshToken = 'refresh-token';
    adapter.enqueue(statusCode: 401, data: const <String, dynamic>{});
    retryAdapter.enqueue(statusCode: 401, data: const <String, dynamic>{});

    await expectLater(
      client.get<dynamic>('/api/v1/tasks'),
      throwsA(
        isA<DioException>()
            .having((e) => e.response?.statusCode, 'status', 401),
      ),
    );

    expect(authRepository.refreshCalls, 1,
        reason: '重放失败不得再次触发刷新（无刷新循环）',);
    expect(authRepository.logoutCalls, 0,
        reason: '刷新成功、仅重放失败时（AUTH-DEEP B-3）会话有效，禁止登出',);
  });

  test('C: replay 5xx → error surfaces, session kept, single refresh',
      () async {
    authRepository
      ..storedAccessToken = 'stale-access'
      ..storedRefreshToken = 'refresh-token';
    adapter.enqueue(statusCode: 401, data: const <String, dynamic>{});
    retryAdapter.enqueue(
      statusCode: 503,
      data: const <String, dynamic>{'detail': 'unavailable'},
    );

    await expectLater(
      client.get<dynamic>('/api/v1/tasks'),
      throwsA(isA<DioException>()),
    );

    expect(authRepository.refreshCalls, 1);
    expect(authRepository.logoutCalls, 0);
  });
}

/// Auth repository fake：token 读写全部落内存，计数刷新/登出。
class _StorageBackedAuthRepository implements AuthRepository {
  String? storedAccessToken;
  String? storedRefreshToken;
  int refreshCalls = 0;
  int logoutCalls = 0;

  @override
  Future<String?> getAccessToken() async => storedAccessToken;

  @override
  Future<String?> getToken() async => storedAccessToken;

  @override
  Future<String?> getRefreshToken() async => storedRefreshToken;

  @override
  Future<TokenResponse> refreshToken() async {
    refreshCalls++;
    storedAccessToken = 'refreshed-access';
    return TokenResponse(
      accessToken: 'refreshed-access',
      refreshToken: storedRefreshToken,
    );
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {
    logoutCalls++;
    storedAccessToken = null;
    storedRefreshToken = null;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _AdapterRecord {
  const _AdapterRecord({required this.headers, required this.path});

  final Map<String, dynamic> headers;
  final String path;
}

class _EnqueueAdapter implements HttpClientAdapter {
  final List<_AdapterRecord> records = <_AdapterRecord>[];

  void enqueue({
    required int statusCode,
    required Object? data,
  }) {
    _queue.add(_QueuedStep(statusCode, jsonEncode(data ?? <String, dynamic>{})));
  }

  final List<_QueuedStep> _queue = <_QueuedStep>[];

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    // Copy: the interceptor mutates requestOptions.headers on the refresh
    // retry path, so a live reference would show post-refresh values.
    records.add(
      _AdapterRecord(
        headers: Map<String, dynamic>.of(options.headers),
        path: options.path,
      ),
    );
    final step = _queue.removeAt(0);
    return ResponseBody.fromString(
      step.body,
      step.statusCode,
      headers: {
        Headers.contentTypeHeader: <String>['application/json'],
      },
    );
  }
}

class _QueuedStep {
  const _QueuedStep(this.statusCode, this.body);

  final int statusCode;
  final String body;
}
