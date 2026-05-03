import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/materials.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/task/task_routes.dart';

class HeatmapDay {
  const HeatmapDay({
    required this.date,
    required this.minutes,
    required this.tasksCompleted,
  });

  final String date;
  final double minutes;
  final int tasksCompleted;

  factory HeatmapDay.fromJson(Map<String, dynamic> json) => HeatmapDay(
        date: json['date'] as String,
        minutes: (json['minutes'] as num).toDouble(),
        tasksCompleted: (json['tasks_completed'] as num?)?.toInt() ?? 0,
      );
}

final learningHeatmapProvider =
    FutureProvider.autoDispose.family<List<HeatmapDay>, int>((ref, days) async {
  final apiClient = ref.read(apiClientProvider);
  final response = await apiClient.get<List<dynamic>>(
    ApiEndpoints.statsActivityHeatmap,
    queryParameters: {'days': days},
  );
  final list = response.data as List<dynamic>;
  return list
      .map((entry) => HeatmapDay.fromJson(entry as Map<String, dynamic>))
      .toList();
});

class LearningHeatmapColor {
  static int levelForMinutes(double minutes) {
    if (minutes <= 0) return 0;
    if (minutes < 30) return 1;
    if (minutes <= 60) return 2;
    return 3;
  }

  static Color colorForMinutes(
    double minutes, {
    required Brightness brightness,
  }) {
    final isDark = brightness == Brightness.dark;
    switch (levelForMinutes(minutes)) {
      case 0:
        return isDark
            ? DS.surfaceTertiary.withValues(alpha: 0.35)
            : DS.surfaceTertiary.withValues(alpha: 0.25);
      case 1:
        return DS.brandPrimary.withValues(alpha: isDark ? 0.30 : 0.35);
      case 2:
        return DS.brandPrimary.withValues(alpha: isDark ? 0.55 : 0.60);
      case 3:
        return DS.brandPrimary.withValues(alpha: isDark ? 0.85 : 0.90);
      default:
        return DS.brandPrimary;
    }
  }
}

class LearningHeatmapWidget extends ConsumerWidget {
  const LearningHeatmapWidget({
    super.key,
    this.days = 90,
    this.data,
  });

  final int days;
  final List<HeatmapDay>? data;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final injectedData = data;
    if (injectedData != null) {
      return _HeatmapContent(days: days, data: injectedData);
    }

    final asyncData = ref.watch(learningHeatmapProvider(days));
    return asyncData.when(
      loading: () => const _HeatmapSkeleton(),
      error: (_, __) => CompactErrorCard(
        onRetry: () => ref.invalidate(learningHeatmapProvider(days)),
      ),
      data: (loadedData) => _HeatmapContent(days: days, data: loadedData),
    );
  }
}

class _HeatmapContent extends StatelessWidget {
  const _HeatmapContent({
    required this.days,
    required this.data,
  });

  final int days;
  final List<HeatmapDay> data;

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    final isChinese = Localizations.localeOf(context)
        .languageCode
        .toLowerCase()
        .startsWith('zh');
    final isEmpty = data.every(
      (day) => day.minutes <= 0 && day.tasksCompleted <= 0,
    );
    final today = DateTime.now();
    final startDate = DateTime(
      today.year,
      today.month,
      today.day,
    ).subtract(Duration(days: days - 1));
    final leadingEmpty = startDate.weekday - 1;
    final totalWeeks = ((leadingEmpty + days) / 7).ceil();
    final totalCells = leadingEmpty + days;
    final dayMap = <String, HeatmapDay>{for (final day in data) day.date: day};

    return MaterialStyler(
      key: const ValueKey('learning-heatmap-widget'),
      material: AppMaterials.ceramic(context),
      borderRadius: DS.borderRadius20,
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                context.l10n.heatmapTitle,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.textPrimary,
                ),
              ),
              Text(
                context.l10n.heatmapDays(days),
                style: TextStyle(
                  fontSize: 11,
                  color: DS.textTertiary,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          if (isEmpty)
            _HeatmapEmptyState(isChinese: isChinese)
          else ...[
            _HeatmapGrid(
              brightness: brightness,
              data: dayMap,
              days: days,
              isChinese: isChinese,
              leadingEmpty: leadingEmpty,
              startDate: startDate,
              today: DateTime(today.year, today.month, today.day),
              totalCells: totalCells,
              totalWeeks: totalWeeks,
            ),
            const SizedBox(height: DS.spacing8),
            _HeatmapLegend(
              brightness: brightness,
              isChinese: isChinese,
            ),
          ],
        ],
      ),
    );
  }
}

class _HeatmapGrid extends StatelessWidget {
  const _HeatmapGrid({
    required this.brightness,
    required this.data,
    required this.days,
    required this.isChinese,
    required this.leadingEmpty,
    required this.startDate,
    required this.today,
    required this.totalCells,
    required this.totalWeeks,
  });

  final Brightness brightness;
  final Map<String, HeatmapDay> data;
  final int days;
  final bool isChinese;
  final int leadingEmpty;
  final DateTime startDate;
  final DateTime today;
  final int totalCells;
  final int totalWeeks;

  static const double _cellGap = 2.5;

  @override
  Widget build(BuildContext context) {
    final weekdayLabels = isChinese
        ? const ['一', '二', '三', '四', '五', '六', '日']
        : const ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            for (var row = 0; row < 7; row++)
              SizedBox(
                height: 12 + _cellGap,
                child: Center(
                  child: Text(
                    weekdayLabels[row],
                    style: TextStyle(
                      fontSize: 8,
                      color: DS.textTertiary,
                      fontWeight: DS.fontWeightMedium,
                    ),
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(width: 4),
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final cellSize =
                  (constraints.maxWidth - _cellGap * (totalWeeks - 1)) /
                      totalWeeks;
              final size = max(8.0, min(cellSize, 14.0));

              return SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: List.generate(totalWeeks, (weekIndex) {
                    return Padding(
                      padding: EdgeInsets.only(
                        left: weekIndex > 0 ? _cellGap : 0,
                      ),
                      child: Column(
                        children: List.generate(7, (rowIndex) {
                          final cellIndex = weekIndex * 7 + rowIndex;
                          if (cellIndex < leadingEmpty ||
                              cellIndex >= totalCells) {
                            return SizedBox(
                              width: size,
                              height: size + _cellGap,
                            );
                          }

                          final dayOffset = cellIndex - leadingEmpty;
                          final currentDate =
                              startDate.add(Duration(days: dayOffset));
                          final dateKey = _formatDate(currentDate);
                          final dayData = data[dateKey];
                          final minutes = dayData?.minutes ?? 0;
                          final tasksCompleted = dayData?.tasksCompleted ?? 0;

                          return _HeatmapCell(
                            brightness: brightness,
                            dateKey: dateKey,
                            gap: _cellGap,
                            isToday: _isSameDay(currentDate, today),
                            size: size,
                            tooltipMessage: _tooltipText(
                              dateKey: dateKey,
                              minutes: minutes,
                              tasksCompleted: tasksCompleted,
                              isChinese: isChinese,
                            ),
                            minutes: minutes,
                          );
                        }),
                      ),
                    );
                  }),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  static String _formatDate(DateTime value) =>
      '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

  static bool _isSameDay(DateTime left, DateTime right) =>
      left.year == right.year &&
      left.month == right.month &&
      left.day == right.day;

  static String _tooltipText({
    required String dateKey,
    required double minutes,
    required int tasksCompleted,
    required bool isChinese,
  }) {
    final roundedMinutes = minutes.round();
    final summary = roundedMinutes == 0 && tasksCompleted == 0
        ? (isChinese
            ? '尚未开始学习，先完成一个 15 分钟的小任务吧'
            : 'Not started yet. Begin with one 15-minute task.')
        : isChinese
            ? '学习了 $roundedMinutes 分钟 · 完成了 $tasksCompleted 个任务'
            : 'Studied $roundedMinutes min · Completed $tasksCompleted task${tasksCompleted == 1 ? '' : 's'}';
    return '$dateKey\n$summary';
  }
}

class _HeatmapEmptyState extends StatelessWidget {
  const _HeatmapEmptyState({required this.isChinese});

  final bool isChinese;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary.withValues(alpha: 0.55),
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border.withValues(alpha: 0.75)),
      ),
      child: Column(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.local_fire_department_outlined,
              color: DS.brandPrimary,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            context.l10n.heatmapNotStarted,
            style: TextStyle(
              fontSize: DS.fontSizeBase,
              fontWeight: DS.fontWeightBold,
              color: DS.textPrimary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            isChinese
                ? '先创建一个今日任务并开始学习，连续记录后这里会逐渐亮起来。'
                : 'Create a task and start learning. Your streak will light up here soon.',
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textSecondary,
              height: 1.45,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: DS.spacing16),
          FilledButton.icon(
            onPressed: () => context.push(TaskRoutes.taskCreate),
            icon: const Icon(Icons.add_task_rounded),
            label: Text(context.l10n.heatmapCreateTask),
          ),
        ],
      ),
    );
  }
}

class _HeatmapLegend extends StatelessWidget {
  const _HeatmapLegend({
    required this.brightness,
    required this.isChinese,
  });

  final Brightness brightness;
  final bool isChinese;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          context.l10n.heatmapLess,
          style: TextStyle(fontSize: 9, color: DS.textTertiary),
        ),
        const SizedBox(width: 3),
        for (var level = 0; level <= 3; level++)
          Padding(
            padding: const EdgeInsets.only(right: 2),
            child: Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: LearningHeatmapColor.colorForMinutes(
                  (switch (level) {
                    0 => 0,
                    1 => 10,
                    2 => 60,
                    _ => 90,
                  })
                      .toDouble(),
                  brightness: brightness,
                ),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
        const SizedBox(width: 3),
        Text(
          context.l10n.heatmapMore,
          style: TextStyle(fontSize: 9, color: DS.textTertiary),
        ),
        const SizedBox(width: DS.spacing12),
        Text(
          context.l10n.heatmapMinutes,
          style: TextStyle(fontSize: 8, color: DS.textTertiary),
        ),
      ],
    );
  }
}

class _HeatmapCell extends StatefulWidget {
  const _HeatmapCell({
    required this.brightness,
    required this.dateKey,
    required this.gap,
    required this.isToday,
    required this.minutes,
    required this.size,
    required this.tooltipMessage,
  });

  final Brightness brightness;
  final String dateKey;
  final double gap;
  final bool isToday;
  final double minutes;
  final double size;
  final String tooltipMessage;

  @override
  State<_HeatmapCell> createState() => _HeatmapCellState();
}

class _HeatmapCellState extends State<_HeatmapCell> {
  bool _isTooltipVisible = false;
  Timer? _dismissTimer;

  @override
  void dispose() {
    _dismissTimer?.cancel();
    super.dispose();
  }

  void _showTooltip() {
    _dismissTimer?.cancel();
    setState(() => _isTooltipVisible = true);
    _dismissTimer = Timer(const Duration(seconds: 2), () {
      if (mounted) setState(() => _isTooltipVisible = false);
    });
  }

  void _hideTooltip() {
    _dismissTimer?.cancel();
    if (mounted) setState(() => _isTooltipVisible = false);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: widget.gap),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          GestureDetector(
            key: ValueKey('learning-heatmap-cell-${widget.dateKey}'),
            behavior: HitTestBehavior.opaque,
            onTap: _isTooltipVisible ? _hideTooltip : _showTooltip,
            child: Container(
              width: widget.size,
              height: widget.size,
              decoration: BoxDecoration(
                color: LearningHeatmapColor.colorForMinutes(
                  widget.minutes,
                  brightness: widget.brightness,
                ),
                borderRadius: BorderRadius.circular(2),
                border: widget.isToday
                    ? Border.all(
                        color: DS.brandPrimary.withValues(alpha: 0.8),
                        width: 1.5,
                      )
                    : null,
              ),
            ),
          ),
          if (_isTooltipVisible)
            Positioned(
              top: widget.size + 6,
              left: 0,
              child: Material(
                key: ValueKey('learning-heatmap-tooltip-${widget.dateKey}'),
                color: Theme.of(context).colorScheme.surface,
                elevation: 8,
                borderRadius: BorderRadius.circular(12),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 220),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing12,
                      vertical: DS.spacing10,
                    ),
                    child: Text(
                      widget.tooltipMessage,
                      style: TextStyle(
                        fontSize: 12,
                        color: DS.textPrimary,
                        height: 1.35,
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _HeatmapSkeleton extends StatelessWidget {
  const _HeatmapSkeleton();

  @override
  Widget build(BuildContext context) {
    return MaterialStyler(
      material: AppMaterials.ceramic(context),
      borderRadius: DS.borderRadius20,
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 120,
            height: 14,
            decoration: BoxDecoration(
              color: DS.surfaceTertiary.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: 2.5,
            runSpacing: 2.5,
            children: List.generate(
              91,
              (_) => Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: DS.surfaceTertiary.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
