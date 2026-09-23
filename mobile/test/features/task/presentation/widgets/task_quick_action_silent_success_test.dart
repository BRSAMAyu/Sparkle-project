import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/task/presentation/widgets/task_card.dart';
import 'package:sparkle/features/task/presentation/widgets/task_quick_action_menu.dart';
import 'package:sparkle/shared/entities/task_model.dart';

import '../../../../shared/i18n_test_helper.dart';

/// N23（A-SPEC4 §4.5 静默成功执行令）· task_quick_action_menu 首刀。
///
/// 验收口径（卡面/A-SPEC4 §5 改造 #7）：
/// - loading toast 取消（TaskCard 内联 spinner 承接等待形状）；
/// - 成功仅状态变化，不再 toast；
/// - 错误路径洗 text（toString replaceFirst）改经 uiErrorMessage 单源 owner；
/// - 重入守卫：同任务在飞时再次唤起菜单直接忽略。
TaskModel _quickActionTask() {
  final now = DateTime(2026, 9, 22, 12);
  return TaskModel(
    id: 'task-quick-action',
    userId: 'user-1',
    title: '整理线性代数错题',
    type: TaskType.learning,
    tags: const ['math'],
    estimatedMinutes: 25,
    difficulty: 2,
    energyCost: 1,
    status: TaskStatus.inProgress,
    priority: 1,
    createdAt: now,
    updatedAt: now,
  );
}

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('TaskCard 内联表达：在飞 → 角部 spinner；空闲 → 无', (tester) async {
    final task = _quickActionTask();

    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: Scaffold(body: TaskCard(task: task)),
        ),
      ),
    );
    // 冲掉 SparkleStaggerItem 的 ≤220ms reveal Timer（timersPending 不变量）。
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(CircularProgressIndicator), findsNothing);

    // 置本任务在飞 → 卡片出现内联 spinner（真容器状态变化驱动 rebuild）。
    final container = ProviderScope.containerOf(
      tester.element(find.byType(TaskCard)),
    );
    container.read(taskQuickActionInFlightProvider.notifier).state = task.id;
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    // 清除在飞 → spinner 消失（在飞状态由菜单 finally 复位）。
    container.read(taskQuickActionInFlightProvider.notifier).state = null;
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('TaskCard 内联表达：其它任务在飞不影响本卡', (tester) async {
    final task = _quickActionTask();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          taskQuickActionInFlightProvider.overrideWith(
            (ref) => 'some-other-task',
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: Scaffold(body: TaskCard(task: task)),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  group('N23 ratchet 机检（task_quick_action_menu 切片）', () {
    final menuSource = File(
      '${Directory.current.path}/lib/features/task/presentation/widgets/'
      'task_quick_action_menu.dart',
    ).readAsStringSync();

    test('quick action 菜单零 loading toast（内联 spinner 承接等待形状）', () {
      expect(menuSource, isNot(contains('AppFeedback.loading(')));
    });

    test('quick action 菜单零 success toast（成功即状态变化）', () {
      expect(menuSource, isNot(contains('AppFeedback.success(')));
    });

    test('错误路径禁洗 toString 直出，必须走 N16 单源映射', () {
      expect(
        menuSource,
        isNot(contains("replaceFirst(RegExp(r'^Exception")),
        reason: 'N15 同型洗 text 禁令（task_quick_action_menu.dart:111/:133 存量清偿）',
      );
      expect(menuSource, contains('categorizeUiError('));
      expect(menuSource, contains('uiErrorMessage('));
    });

    test('重入守卫与内联在飞 provider 在位', () {
      expect(menuSource, contains('taskQuickActionInFlightProvider'));
      expect(
        menuSource,
        contains('ref.read(taskQuickActionInFlightProvider) == task.id'),
      );
    });

    test('TaskCard 消费内联在飞表达（等待必须有形状）', () {
      final cardSource = File(
        '${Directory.current.path}/lib/features/task/presentation/widgets/'
        'task_card.dart',
      ).readAsStringSync();
      expect(cardSource, contains('taskQuickActionInFlightProvider'));
    });
  });
}
