import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/features/home/home_routes.dart';
import 'package:sparkle/features/openclaw/presentation/widgets/openclaw_primitives.dart';
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

    final hasRecentExecution = latestIntent != null;
    final hasQueue = connection.queuedRequestCount > 0;
    final isConnected = connection.isConnected;
    final headline = !isConnected && !hasQueue
        ? '连接后可委派网页调研、文档整理'
        : !isConnected && hasQueue
            ? '已有任务在等待恢复'
            : isConnected && !hasRecentExecution
                ? '已准备好接手'
                : '最近一次做了什么';
    final summary = !isConnected && !hasQueue
        ? '把 OpenClaw 接进来后，聊天页和任务页都会获得稳定的执行入口。'
        : !isConnected && hasQueue
            ? '当前有 ${connection.queuedRequestCount} 个任务已排队，恢复连接后就能继续执行。'
            : isConnected && !hasRecentExecution
                ? '引擎状态正常，现在最适合回到聊天或任务页发起第一次委派。'
                : '最近执行：${latestIntent?.statusLabel ?? '已记录'}'
                    '${(latestIntent?.goal.trim().isNotEmpty ?? false) ? ' · ${latestIntent?.goal}' : ''}';
    final actionLabel = hasQueue ? '打开执行中心，处理等待队列' : '打开执行中心';
    final queueTone =
        hasQueue ? OpenClawVisualTone.offline : OpenClawVisualTone.active;
    final connectionTone =
        isConnected ? OpenClawVisualTone.connected : OpenClawVisualTone.offline;

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
          material: AppMaterials.ceramic(context).copyWith(
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
                          headline,
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
                  OpenClawMetricPill(
                    icon: Icons.sensors_rounded,
                    label: isConnected ? '已连接' : '未连接',
                    tone: connectionTone,
                    emphasized: isConnected,
                  ),
                  OpenClawMetricPill(
                    icon: Icons.schedule_rounded,
                    label: '${connection.queuedRequestCount} 排队中',
                    tone: queueTone,
                    emphasized: hasQueue,
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                summary,
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
                  actionLabel,
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
