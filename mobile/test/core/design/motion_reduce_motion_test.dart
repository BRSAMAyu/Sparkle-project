import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/motion.dart';
import 'package:sparkle/features/focus/presentation/widgets/flip_clock.dart';
import 'package:sparkle/features/focus/presentation/widgets/star_background.dart';
import 'package:sparkle/features/task/presentation/widgets/timer_widget.dart';

/// A11Y-ICONS（N33 持续动效可达守护 · reduce-motion 首批）：
///
/// 验收（卡面）：disableAnimations=true 时以下动效静默——
/// controller 不启动 / 立即静止；口径统一走 MediaQuery
/// （context.reduceMotion），禁 platformDispatcher 直读。
///
/// 断言口径：`binding.transientCallbackCount`（活跃 ticker 数）——
/// 0 = 无任何 repeat 动画在跑；对照组 = 1（repeat 在跑）。
///
/// 覆盖：DS 层 createBreathingController（守护令①）+ focus 域首批
/// star_background / flip_clock / timer_widget（守护令②）。
void main() {
  /// MaterialApp 内层注入 disableAnimations=true 的 MediaQuery
  /// （内层覆盖 MaterialApp 根 MediaQuery，子树读到的即系统减弱动效态）。
  Widget wrapDisabledAnimations(Widget child) => MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: child,
        ),
      );

  /// 收工把树换掉：触发 State.dispose → controller.dispose，
  /// 避免「动画在树销毁后仍在跑」的收尾报错（对照组 repeat 场景必做）。
  Future<void> unwindTree(WidgetTester tester) =>
      tester.pumpWidget(const SizedBox.shrink());

  group('SparkleMotion.createBreathingController（DS 守护令①）', () {
    testWidgets('disableAnimations=true → controller 不启动，静止呼吸中点',
        (tester) async {
      AnimationController? captured;
      await tester.pumpWidget(
        _VsyncHarness(
          builder: (context, vsync) {
            captured ??= SparkleMotion.createBreathingController(
              vsync,
              disableAnimations: true,
            );
            return const SizedBox.shrink();
          },
        ),
      );
      await tester.pump(const Duration(seconds: 2));

      expect(captured, isNotNull);
      expect(
        captured!.isAnimating,
        isFalse,
        reason: '减弱动效下呼吸控制器不得 repeat（N33）',
      );
      expect(captured!.value, 0.5, reason: '静止终态 = 呼吸中点');
      expect(tester.binding.transientCallbackCount, 0);
    });

    testWidgets('disableAnimations=false → 正常呼吸 repeat', (tester) async {
      AnimationController? captured;
      await tester.pumpWidget(
        _VsyncHarness(
          builder: (context, vsync) {
            captured ??= SparkleMotion.createBreathingController(vsync);
            return const SizedBox.shrink();
          },
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));

      expect(captured!.isAnimating, isTrue);
      expect(tester.binding.transientCallbackCount, 1);

      captured!.dispose();
    });
  });

  group('StarBackground（focus 首批）', () {
    testWidgets('disableAnimations=true → 星星静止（无 repeat ticker）',
        (tester) async {
      await tester.pumpWidget(
        wrapDisabledAnimations(
          const Scaffold(
            body: SizedBox(
              width: 200,
              height: 200,
              child: StarBackground(starCount: 10),
            ),
          ),
        ),
      );
      await tester.pump(const Duration(seconds: 3));

      expect(
        tester.binding.transientCallbackCount,
        0,
        reason: '减弱动效下星空闪烁必须静默（N33）',
      );
    });

    testWidgets('对照组：默认（未开启减弱动效）→ 闪烁持续运行', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 200,
              height: 200,
              child: StarBackground(starCount: 10),
            ),
          ),
        ),
      );
      await tester.pump(const Duration(seconds: 1));

      expect(tester.binding.transientCallbackCount, 1,
          reason: '对照组：闪烁 repeat 应在跑',);
      await unwindTree(tester);
    });
  });

  group('FlipClock（focus 首批）', () {
    testWidgets('disableAnimations=true → 冒号常亮静止（无 repeat ticker）',
        (tester) async {
      await tester.pumpWidget(
        wrapDisabledAnimations(
          const Scaffold(body: Center(child: FlipClock(seconds: 65))),
        ),
      );
      await tester.pump(const Duration(seconds: 1));

      expect(
        tester.binding.transientCallbackCount,
        0,
        reason: '减弱动效下冒号闪烁必须静默（N33）',
      );
    });

    testWidgets('disableAnimations=true → 数字变化直接落位（跳过翻转）',
        (tester) async {
      await tester.pumpWidget(
        wrapDisabledAnimations(
          const Scaffold(body: Center(child: FlipClock(seconds: 65))),
        ),
      );
      await tester.pump();
      // 每位数字由上下两半 + 动画层共 4 份 Text 呈现。
      expect(find.text('5'), findsNWidgets(4));

      // 秒位 5 → 6：减弱动效下立即换字（一帧内完成，无 300ms 翻转）。
      await tester.pumpWidget(
        wrapDisabledAnimations(
          const Scaffold(body: Center(child: FlipClock(seconds: 66))),
        ),
      );
      await tester.pump();
      expect(
        find.text('6'),
        findsNWidgets(4),
        reason: '减弱动效下数字必须立即落到新值',
      );
      expect(find.text('5'), findsNothing,
          reason: '旧数字不得残留（有翻转时上半仍停留旧值）',);
    });

    testWidgets('对照组：默认（未开启减弱动效）→ 冒号闪烁运行', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: Center(child: FlipClock(seconds: 65))),
        ),
      );
      await tester.pump(const Duration(seconds: 1));

      expect(tester.binding.transientCallbackCount, 1,
          reason: '对照组：冒号 repeat 应在跑',);
      await unwindTree(tester);
    });
  });

  group('TimerWidget（focus 首批，装饰性脉动守护）', () {
    Finder scaledTransforms() => find.byWidgetPredicate(
          (w) =>
              w is Transform &&
              (w.transform.getMaxScaleOnAxis() - 1.0).abs() > 0.001,
        );

    testWidgets('disableAnimations=true → 计时中表盘无脉动缩放（静止 1.0）',
        (tester) async {
      await tester.pumpWidget(
        wrapDisabledAnimations(
          const Scaffold(
            body: Center(
              child: TimerWidget(
                mode: TimerMode.countUp,
                autoStart: true,
              ),
            ),
          ),
        ),
      );
      // 分两帧推进 800ms：跨过 AnimatedSwitcher 的一次性入场过渡（150ms
      // 级，单次大步 pump 会把它冻结在活跃态），此时剩余 ticker 只可能
      // 是装饰性脉动 repeat。
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));

      expect(
        tester.binding.transientCallbackCount,
        0,
        reason: '减弱动效下表盘脉动 ticker 必须静默（N33）',
      );
      expect(
        scaledTransforms(),
        findsNothing,
        reason: '表盘 scale 保持 1.0；秒级计时功能本身保留',
      );
    });

    testWidgets('对照组：默认（未开启减弱动效）→ 脉动缩放运行', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: TimerWidget(
                mode: TimerMode.countUp,
                autoStart: true,
              ),
            ),
          ),
        ),
      );
      // 同上分两帧：让一次性入场过渡跑完，只留脉动 repeat；800ms 处于
      // 1500ms 脉动周期中段，scale 已偏离 1.0。
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));

      expect(tester.binding.transientCallbackCount, 1,
          reason: '对照组：脉动 repeat 应在跑',);
      expect(scaledTransforms(), findsOneWidget);
      await unwindTree(tester);
    });
  });
}

class _VsyncHarness extends StatefulWidget {
  const _VsyncHarness({required this.builder});

  final Widget Function(BuildContext context, TickerProvider vsync) builder;

  @override
  State<_VsyncHarness> createState() => _VsyncHarnessState();
}

class _VsyncHarnessState extends State<_VsyncHarness>
    with SingleTickerProviderStateMixin {
  @override
  Widget build(BuildContext context) => widget.builder(context, this);
}
