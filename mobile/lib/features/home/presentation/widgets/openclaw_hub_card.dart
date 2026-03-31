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
    final isTightCard = compact || dense;
    final connection = ref.watch(openClawConnectionProvider);
    final taskState = ref.watch(taskListProvider);
    final hasExecutionPermissionIssue = connection.hasExecutionPermissionIssue;
    final hasExecutionEndpointIssue = connection.hasExecutionEndpointIssue;
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
    final isGatewayReachable = connection.isGatewayReachable;
    final headline = hasExecutionPermissionIssue
        ? '网关在线，但当前没有执行权限'
        : hasExecutionEndpointIssue
            ? '网关在线，但执行入口不可用'
            : !isGatewayReachable && !hasQueue
                ? '连接后可委派网页调研、文档整理'
                : !isGatewayReachable && hasQueue
                    ? '已有任务在等待恢复'
                    : isConnected && !hasRecentExecution
                        ? '已准备好接手'
                        : '最近一次做了什么';
    final summary = hasExecutionPermissionIssue
        ? '当前令牌能访问 OpenClaw，但执行会被权限拦住。补齐权限或切到已配对连接后，排队任务就能继续跑。'
        : hasExecutionEndpointIssue
            ? '网关地址本身可达，但执行接口还没准备好。先修好 `/v1/responses` 或 transport，再继续委派。'
            : !isGatewayReachable && !hasQueue
                ? '把 OpenClaw 接进来后，聊天页和任务页都会获得稳定的执行入口。'
                : !isGatewayReachable && hasQueue
                    ? '当前有 ${connection.queuedRequestCount} 个任务已排队，恢复连接后就能继续执行。'
                    : isConnected && !hasRecentExecution
                        ? '引擎状态正常，现在最适合回到聊天或任务页发起第一次委派。'
                        : '最近执行：${latestIntent?.statusLabel ?? '已记录'}'
                            '${(latestIntent?.goal.trim().isNotEmpty ?? false) ? ' · ${latestIntent?.goal}' : ''}';
    final actionLabel = hasExecutionPermissionIssue
        ? '打开执行中心，修复权限'
        : hasExecutionEndpointIssue
            ? '打开执行中心，检查执行入口'
            : hasQueue
                ? '打开执行中心，处理等待队列'
                : '打开执行中心';
    final queueTone =
        hasQueue ? OpenClawVisualTone.offline : OpenClawVisualTone.active;
    final connectionTone =
        hasExecutionPermissionIssue || hasExecutionEndpointIssue
            ? OpenClawVisualTone.attention
            : isGatewayReachable
                ? OpenClawVisualTone.connected
                : OpenClawVisualTone.offline;

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
          padding: EdgeInsets.all(isTightCard ? DS.spacing10 : DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: isTightCard ? 34 : 44,
                    height: isTightCard ? 34 : 44,
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
                          maxLines: isTightCard ? 1 : 2,
                          overflow: TextOverflow.ellipsis,
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
              SizedBox(height: isTightCard ? DS.spacing8 : DS.spacing12),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: isTightCard ? DS.spacing6 : DS.spacing8,
                children: [
                  OpenClawMetricPill(
                    icon: hasExecutionPermissionIssue
                        ? Icons.key_off_rounded
                        : hasExecutionEndpointIssue
                            ? Icons.route_rounded
                            : Icons.sensors_rounded,
                    label: hasExecutionPermissionIssue
                        ? '已连接但无执行权限'
                        : hasExecutionEndpointIssue
                            ? '已连接但执行入口异常'
                            : isGatewayReachable
                                ? '已连接'
                                : '未连接',
                    tone: connectionTone,
                    emphasized:
                        isGatewayReachable || hasExecutionPermissionIssue,
                  ),
                  OpenClawMetricPill(
                    icon: Icons.schedule_rounded,
                    label: '${connection.queuedRequestCount} 排队中',
                    tone: queueTone,
                    emphasized: hasQueue,
                  ),
                ],
              ),
              SizedBox(height: isTightCard ? DS.spacing8 : DS.spacing12),
              Text(
                summary,
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
                maxLines: isTightCard ? 1 : 2,
                overflow: TextOverflow.ellipsis,
              ),
              SizedBox(height: isTightCard ? DS.spacing6 : DS.spacing10),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  actionLabel,
                  style: (isTightCard
                          ? context.sparkleTypography.labelLarge.copyWith(
                              fontSize: 13,
                              height: 1.1,
                            )
                          : context.sparkleTypography.labelLarge)
                      .copyWith(
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
