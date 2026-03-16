import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Galaxy错误对话框
class GalaxyErrorDialog extends StatelessWidget {
  const GalaxyErrorDialog({
    required this.error,
    super.key,
    this.onRetry,
    this.onDismiss,
  });

  final GalaxyError error;
  final VoidCallback? onRetry;
  final VoidCallback? onDismiss;

  static Future<void> show(
    BuildContext context, {
    required GalaxyError error,
    VoidCallback? onRetry,
    VoidCallback? onDismiss,
  }) =>
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => GalaxyErrorDialog(
          error: error,
          onRetry: onRetry,
          onDismiss: onDismiss,
        ),
      );

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
        backgroundColor: DS.surfaceHigh,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(
            color: _getErrorColor().withValues(alpha: 0.3),
          ),
        ),
        title: Row(
          children: [
            Icon(
              _getErrorIcon(),
              color: _getErrorColor(),
              size: 24,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                _getDialogTitle(l10n),
                style: TextStyle(
                  color: DS.textPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              error.userMessage,
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: 14,
              ),
            ),
            if (error.isRetryable) ...[
              const SizedBox(height: 16),
              Text(
                l10n.galaxyErrorRetryHint,
                style: TextStyle(
                  color: DS.textTertiary,
                  fontSize: 12,
                ),
              ),
            ],
          ],
        ),
        actions: [
          if (onDismiss != null)
            SparkleButton(
              label: l10n.close,
              variant: ButtonVariant.ghost,
              onPressed: () {
                Navigator.of(context).pop();
                onDismiss?.call();
              },
            ),
          if (onRetry != null && error.isRetryable)
            SparkleButton(
              label: l10n.retry,
              onPressed: () {
                Navigator.of(context).pop();
                onRetry?.call();
              },
            ),
        ],
      );
  }

  IconData _getErrorIcon() {
    switch (error.type) {
      case GalaxyErrorType.network:
        return Icons.wifi_off_rounded;
      case GalaxyErrorType.circuitBreakerOpen:
        return Icons.cloud_off_rounded;
      case GalaxyErrorType.unknown:
        return Icons.error_outline_rounded;
    }
  }

  Color _getErrorColor() {
    switch (error.type) {
      case GalaxyErrorType.network:
        return DS.warning;
      case GalaxyErrorType.circuitBreakerOpen:
        return DS.error;
      case GalaxyErrorType.unknown:
        return DS.textSecondary;
    }
  }

  String _getDialogTitle(AppLocalizations l10n) {
    switch (error.type) {
      case GalaxyErrorType.network:
        return l10n.galaxyErrorNetwork;
      case GalaxyErrorType.circuitBreakerOpen:
        return l10n.galaxyErrorServiceUnavailable;
      case GalaxyErrorType.unknown:
        return l10n.galaxyErrorLoadFailed;
    }
  }
}

/// Galaxy错误SnackBar
class GalaxyErrorSnackBar {
  static void show(
    BuildContext context, {
    required GalaxyError error,
    VoidCallback? onRetry,
    Duration duration = const Duration(seconds: 4),
  }) {
    final l10n = context.l10n;
    final snackBar = SnackBar(
      content: Row(
        children: [
          Icon(
            _getErrorIcon(error.type),
            color: DS.neutral0,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              error.userMessage,
              style: TextStyle(color: DS.neutral0),
            ),
          ),
        ],
      ),
      backgroundColor: _getErrorColor(error.type),
      duration: duration,
      action: onRetry != null && error.isRetryable
          ? SnackBarAction(
              label: l10n.retry,
              textColor: DS.neutral0,
              onPressed: onRetry,
            )
          : null,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
      ),
      margin: const EdgeInsets.all(DS.lg),
    );

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(snackBar);
  }

  static IconData _getErrorIcon(GalaxyErrorType type) {
    switch (type) {
      case GalaxyErrorType.network:
        return Icons.wifi_off_rounded;
      case GalaxyErrorType.circuitBreakerOpen:
        return Icons.cloud_off_rounded;
      case GalaxyErrorType.unknown:
        return Icons.error_outline_rounded;
    }
  }

  static Color _getErrorColor(GalaxyErrorType type) {
    switch (type) {
      case GalaxyErrorType.network:
        return DS.warning;
      case GalaxyErrorType.circuitBreakerOpen:
        return DS.error;
      case GalaxyErrorType.unknown:
        return DS.textSecondary;
    }
  }
}

/// 离线状态指示器
class OfflineIndicator extends StatelessWidget {
  const OfflineIndicator({
    super.key,
    this.isOffline = false,
    this.isUsingCache = false,
    this.onRetry,
  });

  final bool isOffline;
  final bool isUsingCache;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    if (!isOffline && !isUsingCache) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isOffline
            ? DS.error.withValues(alpha: 0.9)
            : DS.warning.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: DS.overlay30.withValues(alpha: 0.2),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isOffline ? Icons.wifi_off_rounded : Icons.cloud_queue_rounded,
            color: DS.neutral0,
            size: 16,
          ),
          const SizedBox(width: 8),
          Text(
            isOffline ? l10n.galaxyOfflineMode : l10n.galaxyUsingCache,
            style: TextStyle(
              color: DS.neutral0,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
          if (onRetry != null) ...[
            const SizedBox(width: 8),
            GestureDetector(
              onTap: onRetry,
              child: Container(
                padding: const EdgeInsets.all(DS.xs),
                decoration: BoxDecoration(
                  color: DS.neutral0.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.refresh_rounded,
                  color: DS.neutral0,
                  size: 14,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// 加载失败占位组件
class GalaxyErrorPlaceholder extends StatelessWidget {
  const GalaxyErrorPlaceholder({
    required this.error,
    super.key,
    this.onRetry,
  });

  final GalaxyError error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Center(
        child: Padding(
          padding: const EdgeInsets.all(DS.xxl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // 图标
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: _getErrorColor().withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  _getErrorIcon(),
                  color: _getErrorColor(),
                  size: 40,
                ),
              ),
              const SizedBox(height: DS.xl),

              // 标题
              Text(
                _getPlaceholderTitle(l10n),
                style: TextStyle(
                  color: DS.textPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),

              // 描述
              Text(
                error.userMessage,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: DS.textSecondary,
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: DS.xl),

              // 重试按钮
              if (onRetry != null && error.isRetryable)
                SparkleButton(
                  label: l10n.retry,
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh_rounded, size: 18),
                ),
            ],
          ),
        ),
    );
  }

  IconData _getErrorIcon() {
    switch (error.type) {
      case GalaxyErrorType.network:
        return Icons.wifi_off_rounded;
      case GalaxyErrorType.circuitBreakerOpen:
        return Icons.cloud_off_rounded;
      case GalaxyErrorType.unknown:
        return Icons.error_outline_rounded;
    }
  }

  Color _getErrorColor() {
    switch (error.type) {
      case GalaxyErrorType.network:
        return DS.warning;
      case GalaxyErrorType.circuitBreakerOpen:
        return DS.error;
      case GalaxyErrorType.unknown:
        return DS.textSecondary;
    }
  }

  String _getPlaceholderTitle(AppLocalizations l10n) {
    switch (error.type) {
      case GalaxyErrorType.network:
        return l10n.galaxyErrorNetworkFailed;
      case GalaxyErrorType.circuitBreakerOpen:
        return l10n.galaxyErrorServiceTemporarilyUnavailable;
      case GalaxyErrorType.unknown:
        return l10n.galaxyErrorLoadFailed;
    }
  }
}
