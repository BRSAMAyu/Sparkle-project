import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/presentation/providers/capsule_provider.dart';

class CuriosityCapsuleCard extends ConsumerWidget {
  const CuriosityCapsuleCard({
    required this.capsule,
    this.highlighted = false,
    this.initiallyExpanded = false,
    super.key,
  });
  final CuriosityCapsuleModel capsule;
  final bool highlighted;
  final bool initiallyExpanded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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
        borderColor:
            context.sparkleColors.brandPrimary.withValues(alpha: 0.5),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: MaterialStyler(
        material: material,
        borderRadius: DS.borderRadius16,
        child: Theme(
          // Ensure ExpansionTile doesn't draw its own dividers or backgrounds
          data: Theme.of(context).copyWith(
            dividerColor: Colors.transparent,
            splashColor: Colors.transparent,
            highlightColor: Colors.transparent,
          ),
          child: ExpansionTile(
            initiallyExpanded: initiallyExpanded,
            tilePadding: const EdgeInsets.all(DS.lg),
            backgroundColor: Colors.transparent,
            collapsedBackgroundColor: Colors.transparent,

            // Icon
            leading: Container(
              padding: const EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                gradient: DS.secondaryGradient,
                shape: BoxShape.circle,
                boxShadow: context.sparkleShadows.small,
              ),
              child: const Icon(
                Icons.lightbulb_outline,
                color: Colors.white,
                size: 20,
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
                : Text(
                    'New Discovery',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: context.sparkleColors.brandPrimary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),

            onExpansionChanged: (expanded) {
              if (expanded && !capsule.isRead) {
                ref.read(capsuleProvider.notifier).markAsRead(capsule.id);
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
                        materialTapTargetSize:
                            MaterialTapTargetSize.shrinkWrap,
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
}