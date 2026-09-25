import 'package:confetti/confetti.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/design/tokens_v2/state_tokens.dart';
import 'package:sparkle/core/design/widgets/global_particle_counter.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';

void main() {
  group('U-02 motion token resolver（两档输出真实不同）', () {
    test('standard 档保持既有默认动效', () {
      final tokens = resolveSparkleMotionTokens(StimulationLevel.standard);
      expect(tokens.fast, const Duration(milliseconds: 150));
      expect(tokens.normal, const Duration(milliseconds: 250));
      expect(tokens.slow, const Duration(milliseconds: 400));
      expect(tokens.slower, const Duration(milliseconds: 600));
      expect(tokens.bounceCurve, Curves.elasticOut);
      expect(tokens.overshootCurve, Curves.easeOutBack);
    });

    test('low 档时长收缩且弹性/过冲撤除', () {
      final standard = resolveSparkleMotionTokens(StimulationLevel.standard);
      final low = resolveSparkleMotionTokens(StimulationLevel.low);

      // 减法一：时长整体收缩（每档严格更短，屏幕运动滞留时间下降）。
      expect(low.fast, lessThan(standard.fast));
      expect(low.normal, lessThan(standard.normal));
      expect(low.slow, lessThan(standard.slow));
      expect(low.slower, lessThan(standard.slower));

      // 减法二：奖励性曲线（弹性/过冲）替换为 easeOut，语义曲线保持。
      expect(low.bounceCurve, isNot(standard.bounceCurve));
      expect(low.overshootCurve, isNot(standard.overshootCurve));
      expect(low.standardCurve, standard.standardCurve);
      expect(low.enterCurve, standard.enterCurve);
      expect(low.exitCurve, standard.exitCurve);
    });
  });

  group('U-02 状态令牌（calm/celebrate/attention × 两档）', () {
    test('celebrate：低刺激粒子归零、弹性撤除、时长收缩', () {
      final standard = SparkleStateTokens.forMood(
        SparkleStateMood.celebrate,
      );
      final low = SparkleStateTokens.forMood(
        SparkleStateMood.celebrate,
        level: StimulationLevel.low,
      );
      expect(standard.particleScale, greaterThan(0));
      expect(standard.allowBounce, isTrue);
      expect(low.particleScale, 0);
      expect(low.allowBounce, isFalse);
      expect(low.motionScale, lessThan(standard.motionScale));
      expect(low.glowOpacity, lessThan(standard.glowOpacity));
    });

    test('attention：保留可见性，低刺激仅收紧发光与时长', () {
      final low = SparkleStateTokens.forMood(
        SparkleStateMood.attention,
        level: StimulationLevel.low,
      );
      // attention 需求不能减到看不见：发光仍为正。
      expect(low.glowOpacity, greaterThan(0));
      expect(low.particleScale, 0);
      expect(low.allowBounce, isFalse);
    });

    test('calm：本征低装饰，两档一致', () {
      final standard = SparkleStateTokens.forMood(SparkleStateMood.calm);
      final low = SparkleStateTokens.forMood(
        SparkleStateMood.calm,
        level: StimulationLevel.low,
      );
      expect(low.glowOpacity, standard.glowOpacity);
      expect(low.particleScale, 0);
      expect(low.allowBounce, isFalse);
    });
  });

  group('U-02 Theme 层真实接线（applyToTheme 切换注册的扩展档位）', () {
    ThemeData themed() => ThemeData(
          useMaterial3: true,
          extensions: <ThemeExtension<dynamic>>[SparkleThemeExtension.light()],
        );

    testWidgets('普通档：context.motion 为默认时长、lowStimulation 关', (tester) async {
      late Duration motionNormal;
      late bool lowStimulation;
      await tester.pumpWidget(
        MaterialApp(
          theme: themed(),
          home: Builder(
            builder: (context) {
              motionNormal = context.motion.normal;
              lowStimulation = context.lowStimulation;
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      expect(motionNormal, const Duration(milliseconds: 250));
      expect(lowStimulation, isFalse);
    });

    // wt358 已用 where+followedBy 零显式标注修复 CFE 编译雷,接线恢复,本用例回归真实断言。
    testWidgets('低刺激档：同一消费点拿到减法后的时长与档位', (tester) async {
      late Duration motionNormal;
      late bool lowStimulation;
      late double celebrateGlow;
      await tester.pumpWidget(
        MaterialApp(
          theme: themed(),
          home: EmotionResponsiveAppWrapper(
            config: const EmotionResponsiveConfig.lowStimulus(),
            child: Builder(
              builder: (context) {
                motionNormal = context.motion.normal;
                lowStimulation = context.lowStimulation;
                celebrateGlow =
                    context.stateTokens(SparkleStateMood.celebrate).glowOpacity;
                return const SizedBox.shrink();
              },
            ),
          ),
        ),
      );
      // 动效参数真实变化，不是空设置值：档位、时长、庆祝发光全部切到 low 档。
      expect(lowStimulation, isTrue);
      expect(motionNormal, const Duration(milliseconds: 150));
      expect(celebrateGlow, 0.08);
    });
  });

  group('U-02 导航转场一致（in-app 低刺激经 MediaQuery 叠加）', () {
    Future<bool> pumpCalm(
      WidgetTester tester, {
      required bool inAppDisableAnimations,
    }) async {
      late bool calm;
      await tester.pumpWidget(
        MediaQuery(
          data: MediaQueryData(disableAnimations: inAppDisableAnimations),
          child: Builder(
            builder: (context) {
              calm = sparkleTransitionCalm(context, false);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      return calm;
    }

    testWidgets('in-app 关闭动效（低刺激 alwaysLow 半边）→ 平静档', (tester) async {
      expect(await pumpCalm(tester, inAppDisableAnimations: true), isTrue);
    });

    testWidgets('普通档且系统未要求 → 全动效档', (tester) async {
      expect(await pumpCalm(tester, inAppDisableAnimations: false), isFalse);
    });
  });

  group('U-02 庆祝组件低刺激整体短路', () {
    setUp(() {
      GlobalParticleCounter.releaseParticles(
        GlobalParticleCounter.currentCount,
      );
    });

    testWidgets('低刺激：play 触发也不挂载粒子、不占粒子预算', (tester) async {
      await tester.pumpWidget(
        const EmotionResponsiveTheme(
          config: EmotionResponsiveConfig.lowStimulus(),
          child: MaterialApp(
            home: SparkleConfetti(play: true, enableSensory: false),
          ),
        ),
      );
      await tester.pump();
      expect(find.byType(ConfettiWidget), findsNothing);
      expect(GlobalParticleCounter.currentCount, 0);
    });

    testWidgets('普通档：庆祝正常挂载并计入粒子预算', (tester) async {
      await tester.pumpWidget(
        const EmotionResponsiveTheme(
          config: EmotionResponsiveConfig.normal(),
          child: MaterialApp(
            home: SparkleConfetti(
              play: true,
              enableSensory: false,
            ),
          ),
        ),
      );
      await tester.pump();
      expect(find.byType(ConfettiWidget), findsOneWidget);
      expect(GlobalParticleCounter.currentCount, 20);
    });
  });
}
