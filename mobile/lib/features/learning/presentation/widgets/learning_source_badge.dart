import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/learning/data/learning_journey_models.dart';

/// 来源badge（SCREEN_FAMILIES「来源badge能跳原文片段」）：材料/错题的来源
/// 身份 + 版本 + 片段锚。版本从真实行读出（learning_journey.v2），不臆测。
class LearningSourceBadge extends StatelessWidget {
  const LearningSourceBadge({
    required this.source,
    super.key,
    this.onOpenFragment,
    this.compact = false,
  });

  final JourneySourceRef source;
  final VoidCallback? onOpenFragment;

  /// 紧凑模式（列表行内）。
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = context.l10n;
    final anchor = source.fragmentAnchor ?? '';
    final label =
        '${l10n.learningSourceBadgeLabel(_shortId(source.sourceId), source.sourceVersion)}'
        '${anchor.isEmpty ? '' : ' · $anchor'}';
    final badge = Tooltip(
      message: label,
      child: Container(
        key: const Key('learning_source_badge'),
        padding: const EdgeInsets.symmetric(horizontal: DS.sm, vertical: DS.xs),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: theme.dividerColor),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _kindIcon(source.sourceKind),
              size: 12,
              color: DS.textSecondary,
            ),
            const SizedBox(width: DS.xs),
            Flexible(
              child: Text(
                compact ? l10n.learningSourceCompactLabel(source.sourceVersion) : label,
                style: theme.textTheme.labelSmall?.copyWith(color: DS.textSecondary),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
    if (onOpenFragment == null) {
      return badge;
    }
    return Semantics(
      button: true,
      label: l10n.learningSourceTapSemantics(label),
      child: InkWell(
        key: const Key('learning_source_badge_tap'),
        borderRadius: BorderRadius.circular(6),
        onTap: onOpenFragment,
        child: badge,
      ),
    );
  }

  String _shortId(String id) {
    if (id.length <= 8) {
      return id;
    }
    return id.substring(0, 8);
  }

  IconData _kindIcon(String kind) {
    switch (kind) {
      case 'error_record':
        return Icons.assignment_late_outlined;
      case 'manual_text':
        return Icons.edit_note_rounded;
      default:
        return Icons.description_outlined;
    }
  }
}
