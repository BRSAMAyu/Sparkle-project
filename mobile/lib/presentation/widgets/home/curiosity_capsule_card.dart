import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/capsule_provider.dart';
import 'package:sparkle/data/models/curiosity_capsule_model.dart';

class CuriosityCapsuleCard extends ConsumerWidget {
  final CuriosityCapsuleModel capsule;

  const CuriosityCapsuleCard({super.key, required this.capsule});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius16),
      elevation: 2,
      child: ExpansionTile(
        tilePadding: const EdgeInsets.all(16),
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            gradient: AppDesignTokens.secondaryGradient,
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.lightbulb_outline, color: Colors.white),
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
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                MarkdownBody(data: capsule.content),
                const SizedBox(height: 8),
                if (capsule.relatedSubject != null)
                  Chip(label: Text(capsule.relatedSubject!), backgroundColor: AppDesignTokens.neutral100),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
