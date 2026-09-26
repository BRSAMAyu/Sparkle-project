import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
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
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/providers/guidance_mode_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

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
      : super(_NoopApiClient(), SecureTokenStorage(storage: const FlutterSecureStorage()));

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
  }) => _streamFactory(
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

  @override
  T read<T>(ProviderListenable<T> provider) {
    if (provider == authProvider) {
      return authState as T;
    }
    if (provider == guestServiceProvider) {
      return guestService as T;
    }
    if (provider == authRepositoryProvider) {
      return authRepository as T;
    }
    if (provider == activePlanProvider) {
      return activePlanId as T;
    }
    if (provider == aiReasoningModeProvider) {
      return reasoningMode as T;
    }
    if (provider == chatSeedLibraryEnabledProvider) {
      return seedLibraryEnabled as T;
    }
    if (provider == chatModeProvider) {
      return chatMode as T;
    }
    if (provider == systemUpdateLevelProvider) {
      return 0 as T;
    }
    if (provider == guidanceModeProvider) {
      return GuidanceMode.aiGuide as T;
    }
    if (provider == subscriptionsProvider) {
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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ChatNotifier.sendMessage', () {
    test('accumulates streaming content and saves final assistant message',
        () async {
      final controller = StreamController<ChatStreamEvent>();
      final repository = _FakeChatRepository(
        (message, conversationId, {userId, requestId, nickname, extraContext, token, fileIds, includeReferences = false, chatMode}) =>
            controller.stream,
      );
      final notifier = await _createNotifier(repository);
      addTearDown(() {
        notifier.dispose();
        unawaited(controller.close());
      });

      final sendFuture = notifier.sendMessage('hello');
      await _settleChat();

      controller
        ..add(TextEvent(content: 'hello'))
        ..add(TextEvent(content: ' world'))
        ..add(DoneEvent(finishReason: 'STOP'));
      await sendFuture;
      await _settleChat();

      expect(notifier.state.streamingContent, isEmpty);
      expect(notifier.state.messages, hasLength(2));
      expect(notifier.state.messages.last.content, 'hello world');
      expect(notifier.state.messages.last.role, MessageRole.assistant);
    });

    test('updates ai status while stream is active', () async {
      final controller = StreamController<ChatStreamEvent>();
      final repository = _FakeChatRepository(
        (message, conversationId, {userId, requestId, nickname, extraContext, token, fileIds, includeReferences = false, chatMode}) =>
            controller.stream,
      );
      final notifier = await _createNotifier(repository);
      addTearDown(() {
        notifier.dispose();
        unawaited(controller.close());
      });

      final sendFuture = notifier.sendMessage('status check');
      await _settleChat();

      controller.add(
        StatusUpdateEvent(
          state: 'THINKING',
          details: 'planning',
        ),
      );
      await _settleChat();

      expect(notifier.state.aiStatus, 'THINKING');
      expect(notifier.state.runPhase, ChatRunPhase.streaming);

      controller.add(DoneEvent(finishReason: 'STOP'));
      await sendFuture;
    });

    test('captures retryable error state from the stream', () async {
      final controller = StreamController<ChatStreamEvent>();
      final repository = _FakeChatRepository(
        (message, conversationId, {userId, requestId, nickname, extraContext, token, fileIds, includeReferences = false, chatMode}) =>
            controller.stream,
      );
      final notifier = await _createNotifier(repository);
      addTearDown(() {
        notifier.dispose();
        unawaited(controller.close());
      });

      final sendFuture = notifier.sendMessage('please fail');
      await _settleChat();

      controller.add(
        ErrorEvent(
          code: 'STREAM_TIMEOUT',
          message: 'upstream timeout',
          retryable: true,
        ),
      );
      await controller.close();
      await sendFuture;

      expect(notifier.state.error, isNotEmpty);
      expect(notifier.state.errorCode, 'STREAM_TIMEOUT');
      expect(notifier.state.isErrorRetryable, isTrue);
      expect(notifier.state.runPhase, ChatRunPhase.failed);
    });

    test('B-01 in-flight guard: ignores a new send while the previous run is in flight', () async {
      final firstController = StreamController<ChatStreamEvent>();
      final secondController = StreamController<ChatStreamEvent>();
      final controllers = <StreamController<ChatStreamEvent>>[
        firstController,
        secondController,
      ];
      var index = 0;
      final repository = _FakeChatRepository(
        (message, conversationId, {userId, requestId, nickname, extraContext, token, fileIds, includeReferences = false, chatMode}) =>
            controllers[index++].stream,
      );
      final notifier = await _createNotifier(repository);
      addTearDown(() {
        notifier.dispose();
        unawaited(firstController.close());
        unawaited(secondController.close());
      });

      final firstFuture = notifier.sendMessage('first');
      await _settleChat();
      expect(notifier.state.isSending, isTrue);

      // B-01 次生面（V13 重复消息+重复计费）：在途期间新发送被静默丢弃，
      // 不再 cancel+supersede 旧流。
      await notifier.sendMessage('second');
      await _settleChat();
      expect(notifier.state.isSending, isTrue);
      expect(
        notifier.state.messages
            .where((message) => message.role == MessageRole.user)
            .map((message) => message.content),
        ['first'],
      );

      // wt466 V3-FIX-155 语义更新：流必须带终态帧正常收束——无终态关闭
      // 现为截断（failed+STREAM_INTERRUPTED，裸文本不落地，见
      // chat_provider_test 的 STREAM_INTERRUPTED 专项测）。本测守卫面，
      // 用 DoneEvent 正常收尾。
      firstController.add(TextEvent(content: 'stale'));
      firstController.add(DoneEvent(finishReason: 'STOP'));
      await firstController.close();
      await firstFuture;
      await _settleChat();

      final assistantMessages = notifier.state.messages
          .where((message) => message.role == MessageRole.assistant)
          .toList();
      expect(assistantMessages, hasLength(1));
      expect(assistantMessages.single.content, 'stale');
      expect(assistantMessages.single.content, isNot(contains('fresh')));
    });
  });

  group('M6-09 interrupt-preserve semantics', () {
    test(
        'B-01 in-flight guard: a new send mid-stream is dropped and the partial reply keeps streaming',
        () async {
      final firstController = StreamController<ChatStreamEvent>();
      final secondController = StreamController<ChatStreamEvent>();
      final controllers = <StreamController<ChatStreamEvent>>[
        firstController,
        secondController,
      ];
      var index = 0;
      final repository = _FakeChatRepository(
        (message, conversationId, {userId, requestId, nickname, extraContext, token, fileIds, includeReferences = false, chatMode}) =>
            controllers[index++].stream,
      );
      final notifier = await _createNotifier(repository);
      addTearDown(() {
        notifier.dispose();
        unawaited(firstController.close());
        unawaited(secondController.close());
      });

      final firstFuture = notifier.sendMessage('first');
      await _settleChat();
      firstController.add(TextEvent(content: 'partial answer'));
      await _settleChat();
      expect(notifier.state.streamingContent, 'partial answer');

      // B-01 在途禁发：流式中新消息被丢弃，正在输出的一轮不受影响。
      // M6-09 的「中断保留」语义仍可经显式 cancelActiveRun（user stop）触发，
      // 见下方 'user stop keeps the partial reply' 用例。
      await notifier.sendMessage('second');
      await _settleChat();

      expect(notifier.state.isSending, isTrue);
      expect(notifier.state.streamingContent, 'partial answer');
      expect(
        notifier.state.messages
            .where((message) => message.role == MessageRole.user)
            .map((message) => message.content),
        ['first'],
      );
      expect(
        notifier.state.messages.where((message) => message.isInterrupted),
        isEmpty,
      );

      // 旧流继续正常收束（wt466 V3-FIX-155：正常收束需显式终态帧），
      // 已生成部分完整落地。
      firstController.add(TextEvent(content: ' MORE'));
      firstController.add(DoneEvent(finishReason: 'STOP'));
      await firstController.close();
      await firstFuture;
      await _settleChat();

      final assistantMessages = notifier.state.messages
          .where((message) => message.role == MessageRole.assistant)
          .toList();
      expect(assistantMessages.map((message) => message.content),
          ['partial answer MORE'],);
      expect(assistantMessages.single.isInterrupted, isFalse);
    });

    test('user stop keeps the partial reply and marks it interrupted',
        () async {
      final controller = StreamController<ChatStreamEvent>();
      final repository = _FakeChatRepository(
        (message, conversationId, {userId, requestId, nickname, extraContext, token, fileIds, includeReferences = false, chatMode}) =>
            controller.stream,
      );
      final notifier = await _createNotifier(repository);
      addTearDown(() {
        notifier.dispose();
        unawaited(controller.close());
      });

      final sendFuture = notifier.sendMessage('long question');
      await _settleChat();
      controller.add(TextEvent(content: 'visible partial'));
      await _settleChat();

      notifier.cancelActiveRun(reason: 'user_stop');

      final interrupted = notifier.state.messages
          .where((message) => message.isInterrupted)
          .toList();
      expect(interrupted, hasLength(1));
      expect(interrupted.single.role, MessageRole.assistant);
      expect(interrupted.single.content, 'visible partial');
      expect(notifier.state.isSending, isFalse);
      expect(notifier.state.streamingContent, isEmpty);
      expect(notifier.state.runPhase, ChatRunPhase.interrupted);

      await controller.close();
      await sendFuture;
      expect(
        notifier.state.messages.where((message) => message.isInterrupted),
        hasLength(1),
      );
    });

    test('cancel with no streamed content does not emit an empty bubble',
        () async {
      final firstController = StreamController<ChatStreamEvent>();
      final secondController = StreamController<ChatStreamEvent>();
      final controllers = <StreamController<ChatStreamEvent>>[
        firstController,
        secondController,
      ];
      var index = 0;
      final repository = _FakeChatRepository(
        (message, conversationId, {userId, requestId, nickname, extraContext, token, fileIds, includeReferences = false, chatMode}) =>
            controllers[index++].stream,
      );
      final notifier = await _createNotifier(repository);
      addTearDown(() {
        notifier.dispose();
        unawaited(firstController.close());
        unawaited(secondController.close());
      });

      final firstFuture = notifier.sendMessage('first');
      await _settleChat();
      // B-01 后中断的唯一入口是显式取消（输入条 onStop → cancelActiveRun）。
      notifier.cancelActiveRun(reason: 'user_stop');
      expect(
        notifier.state.messages.where((message) => message.isInterrupted),
        isEmpty,
      );
      // 取消收束后允许新一轮发送。
      final secondFuture = notifier.sendMessage('second');
      secondController
        ..add(TextEvent(content: 'fresh'))
        ..add(DoneEvent(finishReason: 'STOP'));
      await secondFuture;
      await firstController.close();
      await firstFuture;
      await _settleChat();
      expect(
        notifier.state.messages
            .where((message) => message.role == MessageRole.assistant)
            .map((message) => message.content),
        ['fresh'],
      );
    });

    test('isInterrupted flag survives JSON roundtrip for local history', () {
      final interrupted = ChatMessageModel(
        conversationId: 'conv-1',
        role: MessageRole.assistant,
        content: 'partial',
        isInterrupted: true,
      );
      final restored = ChatMessageModel.fromJson(interrupted.toJson());
      expect(restored.isInterrupted, isTrue);

      final normal = ChatMessageModel(
        conversationId: 'conv-1',
        role: MessageRole.assistant,
        content: 'done',
      );
      expect(
        ChatMessageModel.fromJson(normal.toJson()).isInterrupted,
        isFalse,
      );
    });
  });
}
