import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
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

  static String _t(String zh, String en) =>
      I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
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
          if (_metaLine().isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              _metaLine(),
              style: TextStyle(color: DS.textSecondary, fontSize: 12),
            ),
          ],
          if (analysis.suggestedActions.isNotEmpty) ...[
            const SizedBox(height: 14),
            Text(
              _t('我建议先这样做', 'A low-cost first step'),
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
              _t('或者我猜错了——', 'Or I got it wrong —'),
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

  String _metaLine() {
    final parts = <String>[];
    if (analysis.deadlineDays != null) {
      parts.add(_t('剩 ${analysis.deadlineDays} 天',
          '${analysis.deadlineDays} days left'));
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

  static String _t(String zh, String en) =>
      I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    final (label, color) = _label(mode);
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
            _t('置信度 ${(confidence * 100).round()}%',
                '${(confidence * 100).round()}% confidence'),
            style: TextStyle(color: DS.textSecondary, fontSize: 11),
          ),
      ],
    );
  }

  (String, Color) _label(String mode) {
    if (mode.startsWith('exam_rescue')) {
      return (_t('考试抢救', 'Exam rescue'), DS.error);
    }
    if (mode.startsWith('exam_build')) {
      return (_t('考试备战', 'Exam prep'), DS.warning);
    }
    if (mode.startsWith('job_search')) {
      return (_t('求职冲刺', 'Job sprint'), DS.info);
    }
    if (mode.startsWith('project')) {
      return (_t('项目交付', 'Project'), DS.brandPrimary);
    }
    if (mode.startsWith('habit')) {
      return (_t('习惯养成', 'Habit'), DS.success);
    }
    return (_t('继续了解', 'Keep going'), DS.textSecondary);
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
