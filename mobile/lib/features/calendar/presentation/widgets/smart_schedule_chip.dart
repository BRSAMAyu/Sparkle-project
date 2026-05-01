import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/features/calendar/data/services/smart_schedule_service.dart';

/// Smart Schedule Chip
/// 智能排程 Chip 组件
///
/// Displays suggested time for a task and allows quick scheduling.
class SmartScheduleChip extends ConsumerWidget {
  const SmartScheduleChip({
    required this.estimatedMinutes,
    required this.onTimeSelected,
    this.energyCost = 2,
    this.difficulty = 2,
    this.preferredDate,
    this.compact = false,
    super.key,
  });

  final int estimatedMinutes;
  final int energyCost;
  final int difficulty;
  final DateTime? preferredDate;
  final bool compact;

  /// Callback when a time slot is selected
  final void Function(SuggestedTime suggestion) onTimeSelected;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final params = TaskScheduleParams(
      estimatedMinutes: estimatedMinutes,
      energyCost: energyCost,
      difficulty: difficulty,
      preferredDate: preferredDate,
    );

    final suggestionsAsync = ref.watch(suggestedTimeSlotsProvider(params));

    return suggestionsAsync.when(
      data: (suggestions) {
        if (suggestions.isEmpty) {
          return const SizedBox.shrink();
        }

        if (compact) {
          return _CompactChip(
            suggestion: suggestions.first,
            onTap: () => _showTimePicker(context, suggestions),
          );
        }

        return _FullChip(
          suggestion: suggestions.first,
          onTap: () => _showTimePicker(context, suggestions),
        );
      },
      loading: () => _LoadingChip(compact: compact),
      error: (_, __) => const SizedBox.shrink(),
    );
  }

  void _showTimePicker(BuildContext context, List<SuggestedTime> suggestions) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.surfacePrimary,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        builder: (context) => _TimeSuggestionSheet(
          suggestions: suggestions,
          onSelected: (suggestion) {
            Navigator.pop(context);
            onTimeSelected(suggestion);
          },
        ),
      ),
    );
  }
}

/// Compact chip showing just the time
class _CompactChip extends StatelessWidget {
  const _CompactChip({
    required this.suggestion,
    required this.onTap,
  });

  final SuggestedTime suggestion;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing8,
            vertical: DS.spacing4,
          ),
          decoration: BoxDecoration(
            color: DS.brandPrimary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: DS.brandPrimary.withValues(alpha: 0.3),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.access_time_rounded,
                size: 12,
                color: DS.brandPrimary,
              ),
              const SizedBox(width: DS.spacing4),
              Text(
                suggestion.timeSlot.startTimeString,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.brandPrimary,
                ),
              ),
            ],
          ),
        ),
      );
}

/// Full chip showing time and confidence
class _FullChip extends StatelessWidget {
  const _FullChip({
    required this.suggestion,
    required this.onTap,
  });

  final SuggestedTime suggestion;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                DS.brandPrimary.withValues(alpha: 0.1),
                DS.brandPrimary.withValues(alpha: 0.05),
              ],
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: DS.brandPrimary.withValues(alpha: 0.2),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(DS.spacing6),
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.auto_awesome_rounded,
                  size: 14,
                  color: DS.brandPrimary,
                ),
              ),
              const SizedBox(width: DS.spacing10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '建议时间',
                    style: TextStyle(
                      fontSize: 10,
                      color: DS.textSecondary,
                    ),
                  ),
                  Text(
                    suggestion.displayString,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: DS.fontWeightSemibold,
                      color: DS.brandPrimary,
                    ),
                  ),
                ],
              ),
              const SizedBox(width: DS.spacing8),
              Icon(
                Icons.chevron_right_rounded,
                size: 16,
                color: DS.textSecondary,
              ),
            ],
          ),
        ),
      );
}

/// Loading chip placeholder
class _LoadingChip extends StatelessWidget {
  const _LoadingChip({required this.compact});

  final bool compact;

  @override
  Widget build(BuildContext context) => Container(
        padding: EdgeInsets.symmetric(
          horizontal: compact ? DS.spacing8 : DS.spacing12,
          vertical: compact ? DS.spacing4 : DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceOverlay,
          borderRadius: BorderRadius.circular(compact ? 12 : 16),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: compact ? 12 : 14,
              height: compact ? 12 : 14,
              child: CircularProgressIndicator(
                strokeWidth: 1.5,
                color: DS.brandPrimary.withValues(alpha: 0.5),
              ),
            ),
            if (!compact) ...[
              const SizedBox(width: DS.spacing8),
              Text(
                '分析中...',
                style: TextStyle(
                  fontSize: 12,
                  color: DS.textSecondary,
                ),
              ),
            ],
          ],
        ),
      );
}

/// Bottom sheet showing all time suggestions
class _TimeSuggestionSheet extends StatelessWidget {
  const _TimeSuggestionSheet({
    required this.suggestions,
    required this.onSelected,
  });

  final List<SuggestedTime> suggestions;
  final void Function(SuggestedTime) onSelected;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.auto_awesome_rounded,
                  color: DS.brandPrimary,
                  size: 20,
                ),
                const SizedBox(width: DS.spacing10),
                Text(
                  '智能时间建议',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: DS.textPrimary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              '根据您的偏好和认知模式推荐',
              style: TextStyle(
                fontSize: 13,
                color: DS.textSecondary,
              ),
            ),
            const SizedBox(height: DS.spacing20),
            ...suggestions.map((suggestion) => _SuggestionTile(
                  suggestion: suggestion,
                  onTap: () => onSelected(suggestion),
                ),),
            const SizedBox(height: DS.spacing16),
            // Safe area padding
            SizedBox(height: MediaQuery.of(context).padding.bottom),
          ],
        ),
      );
}

/// Single suggestion tile
class _SuggestionTile extends StatelessWidget {
  const _SuggestionTile({
    required this.suggestion,
    required this.onTap,
  });

  final SuggestedTime suggestion;
  final VoidCallback onTap;

  Color _getQualityColor() {
    switch (suggestion.timeSlot.quality) {
      case TimeSlotQuality.peak:
        return DS.success;
      case TimeSlotQuality.normal:
        return DS.brandPrimary;
      case TimeSlotQuality.low:
        return DS.textSecondary;
      case TimeSlotQuality.blocked:
        return DS.error;
    }
  }

  IconData _getQualityIcon() {
    switch (suggestion.timeSlot.quality) {
      case TimeSlotQuality.peak:
        return Icons.bolt_rounded;
      case TimeSlotQuality.normal:
        return Icons.schedule_rounded;
      case TimeSlotQuality.low:
        return Icons.coffee_rounded;
      case TimeSlotQuality.blocked:
        return Icons.block_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final qualityColor = _getQualityColor();

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: DS.spacing10),
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: qualityColor.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: qualityColor.withValues(alpha: 0.2),
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.spacing10),
              decoration: BoxDecoration(
                color: qualityColor.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                _getQualityIcon(),
                size: 20,
                color: qualityColor,
              ),
            ),
            const SizedBox(width: DS.spacing16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    suggestion.displayString,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: DS.fontWeightSemibold,
                      color: DS.textPrimary,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    suggestion.reason,
                    style: TextStyle(
                      fontSize: 12,
                      color: DS.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            // Confidence indicator
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing8,
                vertical: DS.spacing4,
              ),
              decoration: BoxDecoration(
                color: qualityColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                '${(suggestion.confidence * 100).toInt()}%',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: DS.fontWeightSemibold,
                  color: qualityColor,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Quick schedule button for task cards
/// 任务卡片上的快速排程按钮
class QuickScheduleButton extends ConsumerWidget {
  const QuickScheduleButton({
    required this.estimatedMinutes,
    required this.onTimeSelected,
    this.energyCost = 2,
    this.difficulty = 2,
    super.key,
  });

  final int estimatedMinutes;
  final int energyCost;
  final int difficulty;
  final void Function(SuggestedTime suggestion) onTimeSelected;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final params = TaskScheduleParams(
      estimatedMinutes: estimatedMinutes,
      energyCost: energyCost,
      difficulty: difficulty,
    );

    final suggestionsAsync = ref.watch(suggestedTimeSlotsProvider(params));

    return suggestionsAsync.maybeWhen(
      data: (suggestions) {
        if (suggestions.isEmpty) return const SizedBox.shrink();

        return GestureDetector(
          onTap: () {
            // Quick schedule with best suggestion
            onTimeSelected(suggestions.first);
          },
          child: Container(
            padding: const EdgeInsets.all(DS.spacing6),
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              Icons.schedule_rounded,
              size: 16,
              color: DS.brandPrimary,
            ),
          ),
        );
      },
      orElse: () => const SizedBox.shrink(),
    );
  }
}
