/// V4-F02 · 像素状态族——取消 / unknown / conflict / 失败 / 成功 的
/// 统一语义映射（DESIGN_SYSTEM.md「主题和状态」：相同状态在任意页面
/// 有相同语义；错误、撤回和未知不能用庆祝视觉）。
///
/// 状态的视觉区分 = **令牌槽 + 字形 + 轮廓形状 + 动效** 四元组
/// （[PixelStateSpec]），全部由既有语义槽（semanticError/semanticWarning/
/// textSecondary/semanticSuccess）解析，不新增颜色字面量：
///
/// | state    | 令牌槽            | 字形              | 轮廓       | 动效 |
/// |----------|-------------------|-------------------|------------|------|
/// | cancelled| line（中性描边）  | 禁止圆（斜杠圆）  | 单线       | 无 |
/// | unknown  | textSecondary     | 问号圈            | 虚线       | 无 |
/// | conflict | semanticWarning   | 分叉箭头          | 双线加粗   | 无 |
/// | failed   | semanticError     | 叉（close）       | 实心切角   | 无 |
/// | success  | semanticSuccess   | 对勾（唯一庆祝）  | 实心切角   | 上升（唯一） |
///
/// 红线：[PixelStateSpec.celebrates] 只有 success 为 true；非成功态
/// **绝不**渲染 [PixelSuccessBadge]（成功动效元素），由反例测试钉死。
library;

import 'dart:async' show unawaited;
import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'package:sparkle/core/design/design_system.dart';

/// 像素状态族（含成功对照态；非成功四态 = 卡面验收 2 的覆盖面）。
enum PixelRunState { cancelled, unknown, conflict, failed, success }

/// 状态四元组（令牌槽解析键 / 字形 / 轮廓 / 是否庆祝动效）。
@immutable
class PixelStateSpec {
  const PixelStateSpec._({
    required this.state,
    required this.label,
    required this.icon,
    required this.outline,
    required this.celebrates,
    required this.colorOf,
  });

  /// 中文短标签（屏幕阅读器直接读，同义权威 = DESIGN_SYSTEM.md 状态语义）。
  final String label;

  /// 字形（Material 图标 = 系统矢量渲染，非位图，不点阵化）。
  final IconData icon;

  /// 状态轮廓处理（非成功态互异；success 复用 failed 的实心切角底，
  /// 但令牌槽/字形/动效不同——四元组整体区分）。
  final PixelStateOutline outline;

  /// 是否庆祝动效（成功上升动效）。**只有 success 为 true**。
  final bool celebrates;

  /// 令牌槽解析（从 context.colors 取既有语义槽，无第二色源）。
  final Color Function(SparkleColors colors) colorOf;

  final PixelRunState state;

  /// 状态 → 四元组（唯一事实源；badge/card/story 全走这里）。
  static PixelStateSpec forState(PixelRunState state) => switch (state) {
        PixelRunState.cancelled => const PixelStateSpec._(
            state: PixelRunState.cancelled,
            label: '已取消',
            icon: Icons.block,
            outline: PixelStateOutline.singleLine,
            celebrates: false,
            colorOf: _lineColor,
          ),
        PixelRunState.unknown => const PixelStateSpec._(
            state: PixelRunState.unknown,
            label: '结果未知',
            icon: Icons.help_outline,
            outline: PixelStateOutline.dashed,
            celebrates: false,
            colorOf: _secondaryColor,
          ),
        PixelRunState.conflict => const PixelStateSpec._(
            state: PixelRunState.conflict,
            label: '版本冲突',
            icon: Icons.call_split,
            outline: PixelStateOutline.doubleLine,
            celebrates: false,
            colorOf: _warningColor,
          ),
        PixelRunState.failed => const PixelStateSpec._(
            state: PixelRunState.failed,
            label: '失败',
            icon: Icons.close,
            outline: PixelStateOutline.solidCut,
            celebrates: false,
            colorOf: _errorColor,
          ),
        PixelRunState.success => const PixelStateSpec._(
            state: PixelRunState.success,
            label: '已完成',
            icon: Icons.check,
            outline: PixelStateOutline.solidCut,
            celebrates: true,
            colorOf: _successColor,
          ),
      };

  /// 语义描述（读屏口径：状态 + 标签；错误/未知不用感叹语气，不庆祝）。
  String get semanticsLabel => label;
}

/// 状态轮廓处理（形状区分维；Classic 全部降级为 none=标准描边）。
enum PixelStateOutline {
  /// 单线（cancelled：中性）。
  singleLine,

  /// 虚线（unknown：边界不确定性可视化）。
  dashed,

  /// 双线加粗（conflict：两版本并存的视觉提示）。
  doubleLine,

  /// 实心底 + 切角（failed/success：终态强调）。
  solidCut,

  /// classic 降级：标准单线，无像素形状特色（行为零差量口径）。
  none,
}

Color _lineColor(SparkleColors c) => c.neutral300;
Color _secondaryColor(SparkleColors c) => c.textSecondary;
Color _warningColor(SparkleColors c) => c.semanticWarning;
Color _errorColor(SparkleColors c) => c.semanticError;
Color _successColor(SparkleColors c) => c.semanticSuccess;

/// 状态令牌解析结果（badge 渲染输入；classic 时 outline 降级 none）。
@immutable
class PixelStateVisual {
  const PixelStateVisual({
    required this.spec,
    required this.color,
    required this.outline,
  });

  final PixelStateSpec spec;
  final Color color;
  final PixelStateOutline outline;

  /// 从 context 解析（像素档取轮廓特色；classic 降级标准单线——
  /// 发布面红线：classic 行为零差量，无像素特色但不破）。
  static PixelStateVisual of(BuildContext context, PixelRunState state) {
    final spec = PixelStateSpec.forState(state);
    final colors = context.sparkleTheme.colors;
    final ext = PixelProfileTheme.of(context);
    return PixelStateVisual(
      spec: spec,
      color: spec.colorOf(colors),
      outline: ext == null ? PixelStateOutline.none : spec.outline,
    );
  }
}

/// 状态徽章：字形 + 短标签 + Semantics（读屏可定位；不做庆祝动效）。
///
/// 动效纪律：非成功态静态呈现（无上升/无脉冲）；success 的庆祝动效由
/// [PixelSuccessBadge] 单独承载——本组件按 spec.celebrates 分流，
/// 反例测试断言非成功树中不存在 PixelSuccessBadge。
class PixelStateBadge extends StatelessWidget {
  const PixelStateBadge({
    required this.state, super.key,
    this.dense = false,
  });

  final PixelRunState state;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final visual = PixelStateVisual.of(context, state);
    // 庆祝动效唯一载体：success 徽章整体委托给 PixelSuccessBadge
    // （反例测试按类型钉死非成功树中不得出现该类型）。
    if (visual.spec.celebrates) {
      return PixelSuccessBadge(dense: dense);
    }
    final typo = context.sparkleTheme.typography;
    final badge = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(visual.spec.icon, size: dense ? 14 : 18, color: visual.color),
        const SizedBox(width: DS.xs),
        Text(
          visual.spec.label,
          style: (dense ? typo.labelSmall : typo.labelLarge).copyWith(
            color: visual.color,
          ),
        ),
      ],
    );
    final content = visual.outline == PixelStateOutline.dashed
        ? _DashedChipBorder(color: visual.color, child: badge)
        : Padding(
            padding: EdgeInsets.symmetric(
              horizontal: DS.xs,
              vertical: dense ? 0 : DS.xs,
            ),
            child: badge,
          );
    return Semantics(
      container: true,
      label: visual.spec.semanticsLabel,
      // 子树装饰/文本不入语义（显式 label 即完整读屏内容，不重复拼接）。
      child: ExcludeSemantics(child: content),
    );
  }
}

/// unknown 的虚线芯片边（装饰层，IgnorePointer 不吞手势；形状区分维）。
class _DashedChipBorder extends StatelessWidget {
  const _DashedChipBorder({required this.color, required this.child});

  final Color color;
  final Widget child;

  @override
  Widget build(BuildContext context) => CustomPaint(
      foregroundPainter: _DashedRectPainter(color: color),
      // 装饰不参与命中（验收 3）；CustomPaint 绘制本身不入语义树
      // （语义由外层 PixelStateBadge 的 Semantics 容器承载）。
      child: IgnorePointer(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: DS.xs, vertical: DS.xs),
          child: child,
        ),
      ),
    );
}

class _DashedRectPainter extends CustomPainter {
  _DashedRectPainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.fill
      ..color = color;
    const dash = 3.0;
    const gap = 2.0;

    // 水平边：dash 沿 x 展开、厚 1；竖直边：dash 沿 y 展开、宽 1。
    void drawDashes(bool vertical, double fixedCoord, double len) {
      for (var t = 0.0; t < len; t += dash + gap) {
        final d = math.min(dash, len - t);
        final rect = vertical
            ? Rect.fromLTWH(fixedCoord, t, 1, d)
            : Rect.fromLTWH(t, fixedCoord, d, 1);
        canvas.drawRect(rect, paint);
      }
    }

    drawDashes(false, 0, size.width);
    drawDashes(false, size.height - 1, size.width);
    drawDashes(true, 0, size.height);
    drawDashes(true, size.width - 1, size.height);
  }

  @override
  bool shouldRepaint(_DashedRectPainter oldDelegate) =>
      oldDelegate.color != color;
}

/// 成功徽章（唯一允许的庆祝动效载体：上升 + 对勾浮现）。
///
/// 独立类型即反例锚点：非成功态的组件树中**不得**出现本类型
/// （test/core/design/pixel/ 反例钉死）。
class PixelSuccessBadge extends StatefulWidget {
  const PixelSuccessBadge({super.key, this.dense = false});

  final bool dense;

  @override
  State<PixelSuccessBadge> createState() => _PixelSuccessBadgeState();
}

class _PixelSuccessBadgeState extends State<PixelSuccessBadge>
    with SingleTickerProviderStateMixin {
  AnimationController? _controller;
  Animation<double>? _rise;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_controller == null) {
      final motion = PixelProfileTheme.of(context)?.stateMotion;
      final controller = AnimationController(
        vsync: this,
        duration: motion?.milestoneMax ?? const Duration(milliseconds: 650),
      );
      _rise = CurvedAnimation(parent: controller, curve: Curves.easeOutCubic);
      _controller = controller;
      unawaited(controller.forward());
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.sparkleTheme.colors;
    final typo = context.sparkleTheme.typography;
    final color = colors.semanticSuccess;
    return Semantics(
      container: true,
      label: '已完成',
      // 子树文本不入语义（读屏内容 = 显式 label，不重复拼接）。
      child: ExcludeSemantics(
        child: AnimatedBuilder(
          animation: _rise!,
          builder: (context, child) => Opacity(
            opacity: _rise!.value.clamp(0.0, 1.0),
            child: Transform.translate(
              offset: Offset(0, (1 - _rise!.value) * 6),
              child: child,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.check_circle, size: widget.dense ? 14 : 18,
                  color: color,),
              const SizedBox(width: DS.xs),
              Text(
                '已完成',
                style: (widget.dense ? typo.labelSmall : typo.labelLarge)
                    .copyWith(color: color),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
