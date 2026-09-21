import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/offline/connectivity_provider.dart';
import 'package:sparkle/features/task/data/services/task_offline_queue.dart';

/// TASK-013: Banner showing offline state and pending task ops.
///
/// Surfaces:
///   1. "Currently offline — your task actions will sync when you reconnect"
///   2. "N task actions waiting to sync"
/// when either condition is true. Hidden when online with empty queue.
class TaskOfflineIndicator extends ConsumerWidget {
  const TaskOfflineIndicator({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isOnline = ref.watch(isOnlineProvider);
    final pendingAsync = ref.watch(pendingTaskOpsCountProvider);
    final pending = pendingAsync.maybeWhen(data: (n) => n, orElse: () => 0);

    if (isOnline && pending == 0) {
      return const SizedBox.shrink();
    }

    final isOffline = !isOnline;
    final color = isOffline ? DS.semanticWarning : DS.brandPrimary;
    final icon = isOffline ? Icons.cloud_off_outlined : Icons.sync;
    final l10n = context.l10n;
    final message = isOffline
        ? l10n.taskOfflineMessage
        : l10n.taskSyncingCount(pending);

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                color: DS.textPrimary,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          if (!isOffline && pending > 0)
            // U-01 Step 3：裸 CPI 迁 owner。
            LoadingIndicator.circular(
              size: 14,
              strokeWidth: 2,
              liveRegion: false,
            ),
        ],
      ),
    );
  }
}
