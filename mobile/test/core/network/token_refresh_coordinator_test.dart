import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/errors/failures.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_interceptor.dart';
import 'package:sparkle/core/network/token_refresh_coordinator.dart';
import 'package:sparkle/features/auth/data/models/token_model.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart'
    show currentUserProvider;
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show sharedPreferencesProvider;
import 'package:sparkle/features/chat/data/services/chat_cache_service.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';

/// AUTH-DEEP B-1 三单飞口收敛回归：
///   1. TokenRefreshCoordinator：并发 N 调用共享同一次
///      AuthRepository.refreshToken（计数断言），失败分级（401/403=会话终局
///      vs 网络/5xx=retryable）；
///   2. HTTP 口（api_interceptor）：并发 401 只触发一次刷新；
///   3. WS Chat 口（websocket_chat_service_v2）：并发 401 合流 + 分级善后；
///   4. Community 口：等待者共享结果（旧布尔旗标的静默丢弃被消灭）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('TokenRefreshCoordinator（单飞 + 分级）', () {
    late _FakeAuthRepository authRepository;
    late ProviderContainer container;
    late TokenRefreshCoordinator coordinator;

    setUp(() {
      authRepository = _FakeAuthRepository();
      container = ProviderContainer(
        overrides: [
          authRepositoryProvider.overrideWithValue(authRepository),
        ],
      );
      coordinator = container.read(tokenRefreshCoordinatorProvider);
    });

    tearDown(() => container.dispose());

    test('并发 N 调用 refreshOnce 只触发一次 refreshToken，且共享同一结果', () async {
      final gate = Completer<void>();
      authRepository.refreshGate = gate;

      final futures = List.generate(
        5,
        (_) => coordinator.refreshOnce(reason: 'test'),
      );
      // 让所有调用者进入 join/启动状态。
      await _settle();

      expect(
        authRepository.refreshCalls,
        1,
        reason: '并发调用必须共享同一次刷新（单飞）',
      );

      gate.complete();
      final tokens = await Future.wait(futures);

      expect(tokens, everyElement('refreshed-1'));
      expect(authRepository.refreshCalls, 1);
    });

    test('刷新失败后新一轮调用开启新刷新（在途位被清理）', () async {
      authRepository.refreshError = const AuthFailure(
        message: 'session expired',
        code: 'TOKEN_EXPIRED',
      );

      await expectLater(
        coordinator.refreshOnce(),
        throwsA(isA<TokenRefreshException>()),
      );

      authRepository.refreshError = null;
      final token = await coordinator.refreshOnce();

      expect(token, 'refreshed-2');
      expect(authRepository.refreshCalls, 2);
    });

    test('分级：401/403（AuthFailure）= 会话终局', () async {
      authRepository.refreshError = const AuthFailure(message: 'rejected');

      final err = await _catchTokenError(coordinator.refreshOnce());

      expect(err, isNotNull);
      expect(err!.isSessionTerminal, isTrue);
      expect(err.isRetryable, isFalse);
    });

    test('分级：5xx / 网络 / 超时 = retryable（不销毁会话）', () async {
      final cases = <Exception>[
        const ServerFailure(message: 'backend down', statusCode: 503),
        const NetworkFailure(message: 'timeout', code: 'CONNECTION_TIMEOUT'),
        const OfflineFailure(message: 'offline'),
        // 真实仓库路径会抛 AppFailureMapper.fromDio 的产物；这里用裸
        // DioException 再验一层映射。
        DioException(
          requestOptions: RequestOptions(path: '/auth/refresh'),
          response: Response<dynamic>(
            requestOptions: RequestOptions(path: '/auth/refresh'),
            statusCode: 503,
          ),
        ),
      ];

      for (final error in cases) {
        authRepository.refreshError = error;
        authRepository.refreshCalls = 0;
        final err = await _catchTokenError(coordinator.refreshOnce());
        expect(err, isNotNull, reason: '$error 应抛 TokenRefreshException');
        expect(err!.isRetryable, isTrue, reason: '$error 应分级为 retryable');
      }
      expect(
        authRepository.logoutCalls,
        0,
        reason: '协调器本身不做登出（善后归调用方）',
      );
    });

    test('getValidAccessToken：有效 JWT 直接返回，不触发刷新', () async {
      authRepository.storedAccessToken = _jwtWithExp(
        DateTime.now().add(const Duration(hours: 1)),
      );
      authRepository.storedRefreshToken = 'refresh-token';

      final token = await coordinator.getValidAccessToken();

      expect(token, authRepository.storedAccessToken);
      expect(authRepository.refreshCalls, 0);
    });

    test('getValidAccessToken：过期 JWT 触发单次刷新并返回新 token', () async {
      authRepository.storedAccessToken = _jwtWithExp(
        DateTime.now().subtract(const Duration(minutes: 5)),
      );
      authRepository.storedRefreshToken = 'refresh-token';

      final token = await coordinator.getValidAccessToken();

      expect(token, 'refreshed-1');
      expect(authRepository.refreshCalls, 1);
    });

    test('getValidAccessToken：无会话返回 null，不抛错不刷新', () async {
      authRepository.storedAccessToken = null;
      authRepository.storedRefreshToken = null;

      final token = await coordinator.getValidAccessToken();

      expect(token, isNull);
      expect(authRepository.refreshCalls, 0);
    });

    test('非 JWT 形态 token（demo）按有效处理，不触发刷新', () async {
      authRepository.storedAccessToken = 'demo_token';
      authRepository.storedRefreshToken = 'demo_refresh_token';

      final token = await coordinator.getValidAccessToken();

      expect(token, 'demo_token');
      expect(authRepository.refreshCalls, 0);
    });
  });

  group('HTTP 口（api_interceptor）：并发 401 全局单飞', () {
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
          authInterceptorProvider.overrideWith(
            (ref) => AuthInterceptor(ref, retryDioForTesting: retryDio),
          ),
        ],
      );
      client = container.read(apiClientProvider);
      client.dio.httpClientAdapter = adapter;
    });

    tearDown(() => container.dispose());

    test('并发 3 个 401 请求只触发一次 refreshToken，各自带新 token 重放', () async {
      authRepository.storedAccessToken = 'stale-access';
      authRepository.storedRefreshToken = 'refresh-token';
      final gate = Completer<void>();
      authRepository.refreshGate = gate;

      for (var i = 0; i < 3; i++) {
        adapter.enqueue(
          statusCode: 401,
          data: const <String, dynamic>{'detail': 'expired'},
        );
      }
      for (var i = 0; i < 3; i++) {
        retryAdapter.enqueue(
          statusCode: 200,
          data: <String, dynamic>{'ok': i},
        );
      }

      final futures = List.generate(
        3,
        (i) => client.get<Map<String, dynamic>>('/api/v1/community/$i'),
      );

      // 等 401 → onError → 全局单飞刷新启动（刷新被 gate 挂起）。
      await _waitUntil(() => authRepository.refreshCalls == 1);
      // 再让其余请求的 401 进入 join 状态（gate 仍挂起）。
      await _settle();
      expect(authRepository.refreshCalls, 1, reason: '全局单飞：只允许一次刷新');

      gate.complete();
      final responses = await Future.wait(futures);

      expect(responses, hasLength(3));
      expect(authRepository.refreshCalls, 1);
      expect(authRepository.logoutCalls, 0);
      expect(
        retryAdapter.records.map((r) => r.headers['Authorization']),
        everyElement('Bearer refreshed-1'),
      );
    });

    test('可重试刷新失败（5xx）：不清 token、不登出（B-3 分级善后）', () async {
      authRepository.storedAccessToken = 'stale-access';
      authRepository.storedRefreshToken = 'refresh-token';
      authRepository.refreshError = DioException(
        requestOptions: RequestOptions(path: '/auth/refresh'),
        response: Response<dynamic>(
          requestOptions: RequestOptions(path: '/auth/refresh'),
          statusCode: 503,
        ),
      );
      adapter.enqueue(statusCode: 401, data: const <String, dynamic>{});

      await expectLater(
        client.get<Map<String, dynamic>>('/api/v1/community/friends'),
        throwsA(isA<DioException>()),
      );

      expect(authRepository.refreshCalls, 1);
      expect(authRepository.logoutCalls, 0);
      expect(authRepository.clearedTokens, isFalse,
          reason: '仓库层 B-3：5xx 不清 token');
    });

    test('会话终局刷新失败（401 被拒）：登出善后', () async {
      authRepository.storedAccessToken = 'stale-access';
      authRepository.storedRefreshToken = 'refresh-token';
      authRepository.refreshError = DioException(
        requestOptions: RequestOptions(path: '/auth/refresh'),
        response: Response<dynamic>(
          requestOptions: RequestOptions(path: '/auth/refresh'),
          statusCode: 401,
        ),
      );
      adapter.enqueue(statusCode: 401, data: const <String, dynamic>{});

      await expectLater(
        client.get<Map<String, dynamic>>('/api/v1/community/friends'),
        throwsA(isA<DioException>()),
      );

      expect(authRepository.refreshCalls, 1);
      expect(authRepository.logoutCalls, 1);
    });
  });

  group('WS Chat 口（websocket_chat_service_v2）：并发 401 合流 + 分级善后', () {
    late _FakeAuthRepository authRepository;
    late ProviderContainer container;
    late WebSocketChatServiceV2 service;

    setUp(() {
      authRepository = _FakeAuthRepository();
      // 预算分支按「refresh token 是否还在」判断会话死活。
      authRepository.storedRefreshToken = 'refresh-token';
      container = ProviderContainer(
        overrides: [
          authRepositoryProvider.overrideWithValue(authRepository),
        ],
      );
      service = WebSocketChatServiceV2(
        container: container,
        channelFactory: (uri, {headers}) =>
            throw UnimplementedError('not needed'),
        enableReconnect: false,
        autoConnect: false,
      );
    });

    tearDown(() {
      service.dispose();
      container.dispose();
    });

    test('并发 401 合流：只触发一次全局刷新，等待者共享结果', () async {
      final gate = Completer<void>();
      authRepository.refreshGate = gate;

      final f1 = service.debugHandle401Error();
      await _settle();
      final f2 = service.debugHandle401Error();
      final f3 = service.debugHandle401Error();
      await _settle();

      expect(authRepository.refreshCalls, 1, reason: '本地轮次合流 + 全局单飞');

      gate.complete();
      await Future.wait([f1, f2, f3]);
      expect(authRepository.refreshCalls, 1);
      expect(authRepository.logoutCalls, 0);
    });

    test('刷新成功后重置 401 预算（握手成功预算复位等价行为）', () async {
      final gate = Completer<void>();
      authRepository.refreshGate = gate;
      final f = service.debugHandle401Error();
      await _waitUntil(() => authRepository.refreshCalls == 1);
      gate.complete();
      await f;

      // 第二轮 401：预算已被成功刷新复位，应允许再刷（而不是预算判死）。
      final gate2 = Completer<void>();
      authRepository.refreshGate = gate2;
      final f2 = service.debugHandle401Error();
      await _waitUntil(() => authRepository.refreshCalls == 2);
      expect(authRepository.refreshCalls, 2, reason: '成功刷新必须复位本地预算');
      gate2.complete();
      await f2;
    });

    test('终局失败（AuthFailure）：登出一次，连接置 failed', () async {
      authRepository.refreshError =
          const AuthFailure(message: 'rejected', code: 'UNAUTHORIZED');

      await service.debugHandle401Error();

      expect(authRepository.refreshCalls, 1);
      expect(authRepository.logoutCalls, 1);
      expect(service.connectionState, WsConnectionState.failed);
    });

    test('可重试失败（5xx）：不登出（B-3）', () async {
      authRepository.refreshError = const ServerFailure(
        message: 'backend down',
        statusCode: 503,
      );

      await service.debugHandle401Error();

      expect(authRepository.refreshCalls, 1);
      expect(
        authRepository.logoutCalls,
        0,
        reason: '可重试失败禁止登出（会话仍有效）',
      );
    });

    test('预算耗尽且会话仍有效：停止循环但不强杀会话', () async {
      // 第一轮：可重试失败（预算 0→1，本轮不禁用，走连接级退避——测试里
      // enableReconnect=false 直接置 failed）。
      authRepository.refreshError =
          const ServerFailure(message: 'down', statusCode: 502);
      await service.debugHandle401Error();

      // 第二轮：预算耗尽；会话活着（refresh token 仍在）→ 不登出。
      await service.debugHandle401Error();

      expect(authRepository.refreshCalls, 1, reason: '预算耗尽后不再发起刷新');
      expect(authRepository.logoutCalls, 0, reason: '会话仍有效时不允许强登出');
      expect(service.connectionState, WsConnectionState.failed);
    });

    test('预算耗尽且凭据已被清（会话已死）：登出兜底', () async {
      authRepository.refreshError =
          const ServerFailure(message: 'down', statusCode: 502);
      await service.debugHandle401Error();

      // 会话已被外部清掉（仓库层清场的终局路径）。
      authRepository.storedRefreshToken = null;
      await service.debugHandle401Error();

      expect(authRepository.logoutCalls, 1, reason: '凭据已死时登出兜底');
    });
  });

  group('Community 口（GroupChatNotifier）：等待者共享结果，不再静默丢弃', () {
    late Directory hiveDir;
    late _FakeAuthRepository authRepository;
    late _FakeCommunityRepository communityRepository;
    late ProviderContainer container;
    late GroupChatNotifier notifier;

    setUpAll(() {
      SharedPreferences.setMockInitialValues(<String, Object>{});
      hiveDir = Directory.systemTemp.createTempSync('wt231_coordinator_hive');
      Hive.init(hiveDir.path);
      _ensureHiveAdapters();
    });

    tearDownAll(() async {
      await _settle();
      try {
        await Hive.close();
      } catch (_) {}
      hiveDir.deleteSync(recursive: true);
    });

    setUp(() {
      // Community WS 在 demo 模式下禁用：让 401 善后测试不触网。
      DemoDataService.isDemoMode = true;

      authRepository = _FakeAuthRepository();
      communityRepository = _FakeCommunityRepository();
      container = ProviderContainer(
        overrides: [
          authRepositoryProvider.overrideWithValue(authRepository),
          currentUserProvider.overrideWithValue(null),
        ],
      );
      final ref = container.read(_refProvider);
      notifier = GroupChatNotifier(
        communityRepository,
        authRepository,
        'g1',
        ref,
      );
    });

    tearDown(() {
      container.dispose();
      DemoDataService.isDemoMode = false;
    });

    test('并发 401 等待者共享同一轮刷新（旧布尔旗标会静默丢弃 2..N）', () async {
      final gate = Completer<void>();
      authRepository.refreshGate = gate;

      final f1 = notifier.debugHandle401Error();
      await _waitUntil(() => authRepository.refreshCalls == 1);

      final f2 = notifier.debugHandle401Error();
      final f3 = notifier.debugHandle401Error();

      // 关键回归断言：等待者必须挂起等待（旧实现立即 return = 静默丢弃）。
      await _expectPending(f2, duration: const Duration(milliseconds: 120));
      await _expectPending(f3, duration: const Duration(milliseconds: 120));
      expect(authRepository.refreshCalls, 1);

      gate.complete();
      await Future.wait([f1, f2, f3]);

      expect(authRepository.refreshCalls, 1, reason: '等待者共享，不重复刷新');
      expect(authRepository.logoutCalls, 0);
    });

    test('终局失败：恰一次登出（等待者不重复善后）', () async {
      final gate = Completer<void>();
      authRepository.refreshGate = gate;
      authRepository.refreshError =
          const AuthFailure(message: 'rejected', code: 'TOKEN_EXPIRED');

      final f1 = notifier.debugHandle401Error();
      await _settle();
      final f2 = notifier.debugHandle401Error();
      await _settle();

      expect(authRepository.refreshCalls, 1);
      gate.complete();
      await Future.wait([f1, f2]);
      await _settle();

      expect(authRepository.refreshCalls, 1);
      expect(authRepository.logoutCalls, 1, reason: '并发善后只允许一次登出');
      expect(notifier.connectionState, WebSocketConnectionState.disconnected);
    });

    test('可重试失败（5xx）：不登出，会话保留', () async {
      authRepository.refreshError =
          const ServerFailure(message: 'down', statusCode: 503);

      await notifier.debugHandle401Error();
      await _settle();

      expect(authRepository.refreshCalls, 1);
      expect(authRepository.logoutCalls, 0, reason: '可重试失败禁止登出');
    });
  });
}

final _refProvider = Provider<Ref>((ref) => ref);

var _hiveAdaptersRegistered = false;

void _ensureHiveAdapters() {
  if (_hiveAdaptersRegistered) {
    return;
  }
  ChatCacheService.registerAdapters();
  _hiveAdaptersRegistered = true;
}

/// 稳定等待：足够多的事件轮次让异步链路（存储读写、provider 初始化）落定。
Future<void> _settle() async {
  for (var i = 0; i < 6; i++) {
    await Future<void>.delayed(Duration.zero);
  }
}

/// 轮询等待条件成立（真实异步链路的确定性同步点）。
Future<void> _waitUntil(
  bool Function() condition, {
  Duration timeout = const Duration(seconds: 2),
}) async {
  final deadline = DateTime.now().add(timeout);
  while (!condition()) {
    if (DateTime.now().isAfter(deadline)) {
      fail('condition not met within $timeout');
    }
    await Future<void>.delayed(const Duration(milliseconds: 5));
  }
}

/// 捕获刷新 Future 抛出的 [TokenRefreshException]；成功返回 null。
Future<TokenRefreshException?> _catchTokenError(Future<String> refresh) async {
  try {
    await refresh;
    return null;
  } on TokenRefreshException catch (e) {
    return e;
  }
}

/// 断言 [future] 在 [duration] 内不完成（回归钉：旧布尔旗标的静默丢弃会让
/// 等待者立刻返回）。
Future<void> _expectPending(
  Future<void> future, {
  required Duration duration,
}) async {
  var completed = false;
  unawaited(
    future.then<void>(
      (_) => completed = true,
      onError: (Object _) => completed = true,
    ),
  );
  await Future<void>.delayed(duration);
  expect(completed, isFalse, reason: '等待者被静默丢弃（旧布尔旗标行为回归）');
}

/// 构造一个携带 exp 的最小 JWT（header.payload.signature，均 base64url）。
String _jwtWithExp(DateTime exp) {
  String enc(Map<String, Object> m) =>
      base64Url.encode(utf8.encode(json.encode(m))).replaceAll('=', '');
  return '${enc(<String, Object>{'alg': 'none'})}.'
      '${enc(<String, Object>{'exp': exp.millisecondsSinceEpoch ~/ 1000})}.'
      'sig';
}

/// 计数型 AuthRepository 替身：可控刷新时机（gate）、失败注入与登出记录。
class _FakeAuthRepository implements AuthRepository {
  String? storedAccessToken;
  String? storedRefreshToken;
  Completer<void>? refreshGate;
  Exception? refreshError;
  int refreshCalls = 0;
  int logoutCalls = 0;
  bool? lastKeepDemoMode;

  bool get clearedTokens =>
      storedAccessToken == null && storedRefreshToken == null;

  @override
  Future<String?> getAccessToken() async => storedAccessToken;

  @override
  Future<String?> getToken() async => storedAccessToken;

  @override
  Future<String?> getRefreshToken() async => storedRefreshToken;

  @override
  Future<TokenResponse> refreshToken() async {
    refreshCalls++;
    if (refreshGate != null) {
      await refreshGate!.future;
    }
    final error = refreshError;
    if (error != null) {
      throw error;
    }
    storedAccessToken = 'refreshed-$refreshCalls';
    return TokenResponse(
      accessToken: storedAccessToken!,
      refreshToken: storedRefreshToken,
    );
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {
    logoutCalls++;
    lastKeepDemoMode = keepDemoMode;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 存储型替身（HTTP 口专用）：可模拟 5xx/401 刷新失败与清场行为。
class _StorageBackedAuthRepository implements AuthRepository {
  String? storedAccessToken;
  String? storedRefreshToken;
  Completer<void>? refreshGate;
  Exception? refreshError;
  bool clearedTokens = false;
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
    if (refreshGate != null) {
      await refreshGate!.future;
    }
    final error = refreshError;
    if (error != null) {
      // 模拟真实仓库：401/403 才清 token（B-3）。
      if (error is DioException) {
        final status = error.response?.statusCode ?? 0;
        if (status == 401 || status == 403) {
          storedAccessToken = null;
          storedRefreshToken = null;
          clearedTokens = true;
        }
      }
      throw error;
    }
    storedAccessToken = 'refreshed-$refreshCalls';
    return TokenResponse(
      accessToken: storedAccessToken!,
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

class _FakeCommunityRepository implements CommunityRepository {
  @override
  Future<List<MessageInfo>> getMessages(
    String groupId, {
    String? beforeId,
    int limit = 50,
  }) async =>
      const <MessageInfo>[];

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
    _queue.add(
      _QueuedStep(statusCode, jsonEncode(data ?? <String, dynamic>{})),
    );
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
    records.add(
      _AdapterRecord(headers: Map<String, dynamic>.of(options.headers)),
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
