import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';
import 'package:sparkle/core/design/tokens_v2/responsive_system.dart';
import 'package:sparkle/core/design/tokens_v2/animation_token.dart';

/// Sparkle Button V2 - 原子组件
///
/// 特性：
/// - 完全类型安全
/// - 响应式设计
/// - 无障碍支持
/// - 动画集成
/// - 主题感知
class SparkleButton extends StatelessWidget {
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

  const SparkleButton({
    required this.label, super.key,
    this.onPressed,
    this.variant = ButtonVariant.primary,
    this.size = ButtonSize.medium,
    this.icon,
    this.loading = false,
    this.disabled = false,
    this.expand = false,
    this.semanticLabel,
    this.focusNode,
  });

  /// 工厂构造函数 - 便捷变体
  factory SparkleButton.primary({
    required String label,
    required VoidCallback onPressed,
    Widget? icon,
    bool loading = false,
    bool expand = false,
  }) {
    return SparkleButton(
      label: label,
      onPressed: onPressed,
      variant: ButtonVariant.primary,
      icon: icon,
      loading: loading,
      expand: expand,
    );
  }

  factory SparkleButton.secondary({
    required String label,
    required VoidCallback onPressed,
    Widget? icon,
    bool expand = false,
  }) {
    return SparkleButton(
      label: label,
      onPressed: onPressed,
      variant: ButtonVariant.secondary,
      icon: icon,
      expand: expand,
    );
  }

  factory SparkleButton.outline({
    required String label,
    required VoidCallback onPressed,
    Widget? icon,
    bool expand = false,
  }) {
    return SparkleButton(
      label: label,
      onPressed: onPressed,
      variant: ButtonVariant.outline,
      icon: icon,
      expand: expand,
    );
  }

  factory SparkleButton.ghost({
    required String label,
    required VoidCallback onPressed,
    Widget? icon,
    bool expand = false,
  }) {
    return SparkleButton(
      label: label,
      onPressed: onPressed,
      variant: ButtonVariant.ghost,
      icon: icon,
      expand: expand,
    );
  }

  factory SparkleButton.destructive({
    required String label,
    required VoidCallback onPressed,
    Widget? icon,
    bool expand = false,
  }) {
    return SparkleButton(
      label: label,
      onPressed: onPressed,
      variant: ButtonVariant.destructive,
      icon: icon,
      expand: expand,
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = ThemeManager().current;
    final info = ResponsiveSystem.getBreakpointInfo(context);

    return Semantics(
      label: semanticLabel ?? label,
      button: true,
      enabled: !disabled && onPressed != null,
      child: AnimatedContainer(
        duration: theme.animations.quick,
        curve: Curves.easeOut,
        child: Material(
          color: _getBackgroundColor(theme.colors, info),
          borderRadius: _getBorderRadius(theme.spacing, info),
          elevation: _getElevation(info),
          shadowColor: _getShadowColor(theme.colors, info),
          child: InkWell(
            onTap: disabled || loading ? null : onPressed,
            borderRadius: _getBorderRadius(theme.spacing, info),
            focusNode: focusNode,
            child: Container(
              width: expand ? double.infinity : null,
              padding: _getPadding(theme.spacing, info),
              child: Row(
                mainAxisSize: expand ? MainAxisSize.max : MainAxisSize.min,
                mainAxisAlignment: expand ? MainAxisAlignment.center : MainAxisAlignment.start,
                children: _buildChildren(theme, info),
              ),
            ),
          ),
        ),
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
      children.add(SizedBox(width: theme.spacing.sm));
    }

    children.add(
      Text(
        label,
        style: _getTextStyle(theme, info),
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
        return Colors.transparent;
      case ButtonVariant.ghost:
        return colors.surfacePrimary.withOpacity(0.1);
      case ButtonVariant.destructive:
        return colors.semanticError;
    }
  }

  Color _getTextColor(SparkleColors colors) {
    if (disabled) return colors.textDisabled;

    switch (variant) {
      case ButtonVariant.primary:
      case ButtonVariant.secondary:
      case ButtonVariant.destructive:
        return DS.brandPrimary;
      case ButtonVariant.outline:
      case ButtonVariant.ghost:
        return colors.brandPrimary;
    }
  }

  Color _getShadowColor(SparkleColors colors, BreakpointInfo info) {
    if (disabled) return Colors.transparent;
    return colors.textPrimary.withOpacity(0.1);
  }

  double _getElevation(BreakpointInfo info) {
    if (disabled) return 0;
    if (info.isDesktop) return 2;
    return 1;
  }

  BorderRadius _getBorderRadius(SpacingSystem spacing, BreakpointInfo info) {
    final base = spacing.sm;
    return BorderRadius.circular(base);
  }

  EdgeInsets _getPadding(SpacingSystem spacing, BreakpointInfo info) {
    final vertical = spacing.scale(info.context, base: spacing.sm);
    final horizontal = spacing.scale(info.context, base: spacing.lg);

    switch (size) {
      case ButtonSize.small:
        return EdgeInsets.symmetric(
          horizontal: spacing.md,
          vertical: spacing.xs,
        );
      case ButtonSize.medium:
        return EdgeInsets.symmetric(
          horizontal: horizontal,
          vertical: vertical,
        );
      case ButtonSize.large:
        return EdgeInsets.symmetric(
          horizontal: spacing.xl,
          vertical: spacing.md,
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
    final scaleFactor = ResponsiveSystem.scale(info.context, 1.0, min: 0.9, max: 1.2);
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
}

enum ButtonSize {
  small,
  medium,
  large,
}

/// 按钮组 - 用于表单或操作集合
class SparkleButtonGroup extends StatelessWidget {
  final List<SparkleButton> buttons;
  final Axis direction;
  final MainAxisAlignment mainAxisAlignment;
  final MainAxisSize mainAxisSize;
  final double spacing;

  const SparkleButtonGroup({
    required this.buttons, super.key,
    this.direction = Axis.horizontal,
    this.mainAxisAlignment = MainAxisAlignment.start,
    this.mainAxisSize = MainAxisSize.max,
    this.spacing = 8.0,
  });

  @override
  Widget build(BuildContext context) {
    final children = <Widget>[];
    for (int i = 0; i < buttons.length; i++) {
      children.add(buttons[i]);
      if (i < buttons.length - 1) {
        children.add(SizedBox(
          width: direction == Axis.horizontal ? spacing : 0,
          height: direction == Axis.vertical ? spacing : 0,
        ),);
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
class SparkleIconButton extends StatelessWidget {
  final Widget icon;
  final VoidCallback? onPressed;
  final ButtonVariant variant;
  final double size;
  final bool disabled;
  final String? semanticLabel;

  const SparkleIconButton({
    required this.icon, super.key,
    this.onPressed,
    this.variant = ButtonVariant.primary,
    this.size = 48.0,
    this.disabled = false,
    this.semanticLabel,
  });

  @override
  Widget build(BuildContext context) {
    final theme = ThemeManager().current;

    return Semantics(
      label: semanticLabel,
      button: true,
      enabled: !disabled && onPressed != null,
      child: Material(
        color: _getBackgroundColor(theme.colors),
        borderRadius: BorderRadius.circular(size / 2),
        child: InkWell(
          onTap: disabled ? null : onPressed,
          borderRadius: BorderRadius.circular(size / 2),
          child: Container(
            width: size,
            height: size,
            alignment: Alignment.center,
            child: IconTheme(
              data: IconThemeData(
                color: _getTextColor(theme.colors),
                size: size * 0.5,
              ),
              child: icon,
            ),
          ),
        ),
      ),
    );
  }

  Color _getBackgroundColor(SparkleColors colors) {
    if (disabled) return colors.surfaceTertiary;
    switch (variant) {
      case ButtonVariant.primary:
        return colors.brandPrimary;
      case ButtonVariant.secondary:
        return colors.brandSecondary;
      case ButtonVariant.outline:
        return Colors.transparent;
      case ButtonVariant.ghost:
        return colors.surfacePrimary.withOpacity(0.1);
      case ButtonVariant.destructive:
        return colors.semanticError;
    }
  }

  Color _getTextColor(SparkleColors colors) {
    if (disabled) return colors.textDisabled;
    switch (variant) {
      case ButtonVariant.primary:
      case ButtonVariant.secondary:
      case ButtonVariant.destructive:
        return DS.brandPrimary;
      case ButtonVariant.outline:
      case ButtonVariant.ghost:
        return colors.brandPrimary;
    }
  }
}

/// 加载按钮 - 自动处理加载状态
class SparkleLoadingButton extends StatefulWidget {
  final String label;
  final Future<void> Function() onPressed;
  final ButtonVariant variant;
  final ButtonSize size;
  final Widget? icon;
  final Widget? loadingIcon;
  final String? semanticLabel;

  const SparkleLoadingButton({
    required this.label, required this.onPressed, super.key,
    this.variant = ButtonVariant.primary,
    this.size = ButtonSize.medium,
    this.icon,
    this.loadingIcon,
    this.semanticLabel,
  });

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
  Widget build(BuildContext context) {
    return SparkleButton(
      label: widget.label,
      onPressed: _loading ? null : _handlePressed,
      variant: widget.variant,
      size: widget.size,
      icon: _loading ? (widget.loadingIcon ?? const SizedBox.shrink()) : widget.icon,
      loading: _loading,
      semanticLabel: widget.semanticLabel,
    );
  }
}
