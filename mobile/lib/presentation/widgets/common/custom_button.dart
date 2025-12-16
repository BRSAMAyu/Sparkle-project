import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// 按钮变体类型
enum ButtonVariant {
  primary, // 主要按钮 - 渐变背景
  secondary, // 次要按钮 - 透明背景 + 边框
  text, // 文字按钮 - 无边框
  icon, // 图标按钮 - 圆形或方形
}

/// 按钮尺寸
enum ButtonSize {
  small, // 小 - 32px高度
  medium, // 中 - 48px高度
  large, // 大 - 56px高度
}

/// 自定义按钮组件
///
/// 支持多种变体、尺寸和状态，具有精致的视觉效果和流畅的动画
class CustomButton extends StatefulWidget {
  /// 按钮文本
  final String? text;

  /// 按钮图标
  final IconData? icon;

  /// 点击回调
  final VoidCallback? onPressed;

  /// 按钮变体
  final ButtonVariant variant;

  /// 按钮尺寸
  final ButtonSize size;

  /// 是否加载中
  final bool isLoading;

  /// 是否全宽
  final bool isFullWidth;

  /// 自定义渐变（仅适用于primary变体）
  final LinearGradient? customGradient;

  /// 图标按钮形状（仅适用于icon变体）
  final bool isCircular;

  const CustomButton({
    super.key,
    this.text,
    this.icon,
    this.onPressed,
    this.variant = ButtonVariant.primary,
    this.size = ButtonSize.medium,
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
    ButtonSize size = ButtonSize.medium,
    bool isLoading = false,
    bool isFullWidth = false,
    LinearGradient? customGradient,
  }) {
    return CustomButton(
      key: key,
      text: text,
      icon: icon,
      onPressed: onPressed,
      variant: ButtonVariant.primary,
      size: size,
      isLoading: isLoading,
      isFullWidth: isFullWidth,
      customGradient: customGradient,
    );
  }

  /// 次要按钮工厂构造函数
  factory CustomButton.secondary({
    required String text, required VoidCallback? onPressed, Key? key,
    IconData? icon,
    ButtonSize size = ButtonSize.medium,
    bool isLoading = false,
    bool isFullWidth = false,
  }) {
    return CustomButton(
      key: key,
      text: text,
      icon: icon,
      onPressed: onPressed,
      variant: ButtonVariant.secondary,
      size: size,
      isLoading: isLoading,
      isFullWidth: isFullWidth,
    );
  }

  /// 文字按钮工厂构造函数
  factory CustomButton.text({
    required String text, required VoidCallback? onPressed, Key? key,
    IconData? icon,
    ButtonSize size = ButtonSize.medium,
    bool isLoading = false,
  }) {
    return CustomButton(
      key: key,
      text: text,
      icon: icon,
      onPressed: onPressed,
      variant: ButtonVariant.text,
      size: size,
      isLoading: isLoading,
      isFullWidth: false,
    );
  }

  /// 图标按钮工厂构造函数
  factory CustomButton.icon({
    required IconData icon, required VoidCallback? onPressed, Key? key,
    ButtonSize size = ButtonSize.medium,
    bool isLoading = false,
    bool isCircular = true,
  }) {
    return CustomButton(
      key: key,
      icon: icon,
      onPressed: onPressed,
      variant: ButtonVariant.icon,
      size: size,
      isLoading: isLoading,
      isCircular: isCircular,
    );
  }

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
      duration: AppDesignTokens.durationFast,
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.98).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: AppDesignTokens.curveEaseInOut,
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
    final bool isDisabled = widget.onPressed == null || widget.isLoading;

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
      case ButtonSize.small:
        return 32.0;
      case ButtonSize.medium:
        return 48.0;
      case ButtonSize.large:
        return 56.0;
    }
  }

  double _getIconSize() {
    switch (widget.size) {
      case ButtonSize.small:
        return AppDesignTokens.iconSizeSm;
      case ButtonSize.medium:
        return AppDesignTokens.iconSizeBase;
      case ButtonSize.large:
        return AppDesignTokens.iconSizeLg;
    }
  }

  double _getFontSize() {
    switch (widget.size) {
      case ButtonSize.small:
        return AppDesignTokens.fontSizeSm;
      case ButtonSize.medium:
        return AppDesignTokens.fontSizeBase;
      case ButtonSize.large:
        return AppDesignTokens.fontSizeLg;
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
    final gradient = widget.customGradient ?? AppDesignTokens.primaryGradient;

    return Container(
      decoration: BoxDecoration(
        gradient: isDisabled ? null : gradient,
        color: isDisabled ? AppDesignTokens.neutral300 : null,
        borderRadius: AppDesignTokens.borderRadius12,
        boxShadow: isDisabled ? null : AppDesignTokens.shadowMd,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isDisabled ? null : widget.onPressed,
          borderRadius: AppDesignTokens.borderRadius12,
          child: Padding(
            padding: EdgeInsets.symmetric(
              horizontal: widget.size == ButtonSize.small
                  ? AppDesignTokens.spacing16
                  : AppDesignTokens.spacing24,
            ),
            child: _buildButtonRow(
              iconColor: Colors.white,
              textColor: Colors.white,
              isDisabled: isDisabled,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSecondaryButton(BuildContext context, bool isDisabled) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.transparent,
        border: Border.all(
          color: isDisabled
              ? AppDesignTokens.neutral300
              : AppDesignTokens.primaryBase,
          width: 2.0,
        ),
        borderRadius: AppDesignTokens.borderRadius12,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isDisabled ? null : widget.onPressed,
          borderRadius: AppDesignTokens.borderRadius12,
          child: Padding(
            padding: EdgeInsets.symmetric(
              horizontal: widget.size == ButtonSize.small
                  ? AppDesignTokens.spacing16
                  : AppDesignTokens.spacing24,
            ),
            child: _buildButtonRow(
              iconColor: isDisabled
                  ? AppDesignTokens.neutral400
                  : AppDesignTokens.primaryBase,
              textColor: isDisabled
                  ? AppDesignTokens.neutral400
                  : AppDesignTokens.primaryBase,
              isDisabled: isDisabled,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTextButton(BuildContext context, bool isDisabled) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: isDisabled ? null : widget.onPressed,
        borderRadius: AppDesignTokens.borderRadius8,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppDesignTokens.spacing12,
          ),
          child: _buildButtonRow(
            iconColor: isDisabled
                ? AppDesignTokens.neutral400
                : AppDesignTokens.primaryBase,
            textColor: isDisabled
                ? AppDesignTokens.neutral400
                : AppDesignTokens.primaryBase,
            isDisabled: isDisabled,
          ),
        ),
      ),
    );
  }

  Widget _buildIconButton(BuildContext context, bool isDisabled) {
    final buttonSize = _getButtonHeight();

    return Container(
      width: buttonSize,
      height: buttonSize,
      decoration: BoxDecoration(
        gradient: isDisabled ? null : AppDesignTokens.primaryGradient,
        color: isDisabled ? AppDesignTokens.neutral300 : null,
        borderRadius: widget.isCircular
            ? AppDesignTokens.borderRadiusFull
            : AppDesignTokens.borderRadius12,
        boxShadow: isDisabled ? null : AppDesignTokens.shadowSm,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isDisabled ? null : widget.onPressed,
          borderRadius: widget.isCircular
              ? AppDesignTokens.borderRadiusFull
              : AppDesignTokens.borderRadius12,
          child: Center(
            child: widget.isLoading
                ? SizedBox(
                    width: _getIconSize() * 0.8,
                    height: _getIconSize() * 0.8,
                    child: const CircularProgressIndicator(
                      strokeWidth: 2.0,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                : Icon(
                    widget.icon,
                    size: _getIconSize(),
                    color: Colors.white,
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
    final List<Widget> children = [];

    if (widget.isLoading) {
      children.add(
        SizedBox(
          width: _getIconSize(),
          height: _getIconSize(),
          child: CircularProgressIndicator(
            strokeWidth: 2.0,
            valueColor: AlwaysStoppedAnimation<Color>(
              widget.variant == ButtonVariant.primary
                  ? Colors.white
                  : AppDesignTokens.primaryBase,
            ),
          ),
        ),
      );
      if (widget.text != null) {
        children.add(const SizedBox(width: AppDesignTokens.spacing8));
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
        children.add(const SizedBox(width: AppDesignTokens.spacing8));
      }
    }

    if (widget.text != null) {
      children.add(
        Text(
          widget.text!,
          style: TextStyle(
            fontSize: _getFontSize(),
            fontWeight: AppDesignTokens.fontWeightMedium,
            color: textColor,
          ),
        ),
      );
    }

    return Opacity(
      opacity: isDisabled ? AppDesignTokens.opacityDisabled : 1.0,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: children,
      ),
    );
  }
}
