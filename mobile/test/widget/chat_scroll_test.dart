import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import '../shared/i18n_test_helper.dart';

// Mock needed dependencies
class MockChatNotifier extends ChatNotifier {
  MockChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> sendMessage(
    String content, {
    String? taskId,
    Map<String, dynamic>? extraContextOverrides,
    bool reuseLastUserMessage = false,
  }) async {
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
  setUp(setUpI18nForTesting);

  testWidgets('ChatScreen scrolls to bottom (0.0) when new message arrives',
      (WidgetTester tester) async {
    // Initialize SharedPreferences and ViewStorageService
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();

    final mockChatRepo = FakeChatRepository();
    final mockChatNotifier = MockChatNotifier(mockChatRepo, FakeRef());

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          chatProvider.overrideWith((ref) => mockChatNotifier),
        ],
        child: testMaterialApp(home: const ChatScreen()),
      ),
    );

    // Pump several frames to let async initialization settle without using
    // pumpAndSettle, which times out due to the CircularProgressIndicator
    // in the loading state.
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }

    // Seed one message so the ListView is rendered (not the quick action panel).
    mockChatNotifier.addMessage(
      ChatMessageModel(
        id: 'seed',
        conversationId: 'test-session',
        content: 'Seed Message',
        role: MessageRole.user,
        createdAt: DateTime.now(),
      ),
    );
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    // Initial check - find ListView
    final listFinder = find.byWidgetPredicate(
      (widget) => widget is ListView && widget.reverse,
      description: 'reversed chat message list',
    );
    expect(listFinder, findsOneWidget);
    final scrollFinder = find.descendant(
      of: listFinder,
      matching: find.byType(Scrollable),
    );
    expect(scrollFinder, findsOneWidget);

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
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    // Scroll up (visually) -> offset increases
    await tester.drag(listFinder, const Offset(0, 300));
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

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
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    // We expect the scroll position to be back at 0.0
    final scrollableState = tester.state<ScrollableState>(scrollFinder);
    expect(scrollableState.position.pixels, 0.0);
  });
}
