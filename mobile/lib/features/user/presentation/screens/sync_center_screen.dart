import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/sync_center_provider.dart';

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
      child: Scaffold(
        appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('同步中心'),
          actions: [
            PopupMenuButton<String>(
              onSelected: (value) async {
                if (value == 'retry_all') {
                  await service.retryAll();
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('已触发全量重试')),
                    );
                  }
                }
              },
              itemBuilder: (context) => const [
                PopupMenuItem(
                  value: 'retry_all',
                  child: Text('Retry now (force all)'),
                ),
              ],
            ),
          ],
          bottom: const TabBar(
            tabs: [
              Tab(text: 'All'),
              Tab(text: 'Failed'),
              Tab(text: 'WaitingAck'),
              Tab(text: 'Pending'),
            ],
          ),
        ),
        body: Padding(
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              statsAsync.when(
                data: (stats) => _StatsView(stats: stats),
                loading: () =>
                    const Center(child: CircularProgressIndicator()),
                error: (error, stackTrace) => Text('加载失败: $error'),
              ),
              const SizedBox(height: DS.spacing16),
              _TopicFilter(
                value: _topicFilter,
                onChanged: (value) {
                  setState(() {
                    _topicFilter = value;
                  });
                },
              ),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: () async {
                    final diagnostics = await service.buildDiagnostics();
                    await Clipboard.setData(
                      ClipboardData(text: diagnostics),
                    );
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('已复制诊断信息')),
                      );
                    }
                  },
                  icon: const Icon(Icons.copy),
                  label: const Text('Copy diagnostics'),
                ),
              ),
              const SizedBox(height: DS.spacing8),
              const Text(
                '最多展示 200 条',
                style: TextStyle(fontSize: 12, color: Colors.grey),
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
        bottomNavigationBar: Padding(
          padding: const EdgeInsets.fromLTRB(
              DS.spacing16, 0, DS.spacing16, DS.spacing16,),
          child: ElevatedButton.icon(
            onPressed: () async {
              await service.retryFailed();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('已触发失败重试')),
                );
              }
            },
            icon: const Icon(Icons.sync),
            label: const Text('Retry failed'),
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
        ? stats.lastSuccessAt!.toLocal().toString()
        : '未同步';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '待同步总数: ${stats.totalPending}',
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: DS.spacing8),
        Text(
          '最近同步: $lastSuccessLabel',
          style: const TextStyle(fontSize: 12, color: Colors.grey),
        ),
        const SizedBox(height: DS.spacing12),
        const Text(
          '按主题统计',
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: DS.spacing8),
        if (topicEntries.isEmpty)
          const Text('暂无待同步项')
        else
          ...topicEntries.map(
            (entry) => ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(_topicLabel(entry.key)),
              trailing: Text('${entry.value}'),
            ),
          ),
      ],
    );
  }

  String _topicLabel(String topic) {
    switch (topic) {
      case 'cognitive':
        return '认知碎片';
      case 'knowledge':
        return '知识图谱';
      case 'crdt':
        return '协同';
      case 'analytics':
        return '分析';
      case 'legacy':
        return 'Legacy';
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
        const Text('Topic:'),
        const SizedBox(width: DS.spacing8),
        DropdownButton<String>(
          value: value,
          onChanged: (next) {
            if (next != null) {
              onChanged(next);
            }
          },
          items: const [
            DropdownMenuItem(value: 'all', child: Text('All')),
            DropdownMenuItem(value: 'cognitive', child: Text('认知碎片')),
            DropdownMenuItem(value: 'knowledge', child: Text('知识图谱')),
            DropdownMenuItem(value: 'crdt', child: Text('协同')),
            DropdownMenuItem(value: 'analytics', child: Text('分析')),
            DropdownMenuItem(value: 'legacy', child: Text('Legacy')),
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
          return const Center(child: Text('暂无记录'));
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
                    const SnackBar(content: Text('已触发重试')),
                  );
                }
              },
              onCopyTraceId: () async {
                final traceId = item.traceId;
                if (traceId == null || traceId.isEmpty) return;
                await Clipboard.setData(ClipboardData(text: traceId));
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('已复制 TraceId')),
                  );
                }
              },
              onCopyEntityId: () async {
                final entityId = item.entityId;
                if (entityId == null || entityId.isEmpty) return;
                await Clipboard.setData(ClipboardData(text: entityId));
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('已复制实体 ID')),
                  );
                }
              },
            );
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stackTrace) => Center(child: Text('加载失败: $error')),
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
    final statusLabel = item.status.name;
    final errorLabel = _errorLabel(item.lastErrorCode);
    final nextAttemptAt =
        item.nextAttemptAt?.toLocal();

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
                Chip(label: Text(topic)),
                Chip(label: Text(opType)),
                Chip(label: Text(statusLabel)),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${item.entityType ?? 'entity'}: ${item.entityId ?? '-'}',
                    style: const TextStyle(fontSize: 12),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.copy, size: 16),
                  onPressed: onCopyEntityId,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              'attempt: ${item.attemptCount}',
              style: const TextStyle(fontSize: 12),
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              'lastError: $errorLabel',
              style: const TextStyle(fontSize: 12),
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              'nextAttempt: ${nextAttemptAt ?? '-'}',
              style: const TextStyle(fontSize: 12),
            ),
            const SizedBox(height: DS.spacing4),
            Row(
              children: [
                Expanded(
                  child: Text(
                    'traceId: ${item.traceId ?? '-'}',
                    style: const TextStyle(fontSize: 12),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.copy, size: 16),
                  onPressed: onCopyTraceId,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Row(
              children: [
                ElevatedButton(
                  onPressed: onRetry,
                  child: const Text('Retry this'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
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
