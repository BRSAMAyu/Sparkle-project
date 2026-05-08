import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/goal/data/models/goal_intent_models.dart';

/// Phase-1 Entry Wire — renders the server's intent analysis as a card the
/// user can confirm, refine, or reject. Always includes a "都不对，我解释一下"
/// escape so the user is never trapped in a wrong judgement.
class IntentConfirmationCard extends StatelessWidget {
  const IntentConfirmationCard({
    required this.analysis,
    required this.onCorrectionSelected,
    required this.onSuggestedActionTapped,
    super.key,
  });

  final GoalIntentAnalysis analysis;
  final ValueChanged<GoalIntentCorrectionOption> onCorrectionSelected;
  final ValueChanged<GoalIntentSuggestedAction> onSuggestedActionTapped;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      key: const ValueKey('intent-confirmation-card'),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: DS.surfaceHigh,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _ModeChip(mode: analysis.mode, confidence: analysis.confidence),
          const SizedBox(height: 10),
          Text(
            analysis.headline,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                  height: 1.4,
                ),
          ),
          if (_metaLine(l10n.intentDaysLeft(analysis.deadlineDays ?? 0)).isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              _metaLine(l10n.intentDaysLeft(analysis.deadlineDays ?? 0)),
              style: TextStyle(color: DS.textSecondary, fontSize: 12),
            ),
          ],
          if (analysis.suggestedActions.isNotEmpty) ...[
            const SizedBox(height: 14),
            Text(
              l10n.intentSuggestedActionLabel,
              style: TextStyle(
                color: DS.textPrimary,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            for (final action in analysis.suggestedActions) ...[
              _SuggestedActionRow(
                action: action,
                onTap: () => onSuggestedActionTapped(action),
              ),
              const SizedBox(height: 6),
            ],
          ],
          if (analysis.correctionOptions.isNotEmpty) ...[
            const SizedBox(height: 12),
            Divider(color: DS.border.withValues(alpha: 0.4)),
            const SizedBox(height: 8),
            Text(
              l10n.intentCorrectionLabel,
              style: TextStyle(color: DS.textSecondary, fontSize: 12),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final option in analysis.correctionOptions)
                  ActionChip(
                    label: Text(option.label),
                    onPressed: () => onCorrectionSelected(option),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  String _metaLine(String daysLeftText) {
    final parts = <String>[];
    if (analysis.deadlineDays != null) {
      parts.add(daysLeftText);
    }
    if ((analysis.detectedSubject ?? '').isNotEmpty) {
      parts.add(analysis.detectedSubject!);
    }
    if ((analysis.baseline ?? '').isNotEmpty &&
        analysis.baseline != 'unknown') {
      parts.add(analysis.baseline!);
    }
    return parts.join(' · ');
  }
}

class _ModeChip extends StatelessWidget {
  const _ModeChip({required this.mode, required this.confidence});

  final String mode;
  final double confidence;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final (label, color) = _label(l10n);
    return Wrap(
      spacing: 6,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(999),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.bolt_rounded, size: 12, color: color),
              const SizedBox(width: 4),
              Text(
                label,
                style: TextStyle(
                  color: color,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        if (confidence > 0)
          Text(
            l10n.intentConfidenceLabel((confidence * 100).round()),
            style: TextStyle(color: DS.textSecondary, fontSize: 11),
          ),
      ],
    );
  }

  (String, Color) _label(dynamic l10n) {
    if (mode.startsWith('exam_rescue')) {
      return (l10n.intentExamRescue, DS.error);
    }
    if (mode.startsWith('exam_build')) {
      return (l10n.intentExamBuild, DS.warning);
    }
    if (mode.startsWith('job_search')) {
      return (l10n.intentJobSearch, DS.info);
    }
    if (mode.startsWith('project')) {
      return (l10n.intentProject, DS.brandPrimary);
    }
    if (mode.startsWith('habit')) {
      return (l10n.intentHabit, DS.success);
    }
    return (l10n.intentKeepGoing, DS.textSecondary);
  }
}

class _SuggestedActionRow extends StatelessWidget {
  const _SuggestedActionRow({required this.action, required this.onTap});

  final GoalIntentSuggestedAction action;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.18)),
        ),
        child: Row(
          children: [
            Icon(Icons.play_arrow_rounded, color: DS.brandPrimary, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                action.label,
                style: TextStyle(color: DS.textPrimary, fontSize: 13),
              ),
            ),
            if (action.estimatedMinutes > 0)
              Text(
                '${action.estimatedMinutes}m',
                style: TextStyle(color: DS.textSecondary, fontSize: 11),
              ),
          ],
        ),
      ),
    );
  }
}
