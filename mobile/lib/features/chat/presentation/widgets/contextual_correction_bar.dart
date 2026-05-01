import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';

/// Contextual correction buttons shown after AI responses.
///
/// When [predictedReplyGroups] are available from the Aurora backend, shows
/// the top group's primary options (sorted by confidence) plus the freeform
/// fallback. Otherwise falls back to the static hardcoded chips.
class ContextualCorrectionBar extends StatefulWidget {
  const ContextualCorrectionBar({
    required this.onRecalibrate,
    this.onSendCorrection,
    this.onFreeformCorrectionRequested,
    this.onNotRightDirection,
    this.onMakeShorter,
    this.onGivePractice,
    this.predictedReplyGroups,
    this.visible = true,
    super.key,
  });

  final VoidCallback? onNotRightDirection;
  final VoidCallback? onMakeShorter;
  final VoidCallback? onGivePractice;
  final VoidCallback onRecalibrate;

  /// Called with the selected predicted reply option and its group id.
  /// The consumer is expected to record telemetry and send the correction
  /// with structured Aurora context rather than plain text.
  final FutureOr<void> Function(
      AuroraPredictedReplyOption option, String groupId)? onSendCorrection;
  final FutureOr<void> Function()? onFreeformCorrectionRequested;

  /// Predicted reply groups from Aurora backend. If non-empty, used instead
  /// of the static fallback chips.
  final List<AuroraPredictedReplyGroup>? predictedReplyGroups;

  final bool visible;

  @override
  State<ContextualCorrectionBar> createState() =>
      _ContextualCorrectionBarState();
}

class _ContextualCorrectionBarState extends State<ContextualCorrectionBar> {
  Timer? _ackTimer;
  String? _acknowledgedLabel;

  @override
  void dispose() {
    _ackTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.visible) return const SizedBox.shrink();

    final groups = widget.predictedReplyGroups;
    final topGroup =
        (groups != null && groups.isNotEmpty) ? groups.first : null;

    if (topGroup != null && topGroup.options.isNotEmpty) {
      return _buildPredictedOptions(context, topGroup);
    }
    return _buildFallback(context);
  }

  Widget _buildPredictedOptions(
    BuildContext context,
    AuroraPredictedReplyGroup group,
  ) {
    final primaryOptions = group.primaryOptions.take(3).toList();
    final freeform = group.freeformOption;
    final groupId = group.groupId;

    return Padding(
      padding: const EdgeInsets.only(
        left: DS.spacing40,
        top: DS.spacing4,
        bottom: DS.spacing8,
      ),
      child: Wrap(
        spacing: DS.spacing6,
        runSpacing: DS.spacing4,
        children: [
          ...primaryOptions.map(
            (opt) => _CorrectionChip(
              presentation: auroraCorrectionPresentationFor(context, opt),
              onTap: () => _handleOptionTap(opt, groupId),
            ),
          ),
          if (freeform != null)
            _CorrectionChip(
              presentation: auroraCorrectionPresentationFor(context, freeform),
              onTap: () => _handleOptionTap(freeform, groupId),
              isAccent: true,
            )
          else
            _CorrectionChip(
              presentation: AuroraCorrectionOptionPresentation(
                label: context.l10n.auroraCorrectRecalibrate,
                subtitle: context.l10n.auroraCorrectRecalibrateSubtitle,
                icon: Icons.tune_rounded,
              ),
              onTap: widget.onRecalibrate,
              isAccent: true,
            ),
          if (_acknowledgedLabel != null)
            _CorrectionAcknowledgement(label: _acknowledgedLabel!),
        ],
      ),
    );
  }

  void _showAcknowledgement(String label) {
    _ackTimer?.cancel();
    if (!mounted) return;
    setState(() => _acknowledgedLabel = label);
    _ackTimer = Timer(const Duration(seconds: 4), () {
      if (mounted) {
        setState(() => _acknowledgedLabel = null);
      }
    });
  }

  void _handleOptionTap(AuroraPredictedReplyOption option, String groupId) {
    final presentation = auroraCorrectionPresentationFor(context, option);
    if (option.isFreeform) {
      final handler = widget.onFreeformCorrectionRequested;
      if (handler != null) {
        unawaited(Future<void>.sync(handler));
      } else {
        widget.onRecalibrate();
      }
      return;
    }
    _showAcknowledgement(presentation.label);
    final handler = widget.onSendCorrection;
    if (handler != null) {
      unawaited(Future<void>.sync(() => handler(option, groupId)));
    }
  }

  Widget _buildFallback(BuildContext context) {
    final l10n = context.l10n;

    return Padding(
      padding: const EdgeInsets.only(
        left: DS.spacing40,
        top: DS.spacing4,
        bottom: DS.spacing8,
      ),
      child: Wrap(
        spacing: DS.spacing6,
        runSpacing: DS.spacing4,
        children: [
          if (widget.onNotRightDirection != null)
            _CorrectionChip(
              presentation: AuroraCorrectionOptionPresentation(
                label: l10n.auroraCorrectNotRight,
                subtitle: l10n.auroraCorrectNotRightSubtitle,
                icon: Icons.report_gmailerrorred_rounded,
              ),
              onTap: () {
                _showAcknowledgement(l10n.auroraCorrectNotRight);
                widget.onNotRightDirection!();
              },
            ),
          if (widget.onMakeShorter != null)
            _CorrectionChip(
              presentation: AuroraCorrectionOptionPresentation(
                label: l10n.auroraCorrectShorter,
                subtitle: l10n.auroraCorrectShorterSubtitle,
                icon: Icons.short_text_rounded,
              ),
              onTap: () {
                _showAcknowledgement(l10n.auroraCorrectShorter);
                widget.onMakeShorter!();
              },
            ),
          if (widget.onGivePractice != null)
            _CorrectionChip(
              presentation: AuroraCorrectionOptionPresentation(
                label: l10n.auroraCorrectDirect,
                subtitle: l10n.auroraCorrectDirectSubtitle,
                icon: Icons.fitness_center_rounded,
              ),
              onTap: () {
                _showAcknowledgement(l10n.auroraCorrectDirect);
                widget.onGivePractice!();
              },
            ),
          _CorrectionChip(
            presentation: AuroraCorrectionOptionPresentation(
              label: l10n.auroraCorrectRecalibrate,
              subtitle: l10n.auroraCorrectRecalibrateSubtitle,
              icon: Icons.tune_rounded,
            ),
            onTap: widget.onRecalibrate,
            isAccent: true,
          ),
          if (_acknowledgedLabel != null)
            _CorrectionAcknowledgement(label: _acknowledgedLabel!),
        ],
      ),
    );
  }
}

/// Source badge shown on AI messages that used personal context.
///
/// Example: "基于：最近 3 次 TCP 错因" → tappable to see evidence.
class SourceBadge extends StatelessWidget {
  const SourceBadge({
    required this.sources,
    this.onTapSource,
    super.key,
  });

  final List<String> sources;
  final ValueChanged<String>? onTapSource;

  @override
  Widget build(BuildContext context) {
    if (sources.isEmpty) return const SizedBox.shrink();

    final l10n = context.l10n;

    return Padding(
      padding: const EdgeInsets.only(
        left: DS.spacing40,
        top: DS.spacing2,
        bottom: DS.spacing2,
      ),
      child: Wrap(
        spacing: DS.spacing6,
        runSpacing: DS.spacing4,
        children: sources
            .map(
              (source) => GestureDetector(
                onTap: () => onTapSource?.call(source),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing8,
                    vertical: DS.spacing4,
                  ),
                  decoration: BoxDecoration(
                    color: DS.surfaceSecondary.withValues(alpha: 0.6),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.info_outline_rounded,
                        size: 12,
                        color: DS.textSecondary.withValues(alpha: 0.8),
                      ),
                      const SizedBox(width: DS.spacing4),
                      Text(
                        l10n.auroraSourceBadge(source),
                        style: TextStyle(
                          color: DS.textSecondary,
                          fontSize: 11,
                          height: 1.2,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            )
            .toList(),
      ),
    );
  }
}

/// Aurora judgment tag — shown when AI makes a clear judgment call.
///
/// Example: "Aurora 判断：现在不建议推进新章节"
class AuroraJudgmentTag extends StatelessWidget {
  const AuroraJudgmentTag({
    required this.judgment,
    this.reason,
    this.onTap,
    super.key,
  });

  final String judgment;
  final String? reason;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(
          left: DS.spacing40,
          top: DS.spacing4,
          bottom: DS.spacing4,
        ),
        padding: const EdgeInsets.all(DS.spacing10),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              DS.brandPrimary.withValues(alpha: 0.06),
              DS.brandPrimary.withValues(alpha: 0.02),
            ],
          ),
          borderRadius: BorderRadius.circular(DS.radius12),
          border: Border.all(
            color: DS.brandPrimary.withValues(alpha: 0.15),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.auto_awesome_rounded,
                  size: 14,
                  color: DS.brandPrimary,
                ),
                const SizedBox(width: DS.spacing6),
                Text(
                  l10n.auroraJudgmentTag,
                  style: TextStyle(
                    color: DS.brandPrimary,
                    fontSize: DS.fontSizeXs,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              judgment,
              style: TextStyle(
                color: DS.textPrimary,
                fontSize: DS.fontSizeSm,
                height: 1.4,
              ),
            ),
            if (reason != null && reason!.trim().isNotEmpty) ...[
              const SizedBox(height: DS.spacing4),
              Text(
                reason!,
                style: TextStyle(
                  color: DS.textSecondary,
                  fontSize: DS.fontSizeXs,
                  height: 1.3,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ── Correction presentation ──────────────────────────────────────

class AuroraCorrectionOptionPresentation {
  const AuroraCorrectionOptionPresentation({
    required this.label,
    required this.subtitle,
    required this.icon,
  });

  final String label;
  final String subtitle;
  final IconData icon;
}

AuroraCorrectionOptionPresentation auroraCorrectionPresentationFor(
  BuildContext context,
  AuroraPredictedReplyOption option,
) {
  final l10n = context.l10n;
  final semantic = option.semanticValue.trim();
  final label = option.label.trim();

  if (option.isFreeform || semantic == 'freeform_correction') {
    return AuroraCorrectionOptionPresentation(
      label: l10n.auroraCorrectionFreeformLabel,
      subtitle: l10n.auroraCorrectionFreeformSubtitle,
      icon: Icons.edit_note_rounded,
    );
  }

  switch (semantic) {
    case 'risk_false_positive':
      return AuroraCorrectionOptionPresentation(
        label: l10n.auroraCorrectionRiskFalsePositive,
        subtitle: l10n.auroraCorrectionRiskSubtitle,
        icon: Icons.self_improvement_rounded,
      );
    case 'risk_wrong_diagnosis':
    case 'judgment_incorrect':
    case 'judgment_denied':
      return AuroraCorrectionOptionPresentation(
        label: l10n.auroraCorrectionJudgmentOff,
        subtitle: l10n.auroraCorrectionJudgmentSubtitle,
        icon: Icons.psychology_alt_rounded,
      );
    case 'risk_overstated':
      return AuroraCorrectionOptionPresentation(
        label: l10n.auroraCorrectionRiskOverstated,
        subtitle: l10n.auroraCorrectionRiskSubtitle,
        icon: Icons.speed_rounded,
      );
    case 'risk_temporary':
    case 'temporary_time_conflict':
      return AuroraCorrectionOptionPresentation(
        label: l10n.auroraCorrectionTemporaryBusy,
        subtitle: l10n.auroraCorrectionTemporarySubtitle,
        icon: Icons.event_busy_rounded,
      );
    case 'strategy_adjust_needed':
    case 'strategy_too_aggressive':
      return AuroraCorrectionOptionPresentation(
        label: l10n.auroraCorrectionStrategyAdjust,
        subtitle: l10n.auroraCorrectionStrategySubtitle,
        icon: Icons.route_rounded,
      );
    case 'strategy_too_conservative':
      return AuroraCorrectionOptionPresentation(
        label: l10n.auroraCorrectionStrategyFaster,
        subtitle: l10n.auroraCorrectionStrategySubtitle,
        icon: Icons.trending_up_rounded,
      );
    case 'knowledge_blocker':
      return AuroraCorrectionOptionPresentation(
        label: l10n.auroraCorrectionKnowledgeBlocker,
        subtitle: l10n.auroraCorrectionKnowledgeSubtitle,
        icon: Icons.school_rounded,
      );
    case 'carelessness':
      return AuroraCorrectionOptionPresentation(
        label: l10n.auroraCorrectionCareless,
        subtitle: l10n.auroraCorrectionCarelessSubtitle,
        icon: Icons.fact_check_rounded,
      );
    case 'not_right_direction':
      return AuroraCorrectionOptionPresentation(
        label: l10n.auroraCorrectNotRight,
        subtitle: l10n.auroraCorrectNotRightSubtitle,
        icon: Icons.report_gmailerrorred_rounded,
      );
  }

  final looksInternal = label.isEmpty ||
      label == semantic ||
      RegExp(r'^[a-z][a-z0-9_]*$').hasMatch(label);
  if (!looksInternal) {
    return AuroraCorrectionOptionPresentation(
      label: label,
      subtitle: _defaultCorrectionSubtitle(context, option),
      icon: _defaultCorrectionIcon(option),
    );
  }

  return AuroraCorrectionOptionPresentation(
    label: option.isDisconfirming
        ? l10n.auroraCorrectionGenericDisconfirm
        : l10n.auroraCorrectionGenericConfirm,
    subtitle: _defaultCorrectionSubtitle(context, option),
    icon: _defaultCorrectionIcon(option),
  );
}

String _defaultCorrectionSubtitle(
  BuildContext context,
  AuroraPredictedReplyOption option,
) {
  final l10n = context.l10n;
  if (option.isDisconfirming) {
    return l10n.auroraCorrectionJudgmentSubtitle;
  }
  switch (option.replyType) {
    case 'strategy_choice':
      return l10n.auroraCorrectionStrategySubtitle;
    case 'fact_confirm':
      return l10n.auroraCorrectionFactSubtitle;
    case 'relational_signal':
      return l10n.auroraCorrectionToneSubtitle;
    case 'assumption_check':
    default:
      return l10n.auroraCorrectionJudgmentSubtitle;
  }
}

IconData _defaultCorrectionIcon(AuroraPredictedReplyOption option) {
  if (option.isDisconfirming) {
    return Icons.report_gmailerrorred_rounded;
  }
  switch (option.replyType) {
    case 'strategy_choice':
      return Icons.route_rounded;
    case 'fact_confirm':
      return Icons.check_circle_outline_rounded;
    case 'relational_signal':
      return Icons.tune_rounded;
    case 'assumption_check':
    default:
      return Icons.psychology_alt_rounded;
  }
}

// ── Internal ────────────────────────────────────────────────────

class _CorrectionChip extends StatelessWidget {
  const _CorrectionChip({
    required this.presentation,
    required this.onTap,
    this.isAccent = false,
  });

  final AuroraCorrectionOptionPresentation presentation;
  final VoidCallback onTap;
  final bool isAccent;

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(DS.radius8);
    final color = isAccent ? DS.brandPrimary : DS.textSecondary;

    return Semantics(
      button: true,
      label: presentation.label,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
        child: Material(
          color: Colors.transparent,
          borderRadius: radius,
          child: InkWell(
            onTap: onTap,
            borderRadius: radius,
            child: Container(
              alignment: Alignment.center,
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: 7,
              ),
              decoration: BoxDecoration(
                color: isAccent
                    ? DS.brandPrimary.withValues(alpha: 0.08)
                    : DS.surfaceSecondary.withValues(alpha: 0.5),
                borderRadius: radius,
                border: isAccent
                    ? Border.all(
                        color: DS.brandPrimary.withValues(alpha: 0.2),
                      )
                    : Border.all(color: Colors.transparent),
              ),
              child: ExcludeSemantics(
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(presentation.icon, size: 14, color: color),
                    const SizedBox(width: DS.spacing6),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 190),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            presentation.label,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: color,
                              fontSize: 11,
                              fontWeight: isAccent
                                  ? DS.fontWeightMedium
                                  : DS.fontWeightRegular,
                            ),
                          ),
                          Text(
                            presentation.subtitle,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: color.withValues(alpha: 0.72),
                              fontSize: 10,
                              height: 1.1,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _CorrectionAcknowledgement extends StatelessWidget {
  const _CorrectionAcknowledgement({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Semantics(
      label: l10n.auroraCorrectionReceivedTitle,
      child: Container(
        constraints: const BoxConstraints(minHeight: 44),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.semanticSuccess.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(DS.radius8),
          border: Border.all(
            color: DS.semanticSuccess.withValues(alpha: 0.22),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.check_circle_outline_rounded,
              size: 15,
              color: DS.semanticSuccess,
            ),
            const SizedBox(width: DS.spacing6),
            Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.auroraCorrectionReceivedTitle,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontSize: 11,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
                Text(
                  l10n.auroraCorrectionReceivedSubtitle,
                  style: TextStyle(
                    color: DS.textSecondary,
                    fontSize: 10,
                    height: 1.1,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
