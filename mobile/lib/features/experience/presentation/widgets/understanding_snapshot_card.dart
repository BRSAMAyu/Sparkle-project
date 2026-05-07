import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/experience/data/experience_models.dart';
import 'package:sparkle/features/experience/presentation/providers/experience_provider.dart';

class UnderstandingSnapshotCard extends ConsumerWidget {
  const UnderstandingSnapshotCard({
    super.key,
    this.onOpenChat,
  });

  final VoidCallback? onOpenChat;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final zh = I18nService.instance.isChinese;
    final snapshot = ref.watch(understandingSnapshotProvider);
    return Semantics(
      container: true,
      label: zh ? 'Sparkle 理解快照' : 'Sparkle understanding snapshot',
      child: snapshot.when(
      data: (data) => _UnderstandingSnapshotSurface(
        snapshot: data,
        onOpenChat: onOpenChat,
      ),
      loading: () => const _ExperienceCardSkeleton(),
      error: (_, __) => CompactErrorCard(
        onRetry: () => ref.invalidate(understandingSnapshotProvider),
      ),
      ),
    );
  }
}

class _UnderstandingSnapshotSurface extends StatelessWidget {
  const _UnderstandingSnapshotSurface({
    required this.snapshot,
    this.onOpenChat,
  });

  final UnderstandingSnapshot snapshot;
  final VoidCallback? onOpenChat;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    final accent =
        snapshot.status == 'risk_found' || snapshot.status == 'needs_confirm'
            ? DS.warning
            : DS.brandPrimary;
    final evidence = snapshot.evidence.isNotEmpty
        ? snapshot.evidence
        : snapshot.memoryClaims;
    final question =
        snapshot.openQuestions.isNotEmpty ? snapshot.openQuestions.first : null;

    return Semantics(
      container: true,
      label: zh
          ? 'Sparkle 对你的理解，可信度 ${(snapshot.confidence * 100).round()}%'
          : 'What Sparkle understands, confidence ${(snapshot.confidence * 100).round()}%',
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          borderColor: accent.withValues(alpha: 0.18),
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: accent.withValues(alpha: 0.12),
                      borderRadius: DS.borderRadius16,
                    ),
                    child: Icon(
                      Icons.psychology_alt_rounded,
                      color: accent,
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          zh ? 'Sparkle 对你的理解' : 'What Sparkle understands',
                          style: TextStyle(
                            color: DS.textSecondary,
                            fontSize: DS.fontSizeXs,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                        const SizedBox(height: DS.spacing4),
                        Text(
                          snapshot.summary.isNotEmpty
                              ? snapshot.summary
                              : (zh
                                  ? '我正在结合你的目标、任务和最近纠正来调整今天的陪跑方式。'
                                  : 'I am using your goal, tasks, and recent corrections to guide today.'),
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: DS.textPrimary,
                            fontSize: DS.fontSizeBase,
                            fontWeight: DS.fontWeightSemibold,
                            height: 1.52,
                          ),
                        ),
                      ],
                    ),
                  ),
                  _ConfidencePill(value: snapshot.confidence),
                ],
              ),
              if (evidence.isNotEmpty) ...[
                const SizedBox(height: DS.spacing12),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: evidence
                      .take(3)
                      .map((item) =>
                          _TinyEvidenceChip(label: item, color: accent))
                      .toList(growable: false),
                ),
              ],
              if (question != null) ...[
                const SizedBox(height: DS.spacing12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(DS.spacing12),
                  decoration: BoxDecoration(
                    color: DS.warning.withValues(alpha: 0.08),
                    borderRadius: DS.borderRadius12,
                    border: Border.all(
                      color: DS.warning.withValues(alpha: 0.18),
                    ),
                  ),
                  child: Text(
                    zh ? '我可能误读了：$question' : 'I may be wrong: $question',
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontSize: DS.fontSizeSm,
                      height: 1.52,
                    ),
                  ),
                ),
              ],
              const SizedBox(height: DS.spacing12),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  if (onOpenChat != null)
                    SparkleButton.primary(
                      label: zh ? '纠正我的理解' : 'Correct this',
                      icon: const Icon(Icons.edit_note_rounded),
                      onPressed: onOpenChat!,
                    ),
                  if (snapshot.nextStepLabel != null)
                    _TinyEvidenceChip(
                      label: snapshot.nextStepLabel!,
                      color: DS.success,
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ConfidencePill extends StatelessWidget {
  const _ConfidencePill({required this.value});

  final double value;

  @override
  Widget build(BuildContext context) {
    final percent = (value * 100).round();
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: DS.info.withValues(alpha: 0.1),
        borderRadius: DS.borderRadiusFull,
      ),
      child: Text(
        '$percent%',
        style: TextStyle(
          color: DS.info,
          fontSize: DS.fontSizeXs,
          fontWeight: DS.fontWeightBold,
        ),
      ),
    );
  }
}

class _TinyEvidenceChip extends StatelessWidget {
  const _TinyEvidenceChip({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.09),
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: color.withValues(alpha: 0.16)),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            color: DS.textPrimary,
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
      );
}

class _ExperienceCardSkeleton extends StatelessWidget {
  const _ExperienceCardSkeleton();

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          padding: const EdgeInsets.all(DS.spacing16),
          child: Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: DS.surfaceOverlay,
                  borderRadius: DS.borderRadius16,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(height: 10, width: 120, color: DS.surfaceOverlay),
                    const SizedBox(height: DS.spacing8),
                    Container(
                        height: 12,
                        width: double.infinity,
                        color: DS.surfaceOverlay),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
}
