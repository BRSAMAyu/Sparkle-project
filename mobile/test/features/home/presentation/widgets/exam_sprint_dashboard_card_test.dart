import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';
import 'package:sparkle/core/services/performance_service.dart';
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
      // S-G9 清偿后：进度文案只走 _HeadlineBlock 主位（examTodayProgress），
      // 弧旁副本（examTodayCompleted「今日 2/3 完成」）清零。
      expect(find.text('今天已完成 2/3 项任务'), findsOneWidget);
      expect(find.text('今日 2/3 完成'), findsNothing);
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
      expect(find.text('今天已完成 2/3 项任务'), findsOneWidget);
      expect(find.text('今日 2/3 完成'), findsNothing);
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
      // SPEC-B #8 后横幅为单次入场（320ms）——pump 越过入场窗口即可
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

  // ───────────────────────── SPEC-B（北极星全旅程 · A 纵队） ─────────────────────────
  // 验收依据：v3-output/A-SPEC-V1_1/REPORT.md §4 N3/N5/N6 + §5 改造 #2/#8/#9。

  group('SPEC-B #9 — N5 urgency 三档色阶（>7d 中性【勘误后】 / ≤7d warning / ≤1d error）', () {
    final standard = SparkleColors.light();

    Future<void> pumpCardAt(WidgetTester tester, int daysLeft) async {
      await tester
          .pumpWidget(_buildCard(_makeData(daysLeft: daysLeft, passProbability: 0.72)));
      await tester.pumpAndSettle();
    }

    Color headerIconColor(WidgetTester tester) => tester
        .widget<Icon>(find.byIcon(Icons.rocket_launch_rounded))
        .color!;

    Color countdownColor(WidgetTester tester, String text) =>
        tester.widget<Text>(find.text(text)).style!.color!;

    testWidgets('中性档（daysLeft=10 ≥ 8）：header 与倒计时数字均为 brandPrimary',
        (tester) async {
      await pumpCardAt(tester, 10);
      expect(find.text('距考试还有 10 天'), findsOneWidget);
      // 翻转收敛两处之一：header（图标 + 模式 pill 同源）。
      expect(headerIconColor(tester), standard.brandPrimary);
      // 翻转收敛两处之二：倒计时数字。
      expect(
        countdownColor(tester, '距考试还有 10 天'),
        standard.brandPrimary,
      );
    });

    testWidgets('档位边界：daysLeft=8 中性 / daysLeft=7 与 2 warning',
        (tester) async {
      await pumpCardAt(tester, 8);
      expect(
        countdownColor(tester, '距考试还有 8 天'),
        standard.brandPrimary,
        reason: '≥7d（即 ≥8 天）应为中性档',
      );

      await pumpCardAt(tester, 7);
      expect(
        countdownColor(tester, '距考试还有 7 天'),
        standard.semanticWarning,
        reason: '≤7d 应进入 warning 档',
      );

      await pumpCardAt(tester, 2);
      expect(countdownColor(tester, '距考试还有 2 天'), standard.semanticWarning);
    });

    testWidgets('warning 档（daysLeft=5）：色值命中 warning 槽，且全树无 error 槽',
        (tester) async {
      await pumpCardAt(tester, 5);
      expect(find.text('距考试还有 5 天'), findsOneWidget);
      expect(headerIconColor(tester), standard.semanticWarning);
      expect(countdownColor(tester, '距考试还有 5 天'), standard.semanticWarning);

      // 验收「error 槽在 ≤7d 档不出现」：扫全树 Text/Icon 前景色。
      final errorColor = standard.semanticError;
      final textColors = tester
          .widgetList<Text>(find.byType(Text))
          .map((t) => t.style?.color)
          .whereType<Color>()
          .toList();
      expect(textColors, isNotEmpty);
      expect(textColors, everyElement(isNot(errorColor)));
      final iconColors = tester
          .widgetList<Icon>(find.byType(Icon))
          .map((i) => i.color)
          .whereType<Color>()
          .toList();
      expect(iconColors, isNotEmpty);
      expect(iconColors, everyElement(isNot(errorColor)));
    });

    testWidgets('error 档（daysLeft=1 ≤ 1d）：header 与倒计时数字均 error 槽',
        (tester) async {
      await pumpCardAt(tester, 1);
      expect(find.text('距考试还有 1 天'), findsOneWidget);
      expect(headerIconColor(tester), standard.semanticError);
      expect(countdownColor(tester, '距考试还有 1 天'), standard.semanticError);
    });
  });

  group('SPEC-B #2 — N6 预测数准入四件（口径行 / 低档文案 / CB-safe 色源 / 320ms）',
      () {
    testWidgets('② 口径一行就地可见：「按当前进度估算」', (tester) async {
      await tester.pumpWidget(_buildCard(_makeData(passProbability: 0.72)));
      await tester.pumpAndSettle();
      expect(find.text('按当前进度估算'), findsOneWidget);
    });

    testWidgets('③ 低档（<0.4）动作文案触发；≥0.4 不出现', (tester) async {
      await tester.pumpWidget(_buildCard(_makeData(passProbability: 0.35)));
      await tester.pumpAndSettle();
      expect(find.text('还来得及，先攻高频考点'), findsOneWidget);

      await tester.pumpWidget(_buildCard(_makeData(passProbability: 0.72)));
      await tester.pumpAndSettle();
      expect(find.text('还来得及，先攻高频考点'), findsNothing);
    });

    testWidgets('④ 入场动画时长 ∈ 正典集：320ms 到点完成（排掉 1200ms offLadder 档）',
        (tester) async {
      await tester.pumpWidget(_buildCard(_makeData(passProbability: 0.72)));
      await tester.pump(); // 首帧：动画起跑，弧值 0%
      expect(find.text('0%'), findsOneWidget);

      // 半程（160ms）：easeOutCubic(0.5)≈0.875 → 显示 ≈63%，证明动画在途非瞬时。
      await tester.pump(const Duration(milliseconds: 160));
      expect(find.text('72%'), findsNothing);

      // 320ms 正典档到点：必须已到位（旧 1200ms 档在此刻远未完成）。
      await tester.pump(const Duration(milliseconds: 160));
      expect(find.text('72%'), findsOneWidget);
    });

    testWidgets('④ CB 变体：编码色经 theme 注入 Okabe-Ito CB-safe 槽（无红绿依赖）',
        (tester) async {
      // CB-friendly 主题（非 ThemeManager 单例路径）注入 ThemeData，
      // 断言弧色取自主题变体而非静态常量。
      final cbColors = SparkleColors.light(colorBlindFriendly: true);
      final standardColors = SparkleColors.light();
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.light().copyWith(
            extensions: [SparkleThemeExtension.light(colors: cbColors)],
          ),
          locale: const Locale('zh'),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(
            body: SingleChildScrollView(
              child: ExamSprintDashboardCard(
                data: _makeData(passProbability: 0.35),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final ringColor = _passProbabilityRingColor(tester);
      // 0.35 < 0.4 → error 槽：CB-safe 变体为 Okabe-Ito 朱红（非普通红），
      // 与标准亮色主题的 error 值不同 ⇒ 色源确实走 theme 注入。
      expect(ringColor, const Color(0xFFD55E00));
      expect(ringColor, isNot(standardColors.semanticError));

      // success 槽（0.72）在 CB 变体下为蓝绿（bluish green），与朱红形成
      // 蓝/红双通道对比——色盲用户仍可区分（无红绿单通道依赖）。
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.light().copyWith(
            extensions: [SparkleThemeExtension.light(colors: cbColors)],
          ),
          locale: const Locale('zh'),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(
            body: SingleChildScrollView(
              child: ExamSprintDashboardCard(
                data: _makeData(passProbability: 0.72),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(
        _passProbabilityRingColor(tester),
        const Color(0xFF009E73),
      );
    });
  });

  group('SPEC-B #8 — N3 DayZero 单次入场 + 静止定帧（禁循环浮动）', () {
    /// 横幅入场偏移（Transform.translate 的 y）；无偏移（全恒等矩阵）视为静止位 0。
    double bannerTranslateY(WidgetTester tester) {
      final transforms = tester
          .widgetList<Transform>(find.byType(Transform))
          .where((t) => !t.transform.isIdentity())
          .toList();
      if (transforms.isEmpty) return 0.0;
      return transforms.first.transform.getTranslation().y;
    }

    ExamSprintDashboardData dayZeroData() => _makeData(
          daysLeft: 0,
          passProbability: 0.9,
          subject: '计算机网络',
        );

    /// 测试宿主默认解析为 medium 档（60Hz + dpr 3.0 → staticFrame），
    /// 强制 high 档才能走进 animated 分支验证入场行为。
    void forceHighTier() {
      PerformanceService.instance.currentTier.value = PerformanceTier.high;
      addTearDown(() =>
          PerformanceService.instance.currentTier.value =
              defaultPerformanceTier());
    }

    testWidgets('单次入场：320ms 内到静止位，之后持续观察无循环浮动', (tester) async {
      forceHighTier();
      await tester.pumpWidget(_buildCard(dayZeroData()));
      await tester.pump(); // 首帧：入场起跑（自下方 6px 浮入）
      expect(find.text('今天考试 · 你已经准备好了 🎓'), findsOneWidget);
      expect(bannerTranslateY(tester), greaterThan(0));

      // 正典档 320ms 到点：静止位（offset 0）。
      await tester.pump(const Duration(milliseconds: 320));
      expect(bannerTranslateY(tester), 0.0);

      // 持续观察 2.5s（覆盖旧 3000ms repeat 的一个完整周期）：偏移恒 0。
      await tester.pump(const Duration(milliseconds: 1000));
      expect(bannerTranslateY(tester), 0.0);
      await tester.pump(const Duration(milliseconds: 1500));
      expect(bannerTranslateY(tester), 0.0);
    });

    testWidgets('reduce-motion：首帧即钉在静止位（无入场播放）', (tester) async {
      forceHighTier(); // 排除 tier 降档干扰：此路径专验 reduce-motion 门控
      await tester.pumpWidget(
        testMaterialApp(
          home: MediaQuery(
            data: const MediaQueryData(disableAnimations: true),
            child: Scaffold(
              body: SingleChildScrollView(
                child: ExamSprintDashboardCard(data: _makeData(daysLeft: 0)),
              ),
            ),
          ),
        ),
      );
      await tester.pump();
      expect(find.text('今天考试 · 你已经准备好了 🎓'), findsOneWidget);
      expect(bannerTranslateY(tester), 0.0);
      await tester.pump(const Duration(milliseconds: 500));
      expect(bannerTranslateY(tester), 0.0);
    });
  });

  // ───────────────── SPEC-FIX（复审闭环 · R5=S-G9/日期拼接清偿） ─────────────────

  group('SPEC-FIX R5 — S-G9 同卡二出去重 + 日期走 date_formatting 唯一入口', () {
    testWidgets('S-G9：今日进度文案只保留 _HeadlineBlock 主位一种措辞', (tester) async {
      await tester.pumpWidget(_buildCard(_makeData(passProbability: 0.72)));
      await tester.pumpAndSettle();

      // 主位（examTodayProgress）恰 1 处；弧旁副本（examTodayCompleted）
      // 与其中文措辞均不出现——同一数字两种措辞并排清零。
      expect(find.text('今天已完成 2/3 项任务'), findsOneWidget);
      expect(find.textContaining('今日 2/3'), findsNothing);
      expect(find.textContaining('2/3 完成'), findsNothing);
    });

    testWidgets('S-G10：任务组日期经 formatSparkleDateOnly 输出（zh：9月20日）',
        (tester) async {
      final data = ExamSprintDashboardData(
        planId: 'test-plan',
        planName: 'Test Sprint',
        subject: 'Math',
        daysLeft: 5,
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
        passProbability: 0.72,
        taskGroups: [
          // DateTime 非 const 构造，组实例不能标 const。
          // today 组（主位渲染）+ 未来组（折叠区渲染）——todayGroup getter
          // 在无 isToday 组时会 fallback 到 first，单组会被渲染两次。
          const ExamSprintTaskGroup(
            dayIndex: 1,
            isToday: true,
            completedCount: 2,
            totalCount: 3,
            tasks: [],
          ),
          ExamSprintTaskGroup(
            dayIndex: 2,
            isToday: false,
            completedCount: 0,
            totalCount: 4,
            tasks: const [],
            date: DateTime(2026, 9, 20),
          ),
        ],
      );
      await tester.pumpWidget(_buildCard(data));
      await tester.pumpAndSettle();

      // 未来任务组默认折叠：先展开（_TaskSectionHeader 的 CTA），日期随组卡可见。
      await tester.tap(find.text('展开后续 1 天'));
      await tester.pumpAndSettle();

      // 旧手工拼接「9/20」清零；date_formatting 令牌输出（zh「9月20日」）在。
      expect(find.text('9/20'), findsNothing);
      expect(find.text('9月20日'), findsOneWidget);
    });
  });
}

/// 提取通过率弧 CustomPaint 的画家色值（画家为私有类，经 runtimeType 定位）。
Color _passProbabilityRingColor(WidgetTester tester) {
  final customPaint = tester.widget<CustomPaint>(
    find.byWidgetPredicate(
      (w) =>
          w is CustomPaint &&
          w.painter != null &&
          w.painter!.runtimeType.toString() == '_PassProbabilityRingPainter',
    ),
  );
  return (customPaint.painter! as dynamic).color as Color;
}
