import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/utils/theme_utils.dart';

/// Unified in-app feedback entry for snack bars.
class AppFeedback {
  const AppFeedback._();

  static void info(BuildContext context, String message) {
    _show(
      context: context,
      message: message,
      icon: Icons.info_outline,
      backgroundColor: DS.surfaceTertiary,
      foregroundColor: DS.textPrimary,
    );
  }

  static void success(BuildContext context, String message) {
    final backgroundColor = DS.success;
    _show(
      context: context,
      message: message,
      icon: Icons.check_circle_outline,
      backgroundColor: backgroundColor,
      foregroundColor: ThemeUtils.getContrastSafeText(
        backgroundColor,
        darkText: DS.textPrimary,
      ),
    );
  }

  static void error(BuildContext context, String message) {
    final backgroundColor = DS.error;
    _show(
      context: context,
      message: message,
      icon: Icons.error_outline,
      backgroundColor: backgroundColor,
      foregroundColor: ThemeUtils.getContrastSafeText(
        backgroundColor,
        darkText: DS.textPrimary,
      ),
    );
  }

  static void _show({
    required BuildContext context,
    required String message,
    required IconData icon,
    required Color backgroundColor,
    required Color foregroundColor,
  }) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          behavior: SnackBarBehavior.floating,
          backgroundColor: backgroundColor,
          content: Row(
            children: [
              Icon(icon, color: foregroundColor, size: 18),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  message,
                  style: TextStyle(color: foregroundColor),
                ),
              ),
            ],
          ),
        ),
      );
  }
}
