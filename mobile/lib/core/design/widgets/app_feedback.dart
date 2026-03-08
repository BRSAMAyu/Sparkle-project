import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/utils/theme_utils.dart';

/// Unified in-app feedback entry for snack bars.
class AppFeedback {
  const AppFeedback._();

  static void info(BuildContext context, String message) {
    _show(context: context, message: message, role: SparkleFeedbackRole.info);
  }

  static void success(BuildContext context, String message) {
    _show(
      context: context,
      message: message,
      role: SparkleFeedbackRole.success,
    );
  }

  static void warning(BuildContext context, String message) {
    _show(
      context: context,
      message: message,
      role: SparkleFeedbackRole.warning,
    );
  }

  static void error(BuildContext context, String message) {
    _show(
      context: context,
      message: message,
      role: SparkleFeedbackRole.error,
    );
  }

  static void loading(BuildContext context, String message) {
    _show(
      context: context,
      message: message,
      role: SparkleFeedbackRole.loading,
    );
  }

  static void undoable({
    required BuildContext context,
    required String message,
    required String actionLabel,
    required VoidCallback onAction,
  }) {
    _show(
      context: context,
      message: message,
      role: SparkleFeedbackRole.undoable,
      actionLabel: actionLabel,
      onAction: onAction,
    );
  }

  static void _show({
    required BuildContext context,
    required String message,
    required SparkleFeedbackRole role,
    String? actionLabel,
    VoidCallback? onAction,
  }) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    final style = DS.feedbackStyle(role);
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          behavior: SnackBarBehavior.floating,
          duration: style.duration,
          backgroundColor: style.backgroundColor,
          showCloseIcon: role == SparkleFeedbackRole.loading,
          closeIconColor: style.foregroundColor,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          content: Row(
            children: [
              Icon(style.icon, color: style.foregroundColor, size: 18),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  message,
                  style: TextStyle(color: style.foregroundColor),
                ),
              ),
            ],
          ),
          action: actionLabel != null && onAction != null
              ? SnackBarAction(
                  label: actionLabel,
                  textColor: role == SparkleFeedbackRole.undoable
                      ? DS.brandPrimary
                      : ThemeUtils.getContrastSafeText(
                          style.backgroundColor,
                          darkText: DS.brandPrimary,
                        ),
                  onPressed: onAction,
                )
              : null,
        ),
      );
  }
}
