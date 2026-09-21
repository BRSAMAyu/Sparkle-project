import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/effect_layer.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/particle_layer.dart';
import 'package:sparkle/features/home/presentation/widgets/weather_header.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';
import '../../../../shared/i18n_test_helper.dart';

/// U-01 Step 2：home 装饰 PerformanceTier 门控扩面验证。
///
/// 断言核心口径：低档（low）装饰挂载数下降 / 静态化（无常驻逐帧动画），
/// 高档（ultra）保持既有装饰动画。
void main() {
  setUpI18nForTesting();
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    PerformanceService.instance.currentTier.value = PerformanceTier.ultra;
    PerformanceService.instance.motionIntensityLevel.value =
        MotionIntensityLevel.high;
  });

  tearDown(() {
    PerformanceService.instance.currentTier.value = defaultPerformanceTier();
  });

  int countPainters(WidgetTester tester, String runtimeTypeName) =>
      tester.widgetList(
        find.byWidgetPredicate(
          (w) =>
              w is CustomPaint &&
              (w.painter?.runtimeType.toString() ?? '').contains(
                runtimeTypeName,
              ),
        ),
      ).length;

  VisualElementModel particleElement() => VisualElementModel(
        id: 'p-test',
        name: '测试粒子',
        elementType: VisualElementType.particle,
        rarity: VisualElementRarity.common,
        unlockSource: VisualElementUnlockSource.system,
        isDefault: true,
        sortOrder: 0,
        config: {
          'count': 50,
          'shape': 'circle',
          'colors': ['#8BE9FD'],
          'twinkle': true,
        },
      );

  group('ParticleLayer — 门控扩面（此前无任何 tier 门控）', () {
    testWidgets('ultra 档：粒子画笔挂载 + 逐帧动画', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.ultra;
      final controller =
          AnimationController(vsync: tester, duration: const Duration(seconds: 1));
      unawaited(controller.repeat());

      await tester.pumpWidget(
        Directionality(
          textDirection: TextDirection.ltr,
          child: ParticleLayer(
            element: particleElement(),
            particleAnimation: controller,
            mainAnimation: controller,
          ),
        ),
      );
      await tester.pump();

      expect(countPainters(tester, '_ParticlePainter'), 1);
      expect(find.byType(AnimatedBuilder), findsOneWidget);

      controller.dispose();
      await tester.pumpWidget(const SizedBox.shrink());
    });

    testWidgets('medium 档：静态单帧（画笔在、逐帧 AnimatedBuilder 不在）',
        (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.medium;
      final controller =
          AnimationController(vsync: tester, duration: const Duration(seconds: 1));
      unawaited(controller.repeat());

      await tester.pumpWidget(
        Directionality(
          textDirection: TextDirection.ltr,
          child: ParticleLayer(
            element: particleElement(),
            particleAnimation: controller,
            mainAnimation: controller,
          ),
        ),
      );
      await tester.pump();

      expect(countPainters(tester, '_ParticlePainter'), 1);
      expect(find.byType(AnimatedBuilder), findsNothing);

      controller.dispose();
      await tester.pumpWidget(const SizedBox.shrink());
    });

    testWidgets('low 档：粒子层整体不挂载（挂载数下降）', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.low;
      final controller =
          AnimationController(vsync: tester, duration: const Duration(seconds: 1));
      unawaited(controller.repeat());

      await tester.pumpWidget(
        Directionality(
          textDirection: TextDirection.ltr,
          child: ParticleLayer(
            element: particleElement(),
            particleAnimation: controller,
            mainAnimation: controller,
          ),
        ),
      );
      await tester.pump();

      expect(countPainters(tester, '_ParticlePainter'), 0);

      controller.dispose();
      await tester.pumpWidget(const SizedBox.shrink());
    });
  });

  group('EffectLayer — 门控扩面', () {
    testWidgets('ultra 档：默认柔光动画挂载', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.ultra;
      final controller =
          AnimationController(vsync: tester, duration: const Duration(seconds: 1));
      unawaited(controller.repeat(reverse: true));

      await tester.pumpWidget(
        Directionality(
          textDirection: TextDirection.ltr,
          child: EffectLayer(mainAnimation: controller),
        ),
      );
      await tester.pump();

      expect(countPainters(tester, '_PulseGlowPainter'), 1);
      expect(countPainters(tester, '_AmbientVignettePainter'), 1);
      expect(find.byType(AnimatedBuilder), findsOneWidget);

      controller.dispose();
      await tester.pumpWidget(const SizedBox.shrink());
    });

    testWidgets('medium 档：柔光静态化（无逐帧重建）', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.medium;
      final controller =
          AnimationController(vsync: tester, duration: const Duration(seconds: 1));
      unawaited(controller.repeat(reverse: true));

      await tester.pumpWidget(
        Directionality(
          textDirection: TextDirection.ltr,
          child: EffectLayer(mainAnimation: controller),
        ),
      );
      await tester.pump();

      expect(countPainters(tester, '_PulseGlowPainter'), 1);
      expect(find.byType(AnimatedBuilder), findsNothing);

      controller.dispose();
      await tester.pumpWidget(const SizedBox.shrink());
    });

    testWidgets('low 档：特效层不挂载', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.low;
      final controller =
          AnimationController(vsync: tester, duration: const Duration(seconds: 1));
      unawaited(controller.repeat(reverse: true));

      await tester.pumpWidget(
        Directionality(
          textDirection: TextDirection.ltr,
          child: EffectLayer(mainAnimation: controller),
        ),
      );
      await tester.pump();

      expect(countPainters(tester, '_PulseGlowPainter'), 0);
      expect(countPainters(tester, '_AmbientVignettePainter'), 0);

      controller.dispose();
      await tester.pumpWidget(const SizedBox.shrink());
    });
  });

  group('WeatherHeader — 全屏天气装饰门控（home 最大装饰源）', () {
    Widget wrap(Widget child) => ProviderScope(
          overrides: [
            dashboardProvider.overrideWith((ref) => _StaticDashboardNotifier()),
          ],
          child: testMaterialApp(
            home: Scaffold(body: Stack(children: [child])),
          ),
        );

    testWidgets('ultra 档：星域+天气特效挂载，常驻动画保持运行', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.ultra;
      await tester.pumpWidget(wrap(const WeatherHeader()));
      // 入场 TweenAnimationBuilder + 常驻 repeat 动画：不能 pumpAndSettle
      await tester.pump(const Duration(milliseconds: 600));

      expect(countPainters(tester, '_AnimatedStarPainter'), 1);
      expect(countPainters(tester, '_SunRayPainter'), 1);
      expect(
        tester.binding.hasScheduledFrame,
        isTrue,
        reason: 'ultra 档天气装饰动画应持续调度帧',
      );

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
    });

    testWidgets(
      'medium 档：装饰静态化——pumpAndSettle 可完成（无常驻逐帧动画）',
      (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.medium;
      await tester.pumpWidget(wrap(const WeatherHeader()));
      await tester.pumpAndSettle();

      expect(
        countPainters(tester, '_AnimatedStarPainter'),
        1,
        reason: 'staticFrame 档保留单帧星域（静态化而非全删）',
      );
      expect(
        tester.binding.hasScheduledFrame,
        isFalse,
        reason: 'staticFrame 档不应有常驻动画调度帧',
      );

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
    });

    testWidgets('low 档：星域/天气特效挂载数下降为 0，且无逐帧动画', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.low;
      await tester.pumpWidget(wrap(const WeatherHeader()));
      await tester.pumpAndSettle();

      expect(countPainters(tester, '_AnimatedStarPainter'), 0);
      expect(countPainters(tester, '_SunRayPainter'), 0);
      expect(countPainters(tester, '_CloudPainter'), 0);
      expect(countPainters(tester, '_RainPainter'), 0);
      expect(countPainters(tester, '_MeteorPainter'), 0);
      expect(tester.binding.hasScheduledFrame, isFalse);

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
    });

    testWidgets('ultra 与 low 档装饰画笔挂载总数对比：low 严格下降', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.ultra;
      await tester.pumpWidget(wrap(const WeatherHeader()));
      await tester.pump(const Duration(milliseconds: 600));
      final ultraPainters = tester
          .widgetList(find.byWidgetPredicate((w) => w is CustomPaint))
          .length;
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();

      PerformanceService.instance.currentTier.value = PerformanceTier.low;
      await tester.pumpWidget(wrap(const WeatherHeader()));
      await tester.pumpAndSettle();
      final lowPainters = tester
          .widgetList(find.byWidgetPredicate((w) => w is CustomPaint))
          .length;
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();

      expect(
        lowPainters,
        lessThan(ultraPainters),
        reason: '低档装饰挂载数必须严格下降（U-01 Step 2 验收口径）',
      );
    });
  });
}

/// 测试用静态 dashboard 仓库：所有接口返回空 map（sunny 默认天气），
/// 不触网、不产生重试 Timer。
class _StubDashboardRepository implements DashboardRepository {
  @override
  Future<Map<String, dynamic>> getDashboardStatus() async => <String, dynamic>{};

  @override
  Future<Map<String, dynamic>> getGrowthDashboard() async =>
      <String, dynamic>{};

  @override
  Future<Map<String, dynamic>> getPredictiveDashboard() async =>
      <String, dynamic>{};

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

/// WeatherHeader 只读 weather.type；用真实 notifier + 桩仓库满足
/// StateNotifierProvider 的 override 类型约束。
class _StaticDashboardNotifier extends DashboardNotifier {
  _StaticDashboardNotifier() : super(_StubDashboardRepository());
}
