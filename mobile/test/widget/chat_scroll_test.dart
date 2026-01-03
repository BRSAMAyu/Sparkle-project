import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/websocket_chat_service_v2.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/repositories/chat_repository.dart';
import 'package:sparkle/presentation/providers/chat_provider.dart';
import 'package:sparkle/presentation/screens/chat/chat_screen.dart';

// Mock needed dependencies
class MockChatNotifier extends ChatNotifier {
  MockChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> sendMessage(String content, {String? taskId}) async {
    // Mock sending
    state = state.copyWith(
      messages: [
        ChatMessageModel(
          id: DateTime.now().toString(),
          conversationId: 'test-session',
          content: content,
          role: MessageRole.user,
          createdAt: DateTime.now(),
        ),
        ...state.messages,
      ],
    );
  }
  
  void addMessage(ChatMessageModel msg) {
     state = state.copyWith(
      messages: [msg, ...state.messages],
    );
  }
}

class FakeChatRepository extends Fake implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream => const Stream.empty();
  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;
  @override
  void dispose() {}
  @override
  Future<List<Map<String, dynamic>>> getRecentConversations() async => [];
}

class FakeRef extends Fake implements Ref {}

void main() {
  testWidgets('ChatScreen scrolls to bottom (0.0) when new message arrives', (WidgetTester tester) async {
    final mockChatRepo = FakeChatRepository();
    final mockChatNotifier = MockChatNotifier(mockChatRepo, FakeRef());

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          chatProvider.overrideWith((ref) => mockChatNotifier),
        ],
        child: const MaterialApp(home: ChatScreen()),
      ),
    );

    await tester.pumpAndSettle();

    // Initial check - find ListView
    final scrollFinder = find.byType(Scrollable);
    expect(scrollFinder, findsOneWidget);
    
    // In reverse list, 0.0 is the "bottom" (start of list visually)
    final listFinder = find.byType(ListView);
    expect(listFinder, findsOneWidget);

    // Add many messages to ensure scrolling is possible
    for (var i = 0; i < 20; i++) {
        mockChatNotifier.addMessage(
            ChatMessageModel(
                id: 'msg_$i',
                conversationId: 'test-session',
                content: 'Message $i',
                role: MessageRole.assistant,
                createdAt: DateTime.now(),
            ),
        );
    }
    await tester.pumpAndSettle();

    // Scroll up (visually) -> offset increases
    await tester.drag(find.byType(ListView), const Offset(0, 300));
    await tester.pumpAndSettle();
    
    // Add new message
    mockChatNotifier.addMessage(
        ChatMessageModel(
            id: 'new_msg',
            conversationId: 'test-session',
            content: 'New Message',
            role: MessageRole.assistant,
            createdAt: DateTime.now(),
        ),
    );
    
    // Trigger the listener
    await tester.pump(); 
    // Wait for animation
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pumpAndSettle();

    // We expect the scroll position to be back at 0.0
    final scrollableState = tester.state<ScrollableState>(scrollFinder);
    expect(scrollableState.position.pixels, 0.0);
  });
}