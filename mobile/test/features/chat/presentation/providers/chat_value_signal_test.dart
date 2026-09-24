import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/guest_conversion_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_conversion_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/shared/entities/user_model.dart';

/// N47（A-SPEC8B §4）· 价值信号接线回归：firstDiagnosisOutput 与
/// firstMemoryReferenced 的触发路径测试——从聊天流的真实事件落点
/// （PlanReviewWidgetEvent / memory_reference_receipt metadata）驱动
/// `ChatNotifier.sendMessage` 全链，断言信号到达 GuestConversionService
/// 持久层。形制照 chat_notifier_stream_test.dart 的 fake repository
/// harness（同一 sendMessage 路径，非 mock service 调用）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('N47 聊天价值信号接线（触发点 → service 记录）', () {
    test(
      '访客收到规划类 AI 输出（PlanReviewWidgetEvent）→ 记录 firstDiagnosisOutput',
      () async {
        final controller = StreamController<ChatStreamEvent>();
        addTearDown(() => unawaited(controller.close()));
        final (container, repository) = await _buildHarness(
          isGuest: true,
          controller: controller,
        );
        addTearDown(container.dispose);

        final notifier = _createNotifier(repository, container);
        final sendFuture = notifier.sendMessage('帮我规划期末复习');
        await _settle();

        controller
          ..add(TextEvent(content: '已为你的期末复习生成计划'))
          ..add(
            PlanReviewWidgetEvent(
              reviewData: <String, dynamic>{
                'review_id': 'review-1',
                'plan_id': 'plan-1',
                'decision': 'requires_confirmation',
              },
            ),
          )
          ..add(DoneEvent(finishReason: 'STOP'));
        await sendFuture;
        await _settle();

        // 信号从触发点到达 service 持久层
        final service = _serviceOf(container);
        expect(service.signalCount, 1);
        expect(service.lastSignalKey, 'first_diagnosis_output');

        // 派生可见性：无进行中任务 → 安全窗口成立（chat/home 挂载点可渲染）
        expect(container.read(guestConversionVisibleProvider), isTrue);
        // 规划卡本身照常就位（触发点行为未被信号接线改变）
        expect(notifier.state.pendingPlanReview, isNotNull);
      },
    );

    test(
      '访客 AI 回复引用记忆（memory_reference_receipt metadata）→ 记录 '
      'firstMemoryReferenced',
      () async {
        final controller = StreamController<ChatStreamEvent>();
        addTearDown(() => unawaited(controller.close()));
        final (container, repository) = await _buildHarness(
          isGuest: true,
          controller: controller,
        );
        addTearDown(container.dispose);

        final notifier = _createNotifier(repository, container);
        final sendFuture = notifier.sendMessage('我上次错在哪里？');
        await _settle();

        controller
          ..add(TextEvent(content: '你上次在数列极限处反复出错，这次换个思路'))
          ..add(
            const MetaEvent(
              meta: <String, dynamic>{
                'memory_reference_receipt': <String, dynamic>{
                  'receipt_type': 'memory_reference_receipt',
                  'used_count': 1,
                  'referenced_memories': <Map<String, dynamic>>[
                    <String, dynamic>{
                      'id': 'mem-1',
                      'type': 'episodic',
                      'content': '数列极限题曾反复出错',
                    },
                  ],
                },
              },
            ),
          )
          ..add(DoneEvent(finishReason: 'STOP'));
        await sendFuture;
        await _settle();

        final service = _serviceOf(container);
        expect(service.signalCount, 1);
        expect(service.lastSignalKey, 'first_memory_referenced');

        // 消息照常落态、receipt 照常可渲染（同一 rawMetadata 数据源）
        final messages = notifier.state.messages;
        expect(messages.last.role, MessageRole.assistant);
        expect(messages.last.rawMetadata?['memory_reference_receipt'], isNotNull);
        expect(container.read(guestConversionVisibleProvider), isTrue);
      },
    );

    test('无价值动作的普通回复不记录信号（负路径）', () async {
      final controller = StreamController<ChatStreamEvent>();
      addTearDown(() => unawaited(controller.close()));
      final (container, repository) = await _buildHarness(
        isGuest: true,
        controller: controller,
      );
      addTearDown(container.dispose);

      final notifier = _createNotifier(repository, container);
      final sendFuture = notifier.sendMessage('今天天气适合学习吗');
      await _settle();

      controller
        ..add(TextEvent(content: '适合，保持节奏'))
        ..add(DoneEvent(finishReason: 'STOP'));
      await sendFuture;
      await _settle();

      final service = _serviceOf(container);
      expect(service.signalCount, 0);
      expect(service.lastSignalKey, isNull);
      expect(container.read(guestConversionVisibleProvider), isFalse);
    });

    test('receipt 空引用（referenced_memories 为空）不记录信号（负路径）', () async {
      final controller = StreamController<ChatStreamEvent>();
      addTearDown(() => unawaited(controller.close()));
      final (container, repository) = await _buildHarness(
        isGuest: true,
        controller: controller,
      );
      addTearDown(container.dispose);

      final notifier = _createNotifier(repository, container);
      final sendFuture = notifier.sendMessage('继续');
      await _settle();

      controller
        ..add(TextEvent(content: '好的'))
        ..add(
          const MetaEvent(
            meta: <String, dynamic>{
              'memory_reference_receipt': <String, dynamic>{
                'receipt_type': 'memory_reference_receipt',
                'used_count': 0,
                'referenced_memories': <Map<String, dynamic>>[],
              },
            },
          ),
        )
        ..add(DoneEvent(finishReason: 'STOP'));
      await sendFuture;
      await _settle();

      expect(_serviceOf(container).signalCount, 0);
    });

    test('注册用户两信号全程 no-op（免费闭环零变化）', () async {
      final controller = StreamController<ChatStreamEvent>();
      addTearDown(() => unawaited(controller.close()));
      final (container, repository) = await _buildHarness(
        isGuest: false,
        controller: controller,
      );
      addTearDown(container.dispose);

      final notifier = _createNotifier(repository, container);
      final firstSend = notifier.sendMessage('帮我规划期末复习');
      await _settle();
      controller
        ..add(TextEvent(content: '计划已生成'))
        ..add(
          PlanReviewWidgetEvent(
            reviewData: <String, dynamic>{'review_id': 'r', 'plan_id': 'p'},
          ),
        )
        ..add(
          const MetaEvent(
            meta: <String, dynamic>{
              'memory_reference_receipt': <String, dynamic>{
                'referenced_memories': <Map<String, dynamic>>[
                  <String, dynamic>{'content': 'x'},
                ],
              },
            },
          ),
        )
        ..add(DoneEvent(finishReason: 'STOP'));
      await firstSend;
      await _settle();

      final service = _serviceOf(container);
      expect(service.signalCount, 0);
      expect(service.lastSignalKey, isNull);
      expect(container.read(guestConversionVisibleProvider), isFalse);
    });
  });
}

GuestConversionService _serviceOf(ProviderContainer container) =>
    GuestConversionService(container.read(sharedPreferencesProvider));

Future<(ProviderContainer, _FakeChatRepository)> _buildHarness({
  required bool isGuest,
  required StreamController<ChatStreamEvent> controller,
}) async {
  SharedPreferences.setMockInitialValues(<String, Object>{});
  // sendMessage 路径会经 chatModeProvider/guidanceModeProvider 等
  // PersistentNotifier 读 ViewStorageService；其唯一后端是
  // SharedPreferences（上方已 mock），此处按 main.dart 启动形制初始化。
  await ViewStorageService.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final repository = _FakeChatRepository(
    (
      message,
      conversationId, {
      userId,
      requestId,
      nickname,
      extraContext,
      token,
      fileIds,
      includeReferences = false,
      chatMode,
    }) =>
        controller.stream,
  );
  final container = ProviderContainer(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      authProvider.overrideWith(
        (ref) => isGuest
            ? _StaticAuthNotifier(registrationSource: 'guest')
            : _StaticAuthNotifier(registrationSource: 'email'),
      ),
      // sendMessage 取 token 走 authRepositoryProvider；真实现会触达
      // flutter_secure_storage（测试环境无 platform channel）。
      authRepositoryProvider.overrideWithValue(
        _FakeAuthRepository(token: 'test-token'),
      ),
    ],
  );
  return (container, repository);
}

ChatNotifier _createNotifier(
  _FakeChatRepository repository,
  ProviderContainer container,
) =>
    ChatNotifier(repository, _ContainerForwardingRef(container));

Future<void> _settle() =>
    Future<void>.delayed(const Duration(milliseconds: 80));

typedef _ChatStreamFactory = Stream<ChatStreamEvent> Function(
  String message,
  String? conversationId, {
  String? userId,
  String? requestId,
  String? nickname,
  Map<String, dynamic>? extraContext,
  String? token,
  List<String>? fileIds,
  bool includeReferences,
  String? chatMode,
});

class _FakeChatRepository extends ChatRepository {
  _FakeChatRepository(this._streamFactory)
      : super(Dio(), container: ProviderContainer());

  final _ChatStreamFactory _streamFactory;
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
      _streamFactory(
        message,
        conversationId,
        userId: userId,
        requestId: requestId,
        nickname: nickname,
        extraContext: extraContext,
        token: token,
        fileIds: fileIds,
        includeReferences: includeReferences,
        chatMode: chatMode,
      );

  @override
  void dispose() {
    unawaited(_connectionController.close());
  }
}

/// 真实 ProviderContainer 转发 Ref：ChatNotifier 既有依赖照常解析，
/// 新增的 guestConversionControllerProvider 读取落在带 override 的
/// 容器上（静态访客/注册用户 + mock prefs）。
class _ContainerForwardingRef implements Ref {
  _ContainerForwardingRef(this._container);

  final ProviderContainer _container;

  @override
  T read<T>(ProviderListenable<T> provider) => _container.read(provider);

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

UserModel _buildUser(String registrationSource) {
  final now = DateTime(2026, 9, 22);
  return UserModel(
    id: '00000000-0000-0000-0000-000000000009',
    username: 'chat_value_signal_user',
    email: 'cvs@example.com',
    flameLevel: 1,
    flameBrightness: 0.5,
    depthPreference: 0.5,
    curiosityPreference: 0.5,
    isActive: true,
    registrationSource: registrationSource,
    createdAt: now,
    updatedAt: now,
  );
}

class _StaticAuthNotifier extends AuthNotifier {
  _StaticAuthNotifier({required String registrationSource})
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(
      isAuthenticated: true,
      user: _buildUser(registrationSource),
    );
  }

  @override
  Future<void> checkAuthStatus() async {}
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

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository({this.token})
      : super(_NoopApiClient(), _MapTokenStorage());

  final String? token;

  @override
  Future<String?> getAccessToken() async => token;
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
