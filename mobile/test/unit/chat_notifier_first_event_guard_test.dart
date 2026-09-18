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
import 'package:sparkle/core/storage/token_storage_io.dart';

/// M-2 stream variance red-green: main chat chain first-event guard.
///
/// Covers the guard semantics added to ChatNotifier.sendMessage: 30s (shrunk
/// here) with zero stream events triggers one automatic resend on a derived
/// request id after a reconnect; a second silent run surfaces the existing
/// failure state.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Duration originalGuardTimeout = ChatNotifier.firstEventGuardTimeout;

  setUp(() {
    originalGuardTimeout = ChatNotifier.firstEventGuardTimeout;
    // Shrink the 30s production window so tests run in real time quickly.
    ChatNotifier.firstEventGuardTimeout = const Duration(milliseconds: 120);
  });

  tearDown(() {
    ChatNotifier.firstEventGuardTimeout = originalGuardTimeout;
  });

  Future<void> waitFor(
    bool Function() condition, {
    Duration timeout = const Duration(seconds: 4),
    String reason = 'condition not met in time',
  }) async {
    final watch = Stopwatch()..start();
    while (!condition() && watch.elapsed < timeout) {
      await Future<void>.delayed(const Duration(milliseconds: 20));
    }
    expect(condition(), isTrue, reason: reason);
  }

  test(
    'guard fires on silent stream, reconnects and resends once with a derived request id',
    () async {
      final silentController = StreamController<ChatStreamEvent>();
      final requestIds = <String>[];
      var reconnectCalls = 0;

      Stream<ChatStreamEvent> recoveredStream() async* {
        yield TextEvent(content: 'recovered');
        yield DoneEvent(finishReason: 'STOP');
      }

      final repository = _FakeChatRepository(
        (message, conversationId, {userId, requestId, nickname, extraContext, token, fileIds, includeReferences = false, chatMode}) {
          requestIds.add(requestId ?? '');
          if (requestIds.length == 1) {
            // First attempt: never emits, never closes -> guard must fire.
            return silentController.stream;
          }
          return recoveredStream();
        },
      )..onReconnect = () => reconnectCalls++;

      final notifier = await _createNotifier(repository);
      addTearDown(() {
        notifier.dispose();
        unawaited(silentController.close());
      });

      await notifier.sendMessage('hello');

      expect(reconnectCalls, 1, reason: 'guard must reconnect exactly once');
      expect(requestIds, hasLength(2));
      expect(requestIds[1], '${requestIds[0]}_r1');
      expect(notifier.state.runPhase, ChatRunPhase.completed);
      expect(notifier.state.error, isNull);
      expect(
        notifier.state.messages.where((message) => message.role == MessageRole.assistant).map((message) => message.content),
        contains('recovered'),
      );
    },
  );

  test('second silent run exhausts the guard and surfaces the failure state', () async {
    final silentControllers = <StreamController<ChatStreamEvent>>[];
    final requestIds = <String>[];
    var reconnectCalls = 0;

    final repository = _FakeChatRepository(
      (message, conversationId, {userId, requestId, nickname, extraContext, token, fileIds, includeReferences = false, chatMode}) {
        requestIds.add(requestId ?? '');
        final controller = StreamController<ChatStreamEvent>();
        silentControllers.add(controller);
        return controller.stream;
      },
    )..onReconnect = () => reconnectCalls++;

    final notifier = await _createNotifier(repository);
    addTearDown(() {
      notifier.dispose();
      for (final controller in silentControllers) {
        unawaited(controller.close());
      }
    });

    final sendFuture = notifier.sendMessage('still silent');
    await waitFor(
      () => notifier.state.runPhase == ChatRunPhase.failed,
      reason: 'run should fail after two silent attempts',
    );
    await sendFuture;

    expect(reconnectCalls, 1);
    expect(requestIds, hasLength(2));
    expect(requestIds[1], '${requestIds[0]}_r1');
    expect(notifier.state.runPhase, ChatRunPhase.failed);
    expect(notifier.state.errorCode, kChatFirstEventTimeoutCode);
    expect(notifier.state.isErrorRetryable, isTrue);
    expect(notifier.state.error, isNotEmpty);
  });

  test('an early status frame counts as a first event and disarms the guard', () async {
    final requestIds = <String>[];
    var reconnectCalls = 0;
    late final StreamController<ChatStreamEvent> controller;

    final repository = _FakeChatRepository(
      (message, conversationId, {userId, requestId, nickname, extraContext, token, fileIds, includeReferences = false, chatMode}) {
        requestIds.add(requestId ?? '');
        return controller.stream;
      },
    )..onReconnect = () => reconnectCalls++;

    controller = StreamController<ChatStreamEvent>();
    final notifier = await _createNotifier(repository);
    addTearDown(() {
      notifier.dispose();
      unawaited(controller.close());
    });

    final sendFuture = notifier.sendMessage('alive stream');
    await Future<void>.delayed(const Duration(milliseconds: 40));

    controller.add(StatusUpdateEvent(state: 'THINKING', details: 'orchestrating'));

    // Stay silent well past the guard window: no reconnect, no resend.
    await Future<void>.delayed(ChatNotifier.firstEventGuardTimeout * 3);
    expect(reconnectCalls, 0);
    expect(requestIds, hasLength(1));
    expect(notifier.state.runPhase, ChatRunPhase.streaming);

    controller.add(DoneEvent(finishReason: 'STOP'));
    await sendFuture;

    expect(notifier.state.runPhase, ChatRunPhase.completed);
    expect(reconnectCalls, 0);
  });
}

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
  void Function()? onReconnect;
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
  Future<void> reconnect() async {
    onReconnect?.call();
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
    authState: AuthState(isAuthenticated: false, user: null),
    guestService: guestService,
    authRepository: _FakeAuthRepository(token: 'test-token'),
  );
  return ChatNotifier(repository, ref);
}
