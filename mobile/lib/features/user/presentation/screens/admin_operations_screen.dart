import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

class AdminOperationsScreen extends ConsumerStatefulWidget {
  const AdminOperationsScreen({super.key});

  @override
  ConsumerState<AdminOperationsScreen> createState() =>
      _AdminOperationsScreenState();
}

class _AdminOperationsScreenState extends ConsumerState<AdminOperationsScreen> {
  int _days = 7;

  @override
  Widget build(BuildContext context) {
    final telemetryAsync = ref.watch(clientTelemetrySummaryProvider(_days));
    final capacityAsync = ref.watch(healthCapacityProvider);
    final alertsAsync = ref.watch(prometheusAlertsProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(context.l10n.userAdminPanel),
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(DS.spacing16),
        child: ContentConstraint(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SparkleStaggerItem(index: 0, child: _buildWindowSelector()),
              const SizedBox(height: DS.spacing16),
              SparkleStaggerItem(
                index: 1,
                child: capacityAsync.when(
                  data: _buildCapacityPanel,
                  loading: () => const GraphiteCardSurface(
                    child: LinearProgressIndicator(minHeight: 3),
                  ),
                  error: (error, _) => _buildErrorCard(
                    context.l10n.userAdminCapacityLoadFailed,
                    '$error',
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              SparkleStaggerItem(
                index: 2,
                child: alertsAsync.when(
                  data: _buildAlertsPanel,
                  loading: () => const GraphiteCardSurface(
                    child: LinearProgressIndicator(minHeight: 3),
                  ),
                  error: (error, _) => _buildErrorCard(
                    context.l10n.userAdminAlertsLoadFailed,
                    '$error',
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              SparkleStaggerItem(
                index: 3,
                child: telemetryAsync.when(
                  data: _buildTelemetryPanel,
                  loading: () => const GraphiteCardSurface(
                    child: LinearProgressIndicator(minHeight: 3),
                  ),
                  error: (error, _) => _buildErrorCard(
                    context.l10n.userAdminClientLoadFailed,
                    '$error',
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildWindowSelector() => GraphiteCardSurface(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.userAdminWindow,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.userAdminWindowHint,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [7, 14, 30]
                  .map(
                    (days) => ChoiceChip(
                      label: Text('$days ${context.l10n.adminDays}'),
                      selected: _days == days,
                      onSelected: (_) => setState(() => _days = days),
                    ),
                  )
                  .toList(),
            ),
          ],
        ),
      );

  Widget _buildCapacityPanel(Map<String, dynamic> payload) {
    final database = (payload['database'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
    final redis = (payload['redis'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
    final queues = (payload['queues'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
    final disk =
        (payload['disk'] as Map<String, dynamic>?) ?? const <String, dynamic>{};
    final recommendations =
        (payload['recommendations'] as List<dynamic>? ?? const <dynamic>[])
            .map((item) => item.toString())
            .toList();

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.userAdminCapacityHealth,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _MetricChip(
                label: context.l10n.userAdminDBProbe,
                value:
                    '${((database['probe_latency_ms'] as num?)?.toDouble() ?? 0).toStringAsFixed(0)}ms',
              ),
              _MetricChip(
                label: context.l10n.userAdminRedisConn,
                value: '${redis['connected_clients'] ?? '-'}',
              ),
              _MetricChip(
                label: context.l10n.userAdminQueueBacklog,
                value:
                    '${queues.values.fold<int>(0, (sum, item) => sum + ((item as num?)?.toInt() ?? 0))}',
              ),
              _MetricChip(
                label: context.l10n.userAdminDiskUsage,
                value:
                    '${((disk['used_ratio_percent'] as num?)?.toDouble() ?? 0).toStringAsFixed(1)}%',
              ),
            ],
          ),
          if (recommendations.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            ...recommendations.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 5,
                      height: 5,
                      margin: const EdgeInsets.only(top: 7, right: 8),
                      decoration: BoxDecoration(
                        color: Theme.of(context).textTheme.bodySmall?.color ??
                            DS.textPrimary,
                        shape: BoxShape.circle,
                      ),
                    ),
                    Expanded(
                      child: Text(
                        item,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: DS.spacing12),
          Text(
            context.l10n.userAdminServiceDrilldown,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          _ServiceDetailTile(
            title: 'PostgreSQL',
            lines: [
              '${context.l10n.adminProbeLatency} ${((database['probe_latency_ms'] as num?)?.toDouble() ?? 0).toStringAsFixed(1)}ms',
              '${context.l10n.adminPool} ${database['pool_size'] ?? '-'} / ${context.l10n.adminOverflow} ${database['max_overflow'] ?? '-'}',
              '${context.l10n.adminTimeout} ${database['pool_timeout_seconds'] ?? '-'}s',
            ],
          ),
          const SizedBox(height: DS.spacing8),
          _ServiceDetailTile(
            title: 'Redis',
            lines: [
              '${context.l10n.adminStatus} ${redis['status'] ?? '-'}',
              '${context.l10n.adminMemory} ${redis['used_memory_human'] ?? '-'} / ${context.l10n.adminPeak} ${redis['used_memory_peak_human'] ?? '-'}',
              '${context.l10n.adminClients} ${redis['connected_clients'] ?? '-'}',
            ],
          ),
          const SizedBox(height: DS.spacing8),
          _ServiceDetailTile(
            title: 'Worker Queues',
            lines: queues.entries
                .map((entry) => '${entry.key}: ${entry.value}')
                .toList(growable: false),
          ),
          const SizedBox(height: DS.spacing8),
          _ServiceDetailTile(
            title: 'Disk',
            lines: [
              '${context.l10n.adminUsed} ${disk['used_gb'] ?? '-'} GB / ${context.l10n.adminFree} ${disk['free_gb'] ?? '-'} GB',
              '${context.l10n.adminTotal} ${disk['total_gb'] ?? '-'} GB',
              '${context.l10n.adminUsage} ${((disk['used_ratio_percent'] as num?)?.toDouble() ?? 0).toStringAsFixed(1)}%',
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAlertsPanel(Map<String, dynamic> payload) {
    final alerts = (payload['alerts'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .toList();
    final firing = payload['firing'] == true;

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.userAdminCurrentAlerts,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing12),
          if (!firing || alerts.isEmpty)
            Text(
              context.l10n.userAdminNoAlerts,
              style: Theme.of(context).textTheme.bodySmall,
            )
          else
            ...alerts.map(
              (alert) => Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: DS.spacing8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: DS.surfacePrimary,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: DS.borderSubtle),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${alert['name'] ?? 'Unknown Alert'} · ${alert['severity'] ?? 'warning'}',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      alert['message']?.toString() ?? '',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildTelemetryPanel(Map<String, dynamic> payload) {
    final overall = (payload['overall'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
    final byEventType =
        (payload['by_event_type'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();
    final dailyTotals =
        (payload['daily_totals'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();
    final recentEvents =
        (payload['recent_events'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.userAdminClientObservability,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _MetricChip(label: context.l10n.userAdminTotalEvents, value: '${overall['count'] ?? 0}'),
              _MetricChip(label: context.l10n.userAdminErrors, value: '${overall['error_count'] ?? 0}'),
              _MetricChip(label: context.l10n.userAdminCrashes, value: '${overall['crash_count'] ?? 0}'),
              _MetricChip(
                label: context.l10n.userAdminAvgDuration,
                value:
                    '${((overall['avg_duration_ms'] as num?)?.toDouble() ?? 0).toStringAsFixed(0)}ms',
              ),
            ],
          ),
          if (dailyTotals.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              context.l10n.userAdminTrendDays,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            _TrendBars(points: dailyTotals),
            const SizedBox(height: DS.spacing10),
            _TelemetryTrendSummary(points: dailyTotals),
          ],
          if (byEventType.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              context.l10n.userAdminEventTypeDrilldown,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            ...byEventType.take(5).map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: _ServiceDetailTile(
                      title: item['event_type']?.toString() ?? 'unknown',
                      lines: [
                        '${context.l10n.adminTotal} ${item['count'] ?? 0}',
                        '${context.l10n.adminErrors} ${item['error_count'] ?? 0} / ${context.l10n.adminCrashes} ${item['crash_count'] ?? 0}',
                        '${context.l10n.adminSuccessRate} ${item['success_rate_percent'] ?? 0}%',
                        '${context.l10n.adminAvgDuration} ${item['avg_duration_ms'] ?? 0}ms',
                      ],
                    ),
                  ),
                ),
          ],
          if (recentEvents.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              context.l10n.adminRecentEvents,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            ...recentEvents.take(4).map(
                  (event) => Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Text(
                      '${event['event_type']} · ${event['status']} · ${event['route'] ?? '-'}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                  ),
                ),
          ],
        ],
      ),
    );
  }

  Widget _buildErrorCard(String title, String error) => GraphiteCardSurface(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(error, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      );
}

class _TrendBars extends StatelessWidget {
  const _TrendBars({required this.points});

  final List<Map<String, dynamic>> points;

  @override
  Widget build(BuildContext context) {
    final values = points
        .map((point) => (point['count'] as num?)?.toDouble() ?? 0.0)
        .toList();
    final maxValue = values.isEmpty
        ? 0.0
        : values.reduce((current, next) => current > next ? current : next);

    return SizedBox(
      height: 72,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (var index = 0; index < points.length; index++) ...[
            Expanded(
              child: Padding(
                padding: EdgeInsets.only(
                  right: index == points.length - 1 ? 0 : 4,
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Expanded(
                      child: Align(
                        alignment: Alignment.bottomCenter,
                        child: FractionallySizedBox(
                          heightFactor: maxValue <= 0
                              ? 0.1
                              : (values[index] / maxValue).clamp(0.1, 1.0),
                          child: Container(
                            decoration: BoxDecoration(
                              color: DS.brandPrimary.withValues(alpha: 0.82),
                              borderRadius: BorderRadius.circular(8),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _shortDate(points[index]['date']?.toString() ?? ''),
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _shortDate(String value) {
    final parts = value.split('-');
    if (parts.length != 3) return value;
    return '${parts[1]}/${parts[2]}';
  }
}

class _TelemetryTrendSummary extends StatelessWidget {
  const _TelemetryTrendSummary({required this.points});

  final List<Map<String, dynamic>> points;

  @override
  Widget build(BuildContext context) {
    final totalEvents = points.fold<int>(
      0,
      (sum, point) => sum + ((point['count'] as num?)?.toInt() ?? 0),
    );
    final totalErrors = points.fold<int>(
      0,
      (sum, point) => sum + ((point['error_count'] as num?)?.toInt() ?? 0),
    );
    final weightedDuration = points.fold<double>(
      0,
      (sum, point) =>
          sum +
          (((point['avg_duration_ms'] as num?)?.toDouble() ?? 0) *
              ((point['count'] as num?)?.toDouble() ?? 0)),
    );
    final averageDuration =
        totalEvents > 0 ? weightedDuration / totalEvents : 0.0;

    return Wrap(
      spacing: DS.spacing8,
      runSpacing: DS.spacing8,
      children: [
        _MetricChip(label: context.l10n.adminWindowEvents, value: '$totalEvents'),
        _MetricChip(label: context.l10n.adminWindowErrors, value: '$totalErrors'),
        _MetricChip(
          label: context.l10n.adminWeightedAvgDuration,
          value: '${averageDuration.toStringAsFixed(0)}ms',
        ),
      ],
    );
  }
}

class _ServiceDetailTile extends StatelessWidget {
  const _ServiceDetailTile({
    required this.title,
    required this.lines,
  });

  final String title;
  final List<String> lines;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: 6),
            ...lines.map(
              (line) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(
                  line,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
              ),
            ),
          ],
        ),
      );
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: 2),
            Text(
              value,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ],
        ),
      );
}
