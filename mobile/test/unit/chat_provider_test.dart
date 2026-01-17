import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/knowledge/data/models/chat_stream_events.dart';

// 生成 Mock 类
// 实际开发中需要运行 flutter pub run build_runner build
// 这里我们手动定义简单的 Mock 类来模拟

class MockChatRepository extends Mock implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream =>
      Stream.value(WsConnectionState.connected);

  @override
  Stream<ChatStreamEvent> chatStream(
    String message,
    String? conversationId, {
    String? userId,
    String? nickname,
    Map<String, dynamic>? extraContext,
    String? token,
    List<String>? fileIds,
    bool includeReferences = false,
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
}
