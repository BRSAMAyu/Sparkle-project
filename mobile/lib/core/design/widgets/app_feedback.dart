import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
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
    final event = switch (role) {
      SparkleFeedbackRole.success => SensoryFeedbackEvent.success,
      SparkleFeedbackRole.warning => SensoryFeedbackEvent.warning,
      SparkleFeedbackRole.error => SensoryFeedbackEvent.error,
      SparkleFeedbackRole.undoable => SensoryFeedbackEvent.confirm,
      SparkleFeedbackRole.loading => SensoryFeedbackEvent.dialogOpen,
      SparkleFeedbackRole.info => SensoryFeedbackEvent.selection,
    };
    unawaited(SensoryFeedbackService.emit(event));

    final messenger = _resolveMessenger(context);
    if (messenger == null) return;
    final style = DS.feedbackStyle(role);
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SparkleSnackBar.create(
          message: message,
          backgroundColor: style.backgroundColor,
          foregroundColor: style.foregroundColor,
          icon: style.icon,
          duration: style.duration,
          showCloseIcon: true,
          actionLabel: actionLabel,
          onAction: onAction,
          actionTextColor: actionLabel != null && onAction != null
              ? (role == SparkleFeedbackRole.undoable
                  ? DS.brandPrimary
                  : ThemeUtils.getContrastSafeText(
                      style.backgroundColor,
                      darkText: DS.brandPrimary,
                    ))
              : null,
        ),
      );
  }

  static ScaffoldMessengerState? _resolveMessenger(BuildContext context) {
    final rootContext = navigatorKey.currentContext;
    final rootMessenger =
        rootContext != null ? ScaffoldMessenger.maybeOf(rootContext) : null;
    return rootMessenger ?? ScaffoldMessenger.maybeOf(context);
  }
}

/// A consistently configured [SnackBar] that always includes:
/// - Floating behavior (swipe-to-dismiss)
/// - A close/dismiss button
/// - Auto-dismiss timeout (defaults to 6s for errors, 3s otherwise)
/// - Rounded corners
///
/// Use this instead of raw [SnackBar] constructors anywhere in the app.
///
/// Example:
/// ```dart
/// ScaffoldMessenger.of(context).showSnackBar(
///   SparkleSnackBar.error('Something went wrong'),
/// );
/// ```
class SparkleSnackBar {
  SparkleSnackBar._();

  /// Default durations by severity.
  static const Duration errorDuration = Duration(seconds: 6);
  static const Duration successDuration = Duration(seconds: 3);
  static const Duration infoDuration = Duration(seconds: 3);
  static const Duration warningDuration = Duration(seconds: 5);

  /// Creates a fully configured [SnackBar] for error messages.
  ///
  /// Always shows a close icon and uses [errorDuration] (6 seconds).
  static SnackBar error(
    String message, {
    Key? key,
    VoidCallback? onRetry,
    String retryLabel = '重试',
  }) =>
      create(
        key: key,
        message: message,
        backgroundColor: DS.semanticError,
        foregroundColor: DS.neutral0,
        icon: Icons.error_outline,
        duration: errorDuration,
        showCloseIcon: true,
        actionLabel: onRetry != null ? retryLabel : null,
        onAction: onRetry,
      );

  /// Creates a fully configured [SnackBar] for success messages.
  static SnackBar success(
    String message, {
    Key? key,
  }) =>
      create(
        key: key,
        message: message,
        backgroundColor: DS.semanticSuccess,
        foregroundColor: DS.neutral0,
        icon: Icons.check_circle_outline,
        duration: successDuration,
        showCloseIcon: true,
      );

  /// Creates a fully configured [SnackBar] for warning messages.
  static SnackBar warning(
    String message, {
    Key? key,
  }) =>
      create(
        key: key,
        message: message,
        backgroundColor: DS.semanticWarning,
        foregroundColor: DS.neutral0,
        icon: Icons.warning_amber_rounded,
        duration: warningDuration,
        showCloseIcon: true,
      );

  /// Creates a fully configured [SnackBar] for informational messages.
  static SnackBar info(
    String message, {
    Key? key,
    Duration? duration,
  }) =>
      create(
        key: key,
        message: message,
        backgroundColor: DS.surfaceTertiary,
        foregroundColor: DS.textPrimary,
        icon: Icons.info_outline,
        duration: duration ?? infoDuration,
        showCloseIcon: true,
      );

  /// Creates a fully configured [SnackBar] with custom content.
  ///
  /// This is the base factory that all named constructors delegate to.
  /// Prefer using the named constructors ([error], [success], etc.) for
  /// standard cases. Use this when you need full control.
  static SnackBar create({
    required String message,
    Key? key,
    Color? backgroundColor,
    Color? foregroundColor,
    IconData? icon,
    Duration duration = errorDuration,
    bool showCloseIcon = true,
    Color? closeIconColor,
    String? actionLabel,
    VoidCallback? onAction,
    Color? actionTextColor,
    DismissDirection dismissDirection = DismissDirection.horizontal,
  }) {
    return SnackBar(
      key: key,
      behavior: SnackBarBehavior.floating,
      duration: duration,
      backgroundColor: backgroundColor ?? DS.semanticError,
      showCloseIcon: showCloseIcon,
      closeIconColor: closeIconColor ?? foregroundColor ?? DS.neutral0,
      dismissDirection: dismissDirection,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
      ),
      content: Row(
        children: [
          if (icon != null) ...[
            Icon(icon, color: foregroundColor ?? DS.neutral0, size: 18),
            const SizedBox(width: DS.spacing8),
          ],
          Expanded(
            child: Text(
              message,
              style: TextStyle(color: foregroundColor ?? DS.neutral0),
            ),
          ),
        ],
      ),
      action: actionLabel != null && onAction != null
          ? SnackBarAction(
              label: actionLabel,
              textColor: actionTextColor,
              onPressed: onAction,
            )
          : null,
    );
  }
}
