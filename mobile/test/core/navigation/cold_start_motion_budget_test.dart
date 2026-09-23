import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/navigation/cold_start_motion.dart';

/// N20（A-SPEC4 SPEC v1.4）· 冷启动表现层总账守卫。
///
/// 账目：splash 品牌窗 + 落地转场 ≤ 600ms 预算；每一段都必须取
/// AnimationSystem 既有档位（禁 Duration 字面量回归）。
/// 改令牌先过此账——预算被顶破即红。
void main() {
  group('ColdStartMotion 令牌守卫（N20）', () {
    test('表现层串行总账 = 品牌窗 + 落地转场 ≤ 600ms 预算', () {
      expect(
        ColdStartMotion.presentationLedger,
        lessThanOrEqualTo(ColdStartMotion.presentationBudget),
      );
      expect(
        ColdStartMotion.presentationBudget,
        const Duration(milliseconds: 600),
      );
    });

    test('每段都取 AnimationSystem 既有档位，无魔法数', () {
      expect(ColdStartMotion.splash, AnimationSystem.scene);
      expect(ColdStartMotion.brandWindow, AnimationSystem.normal);
      expect(ColdStartMotion.landing, AnimationSystem.standard);
      expect(ColdStartMotion.landingReverse, AnimationSystem.quick);
      expect(ColdStartMotion.landingReduceMotion, AnimationSystem.quick);
      expect(
        ColdStartMotion.landingReverseReduceMotion,
        AnimationSystem.micro,
      );
    });

    test('收敛后总账严格小于旧三段串行叠加（审计实证 ≈1.62s）', () {
      // @7f855d70：_ColdStartFade 320ms + splash 900ms 四段 + 落地 400ms
      const legacyLedger = Duration(milliseconds: 320 + 900 + 400);
      expect(
        ColdStartMotion.presentationLedger,
        lessThan(legacyLedger),
      );
      // 与旧账的差距即本卡收敛量（≥1s）。
      expect(
        legacyLedger - ColdStartMotion.presentationLedger,
        greaterThanOrEqualTo(const Duration(milliseconds: 1000)),
      );
    });

    test('splash 动画本体受 D-3 上限（≤400ms 一轮）', () {
      expect(
        ColdStartMotion.splash,
        lessThanOrEqualTo(const Duration(milliseconds: 400)),
      );
      // 品牌窗早于动画上限结束，落地段才能与 splash 尾段交叠。
      expect(ColdStartMotion.brandWindow, lessThan(ColdStartMotion.splash));
    });
  });
}
