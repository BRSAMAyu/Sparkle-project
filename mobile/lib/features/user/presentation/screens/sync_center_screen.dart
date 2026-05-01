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
        child: ContentConstraint(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Compact stats header row
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  DS.spacing16,
                  DS.spacing12,
                  DS.spacing16,
                  DS.spacing4,
                ),
                child: statsAsync.when(
                  data: (stats) => _CompactStatsRow(stats: stats),
                  loading: () => const SizedBox(
                    height: 72,
                    child: Center(child: CircularProgressIndicator()),
                  ),
                  error: (error, _) => Padding(
                    padding: const EdgeInsets.all(DS.spacing12),
                    child: Text(
                      context.l10n.syncCenterLoadFailed(error.toString()),
                      style: DS.bodySmall.copyWith(color: DS.error),
                    ),
                  ),
                ),
              ),
              // Topic filter + diagnostics in a compact row
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing16,
                  vertical: DS.spacing4,
                ),
                child: _CompactFilterRow(
                  topicFilter: _topicFilter,
                  onTopicChanged: (value) {
                    setState(() => _topicFilter = value);
                  },
                  onCopyDiagnostics: () async {
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
                  onCopyLabel: context.l10n.syncCenterCopyDiagnostics,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              // Record list takes full remaining height
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
    );
  }
}

/// Balanced header row showing pending count (left) and last sync time (right).
class _CompactStatsRow extends StatelessWidget {
  const _CompactStatsRow({required this.stats});

  final SyncCenterStats stats;

  @override
  Widget build(BuildContext context) {
    final lastSyncLabel = stats.lastSuccessAt != null
        ? Formatters.formatDateTime(stats.lastSuccessAt!.toLocal())
        : context.l10n.syncCenterNeverSynced;

    final topicEntries = stats.pendingByTopic.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing12,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top row: pending count left, last sync right
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Pending count
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.syncCenterTotalPending(stats.totalPending),
                      style: DS.titleLarge.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.spacing2),
                    Text(
                      context.l10n.syncCenterLastSync(lastSyncLabel),
                      style: DS.bodySmall.copyWith(color: DS.textSecondary),
                    ),
                  ],
                ),
              ),
              // Topic breakdown chips (compact)
              if (topicEntries.isNotEmpty)
                Expanded(
                  child: Wrap(
                    alignment: WrapAlignment.end,
                    spacing: DS.spacing6,
                    runSpacing: DS.spacing4,
                    children: topicEntries.map((entry) {
                      return _StatChip(
                        label: _topicLabel(context, entry.key),
                        count: entry.value,
                      );
                    }).toList(),
                  ),
                ),
            ],
          ),
        ],
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
}

/// A compact chip showing topic name and count, used in the stats header.
class _StatChip extends StatelessWidget {
  const _StatChip({required this.label, required this.count});

  final String label;
  final int count;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: DS.brandPrimary12,
        borderRadius: DS.borderRadius8,
        border: Border.all(color: DS.brandPrimary24),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: DS.labelSmall.copyWith(
              color: DS.brandPrimary,
              fontWeight: DS.fontWeightMedium,
            ),
          ),
          const SizedBox(width: DS.spacing4),
          Text(
            '$count',
            style: DS.labelSmall.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ],
      ),
    );
  }
}

/// Compact single-row filter: topic dropdown on the left, copy button on the right.
class _CompactFilterRow extends StatelessWidget {
  const _CompactFilterRow({
    required this.topicFilter,
    required this.onTopicChanged,
    required this.onCopyDiagnostics,
    required this.onCopyLabel,
  });

  final String topicFilter;
  final ValueChanged<String> onTopicChanged;
  final VoidCallback onCopyDiagnostics;
  final String onCopyLabel;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        // Topic filter dropdown
        Flexible(
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: DS.borderRadius12,
              border: Border.all(color: DS.borderSubtle),
              color: DS.surfacePrimaryElevated,
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: DS.spacing12),
              child: DropdownButton<String>(
                value: topicFilter,
                isExpanded: true,
                underline: const SizedBox.shrink(),
                style: DS.bodySmall.copyWith(color: DS.textPrimary),
                onChanged: (next) {
                  if (next != null) onTopicChanged(next);
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
            ),
          ),
        ),
        const SizedBox(width: DS.spacing8),
        // Copy diagnostics button
        SparkleIconButton(
          variant: ButtonVariant.ghost,
          size: DS.spacing40,
          icon: Icon(Icons.copy, size: 18, color: DS.textSecondary),
          onPressed: onCopyDiagnostics,
        ),
      ],
    );
  }
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
          return const _EmptyState();
        }
        return ListView.separated(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing4,
            DS.spacing16,
            DS.spacing64 + DS.spacing16,
          ),
          itemCount: items.length,
          separatorBuilder: (_, __) => const SizedBox(height: DS.spacing8),
          itemBuilder: (context, index) {
            final item = items[index];
            return _OutboxItemCard(
              item: item,
              onRetry: () async {
                await service.retryItem(item.id);
                if (context.mounted) {
                  AppFeedback.success(
                    context,
                    context.l10n.syncCenterRetryTriggered,
                  );
                }
              },
              onCopyTraceId: () async {
                final traceId = item.traceId;
                if (traceId == null || traceId.isEmpty) return;
                await Clipboard.setData(ClipboardData(text: traceId));
                if (context.mounted) {
                  AppFeedback.info(
                    context,
                    context.l10n.syncCenterTraceCopied,
                  );
                }
              },
              onCopyEntityId: () async {
                final entityId = item.entityId;
                if (entityId == null || entityId.isEmpty) return;
                await Clipboard.setData(ClipboardData(text: entityId));
                if (context.mounted) {
                  AppFeedback.info(
                    context,
                    context.l10n.syncCenterEntityCopied,
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

/// Empty state with icon and descriptive text instead of plain "暂无记录".
class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.cloud_done_rounded,
              size: DS.iconSizeXl * 2,
              color: DS.success.withValues(alpha: 0.35),
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              context.l10n.syncCenterNoRecords,
              style: DS.titleMedium.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.syncCenterNoPendingItems,
              style: DS.bodySmall.copyWith(color: DS.textTertiary),
              textAlign: TextAlign.center,
            ),
          ],
        ),
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

    final statusColor = switch (item.status) {
      SyncStatus.failed => DS.error,
      SyncStatus.waitingAck => DS.warning,
      SyncStatus.pending => DS.info,
      SyncStatus.conflict => DS.warning,
      SyncStatus.synced => DS.success,
    };

    return Container(
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius16,
        border: Border.all(
          color: statusColor.withValues(alpha: 0.18),
        ),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color.alphaBlend(
              statusColor.withValues(alpha: 0.08),
              DS.surfaceSecondary,
            ),
            DS.surfacePrimaryElevated,
          ],
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing4,
              children: [
                _MetaChip(label: _topicLabel(context, topic)),
                _MetaChip(label: opType),
                _MetaChip(label: statusLabel, accent: statusColor),
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
                    style: DS.bodySmall.copyWith(color: DS.textPrimary),
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
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              context.l10n.syncCenterLastErrorValue(errorLabel),
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              context.l10n.syncCenterNextAttemptValue(
                nextAttemptAt != null
                    ? Formatters.formatDateTime(nextAttemptAt)
                    : '-',
              ),
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing4),
            Row(
              children: [
                Expanded(
                  child: Text(
                    context.l10n.syncCenterTraceIdValue(item.traceId ?? '-'),
                    style: DS.bodySmall.copyWith(color: DS.textSecondary),
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
                  icon: const Icon(Icons.refresh_rounded),
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

class _MetaChip extends StatelessWidget {
  const _MetaChip({
    required this.label,
    this.accent,
  });

  final String label;
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    final color = accent ?? DS.textSecondary;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          color.withValues(alpha: 0.08),
          DS.surfacePrimary,
        ),
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: color.withValues(alpha: 0.14),
        ),
      ),
      child: Text(
        label,
        style: DS.labelSmall.copyWith(
          color: color,
          fontWeight: DS.fontWeightMedium,
        ),
      ),
    );
  }
}
