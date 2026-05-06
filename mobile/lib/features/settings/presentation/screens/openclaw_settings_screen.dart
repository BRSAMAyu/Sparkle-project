import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/features/settings/presentation/widgets/openclaw_connection_panel.dart';
import 'package:sparkle/features/settings/presentation/widgets/openclaw_execution_preferences_card.dart';
import 'package:sparkle/features/task/presentation/execution_copy.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class OpenClawSettingsScreen extends ConsumerStatefulWidget {
  const OpenClawSettingsScreen({super.key});

  @override
  ConsumerState<OpenClawSettingsScreen> createState() =>
      _OpenClawSettingsScreenState();
}

class _OpenClawSettingsScreenState
    extends ConsumerState<OpenClawSettingsScreen> {
  bool _retryingQueue = false;

  Future<void> _retryQueuedRequests(OpenClawConnectionService service) async {
    final l10n = context.l10n;
    if (!service.isConnected) {
      _showSnackBar(
        service.hasExecutionPermissionIssue
            ? l10n.settOpenclawGatewayNoPerm
            : service.hasExecutionEndpointIssue
                ? l10n.settOpenclawEndpointUnavailable
                : l10n.settOpenclawEngineNotConnected,
        isError: true,
      );
      return;
    }
    setState(() => _retryingQueue = true);
    final dispatched =
        await ref.read(taskListProvider.notifier).drainQueuedAiHandoffs();
    if (!mounted) return;
    setState(() => _retryingQueue = false);
    _showSnackBar(
      dispatched > 0
          ? l10n.settOpenclawResubmitted(dispatched)
          : l10n.settOpenclawNoRetryableTasks,
    );
  }

  Future<void> _clearQueuedRequests(OpenClawConnectionService service) async {
    await service.clearQueuedRequests();
    if (!mounted) return;
    _showSnackBar(context.l10n.settingsQueueCleared);
  }

  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      isError
          ? SparkleSnackBar.error(message)
          : SparkleSnackBar.success(message),
    );
  }

  @override
  Widget build(BuildContext context) {
    final copy = ExecutionCopy.of(context);
    final l10n = context.l10n;
    final service = ref.watch(openClawConnectionProvider);
    final queuedRequests = service.queuedRequests;

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: Text(copy.engineTitle),
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.settOpenclawDesc,
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: DS.spacing16),
              const OpenClawConnectionPanel(),
              const SizedBox(height: DS.spacing16),
              const OpenClawExecutionPreferencesCard(),
              if (queuedRequests.isNotEmpty) ...[
                const SizedBox(height: DS.spacing16),
                GraphiteCardSurface(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              copy.offlineQueueTitle,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(
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
                              color: DS.warning.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text(
                              l10n.settOpenclawQueuedTasks(queuedRequests.length),
                              style: DS.bodySmall.copyWith(
                                color: DS.warning,
                                fontWeight: DS.fontWeightBold,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: DS.spacing8),
                      Text(
                        l10n.settOpenclawQueueDesc,
                        style: DS.bodySmall.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                      ),
                      const SizedBox(height: DS.spacing12),
                      ...queuedRequests.take(5).map(
                            (request) => Padding(
                              padding:
                                  const EdgeInsets.only(bottom: DS.spacing8),
                              child: Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(DS.spacing10),
                                decoration: BoxDecoration(
                                  color: DS.surfaceSecondary,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      (request.goal?.trim().isNotEmpty ?? false)
                                          ? request.goal!
                                          : l10n.settOpenclawTaskLabel(request.taskId),
                                      style: DS.bodySmall.copyWith(
                                        color: DS.textPrimary,
                                        fontWeight: DS.fontWeightBold,
                                      ),
                                    ),
                                    const SizedBox(height: DS.spacing4),
                                    Text(
                                      [
                                        if ((request.templateId ?? '')
                                            .isNotEmpty)
                                          l10n.settOpenclawTemplateLabel(request.templateId!),
                                        l10n.settOpenclawSourceLabel(request.source),
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
                      if (queuedRequests.length > 5)
                        Text(
                          l10n.settOpenclawMoreQueued(queuedRequests.length - 5),
                          style: DS.bodySmall.copyWith(
                            color: DS.textSecondary,
                          ),
                        ),
                      const SizedBox(height: DS.spacing12),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: _retryingQueue
                                  ? null
                                  : () =>
                                      unawaited(_retryQueuedRequests(service)),
                              child: _retryingQueue
                                  ? const SizedBox(
                                      width: 18,
                                      height: 18,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : Text(context.l10n.settingsRetryQueue),
                            ),
                          ),
                          const SizedBox(width: DS.spacing12),
                          Expanded(
                            child: TextButton(
                              onPressed: () =>
                                  unawaited(_clearQueuedRequests(service)),
                              child: Text(
                                l10n.settOpenclawClearQueue,
                                style: DS.bodyMedium.copyWith(
                                  color: DS.semanticError,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
              if (!service.config.isConfigured) ...[
                const SizedBox(height: DS.spacing16),
                GraphiteCardSurface(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        copy.aboutEngineTitle,
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      Text(
                        copy.aboutEngineBody,
                        style: DS.bodySmall.copyWith(
                          color: DS.textSecondary,
                          height: 1.5,
                        ),
                      ),
                    ],
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
