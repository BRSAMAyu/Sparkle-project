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

/// COMMUNITY-401 regression — community-domain token injection & refresh face.
///
/// Field evidence: after an app restart, every community-tab request 401'd and
/// tap-to-retry could never recover. Two client-side properties must hold:
///   1. "重启后" = tokens are re-read from storage at REQUEST time, so a fresh
///      client instance (cold start) carries the stored token as soon as the
///      storage read completes — even if that happens after client build;
///   2. a 401 on a header-less request no longer hard-skips recovery: with a
///      session present (refresh token in storage) the interceptor refreshes
///      and retries exactly like the with-header path, while with NO session
///      it still fails fast without a logout loop.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late _StorageBackedAuthRepository authRepository;
  late _RecordingAdapter adapter;
  late _RecordingAdapter retryAdapter;
  late Dio retryDio;
  late ProviderContainer container;
  late ApiClient client;

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final prefs = await SharedPreferences.getInstance();
    authRepository = _StorageBackedAuthRepository();
    adapter = _RecordingAdapter();
    retryAdapter = _RecordingAdapter();
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

  test('restart simulation: token restored to storage after client build is '
      'still injected on the next request', () async {
    // Cold start: the client is built before the storage read completes —
    // no token visible yet.
    adapter.enqueue(statusCode: 200, data: const <String, dynamic>{'ok': true});

    // Storage restore lands (async secure-storage read equivalent).
    authRepository.storedAccessToken = 'restored-access';

    final response = await client.get<Map<String, dynamic>>(
      '/api/v1/community/friends',
    );

    expect(response.data, containsPair('ok', true));
    expect(
      adapter.records.single.headers['Authorization'],
      'Bearer restored-access',
    );
  });

  test('401 on a header-less request with an existing session refreshes and '
      'retries (previously: permanent 401, retry never recovered)', () async {
    // Token state was lost (e.g. partial refresh failure wiped the access
    // token) but the session still exists in storage.
    authRepository.storedRefreshToken = 'refresh-token';
    adapter.enqueue(
      statusCode: 401,
      data: const <String, dynamic>{'detail': 'token required'},
    );
    retryAdapter.enqueue(statusCode: 200, data: const <String, dynamic>{'ok': true});

    final response = await client.get<Map<String, dynamic>>(
      '/api/v1/community/groups',
    );

    expect(response.data, containsPair('ok', true));
    expect(authRepository.refreshCalls, 1);
    expect(adapter.records.single.headers['Authorization'], isNull);
    expect(
      retryAdapter.records.single.headers['Authorization'],
      'Bearer refreshed-access',
    );
    expect(authRepository.logoutCalls, 0);
  });

  test('401 with no session at all fails fast without refresh or logout loop',
      () async {
    adapter.enqueue(
      statusCode: 401,
      data: const <String, dynamic>{'detail': 'unauthorized'},
    );

    await expectLater(
      client.get<Map<String, dynamic>>('/api/v1/community/friends'),
      throwsA(isA<DioException>()),
    );

    expect(authRepository.refreshCalls, 0);
    expect(authRepository.logoutCalls, 0);
    expect(retryAdapter.records, isEmpty);
  });

  test('refresh failure still surfaces as DioException (no silent success)',
      () async {
    authRepository.storedRefreshToken = 'refresh-token';
    authRepository.failRefresh = true;
    adapter.enqueue(statusCode: 401, data: const <String, dynamic>{});
    retryAdapter.enqueue(statusCode: 401, data: const <String, dynamic>{});

    await expectLater(
      client.get<Map<String, dynamic>>('/api/v1/community/friends'),
      throwsA(isA<DioException>()),
    );
    expect(authRepository.refreshCalls, 1);
  });
}

/// Auth repository fake whose token reads model a storage-backed store: the
/// client/interceptor can be built before the "storage" has been read, and
/// every `getToken()` reflects whatever is currently stored.
class _StorageBackedAuthRepository implements AuthRepository {
  String? storedAccessToken;
  String? storedRefreshToken;
  bool failRefresh = false;
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
    if (failRefresh) {
      throw Exception('refresh rejected');
    }
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
  const _AdapterRecord({required this.headers});

  final Map<String, dynamic> headers;
}

class _RecordingAdapter implements HttpClientAdapter {
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
    records.add(_AdapterRecord(headers: Map<String, dynamic>.of(options.headers)));
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
