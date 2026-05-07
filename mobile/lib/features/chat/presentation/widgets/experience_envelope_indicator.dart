import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/providers/experience_envelope_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class _AdjustmentLabel {
  const _AdjustmentLabel(this.label, this.icon);
  final String label;
  final IconData icon;
}

Map<String, _AdjustmentLabel> _buildAdjustmentMeta(AppLocalizations l10n) => {
  'tone': _AdjustmentLabel(l10n.envelopeDimTone, Icons.record_voice_over_outlined),
  'verbosity': _AdjustmentLabel(l10n.envelopeDimVerbosity, Icons.short_text_outlined),
  'challenge_level': _AdjustmentLabel(l10n.envelopeDimChallenge, Icons.trending_up_outlined),
  'explanation_depth': _AdjustmentLabel(l10n.envelopeDimDepth, Icons.layers_outlined),
  'pace': _AdjustmentLabel(l10n.envelopeDimPace, Icons.speed_outlined),
  'focus': _AdjustmentLabel(l10n.envelopeDimFocus, Icons.center_focus_strong_outlined),
  'support_level': _AdjustmentLabel(l10n.envelopeDimSupport, Icons.support_outlined),
  'complexity': _AdjustmentLabel(l10n.envelopeDimComplexity, Icons.account_tree_outlined),
};

/// Indicator showing real-time cognitive adjustments Aurora is making.
///
/// Watches [experienceEnvelopeProvider] and displays user-visible
/// [CognitiveAdjustment] entries as compact chips.
class ExperienceEnvelopeIndicator extends ConsumerWidget {
  const ExperienceEnvelopeIndicator({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final envelope = ref.watch(experienceEnvelopeProvider);
    if (envelope.isEmpty) return const SizedBox.shrink();

    final adjustments = envelope.structuredCognitiveAdjustments;
    final engagement = _extractEngagement(envelope.userState);
    final l10n = AppLocalizations.of(context)!;

    return Semantics(
      container: true,
      label: l10n.envelopeIndicatorLabel,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: DS.spacing12, vertical: DS.spacing4),
        padding: const EdgeInsets.all(DS.spacing10),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius8,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Icon(
                  Icons.psychology_outlined,
                  size: DS.iconSizeXs,
                  color: DS.brandPrimary,
                ),
                const SizedBox(width: DS.spacing6),
                Text(
                  l10n.envelopeAdapting,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        fontWeight: DS.fontWeightSemibold,
                        color: DS.brandPrimary,
                      ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing6),
            if (adjustments.isNotEmpty)
              Wrap(
                spacing: DS.spacing6,
                runSpacing: DS.spacing6,
                children: adjustments.map((adj) {
                  final dim = adj['dimension']?.toString() ?? '';
                  final value = adj['value'];
                  final reason = adj['reason']?.toString() ?? '';
                  final meta = _buildAdjustmentMeta(l10n)[dim] ??
                      _AdjustmentLabel('', Icons.tune_outlined);
                  final label = meta.label.isNotEmpty ? meta.label : dim;

                  return Semantics(
                    label: '$label: ${_valueText(value, l10n)} ($reason)',
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing8,
                        vertical: DS.spacing4,
                      ),
                      decoration: BoxDecoration(
                        color: DS.brandPrimary.withValues(alpha: 0.08),
                        borderRadius: DS.borderRadius6,
                        border: Border.all(
                          color: DS.brandPrimary.withValues(alpha: 0.15),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(meta.icon, size: 12, color: DS.brandPrimary),
                          const SizedBox(width: DS.spacing4),
                          Text(
                            '$label: ${_valueText(value, l10n)}',
                            style: Theme.of(context)
                                .textTheme
                                .labelSmall
                                ?.copyWith(
                                  color: DS.brandPrimary,
                                  fontWeight: FontWeight.w500,
                                  fontSize: DS.fontSizeXs,
                                ),
                          ),
                        ],
                      ),
                    ),
                  );
                }).toList(),
              ),
            if (envelope.hasPresentationMeta || envelope.hasSocialContext) ...[
              if (adjustments.isNotEmpty || engagement != null)
                const SizedBox(height: DS.spacing6),
              _PresentationMetaRow(
                style: envelope.presentationStyle,
                tone: envelope.toneVariant,
                socialContext: envelope.hasSocialContext
                    ? envelope.socialContextPresentation
                    : null,
              ),
            ],
            if (engagement != null) ...[
              if (adjustments.isNotEmpty ||
                  envelope.hasPresentationMeta ||
                  envelope.hasSocialContext)
                const SizedBox(height: DS.spacing6),
              _EngagementBar(engagement: engagement),
            ],
          ],
        ),
      ),
    );
  }
}

String _valueText(dynamic value, AppLocalizations l10n) {
  if (value == null) return l10n.envelopeValueNone;
  if (value is bool) {
    return value ? l10n.envelopeValueYes : l10n.envelopeValueNo;
  }
  if (value is double) return value.toStringAsFixed(1);
  return value.toString();
}

_EngagementData? _extractEngagement(Map<String, dynamic> userState) {
  final engagement = userState['engagementState'];
  if (engagement is! Map) return null;
  final streak = engagement['streak'];
  final sessionCount = engagement['sessionCount7d'];
  if (streak == null && sessionCount == null) return null;
  return _EngagementData(
    streak: streak is int ? streak : 0,
    sessions7d: sessionCount is int ? sessionCount : 0,
  );
}

class _EngagementData {
  const _EngagementData({required this.streak, required this.sessions7d});
  final int streak;
  final int sessions7d;
}

class _EngagementBar extends StatelessWidget {
  const _EngagementBar({required this.engagement});
  final _EngagementData engagement;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.local_fire_department_outlined, size: 12, color: DS.brandPrimary),
        const SizedBox(width: DS.spacing4),
        Text(
          l10n.envelopeEngagementSummary(engagement.streak, engagement.sessions7d),
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: DS.brandPrimary.withValues(alpha: 0.7),
                fontSize: DS.fontSizeXs,
              ),
        ),
      ],
    );
  }
}

class _PresentationMetaRow extends StatelessWidget {
  const _PresentationMetaRow({
    this.style,
    this.tone,
    this.socialContext,
  });
  final String? style;
  final String? tone;
  final Map<String, dynamic>? socialContext;

  @override
  Widget build(BuildContext context) {
    final parts = <String>[];
    if (style != null && style!.isNotEmpty) parts.add(style!);
    if (tone != null && tone!.isNotEmpty) parts.add(tone!);
    if (socialContext != null && socialContext!.isNotEmpty) {
      final partner = socialContext!['partner_label']?.toString();
      if (partner != null && partner.isNotEmpty) parts.add(partner);
    }
    if (parts.isEmpty) return const SizedBox.shrink();

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.auto_awesome_outlined,
            size: 12, color: DS.brandPrimary.withValues(alpha: 0.7)),
        const SizedBox(width: DS.spacing4),
        Flexible(
          child: Text(
            parts.join(' · '),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: DS.brandPrimary.withValues(alpha: 0.6),
                  fontSize: DS.fontSizeXs,
                ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}
