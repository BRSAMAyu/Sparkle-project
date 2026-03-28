import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/features/home/home_routes.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';

class OpenClawHubCard extends ConsumerWidget {
  const OpenClawHubCard({
    super.key,
    this.compact = false,
    this.dense = false,
  });

  final bool compact;
  final bool dense;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final connection = ref.watch(openClawConnectionProvider);
    final taskState = ref.watch(taskListProvider);
    final latestIntent = taskState.taskExecutions.values.isEmpty
        ? null
        : (taskState.taskExecutions.values.toList()
              ..sort(
                (left, right) => (right.createdAt ?? DateTime(1970))
                    .compareTo(left.createdAt ?? DateTime(1970)),
              ))
            .first;

    final statusColor = switch (connection.info.status) {
      OpenClawConnectionStatus.connected => DS.semanticSuccess,
      OpenClawConnectionStatus.connecting => DS.info,
      OpenClawConnectionStatus.error => DS.semanticError,
      OpenClawConnectionStatus.disconnected => DS.textTertiary,
    };

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing16,
        0,
        DS.spacing16,
        DS.spacing12,
      ),
      child: SparklePressable(
        onTap: () => context.push(HomeRoutes.openClawHub),
        padding: EdgeInsets.zero,
        borderRadius: DS.borderRadius20,
        child: MaterialStyler(
          material: AppMaterials.ceramic.copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                Color.lerp(DS.surfaceSecondary, DS.info, 0.08)!,
                DS.surfaceSecondary,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderColor: DS.info.withValues(alpha: 0.16),
            borderWidth: 1,
          ),
          borderRadius: DS.borderRadius20,
          padding: EdgeInsets.all(dense ? DS.spacing12 : DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: compact ? 38 : 44,
                    height: compact ? 38 : 44,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          DS.brandPrimaryConst,
                          Color.lerp(DS.brandPrimaryConst, DS.info, 0.45) ??
                              DS.info,
                        ],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(
                      Icons.cloud_sync_rounded,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(width: DS.spacing10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'OpenClaw',
                          style: context.sparkleTypography.labelLarge.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                        const SizedBox(height: DS.spacing4),
                        Text(
                          connection.isConnected ? '执行引擎已就绪' : '独立的 AI 执行中心',
                          style: context.sparkleTypography.labelSmall.copyWith(
                            color: DS.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    Icons.chevron_right_rounded,
                    color: DS.textTertiary,
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  _CardPill(
                    icon: Icons.sensors_rounded,
                    label: connection.isConnected ? '已连接' : '未连接',
                    color: statusColor,
                  ),
                  _CardPill(
                    icon: Icons.schedule_rounded,
                    label: '${connection.queuedRequestCount} 排队中',
                    color: connection.queuedRequestCount > 0
                        ? DS.warning
                        : DS.textSecondary,
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                latestIntent == null
                    ? '从聊天或任务页发起委派后，这里会显示最近的执行状态和入口。'
                    : '最近执行：${latestIntent.statusLabel}'
                        '${latestIntent.goal.trim().isNotEmpty ? ' · ${latestIntent.goal}' : ''}',
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: DS.spacing10),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  '打开 OpenClaw',
                  style: context.sparkleTypography.labelLarge.copyWith(
                    color: DS.brandPrimaryConst,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CardPill extends StatelessWidget {
  const _CardPill({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: DS.spacing4),
            Text(
              label,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: color,
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ],
        ),
      );
}
