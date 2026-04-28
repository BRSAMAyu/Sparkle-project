import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class WorkingMemoryBadge extends StatelessWidget {
  const WorkingMemoryBadge({
    required this.consolidated,
    super.key,
  });

  final bool consolidated;

  @override
  Widget build(BuildContext context) {
    final label = consolidated ? context.l10n.chatMemoryArchivedToLongTerm : context.l10n.chatMemoryCurrentSession;
    final color = consolidated ? DS.success : DS.info;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: DS.fontSizeXs,
          fontWeight: DS.fontWeightSemibold,
        ),
      ),
    );
  }
}
