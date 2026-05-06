import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/goal/data/models/scenario_pack_models.dart';

/// Compact card showing the user's journey progress through a scenario pack.
///
/// Displays: pack name, day X of Y, node progress bar, current phase label.
class JourneyProgressCard extends StatelessWidget {
  const JourneyProgressCard({
    required this.progress,
    this.onTap,
    super.key,
  });

  final JourneyProgress progress;
  final VoidCallback? onTap;

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    if (!progress.hasPack) return const SizedBox.shrink();

    final pct = (progress.progress * 100).round();
    final dayLabel = progress.horizonDays > 0
        ? _t(
            '第 ${progress.dayNumber} 天 / 共 ${progress.horizonDays} 天',
            'Day ${progress.dayNumber} of ${progress.horizonDays}',
          )
        : _t('第 ${progress.dayNumber} 天', 'Day ${progress.dayNumber}');

    return Semantics(
      container: true,
      label: _t(
        '旅程进度：$pct%',
        'Journey progress: $pct%',
      ),
      child: GestureDetector(
        onTap: onTap,
        child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: DS.surfaceHigh,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.2)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.map_outlined, size: 18, color: DS.brandPrimary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    progress.packName ?? '',
                    style: DS.titleMedium.copyWith(
                      color: DS.textPrimary,
                      fontSize: 14,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Text(
                  '$pct%',
                  style: DS.labelSmall.copyWith(
                    color: DS.brandPrimary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: progress.progress.clamp(0.0, 1.0),
                minHeight: 6,
                backgroundColor: DS.surfaceTertiary,
                valueColor: AlwaysStoppedAnimation(DS.brandPrimary),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  dayLabel,
                  style: DS.labelSmall.copyWith(color: DS.textSecondary),
                ),
                if (progress.currentNode != null)
                  Text(
                    _currentNodeLabel(progress.currentNodeIndex),
                    style: DS.labelSmall.copyWith(color: DS.textSecondary),
                  ),
              ],
            ),
            if (!progress.isOnBackbone) ...[
              const SizedBox(height: 6),
              Row(
                children: [
                  Icon(Icons.explore_outlined, size: 14, color: DS.warning),
                  const SizedBox(width: 4),
                  Text(
                    _t('偏离主线，自主探索中', 'Off backbone — exploring'),
                    style: DS.labelSmall.copyWith(color: DS.warning),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
      ),
    );
  }

  String _currentNodeLabel(int index) {
    final phase = index + 1;
    return _t('阶段 $phase', 'Phase $phase');
  }
}
