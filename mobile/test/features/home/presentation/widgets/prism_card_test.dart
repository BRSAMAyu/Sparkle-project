// SPEC-FIX（复审闭环 · R4=N3 守卫扩维缺位清偿）：prism_card 2000ms 无门控
// repeat(reverse) 常驻呼吸退役验收——单次入场（正典集 320ms）+ 静止定帧 +
// DecorationMode 门控（SPEC-B #8 DayZero / SPEC-C #6 呼吸层同款范式）。
// 旧实现（2s repeat(reverse)）在本文件所有时间窗断言上必失败：其 ticker 永不
// 终止、辉光 alpha 永在 0.05–0.15 间摆动。
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/prism_card.dart';
import '../../../../shared/i18n_test_helper.dart';

/// 采样 prism 折射辉光（RadialGradient 装饰的 Container）当前首色 alpha。
double _sampleGlowAlpha(WidgetTester tester) {
  final containers = tester.widgetList<Container>(find.byType(Container));
  for (final c in containers) {
    final decoration = c.decoration;
    if (decoration is BoxDecoration && decoration.gradient is RadialGradient) {
      return (decoration.gradient! as RadialGradient).colors.first.a;
    }
  }
  fail('prism 辉光容器未找到');
}

class _FakeApiClient extends Fake implements ApiClient {}

class _SilentDashboardRepository extends DashboardRepository {
  _SilentDashboardRepository() : super(_FakeApiClient());
}

/// 恒定初始态的 dashboard 桩：不拉数据，cognitive/weather 全默认。
class _StaticPrismDashboardNotifier extends DashboardNotifier {
  _StaticPrismDashboardNotifier() : super(_SilentDashboardRepository()) {
    state = DashboardState.loading();
  }

  @override
  Future<void> fetchData() async {}

  @override
  Future<void> refresh() async {}
}

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  /// 测试宿主默认解析为 medium 档（60Hz + dpr 3.0 → staticFrame），
  /// 强制 high 档才能走进 animated 分支验证入场行为。
  void forceHighTier() {
    PerformanceService.instance.currentTier.value = PerformanceTier.high;
    addTearDown(() =>
        PerformanceService.instance.currentTier.value =
            defaultPerformanceTier(),);
  }

  Widget host({bool disableAnimations = false,}) => ProviderScope(
        overrides: [
          dashboardProvider.overrideWith(
            (ref) => _StaticPrismDashboardNotifier(),
          ),
        ],
        child: MediaQuery(
          data: MediaQueryData(disableAnimations: disableAnimations),
          child: testMaterialApp(home: const Scaffold(body: PrismCard())),
        ),
      );

  group('SPEC-FIX R4 — prism 辉光单次入场 + 静止定帧（N3 呼吸禁令）', () {
    testWidgets('单次入场：320ms 到静止位（alpha 0.15），之后 2s 观察窗恒定',
        (tester) async {
      forceHighTier();
      await tester.pumpWidget(host());
      await tester.pump(); // 首帧：入场起跑（0.1→0.3 在途，alpha < 0.15）
      final alphaDuringEntrance = _sampleGlowAlpha(tester);
      expect(
        alphaDuringEntrance,
        lessThan(0.15),
        reason: '入场在途应低于静止位（旧 repeat 实现首帧同值，此处只做在途佐证）',
      );

      // 正典档 320ms 到点：静止位（Tween 终值 0.3 × 0.5 = 0.15）。
      await tester.pump(const Duration(milliseconds: 320));
      expect(_sampleGlowAlpha(tester), moreOrLessEquals(0.15, epsilon: 1e-6));

      // 持续观察 2.5s（覆盖旧 2000ms repeat 的一个完整往返周期）：
      // alpha 恒 0.15——旧实现此刻必在振荡相位上（2820ms → ~0.109）。
      await tester.pump(const Duration(milliseconds: 1000));
      expect(_sampleGlowAlpha(tester), moreOrLessEquals(0.15, epsilon: 1e-6));
      await tester.pump(const Duration(milliseconds: 1500));
      expect(_sampleGlowAlpha(tester), moreOrLessEquals(0.15, epsilon: 1e-6));

      // ticker 终止性：入场完成后 prism 内无活跃 frame 源（旧 repeat 永不归零）。
      expect(tester.binding.transientCallbackCount, 0);
    });

    testWidgets('staticFrame 档（medium tier）：首帧即钉静止位，无入场播放',
        (tester) async {
      // 不 force tier：测试宿主默认 medium → resolveDecorationMode = staticFrame。
      await tester.pumpWidget(host());
      await tester.pump();
      expect(_sampleGlowAlpha(tester), moreOrLessEquals(0.15, epsilon: 1e-6));
      await tester.pump(const Duration(milliseconds: 500));
      expect(_sampleGlowAlpha(tester), moreOrLessEquals(0.15, epsilon: 1e-6));
      expect(tester.binding.transientCallbackCount, 0);
    });

    testWidgets('reduce-motion（high tier + disableAnimations）：首帧即钉静止位',
        (tester) async {
      forceHighTier(); // 排除 tier 降档干扰：此路径专验 reduce-motion 门控
      await tester.pumpWidget(host(disableAnimations: true));
      await tester.pump();
      expect(_sampleGlowAlpha(tester), moreOrLessEquals(0.15, epsilon: 1e-6));
      await tester.pump(const Duration(milliseconds: 500));
      expect(_sampleGlowAlpha(tester), moreOrLessEquals(0.15, epsilon: 1e-6));
      expect(tester.binding.transientCallbackCount, 0);
    });
  });
}
