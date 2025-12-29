import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/presentation/providers/capsule_provider.dart';
import 'package:sparkle/presentation/widgets/community/share_resource_sheet.dart';

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
  Widget build(BuildContext context, WidgetRef ref) => Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(
        borderRadius: DS.borderRadius16,
        side: highlighted
            ? BorderSide(color: DS.prismGreen.withValues(alpha: 0.6), width: 1.5)
            : BorderSide(color: Colors.transparent, width: 0),
      ),
      elevation: 2,
      child: ExpansionTile(
        initiallyExpanded: initiallyExpanded,
        tilePadding: const EdgeInsets.all(DS.lg),
        leading: Container(
          padding: const EdgeInsets.all(DS.sm),
          decoration: BoxDecoration(
            gradient: DS.secondaryGradient,
            shape: BoxShape.circle,
          ),
          child: Icon(Icons.lightbulb_outline, color: DS.brandPrimary),
        ),
        title: Text(
          capsule.title,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        trailing: IconButton(
          icon: const Icon(Icons.share_outlined),
          onPressed: () => showShareResourceSheet(
            context,
            resourceType: 'curiosity_capsule',
            resourceId: capsule.id,
            title: capsule.title,
            subtitle: capsule.content,
          ),
        ),
        subtitle: capsule.isRead 
            ? null 
            : Text('New!', style: TextStyle(color: DS.primaryBase, fontWeight: FontWeight.bold)),
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
