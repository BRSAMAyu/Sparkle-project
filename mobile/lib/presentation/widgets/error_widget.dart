import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/widgets/custom_button.dart'; // Reusing CustomButton

enum ErrorWidgetType { fullPage, banner }

class AppErrorWidget extends StatelessWidget {
  final String message;
  final String? title;
  final IconData? icon;
  final VoidCallback? onRetry;
  final String retryButtonText;
  final ErrorWidgetType type;

  const AppErrorWidget({
    super.key,
    required this.message,
    this.title,
    this.icon,
    this.onRetry,
    this.retryButtonText = 'Try Again',
    this.type = ErrorWidgetType.fullPage,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (type == ErrorWidgetType.banner) {
      return Container(
        padding: const EdgeInsets.all(AppDesignTokens.spacing16),
        decoration: BoxDecoration(
          color: AppDesignTokens.error.withOpacity(0.1),
          borderRadius: AppDesignTokens.borderRadius8,
          border: Border.all(color: AppDesignTokens.error),
        ),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: AppDesignTokens.error),
            const SizedBox(width: AppDesignTokens.spacing12),
            Expanded(
              child: Text(
                message,
                style: theme.textTheme.bodyMedium?.copyWith(color: AppDesignTokens.error),
              ),
            ),
            if (onRetry != null)
              CustomButton(
                text: retryButtonText,
                onPressed: onRetry,
                variant: CustomButtonVariant.text,
              ),
          ],
        ),
      );
    }

    // Full page error widget
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppDesignTokens.spacing24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            if (icon != null)
              Icon(
                icon,
                size: AppDesignTokens.iconSizeXl,
                color: theme.colorScheme.error,
              ),
            const SizedBox(height: AppDesignTokens.spacing16),
            Text(
              title ?? 'Something Went Wrong',
              style: theme.textTheme.headlineSmall?.copyWith(color: theme.colorScheme.error),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppDesignTokens.spacing8),
            Text(
              message,
              style: theme.textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: AppDesignTokens.spacing24),
              CustomButton(
                text: retryButtonText,
                onPressed: onRetry,
                variant: CustomButtonVariant.error,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
