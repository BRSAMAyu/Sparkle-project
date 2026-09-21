import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/features/home/presentation/widgets/decoration_policy.dart';

/// U-01 Step 2：home 装饰降档决策点单测。
///
/// 档位口径与既有 background_layer 门控对齐：
/// low=off / medium=staticFrame / ultra|high=animated（reduce-motion 降为 staticFrame）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  var currentTierForTest = PerformanceTier.high;

  setUp(() {
    currentTierForTest = PerformanceTier.high;
    PerformanceService.instance.currentTier.value = currentTierForTest;
    PerformanceService.instance.motionIntensityLevel.value =
        MotionIntensityLevel.high;
  });

  tearDown(() {
    PerformanceService.instance.currentTier.value =
        defaultPerformanceTier();
  });

  Future<DecorationMode> pumpAndResolve(
    WidgetTester tester, {
    bool disableAnimations = false,
  }) async {
    var resolved = DecorationMode.animated;
    await tester.pumpWidget(
      MediaQuery(
        data: MediaQueryData(disableAnimations: disableAnimations),
        child: Builder(
          builder: (context) {
            resolved = resolveDecorationMode(context);
            return const SizedBox.shrink();
          },
        ),
      ),
    );
    return resolved;
  }

  group('resolveDecorationMode — tier 梯度', () {
    testWidgets('ultra/high → animated（完整动效档）', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.ultra;
      expect(await pumpAndResolve(tester), DecorationMode.animated);

      PerformanceService.instance.currentTier.value = PerformanceTier.high;
      expect(await pumpAndResolve(tester), DecorationMode.animated);
    });

    testWidgets('medium → staticFrame（单帧静态化档）', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.medium;
      expect(await pumpAndResolve(tester), DecorationMode.staticFrame);
    });

    testWidgets('low → off（非必要装饰不挂载档）', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.low;
      expect(await pumpAndResolve(tester), DecorationMode.off);
    });

    testWidgets('reduce-motion 把 animated 档降为 staticFrame', (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.ultra;
      expect(
        await pumpAndResolve(tester, disableAnimations: true),
        DecorationMode.staticFrame,
      );
    });

    testWidgets('motion=off 时 enableParticles 收口为 false（既有口径不回退）',
        (tester) async {
      PerformanceService.instance.currentTier.value = PerformanceTier.ultra;
      await PerformanceService.instance
          .setMotionIntensityLevel(MotionIntensityLevel.off, persist: false);
      expect(PerformanceService.instance.enableParticles, isFalse);
      expect(
        PerformanceService.instance.currentTier.value,
        PerformanceTier.low,
      );
    });
  });

  group('scaleDecorationCount — 密度降档', () {
    test('animated：ultra 全量，high 收敛 30%', () {
      expect(
        scaleDecorationCount(
          DecorationMode.animated,
          isUltra: true,
          animatedCount: 20,
        ),
        20,
      );
      expect(
        scaleDecorationCount(
          DecorationMode.animated,
          isUltra: false,
          animatedCount: 20,
        ),
        14,
      );
    });

    test('staticFrame 使用减半静态帧数量', () {
      expect(
        scaleDecorationCount(
          DecorationMode.staticFrame,
          isUltra: false,
          animatedCount: 40,
          staticCount: 16,
        ),
        16,
      );
      expect(
        scaleDecorationCount(
          DecorationMode.staticFrame,
          isUltra: false,
          animatedCount: 40,
        ),
        0,
      );
    });

    test('off 恒为 0（调用方跳过挂载）', () {
      expect(
        scaleDecorationCount(
          DecorationMode.off,
          isUltra: true,
          animatedCount: 20,
          staticCount: 10,
        ),
        0,
      );
    });
  });
}
