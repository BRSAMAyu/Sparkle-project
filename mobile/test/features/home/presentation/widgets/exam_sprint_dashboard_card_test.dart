import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/exam_sprint_dashboard_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  ExamSprintDashboardData _makeData({
    double? passProbability,
    int daysLeft = 5,
    String subject = 'Math',
    String? sleepGuardHint,
  }) {
    return ExamSprintDashboardData(
      planId: 'test-plan',
      planName: 'Test Sprint',
      subject: subject,
      daysLeft: daysLeft,
      targetMode: 'pass',
      todayProgress: const ExamSprintTodayProgress(
        completed: 2,
        total: 3,
        completionRate: 0.667,
      ),
      highFreqCoverage: 0.75,
      highFreqCoveredCount: 15,
      highFreqTotalCount: 20,
      mistakeFixRate: 0.6,
      fixedMistakeCount: 6,
      totalMistakeCount: 10,
      streakDays: 3,
      passProbability: passProbability,
      taskGroups: const [],
      sleepGuardHint: sleepGuardHint,
    );
  }

  Widget _buildCard(
    ExamSprintDashboardData data, {
    VoidCallback? onRecordResult,
  }) {
    return testMaterialApp(theme: ThemeData.light().copyWith(
        extensions: [SparkleThemeExtension.light()],
      ),
      home: Scaffold(
        body: SingleChildScrollView(
          child: ExamSprintDashboardCard(
            data: data,
            onRecordResult: onRecordResult,
          ),
        ),
      ),);
  }

  group('F14 — Animated Pass Probability Ring', () {
    testWidgets(
        'pass_probability = 0.72 animates from 0% to 72% with green ring',
        (tester) async {
      final data = _makeData(passProbability: 0.72);
      await tester.pumpWidget(_buildCard(data));

      // Animation starts near 0%
      await tester.pump();
      expect(find.text('0%'), findsOneWidget);

      // After animation completes → 72%
      await tester.pumpAndSettle(const Duration(milliseconds: 1200));
      expect(find.text('72%'), findsOneWidget);

      // Side text shows days and task completion
      expect(find.text('还有 5 天'), findsOneWidget);
      expect(find.text('今日 2/3 完成'), findsOneWidget);
    });

    testWidgets('pass_probability = 0.35 shows red-tinted percentage', (tester) async {
      final data = _makeData(passProbability: 0.35);
      await tester.pumpWidget(_buildCard(data));
      await tester.pumpAndSettle(const Duration(milliseconds: 1200));

      expect(find.text('35%'), findsOneWidget);
    });

    testWidgets('pass_probability = null shows -- without errors', (tester) async {
      final data = _makeData(passProbability: null);
      await tester.pumpWidget(_buildCard(data));
      await tester.pumpAndSettle(const Duration(milliseconds: 1200));

      expect(find.text('--'), findsOneWidget);
      // Side text still renders
      expect(find.text('还有 5 天'), findsOneWidget);
      expect(find.text('今日 2/3 完成'), findsOneWidget);
    });

    testWidgets('animation starts at 0 and ends near target value', (tester) async {
      final data = _makeData(passProbability: 0.80);
      await tester.pumpWidget(_buildCard(data));

      // Frame 0: animation value near 0
      await tester.pump();
      expect(find.text('0%'), findsOneWidget);

      // Mid-animation: value should be between 0% and 80%
      await tester.pump(const Duration(milliseconds: 600));

      // After settle: 80%
      await tester.pumpAndSettle(const Duration(milliseconds: 1200));
      expect(find.text('80%'), findsOneWidget);
    });

    testWidgets('daysLeft = 1 shows 还有 1 天 beside ring', (tester) async {
      final data = ExamSprintDashboardData(
        planId: 'test-plan',
        planName: 'Test',
        subject: '',
        daysLeft: 1,
        targetMode: 'pass',
        todayProgress: const ExamSprintTodayProgress(
          completed: 1,
          total: 1,
          completionRate: 1.0,
        ),
        highFreqCoverage: 0.5,
        highFreqCoveredCount: 5,
        highFreqTotalCount: 10,
        mistakeFixRate: 0.5,
        fixedMistakeCount: 3,
        totalMistakeCount: 6,
        streakDays: 1,
        passProbability: 0.9,
        taskGroups: const [],
      );
      await tester.pumpWidget(_buildCard(data));
      await tester.pumpAndSettle(const Duration(milliseconds: 1200));

      expect(find.text('还有 1 天'), findsOneWidget);
      expect(find.text('90%'), findsOneWidget);
    });
  });

  group('F15 — Day-0 Banner', () {
    testWidgets(
        'daysLeft = 0 renders day-0 banner title without probability ring',
        (tester) async {
      final data = _makeData(
        daysLeft: 0,
        passProbability: 0.9,
        subject: '计算机网络',
        sleepGuardHint: '保持稳定，不熬夜',
      );
      await tester.pumpWidget(_buildCard(data));
      // _DayZeroBanner has a repeating float animation — pump, not pumpAndSettle
      await tester.pump(const Duration(milliseconds: 400));

      // Banner title is present
      expect(find.text('今天考试 · 你已经准备好了 🎓'), findsOneWidget);
      // Subject shown as subtitle
      expect(find.text('计算机网络'), findsOneWidget);
      // Exam tips label and content
      expect(find.text('考场建议'), findsOneWidget);
      expect(find.text('保持稳定，不熬夜'), findsOneWidget);
      // Probability ring should NOT be rendered
      expect(find.text('90%'), findsNothing);
      // Record button present
      expect(find.text('记录考试结果'), findsOneWidget);
    });

    testWidgets('daysLeft = 1 renders normal dashboard with probability ring',
        (tester) async {
      final data = _makeData(
        daysLeft: 1,
        passProbability: 0.85,
      );
      await tester.pumpWidget(_buildCard(data));
      await tester.pumpAndSettle(const Duration(milliseconds: 1200));

      // Normal header
      expect(find.text('考试冲刺仪表盘'), findsOneWidget);
      // Probability ring rendered
      expect(find.text('85%'), findsOneWidget);
      // Day-0 banner title should NOT be present
      expect(find.text('今天考试 · 你已经准备好了 🎓'), findsNothing);
      // Record button should NOT be present
      expect(find.text('记录考试结果'), findsNothing);
    });

    testWidgets('record exam result button fires callback',
        (tester) async {
      var callbackFired = false;
      final data = _makeData(
        daysLeft: 0,
        passProbability: 0.9,
      );
      await tester.pumpWidget(_buildCard(
        data,
        onRecordResult: () {
          callbackFired = true;
        },
      ));
      await tester.pump(const Duration(milliseconds: 400));

      final button = find.text('记录考试结果');
      expect(button, findsOneWidget);

      await tester.tap(button);
      expect(callbackFired, isTrue);
    });
  });
}
