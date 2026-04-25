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
