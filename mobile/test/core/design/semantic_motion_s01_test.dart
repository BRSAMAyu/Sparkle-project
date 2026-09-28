import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/design/semantic_motion.dart';
import 'package:sparkle/core/design/widgets/global_particle_counter.dart';
import 'package:sparkle/core/design/widgets/semantic_motion_widgets.dart';

/// V4-S01 · 语义乐谱动效 + 降低动态等价（motion-policy 锁面机器证据）。
///
/// 卡面验收 → 测试映射（每面一正一反，控制组证明探针判别力）：
///
/// 1. **无后台无限动画和全屏粒子** — F 组：新族 + 按压面 settle 后
///    `transientCallbackCount == 0`（正）/ repeat 控制组 ≥1（反，探针活性）；
///    新表面源码棘轮（禁 `repeat`/`AnimationController`）；印章零粒子
///    （GlobalParticleCounter 零占用）。存量 48 文件 repeat 清单为
///    U15 长尾面，本卡不冒充全 app 达成（见 limitations）。
/// 2. **cancel/replay 不重播成功；enter/state/milestone 预算可测** —
///    A 组：预算 ↔ 乐谱窗口校验一正一反；B 组按压 80ms 对齐 + 静态分支；
///    C 组提案 enter 一次性入场 + reduce-motion 直落终态；D 组回执替换
///    同 key 重投不重播 / 取消内容无成功载体 / 首挂载不播替换；E 组印章
///    160ms 压印 + reduce-motion 静态。
/// 3. **profile 下帧时间与 baseline 对照** — H 组：同一 harness 内动画路
///    vs reduce-motion 静态基线逐帧墙钟对照（测试环境 CPU 代理口径；
///    真机 profile 归设备面，NOT_RUN 登记）。
///
/// reduce-motion 口径：MediaQuery `disableAnimations`（双源并集的系统半边；
/// in-app 半边经 app 壳组装进同一字段，F06 组装律测试已钉）。

/// 阈值走环境开关（CI 慢机 -D 放宽；默认门不删，与 test/performance 口径一致）。
const int _scrollFrameThresholdUs = int.fromEnvironment(
  'S01_SCROLL_FRAME_US',
  defaultValue: 70000,
);
const int _frameThresholdUs = int.fromEnvironment(
  'S01_FRAME_US',
  defaultValue: 33334, // 2 × 16.67ms（CI 慢机可 -D 放宽，门不删）
);

void main() {
  Widget wrap(Widget child, {bool disableAnimations = false}) => MaterialApp(
        home: MediaQuery(
          data: MediaQueryData(disableAnimations: disableAnimations),
          child: Scaffold(body: child),
        ),
      );

  /// 收工卸树：repeat 控制组的 controller 随 dispose 释放，避免跨树泄漏。
  Future<void> unwindTree(WidgetTester tester) =>
      tester.pumpWidget(const SizedBox.shrink());

  double opacityOf(WidgetTester tester) =>
      tester.widget<Opacity>(find.byType(Opacity)).opacity;

  // ═══ A 组：enter/state/milestone 预算可测（验收 2 后半） ═══

  group('A 预算可测（语义乐谱窗口机器校验）', () {
    test('A+ 默认预算逐槽落在乐谱窗口内且校验零违例', () {
      expect(kSparkleSemanticMotionBudgets.validateAgainstScore(), isEmpty);
      expect(
        kSparkleSemanticMotionBudgets.forSlot(SparkleSemanticMotionSlot.press),
        const Duration(milliseconds: 80),
      );
      expect(
        kSparkleSemanticMotionBudgets
            .forSlot(SparkleSemanticMotionSlot.proposalEnter)
            .inMilliseconds,
        inExclusiveRange(160, 220),
      );
      expect(
        kSparkleSemanticMotionBudgets
            .forSlot(SparkleSemanticMotionSlot.receiptReplace),
        const Duration(milliseconds: 160),
      );
      expect(
        kSparkleSemanticMotionBudgets
            .forSlot(SparkleSemanticMotionSlot.evidenceStamp),
        const Duration(milliseconds: 160),
      );
      expect(
        kSparkleSemanticMotionBudgets
            .forSlot(SparkleSemanticMotionSlot.milestone)
            .inMilliseconds,
        lessThanOrEqualTo(650),
      );
    });

    test('A- 变异预算被窗口校验具名判负（探针非恒真）', () {
      const mutated = SparkleSemanticMotionBudgets(
        press: Duration(milliseconds: 200), // 乐谱 80ms
        proposalEnter: Duration(milliseconds: 300), // 乐谱 [160,220]
        milestone: Duration(milliseconds: 900), // 乐谱 ≤650
      );
      final violations = mutated.validateAgainstScore();
      expect(violations, hasLength(3));
      expect(violations.join('\n'), contains('SparkleSemanticMotionSlot.press'));
      expect(violations.join('\n'), contains('proposalEnter'));
      expect(violations.join('\n'), contains('milestone'));
    });
  });

  // ═══ B 组：按压面（乐谱「80ms 轻压」） ═══

  group('B 按压节奏与静态分支（SparklePressable 对齐乐谱）', () {
    testWidgets('B+ 按压 80ms 在航可测：40ms 处在 0.97–1.0 之间，落定 0.97',
        (tester) async {
      await tester.pumpWidget(wrap(
        SparklePressable(onTap: () {}, child: const Text('press')),
      ),);
      final gesture = await tester.startGesture(
        tester.getCenter(find.text('press')),
      );
      await tester.pump(); // onHighlightChanged → setState → 动画启动
      await tester.pump(const Duration(milliseconds: 40));
      // 压缩换算定位：AnimatedScale 的 ScaleTransition 直接包裹 Material
      // （框架树另有无关 ScaleTransition，用包裹物精确认位）。
      final pressScale = find.byWidgetPredicate(
        (w) => w is ScaleTransition && w.child is Material,
      );
      final mid =
          tester.widget<ScaleTransition>(pressScale).scale.value;
      expect(mid, inExclusiveRange(0.97, 1.0));
      await tester.pump(const Duration(milliseconds: 120));
      expect(
        tester.widget<ScaleTransition>(pressScale).scale.value,
        moreOrLessEquals(0.97),
      );
      await gesture.up();
      await tester.pumpAndSettle();
    });

    testWidgets('B+ 静态分支：减弱动效不装 AnimatedScale 壳，点按仍触发',
        (tester) async {
      var tapped = false;
      await tester.pumpWidget(wrap(
        SparklePressable(onTap: () => tapped = true, child: const Text('press')),
        disableAnimations: true,
      ),);
      expect(find.byType(AnimatedScale), findsNothing);
      await tester.tap(find.text('press'));
      await tester.pumpAndSettle();
      expect(tapped, isTrue);
      await unwindTree(tester);
    });

    testWidgets('B- 控制组：常规路径 AnimatedScale 在场（静态分支断言非恒真）',
        (tester) async {
      await tester.pumpWidget(wrap(
        SparklePressable(onTap: () {}, child: const Text('press')),
      ),);
      expect(find.byType(AnimatedScale), findsOneWidget);
      await unwindTree(tester);
    });
  });

  // ═══ C 组：提案出现（enter 面） ═══

  group('C 提案出现：一次性入场 + reduce-motion 直落终态', () {
    testWidgets('C+ 首帧抬起中（透明度 0→1 在航），落定完整可见', (tester) async {
      await tester.pumpWidget(wrap(
        const SparkleProposalEnter(child: Text('proposal')),
      ),);
      expect(opacityOf(tester), moreOrLessEquals(0.0)); // 首帧在抬起点
      await tester.pump(const Duration(milliseconds: 100));
      expect(opacityOf(tester), inExclusiveRange(0.0, 1.0)); // 在航
      await tester.pumpAndSettle();
      expect(opacityOf(tester), moreOrLessEquals(1.0));
      expect(find.text('proposal'), findsOneWidget);
    });

    testWidgets('C+ 静态分支：减弱动效首帧完整呈现（等价信息不丢失），零动画壳',
        (tester) async {
      await tester.pumpWidget(wrap(
        const SparkleProposalEnter(child: Text('proposal')),
        disableAnimations: true,
      ),);
      expect(find.text('proposal'), findsOneWidget);
      expect(find.byType(Opacity), findsNothing);
      expect(find.byType(TweenAnimationBuilder<double>), findsNothing);
      expect(tester.binding.transientCallbackCount, 0);
      await unwindTree(tester);
    });

    testWidgets('C- 控制组：常规路径首帧透明度 < 1（静态分支断言非恒真）',
        (tester) async {
      await tester.pumpWidget(wrap(
        const SparkleProposalEnter(child: Text('proposal')),
      ),);
      expect(opacityOf(tester), lessThan(1.0));
      await tester.pumpAndSettle();
      await unwindTree(tester);
    });
  });

  // ═══ D 组：回执替换（state 面 + replay/cancel 面） ═══

  group('D 回执替换：同 key 重投不重播；取消内容无成功载体', () {
    testWidgets('D+ 首挂载不播替换（初始内容直落终态），key 变化才播一次 160ms',
        (tester) async {
      await tester.pumpWidget(wrap(
        const SparkleReceiptSwap(
          replacementKey: 'evt-1',
          child: Text('v1'),
        ),
      ),);
      expect(find.byType(Opacity), findsNothing); // 首挂载 = 非回执
      expect(find.text('v1'), findsOneWidget);

      await tester.pumpWidget(wrap(
        const SparkleReceiptSwap(
          replacementKey: 'evt-2',
          child: Text('v2'),
        ),
      ),);
      await tester.pump();
      expect(opacityOf(tester), moreOrLessEquals(0.0)); // 替换动画在起点
      await tester.pump(const Duration(milliseconds: 80));
      expect(opacityOf(tester), inExclusiveRange(0.0, 1.0));
      await tester.pumpAndSettle();
      expect(opacityOf(tester), moreOrLessEquals(1.0));
      expect(find.text('v2'), findsOneWidget);
      expect(find.text('v1'), findsNothing);
    });

    testWidgets('D+ 同 key 重投（恢复重放）不重播替换：下一帧即终态', (tester) async {
      await tester.pumpWidget(wrap(
        const SparkleReceiptSwap(
          replacementKey: 'evt-1',
          child: Text('v1'),
        ),
      ),);
      await tester.pumpWidget(wrap(
        const SparkleReceiptSwap(
          replacementKey: 'evt-2',
          child: Text('v2'),
        ),
      ),);
      await tester.pumpAndSettle(); // evt-2 替换完成
      // 恢复重放：同一 evt-2 再次投递（新实例、同 key、同内容）。
      await tester.pumpWidget(wrap(
        const SparkleReceiptSwap(
          replacementKey: 'evt-2',
          child: Text('v2'),
        ),
      ),);
      await tester.pump();
      // 未重启：不是从 0 重播——下一帧已在终态。
      expect(opacityOf(tester), moreOrLessEquals(1.0));
      expect(find.text('v2'), findsOneWidget);
      await unwindTree(tester);
    });

    testWidgets('D+ 取消面：换成取消内容 = 普通替换，树中无成功徽章载体',
        (tester) async {
      await tester.pumpWidget(wrap(
        const SparkleReceiptSwap(
          replacementKey: 'evt-1',
          child: Text('任务已更新'),
        ),
      ),);
      await tester.pumpAndSettle();
      await tester.pumpWidget(wrap(
        const SparkleReceiptSwap(
          replacementKey: 'evt-cancel',
          child: Text('已取消，未保存'),
        ),
      ),);
      await tester.pumpAndSettle();
      expect(find.text('已取消，未保存'), findsOneWidget);
      expect(find.text('任务已更新'), findsNothing);
      // 取消不是成功：无 PixelSuccessBadge、无残留 ticker。
      expect(find.byType(PixelSuccessBadge), findsNothing);
      expect(tester.binding.transientCallbackCount, 0);
      await unwindTree(tester);
    });

    testWidgets('D+ 静态分支：减弱动效下 key 变化即时替换（文本状态恢复不延迟）',
        (tester) async {
      await tester.pumpWidget(wrap(
        const SparkleReceiptSwap(
          replacementKey: 'evt-1',
          child: Text('v1'),
        ),
        disableAnimations: true,
      ),);
      await tester.pumpWidget(wrap(
        const SparkleReceiptSwap(
          replacementKey: 'evt-2',
          child: Text('v2'),
        ),
        disableAnimations: true,
      ),);
      expect(find.text('v2'), findsOneWidget);
      expect(find.byType(Opacity), findsNothing);
      expect(tester.binding.transientCallbackCount, 0);
      await unwindTree(tester);
    });
  });

  // ═══ E 组：证据印章（160ms + 零粒子） ═══

  group('E 证据印章：160ms 压印 + 零粒子 + 静态分支', () {
    testWidgets('E+ 压印在航（透明度/缩放在中段），落定全尺寸；零粒子发射',
        (tester) async {
      await tester.pumpWidget(wrap(
        const SparkleEvidenceStamp(child: Text('证据已登记')),
      ),);
      expect(opacityOf(tester), moreOrLessEquals(0.0));
      await tester.pump(const Duration(milliseconds: 80));
      expect(opacityOf(tester), inExclusiveRange(0.0, 1.0));
      await tester.pumpAndSettle();
      expect(opacityOf(tester), moreOrLessEquals(1.0));
      // 印章落定 = 全尺寸（本族 Transform 直接包裹印章 child；框架树另有
      // 无关 Transform，用「包裹 Text 的 Transform」精确定位）。
      final stampTransform = tester.widget<Transform>(
        find.byWidgetPredicate((w) => w is Transform && w.child is Text),
      );
      expect(
        stampTransform.transform.getMaxScaleOnAxis(),
        moreOrLessEquals(1.0),
      );
      expect(GlobalParticleCounter.currentCount, 0);
    });

    testWidgets('E+ 静态分支：减弱动效印章全尺寸即时呈现，零动画壳零 ticker',
        (tester) async {
      await tester.pumpWidget(wrap(
        const SparkleEvidenceStamp(child: Text('证据已登记')),
        disableAnimations: true,
      ),);
      expect(find.text('证据已登记'), findsOneWidget);
      expect(find.byType(Opacity), findsNothing);
      expect(tester.binding.transientCallbackCount, 0);
      await unwindTree(tester);
    });

    testWidgets('E- 控制组：常规路径首帧透明度 < 1 且粒子计数仍为 0（非恒真）',
        (tester) async {
      await tester.pumpWidget(wrap(
        const SparkleEvidenceStamp(child: Text('证据已登记')),
      ),);
      expect(opacityOf(tester), lessThan(1.0));
      expect(GlobalParticleCounter.currentCount, 0);
      await tester.pumpAndSettle();
      await unwindTree(tester);
    });
  });

  // ═══ F 组：无后台无限动画（验收 1） ═══

  group('F 无后台无限动画：settle 后零 ticker + 源码棘轮', () {
    testWidgets('F+ 语义族 + 按压面全 settle 后零持续 ticker（追加帧仍为 0）',
        (tester) async {
      await tester.pumpWidget(wrap(
        Column(
          children: [
            const SparkleProposalEnter(child: Text('proposal')),
            const SparkleReceiptSwap(
              replacementKey: 'k',
              child: Text('receipt'),
            ),
            const SparkleEvidenceStamp(child: Text('stamp')),
            SparklePressable(onTap: () {}, child: const Text('press')),
          ],
        ),
      ),);
      await tester.pumpAndSettle();
      expect(tester.binding.transientCallbackCount, 0);
      // 追加空转帧：若存在 repeat 类动画此处必然 > 0。
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));
      expect(tester.binding.transientCallbackCount, 0);
      expect(GlobalParticleCounter.currentCount, 0);
      await unwindTree(tester);
    });

    testWidgets('F- 控制组：repeat 动画同探针判 ≥1（零值断言非恒真）',
        (tester) async {
      await tester.pumpWidget(wrap(const _RepeatProbe()));
      await tester.pump();
      expect(tester.binding.transientCallbackCount, greaterThanOrEqualTo(1));
      await unwindTree(tester);
      await tester.pumpAndSettle();
    });

    test('F+ 源码棘轮：S01 新表面禁 repeat/AnimationController（结构零无限面）',
        () {
      for (final path in [
        'lib/core/design/semantic_motion.dart',
        'lib/core/design/widgets/semantic_motion_widgets.dart',
      ]) {
        // 剥离注释行后匹配：棘轮只认代码面（doc 注记提及禁令不判负）。
        final codeOnly = File(path)
            .readAsStringSync()
            .split('\n')
            .where((line) => !line.trimLeft().startsWith('//'))
            .join('\n');
        expect(
          codeOnly.contains('.repeat('),
          isFalse,
          reason: '$path 不得引入 repeat（后台无限动画面）',
        );
        expect(
          codeOnly.contains('AnimationController'),
          isFalse,
          reason: '$path 不得引入 AnimationController（与本族 implicit 纪律冲突）',
        );
      }
    });
  });

  // ═══ G 组：滚动正文不降帧 ═══

  group('G 滚动正文不降帧：语义族不锁正文帧预算', () {
    testWidgets('G+ 含语义族行列表滚帧在阈值内；settle 后零 ticker（不持续调度帧）',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListView.builder(
              itemCount: 60,
              itemBuilder: (context, index) => ListTile(
                title: SparkleProposalEnter(
                  child: Text('row $index'),
                ),
              ),
            ),
          ),
        ),
      );
      final frameTimes = <int>[];
      for (var i = 0; i < 20; i++) {
        final sw = Stopwatch()..start();
        await tester.fling(find.byType(ListView), const Offset(0, -300), 1000);
        await tester.pump();
        sw.stop();
        frameTimes.add(sw.elapsedMicroseconds);
      }
      final avg = frameTimes.reduce((a, b) => a + b) ~/ frameTimes.length;
      // ignore: avoid_print
      print('S01 scroll avg frame time: ${avg}us '
          '(threshold $_scrollFrameThresholdUs us)');
      expect(avg, lessThan(_scrollFrameThresholdUs));
      await tester.pumpAndSettle(); // 已建行的入场动画全部落定
      expect(tester.binding.transientCallbackCount, 0); // 正文不再被锁帧
      await unwindTree(tester);
    });

    testWidgets('G- 控制组：列表混入 repeat 行 → settle 后 ticker ≥1（探针活性）',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListView(
              children: const [
                ListTile(title: Text('plain')),
                ListTile(
                  title: SparkleProposalEnter(child: Text('semantic')),
                ),
                ListTile(title: _RepeatProbe()),
              ],
            ),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 400));
      expect(tester.binding.transientCallbackCount, greaterThanOrEqualTo(1));
      await unwindTree(tester);
      await tester.pumpAndSettle();
    });
  });

  // ═══ H 组：帧时间 vs baseline 对照（验收 3；测试环境 CPU 代理口径） ═══

  group('H 帧时间对照：动画路 vs reduce-motion 静态基线（同 harness）', () {
    Future<double> measureFrames(
      WidgetTester tester, {
      required bool disableAnimations,
    }) async {
      await tester.pumpWidget(wrap(
        const SparkleProposalEnter(child: Text('profile target')),
        disableAnimations: disableAnimations,
      ),);
      final frameTimes = <int>[];
      for (var i = 0; i < 60; i++) {
        final sw = Stopwatch()..start();
        await tester.pump(const Duration(milliseconds: 16));
        sw.stop();
        frameTimes.add(sw.elapsedMicroseconds);
      }
      await unwindTree(tester);
      return frameTimes.reduce((a, b) => a + b) / frameTimes.length;
    }

    testWidgets('H+ 动画帧时 < 阈值，且与静态基线同批对照落证', (tester) async {
      final animatedAvgUs =
          await measureFrames(tester, disableAnimations: false);
      final baselineAvgUs =
          await measureFrames(tester, disableAnimations: true);
      // ignore: avoid_print
      print('S01 proposal-enter animated avg frame: '
          '${animatedAvgUs.toStringAsFixed(1)}us');
      // ignore: avoid_print
      print('S01 reduce-motion static baseline avg frame: '
          '${baselineAvgUs.toStringAsFixed(1)}us');
      expect(animatedAvgUs, lessThan(_frameThresholdUs));
      expect(baselineAvgUs, lessThan(_frameThresholdUs));
    }, timeout: const Timeout(Duration(minutes: 2)),);

    testWidgets('H- 控制组：静态基线在航期零 ticker（基线确为静止路径）',
        (tester) async {
      await tester.pumpWidget(wrap(
        const SparkleProposalEnter(child: Text('baseline')),
        disableAnimations: true,
      ),);
      await tester.pump(const Duration(milliseconds: 16));
      expect(tester.binding.transientCallbackCount, 0);
      await unwindTree(tester);
    });
  });
}

/// repeat 控制探针：恒动 ticker（F-/G- 控制组专用，不入 lib）。
class _RepeatProbe extends StatefulWidget {
  const _RepeatProbe();

  @override
  State<_RepeatProbe> createState() => _RepeatProbeState();
}

class _RepeatProbeState extends State<_RepeatProbe>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(seconds: 1));
    unawaited(_controller.repeat());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) =>
      AnimatedBuilder(
        animation: _controller,
        builder: (context, child) => const Text('probe'),
      );
}
