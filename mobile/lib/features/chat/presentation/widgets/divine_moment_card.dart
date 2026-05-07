import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Divine Moment card types — one per MAGIC-002 through MAGIC-006.
/// MAGIC-001 (streak milestone) uses the dedicated [GrowthCard] widget.
enum DivineMomentType {
  /// MAGIC-002: User correction acknowledged and task plan adjusted.
  correctionImpact,

  /// MAGIC-003: Aurora intentionally skips materials the user doesn't need.
  materialNonUse,

  /// MAGIC-004: Proactive absence detection and recovery.
  absenceNotice,

  /// MAGIC-005: Low-yield activity blocked, high-yield alternative offered.
  lowYieldBlock,

  /// MAGIC-006: Community cohort signals suggest a strategy adaptation.
  communityStrategy,
}

/// Data for a divine moment card emitted by the backend spine.
class DivineMomentData {
  const DivineMomentData({
    required this.type,
    this.title = '',
    this.narrative = '',
    this.actions = const [],
    this.metadata = const {},
  });

  final DivineMomentType type;
  final String title;
  final String narrative;
  final List<String> actions;
  final Map<String, dynamic> metadata;

  factory DivineMomentData.fromJson(Map<String, dynamic> json) {
    final typeStr = json['divine_moment_type'] as String? ?? '';
    return DivineMomentData(
      type: _parseType(typeStr),
      title: json['title'] as String? ?? '',
      narrative: json['narrative'] as String? ?? '',
      actions: (json['actions'] as List?)?.map((e) => e.toString()).toList() ?? [],
      metadata: Map<String, dynamic>.from(json['metadata'] as Map? ?? {}),
    );
  }

  static DivineMomentType _parseType(String type) {
    return switch (type) {
      'correction_impact' => DivineMomentType.correctionImpact,
      'material_non_use' => DivineMomentType.materialNonUse,
      'absence_notice' => DivineMomentType.absenceNotice,
      'low_yield_block' => DivineMomentType.lowYieldBlock,
      'community_strategy' => DivineMomentType.communityStrategy,
      _ => DivineMomentType.correctionImpact,
    };
  }
}

/// Unified Divine Moment card for MAGIC-002 through MAGIC-006.
///
/// Each divine moment type gets its own icon, accent color, and
/// contextual label, but they share the same card skeleton so the
/// visual language stays consistent across all "Aurora noticed
/// something" moments.
class DivineMomentCard extends StatefulWidget {
  const DivineMomentCard({
    required this.data,
    required this.onAction,
    super.key,
  });

  final DivineMomentData data;
  final ValueChanged<String> onAction;

  @override
  State<DivineMomentCard> createState() => _DivineMomentCardState();
}

class _DivineMomentCardState extends State<DivineMomentCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _fade;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 350),
    );
    _fade = CurvedAnimation(parent: _ctrl, curve: Curves.easeOut);
    _ctrl.forward();
    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final type = widget.data.type;
    final (icon, color) = _visuals(type);
    final title = widget.data.title.isNotEmpty ? widget.data.title : _defaultTitle(l10n, type);
    final narrative = widget.data.narrative.isNotEmpty
        ? widget.data.narrative
        : _defaultNarrative(l10n, type, widget.data.metadata);
    final actions = widget.data.actions.isNotEmpty
        ? widget.data.actions
        : _defaultActions(l10n, type);

    return Semantics(
      container: true,
      label: title,
      child: FadeTransition(
      opacity: _fade,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: DS.surfaceHigh,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: color.withValues(alpha: 0.35)),
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: 0.06),
              blurRadius: 10,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 8, 6),
              child: Row(
                children: [
                  Icon(icon, size: 20, color: color),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      title,
                      style: DS.titleMedium.copyWith(color: DS.textPrimary),
                    ),
                  ),
                  _TypeBadge(type: type, color: color),
                ],
              ),
            ),
            if (narrative.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
                child: Text(
                  narrative,
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.4,
                  ),
                ),
              ),
            _ExtraSection(type: type, metadata: widget.data.metadata, color: color),
            if (actions.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
                child: Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: actions.map((action) {
                    final isDismiss = action == actions.last && actions.length > 1;
                    return ActionChip(
                      label: Text(action),
                      labelStyle: DS.labelSmall.copyWith(
                        color: isDismiss ? DS.textSecondary : color,
                      ),
                      backgroundColor: isDismiss
                          ? DS.surfaceSecondary
                          : color.withValues(alpha: 0.1),
                      side: BorderSide(
                        color: isDismiss
                            ? DS.borderSubtle
                            : color.withValues(alpha: 0.3),
                      ),
                      onPressed: () => widget.onAction(action),
                    );
                  }).toList(),
                ),
              ),
          ],
        ),
      ),
      ),
    );
  }

  (IconData, Color) _visuals(DivineMomentType type) => switch (type) {
        DivineMomentType.correctionImpact => (Icons.psychology_alt_outlined, DS.brandPrimary),
        DivineMomentType.materialNonUse => (Icons.menu_book_outlined, DS.warning),
        DivineMomentType.absenceNotice => (Icons.waving_hand_outlined, DS.info),
        DivineMomentType.lowYieldBlock => (Icons.block, DS.error),
        DivineMomentType.communityStrategy => (Icons.groups_outlined, DS.brandPrimary),
      };

  String _defaultTitle(AppLocalizations l10n, DivineMomentType type) => switch (type) {
        DivineMomentType.correctionImpact => l10n.divineCorrectionImpactTitle,
        DivineMomentType.materialNonUse => l10n.divineMaterialNonUseTitle,
        DivineMomentType.absenceNotice => l10n.divineAbsenceTitle,
        DivineMomentType.lowYieldBlock => l10n.divineLowYieldTitle,
        DivineMomentType.communityStrategy => l10n.divineCommunityTitle,
      };

  String _defaultNarrative(AppLocalizations l10n, DivineMomentType type, Map<String, dynamic> meta) {
    return switch (type) {
      DivineMomentType.correctionImpact => l10n.divineCorrectionImpactNarrative,
      DivineMomentType.materialNonUse => l10n.divineMaterialSkipped(
          meta['material'] as String? ?? '',
        ),
      DivineMomentType.absenceNotice => switch (meta['absence_level'] as String? ?? '') {
          'short' || 'prolonged' => l10n.divineAbsenceShort,
          'extended' => l10n.divineAbsenceLong,
          _ => l10n.divineAbsenceIdle,
        },
      DivineMomentType.lowYieldBlock => l10n.divineLowYieldNarrative(
          meta['activity'] as String? ?? '',
          meta['alternative'] as String? ?? '',
        ),
      DivineMomentType.communityStrategy => l10n.divineCommunityNarrative(
          meta['cohort_size'] as int? ?? 0,
          meta['knowledge_node'] as String? ?? '',
        ),
    };
  }

  List<String> _defaultActions(AppLocalizations l10n, DivineMomentType type) => switch (type) {
        DivineMomentType.correctionImpact => [
            l10n.divineCorrectionViewAdjusted,
            l10n.divineMomentContinue,
          ],
        DivineMomentType.materialNonUse => [l10n.divineMaterialAcknowledge],
        DivineMomentType.absenceNotice => [l10n.divineAbsenceResume, l10n.divineAbsenceRestart],
        DivineMomentType.lowYieldBlock => [
            l10n.divineLowYieldSwitch(
              widget.data.metadata['alternative'] as String? ?? '',
            ),
            l10n.divineLowYieldIgnore,
          ],
        DivineMomentType.communityStrategy => [
            l10n.divineCommunityTry(
              widget.data.metadata['knowledge_node'] as String? ?? '',
            ),
            l10n.divineCommunityNotNow,
          ],
      };
}

class _TypeBadge extends StatelessWidget {
  const _TypeBadge({required this.type, required this.color});

  final DivineMomentType type;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final label = switch (type) {
      DivineMomentType.correctionImpact => 'MAGIC-002',
      DivineMomentType.materialNonUse => 'MAGIC-003',
      DivineMomentType.absenceNotice => 'MAGIC-004',
      DivineMomentType.lowYieldBlock => 'MAGIC-005',
      DivineMomentType.communityStrategy => 'MAGIC-006',
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}

class _ExtraSection extends StatelessWidget {
  const _ExtraSection({
    required this.type,
    required this.metadata,
    required this.color,
  });

  final DivineMomentType type;
  final Map<String, dynamic> metadata;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final extra = _build(type, metadata, context);
    if (extra == null) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(8),
      ),
      child: extra,
    );
  }

  Widget? _build(DivineMomentType type, Map<String, dynamic> meta, BuildContext context) {
    final l10n = context.l10n;
    return switch (type) {
      DivineMomentType.lowYieldBlock => _boostRow(
          l10n.divineLowYieldBoost(meta['yield_improvement_pct'] as int? ?? 0),
          color,
        ),
      DivineMomentType.absenceNotice when meta['elapsed_minutes'] != null => _minutesRow(
          meta['elapsed_minutes'] as num? ?? 0,
          color,
          context,
        ),
      _ => null,
    };
  }

  Widget _boostRow(String text, Color color) => Row(
        children: [
          Icon(Icons.trending_up, size: 14, color: color),
          const SizedBox(width: 6),
          Expanded(
            child: Text(text, style: DS.labelSmall.copyWith(color: DS.textSecondary)),
          ),
        ],
      );

  Widget _minutesRow(num mins, Color color, BuildContext context) => Row(
        children: [
          Icon(Icons.schedule, size: 14, color: color),
          const SizedBox(width: 6),
          Text(
            context.l10n.divineAbsenceMinutes(mins.round()),
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
          ),
        ],
      );
}
