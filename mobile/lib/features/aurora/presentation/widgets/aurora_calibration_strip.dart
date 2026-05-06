import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/features/aurora/data/models/aurora_calibration_card.dart';
import 'package:sparkle/features/aurora/data/repositories/aurora_calibration_repository.dart';
import 'package:sparkle/features/aurora/presentation/providers/aurora_calibration_provider.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class AuroraCalibrationStrip extends ConsumerStatefulWidget {
  const AuroraCalibrationStrip({
    super.key,
    this.planId,
  });

  final String? planId;

  @override
  ConsumerState<AuroraCalibrationStrip> createState() =>
      _AuroraCalibrationStripState();
}

class _AuroraCalibrationStripState
    extends ConsumerState<AuroraCalibrationStrip> {
  bool _expanded = false;
  final Map<String, AuroraCalibrationResponse> _pendingResponses = {};

  Future<void> _respondToCard(
    AuroraCalibrationCard card,
    AuroraCalibrationResponse response,
  ) async {
    setState(() {
      _pendingResponses[card.id] = response;
    });

    try {
      await ref
          .read(auroraCalibrationRepositoryProvider)
          .respondToCalibrationCard(
            cardId: card.id,
            response: response,
          );
      ref.invalidate(auroraCalibrationSurfaceProvider(widget.planId));
      if (!mounted) return;
      AppFeedback.success(context, _successMessage(response));
    } catch (error) {
      if (!mounted) return;
      AppFeedback.error(context, context.l10n.auroraFeedbackFailed(error.toString()));
    } finally {
      if (mounted) {
        setState(() {
          _pendingResponses.remove(card.id);
        });
      }
    }
  }

  String _successMessage(AuroraCalibrationResponse response) {
    switch (response) {
      case AuroraCalibrationResponse.confirm:
        return 'Aurora 会把这条判断当成已确认';
      case AuroraCalibrationResponse.incorrect:
        return 'Aurora 会收回这条判断并重新学习';
      case AuroraCalibrationResponse.mute:
        return 'Aurora 不会再用这种方式打扰你';
    }
  }

  @override
  Widget build(BuildContext context) {
    final surfaceAsync = ref.watch(
      auroraCalibrationSurfaceProvider(widget.planId),
    );

    return surfaceAsync.when(
      data: (surface) {
        if (!surface.hasItems) {
          return const SizedBox.shrink();
        }

        return ContentConstraint(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
              DS.spacing16,
              DS.spacing4,
              DS.spacing16,
              DS.spacing12,
            ),
            child: GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              padding: const EdgeInsets.fromLTRB(
                DS.spacing16,
                14,
                DS.spacing16,
                DS.spacing16,
              ),
              borderColor: surface.state == 'needs_confirmation'
                  ? DS.brandPrimary.withValues(alpha: 0.28)
                  : DS.borderSubtle,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  InkWell(
                    borderRadius: BorderRadius.circular(18),
                    onTap: () {
                      setState(() {
                        _expanded = !_expanded;
                      });
                    },
                    child: Row(
                      children: [
                        Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(
                            color: (surface.state == 'needs_confirmation'
                                    ? DS.brandPrimary
                                    : DS.info)
                                .withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Icon(
                            surface.state == 'needs_confirmation'
                                ? Icons.priority_high_rounded
                                : Icons.visibility_outlined,
                            color: surface.state == 'needs_confirmation'
                                ? DS.brandPrimary
                                : DS.info,
                            size: 18,
                          ),
                        ),
                        const SizedBox(width: DS.spacing12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                surface.label,
                                style: Theme.of(context)
                                    .textTheme
                                    .titleSmall
                                    ?.copyWith(
                                      fontWeight: FontWeight.w700,
                                    ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                '${surface.items.length} 条关键假设待你校准',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(
                                      color: DS.textSecondary,
                                      height: 1.35,
                                    ),
                              ),
                            ],
                          ),
                        ),
                        AnimatedRotation(
                          turns: _expanded ? 0.5 : 0,
                          duration: DS.motionDuration(
                            SparkleMotionToken.micro,
                            reduceMotion: context.reduceMotion,
                          ),
                          child: Icon(
                            Icons.keyboard_arrow_down_rounded,
                            color: DS.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  AnimatedSize(
                    duration: DS.motionDuration(
                      SparkleMotionToken.standard,
                      reduceMotion: context.reduceMotion,
                    ),
                    curve: DS.motionCurve(SparkleMotionToken.standard),
                    child: _expanded
                        ? Padding(
                            padding: const EdgeInsets.only(top: 14),
                            child: Column(
                              children: [
                                for (var index = 0;
                                    index < surface.items.length;
                                    index++) ...[
                                  _CalibrationCardTile(
                                    card: surface.items[index],
                                    isBusy: _pendingResponses
                                        .containsKey(surface.items[index].id),
                                    pendingResponse: _pendingResponses[
                                        surface.items[index].id],
                                    onRespond: _respondToCard,
                                  ),
                                  if (index != surface.items.length - 1)
                                    const SizedBox(height: DS.spacing12),
                                ],
                              ],
                            ),
                          )
                        : const SizedBox.shrink(),
                  ),
                ],
              ),
            ),
          ),
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, __) => CompactErrorCard(
        onRetry: () => ref.invalidate(auroraCalibrationSurfaceProvider(widget.planId)),
      ),
    );
  }
}

class _CalibrationCardTile extends StatelessWidget {
  const _CalibrationCardTile({
    required this.card,
    required this.isBusy,
    required this.pendingResponse,
    required this.onRespond,
  });

  final AuroraCalibrationCard card;
  final bool isBusy;
  final AuroraCalibrationResponse? pendingResponse;
  final Future<void> Function(
    AuroraCalibrationCard card,
    AuroraCalibrationResponse response,
  ) onRespond;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final evidenceSummary = (card.evidenceSummary ?? '').trim();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: DS.surfacePrimary.withValues(alpha: 0.42),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  card.statement.isNotEmpty ? card.statement : card.title,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                    height: 1.45,
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing10),
              _ConfidenceBadge(
                label: card.confidenceLabel,
                needsConfirmation: card.needsConfirmation,
              ),
            ],
          ),
          if (evidenceSummary.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            Text(
              evidenceSummary,
              style: theme.textTheme.bodySmall?.copyWith(
                color: DS.textSecondary,
                height: 1.45,
              ),
            ),
          ],
          if (card.evidence.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                for (final item in card.evidence) _EvidenceChip(label: item),
              ],
            ),
          ],
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              SparkleButton(
                label: context.l10n.auroraConfirm,
                variant: ButtonVariant.outline,
                size: ButtonSize.small,
                loading: pendingResponse == AuroraCalibrationResponse.confirm,
                disabled: isBusy,
                onPressed: () => unawaited(
                  onRespond(card, AuroraCalibrationResponse.confirm),
                ),
              ),
              SparkleButton(
                label: context.l10n.auroraNotRight,
                variant: ButtonVariant.ghost,
                size: ButtonSize.small,
                loading: pendingResponse == AuroraCalibrationResponse.incorrect,
                disabled: isBusy,
                onPressed: () => unawaited(
                  onRespond(card, AuroraCalibrationResponse.incorrect),
                ),
              ),
              SparkleButton(
                label: context.l10n.auroraDontJudge,
                variant: ButtonVariant.ghost,
                size: ButtonSize.small,
                loading: pendingResponse == AuroraCalibrationResponse.mute,
                disabled: isBusy,
                onPressed: () => unawaited(
                  onRespond(card, AuroraCalibrationResponse.mute),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ConfidenceBadge extends StatelessWidget {
  const _ConfidenceBadge({
    required this.label,
    required this.needsConfirmation,
  });

  final String label;
  final bool needsConfirmation;

  @override
  Widget build(BuildContext context) {
    final accent = needsConfirmation ? DS.brandPrimary : DS.info;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: accent.withValues(alpha: 0.18)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: accent,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class _EvidenceChip extends StatelessWidget {
  const _EvidenceChip({
    required this.label,
  });

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(maxWidth: 280),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary.withValues(alpha: 0.85),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
                color: DS.textSecondary,
                height: 1.35,
              ),
        ),
      );
}
