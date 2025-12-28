import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/repositories/enhanced_galaxy_repository.dart';

/// Galaxy错误对话框
class GalaxyErrorDialog extends StatelessWidget {
  const GalaxyErrorDialog({
    required this.error, super.key,
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
  }) => showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => GalaxyErrorDialog(
        error: error,
        onRetry: onRetry,
        onDismiss: onDismiss,
      ),
    );

  @override
  Widget build(BuildContext context) => AlertDialog(
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
              _getTitle(),
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
              '点击"重试"按钮重新加载',
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
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              onDismiss?.call();
            },
            child: Text(
              '关闭',
              style: TextStyle(color: DS.textSecondary),
            ),
          ),
        if (onRetry != null && error.isRetryable)
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              onRetry?.call();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: DS.brandPrimary,
              foregroundColor: DS.textPrimary,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            child: const Text('重试'),
          ),
      ],
    );

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
        return Colors.orange;
      case GalaxyErrorType.circuitBreakerOpen:
        return Colors.red;
      case GalaxyErrorType.unknown:
        return Colors.grey;
    }
  }

  String _getTitle() {
    switch (error.type) {
      case GalaxyErrorType.network:
        return '网络错误';
      case GalaxyErrorType.circuitBreakerOpen:
        return '服务不可用';
      case GalaxyErrorType.unknown:
        return '加载失败';
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
    final snackBar = SnackBar(
      content: Row(
        children: [
          Icon(
            _getErrorIcon(error.type),
            color: Colors.white,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              error.userMessage,
              style: const TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
      backgroundColor: _getErrorColor(error.type),
      duration: duration,
      action: onRetry != null && error.isRetryable
          ? SnackBarAction(
              label: '重试',
              textColor: Colors.white,
              onPressed: onRetry,
            )
          : null,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
      ),
      margin: const EdgeInsets.all(16),
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
        return Colors.orange.shade700;
      case GalaxyErrorType.circuitBreakerOpen:
        return Colors.red.shade700;
      case GalaxyErrorType.unknown:
        return Colors.grey.shade700;
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
    if (!isOffline && !isUsingCache) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isOffline
            ? Colors.red.withValues(alpha: 0.9)
            : Colors.orange.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
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
            color: Colors.white,
            size: 16,
          ),
          const SizedBox(width: 8),
          Text(
            isOffline ? '离线模式' : '使用缓存数据',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
          if (onRetry != null) ...[
            const SizedBox(width: 8),
            GestureDetector(
              onTap: onRetry,
              child: Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.refresh_rounded,
                  color: Colors.white,
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
    required this.error, super.key,
    this.onRetry,
  });

  final GalaxyError error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
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
            const SizedBox(height: 24),

            // 标题
            Text(
              _getTitle(),
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
            const SizedBox(height: 24),

            // 重试按钮
            if (onRetry != null && error.isRetryable)
              ElevatedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: const Text('重试'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: DS.brandPrimary,
                  foregroundColor: DS.textPrimary,
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
          ],
        ),
      ),
    );

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
        return Colors.orange;
      case GalaxyErrorType.circuitBreakerOpen:
        return Colors.red;
      case GalaxyErrorType.unknown:
        return Colors.grey;
    }
  }

  String _getTitle() {
    switch (error.type) {
      case GalaxyErrorType.network:
        return '网络连接失败';
      case GalaxyErrorType.circuitBreakerOpen:
        return '服务暂时不可用';
      case GalaxyErrorType.unknown:
        return '加载失败';
    }
  }
}
