import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/features/openclaw/presentation/widgets/openclaw_primitives.dart';
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
  late bool _connectionExpanded;
  late bool _delegateExpanded;
  late bool _activityExpanded;

  @override
  void initState() {
    super.initState();
    _connectionExpanded =
        widget.initialSection == OpenClawHubSection.connection;
    _delegateExpanded = widget.initialSection == OpenClawHubSection.delegate;
    _activityExpanded = widget.initialSection == OpenClawHubSection.activity;
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      await _primeExecutionState();
      _jumpToInitialSection();
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
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
    unawaited(
      Scrollable.ensureVisible(
        key!.currentContext!,
        duration: DS.durationNormal,
        curve: Curves.easeOutCubic,
        alignment: 0.08,
      ),
    );
  }

  Future<void> _focusSection(GlobalKey key, VoidCallback onExpand) async {
    onExpand();
    await Future<void>.delayed(const Duration(milliseconds: 16));
    if (!mounted || key.currentContext == null) return;
    await Scrollable.ensureVisible(
      key.currentContext!,
      duration: DS.durationNormal,
      curve: Curves.easeOutCubic,
      alignment: 0.08,
    );
  }

  Future<void> _retryQueuedRequests(OpenClawConnectionService service) async {
    if (!service.isConnected) {
      _showSnackBar(
        service.hasExecutionPermissionIssue
            ? '当前网关可访问，但没有执行权限，暂时无法重试队列'
            : service.hasExecutionEndpointIssue
                ? '当前网关可访问，但执行入口不可用，暂时无法重试队列'
                : '执行引擎尚未连接，暂时无法重试队列',
        isError: true,
      );
      return;
    }
    final dispatched =
        await ref.read(taskListProvider.notifier).drainQueuedAiHandoffs();
    if (!mounted) return;
    _showSnackBar(
      dispatched > 0 ? '已重新提交 $dispatched 个排队任务' : '当前没有可重试的排队任务',
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
  Widget build(BuildContext context) {
    final connection = ref.watch(openClawConnectionProvider);
    final taskState = ref.watch(taskListProvider);
    final info = connection.info;

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

    final latestTask = recentTasks.isEmpty ? null : recentTasks.first;
    final latestIntent =
        latestTask == null ? null : taskState.taskExecutions[latestTask.id];
    final latestRecord = latestTask == null
        ? null
        : taskState.taskExecutionRecords[latestTask.id];
    final hasExecutionPermissionIssue = connection.hasExecutionPermissionIssue;
    final hasExecutionEndpointIssue = connection.hasExecutionEndpointIssue;
    final isGatewayReachable = connection.isGatewayReachable;

    final overviewTone = connection.isConnected
        ? OpenClawVisualTone.connected
        : isGatewayReachable
            ? OpenClawVisualTone.attention
            : connection.queuedRequestCount > 0
                ? OpenClawVisualTone.offline
                : info.status == OpenClawConnectionStatus.connecting
                    ? OpenClawVisualTone.active
                    : OpenClawVisualTone.attention;
    final overviewTitle = switch ((
      hasExecutionPermissionIssue,
      hasExecutionEndpointIssue,
      connection.isConnected,
      connection.queuedRequestCount > 0,
      connection.config.isConfigured
    )) {
      (true, _, _, _, _) => '网关在线，但没有执行权限',
      (false, true, _, _, _) => '网关在线，但执行入口不可用',
      (false, false, true, _, _) => 'OpenClaw 已准备好接手',
      (false, false, false, true, _) => '已有任务在等它恢复',
      (false, false, false, false, true) => '连接信息已保存，当前还没连上',
      _ => '先接入 OpenClaw，再开始稳定委派',
    };
    final overviewSubtitle = switch ((
      hasExecutionPermissionIssue,
      hasExecutionEndpointIssue,
      connection.isConnected,
      latestIntent != null,
      connection.queuedRequestCount > 0
    )) {
      (true, _, _, _, _) =>
        '当前这台网关可以访问，但真正执行会被权限拦住。先补可写 scope，或改用设备配对 + WebSocket，才算闭环接通。',
      (false, true, _, _, _) =>
        '当前地址本身可访问，但执行接口还没准备好。优先检查 `/v1/responses`、代理转发和 transport 选择是否一致。',
      (false, false, true, true, _) =>
        '最近一次执行状态是“${latestIntent?.statusLabel ?? '已记录'}”，你可以从这里继续查看连接、队列和活动。',
      (false, false, true, false, _) => '连接保持正常，适合从任务页或聊天页直接把网页调研、整理和抓取类任务交给它。',
      (false, false, false, _, true) =>
        '你已经有 ${connection.queuedRequestCount} 个委派在等待恢复连接，先把引擎重新连上会最有效。',
      _ => '连接完成后，首页、聊天和任务页会共享同一个执行中心，不再四处寻找入口。',
    };
    final primaryActionHint = switch ((
      hasExecutionPermissionIssue,
      hasExecutionEndpointIssue,
      connection.isConnected,
      connection.queuedRequestCount > 0
    )) {
      (true, _, _, _) => '现在最值得先做的是更换具备执行权限的令牌，或切到已配对的 WebSocket 连接。',
      (false, true, _, _) => '现在最值得先做的是检查执行接口与 transport，让网关从“可达”变成“可执行”。',
      (false, false, true, true) => '现在最值得先做的是把等待队列重新提交。',
      (false, false, false, true) => '现在最值得先做的是恢复连接，让已排队的任务继续执行。',
      (false, false, true, false) => '现在最值得先做的是回到聊天或任务页发起新的委派。',
      _ => '现在最值得先做的是完成连接，让 OpenClaw 真正成为你的执行伴侣。',
    };

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
              OpenClawStatusCapsule(
                title: overviewTitle,
                subtitle: overviewSubtitle,
                tone: overviewTone,
                showToggle: false,
                metrics: [
                  OpenClawMetricPill(
                    icon: Icons.sensors_rounded,
                    label: connection.hasExecutionPermissionIssue
                        ? '已连接但无执行权限'
                        : connection.hasExecutionEndpointIssue
                            ? '已连接但执行入口异常'
                            : isGatewayReachable
                                ? '已连接'
                                : '未连接',
                    tone:
                        hasExecutionPermissionIssue || hasExecutionEndpointIssue
                            ? OpenClawVisualTone.attention
                            : isGatewayReachable
                                ? OpenClawVisualTone.connected
                                : OpenClawVisualTone.offline,
                    emphasized: isGatewayReachable,
                  ),
                  OpenClawMetricPill(
                    icon: Icons.schedule_rounded,
                    label: '${connection.queuedRequestCount} 个排队任务',
                    tone: connection.queuedRequestCount > 0
                        ? OpenClawVisualTone.offline
                        : OpenClawVisualTone.active,
                    emphasized: connection.queuedRequestCount > 0,
                  ),
                  if (info.nodeCount != null)
                    OpenClawMetricPill(
                      icon: Icons.hub_rounded,
                      label: '${info.nodeCount} 个节点',
                      tone: OpenClawVisualTone.active,
                    ),
                  OpenClawMetricPill(
                    icon: connection.config.transport == 'gateway_ws'
                        ? Icons.wifi_tethering_rounded
                        : Icons.http_rounded,
                    label: connection.config.transport == 'gateway_ws'
                        ? 'WebSocket'
                        : 'HTTP',
                    tone: OpenClawVisualTone.active,
                  ),
                  OpenClawMetricPill(
                    icon: connection.config.isPaired
                        ? Icons.devices_rounded
                        : Icons.key_rounded,
                    label: connection.config.isPaired ? '已配对设备' : '令牌认证',
                    tone: connection.config.isPaired
                        ? OpenClawVisualTone.connected
                        : OpenClawVisualTone.attention,
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: DS.spacing10,
                      runSpacing: DS.spacing10,
                      children: [
                        FilledButton.icon(
                          onPressed: () => _focusSection(
                            _connectionKey,
                            () => setState(() => _connectionExpanded = true),
                          ),
                          icon: const Icon(Icons.settings_rounded),
                          label: const Text('继续设置'),
                        ),
                        OutlinedButton.icon(
                          onPressed: () => _focusSection(
                            _delegateKey,
                            () => setState(() => _delegateExpanded = true),
                          ),
                          icon: const Icon(Icons.schedule_send_rounded),
                          label: const Text('查看队列'),
                        ),
                        TextButton.icon(
                          onPressed: () => context.push('/chat'),
                          icon: const Icon(Icons.chat_bubble_outline_rounded),
                          label: const Text('进入聊天'),
                        ),
                        TextButton.icon(
                          onPressed: () => context.push('/tasks'),
                          icon: const Icon(Icons.task_alt_rounded),
                          label: const Text('查看任务'),
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing12),
                    Text(
                      primaryActionHint,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: DS.fontWeightSemiBold,
                            color: DS.textPrimary,
                          ),
                    ),
                    if ((info.capabilities ?? const []).isNotEmpty) ...[
                      const SizedBox(height: DS.spacing10),
                      Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing8,
                        children: (info.capabilities ?? const [])
                            .take(6)
                            .map(
                              (capability) => OpenClawMetricPill(
                                icon: Icons.auto_awesome_rounded,
                                label: capability,
                                tone: OpenClawVisualTone.active,
                              ),
                            )
                            .toList(growable: false),
                      ),
                    ],
                    if ((info.errorMessage ?? '').isNotEmpty) ...[
                      const SizedBox(height: DS.spacing10),
                      Text(
                        info.errorMessage!,
                        style: DS.bodySmall.copyWith(
                          color: DS.semanticError,
                          height: 1.45,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing16),
              OpenClawSectionSurface(
                key: _connectionKey,
                icon: Icons.link_rounded,
                title: '连接与控制',
                subtitle: '先用摘要看清当前连接，再决定是否展开编辑，避免一进来就被整张表单打断。',
                tone: connection.isConnected
                    ? OpenClawVisualTone.connected
                    : OpenClawVisualTone.attention,
                expanded: _connectionExpanded,
                toggleLabel: _connectionExpanded ? '收起连接编辑' : '编辑连接方式',
                onToggle: () {
                  setState(() => _connectionExpanded = !_connectionExpanded);
                },
                summary: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: [
                        OpenClawMetricPill(
                          icon: Icons.public_rounded,
                          label: connection.config.isConfigured
                              ? connection.config.normalizedGatewayUrl
                              : '尚未填写网关地址',
                          tone: connection.config.isConfigured
                              ? OpenClawVisualTone.active
                              : OpenClawVisualTone.offline,
                        ),
                        if (info.latencyMs != null)
                          OpenClawMetricPill(
                            icon: Icons.speed_rounded,
                            label: '${info.latencyMs}ms',
                            tone: OpenClawVisualTone.connected,
                          ),
                        OpenClawMetricPill(
                          icon: connection.config.transport == 'gateway_ws'
                              ? Icons.wifi_tethering_rounded
                              : Icons.http_rounded,
                          label: connection.config.transport == 'gateway_ws'
                              ? 'WebSocket'
                              : 'HTTP',
                          tone: OpenClawVisualTone.active,
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing10),
                    Text(
                      connection.hasExecutionPermissionIssue
                          ? '这台网关已经能访问，但当前认证没有真正发起执行的权限；更适合先修权限，再统一重试队列。'
                          : connection.hasExecutionEndpointIssue
                              ? '网关本身可达，但执行接口还没准备好；先检查 transport 和 `/v1/responses` 会更有效。'
                              : connection.isConnected
                                  ? '当前连接保持稳定，适合继续使用现有方式直接委派。'
                                  : connection.config.isConfigured
                                      ? '配置已经在本地保存好，展开后可以微调认证方式、协议和配对流程。'
                                      : '第一次接入通常只需要填地址，再选择令牌认证或设备配对中的一种。',
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
                  ],
                ),
                expandedChild: const OpenClawConnectionPanel(compact: true),
              ),
              const SizedBox(height: DS.spacing16),
              OpenClawSectionSurface(
                key: _delegateKey,
                icon: Icons.playlist_add_check_circle_rounded,
                title: '队列与委派',
                subtitle: '让你先知道现在最该做什么，再决定是否展开看完整队列和模板能力。',
                tone: connection.queuedRequests.isNotEmpty
                    ? OpenClawVisualTone.offline
                    : OpenClawVisualTone.active,
                expanded: _delegateExpanded,
                toggleLabel: _delegateExpanded ? '收起队列详情' : '查看全部队列',
                onToggle: () {
                  setState(() => _delegateExpanded = !_delegateExpanded);
                },
                summary: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      connection.isConnected &&
                              connection.queuedRequests.isNotEmpty
                          ? '你现在最适合先把排队任务重新提交，等引擎把积压处理完再发起新的委派。'
                          : !connection.isConnected &&
                                  connection.queuedRequests.isNotEmpty
                              ? '你已经把任务排好了，下一步先恢复连接，之后就能一口气继续执行。'
                              : connection.isConnected
                                  ? '当前没有等待中的任务，最适合回到聊天或任务页发起新的委派。'
                                  : '当前也没有排队任务，可以先完成连接，再决定要不要开始第一笔委派。',
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    if (connection.queuedRequests.isEmpty)
                      const OpenClawMetricPill(
                        icon: Icons.inbox_rounded,
                        label: '等待队列当前为空',
                        tone: OpenClawVisualTone.active,
                      )
                    else
                      ...connection.queuedRequests.take(3).map(
                            (request) => Padding(
                              padding:
                                  const EdgeInsets.only(bottom: DS.spacing8),
                              child: _QueuePreviewCard(request: request),
                            ),
                          ),
                  ],
                ),
                expandedChild: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (connection.queuedRequests.isNotEmpty) ...[
                      ...connection.queuedRequests.take(8).map(
                            (request) => Padding(
                              padding:
                                  const EdgeInsets.only(bottom: DS.spacing8),
                              child: _QueuePreviewCard(request: request),
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
                      const SizedBox(height: DS.spacing16),
                    ],
                    Text(
                      '可用模板 / 能力说明',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    if (templateNames.isEmpty)
                      Text(
                        '模板会在你打开具体任务后按需加载；现在可以先把连接、队列和最近活动整理顺，再回到具体任务开始委派。',
                        style: DS.bodySmall.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                      )
                    else
                      Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing8,
                        children: templateNames
                            .map(
                              (name) => OpenClawMetricPill(
                                icon: Icons.auto_awesome_rounded,
                                label: name,
                                tone: OpenClawVisualTone.active,
                              ),
                            )
                            .toList(growable: false),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing16),
              OpenClawSectionSurface(
                key: _activityKey,
                icon: Icons.history_rounded,
                title: '最近活动',
                subtitle: '用高密度时间线看最近的委派，不需要再在不同任务页之间来回翻找。',
                tone: latestIntent?.isTerminal ?? false
                    ? OpenClawVisualTone.connected
                    : OpenClawVisualTone.active,
                expanded: _activityExpanded,
                toggleLabel: _activityExpanded ? '收起活动详情' : '查看全部活动',
                onToggle: () {
                  setState(() => _activityExpanded = !_activityExpanded);
                },
                summary: recentTasks.isEmpty
                    ? Text(
                        '暂时还没有最近执行。你可以从首页卡牌、任务执行页或聊天入口发起第一笔委派。',
                        style: DS.bodySmall.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                      )
                    : Column(
                        children: recentTasks.take(3).map((task) {
                          final intent = taskState.taskExecutions[task.id];
                          final record =
                              taskState.taskExecutionRecords[task.id];
                          return Padding(
                            padding: const EdgeInsets.only(bottom: DS.spacing8),
                            child: _ActivityTimelineCard(
                              task: task,
                              intent: intent,
                              recordHint: record?.trustLabel,
                            ),
                          );
                        }).toList(growable: false),
                      ),
                expandedChild: recentTasks.isEmpty
                    ? null
                    : Column(
                        children: recentTasks.take(5).map((task) {
                          final intent = taskState.taskExecutions[task.id];
                          final record =
                              taskState.taskExecutionRecords[task.id];
                          return Padding(
                            padding:
                                const EdgeInsets.only(bottom: DS.spacing10),
                            child: _ActivityTimelineCard(
                              task: task,
                              intent: intent,
                              recordHint:
                                  record?.errorMessage ?? record?.trustLabel,
                              showAction: true,
                            ),
                          );
                        }).toList(growable: false),
                      ),
              ),
              if (latestRecord != null &&
                  (latestRecord.trustLabel).isNotEmpty) ...[
                const SizedBox(height: DS.spacing4),
                Padding(
                  padding: const EdgeInsets.only(left: DS.spacing4),
                  child: Text(
                    '最近一次信任判断：${latestRecord.trustLabel}',
                    style: DS.bodySmall.copyWith(
                      color: DS.textSecondary,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
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

class _QueuePreviewCard extends StatelessWidget {
  const _QueuePreviewCard({required this.request});

  final OpenClawQueuedRequest request;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              (request.goal?.trim().isNotEmpty ?? false)
                  ? request.goal!
                  : '任务 ${request.taskId}',
              style: DS.bodySmall.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              [
                if ((request.templateId ?? '').isNotEmpty)
                  '模板 ${request.templateId}',
                '来源 ${request.source}',
              ].join(' · '),
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
      );
}

class _ActivityTimelineCard extends StatelessWidget {
  const _ActivityTimelineCard({
    required this.task,
    required this.intent,
    this.recordHint,
    this.showAction = false,
  });

  final TaskModel task;
  final ExecutionIntentModel? intent;
  final String? recordHint;
  final bool showAction;

  @override
  Widget build(BuildContext context) {
    final statusColor = _statusColorForIntent(intent);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 12,
            height: 12,
            margin: const EdgeInsets.only(top: 4),
            decoration: BoxDecoration(
              color: statusColor,
              borderRadius: BorderRadius.circular(999),
            ),
          ),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        task.title,
                        style: DS.bodyMedium.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    OpenClawMetricPill(
                      label: intent?.statusLabel ?? '已记录',
                      tone: switch (intent?.status) {
                        ExecutionIntentStatus.succeeded =>
                          OpenClawVisualTone.connected,
                        ExecutionIntentStatus.waitingApproval ||
                        ExecutionIntentStatus.partial =>
                          OpenClawVisualTone.attention,
                        ExecutionIntentStatus.failed ||
                        ExecutionIntentStatus.timedOut ||
                        ExecutionIntentStatus.canceled =>
                          OpenClawVisualTone.offline,
                        _ => OpenClawVisualTone.active,
                      },
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing6),
                Text(
                  (recordHint?.trim().isNotEmpty ?? false)
                      ? recordHint!
                      : (intent?.goal.trim().isNotEmpty ?? false)
                          ? intent!.goal
                          : '可继续查看该任务的执行详情。',
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.45,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                if (showAction) ...[
                  const SizedBox(height: DS.spacing10),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: () => context.push(
                        '/tasks/${task.id}/execute?origin=${Uri.encodeComponent(_openClawHubOrigin)}',
                      ),
                      icon: const Icon(Icons.open_in_new_rounded, size: 16),
                      label: const Text('打开任务执行'),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
