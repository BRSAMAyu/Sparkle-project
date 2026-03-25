import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/task/data/repositories/subtask_repository.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/screens/task_create_screen.dart';
import 'package:sparkle/features/task/presentation/screens/task_detail_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/subtask_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class _NoopApiClient implements ApiClient {
  @override
  Dio get dio => throw UnimplementedError();

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? headers,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> patch<T>(String path, {Object? data}) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();
}

class _FakeTaskRepository extends TaskRepository {
  _FakeTaskRepository({
    required this.task,
    TaskSuggestionResponse? suggestions,
  })  : suggestions = suggestions ??
            TaskSuggestionResponse(
              intent: 'learning',
              suggestedNodes: const [],
              suggestedTags: const [],
            ),
        super(_NoopApiClient());

  final TaskModel task;
  final TaskSuggestionResponse suggestions;

  @override
  Future<TaskModel> getTask(String id) async => task;

  @override
  Future<TaskSuggestionResponse> getSuggestions(String inputText) async =>
      suggestions;
}

class _FakeSubtaskRepository extends SubtaskRepository {
  _FakeSubtaskRepository() : super(_NoopApiClient());

  @override
  Future<List<SubTaskModel>> getSubtasks(String taskId) async => const [];
}

void main() {
  group('J1 frontend closure', () {
    testWidgets('chat bubble renders malformed markdown stably',
        (tester) async {
      final message = ChatMessageModel(
        conversationId: 'j1-conv',
        role: MessageRole.assistant,
        content: '''
## 今日总结

1. **先做 25 分钟专注**
2. 复习 TCP 三次握手
3. 记录一个最容易混淆的点

```dart
final x = 42;
print(x);
```

未闭合粗体 **这里继续
''',
        aiStatus: 'GENERATING',
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            theme: AppThemes.lightTheme,
            darkTheme: AppThemes.darkTheme,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(
              body: ChatBubble(
                message: message,
                currentUserId: 'me',
                isLatestAssistantMessage: true,
              ),
            ),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.textContaining('今日总结'), findsOneWidget);
      expect(find.textContaining('先做 25 分钟专注'), findsOneWidget);
      expect(find.textContaining('TCP 三次握手'), findsOneWidget);
      expect(find.byIcon(Icons.copy_all_rounded), findsOneWidget);
      expect(find.textContaining('�'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('task create screen stays editable on narrow edit mode',
        (tester) async {
      final taskRepository = _FakeTaskRepository(
        task: TaskModel(
          id: 't-edit',
          userId: 'u-1',
          title: 'TCP 三次握手复盘',
          type: TaskType.learning,
          tags: const ['Network', 'TCP'],
          estimatedMinutes: 45,
          difficulty: 3,
          energyCost: 2,
          status: TaskStatus.pending,
          priority: 2,
          createdAt: DateTime(2026, 3, 25, 8),
          updatedAt: DateTime(2026, 3, 25, 8),
          dueDate: DateTime(2026, 3, 27),
        ),
      );

      final router = GoRouter(
        initialLocation: '/tasks/new?taskId=t-edit',
        routes: [
          GoRoute(
            path: '/tasks/new',
            builder: (context, state) => const TaskCreateScreen(),
          ),
        ],
      );

      tester.view.physicalSize = const Size(375, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskRepositoryProvider.overrideWithValue(taskRepository),
          ],
          child: MaterialApp.router(
            theme: AppThemes.lightTheme,
            darkTheme: AppThemes.darkTheme,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            routerConfig: router,
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 900));
      await tester.pumpAndSettle();

      expect(find.text('编辑任务'), findsOneWidget);
      expect(find.text('TCP 三次握手复盘'), findsOneWidget);
      expect(find.byIcon(Icons.timer_outlined), findsOneWidget);
      expect(find.byIcon(Icons.bar_chart), findsWidgets);
      expect(find.byIcon(Icons.bolt), findsOneWidget);

      await tester.enterText(find.byType(TextFormField).first, 'TCP 挥手复盘');
      await tester.pump();

      expect(find.text('TCP 挥手复盘'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('task detail renders guide markdown without exceptions',
        (tester) async {
      final taskRepository = _FakeTaskRepository(
        task: TaskModel(
          id: 't-guide',
          userId: 'u-1',
          title: 'Python 测验准备',
          type: TaskType.learning,
          tags: const ['Python'],
          estimatedMinutes: 25,
          difficulty: 2,
          energyCost: 2,
          status: TaskStatus.pending,
          priority: 2,
          createdAt: DateTime(2026, 3, 25, 9),
          updatedAt: DateTime(2026, 3, 25, 9),
          guideContent: '''
# AI 执行指南

- 先复习列表推导式
- 再写一个 `for` 循环小例子

```python
nums = [x * 2 for x in range(3)]
print(nums)
```
''',
        ),
      );
      final subtaskRepository = _FakeSubtaskRepository();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskRepositoryProvider.overrideWithValue(taskRepository),
            subtaskRepositoryProvider.overrideWithValue(subtaskRepository),
          ],
          child: MaterialApp(
            theme: AppThemes.lightTheme,
            darkTheme: AppThemes.darkTheme,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: const TaskDetailScreen(taskId: 't-guide'),
          ),
        ),
      );

      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.textContaining('AI 执行指南'), findsWidgets);
      expect(find.textContaining('先复习列表推导式'), findsOneWidget);
      expect(
        find.textContaining('nums = [x * 2 for x in range(3)]'),
        findsOneWidget,
      );
      expect(find.textContaining('�'), findsNothing);
      expect(tester.takeException(), isNull);
    });
  });
}
