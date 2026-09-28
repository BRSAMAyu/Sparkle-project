import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/shared/entities/user_model.dart';

/// V4-FIX-547 · sendMessage 异步续延的 dispose 活性守卫回归钉。
///
/// CI 29 job 108772804580 真红链（wt805 notes §2.3 取证）：sendMessage
/// 续延在 `chat_provider.dart:1388` 读 `subscriptionsProvider` 触发
/// SubscriptionsNotifier 构建与其 `unawaited(loadSubscriptions())` 网络写回，
/// 容器在写回落定前 dispose → `state =` 落在已 dispose 的 notifier 上 →
/// `Bad state: Tried to use SubscriptionsNotifier after dispose` 以未处理
/// 异步错误形态泄漏 →「failed after test completion」。
///
/// 本文件三测：
/// 1. 控制组——容器存活时正常路径不受守卫影响（订阅写回照常发生、发送照常完成）；
/// 2. 钉 A（CI 29 形态）——读簇已触发订阅加载后容器 dispose，写回落定于
///    dispose 之后：不得泄漏 Bad state（写被活性守卫拦截，即不写 state）；
/// 3. 钉 B（token 缺口形态）——sendMessage 挂在 token await 上时容器
///    dispose，续延恢复后不得再触碰 provider 读/state 写，sendMessage
///    future 干净完成（不抛 Bad state）。
///
/// 两钉均为「真接线」形制：ChatNotifier 经 `chatProvider` 由容器持有，
/// `container.dispose()` 同时 dispose ChatNotifier 与 SubscriptionsNotifier
/// （与生产 StateNotifierProvider 生命周期一致；chat_value_signal_test 的
/// 手工 notifier 形制盖不到这一点）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('V4-FIX-547 sendMessage 续延 dispose 活性守卫', () {
    test('控制组：容器存活时订阅正常写回、发送正常完成（守卫不改变正常路径）', () async {
      final controller = StreamController<ChatStreamEvent>();
      addTearDown(() => unawaited(controller.close()));
      final pageCompleter =
          Completer<PaginatedResponse<UserLibrarySubscription>>();
      final stub =
          _ControlledSeedLibraryRepository(pageCompleter: pageCompleter);
      final (container, _) = await _buildHarness(
        chatStream: controller.stream,
        seedRepository: stub,
      );
      addTearDown(container.dispose);

      final notifier = container.read(chatProvider.notifier);
      final sendFuture = notifier.sendMessage('帮我规划期末复习');
      await _drainUntil(() => stub.subscriptionsCalls, 1);

      // 读簇已触发 subscriptionsProvider 构建与 loadSubscriptions
      expect(stub.subscriptionsCalls, 1);

      // 容器存活时写回落定：订阅列表照常写入（正常路径行为不变）
      pageCompleter.complete(_pageWithOneEnabledSubscription());
      await _settle();
      final subscriptions = container.read(subscriptionsProvider).subscriptions;
      expect(subscriptions, hasLength(1));
      expect(subscriptions.single.libraryId, 'lib-1');
      expect(subscriptions.single.isEnabled, isTrue);

      // 发送链照常收束
      controller
        ..add(TextEvent(content: '计划已生成'))
        ..add(DoneEvent(finishReason: 'STOP'));
      await sendFuture;
      expect(notifier.state.isSending, isFalse);
    });

    test('钉 A：读簇触发订阅加载后容器 dispose，迟写回落定不得泄漏 Bad state', () async {
      final errors = <Object>[];
      var flowCompleted = false;
      final pageCompleter =
          Completer<PaginatedResponse<UserLibrarySubscription>>();
      final stub =
          _ControlledSeedLibraryRepository(pageCompleter: pageCompleter);
      // CI 29 形态的异步错误经 unawaited(loadSubscriptions()) 链泄漏；
      // 用独立 zone 捕获以在测试体内确定性断言，而非依赖
      // 「failed after test completion」的事后形态。
      await runZonedGuarded(
        () async {
          final controller = StreamController<ChatStreamEvent>();
          final (container, _) = await _buildHarness(
            chatStream: controller.stream,
            seedRepository: stub,
          );

          final notifier = container.read(chatProvider.notifier);
          // 不 await：钉点在发送链 park 于 await-for 之后
          unawaited(notifier.sendMessage('帮我规划期末复习'));
          await _drainUntil(() => stub.subscriptionsCalls, 1);

          // 读簇已过（subscriptionsProvider 已构建、loadSubscriptions 已挂起），
          // 此刻容器整体拆毁：ChatNotifier 与 SubscriptionsNotifier 一并 dispose
          container.dispose();
          await controller.close();

          // 迟到的订阅写回：dispose 之后才落定
          pageCompleter.complete(_pageWithOneEnabledSubscription());
          await _settle();
          await Future<void>.delayed(const Duration(milliseconds: 1));
          await _settle();

          flowCompleted = true;
        },
        (error, stackTrace) => errors.add(error),
      );

      expect(flowCompleted, isTrue);
      // dispose 后写回必须被活性守卫拦截：已 dispose 的 StateNotifier 任何
      // state 写都必然抛 Bad state，故「无泄漏错误」与「未写 state」互为充要
      expect(errors, everyElement(isNot(isA<StateError>())));
      expect(errors, isEmpty);
    });

    test('钉 B：token await 挂起期间容器 dispose，续延恢复后不得触碰 provider/state', () async {
      final tokenCompleter = Completer<String?>();
      final controller = StreamController<ChatStreamEvent>();
      addTearDown(() => unawaited(controller.close()));
      final stub = _ControlledSeedLibraryRepository(
        pageCompleter: Completer<PaginatedResponse<UserLibrarySubscription>>(),
      );
      final (container, _) = await _buildHarness(
        chatStream: controller.stream,
        seedRepository: stub,
        tokenCompleter: tokenCompleter,
      );

      final notifier = container.read(chatProvider.notifier);
      final sendFuture = notifier.sendMessage('帮我规划期末复习');
      await _settle();
      // 续延应 park 在 token await 上：读簇（含 subscriptionsProvider 触发）未达
      expect(stub.subscriptionsCalls, 0);

      // token 在途期间容器拆毁
      container.dispose();
      tokenCompleter.complete('test-token');

      // 修复后续延在 token await 恢复点即退出：不读 provider、不写 state、
      // sendMessage future 干净完成。修复前此处抛
      // Bad state（state 写 / finalizeRun 二次抛）。
      await sendFuture;
      await _settle();
    });
  });
}

PaginatedResponse<UserLibrarySubscription> _pageWithOneEnabledSubscription() =>
    PaginatedResponse<UserLibrarySubscription>(
      items: <UserLibrarySubscription>[
        UserLibrarySubscription(
          id: 'sub-1',
          userId: 'user-1',
          libraryId: 'lib-1',
          isEnabled: true,
          priority: 5,
          subscribedAt: DateTime(2026, 9, 28),
          createdAt: DateTime(2026, 9, 28),
          updatedAt: DateTime(2026, 9, 28),
        ),
      ],
      total: 1,
      page: 1,
      pageSize: 20,
      totalPages: 1,
    );

/// 微任务链确定性 drain（形制同 chat_value_signal_test._settle：全部残留
/// 工作均为微任务级，8 轮 Duration.zero 覆盖事件循环跳数）。
Future<void> _settle() async {
  for (var i = 0; i < 8; i++) {
    await Future<void>.delayed(Duration.zero);
  }
}

/// 条件化 drain：等待 [actual] 达到 [expected]（有界轮数内确定性达成）。
Future<void> _drainUntil(int Function() actual, int expected) async {
  for (var i = 0; i < 200 && actual() < expected; i++) {
    await Future<void>.delayed(Duration.zero);
  }
}

/// 真接线 harness：覆写与 chat_value_signal_test V3-FIX-547 版一致，唯两处
/// 有意差异——**不覆写** subscriptionsProvider（CI 29 红链的产品侧主角必须
/// 以真 provider 生命周期参与），改覆写其仓库依赖 seedLibraryRepositoryProvider
/// 为受控替身（Completer 掌控写回落定时机）；authRepositoryProvider 换受控
/// token 缺口替身（钉 B 需要把续延精确 park 在 token await 上）。
Future<(ProviderContainer, _ControlledAuthRepository)> _buildHarness({
  required Stream<ChatStreamEvent> chatStream,
  required _ControlledSeedLibraryRepository seedRepository,
  Completer<String?>? tokenCompleter,
}) async {
  SharedPreferences.setMockInitialValues(<String, Object>{});
  // sendMessage 路径会经 chatModeProvider/guidanceModeProvider 等
  // PersistentNotifier 读 ViewStorageService（唯一后端 SharedPreferences，
  // 上方已 mock）；按 main.dart 启动形制初始化。
  await ViewStorageService.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final authRepository =
      _ControlledAuthRepository(tokenCompleter: tokenCompleter);
  final container = ProviderContainer(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      authProvider.overrideWith(
        (ref) => _StaticAuthNotifier(registrationSource: 'guest'),
      ),
      authRepositoryProvider.overrideWithValue(authRepository),
      chatRepositoryProvider.overrideWithValue(
        _StubChatRepository(chatStream),
      ),
      seedLibraryRepositoryProvider.overrideWithValue(seedRepository),
    ],
  );
  return (container, authRepository);
}

class _StaticAuthNotifier extends AuthNotifier {
  _StaticAuthNotifier({required String registrationSource})
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    final now = DateTime(2026, 9, 28);
    state = AuthState(
      isAuthenticated: true,
      user: UserModel(
        id: '00000000-0000-0000-0000-000000000047',
        username: 'dispose_guard_user',
        email: 'dispose-guard@example.com',
        flameLevel: 1,
        flameBrightness: 0.5,
        depthPreference: 0.5,
        curiosityPreference: 0.5,
        isActive: true,
        registrationSource: registrationSource,
        createdAt: now,
        updatedAt: now,
      ),
    );
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _ControlledAuthRepository extends AuthRepository {
  _ControlledAuthRepository({Completer<String?>? tokenCompleter})
      : _tokenCompleter = tokenCompleter,
        super(_NoopApiClient(), _MapTokenStorage());

  final Completer<String?>? _tokenCompleter;

  @override
  Future<String?> getAccessToken() =>
      _tokenCompleter?.future ?? Future<String?>.value('test-token');
}

class _ControlledSeedLibraryRepository extends SeedLibraryRepository {
  _ControlledSeedLibraryRepository({required this.pageCompleter})
      : super(_NoopApiClient());

  final Completer<PaginatedResponse<UserLibrarySubscription>> pageCompleter;
  int subscriptionsCalls = 0;

  @override
  Future<PaginatedResponse<UserLibrarySubscription>> getMySubscriptions({
    bool? isEnabled,
    int page = 1,
    int pageSize = 20,
  }) async {
    subscriptionsCalls += 1;
    return pageCompleter.future;
  }

  @override
  Future<SeedLibrary> getLibrary(String id) async {
    // 逐条 library 详情获取在 loadSubscriptions 内被 per-item try/catch 吸收，
    // 订阅条目原样保留——足够钉住写回时序，无需真实 SeedLibrary 载荷。
    throw UnimplementedError();
  }
}

class _StubChatRepository extends ChatRepository {
  _StubChatRepository(this._stream)
      : super(Dio(), container: ProviderContainer());

  final Stream<ChatStreamEvent> _stream;
  final StreamController<WsConnectionState> _connectionController =
      StreamController<WsConnectionState>.broadcast();

  @override
  Stream<WsConnectionState> get connectionStateStream =>
      _connectionController.stream;

  @override
  Stream<ChatStreamEvent> chatStream(
    String message,
    String? conversationId, {
    String? userId,
    String? requestId,
    String? nickname,
    Map<String, dynamic>? extraContext,
    String? token,
    List<String>? fileIds,
    bool includeReferences = false,
    String? chatMode,
    bool? useDocumentContext,
  }) =>
      _stream;

  @override
  void dispose() {
    unawaited(_connectionController.close());
  }
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) => InterceptorsWrapper() as T;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository() : super(_NoopApiClient(), _MapTokenStorage());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MapTokenStorage implements TokenStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<String?> read(String key) async => _values[key];

  @override
  Future<void> write(String key, String value) async {
    _values[key] = value;
  }

  @override
  Future<void> delete(String key) async {
    _values.remove(key);
  }
}
