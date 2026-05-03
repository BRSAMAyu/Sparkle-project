import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';

/// Compact error indicator for inline cards — replaces SizedBox.shrink()
/// so users see a visible hint + tap-to-retry instead of silent disappearance.
class CompactErrorCard extends StatelessWidget {
  const CompactErrorCard({super.key, this.onRetry});

  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    return GestureDetector(
      onTap: onRetry,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing8,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: 14, color: DS.textTertiary),
            const SizedBox(width: DS.spacing6),
            Text(
              zh ? '加载失败' : 'Failed to load',
              style: TextStyle(fontSize: 12, color: DS.textTertiary),
            ),
            if (onRetry != null) ...[
              const SizedBox(width: DS.spacing6),
              Text(
                zh ? '轻触重试' : 'Tap to retry',
                style: TextStyle(fontSize: 12, color: DS.brandPrimary),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
