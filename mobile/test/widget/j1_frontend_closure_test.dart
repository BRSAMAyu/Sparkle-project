import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_message_renderer.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/task/data/repositories/subtask_repository.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/screens/task_create_screen.dart';
import 'package:sparkle/features/task/presentation/screens/task_detail_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/subtask_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';
import '../shared/i18n_test_helper.dart';

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
    TaskGuidanceModel? humanGuidance,
    TaskGuidanceModel? aiGuidance,
  })  : suggestions = suggestions ??
            TaskSuggestionResponse(
              intent: 'learning',
              suggestedNodes: const [],
              suggestedTags: const [],
            ),
        _guidanceByAudience = {
          if (humanGuidance != null) TaskGuidanceAudience.human: humanGuidance,
          if (aiGuidance != null) TaskGuidanceAudience.ai: aiGuidance,
        },
        super(_NoopApiClient());

  final TaskModel task;
  final TaskSuggestionResponse suggestions;
  final Map<TaskGuidanceAudience, TaskGuidanceModel> _guidanceByAudience;

  @override
  Future<TaskModel> getTask(String id) async => task;

  @override
  Future<PaginatedResponse<TaskModel>> getTasks({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 10,
  }) async =>
      PaginatedResponse(
        items: [task],
        total: 1,
        page: page,
        pageSize: pageSize,
      );

  @override
  Future<List<TaskModel>> getTodayTasks() async => const [];

  @override
  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async =>
      const [];

  @override
  Future<TaskSuggestionResponse> getSuggestions(String inputText) async =>
      suggestions;

  @override
  Future<TaskGuidanceModel?> getTaskGuidance(
    String taskId, {
    TaskGuidanceAudience audience = TaskGuidanceAudience.human,
  }) async =>
      _guidanceByAudience[audience];

  @override
  Future<TaskGuidanceModel> createOrRefreshTaskGuidance(
    String taskId, {
    TaskGuidanceAudience audience = TaskGuidanceAudience.human,
    bool regenerate = false,
  }) async {
    final next = TaskGuidanceModel(
      id: 'guidance-$taskId-${audience.wireValue}',
      taskId: taskId,
      userId: task.userId,
      audience: audience,
      content: audience == TaskGuidanceAudience.human
          ? '''
# 用户版任务指南

- 先抓主线，再开始
- 做完后回到 Sparkle 里记录结果
'''
          : '''
TASK_GUIDANCE_SCAFFOLD v1
task_id=$taskId
task_title=${task.title}
Use this only inside Sparkle task assistant.
''',
      generatedBy: audience == TaskGuidanceAudience.human
          ? 'test_human_guidance'
          : 'test_ai_guidance',
      policyVersion: 'stage4.task_guidance.v1',
      contentFormat:
          audience == TaskGuidanceAudience.human ? 'markdown' : 'plaintext',
      createdAt: DateTime(2026, 4, 19, 9),
      updatedAt: DateTime(2026, 4, 19, regenerate ? 11 : 10),
      sourceTaskUpdatedAt: task.updatedAt,
    );
    _guidanceByAudience[audience] = next;
    return next;
  }
}

class _FakeSubtaskRepository extends SubtaskRepository {
  _FakeSubtaskRepository() : super(_NoopApiClient());

  @override
  Future<List<SubTaskModel>> getSubtasks(String taskId) async => const [];
}

void main() {

  setUp(setUpI18nForTesting);
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
      expect(find.byIcon(Icons.copy_rounded), findsOneWidget);
      expect(find.textContaining('�'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets(
        'chat bubble normalizes question-mark bullets into markdown list',
        (tester) async {
      final message = ChatMessageModel(
        conversationId: 'j1-bullets',
        role: MessageRole.assistant,
        content: '''
好的，我们来练习英语。你可以先告诉我一个话题，或者我来提供一些选项。

? **日常话题**：天气、爱好、周末计划
? **情景对话**：点餐、问路、购物
? **观点讨论**：喜欢的电影、对某件事的看法
''',
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
              ),
            ),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 220));

      expect(find.textContaining('日常话题'), findsOneWidget);
      expect(find.textContaining('情景对话'), findsOneWidget);
      expect(find.textContaining('观点讨论'), findsOneWidget);
      expect(find.textContaining('? **'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('agent message renderer uses the same markdown pipeline',
        (tester) async {
      final message = ChatMessageModel(
        conversationId: 'j1-agent-renderer',
        role: MessageRole.assistant,
        content: '''
好的，我们来练习英语。你可以先告诉我一个话题，或者我来提供一些选项。

? **日常话题**：天气、爱好、周末计划
❓ **情景对话**：点餐、问路、购物
— **观点讨论**：喜欢的电影、对某件事的看法
''',
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            theme: AppThemes.lightTheme,
            darkTheme: AppThemes.darkTheme,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(
              body: AgentMessageRenderer(message: message),
            ),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 220));

      expect(find.textContaining('日常话题'), findsOneWidget);
      expect(find.textContaining('情景对话'), findsOneWidget);
      expect(find.textContaining('观点讨论'), findsOneWidget);
      expect(find.textContaining('? **'), findsNothing);
      expect(find.textContaining('❓'), findsNothing);
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

    testWidgets(
        'task detail renders Stage 4 guidance surface on the default human path',
        (tester) async {
      AppFeatureFlags.enableTaskGuidanceV2 = true;
      addTearDown(() => AppFeatureFlags.enableTaskGuidanceV2 = false);

      const taskId = '11111111-1111-1111-1111-111111111111';
      final taskRepository = _FakeTaskRepository(
        task: TaskModel(
          id: taskId,
          userId: 'u-1',
          title: '数据库索引复盘',
          type: TaskType.learning,
          tags: const ['DB'],
          estimatedMinutes: 35,
          difficulty: 3,
          energyCost: 2,
          status: TaskStatus.pending,
          priority: 2,
          createdAt: DateTime(2026, 4, 19, 8),
          updatedAt: DateTime(2026, 4, 19, 8),
          guideContent: '# 旧版指南\n\n- legacy',
        ),
        humanGuidance: TaskGuidanceModel(
          id: 'guidance-human',
          taskId: taskId,
          userId: 'u-1',
          audience: TaskGuidanceAudience.human,
          content: '''
# 用户版任务指南

- 先抓主线，再开始
- 做完后回到 Sparkle 里记录结果
''',
          generatedBy: 'test_human_guidance',
          policyVersion: 'stage4.task_guidance.v1',
          contentFormat: 'markdown',
          createdAt: DateTime(2026, 4, 19, 9),
          updatedAt: DateTime(2026, 4, 19, 10),
          sourceTaskUpdatedAt: DateTime(2026, 4, 19, 8),
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
            home: const TaskDetailScreen(taskId: taskId),
          ),
        ),
      );

      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.text('给自己看'), findsOneWidget);
      expect(find.text('给 AI 用'), findsOneWidget);
      expect(find.textContaining('先抓主线，再开始'), findsOneWidget);
      expect(find.textContaining('默认闭环交付'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
