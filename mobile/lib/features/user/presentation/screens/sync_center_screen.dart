import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/sync_center_provider.dart';
import 'package:sparkle/core/utils/formatters.dart';

class SyncCenterScreen extends ConsumerStatefulWidget {
  const SyncCenterScreen({super.key});

  @override
  ConsumerState<SyncCenterScreen> createState() => _SyncCenterScreenState();
}

class _SyncCenterScreenState extends ConsumerState<SyncCenterScreen> {
  String _topicFilter = 'all';

  @override
  Widget build(BuildContext context) {
    final statsAsync = ref.watch(syncCenterStatsProvider);
    final service = ref.watch(syncCenterServiceProvider);

    return DefaultTabController(
      length: 4,
      child: SparklePageScaffold(
        role: SparklePageRole.settings,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            size: DS.touchTargetMinSize,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: Text(context.l10n.syncCenter),
          actions: [
            PopupMenuButton<String>(
              onSelected: (value) async {
                if (value == 'retry_all') {
                  await service.retryAll();
                  if (context.mounted) {
                    AppFeedback.success(
                      context,
                      context.l10n.syncCenterRetryAllTriggered,
                    );
                  }
                }
              },
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: 'retry_all',
                  child: Text(context.l10n.syncCenterRetryAll),
                ),
              ],
            ),
          ],
          bottom: TabBar(
            isScrollable: true,
            tabs: [
              Tab(text: context.l10n.syncCenterTabAll),
              Tab(text: context.l10n.syncCenterTabFailed),
              Tab(text: context.l10n.syncCenterTabWaitingAck),
              Tab(text: context.l10n.syncCenterTabPending),
            ],
          ),
        ),
        child: ContentConstraint(
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  child: statsAsync.when(
                    data: (stats) => _StatsView(stats: stats),
                    loading: () =>
                        const Center(child: CircularProgressIndicator()),
                    error: (error, stackTrace) => Text(
                      context.l10n.syncCenterLoadFailed(error.toString()),
                    ),
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _TopicFilter(
                        value: _topicFilter,
                        onChanged: (value) {
                          setState(() {
                            _topicFilter = value;
                          });
                        },
                      ),
                      const SizedBox(height: DS.spacing8),
                      Align(
                        alignment: Alignment.centerRight,
                        child: SparkleButton.ghost(
                          onPressed: () async {
                            final diagnostics =
                                await service.buildDiagnostics();
                            await Clipboard.setData(
                              ClipboardData(text: diagnostics),
                            );
                            if (context.mounted) {
                              AppFeedback.success(
                                context,
                                context.l10n.syncCenterDiagnosticsCopied,
                              );
                            }
                          },
                          icon: const Icon(Icons.copy),
                          label: context.l10n.syncCenterCopyDiagnostics,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  context.l10n.syncCenterDisplayLimit(200),
                  style: TextStyle(fontSize: 12, color: DS.textSecondary),
                ),
                const SizedBox(height: DS.spacing8),
                Expanded(
                  child: TabBarView(
                    children: [
                      _ItemsList(
                        query: SyncCenterQuery(topicFilter: _topicFilter),
                      ),
                      _ItemsList(
                        query: SyncCenterQuery(
                          statusFilter: SyncStatus.failed,
                          topicFilter: _topicFilter,
                        ),
                      ),
                      _ItemsList(
                        query: SyncCenterQuery(
                          statusFilter: SyncStatus.waitingAck,
                          topicFilter: _topicFilter,
                        ),
                      ),
                      _ItemsList(
                        query: SyncCenterQuery(
                          statusFilter: SyncStatus.pending,
                          topicFilter: _topicFilter,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        bottomNavigationBar: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
              DS.spacing16,
              0,
              DS.spacing16,
              DS.spacing16,
            ),
            child: SparkleButton(
              onPressed: () async {
                await service.retryFailed();
                if (context.mounted) {
                  AppFeedback.success(
                    context,
                    context.l10n.syncCenterRetryFailedTriggered,
                  );
                }
              },
              icon: const Icon(Icons.sync),
              label: context.l10n.syncCenterRetryFailed,
              expand: true,
            ),
          ),
        ),
      ),
    );
  }
}

class _StatsView extends StatelessWidget {
  const _StatsView({required this.stats});

  final SyncCenterStats stats;

  @override
  Widget build(BuildContext context) {
    final topicEntries = stats.pendingByTopic.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final lastSuccessLabel = stats.lastSuccessAt != null
        ? Formatters.formatDateTime(stats.lastSuccessAt!.toLocal())
        : context.l10n.syncCenterNeverSynced;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.l10n.syncCenterTotalPending(stats.totalPending),
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: DS.spacing8),
        Text(
          context.l10n.syncCenterLastSync(lastSuccessLabel),
          style: TextStyle(fontSize: 12, color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing12),
        Text(
          context.l10n.syncCenterByTopic,
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: DS.spacing8),
        if (topicEntries.isEmpty)
          Text(context.l10n.syncCenterNoPendingItems)
        else
          ...topicEntries.map(
            (entry) => ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(_topicLabel(context, entry.key)),
              trailing: Text('${entry.value}'),
            ),
          ),
      ],
    );
  }

  String _topicLabel(BuildContext context, String topic) {
    switch (topic) {
      case 'cognitive':
        return context.l10n.syncCenterTopicCognitive;
      case 'knowledge':
        return context.l10n.syncCenterTopicKnowledge;
      case 'crdt':
        return context.l10n.syncCenterTopicCollab;
      case 'analytics':
        return context.l10n.syncCenterTopicAnalytics;
      case 'legacy':
        return context.l10n.syncCenterTopicLegacy;
      default:
        return topic;
    }
  }
}

class _TopicFilter extends StatelessWidget {
  const _TopicFilter({
    required this.value,
    required this.onChanged,
  });

  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Text(context.l10n.syncCenterTopicLabel),
          const SizedBox(width: DS.spacing8),
          DropdownButton<String>(
            value: value,
            onChanged: (next) {
              if (next != null) {
                onChanged(next);
              }
            },
            items: [
              DropdownMenuItem(
                value: 'all',
                child: Text(context.l10n.syncCenterTopicAll),
              ),
              DropdownMenuItem(
                value: 'cognitive',
                child: Text(context.l10n.syncCenterTopicCognitive),
              ),
              DropdownMenuItem(
                value: 'knowledge',
                child: Text(context.l10n.syncCenterTopicKnowledge),
              ),
              DropdownMenuItem(
                value: 'crdt',
                child: Text(context.l10n.syncCenterTopicCollab),
              ),
              DropdownMenuItem(
                value: 'analytics',
                child: Text(context.l10n.syncCenterTopicAnalytics),
              ),
              DropdownMenuItem(
                value: 'legacy',
                child: Text(context.l10n.syncCenterTopicLegacy),
              ),
            ],
          ),
        ],
      );
}

class _ItemsList extends ConsumerWidget {
  const _ItemsList({required this.query});

  final SyncCenterQuery query;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final itemsAsync = ref.watch(syncCenterItemsProvider(query));
    final service = ref.watch(syncCenterServiceProvider);

    return itemsAsync.when(
      data: (items) {
        if (items.isEmpty) {
          return Center(child: Text(context.l10n.syncCenterNoRecords));
        }
        return ListView.separated(
          itemCount: items.length,
          separatorBuilder: (_, __) => const SizedBox(height: DS.spacing8),
          itemBuilder: (context, index) {
            final item = items[index];
            return _OutboxItemCard(
              item: item,
              onRetry: () async {
                await service.retryItem(item.id);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(context.l10n.syncCenterRetryTriggered),
                    ),
                  );
                }
              },
              onCopyTraceId: () async {
                final traceId = item.traceId;
                if (traceId == null || traceId.isEmpty) return;
                await Clipboard.setData(ClipboardData(text: traceId));
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(context.l10n.syncCenterTraceCopied),
                    ),
                  );
                }
              },
              onCopyEntityId: () async {
                final entityId = item.entityId;
                if (entityId == null || entityId.isEmpty) return;
                await Clipboard.setData(ClipboardData(text: entityId));
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(context.l10n.syncCenterEntityCopied),
                    ),
                  );
                }
              },
            );
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stackTrace) => Center(
        child: Text(context.l10n.syncCenterLoadFailed(error.toString())),
      ),
    );
  }
}

class _OutboxItemCard extends StatelessWidget {
  const _OutboxItemCard({
    required this.item,
    required this.onRetry,
    required this.onCopyTraceId,
    required this.onCopyEntityId,
  });

  final OutboxItem item;
  final VoidCallback onRetry;
  final VoidCallback onCopyTraceId;
  final VoidCallback onCopyEntityId;

  @override
  Widget build(BuildContext context) {
    final topic = item.topic ?? 'legacy';
    final opType = item.opType ?? item.type ?? 'unknown';
    final statusLabel = item.status.localizedLabel(context.l10n);
    final errorLabel = _errorLabel(item.lastErrorCode);
    final nextAttemptAt = item.nextAttemptAt?.toLocal();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing4,
              children: [
                Chip(label: Text(_topicLabel(context, topic))),
                Chip(label: Text(opType)),
                Chip(label: Text(statusLabel)),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Row(
              children: [
                Expanded(
                  child: Text(
                    context.l10n.syncCenterEntityValue(
                      item.entityType ?? 'entity',
                      item.entityId ?? '-',
                    ),
                    style: const TextStyle(fontSize: 12),
                  ),
                ),
                SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  size: DS.spacing32,
                  icon: const Icon(Icons.copy, size: 16),
                  onPressed: onCopyEntityId,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              context.l10n.syncCenterAttemptValue(item.attemptCount),
              style: const TextStyle(fontSize: 12),
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              context.l10n.syncCenterLastErrorValue(errorLabel),
              style: const TextStyle(fontSize: 12),
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              context.l10n.syncCenterNextAttemptValue(
                nextAttemptAt != null
                    ? Formatters.formatDateTime(nextAttemptAt)
                    : '-',
              ),
              style: const TextStyle(fontSize: 12),
            ),
            const SizedBox(height: DS.spacing4),
            Row(
              children: [
                Expanded(
                  child: Text(
                    context.l10n.syncCenterTraceIdValue(item.traceId ?? '-'),
                    style: const TextStyle(fontSize: 12),
                  ),
                ),
                SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  size: DS.spacing32,
                  icon: const Icon(Icons.copy, size: 16),
                  onPressed: onCopyTraceId,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Row(
              children: [
                SparkleButton(
                  onPressed: onRetry,
                  label: context.l10n.syncCenterRetryThis,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _topicLabel(BuildContext context, String topic) {
    switch (topic) {
      case 'cognitive':
        return context.l10n.syncCenterTopicCognitive;
      case 'knowledge':
        return context.l10n.syncCenterTopicKnowledge;
      case 'crdt':
        return context.l10n.syncCenterTopicCollab;
      case 'analytics':
        return context.l10n.syncCenterTopicAnalytics;
      case 'legacy':
        return context.l10n.syncCenterTopicLegacy;
      default:
        return topic;
    }
  }

  String _errorLabel(String? code) {
    switch (code) {
      case 'ACK_TIMEOUT':
        return 'ACK_TIMEOUT';
      case 'ACK_ERROR':
        return 'ACK_ERROR';
      case 'AUTH_401':
        return 'AUTH_401';
      case 'RATE_429':
        return 'RATE_429';
      case 'SERVER_5XX':
        return 'SERVER_5XX';
      case 'HTTP_409':
        return 'CONFLICT';
      case 'TIMEOUT':
        return 'TIMEOUT';
      case 'NETWORK':
        return 'NETWORK';
      case 'network':
        return 'NETWORK';
      default:
        return code ?? '-';
    }
  }
}
