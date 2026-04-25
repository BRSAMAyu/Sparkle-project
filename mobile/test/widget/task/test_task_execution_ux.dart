import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/screens/task_execution_screen.dart';
import 'package:sparkle/features/task/presentation/widgets/stuck_help_sheet.dart';
import 'package:sparkle/features/task/presentation/widgets/task_guide_panel.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('TaskGuidePanel handles null guideJson without crashing',
      (tester) async {
    final task = _task(
      guideJson: null,
      guideContent: null,
      successCriteria: null,
    );

    await tester.pumpWidget(_materialHost(TaskGuidePanel(task: task)));

    expect(find.text(task.title), findsOneWidget);
    expect(find.text('展开指南'), findsOneWidget);

    await tester.tap(find.byKey(const Key('task-guide-toggle')));
    await tester.pumpAndSettle();

    expect(find.text('这张卡还没有更细的指南，先从你能确定的一小步开始。'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('StuckHelpSheet falls back to generic suggestions',
      (tester) async {
    final task = _task();

    await tester.pumpWidget(
      _materialHost(StuckHelpSheet(task: task)),
    );

    expect(find.text('别担心，我们来看看卡在哪里'), findsOneWidget);
    expect(find.text('把卡住的具体位置写下来'), findsOneWidget);
    expect(find.text('标记这个点，继续其他部分'), findsOneWidget);
  });

  testWidgets(
      'TaskGuidePanel renders structured steps and done criteria progress',
      (tester) async {
    final task = _task(
      guideJson: const <String, dynamic>{
        'focus_cue': '今天最核心的一件事：把三次握手画顺。',
        'steps': [
          {
            'name': '先写出每一步的角色和目的。',
            'duration_min': 5,
            'output': '留下第一版时序骨架。',
          },
          {
            'name': '独立画出完整三次握手流程。',
            'duration_min': 8,
            'output': '画出关键报文和方向。',
          },
          {
            'name': '对照标准答案补标志位和序号。',
            'duration_min': 6,
            'output': '标出遗漏和混淆点。',
          },
          {
            'name': '闭卷再重画一遍。',
            'duration_min': 4,
            'output': '完成最小检查。',
          },
        ],
        'done_criteria': [
          '能说出每一步的目的。',
          '能不看资料重画一遍。',
        ],
      },
    );

    await tester.pumpWidget(
      _materialHost(
        SingleChildScrollView(
          child: TaskGuidePanel(task: task),
        ),
      ),
    );

    await tester.tap(find.byKey(const Key('task-guide-toggle')));
    await tester.pumpAndSettle();

    expect(find.text('先写出每一步的角色和目的。'), findsOneWidget);
    expect(find.text('已完成 0/4'), findsOneWidget);
    expect(find.text('0/2'), findsOneWidget);
    expect(find.text('当前进行中'), findsOneWidget);

    await tester.tap(find.byKey(const Key('guide-step-0')));
    await tester.pumpAndSettle();

    expect(find.text('已完成 1/4'), findsOneWidget);

    await tester.ensureVisible(find.byKey(const Key('done-criterion-0')));
    await tester.tap(find.byKey(const Key('done-criterion-0')));
    await tester.pumpAndSettle();

    expect(find.text('1/2'), findsOneWidget);
  });

  testWidgets('StuckHelpSheet prefers structured fallback levels',
      (tester) async {
    final task = _task(
      guideJson: const <String, dynamic>{
        'fallback_if_stuck': [
          {
            'level': 1,
            'title': '先给半成品框架',
            'guidance': ['定义：___ | 条件：___ | 例子：___'],
          },
          {
            'level': 2,
            'title': '再给关键步骤',
            'guidance': ['先写角色', '再写报文'],
          },
        ],
      },
    );

    await tester.pumpWidget(
      _materialHost(StuckHelpSheet(task: task)),
    );

    expect(find.text('Level 1 · 先给半成品框架'), findsOneWidget);
    expect(find.text('定义：___ | 条件：___ | 例子：___'), findsOneWidget);
    expect(find.text('Level 2 · 再给关键步骤'), findsOneWidget);
  });

  testWidgets('stuck FAB opens help sheet from task execution screen',
      (tester) async {
    final task = _task();

    await tester.pumpWidget(_executionHost(task));
    await tester.pump();

    await tester.tap(find.byKey(const Key('stuck-help-fab')));
    await tester.pumpAndSettle();

    expect(find.text('别担心，我们来看看卡在哪里'), findsOneWidget);
    expect(find.text('把卡住的具体位置写下来'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('completion self-check triggers celebration', (tester) async {
    final task = _task(
      guideJson: const <String, dynamic>{
        'success_criteria': ['写出一个可提交的结论'],
      },
    );

    await tester.pumpWidget(_executionHost(task));
    await tester.pump();

    await tester.tap(find.text('完成任务'));
    await tester.pumpAndSettle();

    expect(find.text('今天完成了！'), findsOneWidget);
    expect(find.text('写出一个可提交的结论'), findsOneWidget);

    await tester.tap(find.text('符合，完成'));
    await tester.pump();

    expect(
      find.byKey(const Key('task-completion-celebration')),
      findsOneWidget,
    );
    expect(find.text('✓ 做到了！'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
  });
}

Widget _materialHost(Widget child) => MaterialApp(
      theme: AppThemes.lightTheme,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: const Locale('zh'),
      home: Scaffold(body: child),
    );

Widget _executionHost(TaskModel task) => ProviderScope(
      overrides: [
        activeTaskProvider.overrideWith((ref) => task),
      ],
      child: MaterialApp(
        theme: AppThemes.lightTheme,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: const TaskExecutionScreen(),
      ),
    );

TaskModel _task({
  Map<String, dynamic>? guideJson = const <String, dynamic>{},
  String? guideContent = '先找到题目要求，再写出你自己的第一版答案。',
  String? successCriteria = '写出一个可提交的结论',
}) {
  final now = DateTime(2026);
  return TaskModel(
    id: 'local-task',
    userId: 'user-1',
    title: '整理错题原因',
    type: TaskType.learning,
    tags: const ['math'],
    estimatedMinutes: 15,
    difficulty: 2,
    energyCost: 1,
    status: TaskStatus.inProgress,
    priority: 1,
    createdAt: now,
    updatedAt: now,
    guideContent: guideContent,
    guideJson: guideJson,
    successCriteria: successCriteria,
  );
}
