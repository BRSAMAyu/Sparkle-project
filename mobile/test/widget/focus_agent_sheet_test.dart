import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/knowledge/data/models/chat_message_model.dart';
import 'package:sparkle/features/knowledge/data/models/focus_session_model.dart';
import 'package:sparkle/data/repositories/focus_repository.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/chat/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/presentation/widgets/focus/focus_agent_sheet.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class FakeFocusRepository implements FocusRepository {
  @override
  Future<FocusSessionResponse> logFocusSession({
    required DateTime startTime,
    required DateTime endTime,
    required int durationMinutes,
    String? taskId,
    String focusType = 'pomodoro',
    String status = 'completed',
    String? whiteNoiseType,
  }) =>
      Future.error(UnimplementedError());

  @override
  Future<FocusStatsResponse> getFocusStats() =>
      Future.error(UnimplementedError());

  @override
  Future<String> getLLMGuidance({
    required String taskTitle,
    required String context,
  }) =>
      Future.error(UnimplementedError());

  @override
  Future<List<String>> breakdownTask({
    required String taskTitle,
    required String taskType,
  }) =>
      Future.error(UnimplementedError());
}

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
      createdAt: DateTime(2024),
      taskId: taskId,
      conversationId: 'test',
    );
    state =
        state.copyWith(messages: [...state.messages, msg], isLoading: false);
  }
}

class FakeMindfulnessNotifier extends MindfulnessNotifier {
  FakeMindfulnessNotifier(MindfulnessState state)
      : super(FakeFocusRepository()) {
    this.state = state;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('FocusAgentSheet renders header and sends quick prompt',
      (tester) async {
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
      createdAt: DateTime(2024),
      updatedAt: DateTime(2024),
    );
    final sentMessages = <String>[];
    final container = ProviderContainer(
      overrides: [
        taskChatProvider.overrideWith(
          (ref, taskId) => FakeTaskChatNotifier(sentMessages, taskId),
        ),
        mindfulnessProvider.overrideWith(
          (ref) => FakeMindfulnessNotifier(
            const MindfulnessState(elapsedSeconds: 600),
          ),
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
