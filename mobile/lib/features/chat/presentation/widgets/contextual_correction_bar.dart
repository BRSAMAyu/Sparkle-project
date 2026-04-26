import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';

/// Contextual correction buttons shown after AI responses.
///
/// When [predictedReplyGroups] are available from the Aurora backend, shows
/// the top group's primary options (sorted by confidence) plus the freeform
/// fallback. Otherwise falls back to the static hardcoded chips.
class ContextualCorrectionBar extends StatelessWidget {
  const ContextualCorrectionBar({
    required this.onRecalibrate,
    this.onSendCorrection,
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

  /// Called with the user's semantic reply text (from predicted options or freeform).
  final ValueChanged<String>? onSendCorrection;

  /// Predicted reply groups from Aurora backend. If non-empty, used instead
  /// of the static fallback chips.
  final List<AuroraPredictedReplyGroup>? predictedReplyGroups;

  final bool visible;

  @override
  Widget build(BuildContext context) {
    if (!visible) return const SizedBox.shrink();

    final groups = predictedReplyGroups;
    final topGroup = (groups != null && groups.isNotEmpty) ? groups.first : null;

    if (topGroup != null && topGroup.options.isNotEmpty) {
      return _buildPredictedOptions(context, topGroup);
    }
    return _buildFallback(context);
  }

  Widget _buildPredictedOptions(BuildContext context, AuroraPredictedReplyGroup group) {
    final primaryOptions = group.primaryOptions.take(3).toList();
    final freeform = group.freeformOption;

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
          ...primaryOptions.map((opt) => _CorrectionChip(
                label: opt.label,
                onTap: () => _handleOptionTap(opt),
              )),
          if (freeform != null)
            _CorrectionChip(
              label: freeform.label,
              onTap: () => _handleOptionTap(freeform),
              isAccent: true,
            )
          else
            _CorrectionChip(
              label: context.l10n.auroraCorrectRecalibrate,
              onTap: onRecalibrate,
              isAccent: true,
            ),
        ],
      ),
    );
  }

  void _handleOptionTap(AuroraPredictedReplyOption option) {
    if (option.isFreeform) {
      onRecalibrate();
      return;
    }
    final text = option.semanticValue.isNotEmpty ? option.semanticValue : option.label;
    onSendCorrection?.call(text);
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
          if (onNotRightDirection != null)
            _CorrectionChip(
              label: l10n.auroraCorrectNotRight,
              onTap: onNotRightDirection!,
            ),
          if (onMakeShorter != null)
            _CorrectionChip(
              label: l10n.auroraCorrectShorter,
              onTap: onMakeShorter!,
            ),
          if (onGivePractice != null)
            _CorrectionChip(
              label: l10n.auroraCorrectDirect,
              onTap: onGivePractice!,
            ),
          _CorrectionChip(
            label: l10n.auroraCorrectRecalibrate,
            onTap: onRecalibrate,
            isAccent: true,
          ),
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
        children: sources.map((source) {
          return GestureDetector(
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
          );
        }).toList(),
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

// ── Internal ────────────────────────────────────────────────────

class _CorrectionChip extends StatelessWidget {
  const _CorrectionChip({
    required this.label,
    required this.onTap,
    this.isAccent = false,
  });

  final String label;
  final VoidCallback onTap;
  final bool isAccent;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: isAccent
              ? DS.brandPrimary.withValues(alpha: 0.08)
              : DS.surfaceSecondary.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(999),
          border: isAccent
              ? Border.all(
                  color: DS.brandPrimary.withValues(alpha: 0.2),
                )
              : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isAccent ? DS.brandPrimary : DS.textSecondary,
            fontSize: 11,
            fontWeight: isAccent ? DS.fontWeightMedium : DS.fontWeightRegular,
          ),
        ),
      ),
    );
  }
}
