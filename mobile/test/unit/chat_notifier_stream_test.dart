import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/guest_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
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
      : super(_NoopApiClient(), const FlutterSecureStorage());

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
  }) {
    return _streamFactory(
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
  }

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
    this.activePlanId = 'plan-1',
    this.reasoningMode = 'balanced',
    this.seedLibraryEnabled = false,
    ChatMode? chatMode,
  }) : chatMode = chatMode ?? standard;

  final AuthState authState;
  final GuestService guestService;
  final AuthRepository authRepository;
  final String activePlanId;
  final String reasoningMode;
  final bool seedLibraryEnabled;
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
    authState: AuthState(isAuthenticated: false, user: null),
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

    test('cancels the previous run before accepting a new stream', () async {
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

      final secondFuture = notifier.sendMessage('second');
      await _settleChat();

      firstController.add(TextEvent(content: 'stale'));
      await firstController.close();
      await firstFuture;

      secondController
        ..add(TextEvent(content: 'fresh'))
        ..add(DoneEvent(finishReason: 'STOP'));
      await secondFuture;
      await _settleChat();

      final assistantMessages = notifier.state.messages
          .where((message) => message.role == MessageRole.assistant)
          .toList();
      expect(assistantMessages, hasLength(1));
      expect(assistantMessages.single.content, 'fresh');
      expect(assistantMessages.single.content, isNot(contains('stale')));
    });
  });
}
