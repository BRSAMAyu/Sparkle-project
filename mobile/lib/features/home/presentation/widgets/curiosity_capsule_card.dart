import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_archive_provider.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';

class CuriosityCapsuleCard extends ConsumerWidget {
  const CuriosityCapsuleCard({
    required this.capsule,
    this.highlighted = false,
    this.initiallyExpanded = false,
    this.archived = false,
    super.key,
  });
  final CuriosityCapsuleModel capsule;
  final bool highlighted;
  final bool initiallyExpanded;
  final bool archived;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rawPatterns = capsule.personalizationContext?['based_on_patterns'];
    final localizedPatterns = _localizedPatterns(context, rawPatterns);
    // 1. Resolve base material (NeoGlass)
    var material = AppMaterials.neoGlass;

    // 2. Apply "Highlighted" state modifications
    if (highlighted) {
      material = material.copyWith(
        // Stronger rim light
        rimLightColor:
            context.sparkleColors.brandPrimary.withValues(alpha: 0.8),
        // Active glow
        glowColor: context.sparkleColors.brandPrimary.withValues(alpha: 0.15),
        // Border
        borderWidth: 1.5,
        borderColor: context.sparkleColors.brandPrimary.withValues(alpha: 0.5),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing8,
      ),
      child: MaterialStyler(
        material: material,
        borderRadius: DS.borderRadius16,
        child: Theme(
          // Ensure ExpansionTile doesn't draw its own dividers or backgrounds
          data: Theme.of(context).copyWith(
            dividerColor: DS.surfacePrimary.withValues(alpha: 0),
            splashColor: DS.surfacePrimary.withValues(alpha: 0),
            highlightColor: DS.surfacePrimary.withValues(alpha: 0),
          ),
          child: ExpansionTile(
            initiallyExpanded: initiallyExpanded,
            tilePadding: const EdgeInsets.all(DS.lg),
            backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
            collapsedBackgroundColor: DS.surfacePrimary.withValues(alpha: 0),

            // Icon
            leading: SparkleAttentionPulse(
              active: !capsule.isRead,
              glowColor: DS.secondaryBase,
              child: Container(
                padding: const EdgeInsets.all(DS.sm),
                decoration: BoxDecoration(
                  gradient: DS.secondaryGradient,
                  shape: BoxShape.circle,
                  boxShadow: context.sparkleShadows.small,
                ),
                child: Icon(
                  Icons.lightbulb_outline,
                  color: DS.textOnPrimary,
                  size: 20,
                ),
              ),
            ),

            // Title
            title: Text(
              capsule.title,
              style: context.sparkleTypography.headingMedium.copyWith(
                fontSize: 18,
              ),
            ),

            // Subtitle (New Badge)
            subtitle: capsule.isRead
                ? null
                : SparkleAttentionPulse(
                    glowColor: context.sparkleColors.brandPrimary,
                    child: Text(
                      context.l10n.capsuleNewDiscovery,
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: context.sparkleColors.brandPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),

            onExpansionChanged: (expanded) {
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
              );
              if (expanded && !capsule.isRead) {
                unawaited(
                  ref.read(capsuleProvider.notifier).markAsRead(capsule.id),
                );
              }
            },

            // Content
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(DS.lg, 0, DS.lg, DS.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Divider line (optional, maybe just space)
                    const SizedBox(height: DS.sm),

                    if (localizedPatterns.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(bottom: DS.spacing8),
                        child: _buildPersonalizationBadge(
                          context,
                          patterns: localizedPatterns,
                        ),
                      ),

                    MarkdownBody(
                      data: capsule.content,
                      styleSheet: MarkdownStyleSheet(
                        p: context.sparkleTypography.bodyMedium,
                        strong: context.sparkleTypography.bodyMedium
                            .copyWith(fontWeight: FontWeight.bold),
                      ),
                    ),
                    const SizedBox(height: DS.md),

                    if (capsule.relatedSubject != null)
                      Chip(
                        label: Text(
                          capsule.relatedSubject!,
                          style: context.sparkleTypography.labelSmall,
                        ),
                        backgroundColor: context.sparkleColors.surfaceTertiary
                            .withValues(alpha: 0.5),
                        side: BorderSide.none,
                        padding: EdgeInsets.zero,
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    const SizedBox(height: DS.spacing12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: SparkleButton(
                        label: archived
                            ? context.l10n.capsuleRestoreCurrent
                            : context.l10n.capsuleArchiveAction,
                        variant: ButtonVariant.ghost,
                        onPressed: () {
                          unawaited(
                            SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.confirm,
                            ),
                          );
                          ref
                              .read(capsuleArchiveProvider.notifier)
                              .toggleArchive(capsule.id);
                          AppFeedback.info(
                            context,
                            archived
                                ? context.l10n.capsuleRestored
                                : context.l10n.capsuleArchivedInfo,
                          );
                        },
                        icon: Icon(
                          archived
                              ? Icons.unarchive_outlined
                              : Icons.archive_outlined,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<String> _localizedPatterns(BuildContext context, dynamic rawPatterns) {
    if (rawPatterns is! List) {
      return [];
    }
    return rawPatterns
        .map((item) => item.toString())
        .where((item) => item.isNotEmpty)
        .map((item) => _localizePatternName(context, item))
        .toList();
  }

  String _localizePatternName(BuildContext context, String name) {
    final l10n = context.l10n;
    switch (name) {
      case 'Planning Optimism':
        return l10n.patternPlanningOptimism;
      case 'Focus Decay':
        return l10n.patternFocusDecay;
      case 'Procrastination':
        return l10n.patternProcrastination;
      default:
        return name;
    }
  }

  Widget _buildPersonalizationBadge(BuildContext context, {required List<String> patterns}) {
    if (patterns.isEmpty) {
      return const SizedBox.shrink();
    }
    final l10n = context.l10n;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: DS.prismPurple.withValues(alpha: 0.08),
        borderRadius: DS.borderRadius8,
        border: Border.all(
          color: DS.prismPurple.withValues(alpha: 0.2),
          width: 0.5,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.psychology_outlined, size: 13, color: DS.prismPurple),
          const SizedBox(width: DS.spacing4),
          Text(
            l10n.capsulePersonalizationBadge(patterns.first),
            style: TextStyle(
              fontSize: 11,
              color: DS.prismPurple,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
