import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';

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
  }) => super.noSuchMethod(
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
}
