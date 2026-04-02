import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/features/settings/presentation/widgets/openclaw_connection_panel.dart';
import 'package:sparkle/features/settings/presentation/widgets/openclaw_execution_preferences_card.dart';
import 'package:sparkle/features/task/presentation/execution_copy.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';

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
    setState(() => _retryingQueue = true);
    final dispatched =
        await ref.read(taskListProvider.notifier).drainQueuedAiHandoffs();
    if (!mounted) return;
    setState(() => _retryingQueue = false);
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
    final copy = ExecutionCopy.of(context);
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
                '这里统一管理 OpenClaw 的接入状态、执行可用性和等待队列，避免你在不同页面看到不同结论。',
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
                              '${queuedRequests.length} 个任务',
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
                        '当执行链路暂时不可用时，新的委派会先进入这里。等权限或连接恢复后，你可以一键重新提交。',
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
                                          : '任务 ${request.taskId}',
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
                      if (queuedRequests.length > 5)
                        Text(
                          '还有 ${queuedRequests.length - 5} 个排队任务',
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
                                  : const Text('重试队列'),
                            ),
                          ),
                          const SizedBox(width: DS.spacing12),
                          Expanded(
                            child: TextButton(
                              onPressed: () =>
                                  unawaited(_clearQueuedRequests(service)),
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
