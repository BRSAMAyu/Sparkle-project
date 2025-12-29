import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/data/repositories/chat_repository.dart';
import 'package:sparkle/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/presentation/providers/task_chat_provider.dart';
import 'package:sparkle/presentation/widgets/focus/focus_agent_sheet.dart';

class FakeTaskChatNotifier extends TaskChatNotifier {
  FakeTaskChatNotifier(this.sentMessages, String taskId)
      : super(ChatRepository(Dio()), taskId);

  final List<String> sentMessages;

  @override
  Future<void> sendMessage(String text) async {
    sentMessages.add(text);
    final msg = ChatMessageModel(
      id: 'local',
      userId: 'user',
      role: MessageRole.user,
      content: text,
      createdAt: DateTime(2024, 1),
      taskId: taskId,
      conversationId: 'test',
    );
    state = state.copyWith(messages: [...state.messages, msg], isLoading: false);
  }
}

class FakeMindfulnessNotifier extends StateNotifier<MindfulnessState> {
  FakeMindfulnessNotifier(super.state);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('FocusAgentSheet renders header and sends quick prompt', (tester) async {
    final task = TaskModel(
      id: 'task-1',
      userId: 'user-1',
      title: 'Test Task',
      type: TaskType.learning,
      tags: const [],
      estimatedMinutes: 25,
      difficulty: 1,
      energyCost: 1,
      status: TaskStatus.pending,
      priority: 1,
      createdAt: DateTime(2024, 1),
      updatedAt: DateTime(2024, 1),
    );
    final sentMessages = <String>[];
    final container = ProviderContainer(
      overrides: [
        taskChatProvider.overrideWith((ref, taskId) => FakeTaskChatNotifier(sentMessages, taskId)),
        mindfulnessProvider.overrideWith(
          (ref) => FakeMindfulnessNotifier(const MindfulnessState(elapsedSeconds: 600)),
        ),
      ],
    );

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          home: Scaffold(
            body: FocusAgentSheet(task: task),
          ),
        ),
      ),
    );

    expect(find.text('任务：Test Task · 已专注10分钟'), findsOneWidget);
    expect(find.text('需要帮助就问我！'), findsOneWidget);

    await tester.tap(find.text('拆解接下来15分钟'));
    await tester.pump();

    expect(sentMessages.length, 1);
    expect(sentMessages.first, contains('Test Task'));

    container.dispose();
  });
}
