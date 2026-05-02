import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/offline/connectivity_provider.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/task/data/services/task_offline_queue.dart';

/// TASK-013: Banner showing offline state and pending task ops.
///
/// Surfaces:
///   1. "Currently offline — your task actions will sync when you reconnect"
///   2. "N task actions waiting to sync"
/// when either condition is true. Hidden when online with empty queue.
class TaskOfflineIndicator extends ConsumerWidget {
  const TaskOfflineIndicator({super.key});

  static String _t(String zh, String en) =>
      I18nService.instance.isChinese ? zh : en;

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
    final message = isOffline
        ? _t(
            '当前无网络 — 你的任务操作会在恢复连接后自动同步',
            'Currently offline — task actions will sync when you reconnect',
          )
        : _t(
            '$pending 个任务操作正在同步',
            '$pending task actions syncing',
          );

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
            const SizedBox(
              height: 14,
              width: 14,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
        ],
      ),
    );
  }
}
