/// Golden Tests for Chat Screen
/// 聊天屏幕Golden测试
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';

void main() {
  group('Chat Golden Tests', () {
    testGoldens('Chat screen with messages - light theme', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.light(),
          home: ChatScreen(
            messages: _generateMockMessages(5),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(ChatScreen),
        matchesGoldenFile('chat_light_5_messages.png'),
      );
    });

    testGoldens('Chat screen with messages - dark theme', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: ChatScreen(
            messages: _generateMockMessages(5),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(ChatScreen),
        matchesGoldenFile('chat_dark_5_messages.png'),
      );
    });

    testGoldens('Chat screen empty state', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ChatScreen(messages: []),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(ChatScreen),
        matchesGoldenFile('chat_empty.png'),
      );
    });

    testGoldens('Chat screen with plan review card', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: ChatScreen(
            messages: _generateMockMessages(3),
            showPlanReview: true,
            planReviewData: PlanReviewData(
              planId: 'plan-123',
              overallScore: 85,
              issues: [
                PlanIssue(
                  severity: IssueSeverity.warning,
                  message: 'Consider adding more detail to step 2',
                ),
              ],
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(ChatScreen),
        matchesGoldenFile('chat_with_plan_review.png'),
      );
    });

    testGoldens('Chat screen with typing indicator', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: ChatScreen(
            messages: _generateMockMessages(2),
            isTyping: true,
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      await expectLater(
        find.byType(ChatScreen),
        matchesGoldenFile('chat_typing.png'),
      );
    });

    testGoldens('Chat screen with long message', (tester) async {
      final longMessage = ChatMessage(
        id: 'msg-1',
        content:
            'This is a very long message that should wrap to multiple lines. '
            'It contains a lot of text to test how the chat UI handles '
            'messages with substantial content. The text should wrap '
            'properly and maintain readability across different screen sizes.',
        role: 'assistant',
        timestamp: DateTime.now(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ChatScreen(messages: [longMessage]),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(ChatScreen),
        matchesGoldenFile('chat_long_message.png'),
      );
    });

    testGoldens('Chat screen with code block', (tester) async {
      final codeMessage = ChatMessage(
        id: 'msg-1',
        content:
            'Here is the code:\n```python\ndef hello():\n    print("Hello")\n```',
        role: 'assistant',
        timestamp: DateTime.now(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ChatScreen(messages: [codeMessage]),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(ChatScreen),
        matchesGoldenFile('chat_code_block.png'),
      );
    });

    testGoldens('Chat screen with error message', (tester) async {
      final errorMessage = ChatMessage(
        id: 'msg-1',
        content: 'Failed to process request',
        role: 'system',
        timestamp: DateTime.now(),
        isError: true,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ChatScreen(messages: [errorMessage]),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(ChatScreen),
        matchesGoldenFile('chat_error.png'),
      );
    });

    testGoldens('Chat screen responsive - mobile', (tester) async {
      await tester.pumpWidgetBuilder(
        MaterialApp(
          home: MediaQuery(
            data: const MediaQueryData(size: Size(375, 667)),
            child: ChatScreen(messages: _generateMockMessages(10)),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(ChatScreen),
        matchesGoldenFile('chat_mobile.png'),
      );
    });

    testGoldens('Chat screen responsive - tablet', (tester) async {
      await tester.pumpWidgetBuilder(
        MaterialApp(
          home: MediaQuery(
            data: const MediaQueryData(size: Size(768, 1024)),
            child: ChatScreen(messages: _generateMockMessages(10)),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(ChatScreen),
        matchesGoldenFile('chat_tablet.png'),
      );
    });
  });
}

// Mock implementations
class ChatScreen extends StatelessWidget {
  const ChatScreen({
    super.key,
    required this.messages,
    this.isTyping = false,
    this.showPlanReview = false,
    this.planReviewData,
  });
  final List<ChatMessage> messages;
  final bool isTyping;
  final bool showPlanReview;
  final PlanReviewData? planReviewData;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Chat')),
        body: Column(
          children: [
            Expanded(
              child: ListView.builder(
                itemCount: messages.length,
                itemBuilder: (context, index) {
                  final msg = messages[index];
                  return _buildMessageBubble(msg);
                },
              ),
            ),
            if (isTyping) _buildTypingIndicator(),
            if (showPlanReview && planReviewData != null)
              _buildPlanReviewCard(planReviewData!),
          ],
        ),
      );

  Widget _buildMessageBubble(ChatMessage msg) => Container(
        padding: const EdgeInsets.all(12),
        margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
        decoration: BoxDecoration(
          color: msg.isError ? Colors.red.shade100 : Colors.grey.shade200,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(msg.content),
      );

  Widget _buildTypingIndicator() => const Padding(
        padding: EdgeInsets.all(16),
        child: Row(
          children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            SizedBox(width: 8),
            Text('AI is typing...'),
          ],
        ),
      );

  Widget _buildPlanReviewCard(PlanReviewData data) => Container(
        padding: const EdgeInsets.all(16),
        margin: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.blue.shade50,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.blue.shade300),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Plan Review',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            Text('Score: ${data.overallScore}'),
            if (data.issues.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Issues:', style: TextStyle(fontWeight: FontWeight.bold)),
              for (final issue in data.issues) Text('• ${issue.message}'),
            ],
          ],
        ),
      );
}

class ChatMessage {
  ChatMessage({
    required this.id,
    required this.content,
    required this.role,
    required this.timestamp,
    this.isError = false,
  });
  final String id;
  final String content;
  final String role;
  final DateTime timestamp;
  final bool isError;
}

class PlanReviewData {
  PlanReviewData({
    required this.planId,
    required this.overallScore,
    required this.issues,
  });
  final String planId;
  final int overallScore;
  final List<PlanIssue> issues;
}

class PlanIssue {
  PlanIssue({required this.severity, required this.message});
  final IssueSeverity severity;
  final String message;
}

enum IssueSeverity { info, warning, error }

List<ChatMessage> _generateMockMessages(int count) => List.generate(
      count,
      (i) => ChatMessage(
        id: 'msg-$i',
        content: i % 2 == 0 ? 'User message $i' : 'Assistant response $i',
        role: i % 2 == 0 ? 'user' : 'assistant',
        timestamp: DateTime.now(),
      ),
    );
