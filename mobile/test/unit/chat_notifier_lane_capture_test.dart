import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/providers/experience_envelope_provider.dart';
import 'package:sparkle/core/services/guest_service.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/guidance_mode_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

/// V4-U07 快慢反馈：ChatNotifier 对 I09 快慢路帧 metadata 的真实捕获链
/// （StatusUpdateEvent/TextEvent metadata → state → 终帧消息 rawMetadata）。
/// 每面一正一反：
/// - 正：快路轮（状态帧+模板 delta 均带 deterministic 标记）→ 等待期不进
///   三段胶囊 + 终帧消息 rawMetadata 收口 lane/形态词；
/// - 反：集合外 lane 值不捕获（零影响）；无键慢路轮不产 lane 标记，
///   终帧消息不误标即时回复。
class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported read for $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository({this.token})
      : super(
          _NoopApiClient(),
          SecureTokenStorage(storage: const FlutterSecureStorage()),
        );

  final String? token;

  @override
  Future<String?> getAccessToken() async => token;
}

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

class _FakeRef implements Ref {
  _FakeRef({
    required this.authState,
    required this.guestService,
    required this.authRepository,
    ChatMode? chatMode,
  }) : chatMode = chatMode ?? standard;

  final AuthState authState;
  final GuestService guestService;
  final AuthRepository authRepository;
  final String activePlanId = 'plan-1';
  final String reasoningMode = 'balanced';
  final bool seedLibraryEnabled = false;
  final ChatMode chatMode;

  // TextEvent 携带 metadata 时 chat_provider 会读 experience envelope
  // （零依赖 StateNotifier）；按返回类型分发，避免真实容器及其副作用。
  final ExperienceEnvelopeNotifier _experienceEnvelopeNotifier =
      ExperienceEnvelopeNotifier();

  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == ExperienceEnvelopeNotifier) {
      return _experienceEnvelopeNotifier as T;
    }
    if (identical(provider, authProvider)) {
      return authState as T;
    }
    if (identical(provider, guestServiceProvider)) {
      return guestService as T;
    }
    if (identical(provider, authRepositoryProvider)) {
      return authRepository as T;
    }
    if (identical(provider, activePlanProvider)) {
      return activePlanId as T;
    }
    if (identical(provider, aiReasoningModeProvider)) {
      return reasoningMode as T;
    }
    if (identical(provider, chatSeedLibraryEnabledProvider)) {
      return seedLibraryEnabled as T;
    }
    if (identical(provider, chatModeProvider)) {
      return chatMode as T;
    }
    if (identical(provider, systemUpdateLevelProvider)) {
      return 0 as T;
    }
    if (identical(provider, guidanceModeProvider)) {
      return GuidanceMode.aiGuide as T;
    }
    if (identical(provider, subscriptionsProvider)) {
      return const SubscriptionsState() as T;
    }
    throw UnimplementedError('Unsupported provider read: $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Future<ChatNotifier> _createNotifier(_FakeChatRepository repository) async {
  SharedPreferences.setMockInitialValues(<String, Object>{});
  final prefs = await SharedPreferences.getInstance();
  final guestService = GuestService(prefs);
  final ref = _FakeRef(
    authState: AuthState(),
    guestService: guestService,
    authRepository: _FakeAuthRepository(token: 'test-token'),
  );
  return ChatNotifier(repository, ref);
}

Future<void> _settleChat() async {
  await Future<void>.delayed(const Duration(milliseconds: 80));
}

const _fastLaneMetadata = <String, dynamic>{
  'chat_lane': 'deterministic',
  'deterministic_lane_kind': 'greeting',
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ChatNotifier 快慢路捕获（V4-U07 × I09 帧契约）', () {
    test('正：快路轮状态帧捕获 lane；等待期不进三段胶囊；终帧消息收口即时回复判据', () async {
      final controller = StreamController<ChatStreamEvent>();
      final repository = _FakeChatRepository(
        (message, conversationId,
                {userId,
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
      final notifier = await _createNotifier(repository);
      addTearDown(() {
        notifier.dispose();
        unawaited(controller.close());
      });

      final sendFuture = notifier.sendMessage('你好');
      await _settleChat();

      // 状态帧先行（I09 WT373 拆帧契约）：携带 lane 标记。
      controller.add(
        StatusUpdateEvent(
          state: 'GENERATING',
          details: '已收到你的消息。',
          metadata: _fastLaneMetadata,
        ),
      );
      await _settleChat();

      expect(notifier.state.chatLane, 'deterministic');
      expect(notifier.state.deterministicLaneKind, 'greeting');
      // 快路等待面：有活跃 run 且尚无内容，但不进检索/思考三段胶囊。
      expect(notifier.state.hasActiveRun, isTrue);
      expect(notifier.state.streamingContent, isEmpty);
      expect(notifier.state.shouldShowPhaseCapsule, isFalse);

      // 模板应答 delta（快路直出，无真模型生成）。
      controller
        ..add(
          TextEvent(
            content: '你好！我是 Sparkle，很高兴见到你。',
            metadata: _fastLaneMetadata,
          ),
        )
        ..add(DoneEvent(finishReason: 'STOP'));
      await sendFuture;
      await _settleChat();

      final reply = notifier.state.messages.last;
      expect(reply.role, MessageRole.assistant);
      expect(reply.isDeterministicLaneReply, isTrue);
      expect(reply.chatLane, 'deterministic');
      expect(reply.deterministicLaneKind, 'greeting');
      // run 终态：state 上的轮级标记清零（消息级判据已收口）。
      expect(notifier.state.chatLane, isNull);
      expect(notifier.state.shouldShowPhaseCapsule, isFalse);
    });

    test('反：集合外 lane 值不捕获，等待面保持既有三段胶囊语义', () async {
      final controller = StreamController<ChatStreamEvent>();
      final repository = _FakeChatRepository(
        (message, conversationId,
                {userId,
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
      final notifier = await _createNotifier(repository);
      addTearDown(() {
        notifier.dispose();
        unawaited(controller.close());
      });

      final sendFuture = notifier.sendMessage('讲讲傅里叶变换');
      await _settleChat();

      controller.add(
        StatusUpdateEvent(
          state: 'THINKING',
          details: 'planning',
          metadata: const {
            'chat_lane': 'warp_speed',
            'deterministic_lane_kind': 'greeting',
          },
        ),
      );
      await _settleChat();

      expect(notifier.state.chatLane, isNull);
      expect(notifier.state.deterministicLaneKind, isNull);
      // 未携带合法 lane → 既有慢路等待面（三段胶囊）不变。
      expect(notifier.state.shouldShowPhaseCapsule, isTrue);

      controller
        ..add(
          TextEvent(
            content: '傅里叶变换把信号分解成不同频率的正弦波。',
            metadata: const {'chat_lane': 'model'},
          ),
        )
        ..add(DoneEvent(finishReason: 'STOP'));
      await sendFuture;
      await _settleChat();

      final reply = notifier.state.messages.last;
      expect(reply.isDeterministicLaneReply, isFalse, reason: '真模型慢路回复不误标即时回复');
    });

    test('反：无键慢路轮全程无 lane 标记（旧后端零变化）', () async {
      final controller = StreamController<ChatStreamEvent>();
      final repository = _FakeChatRepository(
        (message, conversationId,
                {userId,
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
      final notifier = await _createNotifier(repository);
      addTearDown(() {
        notifier.dispose();
        unawaited(controller.close());
      });

      final sendFuture = notifier.sendMessage('帮我规划今天的学习');
      await _settleChat();

      controller.add(
        StatusUpdateEvent(state: 'THINKING', details: 'planning'),
      );
      await _settleChat();

      expect(notifier.state.chatLane, isNull);
      expect(notifier.state.shouldShowPhaseCapsule, isTrue);

      controller
        ..add(TextEvent(content: '好的，先从数学开始。'))
        ..add(DoneEvent(finishReason: 'STOP'));
      await sendFuture;
      await _settleChat();

      final reply = notifier.state.messages.last;
      expect(reply.rawMetadata?['chat_lane'], isNull);
      expect(reply.isDeterministicLaneReply, isFalse);
    });
  });
}
