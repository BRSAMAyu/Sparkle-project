import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/theme_utils.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';

/// Sparkle Button V2 - 原子组件
///
/// 特性：
/// - 完全类型安全
/// - 响应式设计
/// - 无障碍支持
/// - 动画集成
/// - 主题感知
class SparkleButton extends StatelessWidget {
  const SparkleButton({
    required this.label,
    super.key,
    this.onPressed,
    this.variant = ButtonVariant.primary,
    this.size = ButtonSize.medium,
    this.icon,
    this.loading = false,
    this.disabled = false,
    this.expand = false,
    this.semanticLabel,
    this.focusNode,
    this.minWidth,
    this.minHeight,
    this.borderSide,
    this.foregroundColor,
    this.backgroundGradient,
  });

  /// 工厂构造函数 - 便捷变体
  factory SparkleButton.primary({
    required String label,
    required VoidCallback onPressed,
    Key? key,
    Widget? icon,
    bool loading = false,
    bool expand = false,
  }) =>
      SparkleButton(
        key: key,
        label: label,
        onPressed: onPressed,
        icon: icon,
        loading: loading,
        expand: expand,
      );

  factory SparkleButton.secondary({
    required String label,
    required VoidCallback onPressed,
    Key? key,
    Widget? icon,
    bool expand = false,
  }) =>
      SparkleButton(
        key: key,
        label: label,
        onPressed: onPressed,
        variant: ButtonVariant.secondary,
        icon: icon,
        expand: expand,
      );

  factory SparkleButton.outline({
    required String label,
    required VoidCallback onPressed,
    Key? key,
    Widget? icon,
    bool expand = false,
  }) =>
      SparkleButton(
        key: key,
        label: label,
        onPressed: onPressed,
        variant: ButtonVariant.outline,
        icon: icon,
        expand: expand,
      );

  factory SparkleButton.ghost({
    required String label,
    required VoidCallback onPressed,
    Key? key,
    Widget? icon,
    bool expand = false,
  }) =>
      SparkleButton(
        key: key,
        label: label,
        onPressed: onPressed,
        variant: ButtonVariant.ghost,
        icon: icon,
        expand: expand,
      );

  factory SparkleButton.destructive({
    required String label,
    required VoidCallback onPressed,
    Key? key,
    Widget? icon,
    bool expand = false,
  }) =>
      SparkleButton(
        key: key,
        label: label,
        onPressed: onPressed,
        variant: ButtonVariant.destructive,
        icon: icon,
        expand: expand,
      );
  final String label;
  final VoidCallback? onPressed;
  final ButtonVariant variant;
  final ButtonSize size;
  final Widget? icon;
  final bool loading;
  final bool disabled;
  final bool expand;
  final String? semanticLabel;
  final FocusNode? focusNode;

  /// 最小宽度下限（默认 null = 不约束，保持历史行为）。
  /// 迁移 M3 按钮（minimumSize 64x40）等场景时用于命中区/布局等价。
  final double? minWidth;

  /// 最小高度下限（默认 null = 不约束，保持历史行为）。
  /// 迁移 M3 按钮（视觉高 40）等场景时用于布局高度等价。
  final double? minHeight;

  /// 描边（默认 null = 无描边，保持历史行为）。
  /// 迁移 OutlinedButton / CustomButton.secondary（2px 边框）时传入。
  final BorderSide? borderSide;

  /// 前景（文字/图标）色覆盖（默认 null = 按 variant 取色，保持历史行为）。
  /// 迁移带语义色文字的按钮（如 destructive 文字动作）时传入；disabled 态仍取 [SparkleColors.textDisabled]。
  final Color? foregroundColor;

  /// 背景渐变覆盖（默认 null = variant 纯色背景，保持历史行为）。
  /// 承接历史渐变 CTA（决策确认/行动卡）时传入原渐变对象；disabled 态仍用 surfaceTertiary 纯色。
  final Gradient? backgroundGradient;

  void _handlePressed() {
    if (disabled || loading || onPressed == null) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
    onPressed?.call();
  }

  @override
  Widget build(BuildContext context) {
    final theme = context.sparkleTheme;
    final info = context.breakpointInfo;
    final hasMinSize = minWidth != null || minHeight != null;
    final useGradient = backgroundGradient != null && !disabled;

    final Widget ink = InkWell(
      onTap: disabled || loading ? null : _handlePressed,
      borderRadius: _getBorderRadius(info),
      focusNode: focusNode,
        child: Container(
          width: expand ? double.infinity : null,
          padding: _getPadding(info),
          constraints: hasMinSize
              ? BoxConstraints(
                  minWidth: minWidth ?? 0,
                  minHeight: minHeight ?? 0,
                )
              : null,
          child: Row(
            mainAxisSize: expand ? MainAxisSize.max : MainAxisSize.min,
            mainAxisAlignment:
                expand ? MainAxisAlignment.center : MainAxisAlignment.start,
            children: _buildChildren(theme, info),
          ),
        ),
    );

    final button = useGradient
        ? DecoratedBox(
            decoration: BoxDecoration(
              gradient: backgroundGradient,
              borderRadius: _getBorderRadius(info),
              boxShadow: [
                BoxShadow(
                  color: _getShadowColor(theme.colors, info),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Material(
              color: theme.colors.surfacePrimary.withValues(alpha: 0),
              child: ink,
            ),
          )
        : Material(
            color: _getBackgroundColor(theme.colors, info),
            shape: borderSide == null
                ? null
                : RoundedRectangleBorder(
                    borderRadius: _getBorderRadius(info),
                    side: borderSide!,
                  ),
            borderRadius:
                borderSide == null ? _getBorderRadius(info) : null,
            elevation:
                variant == ButtonVariant.text ? 0 : _getElevation(info),
            shadowColor: _getShadowColor(theme.colors, info),
            child: ink,
          );

    return Semantics(
      label: semanticLabel ?? label,
      button: true,
      enabled: !disabled && onPressed != null,
      child: AnimatedContainer(
        duration: theme.animations.quick,
        curve: Curves.easeOut,
        child: button,
      ),
    );
  }

  List<Widget> _buildChildren(SparkleThemeData theme, BreakpointInfo info) {
    final children = <Widget>[];

    if (loading) {
      children.add(
        SizedBox(
          width: _getIconSize(info),
          height: _getIconSize(info),
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation(_getTextColor(theme.colors)),
          ),
        ),
      );
    } else if (icon != null) {
      children.add(
        IconTheme(
          data: IconThemeData(
            color: _getTextColor(theme.colors),
            size: _getIconSize(info),
          ),
          child: icon!,
        ),
      );
    }

    if (icon != null || loading) {
      children.add(const SizedBox(width: DS.sm));
    }

    children.add(
      Flexible(
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          softWrap: false,
          style: _getTextStyle(theme, info),
        ),
      ),
    );

    return children;
  }

  Color _getBackgroundColor(SparkleColors colors, BreakpointInfo info) {
    if (disabled) return colors.surfaceTertiary;

    switch (variant) {
      case ButtonVariant.primary:
        return colors.brandPrimary;
      case ButtonVariant.secondary:
        return colors.brandSecondary;
      case ButtonVariant.outline:
      case ButtonVariant.text:
        return colors.surfacePrimary.withValues(alpha: 0);
      case ButtonVariant.ghost:
        return colors.surfacePrimary.withValues(alpha: 0.1);
      case ButtonVariant.destructive:
        return colors.semanticError;
    }
  }

  Color _getTextColor(SparkleColors colors) {
    if (disabled) return colors.textDisabled;
    if (foregroundColor != null) return foregroundColor!;

    switch (variant) {
      case ButtonVariant.primary:
        return ThemeUtils.getContrastSafeText(
          colors.brandPrimary,
          darkText: colors.textPrimary,
        );
      case ButtonVariant.secondary:
        return ThemeUtils.getContrastSafeText(
          colors.brandSecondary,
          darkText: colors.textPrimary,
        );
      case ButtonVariant.destructive:
        return ThemeUtils.getContrastSafeText(
          colors.semanticError,
          darkText: colors.textPrimary,
        );
      case ButtonVariant.outline:
      case ButtonVariant.ghost:
      case ButtonVariant.text:
        return colors.brandPrimary;
    }
  }

  Color _getShadowColor(SparkleColors colors, BreakpointInfo info) {
    if (disabled) return colors.surfacePrimary.withValues(alpha: 0);
    return colors.textPrimary.withValues(alpha: 0.1);
  }

  double _getElevation(BreakpointInfo info) {
    if (disabled) return 0;
    if (info.isDesktop) return 2;
    return 1;
  }

  BorderRadius _getBorderRadius(BreakpointInfo info) {
    const base = DS.sm;
    return BorderRadius.circular(base);
  }

  EdgeInsets _getPadding(BreakpointInfo info) {
    final vertical = ResponsiveSystem.scale(info.context, DS.sm);
    final horizontal = ResponsiveSystem.scale(info.context, DS.lg);

    switch (size) {
      case ButtonSize.small:
        return const EdgeInsets.symmetric(
          horizontal: DS.md,
          vertical: DS.xs,
        );
      case ButtonSize.medium:
        return EdgeInsets.symmetric(
          horizontal: horizontal,
          vertical: vertical,
        );
      case ButtonSize.large:
        return const EdgeInsets.symmetric(
          horizontal: DS.xl,
          vertical: DS.md,
        );
    }
  }

  double _getIconSize(BreakpointInfo info) {
    switch (size) {
      case ButtonSize.small:
        return 16.0;
      case ButtonSize.medium:
        return 20.0;
      case ButtonSize.large:
        return 24.0;
    }
  }

  TextStyle _getTextStyle(SparkleThemeData theme, BreakpointInfo info) {
    final base = theme.typography.labelLarge.copyWith(
      color: _getTextColor(theme.colors),
    );

    // 响应式字体大小
    final scaleFactor =
        ResponsiveSystem.scale(info.context, 1.0, min: 0.9, max: 1.2);
    final adjustedSize = (base.fontSize ?? 14.0) * scaleFactor;

    return base.copyWith(
      fontSize: adjustedSize,
      fontWeight: size == ButtonSize.large ? FontWeight.w600 : FontWeight.w500,
    );
  }
}

enum ButtonVariant {
  primary,
  secondary,
  outline,
  ghost,
  destructive,

  /// 纯文字按钮（透明底、无阴影、brandPrimary 文字）。
  /// 等价承接 M3 TextButton / CustomButton.text 的语义。
  text,
}

enum ButtonSize {
  small,
  medium,
  large,
}

/// 按钮组 - 用于表单或操作集合
class SparkleButtonGroup extends StatelessWidget {
  const SparkleButtonGroup({
    required this.buttons,
    super.key,
    this.direction = Axis.horizontal,
    this.mainAxisAlignment = MainAxisAlignment.start,
    this.mainAxisSize = MainAxisSize.max,
    this.spacing = 8.0,
  });
  final List<SparkleButton> buttons;
  final Axis direction;
  final MainAxisAlignment mainAxisAlignment;
  final MainAxisSize mainAxisSize;
  final double spacing;

  @override
  Widget build(BuildContext context) {
    final children = <Widget>[];
    for (var i = 0; i < buttons.length; i++) {
      children.add(buttons[i]);
      if (i < buttons.length - 1) {
        children.add(
          SizedBox(
            width: direction == Axis.horizontal ? spacing : 0,
            height: direction == Axis.vertical ? spacing : 0,
          ),
        );
      }
    }

    return Flex(
      direction: direction,
      mainAxisAlignment: mainAxisAlignment,
      mainAxisSize: mainAxisSize,
      children: children,
    );
  }
}

/// 图标按钮
///
/// 几何语义（FAB-UNIFY 根治）：组件自带**最大尺寸约束**——默认渲染为
/// `max(size, 触控下限)` 的正方形（48-56 视觉档）。只带 min 约束的历史
/// 实现在 bounded-loose 槽位（如 Scaffold 的 floatingActionButton 槽）
/// 会被拉伸成全屏 InkWell 吞掉整页 tap；现在任何槽位下几何都钉死在
/// 视觉档内，不再依赖调用方自觉包 SizedBox。
///
/// FAB 用途请用 [SparkleIconButton.fabGeometry] 命名构造（56 方档）。
///
/// 语义名（N31 图标钮必有名 / A-SPEC6 AX-G1）：解析顺序——
/// 1. 显式 [semanticLabel]（首选：调用点最懂自己的用途，走 l10n）；
/// 2. **反推**：icon 为 Flutter `Icon` 且自带 `semanticLabel` 时上提为
///    按钮语义名（与视觉标注同一事实源，零新增登记；上提后按钮角色与
///    名字合并在同一语义节点播报，不再出现「无名按钮+内部孤名」）；
/// 3. 两者皆无 → debug 下输出一次登记诊断（非致命）。存量无名钮走
///    登记制清偿（ratchet 只降不升），新调用点在 debug/测试期即可见。
///    不采「强制 required 参数」方案：存量 ~170 处无名调用点跨 ~130 文件，
///    一次编译期铺开破坏面最大（评估记录见 v3-output/A11Y-ICONS/REPORT.md）。
class SparkleIconButton extends ConsumerWidget { // 56

  const SparkleIconButton({
    required this.icon,
    super.key,
    this.onPressed,
    this.variant = ButtonVariant.primary,
    this.size = defaultSize,
    this.disabled = false,
    this.semanticLabel,
    this.constraints,
  });

  /// FAB 用途命名构造：把自身钉死在方形几何（默认 [fabSize] 方档），
  /// Scaffold 的 FAB 槽位（bounded-loose）不可再拉伸。不接受自由
  /// [constraints]——FAB 的方形几何语义不可被调用方放宽。
  const SparkleIconButton.fabGeometry({
    required this.icon,
    super.key,
    this.onPressed,
    this.variant = ButtonVariant.primary,
    this.size = fabSize,
    this.disabled = false,
    this.semanticLabel,
  }) : constraints = null;
  /// 默认（AppBar/工具栏）视觉档。
  static const double defaultSize = DS.touchTargetMinSize; // 48

  /// FAB 视觉档（48 触控档 + 8 间距 = 56 方档）。
  static const double fabSize = DS.touchTargetMinSize + DS.spacing8;

  final Widget icon;
  final VoidCallback? onPressed;
  final ButtonVariant variant;
  final double size;
  final bool disabled;
  final String? semanticLabel;

  /// 可选：覆盖默认方形几何。仍强制触控下限（a11y 不可破），且不会
  /// 在调用方未显式声明时引入无上限方向——上限语义默认常在。
  final BoxConstraints? constraints;

  BoxConstraints _resolveConstraints(double minTouchTarget) {
    final caller = constraints;
    if (caller != null) {
      final minW = math.max(caller.minWidth, minTouchTarget);
      final minH = math.max(caller.minHeight, minTouchTarget);
      return BoxConstraints(
        minWidth: minW,
        maxWidth: math.max(caller.maxWidth, minW),
        minHeight: minH,
        maxHeight: math.max(caller.maxHeight, minH),
      );
    }
    // 默认：正方形视觉档（min==max → 任何槽位都不变形）。
    final side = math.max(size, minTouchTarget);
    return BoxConstraints(
      minWidth: side,
      maxWidth: side,
      minHeight: side,
      maxHeight: side,
    );
  }

  /// 反推语义名：调用方未显式给 [semanticLabel] 时，从 Flutter `Icon`
  /// 自带的 `semanticLabel` 上提（同一事实源，非第二套命名表）。
  String? get _iconProvidedSemanticLabel {
    final iconWidget = icon;
    if (iconWidget is Icon) {
      return iconWidget.semanticLabel;
    }
    return null;
  }

  /// N31 登记守卫（debug-only，非致命）：无名 icon-only 钮在 debug/测试期
  /// 输出一次诊断——存量走登记制清偿，新增破口当场可见。assert 块在
  /// release/profile 整体剔除，零生产开销。
  void _debugReportUnnamedLabel(String? effectiveLabel) {
    assert(() {
      if (effectiveLabel != null) {
        return true;
      }
      final iconWidget = icon;
      final codePoint = iconWidget is Icon && iconWidget.icon != null
          ? '0x${iconWidget.icon!.codePoint.toRadixString(16)}'
          : 'custom';
      debugPrint(
        'SparkleIconButton (N31 a11y): icon-only button without semanticLabel '
        '(icon: $codePoint). Add semanticLabel (l10n) so screen readers can '
        'announce the button purpose.',
      );
      return true;
    }());
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = context.sparkleTheme;
    final accessibility = ref.watch(accessibilitySettingsProvider);
    final minTouchTarget = accessibility.isLoaded
        ? accessibility.minimumTouchTargetSize
        : DS.touchTargetMinSize;
    final geometry = _resolveConstraints(minTouchTarget);
    final visualSide = math.max(size, minTouchTarget);

    // N31 语义名解析：显式 semanticLabel > icon 自带 semanticLabel（反推）。
    final effectiveLabel = semanticLabel ?? _iconProvidedSemanticLabel;
    _debugReportUnnamedLabel(effectiveLabel);

    return Semantics(
      label: effectiveLabel,
      button: true,
      enabled: !disabled && onPressed != null,
      child: Material(
        color: _getBackgroundColor(theme.colors),
        borderRadius: BorderRadius.circular(visualSide / 2),
        child: InkWell(
          onTap: disabled
              ? null
              : () {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.tap),
                  );
                  onPressed?.call();
                },
          borderRadius: BorderRadius.circular(visualSide / 2),
          child: Container(
            constraints: geometry,
            alignment: Alignment.center,
            child: IconTheme(
              data: IconThemeData(
                color: _getTextColor(theme.colors),
                size: size * 0.5,
              ),
              child: _resolveIconWidget(),
            ),
          ),
        ),
      ),
    );
  }

  /// 反推生效时把 Icon 自带的 semanticLabel 置空：标签已由按钮级 Semantics
  /// 承载（显式或反推上提），Icon 级残留会在扁平化时拼串/重复播报
  /// （widget test 实测：「返回\n返回」导致 bySemanticsLabel 精确匹配失败）。
  /// effectiveLabel 为空时 Icon 必无自带标签（否则已反推），透传等价。
  Widget _resolveIconWidget() {
    final iconWidget = icon;
    if (iconWidget is Icon) {
      return Icon(
        iconWidget.icon,
        size: iconWidget.size,
        fill: iconWidget.fill,
        weight: iconWidget.weight,
        grade: iconWidget.grade,
        opticalSize: iconWidget.opticalSize,
        color: iconWidget.color,
        shadows: iconWidget.shadows,
        textDirection: iconWidget.textDirection,
      );
    }
    return icon;
  }

  Color _getBackgroundColor(SparkleColors colors) {
    if (disabled) return colors.surfaceTertiary;
    switch (variant) {
      case ButtonVariant.primary:
        return colors.brandPrimary;
      case ButtonVariant.secondary:
        return colors.brandSecondary;
      case ButtonVariant.outline:
      case ButtonVariant.text:
        return colors.surfacePrimary.withValues(alpha: 0);
      case ButtonVariant.ghost:
        return colors.surfacePrimary.withValues(alpha: 0.1);
      case ButtonVariant.destructive:
        return colors.semanticError;
    }
  }

  Color _getTextColor(SparkleColors colors) {
    if (disabled) return colors.textDisabled;
    switch (variant) {
      case ButtonVariant.primary:
        return ThemeUtils.getContrastSafeText(
          colors.brandPrimary,
          darkText: colors.textPrimary,
        );
      case ButtonVariant.secondary:
        return ThemeUtils.getContrastSafeText(
          colors.brandSecondary,
          darkText: colors.textPrimary,
        );
      case ButtonVariant.destructive:
        return ThemeUtils.getContrastSafeText(
          colors.semanticError,
          darkText: colors.textPrimary,
        );
      case ButtonVariant.outline:
      case ButtonVariant.ghost:
      case ButtonVariant.text:
        return colors.brandPrimary;
    }
  }
}

/// 加载按钮 - 自动处理加载状态
class SparkleLoadingButton extends StatefulWidget {
  const SparkleLoadingButton({
    required this.label,
    required this.onPressed,
    super.key,
    this.variant = ButtonVariant.primary,
    this.size = ButtonSize.medium,
    this.icon,
    this.loadingIcon,
    this.semanticLabel,
  });
  final String label;
  final Future<void> Function() onPressed;
  final ButtonVariant variant;
  final ButtonSize size;
  final Widget? icon;
  final Widget? loadingIcon;
  final String? semanticLabel;

  @override
  State<SparkleLoadingButton> createState() => _SparkleLoadingButtonState();
}

class _SparkleLoadingButtonState extends State<SparkleLoadingButton> {
  bool _loading = false;

  Future<void> _handlePressed() async {
    if (_loading) return;

    setState(() => _loading = true);
    try {
      await widget.onPressed();
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => SparkleButton(
        label: widget.label,
        onPressed: _loading ? null : _handlePressed,
        variant: widget.variant,
        size: widget.size,
        icon: _loading
            ? (widget.loadingIcon ?? const SizedBox.shrink())
            : widget.icon,
        loading: _loading,
        semanticLabel: widget.semanticLabel,
      );
}
