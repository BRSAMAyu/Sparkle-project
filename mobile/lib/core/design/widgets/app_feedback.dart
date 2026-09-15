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
          accentColor: style.backgroundColor,
          backgroundColor: DS.surfaceRoleColor(SparkleSurfaceRole.modal),
          foregroundColor: DS.textPrimary,
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
  static const Duration errorDuration = Duration(seconds: 4);
  static const Duration successDuration = Duration(milliseconds: 2500);
  static const Duration infoDuration = Duration(seconds: 3);
  static const Duration warningDuration = Duration(seconds: 4);

  /// Creates a fully configured [SnackBar] for error messages.
  ///
  /// Always shows a close icon and uses [errorDuration].
  static SnackBar error(
    String message, {
    Key? key,
    VoidCallback? onRetry,
    String? retryLabel,
  }) {
    final resolvedLabel = retryLabel ?? 'Retry';
    return create(
      key: key,
      message: message,
      accentColor: DS.semanticError,
      backgroundColor: DS.surfaceRoleColor(SparkleSurfaceRole.modal),
      foregroundColor: DS.textPrimary,
      icon: Icons.error_outline,
      duration: errorDuration,
      showCloseIcon: true,
      actionLabel: onRetry != null ? resolvedLabel : null,
      onAction: onRetry,
    );
  }

  /// Creates a fully configured [SnackBar] for success messages.
  static SnackBar success(
    String message, {
    Key? key,
  }) =>
      create(
        key: key,
        message: message,
        accentColor: DS.semanticSuccess,
        backgroundColor: DS.surfaceRoleColor(SparkleSurfaceRole.modal),
        foregroundColor: DS.textPrimary,
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
        accentColor: DS.semanticWarning,
        backgroundColor: DS.surfaceRoleColor(SparkleSurfaceRole.modal),
        foregroundColor: DS.textPrimary,
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
        accentColor: DS.info,
        backgroundColor: DS.surfaceRoleColor(SparkleSurfaceRole.modal),
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
    Color? accentColor,
    IconData? icon,
    Duration duration = errorDuration,
    bool showCloseIcon = true,
    Color? closeIconColor,
    String? actionLabel,
    VoidCallback? onAction,
    Color? actionTextColor,
    DismissDirection dismissDirection = DismissDirection.horizontal,
  }) {
    final resolvedAccent = accentColor ?? backgroundColor ?? DS.semanticError;
    final resolvedForeground = foregroundColor ?? DS.textPrimary;

    return SnackBar(
      key: key,
      behavior: SnackBarBehavior.floating,
      duration: duration,
      backgroundColor:
          backgroundColor ?? DS.surfaceRoleColor(SparkleSurfaceRole.modal),
      elevation: 0,
      margin: const EdgeInsets.fromLTRB(
        DS.spacing16,
        0,
        DS.spacing16,
        DS.spacing16,
      ),
      showCloseIcon: showCloseIcon,
      closeIconColor: closeIconColor ?? resolvedForeground,
      dismissDirection: dismissDirection,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: DS.borderSubtle),
      ),
      content: IntrinsicHeight(
        child: Row(
          children: [
            Container(
              width: 4,
              decoration: BoxDecoration(
                color: resolvedAccent,
                borderRadius: BorderRadius.circular(999),
              ),
            ),
            const SizedBox(width: DS.spacing12),
            if (icon != null) ...[
              Icon(icon, color: resolvedAccent, size: 20),
              const SizedBox(width: DS.spacing10),
            ],
            Expanded(
              child: Text(
                message,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: DS.bodyMedium.copyWith(
                  color: resolvedForeground,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
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
