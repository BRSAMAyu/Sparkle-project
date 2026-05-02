import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/notification_center/data/models/notification_analytics_model.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_analytics_provider.dart'
    as providers;

/// Notification Analytics Screen
class NotificationAnalyticsScreen extends ConsumerStatefulWidget {
  const NotificationAnalyticsScreen({super.key});

  @override
  ConsumerState<NotificationAnalyticsScreen> createState() =>
      _NotificationAnalyticsScreenState();
}

class _NotificationAnalyticsScreenState
    extends ConsumerState<NotificationAnalyticsScreen> {
  @override
  void initState() {
    super.initState();
    // Load analytics on init
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(providers.notificationAnalyticsProvider.notifier)
          .loadAnalytics('7d');
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(providers.notificationAnalyticsProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(context.l10n.notificationAnalyticsTitle),
        actions: [
          DropdownButton<String>(
            value: state.period,
            underline: const SizedBox.shrink(),
            icon: const Icon(Icons.arrow_drop_down),
            items: providers.AnalyticsPeriod.all
                .map(
                  (period) => DropdownMenuItem(
                    value: period.value,
                    child: Text(period.localizedLabel(context.l10n)),
                  ),
                )
                .toList(),
            onChanged: (value) {
              if (value != null) {
                unawaited(
                  SensoryFeedbackService.emit(
                    SensoryFeedbackEvent.selection,
                  ),
                );
                ref
                    .read(providers.notificationAnalyticsProvider.notifier)
                    .setPeriod(value);
              }
            },
          ),
        ],
      ),
      child: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : state.error != null
              ? _buildError(state.error!)
              : state.analytics == null
                  ? Center(
                      child: Text(context.l10n.notificationAnalyticsNoData),
                    )
                  : _buildContent(state.analytics!),
    );
  }

  Widget _buildError(String error) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: DS.spacing64, color: DS.error),
            const SizedBox(height: DS.spacing16),
            Text(context.l10n.notificationAnalyticsLoadFailed(error)),
            const SizedBox(height: DS.spacing16),
            SparkleButton(
              onPressed: () => ref
                  .read(providers.notificationAnalyticsProvider.notifier)
                  .refresh(),
              label: context.l10n.retry,
            ),
          ],
        ),
      );

  Widget _buildContent(NotificationAnalytics analytics) =>
      SingleChildScrollView(
        padding: const EdgeInsets.all(DS.spacing16),
        child: ContentConstraint(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Summary cards
              _buildSummarySection(analytics.summary),

              const SizedBox(height: DS.spacing24),

              // Type distribution
              _buildTypeDistributionSection(analytics.byType),

              const SizedBox(height: DS.spacing24),

              if (analytics.interventionFunnels.isNotEmpty) ...[
                _buildInterventionFunnelsSection(analytics.interventionFunnels),
                const SizedBox(height: DS.spacing24),
              ],

              if (analytics.toneEffectiveness.isNotEmpty) ...[
                _buildToneEffectivenessSection(analytics.toneEffectiveness),
                const SizedBox(height: DS.spacing24),
              ],

              if (analytics.timeToActionBuckets.isNotEmpty) ...[
                _buildTimeToActionSection(analytics.timeToActionBuckets),
                const SizedBox(height: DS.spacing24),
              ],

              // Trends
              _buildTrendsSection(analytics.trends),

              const SizedBox(height: DS.spacing24),

              // Hourly distribution
              _buildHourlyDistributionSection(analytics.hourlyDistribution),
            ],
          ),
        ),
      );

  Widget _buildInterventionFunnelsSection(
    List<InterventionFunnelStats> funnels,
  ) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.notificationAnalyticsFunnelTitle,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: DS.spacing16),
          ...funnels.map(
            (funnel) => GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              margin: const EdgeInsets.only(bottom: DS.spacing12),
              padding: const EdgeInsets.all(DS.spacing16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    funnel.dimension,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: DS.spacing12),
                  _buildProgressBar(
                      context.l10n.notificationAnalyticsCreated, funnel.created, funnel.created.toDouble()),
                  const SizedBox(height: DS.spacing8),
                  _buildProgressBar(
                      context.l10n.notificationAnalyticsDelivered, funnel.delivered, funnel.created.toDouble()),
                  const SizedBox(height: DS.spacing8),
                  _buildProgressBar(
                      context.l10n.notificationAnalyticsSeen, funnel.seen, funnel.delivered.toDouble()),
                  const SizedBox(height: DS.spacing8),
                  _buildProgressBar(
                      context.l10n.notificationAnalyticsAccepted, funnel.accepted, funnel.seen.toDouble()),
                  const SizedBox(height: DS.spacing8),
                  _buildProgressBar(
                      context.l10n.notificationAnalyticsActed, funnel.acted, funnel.accepted.toDouble()),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    context.l10n.notificationAnalyticsAcceptanceActionRate(funnel.acceptanceRate.toStringAsFixed(1), funnel.actionRate.toStringAsFixed(1)),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                ],
              ),
            ),
          ),
        ],
      );

  Widget _buildToneEffectivenessSection(
    List<InterventionToneEffectiveness> items,
  ) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.notificationAnalyticsToneEffectivenessTitle,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: DS.spacing16),
          Wrap(
            spacing: DS.spacing12,
            runSpacing: DS.spacing12,
            children: items
                .map(
                  (item) => SizedBox(
                    width: 220,
                    child: GraphiteCardSurface(
                      surfaceRole: SparkleSurfaceRole.card,
                      padding: const EdgeInsets.all(DS.spacing16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${item.tone} · ${item.channel}',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: DS.spacing8),
                          Text(context.l10n.notificationAnalyticsCreatedCount(item.created)),
                          Text(context.l10n.notificationAnalyticsAcceptedCount(item.accepted)),
                          Text(context.l10n.notificationAnalyticsActedCount(item.acted)),
                          Text(context.l10n.notificationAnalyticsEffectiveCount(item.effective)),
                          const SizedBox(height: DS.spacing8),
                          Text(
                            context.l10n.notificationAnalyticsActedEffectiveRate(item.actedRate.toStringAsFixed(1), item.effectiveRate.toStringAsFixed(1)),
                            style:
                                Theme.of(context).textTheme.bodySmall?.copyWith(
                                      color: DS.textSecondary,
                                    ),
                          ),
                        ],
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      );

  Widget _buildTimeToActionSection(
    List<InterventionTimeToActionBucket> buckets,
  ) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.notificationAnalyticsTimeToActionTitle,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: DS.spacing16),
          GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            padding: const EdgeInsets.all(DS.spacing16),
            child: Wrap(
              spacing: DS.spacing12,
              runSpacing: DS.spacing12,
              children: buckets
                  .map(
                    (bucket) => _buildTrendMetricChip(
                      '${bucket.label}:',
                      bucket.count,
                    ),
                  )
                  .toList(),
            ),
          ),
        ],
      );

  Widget _buildSummarySection(NotificationAnalyticsSummary summary) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.notificationAnalyticsSummary,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: DS.spacing16),
          LayoutBuilder(
            builder: (context, constraints) {
              final cards = [
                _buildStatCard(
                  context.l10n.notificationAnalyticsTotalSent,
                  '${summary.totalSent}',
                  Icons.send,
                ),
                _buildStatCard(
                  context.l10n.notificationAnalyticsTotalViewed,
                  '${summary.totalViewed}',
                  Icons.visibility,
                ),
                _buildStatCard(
                  context.l10n.notificationAnalyticsTotalClicked,
                  '${summary.totalClicked}',
                  Icons.touch_app,
                ),
                _buildStatCard(
                  context.l10n.notificationAnalyticsAcceptSuggestion,
                  '${summary.totalAccepted}',
                  Icons.check_circle_outline,
                ),
                _buildStatCard(
                  context.l10n.notificationAnalyticsStartExecution,
                  '${summary.totalActed}',
                  Icons.play_circle_outline,
                ),
                _buildStatCard(
                  context.l10n.notificationAnalyticsViewRate,
                  '${summary.viewRate.toStringAsFixed(1)}%',
                  Icons.pie_chart,
                ),
                _buildStatCard(
                  context.l10n.notificationAnalyticsAcceptanceRate,
                  '${summary.acceptanceRate.toStringAsFixed(1)}%',
                  Icons.trending_up,
                ),
                _buildStatCard(
                  context.l10n.notificationAnalyticsActionRate,
                  '${summary.actionRate.toStringAsFixed(1)}%',
                  Icons.directions_run,
                ),
              ];

              if (constraints.maxWidth < 420) {
                final tileWidth = (constraints.maxWidth - DS.spacing12) / 2;
                return Wrap(
                  spacing: DS.spacing12,
                  runSpacing: DS.spacing12,
                  children: [
                    for (var i = 0; i < cards.length; i++)
                      SizedBox(
                        width: tileWidth,
                        child: SparkleStaggerItem(
                          index: i,
                          child: cards[i],
                        ),
                      ),
                  ],
                );
              }

              return Column(
                children: [
                  for (var rowIndex = 0;
                      rowIndex < cards.length;
                      rowIndex += 2) ...[
                    SparkleStaggerItem(
                      index: rowIndex ~/ 2,
                      child: Row(
                        children: [
                          Expanded(child: cards[rowIndex]),
                          const SizedBox(width: DS.spacing12),
                          Expanded(
                            child: rowIndex + 1 < cards.length
                                ? cards[rowIndex + 1]
                                : const SizedBox.shrink(),
                          ),
                        ],
                      ),
                    ),
                    if (rowIndex + 2 < cards.length)
                      const SizedBox(height: DS.spacing12),
                  ],
                ],
              );
            },
          ),
        ],
      );

  Widget _buildStatCard(String title, String value, IconData icon) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  icon,
                  size: 20,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Align(
              alignment: Alignment.centerLeft,
              child: FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Text(
                  value,
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
              ),
            ),
          ],
        ),
      );

  Widget _buildTypeDistributionSection(
    Map<String, NotificationTypeStats> byType,
  ) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.notificationAnalyticsByType,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: DS.spacing16),
          ...byType.entries.toList().asMap().entries.map((entry) {
            final stats = entry.value.value;
            final typeKey = entry.value.key;
            return _buildTypeStatCard(
              typeKey == 'system'
                  ? context.l10n.notificationSourceSystem
                  : context.l10n.notificationSourceIntervention,
              stats,
            );
          }),
        ],
      );

  Widget _buildTypeStatCard(
    String title,
    NotificationTypeStats stats,
  ) =>
      SparkleStaggerItem(
        index: stats.sent,
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          margin: const EdgeInsets.only(bottom: DS.spacing12),
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: DS.spacing12),
              Row(
                children: [
                  Expanded(
                    child: _buildProgressBar(
                      context.l10n.notificationAnalyticsSent,
                      stats.sent,
                      stats.sent.toDouble(),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing8),
              Row(
                children: [
                  Expanded(
                    child: _buildProgressBar(
                      context.l10n.notificationAnalyticsViewed,
                      stats.viewed,
                      stats.sent.toDouble(),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing8),
              if (title == context.l10n.notificationSourceIntervention) ...[
                Row(
                  children: [
                    Expanded(
                      child: _buildProgressBar(
                        context.l10n.notificationAnalyticsAcceptedLabel,
                        stats.accepted,
                        stats.viewed.toDouble(),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing8),
                Row(
                  children: [
                    Expanded(
                      child: _buildProgressBar(
                        context.l10n.notificationAnalyticsStartedLabel,
                        stats.acted,
                        stats.accepted.toDouble(),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing8),
              ],
              Text(
                title == context.l10n.notificationSourceIntervention
                    ? '${context.l10n.notificationAnalyticsViewRate}: ${stats.viewRate.toStringAsFixed(1)}% · ${I18nService.instance.isChinese ? '接受率' : 'Acceptance'}: ${stats.acceptanceRate.toStringAsFixed(1)}% · ${I18nService.instance.isChinese ? '行动率' : 'Action'}: ${stats.actionRate.toStringAsFixed(1)}%'
                    : '${context.l10n.notificationAnalyticsViewRate}: ${stats.viewRate.toStringAsFixed(1)}%',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ],
          ),
        ),
      );

  Widget _buildProgressBar(String label, int value, double total) {
    final percentage = total > 0 ? (value / total * 100) : 0.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(fontSize: 12)),
            Text(
              '$value (${percentage.toStringAsFixed(0)}%)',
              style: const TextStyle(fontSize: 12, fontWeight: DS.fontWeightBold),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing4),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: percentage / 100,
            minHeight: 8,
            backgroundColor: DS.surfaceTertiary,
            valueColor: AlwaysStoppedAnimation<Color>(
              Theme.of(context).colorScheme.primary,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTrendsSection(List<NotificationTrendData> trends) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.notificationAnalyticsTrends,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: DS.spacing16),
          SparkleStaggerItem(
            index: 0,
            child: GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              padding: const EdgeInsets.all(DS.spacing16),
              child: _buildTrendChart(trends),
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _buildTrendMetricChip(
                  I18nService.instance.isChinese ? '查看' : 'Viewed', trends.fold(0, (sum, item) => sum + item.viewed)),
              _buildTrendMetricChip(
                  I18nService.instance.isChinese ? '接受' : 'Accepted', trends.fold(0, (sum, item) => sum + item.accepted)),
              _buildTrendMetricChip(
                  I18nService.instance.isChinese ? '开始' : 'Acted', trends.fold(0, (sum, item) => sum + item.acted)),
            ],
          ),
        ],
      );

  Widget _buildTrendChart(List<NotificationTrendData> trends) {
    if (trends.isEmpty) {
      return Center(child: Text(context.l10n.notificationAnalyticsNoTrends));
    }

    final maxValue =
        trends.map((t) => t.sent).reduce((a, b) => a > b ? a : b).toDouble();

    return CustomPaint(
      size: const Size(double.infinity, double.infinity),
      painter: _TrendChartPainter(trends, maxValue, DS.info),
    );
  }

  Widget _buildHourlyDistributionSection(List<int> distribution) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.notificationAnalyticsHourlyDistribution,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: DS.spacing16),
          SparkleStaggerItem(
            index: 0,
            child: GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              padding: const EdgeInsets.all(DS.spacing16),
              child: _buildHourlyChart(distribution),
            ),
          ),
        ],
      );

  Widget _buildTrendMetricChip(String label, int value) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: DS.surfaceTertiary,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text('$label $value'),
      );

  Widget _buildHourlyChart(List<int> distribution) {
    if (distribution.isEmpty) {
      return Center(child: Text(context.l10n.notificationAnalyticsNoData));
    }

    final maxValue = distribution.reduce((a, b) => a > b ? a : b).toDouble();

    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: List.generate(24, (index) {
        final value = distribution[index].toDouble();
        final height = maxValue > 0 ? (value / maxValue * 100) : 0.0;

        return Column(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            Container(
              width: DS.spacing8,
              height: height * 1.2, // Scale to fit container
              decoration: BoxDecoration(
                color: index % 6 == 0
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context)
                        .colorScheme
                        .primary
                        .withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            const SizedBox(height: DS.spacing4),
            if (index % 6 == 0)
              Text(
                '$index',
                style: const TextStyle(fontSize: 10),
              ),
          ],
        );
      }),
    );
  }
}

/// Custom painter for trend chart
class _TrendChartPainter extends CustomPainter {
  _TrendChartPainter(this.trends, this.maxValue, this.lineColor);
  final List<NotificationTrendData> trends;
  final double maxValue;
  final Color lineColor;

  @override
  void paint(Canvas canvas, Size size) {
    if (trends.isEmpty || maxValue == 0) return;

    const padding = 40.0;
    final chartWidth = size.width - padding * 2;
    final chartHeight = size.height - padding * 2;

    final paint = Paint()
      ..color = lineColor
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    final fillPaint = Paint()
      ..color = lineColor.withValues(alpha: 0.2)
      ..style = PaintingStyle.fill;

    final points = <Offset>[];

    for (var i = 0; i < trends.length; i++) {
      final trend = trends[i];
      final x = padding + (i / (trends.length - 1)) * chartWidth;
      final y = size.height - padding - (trend.sent / maxValue) * chartHeight;
      points.add(Offset(x, y));
    }

    // Draw fill
    final fillPath = Path()
      ..moveTo(points.first.dx, size.height - padding)
      ..addPolygon(points, true)
      ..lineTo(points.last.dx, size.height - padding)
      ..close();

    canvas.drawPath(fillPath, fillPaint);

    // Draw line
    final path = Path()..moveTo(points.first.dx, points.first.dy);
    for (var i = 1; i < points.length; i++) {
      path.lineTo(points[i].dx, points[i].dy);
    }
    canvas.drawPath(path, paint);

    // Draw points
    for (final point in points) {
      canvas.drawCircle(point, 4, Paint()..color = lineColor);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
