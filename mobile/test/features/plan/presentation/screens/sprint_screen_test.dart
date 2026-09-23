// SPEC-A 冲刺仪表盘 #1+#3+#5 验收测试。
// 覆盖：①倒计时口径归一（跨屏同源同值 + 客户端零 DateTime.now() 推算）
// ②三态补齐（错误态三件套 / 任务空态 EmptyState / 骨架贴真实布局）
// ③进度位诚实编码（横幅无渐变、进度条仅中性/success 语义槽派生色）。
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/exam_sprint_dashboard_card.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/plan/presentation/screens/sprint_screen.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  ExamSprintDashboardData examPayload({int daysLeft = 5}) =>
      ExamSprintDashboardData(
        planId: 'plan-sprint-1',
        planName: '操作系统期末冲刺',
        subject: 'Operating Systems',
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
        taskGroups: const [],
      );

  Widget host({
    required Widget child,
    PlanListState? planListState,
    Object Function()? planDetail,
    ExamSprintDashboardData? examData,
    AchievementNotifier Function()? achievement,
    Key? scopeKey,
  }) {
    final effectivePlanState = planListState ?? PlanListState();
    return ProviderScope(
      // scopeKey：同一 tester 上二次 pumpWidget 换 examData 档位时必须换 key，
      // 否则 ProviderScope 元素原位复用、overrides 不重建（Riverpod 已知行为）。
      key: scopeKey,
      overrides: [
        planListProvider.overrideWith(
          (ref) => _StaticPlanNotifier(effectivePlanState),
        ),
        if (planDetail != null)
          planDetailProvider('plan-sprint-1').overrideWith((ref) {
            final result = planDetail();
            if (result is PlanModel) return Future<PlanModel>.value(result);
            return Future.error(result);
          }),
        if (examData != null)
          examSprintDashboardProvider
              .overrideWith((ref) => Future.value(examData)),
        if (achievement != null)
          achievementProvider.overrideWith((ref) => achievement()),
      ],
      child: testMaterialApp(home: Scaffold(body: child)),
    );
  }

  testWidgets('#1 跨屏同源同值：sprint 屏倒计时读 exam payload 服务端值', (tester) async {
    await tester.pumpWidget(
      host(
        planListState: PlanListState(activePlans: [PlanModelStub.plan]),
        planDetail: () => PlanModelStub.plan,
        examData: examPayload(),
        achievement: _StaticAchievementNotifier.new,
        child: const SprintScreen(),
      ),
    );
    // 用固定 pump 而非 pumpAndSettle：骨架/刷新件可能存在循环动画。
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(milliseconds: 300));

    // 服务端真值 5 天（与 exam 卡同源），而非 targetDate 推算的 ~160 天。
    expect(find.text('剩余 5 天'), findsOneWidget);
    expect(find.textContaining('160'), findsNothing);
    expect(find.text('冲刺已结束'), findsNothing);
    // 口径标注就地可见。
    expect(find.text('口径：服务端按冲刺任务完成比结算'), findsOneWidget);
  });

  testWidgets('#1 exam 卡同一 payload 显示同一剩余天数（跨屏同值）', (tester) async {
    final data = examPayload();
    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body:
              SingleChildScrollView(child: ExamSprintDashboardCard(data: data)),
        ),
      ),
    );
    await tester.pumpAndSettle(const Duration(milliseconds: 1200));

    expect(find.text('还有 5 天'), findsOneWidget);
    expect(find.text('距考试还有 5 天'), findsOneWidget);
  });

  testWidgets('#3 错误态三件套：人话标题+影响一句+可重试（N4）', (tester) async {
    var buildCount = 0;
    await tester.pumpWidget(
      host(
        planListState: PlanListState(activePlans: [PlanModelStub.plan]),
        planDetail: () {
          buildCount++;
          return StateError('boom');
        },
        examData: examPayload(),
        achievement: _StaticAchievementNotifier.new,
        child: const SprintScreen(),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.byType(CustomErrorWidget), findsOneWidget);
    expect(find.text('冲刺面板加载失败'), findsOneWidget);
    expect(find.text('任务和进度暂时看不到；你的数据没有丢，点重试即可恢复。'), findsOneWidget);
    // 错误对象不裸奔：StateError 文案不出现。
    expect(find.textContaining('boom'), findsNothing);
    // 重试钮可发现且真的重试。
    expect(find.text('重试'), findsOneWidget);
    await tester.tap(find.text('重试'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(buildCount, 2);
  });

  testWidgets('#3 任务空态：为何空 + 单一 CTA（EmptyState）', (tester) async {
    await tester.pumpWidget(
      host(
        planListState: PlanListState(activePlans: [PlanModelStub.plan]),
        planDetail: () => PlanModelStub.plan, // tasks: []
        examData: examPayload(),
        achievement: _StaticAchievementNotifier.new,
        child: const SprintScreen(),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byType(EmptyState), findsOneWidget);
    expect(find.text('这个冲刺还没排任务'), findsOneWidget);
    expect(
      find.textContaining('冲刺的任务会按天排在这里'),
      findsOneWidget,
    );
    expect(find.text('去排任务'), findsOneWidget);
    // 旧裸文本空态清零。
    expect(find.text('这个冲刺暂无任务。'), findsNothing);
  });

  testWidgets('#3 骨架贴真实布局：无 80×80 方块，含 header/成就/任务三段', (tester) async {
    await tester.pumpWidget(
      host(
        planListState: PlanListState(isLoading: true),
        child: const SprintScreen(),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    final skeletons =
        tester.widgetList<SparkleSkeleton>(find.byType(SparkleSkeleton));
    // 旧骨架的形异件：80×80 方块必须清零。
    expect(
      skeletons.where((s) => (s.width ?? 0) == 80 && s.height == 80),
      isEmpty,
    );
    // 新骨架贴真实布局的三个特征件：
    // header 全宽复盘钮位、40×40 成就圆环位、全宽任务卡位。
    expect(
      skeletons.any((s) => s.width == double.infinity && s.height == 44),
      isTrue,
    );
    expect(
      skeletons.any((s) => (s.width ?? 0) == 40 && s.height == 40),
      isTrue,
    );
    expect(
      skeletons.where((s) => s.width == double.infinity && s.height == 14),
      isNotEmpty,
    );
  });

  testWidgets('#5 进度位诚实编码：横幅无渐变，进度条仅中性/success 语义色', (tester) async {
    await tester.pumpWidget(
      host(
        planListState: PlanListState(activePlans: [PlanModelStub.plan]),
        planDetail: () => PlanModelStub.plan,
        examData: examPayload(),
        achievement: () => _StaticAchievementNotifier(
          closeToUnlock: [_AchievementStubs.epic82],
          achievements: [_AchievementStubs.epic82],
        ),
        child: const SprintScreen(),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(milliseconds: 300));

    // ① 渐变横幅降级为单色阶 + 描边：banner 容器 gradient == null。
    final banner = tester.widget<Container>(
      find.byKey(const ValueKey('sprint-close-unlock-banner')),
    );
    final decoration = banner.decoration! as BoxDecoration;
    expect(decoration.gradient, isNull);
    expect(decoration.color, isNotNull);
    expect(decoration.border, isNotNull);

    // ② 进度位色值断言：显式 valueColor 的进度条（成就进度位）只能是
    // 中性层（neutral500）或语义槽（success），绝无稀有度色；
    // header 总进度条走主题默认色，同样不得是稀有度色。
    final progressBars = tester.widgetList<LinearProgressIndicator>(
      find.byType(LinearProgressIndicator),
    );
    expect(progressBars, isNotEmpty);
    final explicitBars =
        progressBars.where((b) => b.valueColor != null).toList();
    expect(explicitBars, isNotEmpty, reason: '成就进度位必须显式编码色值');
    final rarityColors = [DS.rarityRare, DS.rarityEpic, DS.rarityLegendary];
    for (final bar in progressBars) {
      final color = bar.valueColor?.value;
      if (color != null) {
        expect(
          color,
          anyOf(DS.neutral500, DS.success),
          reason: '进度位出现了非中性/语义槽的颜色：$color',
        );
      }
      expect(
        color,
        isNot(anyOf(rarityColors[0], rarityColors[1], rarityColors[2])),
        reason: '进度位不得出现稀有度色',
      );
    }
    // 稀有度色只允许留在图标环身份位：进度条 hero 区不得出现 epic 紫。
    expect(DS.rarityEpic, isNot(anyOf(DS.neutral500, DS.success)));
  });

  // ─────────── SPEC-FIX（复审闭环 · R4=N5 三档 urgency 收敛到 sprint pill） ───────────

  group('SPEC-FIX R4 — 倒计时 pill 与 exam 卡同款 N5 三档色阶', () {
    /// 倒计时 pill（带 timelapse 图标的 SemanticPill）的 tone 与其文字色。
    ({PillTone tone, Color textColor}) countdownPill(WidgetTester tester) {
      final pill = tester.widget<SemanticPill>(
        find.byWidgetPredicate(
          (w) => w is SemanticPill && w.icon == Icons.timelapse,
        ),
      );
      final text = tester.widget<Text>(
        find.descendant(of: find.byWidget(pill), matching: find.byType(Text)),
      );
      return (tone: pill.tone, textColor: text.style!.color!);
    }

    Future<void> pumpScreenAt(WidgetTester tester, int daysLeft) async {
      await tester.pumpWidget(
        host(
          planListState: PlanListState(activePlans: [PlanModelStub.plan]),
          planDetail: () => PlanModelStub.plan,
          examData: examPayload(daysLeft: daysLeft),
          achievement: _StaticAchievementNotifier.new,
          scopeKey: UniqueKey(),
          child: const SprintScreen(),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));
    }

    testWidgets('中性档（daysLeft=10 > 7）：brand tone，文字色 = brandPrimary',
        (tester) async {
      await pumpScreenAt(tester, 10);
      final pill = countdownPill(tester);
      expect(pill.tone, PillTone.brand);
      expect(pill.textColor, DS.brandPrimary);
    });

    testWidgets('档位边界：daysLeft=7 warning / daysLeft=8 brand（N5 口径 >7 中性）',
        (tester) async {
      await pumpScreenAt(tester, 7);
      expect(countdownPill(tester).tone, PillTone.warning);
      expect(countdownPill(tester).textColor, DS.warning);

      await pumpScreenAt(tester, 8);
      expect(countdownPill(tester).tone, PillTone.brand);
      expect(countdownPill(tester).textColor, DS.brandPrimary);
    });

    testWidgets('warning 档（daysLeft=5）：文字色 = warning 槽（与 home exam 卡同橙）',
        (tester) async {
      await pumpScreenAt(tester, 5);
      expect(find.text('剩余 5 天'), findsOneWidget);
      final pill = countdownPill(tester);
      expect(pill.tone, PillTone.warning);
      expect(pill.textColor, DS.warning);
    });

    testWidgets('danger 档（daysLeft=1 / 考日 0）：文字色 = error 槽（「不可挽回节点临近」）',
        (tester) async {
      await pumpScreenAt(tester, 1);
      expect(countdownPill(tester).tone, PillTone.danger);
      expect(countdownPill(tester).textColor, DS.error);

      await pumpScreenAt(tester, 0);
      expect(find.text('今天考试'), findsOneWidget);
      expect(countdownPill(tester).tone, PillTone.danger);
      expect(countdownPill(tester).textColor, DS.error);
    });
  });
}

// ---------- 测试桩 ----------

/// 供闭包引用的固定 plan（testWidgets 闭包捕获 final 即可）。
class PlanModelStub {
  static final PlanModel plan = PlanModel(
    id: 'plan-sprint-1',
    userId: 'user-1',
    name: '操作系统期末冲刺',
    subject: 'Operating Systems',
    type: PlanType.sprint,
    dailyAvailableMinutes: 120,
    masteryLevel: 0.45,
    progress: 0.35,
    isActive: true,
    tasks: const [],
    targetDate: DateTime(2027, 3, 2),
    createdAt: DateTime(2026, 4, 25),
    updatedAt: DateTime(2026, 4, 25),
  );
}

class _AchievementStubs {
  static AchievementWithProgress get epic82 => AchievementWithProgress(
        achievement: AchievementModel(
          id: 'ach-1',
          name: '七天冲刺王',
          type: AchievementType.sprint,
          rarity: AchievementRarity.epic,
          createdAt: DateTime(2026, 2, 3),
          updatedAt: DateTime(2026, 2, 3),
        ),
        isUnlocked: false,
        progressPercentage: 82,
      );
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StaticPlanNotifier extends PlanNotifier {
  _StaticPlanNotifier(PlanListState initialState)
      : super(_UnusedPlanRepository(), _UnusedRef()) {
    state = initialState;
  }

  @override
  Future<void> loadPlans({PlanType? type}) async {}

  @override
  Future<void> loadActivePlans() async {}
}

class _UnusedRef implements Ref {
  // 与 dashboard_test_harness 同款宽假 Ref：read 一律给占位对象，
  // 桩 notifier 的生命周期内不会真正消费该值。
  @override
  T read<T>(ProviderListenable<T> provider) => InterceptorsWrapper() as T;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedPlanRepository extends PlanRepository {
  _UnusedPlanRepository() : super(_NoopApiClient());
}

class _NoopAchievementRepository extends AchievementRepository {
  _NoopAchievementRepository() : super(_NoopApiClient());
}

class _StaticAchievementNotifier extends AchievementNotifier {
  _StaticAchievementNotifier({
    List<AchievementWithProgress> closeToUnlock = const [],
    List<AchievementWithProgress> achievements = const [],
  })  : _closeToUnlock = closeToUnlock,
        super(_NoopAchievementRepository(), _UnusedRef()) {
    state = AchievementState.loading().copyWith(
      achievements: achievements,
      isLoading: false,
    );
  }

  final List<AchievementWithProgress> _closeToUnlock;

  @override
  Future<void> loadInitialData() async {}

  @override
  Future<List<AchievementWithProgress>> getCloseToUnlockAchievements({
    String? category,
    double threshold = 0.8,
  }) async =>
      _closeToUnlock;
}
