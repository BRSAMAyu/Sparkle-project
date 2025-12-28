import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/presentation/providers/capsule_provider.dart';

class CuriosityCapsuleCard extends ConsumerWidget {

  const CuriosityCapsuleCard({required this.capsule, super.key});
  final CuriosityCapsuleModel capsule;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius16),
      elevation: 2,
      child: ExpansionTile(
        tilePadding: const EdgeInsets.all(DS.lg),
        leading: Container(
          padding: const EdgeInsets.all(DS.sm),
          decoration: const BoxDecoration(
            gradient: AppDesignTokens.secondaryGradient,
            shape: BoxShape.circle,
          ),
          child: Icon(Icons.lightbulb_outline, color: DS.brandPrimary),
        ),
        title: Text(
          capsule.title,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: capsule.isRead 
            ? null 
            : const Text('New!', style: TextStyle(color: AppDesignTokens.primaryBase, fontWeight: FontWeight.bold)),
        onExpansionChanged: (expanded) {
          if (expanded && !capsule.isRead) {
            ref.read(capsuleProvider.notifier).markAsRead(capsule.id);
          }
        },
        children: [
          Padding(
            padding: const EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                MarkdownBody(data: capsule.content),
                const SizedBox(height: DS.sm),
                if (capsule.relatedSubject != null)
                  Chip(
                    label: Text(capsule.relatedSubject!),
                    backgroundColor: context.colors.surfaceElevated,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
}
