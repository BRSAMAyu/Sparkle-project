import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/guest_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';

// 生成 Mock 类
// 实际开发中需要运行 flutter pub run build_runner build
// 这里我们手动定义简单的 Mock 类来模拟

class MockChatRepository extends Mock implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream =>
      Stream.value(WsConnectionState.connected);

  @override
  Future<List<ChatMessageModel>> getConversationHistory(
    String conversationId, {
    int? limit,
    int? offset,
  }) =>
      super.noSuchMethod(
        Invocation.method(
          #getConversationHistory,
          [conversationId],
          {
            #limit: limit,
            #offset: offset,
          },
        ),
        returnValue: Future<List<ChatMessageModel>>.value(const []),
      ) as Future<List<ChatMessageModel>>;

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
      // 模拟流式响应
      Stream.fromIterable([
        StatusUpdateEvent(state: 'THINKING', details: '思考中...'),
        TextEvent(content: 'Hello'),
        TextEvent(content: ' World'),
        DoneEvent(finishReason: 'stop'),
      ]);

  @override
  void dispose() {}
}

void main() {
  late MockChatRepository mockChatRepository;

  setUp(() {
    mockChatRepository = MockChatRepository();
  });

  test('ChatNotifier initial state is correct', () {
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(mockChatRepository),
      ],
    );
    final state = container.read(chatProvider);

    expect(state.isLoading, false);
    expect(state.messages, isEmpty);
    expect(state.hasMoreMessages, false);
    expect(state.wsConnectionState, WsConnectionState.disconnected); // Default
  });

  test('sendMessage updates state with user message and AI response stream',
      () async {
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(mockChatRepository),
      ],
    );

    // We can't fully test sendMessage without deeper mocks of AuthProvider and GuestProvider
    // In a real app we would mock those too.
    // For now this test just validates the provider setup.
    final notifier = container.read(chatProvider.notifier);
    expect(notifier, isNotNull);
  });

  test('loadConversationHistory keeps previous session visible on failure',
      () async {
    I18nService.instance.reset();
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(mockChatRepository),
      ],
    );
    addTearDown(container.dispose);

    final notifier = container.read(chatProvider.notifier);
    final existingMessage = ChatMessageModel(
      id: 'existing-message',
      userId: 'u1',
      conversationId: 'session-1',
      role: MessageRole.assistant,
      content: 'existing',
      createdAt: DateTime.now(),
    );
    notifier.state = notifier.state.copyWith(
      conversationId: 'session-1',
      messages: [existingMessage],
    );

    when(
      mockChatRepository.getConversationHistory(
        'session-2',
        limit: anyNamed('limit'),
      ),
    ).thenAnswer((_) async => throw Exception('boom'));

    await notifier.loadConversationHistory('session-2');

    final state = container.read(chatProvider);
    expect(state.conversationId, 'session-1');
    expect(state.messages, [existingMessage]);
    expect(state.error, isNotNull);
  });

  test('handleWidgetAction queues navigation for core cross-module actions',
      () async {
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(mockChatRepository),
      ],
    );
    addTearDown(container.dispose);

    final notifier = container.read(chatProvider.notifier);

    await notifier.handleWidgetAction('create_task_draft', {
      'payload': {'title': '整理番茄钟任务'},
    });
    expect(container.read(chatProvider).lastActionStatus, 'navigation_ready');
    expect(
      container.read(chatProvider).lastActionMessage,
      '/tasks/new?title=%E6%95%B4%E7%90%86%E7%95%AA%E8%8C%84%E9%92%9F%E4%BB%BB%E5%8A%A1',
    );

    await notifier.handleWidgetAction('open_task', {
      'payload': {'task_id': 'task-42'},
    });
    expect(container.read(chatProvider).lastActionStatus, 'navigation_ready');
    expect(
      container.read(chatProvider).lastActionMessage,
      '/tasks/task-42/execute',
    );

    await notifier.handleWidgetAction('start_focus', {
      'payload': {'task_id': 'focus-7'},
    });
    expect(container.read(chatProvider).lastActionStatus, 'navigation_ready');
    expect(
      container.read(chatProvider).lastActionMessage,
      '/focus/mindfulness/focus-7',
    );

    await notifier.handleWidgetAction('route', {
      'payload': {'route': '/calendar'},
    });
    expect(container.read(chatProvider).lastActionStatus, 'navigation_ready');
    expect(container.read(chatProvider).lastActionMessage, '/calendar');
  });

  test('loadMoreHistory silences transient invalid session pagination errors',
      () async {
    I18nService.instance.reset();
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(mockChatRepository),
      ],
    );
    addTearDown(container.dispose);

    final notifier = container.read(chatProvider.notifier);
    notifier.state = notifier.state.copyWith(
      conversationId: '00000000-0000-0000-0000-000000000123',
      messages: [
        ChatMessageModel(
          id: 'm1',
          userId: 'u1',
          conversationId: '00000000-0000-0000-0000-000000000123',
          role: MessageRole.user,
          content: 'hello',
          createdAt: DateTime.now(),
        ),
      ],
      hasMoreMessages: true,
    );

    when(
      mockChatRepository.getConversationHistory(
        '00000000-0000-0000-0000-000000000123',
        limit: anyNamed('limit'),
        offset: anyNamed('offset'),
      ),
    ).thenAnswer((_) async => throw Exception('invalid session_id'));

    await notifier.loadMoreHistory();

    final state = container.read(chatProvider);
    expect(state.error, isNull);
    expect(state.hasMoreMessages, isFalse);
    expect(state.isLoadingMore, isFalse);
  });

  test('loadMoreHistory ignores synthetic temporary conversations', () async {
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(mockChatRepository),
      ],
    );
    addTearDown(container.dispose);

    final notifier = container.read(chatProvider.notifier);
    notifier.state = notifier.state.copyWith(
      conversationId: 'temp_conversation',
      hasMoreMessages: true,
    );

    await notifier.loadMoreHistory();

    final state = container.read(chatProvider);
    expect(state.hasMoreMessages, isFalse);
    verifyNever(
      mockChatRepository.getConversationHistory(
        'temp_conversation',
        limit: anyNamed('limit'),
        offset: anyNamed('offset'),
      ),
    );
  });

  test('B-01: loadConversationHistory skips while a run is in flight',
      () async {
    I18nService.instance.reset();
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(mockChatRepository),
      ],
    );
    addTearDown(container.dispose);

    final notifier = container.read(chatProvider.notifier);
    final optimisticMessage = ChatMessageModel(
      id: 'temp_user_1',
      userId: 'u1',
      conversationId: 'session-live',
      role: MessageRole.user,
      content: '7天后考离散数学',
      createdAt: DateTime.now(),
    );
    notifier.state = notifier.state.copyWith(
      conversationId: 'session-live',
      messages: [optimisticMessage],
      isSending: true,
      activeRunId: 'run_1',
    );

    await notifier.loadConversationHistory('session-live');

    // V13「发了但看不见」的移动端共因：在途回拉会冲掉乐观气泡与流式态。
    final state = container.read(chatProvider);
    expect(state.isSending, isTrue, reason: '在途轮次不得被打断');
    expect(state.messages, [optimisticMessage], reason: '乐观气泡不得被冲掉');
    expect(state.streamingContent, isEmpty);
    verifyNever(
      mockChatRepository.getConversationHistory(
        'session-live',
        limit: anyNamed('limit'),
      ),
    );
  });

  test('B-01: sendMessage is blocked while a run is in flight', () async {
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(mockChatRepository),
      ],
    );
    addTearDown(container.dispose);

    final notifier = container.read(chatProvider.notifier);
    notifier.state = notifier.state.copyWith(
      isSending: true,
      activeRunId: 'run_in_flight',
    );

    // in-flight 禁发：早退于 auth/guest 读取之前，重复触发静默丢弃，
    // 不再 cancel+supersede 造成重复消息与重复 LLM 回复。
    await notifier.sendMessage('重复发送');

    final state = container.read(chatProvider);
    expect(state.activeRunId, 'run_in_flight', reason: '在途 run 不得被顶替');
    expect(state.messages, isEmpty, reason: '不得追加第二条用户消息');
  });

  test('V3-FIX-155: stream closing without terminal event fails the run '
      '(错误态非静默，不得当完整答案)', () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
    final prefs = await SharedPreferences.getInstance();
    I18nService.instance.reset();
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(_NoTerminalEventRepository()),
        authProvider.overrideWith((ref) => _UnusedAuthNotifier()),
        authRepositoryProvider.overrideWithValue(_StubAuthRepository()),
        guestServiceProvider.overrideWithValue(GuestService(prefs)),
      ],
    );
    addTearDown(container.dispose);

    final notifier = container.read(chatProvider.notifier);
    await notifier.sendMessage('讲讲方法');

    final state = container.read(chatProvider);
    expect(
      state.runPhase,
      ChatRunPhase.failed,
      reason: '流关闭而无 DoneEvent/ErrorEvent（网关/引擎中断、socket 静默断开）'
          '= 本轮被中断，runPhase 不得静默落 completed',
    );
    expect(
      // 与 chat_provider.dart 的 kChatStreamInterruptedCode 字面一致；
      // 用字面量让 base（无该常量）可编译，行为红可实录。
      state.errorCode,
      'STREAM_INTERRUPTED',
      reason: '中断态必须以 STREAM_INTERRUPTED 显式落码（经流收尾路径而非异常兜底）',
    );
    expect(state.isSending, isFalse, reason: '失败收尾必须重置 isSending');
  });
}

/// V3-FIX-155：token 读取桩（避免测试环境 secure storage 平台通道）。
class _StubAuthRepository extends AuthRepository {
  _StubAuthRepository() : super(_UnusedApiClient(), _UnusedTokenStorage());

  @override
  Future<String?> getAccessToken() async => 'test-token';
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedTokenStorage implements TokenStorage {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// V3-FIX-155：只发部分文本后关闭、无任何终态事件的流（模拟网关/引擎中断）。
class _NoTerminalEventRepository extends MockChatRepository {
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
      Stream.fromIterable([
        StatusUpdateEvent(state: 'THINKING', details: '思考中...'),
        TextEvent(content: '部分文本'),
        // 无 DoneEvent / ErrorEvent —— 流静默关闭
      ]);
}

class _UnusedAuthNotifier extends AuthNotifier {
  _UnusedAuthNotifier() : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState();
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedAuthRepository implements AuthRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
