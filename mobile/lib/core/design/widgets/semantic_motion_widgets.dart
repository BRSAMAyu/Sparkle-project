import 'package:flutter/material.dart';
import 'package:sparkle/core/design/semantic_motion.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';

/// V4-S01 · 语义乐谱动效组件族（提案出现 / 回执替换 / 证据印章）。
///
/// 乐谱三行的视觉实现（`v4/02_design/MOTION_AUDIO_HAPTICS.md` 事件乐谱）：
///
/// - [SparkleProposalEnter] —「提案出现：160–220ms 从纸面抬起」；
/// - [SparkleReceiptSwap] —「写入提交成功：标题/状态 160ms 替换」；
/// - [SparkleEvidenceStamp] —「证据已登记：小印章 160ms」。
///
/// 族纪律（每条有测试钉死）：
///
/// 1. **全 implicit 一次性动画**：无 AnimationController、无 `repeat`、
///    无完成回调——取消（卸载/换内容）即消失，不残留后台 ticker；
///    落定后不再调度帧（滚动正文不降帧的组件面前提）。
/// 2. **reduce-motion 静态分支**：`context.reduceMotion`（MediaQuery 双源
///    并集，F06 统一口径）命中时**不装动画壳**直落终态——等价信息不丢失
///    （提案完整可见/替换即时完成/印章全尺寸呈现）；**不通配 Duration.zero**
///    （V3-FIX-374 零时长 AnimatedSize 崩溃面在分支前就不存在）。
/// 3. **零粒子零声触**：本族不发射粒子（GlobalParticleCounter 零占用）、
///    不发声/震（唯一感官出口 = F03 ExperienceFeedbackAdapter）；
///    证据印章不庆祝（文字不说已掌握）。
/// 4. **预算单源**：时长一律取 [kSparkleSemanticMotionBudgets]（语义乐谱
///    机器表，semantic_motion.dart），组件不接受自由 Duration。

/// 提案出现：从纸面抬起（乐谱 160–220ms，预算表落点 200ms）。
///
/// 一次性入场：TweenAnimationBuilder 首建从 begin 播到 end；同 tween 重建
/// **不重播**（内容刷新由调用方换 key/新实例承担）。无完成回调——取消
/// （卸载）即消失，不残留任何在航状态。
class SparkleProposalEnter extends StatelessWidget {
  const SparkleProposalEnter({
    required this.child,
    super.key,
    this.budgets = kSparkleSemanticMotionBudgets,
  });

  final Widget child;
  final SparkleSemanticMotionBudgets budgets;

  @override
  Widget build(BuildContext context) {
    // 静态分支：减弱动效 → 提案完整呈现（等价信息不丢失）。
    if (context.reduceMotion) {
      return child;
    }
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0, end: 1),
      duration: budgets.proposalEnter,
      curve: Curves.easeOut,
      builder: (context, t, child) => Opacity(
        opacity: t.clamp(0.0, 1.0),
        child: Transform.translate(
          offset: Offset(0, (1 - t) * 10), // 抬起 10dp 落定
          child: child,
        ),
      ),
      child: child,
    );
  }
}

/// 回执替换：标题/状态 160ms 替换（乐谱「写入提交成功」行）。
///
/// 重播抑制的运动面（卡验收「cancel/replay 不重播成功」）：
///
/// - [replacementKey] 锚定一次回执（建议 = experience event_id）；
/// - key **变化** → 新内容一次 160ms 淡入替换；
/// - key **相同**（恢复重放/重复投递）→ 不重启动画，不重播替换；
/// - **首挂载不播替换**（初始内容不是回执，直落终态）；
/// - 文本状态仍恢复：调用方直接换 [child]，本组件只承载运动不截留内容。
///
/// 取消面：换成取消/错误内容 = 普通 key 变化替换，**无成功庆祝载体**
/// （本组件不含任何成功徽章/声触——成功面孔归 F03 适配器与 PixelSuccessBadge）。
class SparkleReceiptSwap extends StatefulWidget {
  const SparkleReceiptSwap({
    required this.replacementKey,
    required this.child,
    super.key,
    this.budgets = kSparkleSemanticMotionBudgets,
  });

  final Object replacementKey;
  final Widget child;
  final SparkleSemanticMotionBudgets budgets;

  @override
  State<SparkleReceiptSwap> createState() => _SparkleReceiptSwapState();
}

class _SparkleReceiptSwapState extends State<SparkleReceiptSwap> {
  int _swapTick = 0;

  @override
  void didUpdateWidget(covariant SparkleReceiptSwap oldWidget) {
    super.didUpdateWidget(oldWidget);
    // 仅 key 变化推进替换代际；同 key 重投（重放）不推进 → 不重播。
    if (widget.replacementKey != oldWidget.replacementKey) {
      _swapTick++;
    }
  }

  @override
  Widget build(BuildContext context) {
    // 静态分支：减弱动效 → 即时替换（文本状态恢复不延迟、不丢失）。
    if (context.reduceMotion) {
      return widget.child;
    }
    // 首挂载（_swapTick == 0）：初始内容直落终态，不播替换动画。
    if (_swapTick == 0) {
      return widget.child;
    }
    return TweenAnimationBuilder<double>(
      // key 换代 = 重启一次替换动画；同代重建 tween 不变 → 不重播。
      key: ValueKey<int>(_swapTick),
      tween: Tween<double>(begin: 0, end: 1),
      duration: widget.budgets.receiptReplace,
      curve: Curves.easeOut,
      builder: (context, t, child) =>
          Opacity(opacity: t.clamp(0.0, 1.0), child: child),
      child: widget.child,
    );
  }
}

/// 证据已登记：小印章 160ms（乐谱「证据已登记」行；文字不说已掌握）。
///
/// 印章落定 = 轻微从大到小压印（1.12 → 1.0）+ 淡入，一次完成；零粒子、
/// 零声触（声触可选面归 F03 出口）。乐谱「独立检验通过」的星点连线里程碑
/// （≤650ms 可跳过）由既有 PixelSuccessBadge 承载（V4-F06 已含静态分支），
/// 本族不造第二里程碑载体。
class SparkleEvidenceStamp extends StatelessWidget {
  const SparkleEvidenceStamp({
    required this.child,
    super.key,
    this.budgets = kSparkleSemanticMotionBudgets,
  });

  final Widget child;
  final SparkleSemanticMotionBudgets budgets;

  @override
  Widget build(BuildContext context) {
    // 静态分支：减弱动效 → 印章全尺寸即时呈现。
    if (context.reduceMotion) {
      return child;
    }
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0, end: 1),
      duration: budgets.evidenceStamp,
      curve: Curves.easeOut,
      builder: (context, t, child) => Opacity(
        opacity: t.clamp(0.0, 1.0),
        child: Transform.scale(
          scale: 1.12 - (0.12 * t), // 1.12 → 1.00 压印落定
          child: child,
        ),
      ),
      child: child,
    );
  }
}
