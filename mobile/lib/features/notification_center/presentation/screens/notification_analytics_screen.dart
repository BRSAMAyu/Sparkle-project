import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/notification_center/data/models/notification_analytics_model.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_analytics_provider.dart' as providers;

/// Notification Analytics Screen
class NotificationAnalyticsScreen extends ConsumerStatefulWidget {
  const NotificationAnalyticsScreen({super.key});

  @override
  ConsumerState<NotificationAnalyticsScreen> createState() => _NotificationAnalyticsScreenState();
}

class _NotificationAnalyticsScreenState extends ConsumerState<NotificationAnalyticsScreen> {
  @override
  void initState() {
    super.initState();
    // Load analytics on init
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(providers.notificationAnalyticsProvider.notifier).loadAnalytics('7d');
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(providers.notificationAnalyticsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('通知统计'),
        actions: [
          DropdownButton<String>(
            value: state.period,
            underline: const SizedBox.shrink(),
            icon: const Icon(Icons.arrow_drop_down),
            items: providers.AnalyticsPeriod.all.map((period) => DropdownMenuItem(
                value: period.value,
                child: Text(period.label),
              ),).toList(),
            onChanged: (value) {
              if (value != null) {
                ref.read(providers.notificationAnalyticsProvider.notifier).setPeriod(value);
              }
            },
          ),
        ],
      ),
      body: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : state.error != null
              ? _buildError(state.error!)
              : state.analytics == null
                  ? const Center(child: Text('暂无数据'))
                  : _buildContent(state.analytics!),
    );
  }

  Widget _buildError(String error) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 64, color: Colors.red),
          const SizedBox(height: 16),
          Text('加载失败: $error'),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () => ref.read(providers.notificationAnalyticsProvider.notifier).refresh(),
            child: const Text('重试'),
          ),
        ],
      ),
    );

  Widget _buildContent(NotificationAnalytics analytics) => SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: ContentConstraint(
        child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Summary cards
          _buildSummarySection(analytics.summary),

          const SizedBox(height: 24),

          // Type distribution
          _buildTypeDistributionSection(analytics.byType),

          const SizedBox(height: 24),

          // Trends
          _buildTrendsSection(analytics.trends),

          const SizedBox(height: 24),

          // Hourly distribution
          _buildHourlyDistributionSection(analytics.hourlyDistribution),
        ],
      ),
      ),
    );

  Widget _buildSummarySection(NotificationAnalyticsSummary summary) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '汇总统计',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(child: _buildStatCard('发送总数', '${summary.totalSent}', Icons.send)),
            const SizedBox(width: 12),
            Expanded(child: _buildStatCard('查看数', '${summary.totalViewed}', Icons.visibility)),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: _buildStatCard('点击数', '${summary.totalClicked}', Icons.touch_app)),
            const SizedBox(width: 12),
            Expanded(child: _buildStatCard('查看率', '${summary.viewRate.toStringAsFixed(1)}%', Icons.pie_chart)),
          ],
        ),
      ],
    );

  Widget _buildStatCard(String title, String value, IconData icon) => Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 20, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 8),
              Text(
                title,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
              fontWeight: FontWeight.bold,
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
          '按类型统计',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 16),
        ...byType.entries.map((MapEntry<String, NotificationTypeStats> entry) {
          final stats = entry.value;
          return _buildTypeStatCard(
            entry.key == 'system' ? '系统通知' : '干预通知',
            stats.sent,
            stats.viewed,
            stats.viewRate,
          );
        }),
      ],
    );

  Widget _buildTypeStatCard(String title, int sent, int viewed, double viewRate) => Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildProgressBar('发送', sent, sent.toDouble()),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _buildProgressBar('查看', viewed, sent.toDouble()),
              ),
            ],
          ),
        ],
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
            Text('$value (${percentage.toStringAsFixed(0)}%)',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: percentage / 100,
            minHeight: 8,
            backgroundColor: Colors.grey[200],
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
          '趋势分析',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 16),
        Container(
          height: 200,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.3),
            ),
          ),
          child: _buildTrendChart(trends),
        ),
      ],
    );

  Widget _buildTrendChart(List<NotificationTrendData> trends) {
    if (trends.isEmpty) {
      return const Center(child: Text('暂无趋势数据'));
    }

    final maxValue =
        trends.map((t) => t.sent).reduce((a, b) => a > b ? a : b).toDouble();

    return CustomPaint(
      size: const Size(double.infinity, double.infinity),
      painter: _TrendChartPainter(trends, maxValue),
    );
  }

  Widget _buildHourlyDistributionSection(List<int> distribution) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '24小时分布',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 16),
        Container(
          height: 150,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.3),
            ),
          ),
          child: _buildHourlyChart(distribution),
        ),
      ],
    );

  Widget _buildHourlyChart(List<int> distribution) {
    if (distribution.isEmpty) {
      return const Center(child: Text('暂无数据'));
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
              width: 8,
              height: height * 1.2, // Scale to fit container
              decoration: BoxDecoration(
                color: index % 6 == 0
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context).colorScheme.primary.withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            const SizedBox(height: 4),
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
  _TrendChartPainter(this.trends, this.maxValue);
  final List<NotificationTrendData> trends;
  final double maxValue;

  @override
  void paint(Canvas canvas, Size size) {
    if (trends.isEmpty || maxValue == 0) return;

    const padding = 40.0;
    final chartWidth = size.width - padding * 2;
    final chartHeight = size.height - padding * 2;

    final paint = Paint()
      ..color = Colors.blue
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    final fillPaint = Paint()
      ..color = Colors.blue.withValues(alpha: 0.2)
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
      canvas.drawCircle(point, 4, Paint()..color = Colors.blue);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
