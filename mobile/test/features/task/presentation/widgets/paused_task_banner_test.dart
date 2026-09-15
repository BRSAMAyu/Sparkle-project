import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/task/presentation/widgets/paused_task_status_panel.dart';
import 'package:sparkle/shared/entities/task_model.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('paused banner renders status, duration, and reason details',
      (tester) async {
    final task = _pausedTask(
      pausedReason: 'inactivity',
      pausedAt: DateTime.now().subtract(const Duration(hours: 3, minutes: 5)),
    );

    await tester.pumpWidget(
      testMaterialApp(
        theme: AppThemes.lightTheme,
        home: Scaffold(
          body: PausedTaskBanner(task: task),
        ),
      ),
    );

    expect(find.byIcon(Icons.pause_circle_outline_rounded), findsOneWidget);
    expect(find.text('任务已暂停'), findsOneWidget);
    expect(find.textContaining('已暂停 3 小时'), findsOneWidget);
    expect(find.text('查看暂停原因'), findsOneWidget);

    await tester.tap(find.text('查看暂停原因'));
    await tester.pumpAndSettle();

    expect(find.text('暂停原因'), findsOneWidget);
    expect(find.textContaining('长时间未继续'), findsWidgets);
  });

  testWidgets('paused banner resume button invokes callback', (tester) async {
    var resumeCount = 0;

    await tester.pumpWidget(
      testMaterialApp(
        theme: AppThemes.lightTheme,
        home: Scaffold(
          body: PausedTaskBanner(
            task: _pausedTask(pausedReason: 'manual'),
            onResume: () async { resumeCount += 1; return true; },
          ),
        ),
      ),
    );

    await tester.tap(find.text('继续任务'));
    await tester.pump();

    expect(resumeCount, 1);
    expect(find.text('已请求恢复任务。'), findsOneWidget);
  });
}

TaskModel _pausedTask({
  String? pausedReason,
  DateTime? pausedAt,
}) {
  final now = DateTime(2026, 4, 25, 12);
  return TaskModel(
    id: 'task-paused',
    userId: 'user-1',
    title: '整理错题原因',
    type: TaskType.learning,
    tags: const ['math'],
    estimatedMinutes: 25,
    difficulty: 2,
    energyCost: 1,
    status: TaskStatus.paused,
    priority: 1,
    createdAt: now,
    updatedAt: now,
    pausedReason: pausedReason,
    pausedAt: pausedAt ?? now,
  );
}
