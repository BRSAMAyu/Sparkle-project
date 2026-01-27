// Flutter Integration Test: Complete User Journey
// ====================================================
//
// Tests the complete Flutter app flow:
// UI Interactions → State Management → WebSocket → Backend → Response

import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:sparkle_mobile/main.dart' as app;
import 'package:sparkle_mobile/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle_mobile/features/home/presentation/providers/intent_prediction_provider.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('E2E: Complete Chat Flow', () {
    testWidgets('User sends message → Receives response → UI updated', (tester) async {
      // 1. Build app
      app.main();
      await tester.pumpAndSettle();

      // 2. Navigate to chat screen
      final chatButtonFinder = find.text('聊天');
      expect(chatButtonFinder, findsOneWidget);
      await tester.tap(chatButtonFinder);
      await tester.pumpAndSettle();

      // 3. Find omnibar input
      final omnibarFinder = find.byKey(const Key('omnibar_input'));
      expect(omnibarFinder, findsOneWidget);

      // 4. Type message
      await tester.enterText(omnibarFinder, '我想学习Python');
      await tester.pumpAndSettle();

      // 5. Send message
      final sendButtonFinder = find.byKey(const Key('send_message_button'));
      await tester.tap(sendButtonFinder);
      await tester.pumpAndSettle();

      // 6. Verify user message displayed
      expect(find.text('我想学习Python'), findsOneWidget);

      // 7. Wait for response (simulate streaming)
      await tester.pump(const Duration(seconds: 2));

      // 8. Verify assistant response displayed
      final responseFinder = find.byType(AssistantMessageBubble);
      expect(responseFinder, findsOneWidget);
    });

    testWidgets('User creates plan → Tasks displayed → Can complete', (tester) async {
      // 1. Build and navigate
      app.main();
      await tester.pumpAndSettle();

      // 2. Request plan creation via chat
      final omnibarFinder = find.byKey(const Key('omnibar_input'));
      await tester.enterText(omnibarFinder, '制定一个7天Python学习计划');
      await tester.pumpAndSettle();

      final sendButtonFinder = find.byKey(const Key('send_message_button'));
      await tester.tap(sendButtonFinder);
      await tester.pumpAndSettle();

      // 3. Wait for plan creation (mock response)
      await tester.pump(const Duration(seconds: 3));

      // 4. Navigate to task board
      final taskBoardFinder = find.text('任务板');
      expect(taskBoardFinder, findsOneWidget);
      await tester.tap(taskBoardFinder);
      await tester.pumpAndSettle();

      // 5. Verify tasks displayed
      final taskCardFinder = find.byType(TaskBoardCard);
      expect(taskCardFinder, findsWidgets);

      // 6. Complete first task
      final firstTaskCard = taskCardFinder.first;
      await tester.tap(firstTaskCard);
      await tester.pumpAndSettle();

      final completeButtonFinder = find.text('完成任务');
      expect(completeButtonFinder, findsOneWidget);
      await tester.tap(completeButtonFinder);
      await tester.pumpAndSettle();

      // 7. Verify task marked as completed
      expect(find.byIcon(Icons.check_circle), findsOneWidget);
    });
  });

  group('E2E: Knowledge Galaxy', () {
    testWidgets('User views galaxy → Can interact with nodes', (tester) async {
      app.main();
      await tester.pumpAndSettle();

      // 1. Navigate to galaxy
      final galaxyFinder = find.text('知识星图');
      await tester.tap(galaxyFinder);
      await tester.pumpAndSettle();

      // 2. Verify galaxy displayed
      final galaxyWidgetFinder = find.byType(KnowledgeGalaxyWidget);
      expect(galaxyWidgetFinder, findsOneWidget);

      // 3. Tap on a node
      final nodeFinder = find.byType(KnowledgeNodeWidget).first;
      await tester.tap(nodeFinder);
      await tester.pumpAndSettle();

      // 4. Verify node detail displayed
      expect(find.text('节点详情'), findsOneWidget);
    });
  });

  group('E2E: Offline Mode', () {
    testWidgets('User offline → Actions queued → Sync on reconnect', (tester) async {
      app.main();
      await tester.pumpAndSettle();

      // 1. Simulate offline mode
      final offlineProvider = tester.provider<ConnectivityProvider>();
      offlineProvider.setOffline(true);
      await tester.pumpAndSettle();

      // 2. Verify offline indicator shown
      expect(find.text('离线模式'), findsOneWidget);

      // 3. Create task while offline
      final omnibarFinder = find.byKey(const Key('omnibar_input'));
      await tester.enterText(omnibarFinder, '创建任务:学习变量');
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('send_message_button')));
      await tester.pumpAndSettle();

      // 4. Verify queued indicator
      expect(find.text('已加入同步队列'), findsOneWidget);

      // 5. Reconnect
      offlineProvider.setOffline(false);
      await tester.pumpAndSettle();

      // 6. Verify sync completed
      await tester.pump(const Duration(seconds: 2));
      expect(find.text('同步完成'), findsOneWidget);
    });
  });

  group('E2E: Settings and Preferences', () {
    testWidgets('User changes settings → Preferences persisted', (tester) async {
      app.main();
      await tester.pumpAndSettle();

      // 1. Navigate to settings
      final settingsFinder = find.text('设置');
      await tester.tap(settingsFinder);
      await tester.pumpAndSettle();

      // 2. Change theme
      final themeFinder = find.text('主题');
      await tester.tap(themeFinder);
      await tester.pumpAndSettle();

      final darkModeFinder = find.text('深色模式');
      await tester.tap(darkModeFinder);
      await tester.pumpAndSettle();

      // 3. Verify theme changed
      final brightness = tester.widget<MaterialApp>(find.byType(MaterialApp)).theme.brightness;
      expect(brightness, Brightness.dark);

      // 4. Restart app (simulate)
      app.main();
      await tester.pumpAndSettle();

      // 5. Verify preference persisted
      final persistedBrightness = tester.widget<MaterialApp>(find.byType(MaterialApp)).theme.brightness;
      expect(persistedBrightness, Brightness.dark);
    });
  });

  group('E2E: Error Handling', () {
    testWidgets('Network error → Retry mechanism → Success', (tester) async {
      app.main();
      await tester.pumpAndSettle();

      // 1. Mock network error
      final mockService = tester.provider<ChatService>();
      mockService.setShouldFail(true);

      // 2. Try to send message
      final omnibarFinder = find.byKey(const Key('omnibar_input'));
      await tester.enterText(omnibarFinder, 'Test message');
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('send_message_button')));
      await tester.pumpAndSettle();

      // 3. Verify error displayed
      expect(find.text('网络错误，正在重试...'), findsOneWidget);

      // 4. Mock successful retry
      mockService.setShouldFail(false);
      await tester.pump(const Duration(seconds: 3));

      // 5. Verify retry succeeded
      expect(find.text('发送成功'), findsOneWidget);
    });
  });

  group('E2E: Performance', () {
    testWidgets('Large message list → Scrolling performance', (tester) async {
      app.main();
      await tester.pumpAndSettle();

      // 1. Navigate to chat with large history
      final chatProvider = tester.provider<ChatProvider>();
      await chatProvider.loadLargeHistory(count: 1000);
      await tester.pumpAndSettle();

      // 2. Measure scroll performance
      final stopwatch = Stopwatch()..start();
      await tester.fling(
        find.byType(ChatMessageList),
        const Offset(0, -500),
        10000,
      );
      await tester.pumpAndSettle();
      stopwatch.stop();

      // 3. Verify smooth scrolling (should take < 100ms)
      expect(stopwatch.elapsedMilliseconds, lessThan(100));
    });
  });
}

// Mock widgets and providers for testing
class TaskBoardCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container();
  }
}

class AssistantMessageBubble extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container();
  }
}

class KnowledgeGalaxyWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container();
  }
}

class KnowledgeNodeWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container();
  }
}

class ChatMessageList extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container();
  }
}
