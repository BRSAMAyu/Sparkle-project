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
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart'
    show WsConnectionState;
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/guidance_mode_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

/// V4-FIX-566①：纯连接失败 reuse 重试路径的 provider 侧语义钉
/// （`retryLastMessage` → `sendMessage(reuseLastUserMessage: true)`，
/// chat_provider.dart 的 canReuseLastUserMessage 分支）：
/// - 用户消息居末位 + 内容相同 → 不追加重复用户消息（B-01 反重复计费）；
/// - 重试照常开启新一轮 run（isSending）。
/// 屏幕侧「点重试 → force 滚动」差量由
/// test/widget/chat_f566_retry_force_scroll_jump_latest_test.dart 钉。
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
  WsConnectionState get connectionState => WsConnectionState.failed;

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
          chatMode: chatMode,);

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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('F566① 纯连接失败后 reuse 重试：不追加重复用户消息且照常开启新 run',
      () async {
    final firstAttempt = StreamController<ChatStreamEvent>();
    final retryAttempt = StreamController<ChatStreamEvent>();
    final attempts = <StreamController<ChatStreamEvent>>[
      firstAttempt,
      retryAttempt,
    ];
    var index = 0;
    final repository = _FakeChatRepository(
      (message, conversationId,
              {userId, requestId, nickname, extraContext, token, fileIds,
              includeReferences = false, chatMode,}) =>
          attempts[index++].stream,
    );
    final notifier = await _createNotifier(repository);
    addTearDown(() {
      notifier.dispose();
      unawaited(firstAttempt.close());
      unawaited(retryAttempt.close());
    });

    // 首次发送：用户消息追加 → 流即刻报错（纯连接失败，无部分内容保留）。
    final failedSend = notifier.sendMessage('连接测试');
    await _settleChat();
    final failureStream = firstAttempt
      ..add(
        ErrorEvent(
          code: 'STREAM_TIMEOUT',
          message: 'connection lost',
          retryable: true,
        ),
      );
    unawaited(failureStream.close());
    await failedSend;
    await _settleChat();

    // 失败态前置自证：用户消息居末位（canReuseLastUserMessage 前提）。
    expect(notifier.state.error, isNotEmpty);
    expect(notifier.state.isErrorRetryable, isTrue);
    expect(notifier.state.messages.last.role, MessageRole.user);
    expect(notifier.state.messages.last.content, '连接测试');
    final userMessagesBefore = notifier.state.messages
        .where((message) => message.role == MessageRole.user)
        .length;
    expect(userMessagesBefore, 1);

    // reuse 重试：不追加重复用户消息，但新一轮 run 照常开启。
    unawaited(notifier.retryLastMessage());
    await _settleChat();

    expect(
      notifier.state.messages
          .where((message) => message.role == MessageRole.user)
          .map((message) => message.content),
      ['连接测试'],
      reason: 'reuse 路径复用末位用户消息，不追加重复项（B-01 反重复计费语义）',
    );
    expect(notifier.state.isSending, isTrue, reason: '重试已开启新一轮 run');
    expect(notifier.state.error, isNull, reason: '重试入口先清错误');
  });
}
