import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/app/theme.dart'; // Import AppColors and ThemeExtensionHelper

enum CustomButtonVariant {
  primary,
  secondary,
  outline,
  text,
  success,
  warning,
  error,
}

class CustomButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final CustomButtonVariant variant;
  final bool isLoading;
  final bool isDisabled;
  final Widget? leadingIcon;
  final Widget? trailingIcon;

  const CustomButton({
    required this.text, required this.onPressed, super.key,
    this.variant = CustomButtonVariant.primary,
    this.isLoading = false,
    this.isDisabled = false,
    this.leadingIcon,
    this.trailingIcon,
  });

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final AppThemeExtension? appTheme = theme.appExtension;

    Color backgroundColor;
    Color foregroundColor;
    Color? overlayColor;
    BorderSide? borderSide;
    List<BoxShadow>? shadows;
    final TextStyle textStyle = theme.textTheme.labelLarge!.copyWith(
      fontWeight: AppDesignTokens.fontWeightSemibold,
    );
    EdgeInsetsGeometry padding = const EdgeInsets.symmetric(
      horizontal: AppDesignTokens.spacing24,
      vertical: AppDesignTokens.spacing12,
    );
    final BorderRadius borderRadius = AppDesignTokens.borderRadius8;

    switch (variant) {
      case CustomButtonVariant.primary:
        backgroundColor = theme.primaryColor;
        foregroundColor = Colors.white;
        shadows = appTheme?.elevatedShadow;
        break;
      case CustomButtonVariant.secondary:
        backgroundColor = AppColors.secondary;
        foregroundColor = Colors.white;
        shadows = appTheme?.elevatedShadow;
        break;
      case CustomButtonVariant.outline:
        backgroundColor = Colors.transparent;
        foregroundColor = theme.primaryColor;
        borderSide = BorderSide(color: theme.primaryColor, width: 1.5);
        shadows = AppDesignTokens.shadowSm;
        break;
      case CustomButtonVariant.text:
        backgroundColor = Colors.transparent;
        foregroundColor = theme.primaryColor;
        padding = const EdgeInsets.symmetric(
          horizontal: AppDesignTokens.spacing16,
          vertical: AppDesignTokens.spacing8,
        );
        break;
      case CustomButtonVariant.success:
        backgroundColor = AppDesignTokens.success;
        foregroundColor = Colors.white;
        shadows = appTheme?.elevatedShadow;
        break;
      case CustomButtonVariant.warning:
        backgroundColor = AppDesignTokens.warning;
        foregroundColor = Colors.white;
        shadows = appTheme?.elevatedShadow;
        break;
      case CustomButtonVariant.error:
        backgroundColor = AppDesignTokens.error;
        foregroundColor = Colors.white;
        shadows = appTheme?.elevatedShadow;
        break;
    }

    // Apply disabled styles
    if (isDisabled || isLoading) {
      backgroundColor = (backgroundColor is MaterialColor)
          ? backgroundColor[300]!
          : backgroundColor.withOpacity(AppDesignTokens.opacityDisabled);
      foregroundColor = foregroundColor.withOpacity(AppDesignTokens.opacityDisabled);
      borderSide = borderSide?.copyWith(
          color: borderSide.color.withOpacity(AppDesignTokens.opacityDisabled),);
      shadows = null; // No shadows when disabled
    }

    return Opacity(
      opacity: isDisabled ? AppDesignTokens.opacityDisabled : AppDesignTokens.opacityFull,
      child: Material(
        color: backgroundColor,
        borderRadius: borderRadius,
        elevation: 0, // Handled by custom shadows
        shadowColor: Colors.transparent,
        child: InkWell(
          onTap: (onPressed != null && !isDisabled && !isLoading) 
            ? () {
                HapticFeedback.lightImpact();
                onPressed!();
              } 
            : null,
          borderRadius: borderRadius,
          child: Container(
            padding: padding,
            decoration: BoxDecoration(
              borderRadius: borderRadius,
              border: borderSide != null ? Border.fromBorderSide(borderSide) : null,
              boxShadow: shadows,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (isLoading)
                  SizedBox(
                    width: textStyle.fontSize! + AppDesignTokens.spacing4,
                    height: textStyle.fontSize! + AppDesignTokens.spacing4,
                    child: CircularProgressIndicator(
                      valueColor: AlwaysStoppedAnimation<Color>(foregroundColor),
                      strokeWidth: 2,
                    ),
                  )
                else if (leadingIcon != null)
                  Padding(
                    padding: const EdgeInsets.only(right: AppDesignTokens.spacing8),
                    child: IconTheme(
                      data: IconThemeData(color: foregroundColor, size: textStyle.fontSize),
                      child: leadingIcon!,
                    ),
                  ),
                Text(
                  text,
                  style: textStyle.copyWith(color: foregroundColor),
                ),
                if (!isLoading && trailingIcon != null)
                  Padding(
                    padding: const EdgeInsets.only(left: AppDesignTokens.spacing8),
                    child: IconTheme(
                      data: IconThemeData(color: foregroundColor, size: textStyle.fontSize),
                      child: trailingIcon!,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}