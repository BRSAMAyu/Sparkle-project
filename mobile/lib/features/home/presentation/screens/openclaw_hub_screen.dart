import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/features/settings/presentation/widgets/openclaw_connection_panel.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

enum OpenClawHubSection {
  overview,
  connection,
  delegate,
  activity;

  static OpenClawHubSection fromQuery(String? value) {
    switch (value) {
      case 'connection':
        return OpenClawHubSection.connection;
      case 'delegate':
        return OpenClawHubSection.delegate;
      case 'activity':
        return OpenClawHubSection.activity;
      default:
        return OpenClawHubSection.overview;
    }
  }

  String get queryValue => switch (this) {
        OpenClawHubSection.connection => 'connection',
        OpenClawHubSection.delegate => 'delegate',
        OpenClawHubSection.activity => 'activity',
        OpenClawHubSection.overview => 'overview',
      };
}

const _openClawHubOrigin = '/openclaw';

class OpenClawHubScreen extends ConsumerStatefulWidget {
  const OpenClawHubScreen({
    super.key,
    this.initialSection = OpenClawHubSection.overview,
  });

  final OpenClawHubSection initialSection;

  @override
  ConsumerState<OpenClawHubScreen> createState() => _OpenClawHubScreenState();
}

class _OpenClawHubScreenState extends ConsumerState<OpenClawHubScreen> {
  final ScrollController _scrollController = ScrollController();
  final GlobalKey _connectionKey = GlobalKey();
  final GlobalKey _delegateKey = GlobalKey();
  final GlobalKey _activityKey = GlobalKey();
  bool _didPrime = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      await _primeExecutionState();
      _jumpToInitialSection();
    });
  }

  Future<void> _primeExecutionState() async {
    if (_didPrime) return;
    _didPrime = true;

    final notifier = ref.read(taskListProvider.notifier);
    await notifier.loadTodayTasks();
    await notifier.loadRecommendedTasks();
    if (!mounted) return;

    final state = ref.read(taskListProvider);
    final candidates = <TaskModel>[
      ...state.todayTasks,
      ...state.recommendedTasks,
    ];
    final seen = <String>{};
    for (final task in candidates) {
      if (!seen.add(task.id)) continue;
      unawaited(notifier.loadTaskExecutionState(task.id));
      unawaited(notifier.loadTaskExecutionTemplates(task.id));
      if (seen.length >= 5) break;
    }
  }

  void _jumpToInitialSection() {
    final key = switch (widget.initialSection) {
      OpenClawHubSection.connection => _connectionKey,
      OpenClawHubSection.delegate => _delegateKey,
      OpenClawHubSection.activity => _activityKey,
      OpenClawHubSection.overview => null,
    };
    if (key?.currentContext == null) return;
    unawaited(Scrollable.ensureVisible(
      key!.currentContext!,
      duration: DS.durationNormal,
      curve: Curves.easeOutCubic,
      alignment: 0.08,
    ));
  }

  Future<void> _retryQueuedRequests(OpenClawConnectionService service) async {
    if (!service.isConnected) {
      _showSnackBar('执行引擎尚未连接，暂时无法重试队列', isError: true);
      return;
    }
    final dispatched =
        await ref.read(taskListProvider.notifier).drainQueuedAiHandoffs();
    if (!mounted) return;
    _showSnackBar(
      dispatched > 0 ? '已重新提交 $dispatched 个排队任务' : '当前没有可重试的排队任务',
      isError: false,
    );
  }

  Future<void> _clearQueuedRequests(OpenClawConnectionService service) async {
    await service.clearQueuedRequests();
    if (!mounted) return;
    _showSnackBar('等待队列已清空');
  }

  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? DS.semanticError : DS.semanticSuccess,
      ),
    );
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final connection = ref.watch(openClawConnectionProvider);
    final taskState = ref.watch(taskListProvider);
    final info = connection.info;
    final statusColor = switch (info.status) {
      OpenClawConnectionStatus.connected => DS.semanticSuccess,
      OpenClawConnectionStatus.connecting => DS.info,
      OpenClawConnectionStatus.error => DS.semanticError,
      OpenClawConnectionStatus.disconnected => DS.textTertiary,
    };

    final allTasks = <TaskModel>[
      ...taskState.todayTasks,
      ...taskState.recommendedTasks,
      ...taskState.tasks,
    ];
    final taskMap = <String, TaskModel>{};
    for (final task in allTasks) {
      taskMap.putIfAbsent(task.id, () => task);
    }

    final recentTasks = taskMap.values.where((task) {
      return taskState.taskExecutions.containsKey(task.id) ||
          taskState.taskExecutionRecords.containsKey(task.id);
    }).toList()
      ..sort((left, right) {
        final leftAt =
            taskState.taskExecutions[left.id]?.createdAt ?? DateTime(1970);
        final rightAt =
            taskState.taskExecutions[right.id]?.createdAt ?? DateTime(1970);
        return rightAt.compareTo(leftAt);
      });

    final templateNames = taskState.taskExecutionTemplates.values
        .expand((templates) => templates)
        .map((template) => template.name)
        .toSet()
        .take(6)
        .toList(growable: false);

    return SparklePageScaffold(
      role: SparklePageRole.dashboard,
      appBar: AppBar(
        title: const Text('OpenClaw 执行中心'),
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          controller: _scrollController,
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 56,
                          height: 56,
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: [
                                DS.brandPrimaryConst,
                                Color.lerp(
                                      DS.brandPrimaryConst,
                                      DS.info,
                                      0.45,
                                    ) ??
                                    DS.info,
                              ],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                            borderRadius: BorderRadius.circular(18),
                          ),
                          child: const Icon(
                            Icons.cloud_sync_rounded,
                            color: Colors.white,
                            size: 28,
                          ),
                        ),
                        const SizedBox(width: DS.spacing12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'OpenClaw 执行中心',
                                style: Theme.of(context)
                                    .textTheme
                                    .titleLarge
                                    ?.copyWith(
                                      fontWeight: DS.fontWeightBold,
                                    ),
                              ),
                              const SizedBox(height: DS.spacing6),
                              Text(
                                '把连接状态、队列、委派入口和最近执行放到一个完整空间里，避免在任务页和聊天页里反复打断你。',
                                style: DS.bodySmall.copyWith(
                                  color: DS.textSecondary,
                                  height: 1.5,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing16),
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: [
                        _HubStatChip(
                          icon: Icons.sensors_rounded,
                          label: connection.isConnected ? '已连接' : '未连接',
                          color: statusColor,
                        ),
                        _HubStatChip(
                          icon: Icons.schedule_rounded,
                          label: '${connection.queuedRequestCount} 个排队任务',
                          color: connection.queuedRequestCount > 0
                              ? DS.warning
                              : DS.textSecondary,
                        ),
                        _HubStatChip(
                          icon: Icons.auto_awesome_rounded,
                          label: recentTasks.isEmpty
                              ? '暂无最近执行'
                              : '最近执行 ${taskState.taskExecutions[recentTasks.first.id]?.statusLabel ?? '可查看'}',
                          color: recentTasks.isEmpty
                              ? DS.textSecondary
                              : DS.brandPrimaryConst,
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing16),
                    Wrap(
                      spacing: DS.spacing10,
                      runSpacing: DS.spacing10,
                      children: [
                        FilledButton.icon(
                          onPressed: () => Scrollable.ensureVisible(
                            _connectionKey.currentContext!,
                            duration: DS.durationNormal,
                            curve: Curves.easeOutCubic,
                            alignment: 0.08,
                          ),
                          icon: const Icon(Icons.settings_rounded),
                          label: const Text('连接与控制'),
                        ),
                        OutlinedButton.icon(
                          onPressed: () => Scrollable.ensureVisible(
                            _delegateKey.currentContext!,
                            duration: DS.durationNormal,
                            curve: Curves.easeOutCubic,
                            alignment: 0.08,
                          ),
                          icon: const Icon(
                              Icons.playlist_add_check_circle_rounded),
                          label: const Text('队列与委派'),
                        ),
                        TextButton.icon(
                          onPressed: () => Scrollable.ensureVisible(
                            _activityKey.currentContext!,
                            duration: DS.durationNormal,
                            curve: Curves.easeOutCubic,
                            alignment: 0.08,
                          ),
                          icon: const Icon(Icons.history_rounded),
                          label: const Text('最近活动'),
                        ),
                        OutlinedButton.icon(
                          onPressed: () => context.push('/chat'),
                          icon: const Icon(Icons.chat_bubble_outline_rounded),
                          label: const Text('进入聊天'),
                        ),
                        OutlinedButton.icon(
                          onPressed: () => context.push('/tasks'),
                          icon: const Icon(Icons.task_alt_rounded),
                          label: const Text('查看任务'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing16),
              _HubSection(
                title: '引擎状态',
                subtitle: '查看 OpenClaw 当前健康、节点能力和设备配对状态。',
                child: GraphiteCardSurface(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 12,
                            height: 12,
                            decoration: BoxDecoration(
                              color: statusColor,
                              borderRadius: BorderRadius.circular(99),
                            ),
                          ),
                          const SizedBox(width: DS.spacing8),
                          Text(
                            switch (info.status) {
                              OpenClawConnectionStatus.connected => '已连接',
                              OpenClawConnectionStatus.connecting => '连接中...',
                              OpenClawConnectionStatus.error => '连接失败',
                              OpenClawConnectionStatus.disconnected => '未连接',
                            },
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(fontWeight: DS.fontWeightBold),
                          ),
                          const Spacer(),
                          if (info.latencyMs != null)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: DS.spacing8,
                                vertical: DS.spacing4,
                              ),
                              decoration: BoxDecoration(
                                color: statusColor.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(999),
                              ),
                              child: Text(
                                '${info.latencyMs}ms',
                                style:
                                    DS.bodySmall.copyWith(color: statusColor),
                              ),
                            ),
                        ],
                      ),
                      if ((info.errorMessage ?? '').isNotEmpty) ...[
                        const SizedBox(height: DS.spacing8),
                        Text(
                          info.errorMessage!,
                          style: DS.bodySmall.copyWith(color: DS.semanticError),
                        ),
                      ],
                      const SizedBox(height: DS.spacing12),
                      Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing8,
                        children: [
                          _InfoPill(
                            label: '节点 ${info.nodeCount ?? 0}',
                            color: DS.info,
                          ),
                          _InfoPill(
                            label:
                                connection.config.isPaired ? '已配对设备' : '未配对设备',
                            color: connection.config.isPaired
                                ? DS.semanticSuccess
                                : DS.warning,
                          ),
                          _InfoPill(
                            label: connection.config.transport == 'gateway_ws'
                                ? 'WebSocket'
                                : 'HTTP',
                            color: DS.brandPrimaryConst,
                          ),
                        ],
                      ),
                      if ((info.capabilities ?? const []).isNotEmpty) ...[
                        const SizedBox(height: DS.spacing12),
                        Text(
                          '能力矩阵',
                          style: DS.bodySmall.copyWith(
                            color: DS.textSecondary,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                        const SizedBox(height: DS.spacing8),
                        Wrap(
                          spacing: DS.spacing8,
                          runSpacing: DS.spacing8,
                          children: (info.capabilities ?? const [])
                              .map(
                                (capability) => Chip(
                                  label: Text(capability),
                                  side: BorderSide.none,
                                  backgroundColor: DS.surfaceSecondary,
                                ),
                              )
                              .toList(growable: false),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              _HubSection(
                key: _connectionKey,
                title: '连接与控制',
                subtitle: '修复后的连接表单只在首次进入时同步配置，之后由你的当前输入驱动。',
                child: GraphiteCardSurface(
                  child: const OpenClawConnectionPanel(),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              _HubSection(
                key: _delegateKey,
                title: '队列与委派',
                subtitle: '离线时先排队，恢复后再统一提交；把 OpenClaw 变成稳定可控的执行器。',
                child: GraphiteCardSurface(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (connection.queuedRequests.isEmpty)
                        Text(
                          '当前没有等待中的委派任务。你可以从任务页或聊天建议卡把工作交给 OpenClaw。',
                          style: DS.bodySmall.copyWith(
                            color: DS.textSecondary,
                            height: 1.5,
                          ),
                        )
                      else ...[
                        Text(
                          '等待队列',
                          style: Theme.of(context)
                              .textTheme
                              .titleMedium
                              ?.copyWith(fontWeight: DS.fontWeightBold),
                        ),
                        const SizedBox(height: DS.spacing8),
                        ...connection.queuedRequests.take(5).map(
                              (request) => Padding(
                                padding:
                                    const EdgeInsets.only(bottom: DS.spacing8),
                                child: Container(
                                  width: double.infinity,
                                  padding: const EdgeInsets.all(DS.spacing12),
                                  decoration: BoxDecoration(
                                    color: DS.surfaceSecondary,
                                    borderRadius: BorderRadius.circular(14),
                                  ),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        (request.goal?.trim().isNotEmpty ??
                                                false)
                                            ? request.goal!
                                            : '任务 ${request.taskId}',
                                        style: DS.bodySmall.copyWith(
                                          fontWeight: DS.fontWeightBold,
                                        ),
                                      ),
                                      const SizedBox(height: DS.spacing4),
                                      Text(
                                        [
                                          if ((request.templateId ?? '')
                                              .isNotEmpty)
                                            '模板 ${request.templateId}',
                                          '来源 ${request.source}',
                                        ].join(' · '),
                                        style: DS.bodySmall.copyWith(
                                          color: DS.textSecondary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                        const SizedBox(height: DS.spacing8),
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: () =>
                                    unawaited(_retryQueuedRequests(connection)),
                                child: const Text('重试队列'),
                              ),
                            ),
                            const SizedBox(width: DS.spacing12),
                            Expanded(
                              child: TextButton(
                                onPressed: () =>
                                    unawaited(_clearQueuedRequests(connection)),
                                child: Text(
                                  '清空队列',
                                  style: DS.bodyMedium.copyWith(
                                    color: DS.semanticError,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                      const SizedBox(height: DS.spacing16),
                      Text(
                        '可用模板 / 能力说明',
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(fontWeight: DS.fontWeightBold),
                      ),
                      const SizedBox(height: DS.spacing8),
                      if (templateNames.isEmpty)
                        Text(
                          '模板会在你打开具体任务后按需加载；当前可以先通过连接状态和能力矩阵判断引擎是否准备好接单。',
                          style: DS.bodySmall.copyWith(
                            color: DS.textSecondary,
                            height: 1.5,
                          ),
                        )
                      else
                        Wrap(
                          spacing: DS.spacing8,
                          runSpacing: DS.spacing8,
                          children: templateNames
                              .map(
                                (name) => Chip(
                                  label: Text(name),
                                  side: BorderSide.none,
                                  backgroundColor: DS.surfaceSecondary,
                                ),
                              )
                              .toList(growable: false),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              _HubSection(
                key: _activityKey,
                title: '最近活动',
                subtitle: '最近的委派结果会在这里集中显示，避免你在任务页之间反复查找。',
                child: GraphiteCardSurface(
                  child: recentTasks.isEmpty
                      ? Text(
                          '暂时还没有最近执行。你可以从首页卡牌、任务执行页或聊天入口发起第一笔委派。',
                          style: DS.bodySmall.copyWith(
                            color: DS.textSecondary,
                            height: 1.5,
                          ),
                        )
                      : Column(
                          children: recentTasks.take(5).map((task) {
                            final intent = taskState.taskExecutions[task.id];
                            final record =
                                taskState.taskExecutionRecords[task.id];
                            final statusColor = _statusColorForIntent(intent);
                            return Padding(
                              padding:
                                  const EdgeInsets.only(bottom: DS.spacing10),
                              child: Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(DS.spacing12),
                                decoration: BoxDecoration(
                                  color: DS.surfaceSecondary,
                                  borderRadius: BorderRadius.circular(14),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            task.title,
                                            style: DS.bodyMedium.copyWith(
                                              fontWeight: DS.fontWeightBold,
                                            ),
                                          ),
                                        ),
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: DS.spacing8,
                                            vertical: DS.spacing4,
                                          ),
                                          decoration: BoxDecoration(
                                            color: statusColor.withValues(
                                              alpha: 0.12,
                                            ),
                                            borderRadius:
                                                BorderRadius.circular(999),
                                          ),
                                          child: Text(
                                            intent?.statusLabel ?? '已记录',
                                            style: DS.bodySmall.copyWith(
                                              color: statusColor,
                                              fontWeight: DS.fontWeightBold,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: DS.spacing6),
                                    Text(
                                      record?.errorMessage ??
                                          record?.trustLabel ??
                                          intent?.goal ??
                                          '可继续查看该任务的执行详情。',
                                      style: DS.bodySmall.copyWith(
                                        color: DS.textSecondary,
                                        height: 1.45,
                                      ),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    const SizedBox(height: DS.spacing10),
                                    Align(
                                      alignment: Alignment.centerLeft,
                                      child: TextButton.icon(
                                        onPressed: () => context.push(
                                          '/tasks/${task.id}/execute?origin=${Uri.encodeComponent(_openClawHubOrigin)}',
                                        ),
                                        icon: const Icon(
                                          Icons.open_in_new_rounded,
                                          size: 16,
                                        ),
                                        label: const Text('打开任务执行'),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          }).toList(growable: false),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _statusColorForIntent(ExecutionIntentModel? intent) {
    switch (intent?.status) {
      case ExecutionIntentStatus.succeeded:
        return DS.semanticSuccess;
      case ExecutionIntentStatus.partial:
      case ExecutionIntentStatus.waitingApproval:
        return DS.warning;
      case ExecutionIntentStatus.failed:
      case ExecutionIntentStatus.timedOut:
      case ExecutionIntentStatus.canceled:
        return DS.semanticError;
      case ExecutionIntentStatus.running:
      case ExecutionIntentStatus.dispatched:
        return DS.info;
      case ExecutionIntentStatus.handedBack:
      case ExecutionIntentStatus.unknown:
      case ExecutionIntentStatus.draft:
      case ExecutionIntentStatus.ready:
      case null:
        return DS.textSecondary;
    }
  }
}

class _HubSection extends StatelessWidget {
  const _HubSection({
    required this.title,
    required this.subtitle,
    required this.child,
    super.key,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            subtitle,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.45,
            ),
          ),
          const SizedBox(height: DS.spacing10),
          child,
        ],
      );
}

class _HubStatChip extends StatelessWidget {
  const _HubStatChip({
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
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: color),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: DS.bodySmall.copyWith(
                color: color,
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ],
        ),
      );
}

class _InfoPill extends StatelessWidget {
  const _InfoPill({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: DS.bodySmall.copyWith(
            color: color,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}
