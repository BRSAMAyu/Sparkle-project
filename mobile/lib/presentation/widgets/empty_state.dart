import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/widgets/custom_button.dart';

class EmptyState extends StatelessWidget {
  final String message;
  final String? title;
  final IconData? icon;
  final String? imagePath; // Path to an asset image
  final VoidCallback? onActionPressed;
  final String actionButtonText;

  const EmptyState({
    super.key,
    required this.message,
    this.title,
    this.icon,
    this.imagePath,
    this.onActionPressed,
    this.actionButtonText = 'Take Action',
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppDesignTokens.spacing24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            if (imagePath != null) ...[
              Image.asset(
                imagePath!,
                height: AppDesignTokens.iconSize3xl, // Use a larger size for images
                width: AppDesignTokens.iconSize3xl,
              ),
              const SizedBox(height: AppDesignTokens.spacing16),
            ] else if (icon != null) ...[
              Icon(
                icon,
                size: AppDesignTokens.iconSize3xl,
                color: theme.colorScheme.onSurface.withOpacity(0.6),
              ),
              const SizedBox(height: AppDesignTokens.spacing16),
            ],
            Text(
              title ?? 'No Content Here',
              style: theme.textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppDesignTokens.spacing8),
            Text(
              message,
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.8),
              ),
              textAlign: TextAlign.center,
            ),
            if (onActionPressed != null) ...[
              const SizedBox(height: AppDesignTokens.spacing24),
              CustomButton(
                text: actionButtonText,
                onPressed: onActionPressed,
                variant: CustomButtonVariant.primary,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
