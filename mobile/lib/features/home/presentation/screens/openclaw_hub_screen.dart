import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/services/openclaw_automation_service.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/features/home/presentation/widgets/openclaw_automation_panel.dart';
import 'package:sparkle/features/home/presentation/widgets/openclaw_connection_diagnostics_sheet.dart';
import 'package:sparkle/features/home/presentation/widgets/openclaw_node_management_panel.dart';
import 'package:sparkle/features/openclaw/presentation/widgets/openclaw_primitives.dart';
import 'package:sparkle/features/settings/presentation/widgets/openclaw_connection_panel.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

enum OpenClawHubSection {
  overview,
  connection,
  delegate,
  automation,
  activity;

  static OpenClawHubSection fromQuery(String? value) {
    switch (value) {
      case 'connection':
        return OpenClawHubSection.connection;
      case 'delegate':
        return OpenClawHubSection.delegate;
      case 'automation':
        return OpenClawHubSection.automation;
      case 'activity':
        return OpenClawHubSection.activity;
      default:
        return OpenClawHubSection.overview;
    }
  }

  String get queryValue => switch (this) {
        OpenClawHubSection.connection => 'connection',
        OpenClawHubSection.delegate => 'delegate',
        OpenClawHubSection.automation => 'automation',
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
  final GlobalKey _devicesKey = GlobalKey();
  final GlobalKey _delegateKey = GlobalKey();
  final GlobalKey _automationKey = GlobalKey();
  final GlobalKey _activityKey = GlobalKey();
  bool _didPrime = false;
  late bool _connectionExpanded;
  late bool _devicesExpanded;
  late bool _delegateExpanded;
  late bool _automationExpanded;
  late bool _activityExpanded;

  @override
  void initState() {
    super.initState();
    _connectionExpanded =
        widget.initialSection == OpenClawHubSection.connection;
    _devicesExpanded = false;
    _delegateExpanded = widget.initialSection == OpenClawHubSection.delegate;
    _automationExpanded =
        widget.initialSection == OpenClawHubSection.automation;
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
      OpenClawHubSection.automation => _automationKey,
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
            ?             context.l10n.openclawHubGatewayNoPermission
            : service.hasExecutionEndpointIssue
                ? context.l10n.openclawHubEndpointUnavailable
                : context.l10n.openclawHubEngineNotConnected,
        isError: true,
      );
      return;
    }
    final dispatched =
        await ref.read(taskListProvider.notifier).drainQueuedAiHandoffs();
    if (!mounted) return;
    _showSnackBar(
      dispatched > 0 ? context.l10n.openclawHubRetryQueuedSuccess(dispatched) : context.l10n.openclawHubNoRetryQueuedItems,
    );
  }

  Future<void> _clearQueuedRequests(OpenClawConnectionService service) async {
    await service.clearQueuedRequests();
    if (!mounted) return;
    _showSnackBar(context.l10n.openclawHubQueueCleared);
  }

  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      isError
          ? SparkleSnackBar.error(message)
          : SparkleSnackBar.success(message),
    );
  }

  Future<void> _openDiagnostics(OpenClawConnectionService service) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => OpenClawConnectionDiagnosticsSheet(service: service),
    );
  }

  Color _statusIndicatorColor(OpenClawConnectionService connection) {
    if (connection.isConnected) {
      return DS.semanticSuccess;
    }
    if (connection.hasExecutionPermissionIssue ||
        connection.hasExecutionEndpointIssue ||
        connection.queuedRequestCount > 0 ||
        connection.info.status == OpenClawConnectionStatus.connecting) {
      return DS.semanticWarning;
    }
    return DS.textTertiary;
  }

  IconData _statusIndicatorIcon(OpenClawConnectionService connection) {
    if (connection.isConnected) {
      return Icons.wifi_tethering_rounded;
    }
    if (connection.hasExecutionPermissionIssue ||
        connection.hasExecutionEndpointIssue ||
        connection.queuedRequestCount > 0) {
      return Icons.network_check_rounded;
    }
    if (connection.info.status == OpenClawConnectionStatus.connecting) {
      return Icons.sync_rounded;
    }
    return Icons.portable_wifi_off_rounded;
  }

  String _statusIndicatorTooltip(OpenClawConnectionService connection) {
    if (connection.isConnected) {
      return context.l10n.openclawHubConnectedDiagnostics;
    }
    if (connection.hasExecutionPermissionIssue) {
      return context.l10n.openclawHubGatewayNoPermissionDiagnostics;
    }
    if (connection.hasExecutionEndpointIssue) {
      return context.l10n.openclawHubEndpointIssueDiagnostics;
    }
    if (connection.queuedRequestCount > 0) {
      return context.l10n.openclawHubQueuedTasksDiagnostics;
    }
    return context.l10n.openclawHubNotConnectedDiagnostics;
  }

  @override
  Widget build(BuildContext context) {
    final connection = ref.watch(openClawConnectionProvider);
    final automation = ref.watch(openClawAutomationProvider);
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

    final recentTasks = taskMap.values
        .where(
          (task) =>
              taskState.taskExecutions.containsKey(task.id) ||
              taskState.taskExecutionRecords.containsKey(task.id),
        )
        .toList()
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
      (true, _, _, _, _) => context.l10n.openclawHubOverviewGatewayNoPermission,
      (false, true, _, _, _) => context.l10n.openclawHubOverviewEndpointIssue,
      (false, false, true, _, _) => context.l10n.openclawHubOverviewReady,
      (false, false, false, true, _) => context.l10n.openclawHubOverviewTasksWaiting,
      (false, false, false, false, true) => context.l10n.openclawHubOverviewConfigSaved,
      _ => context.l10n.openclawHubOverviewConnectFirst,
    };
    final overviewSubtitle = switch ((
      hasExecutionPermissionIssue,
      hasExecutionEndpointIssue,
      connection.isConnected,
      latestIntent != null,
      connection.queuedRequestCount > 0
    )) {
      (true, _, _, _, _) =>
        context.l10n.openclawHubOverviewGatewayNoPermissionDesc,
      (false, true, _, _, _) =>
        context.l10n.openclawHubOverviewEndpointIssueDesc,
      (false, false, true, true, _) =>
        context.l10n.openclawHubLastExecutionStatus(latestIntent?.statusLabel ?? context.l10n.openclawHubStatusRecorded),
      (false, false, true, false, _) => context.l10n.openclawHubOverviewConnectedDesc,
      (false, false, false, _, true) =>
        context.l10n.openclawHubPendingDelegationsDesc(connection.queuedRequestCount),
      _ => context.l10n.openclawHubOverviewDefaultDesc,
    };
    final primaryActionHint = switch ((
      hasExecutionPermissionIssue,
      hasExecutionEndpointIssue,
      connection.isConnected,
      connection.queuedRequestCount > 0
    )) {
      (true, _, _, _) => context.l10n.openclawHubActionHintPermission,
      (false, true, _, _) => context.l10n.openclawHubActionHintEndpoint,
      (false, false, true, true) => context.l10n.openclawHubActionHintRetryQueue,
      (false, false, false, true) => context.l10n.openclawHubActionHintReconnect,
      (false, false, true, false) => context.l10n.openclawHubActionHintNewDelegation,
      _ => context.l10n.openclawHubActionHintCompleteConnection,
    };

    return SparklePageScaffold(
      role: SparklePageRole.dashboard,
      appBar: AppBar(
        title: Text(context.l10n.openclawHubAppBarTitle),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: DS.spacing12),
            child: Tooltip(
              message: _statusIndicatorTooltip(connection),
              child: IconButton(
                onPressed: () => _openDiagnostics(connection),
                icon: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    Icon(
                      _statusIndicatorIcon(connection),
                      color: _statusIndicatorColor(connection),
                    ),
                    Positioned(
                      right: -1,
                      top: -1,
                      child: Container(
                        width: 9,
                        height: 9,
                        decoration: BoxDecoration(
                          color: _statusIndicatorColor(connection),
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: Theme.of(context).scaffoldBackgroundColor,
                            width: 1.5,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
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
                        ? context.l10n.openclawHubMetricConnectedNoPermission
                        : connection.hasExecutionEndpointIssue
                            ? context.l10n.openclawHubMetricConnectedEndpointIssue
                            : isGatewayReachable
                                ? context.l10n.openclawHubMetricConnected
                                : context.l10n.openclawHubMetricNotConnected,
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
                    label: context.l10n.openclawHubQueuedTasksCount(connection.queuedRequestCount),
                    tone: connection.queuedRequestCount > 0
                        ? OpenClawVisualTone.offline
                        : OpenClawVisualTone.active,
                    emphasized: connection.queuedRequestCount > 0,
                  ),
                  if (info.nodeCount != null)
                    OpenClawMetricPill(
                      icon: Icons.hub_rounded,
                      label: context.l10n.openclawHubNodeCount(info.nodeCount!),
                    ),
                  OpenClawMetricPill(
                    icon: connection.config.transport == 'gateway_ws'
                        ? Icons.wifi_tethering_rounded
                        : Icons.http_rounded,
                    label: connection.config.transport == 'gateway_ws'
                        ? 'WebSocket'
                        : 'HTTP',
                  ),
                  OpenClawMetricPill(
                    icon: connection.config.isPaired
                        ? Icons.devices_rounded
                        : Icons.key_rounded,
                    label: connection.config.isPaired ? context.l10n.openclawHubMetricPairedDevice : context.l10n.openclawHubMetricTokenAuth,
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
                          label: Text(context.l10n.openclawHubButtonContinueSetup),
                        ),
                        OutlinedButton.icon(
                          onPressed: () => _focusSection(
                            _delegateKey,
                            () => setState(() => _delegateExpanded = true),
                          ),
                          icon: const Icon(Icons.schedule_send_rounded),
                          label: Text(context.l10n.openclawHubButtonViewQueue),
                        ),
                        OutlinedButton.icon(
                          onPressed: () => _focusSection(
                            _automationKey,
                            () => setState(() => _automationExpanded = true),
                          ),
                          icon: const Icon(Icons.auto_awesome_motion_rounded),
                          label: Text(context.l10n.openclawHubButtonAutomation),
                        ),
                        TextButton.icon(
                          onPressed: () => context.push('/chat'),
                          icon: const Icon(Icons.chat_bubble_outline_rounded),
                          label: Text(context.l10n.openclawHubButtonEnterChat),
                        ),
                        TextButton.icon(
                          onPressed: () => context.push('/tasks'),
                          icon: const Icon(Icons.task_alt_rounded),
                          label: Text(context.l10n.openclawHubButtonViewTasks),
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
                title: context.l10n.openclawHubSectionConnectionTitle,
                subtitle: context.l10n.openclawHubSectionConnectionSubtitle,
                tone: connection.isConnected
                    ? OpenClawVisualTone.connected
                    : OpenClawVisualTone.attention,
                expanded: _connectionExpanded,
                toggleLabel: _connectionExpanded ? context.l10n.openclawHubCollapseConnectionEdit : context.l10n.openclawHubExpandConnectionEdit,
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
                              : context.l10n.openclawHubGatewayUrlEmpty,
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
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing10),
                    Text(
                      connection.hasExecutionPermissionIssue
                          ? context.l10n.openclawHubConnectionSummaryPermission
                          : connection.hasExecutionEndpointIssue
                              ? context.l10n.openclawHubConnectionSummaryEndpoint
                              : connection.isConnected
                                  ? context.l10n.openclawHubConnectionSummaryConnected
                                  : connection.config.isConfigured
                                      ? context.l10n.openclawHubConnectionSummaryConfigured
                                      : context.l10n.openclawHubConnectionSummaryFirstTime,
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
                key: _devicesKey,
                icon: Icons.hub_rounded,
                title: context.l10n.openclawHubSectionDevicesTitle,
                subtitle: context.l10n.openclawHubSectionDevicesSubtitle,
                tone: (info.nodeCount ?? 0) > 0
                    ? OpenClawVisualTone.active
                    : OpenClawVisualTone.offline,
                expanded: _devicesExpanded,
                toggleLabel: _devicesExpanded ? context.l10n.openclawHubCollapseDeviceDetails : context.l10n.openclawHubExpandDeviceDetails,
                onToggle: () {
                  setState(() => _devicesExpanded = !_devicesExpanded);
                },
                summary: Text(
                  (info.nodeCount ?? 0) > 0
                      ? context.l10n.openclawHubDevicesSummaryActiveWithCount(info.nodeCount!)
                      : context.l10n.openclawHubDevicesSummaryEmpty,
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.45,
                  ),
                ),
                expandedChild: const OpenClawNodeManagementPanel(),
              ),
              const SizedBox(height: DS.spacing16),
              OpenClawSectionSurface(
                key: _delegateKey,
                icon: Icons.playlist_add_check_circle_rounded,
                title: context.l10n.openclawHubSectionQueueTitle,
                subtitle: context.l10n.openclawHubSectionQueueSubtitle,
                tone: connection.queuedRequests.isNotEmpty
                    ? OpenClawVisualTone.offline
                    : OpenClawVisualTone.active,
                expanded: _delegateExpanded,
                toggleLabel: _delegateExpanded ? context.l10n.openclawHubCollapseQueueDetails : context.l10n.openclawHubExpandQueueDetails,
                onToggle: () {
                  setState(() => _delegateExpanded = !_delegateExpanded);
                },
                summary: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      connection.isConnected &&
                              connection.queuedRequests.isNotEmpty
                          ? context.l10n.openclawHubQueueSummaryConnected
                          : !connection.isConnected &&
                                  connection.queuedRequests.isNotEmpty
                              ? context.l10n.openclawHubQueueSummaryNotConnected
                              : connection.isConnected
                                  ? context.l10n.openclawHubQueueSummaryConnectedEmpty
                                  : context.l10n.openclawHubQueueSummaryNotConnectedEmpty,
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    if (connection.queuedRequests.isEmpty)
                      OpenClawMetricPill(
                        icon: Icons.inbox_rounded,
                        label: context.l10n.openclawHubQueueEmptyLabel,
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
                              child: Text(context.l10n.openclawHubButtonRetryQueue),
                            ),
                          ),
                          const SizedBox(width: DS.spacing12),
                          Expanded(
                            child: TextButton(
                              onPressed: () =>
                                  unawaited(_clearQueuedRequests(connection)),
                              child: Text(
                                context.l10n.openclawHubButtonClearQueue,
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
                      context.l10n.openclawHubAvailableTemplates,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    if (templateNames.isEmpty)
                      Text(
                        context.l10n.openclawHubTemplatesEmptyHint,
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
                              ),
                            )
                            .toList(growable: false),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing16),
              OpenClawSectionSurface(
                key: _automationKey,
                icon: Icons.auto_awesome_motion_rounded,
                title: context.l10n.openclawHubSectionAutomationTitle,
                subtitle: context.l10n.openclawHubSectionAutomationSubtitle,
                tone: automation.schedules.isNotEmpty || automation.latestBatch != null
                    ? OpenClawVisualTone.connected
                    : OpenClawVisualTone.active,
                expanded: _automationExpanded,
                toggleLabel: _automationExpanded ? context.l10n.openclawHubCollapseAutomationDetails : context.l10n.openclawHubExpandAutomationDetails,
                onToggle: () {
                  setState(() => _automationExpanded = !_automationExpanded);
                },
                summary: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      automation.schedules.isEmpty
                          ? context.l10n.openclawHubAutomationSummaryEmpty
                          : context.l10n.openclawHubAutomationSummaryActiveWithCount(automation.schedules.length),
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
                    const SizedBox(height: DS.spacing10),
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: [
                        OpenClawMetricPill(
                          icon: Icons.schedule_rounded,
                          label: context.l10n.openclawHubAutomationCount(automation.schedules.length),
                          tone: automation.schedules.isNotEmpty
                              ? OpenClawVisualTone.connected
                              : OpenClawVisualTone.active,
                        ),
                        if (automation.latestBatch != null)
                          OpenClawMetricPill(
                            icon: Icons.playlist_add_check_circle_rounded,
                            label:
                                context.l10n.openclawHubLatestBatch(
                                    automation.latestBatch!.completedCount,
                                    automation.latestBatch!.taskIds.length,
                                  ),
                            tone: OpenClawVisualTone.attention,
                          ),
                      ],
                    ),
                  ],
                ),
                expandedChild: const OpenClawAutomationPanel(),
              ),
              const SizedBox(height: DS.spacing16),
              OpenClawSectionSurface(
                key: _activityKey,
                icon: Icons.history_rounded,
                title: context.l10n.openclawHubSectionActivityTitle,
                subtitle: context.l10n.openclawHubSectionActivitySubtitle,
                tone: latestIntent?.isTerminal ?? false
                    ? OpenClawVisualTone.connected
                    : OpenClawVisualTone.active,
                expanded: _activityExpanded,
                toggleLabel: _activityExpanded ? context.l10n.openclawHubCollapseActivityDetails : context.l10n.openclawHubExpandActivityDetails,
                onToggle: () {
                  setState(() => _activityExpanded = !_activityExpanded);
                },
                summary: recentTasks.isEmpty
                    ? Text(
                        context.l10n.openclawHubActivityEmptyHint,
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
                  latestRecord.trustLabel.isNotEmpty) ...[
                const SizedBox(height: DS.spacing4),
                Padding(
                  padding: const EdgeInsets.only(left: DS.spacing4),
                  child: Text(
                    context.l10n.openclawHubLastTrustLabel(latestRecord.trustLabel),
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
    case ExecutionIntentStatus.queued:
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
                  : context.l10n.openclawHubTaskLabel(request.taskId),
              style: DS.bodySmall.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              [
                if ((request.templateId ?? '').isNotEmpty)
                  context.l10n.openclawHubTaskLabelTemplate(request.templateId!),
                context.l10n.openclawHubTaskLabelSource(request.source),
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
                      label: intent?.statusLabel ?? context.l10n.openclawHubStatusRecorded,
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
                          : context.l10n.openclawHubActivityHint,
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
                      label: Text(context.l10n.openclawHubActivityOpenTask),
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
