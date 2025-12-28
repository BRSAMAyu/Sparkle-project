import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 按钮变体类型
enum ButtonVariant {
  primary, // 主要按钮 - 渐变背景
  secondary, // 次要按钮 - 透明背景 + 边框
  text, // 文字按钮 - 无边框
  icon, // 图标按钮 - 圆形或方形
}

/// 按钮尺寸
enum CustomButtonSize {
  small, // 小 - 32px高度
  medium, // 中 - 48px高度
  large, // 大 - 56px高度
}

/// 自定义按钮组件
///
/// 支持多种变体、尺寸和状态，具有精致的视觉效果和流畅的动画
class CustomButton extends StatefulWidget {

  const CustomButton({
    super.key,
    this.text,
    this.icon,
    this.onPressed,
    this.variant = ButtonVariant.primary,
    this.size = CustomButtonSize.medium,
    this.isLoading = false,
    this.isFullWidth = false,
    this.customGradient,
    this.isCircular = true,
  }) : assert(
          text != null || icon != null,
          'Either text or icon must be provided',
        );

  /// 主要按钮工厂构造函数
  factory CustomButton.primary({
    required String text, required VoidCallback? onPressed, Key? key,
    IconData? icon,
    CustomButtonSize size = CustomButtonSize.medium,
    bool isLoading = false,
    bool isFullWidth = false,
    LinearGradient? customGradient,
  }) => CustomButton(
      key: key,
      text: text,
      icon: icon,
      onPressed: onPressed,
      size: size,
      isLoading: isLoading,
      isFullWidth: isFullWidth,
      customGradient: customGradient,
    );

  /// 次要按钮工厂构造函数
  factory CustomButton.secondary({
    required String text, required VoidCallback? onPressed, Key? key,
    IconData? icon,
    CustomButtonSize size = CustomButtonSize.medium,
    bool isLoading = false,
    bool isFullWidth = false,
  }) => CustomButton(
      key: key,
      text: text,
      icon: icon,
      onPressed: onPressed,
      variant: ButtonVariant.secondary,
      size: size,
      isLoading: isLoading,
      isFullWidth: isFullWidth,
    );

  /// 文字按钮工厂构造函数
  factory CustomButton.text({
    required String text, required VoidCallback? onPressed, Key? key,
    IconData? icon,
    CustomButtonSize size = CustomButtonSize.medium,
    bool isLoading = false,
  }) => CustomButton(
      key: key,
      text: text,
      icon: icon,
      onPressed: onPressed,
      variant: ButtonVariant.text,
      size: size,
      isLoading: isLoading,
    );

  /// 图标按钮工厂构造函数
  factory CustomButton.icon({
    required IconData icon, required VoidCallback? onPressed, Key? key,
    CustomButtonSize size = CustomButtonSize.medium,
    bool isLoading = false,
    bool isCircular = true,
  }) => CustomButton(
      key: key,
      icon: icon,
      onPressed: onPressed,
      variant: ButtonVariant.icon,
      size: size,
      isLoading: isLoading,
      isCircular: isCircular,
    );
  /// 按钮文本
  final String? text;

  /// 按钮图标
  final IconData? icon;

  /// 点击回调
  final VoidCallback? onPressed;

  /// 按钮变体
  final ButtonVariant variant;

  /// 按钮尺寸
  final CustomButtonSize size;

  /// 是否加载中
  final bool isLoading;

  /// 是否全宽
  final bool isFullWidth;

  /// 自定义渐变（仅适用于primary变体）
  final LinearGradient? customGradient;

  /// 图标按钮形状（仅适用于icon变体）
  final bool isCircular;

  @override
  State<CustomButton> createState() => _CustomButtonState();
}

class _CustomButtonState extends State<CustomButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: DS.durationFast,
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.98).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: DS.curveEaseInOut,
      ),
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  void _handleTapDown(TapDownDetails details) {
    if (widget.onPressed != null && !widget.isLoading) {
      _animationController.forward();
    }
  }

  void _handleTapUp(TapUpDetails details) {
    _animationController.reverse();
  }

  void _handleTapCancel() {
    _animationController.reverse();
  }

  @override
  Widget build(BuildContext context) {
    final isDisabled = widget.onPressed == null || widget.isLoading;

    return GestureDetector(
      onTapDown: _handleTapDown,
      onTapUp: _handleTapUp,
      onTapCancel: _handleTapCancel,
      child: ScaleTransition(
        scale: _scaleAnimation,
        child: SizedBox(
          width: widget.isFullWidth ? double.infinity : null,
          height: _getButtonHeight(),
          child: _buildButtonContent(context, isDisabled),
        ),
      ),
    );
  }

  double _getButtonHeight() {
    switch (widget.size) {
      case CustomButtonSize.small:
        return 32.0;
      case CustomButtonSize.medium:
        return 48.0;
      case CustomButtonSize.large:
        return 56.0;
    }
  }

  double _getIconSize() {
    switch (widget.size) {
      case CustomButtonSize.small:
        return DS.iconSizeSm;
      case CustomButtonSize.medium:
        return DS.iconSizeBase;
      case CustomButtonSize.large:
        return DS.iconSizeLg;
    }
  }

  double _getFontSize() {
    switch (widget.size) {
      case CustomButtonSize.small:
        return DS.fontSizeSm;
      case CustomButtonSize.medium:
        return DS.fontSizeBase;
      case CustomButtonSize.large:
        return DS.fontSizeLg;
    }
  }

  Widget _buildButtonContent(BuildContext context, bool isDisabled) {
    switch (widget.variant) {
      case ButtonVariant.primary:
        return _buildPrimaryButton(context, isDisabled);
      case ButtonVariant.secondary:
        return _buildSecondaryButton(context, isDisabled);
      case ButtonVariant.text:
        return _buildTextButton(context, isDisabled);
      case ButtonVariant.icon:
        return _buildIconButton(context, isDisabled);
    }
  }

  Widget _buildPrimaryButton(BuildContext context, bool isDisabled) {
    final gradient = widget.customGradient ?? DS.primaryGradient;

    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: isDisabled ? null : gradient,
        color: isDisabled ? DS.neutral300 : null,
        borderRadius: DS.borderRadius12,
        boxShadow: isDisabled ? null : DS.shadowMd,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isDisabled ? null : widget.onPressed,
          borderRadius: DS.borderRadius12,
          child: Padding(
            padding: EdgeInsets.symmetric(
              horizontal: widget.size == CustomButtonSize.small
                  ? DS.spacing16
                  : DS.spacing24,
            ),
            child: _buildButtonRow(
              iconColor: DS.brandPrimary,
              textColor: DS.brandPrimary,
              isDisabled: isDisabled,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSecondaryButton(BuildContext context, bool isDisabled) => DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.transparent,
        border: Border.all(
          color: isDisabled
              ? DS.neutral300
              : DS.primaryBase,
          width: 2.0,
        ),
        borderRadius: DS.borderRadius12,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isDisabled ? null : widget.onPressed,
          borderRadius: DS.borderRadius12,
          child: Padding(
            padding: EdgeInsets.symmetric(
              horizontal: widget.size == CustomButtonSize.small
                  ? DS.spacing16
                  : DS.spacing24,
            ),
            child: _buildButtonRow(
              iconColor: isDisabled
                  ? DS.neutral400
                  : DS.primaryBase,
              textColor: isDisabled
                  ? DS.neutral400
                  : DS.primaryBase,
              isDisabled: isDisabled,
            ),
          ),
        ),
      ),
    );

  Widget _buildTextButton(BuildContext context, bool isDisabled) => Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: isDisabled ? null : widget.onPressed,
        borderRadius: DS.borderRadius8,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
          ),
          child: _buildButtonRow(
            iconColor: isDisabled
                ? DS.neutral400
                : DS.primaryBase,
            textColor: isDisabled
                ? DS.neutral400
                : DS.primaryBase,
            isDisabled: isDisabled,
          ),
        ),
      ),
    );

  Widget _buildIconButton(BuildContext context, bool isDisabled) {
    final buttonSize = _getButtonHeight();

    return Container(
      width: buttonSize,
      height: buttonSize,
      decoration: BoxDecoration(
        gradient: isDisabled ? null : DS.primaryGradient,
        color: isDisabled ? DS.neutral300 : null,
        borderRadius: widget.isCircular
            ? DS.borderRadiusFull
            : DS.borderRadius12,
        boxShadow: isDisabled ? null : DS.shadowSm,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isDisabled ? null : widget.onPressed,
          borderRadius: widget.isCircular
              ? DS.borderRadiusFull
              : DS.borderRadius12,
          child: Center(
            child: widget.isLoading
                ? SizedBox(
                    width: _getIconSize() * 0.8,
                    height: _getIconSize() * 0.8,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.0,
                      valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary),
                    ),
                  )
                : Icon(
                    widget.icon,
                    size: _getIconSize(),
                    color: DS.brandPrimaryConst,
                  ),
          ),
        ),
      ),
    );
  }

  Widget _buildButtonRow({
    required Color iconColor,
    required Color textColor,
    required bool isDisabled,
  }) {
    final children = <Widget>[];

    if (widget.isLoading) {
      children.add(
        SizedBox(
          width: _getIconSize(),
          height: _getIconSize(),
          child: CircularProgressIndicator(
            strokeWidth: 2.0,
            valueColor: AlwaysStoppedAnimation<Color>(
              widget.variant == ButtonVariant.primary
                  ? DS.brandPrimary
                  : DS.primaryBase,
            ),
          ),
        ),
      );
      if (widget.text != null) {
        children.add(const SizedBox(width: DS.spacing8));
      }
    } else if (widget.icon != null) {
      children.add(
        Icon(
          widget.icon,
          size: _getIconSize(),
          color: iconColor,
        ),
      );
      if (widget.text != null) {
        children.add(const SizedBox(width: DS.spacing8));
      }
    }

    if (widget.text != null) {
      children.add(
        Text(
          widget.text!,
          style: TextStyle(
            fontSize: _getFontSize(),
            fontWeight: DS.fontWeightMedium,
            color: textColor,
          ),
        ),
      );
    }

    return Opacity(
      opacity: isDisabled ? DS.opacityDisabled : 1.0,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: children,
      ),
    );
  }
}
