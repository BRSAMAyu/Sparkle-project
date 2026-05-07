import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/providers/locale_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Aggregated reflection data from the summary API.
class ReflectionSummaryData {
  const ReflectionSummaryData({
    required this.totalReflections,
    required this.days,
    required this.avgMood,
    required this.topThemes,
    required this.timeline,
  });

  factory ReflectionSummaryData.fromJson(Map<String, dynamic> json) {
    return ReflectionSummaryData(
      totalReflections: json['total_reflections'] as int? ?? 0,
      days: json['days'] as int? ?? 7,
      avgMood: (json['avg_mood'] as num?)?.toDouble(),
      topThemes: (json['top_themes'] as List<dynamic>?)
              ?.map((t) => _ThemeEntry.fromJson(t as Map<String, dynamic>))
              .toList() ??
          [],
      timeline: (json['timeline'] as List<dynamic>?)
              ?.map((e) => _TimelineEntry.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  final int totalReflections;
  final int days;
  final double? avgMood;
  final List<_ThemeEntry> topThemes;
  final List<_TimelineEntry> timeline;
}

class _ThemeEntry {
  const _ThemeEntry({required this.theme, required this.count});
  factory _ThemeEntry.fromJson(Map<String, dynamic> json) =>
      _ThemeEntry(theme: json['theme'] as String? ?? '', count: json['count'] as int? ?? 0);
  final String theme;
  final int count;
}

class _TimelineEntry {
  const _TimelineEntry({
    required this.feedbackId,
    required this.taskId,
    required this.createdAt,
    required this.completionQuality,
    required this.payload,
  });
  factory _TimelineEntry.fromJson(Map<String, dynamic> json) => _TimelineEntry(
        feedbackId: json['feedback_id'] as String? ?? '',
        taskId: json['task_id'] as String?,
        createdAt: json['created_at'] as String?,
        completionQuality: json['completion_quality'] as int?,
        payload: json['payload'] as Map<String, dynamic>? ?? {},
      );
  final String feedbackId;
  final String? taskId;
  final String? createdAt;
  final int? completionQuality;
  final Map<String, dynamic> payload;
}

/// Provider for reflection summary data.
final reflectionSummaryProvider =
    FutureProvider.family<ReflectionSummaryData, int>((ref, days) async {
  final api = ref.read(apiClientProvider);
  final response = await api.dio.get(
    '${ApiEndpoints.reflectionSummary}?days=$days',
  );
  return ReflectionSummaryData.fromJson(response.data as Map<String, dynamic>);
});

/// A screen that shows a timeline of recent task reflections with stats.
class ReflectionSummaryScreen extends ConsumerWidget {
  const ReflectionSummaryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isChinese = ref.watch(localeProvider).languageCode == 'zh';
    final summary = ref.watch(reflectionSummaryProvider(7));

    return Scaffold(
      appBar: AppBar(
        title: Text(isChinese ? '每日反思' : 'Daily Reflection'),
      ),
      body: summary.when(
        data: (data) => _buildContent(context, data, isChinese),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Text(isChinese ? '加载失败' : 'Failed to load'),
        ),
      ),
    );
  }

  Widget _buildContent(
      BuildContext context, ReflectionSummaryData data, bool isChinese) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildStatsCard(context, data, isChinese),
        const SizedBox(height: 16),
        if (data.topThemes.isNotEmpty) ...[
          _buildThemesCard(context, data, isChinese),
          const SizedBox(height: 16),
        ],
        _buildTimelineHeader(context, data, isChinese),
        ...data.timeline.map((e) => _buildTimelineItem(context, e, isChinese)),
        if (data.timeline.isEmpty)
          Padding(
            padding: const EdgeInsets.all(32),
            child: Text(
              isChinese ? '暂无反思记录\n完成专注任务后可以在这里回顾你的思考' : 'No reflections yet\nReflections appear here after you complete focus sessions',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
          ),
      ],
    );
  }

  Widget _buildStatsCard(BuildContext context, ReflectionSummaryData data, bool isChinese) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _StatItem(
              label: isChinese ? '反思次数' : 'Reflections',
              value: data.totalReflections.toString(),
            ),
            _StatItem(
              label: isChinese ? '平均心情' : 'Avg Mood',
              value: data.avgMood != null
                  ? '${data.avgMood!.toStringAsFixed(1)}/5'
                  : '--',
            ),
            _StatItem(
              label: isChinese ? '统计天数' : 'Days',
              value: data.days.toString(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildThemesCard(BuildContext context, ReflectionSummaryData data, bool isChinese) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              isChinese ? '常见主题' : 'Common Themes',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: data.topThemes
                  .map((t) => Chip(
                        label: Text(
                          '${t.theme} (${t.count})',
                          style: const TextStyle(fontSize: 12),
                        ),
                        visualDensity: VisualDensity.compact,
                      ))
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimelineHeader(BuildContext context, ReflectionSummaryData data, bool isChinese) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        isChinese ? '反思时间线' : 'Reflection Timeline',
        style: Theme.of(context).textTheme.titleSmall,
      ),
    );
  }

  Widget _buildTimelineItem(BuildContext context, _TimelineEntry entry, bool isChinese) {
    final dateStr = entry.createdAt ?? '';
    final quality = entry.completionQuality;
    final highlights = entry.payload['highlights'] as String?;
    final challenges = entry.payload['challenges'] as String?;
    final whatHelped = entry.payload['what_helped'] as String?;
    final whatWouldChange = entry.payload['what_would_change'] as String?;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  dateStr.length >= 10 ? dateStr.substring(0, 10) : dateStr,
                  style: Theme.of(context).textTheme.labelSmall,
                ),
                const Spacer(),
                if (quality != null)
                  Row(
                    children: List.generate(
                      5,
                      (i) => Icon(
                        i < quality ? Icons.star : Icons.star_border,
                        size: 14,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                  ),
              ],
            ),
            if (highlights != null && highlights.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                '${isChinese ? "亮点" : "Highlights"}: $highlights',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            if (challenges != null && challenges.isNotEmpty) ...[
              const SizedBox(height: 2),
              Text(
                '${isChinese ? "挑战" : "Challenges"}: $challenges',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            if (whatHelped != null && whatHelped.isNotEmpty) ...[
              const SizedBox(height: 2),
              Text(
                '${isChinese ? "帮助" : "What helped"}: $whatHelped',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            if (whatWouldChange != null && whatWouldChange.isNotEmpty) ...[
              const SizedBox(height: 2),
              Text(
                '${isChinese ? "改进" : "Change next time"}: $whatWouldChange',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  const _StatItem({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.labelSmall,
        ),
      ],
    );
  }
}
