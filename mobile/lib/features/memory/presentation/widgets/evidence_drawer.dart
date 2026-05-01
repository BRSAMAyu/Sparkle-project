import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class EvidenceDrawer extends StatelessWidget {
  const EvidenceDrawer({
    super.key,
    this.items = const [],
    this.refs = const [],
    this.evidenceMissing = false,
  });

  final List<Map<String, dynamic>> items;
  final List<EvidenceRefModel> refs;
  final bool evidenceMissing;

  static Future<void> show(
    BuildContext context, {
    List<EvidenceRefModel> refs = const [],
    List<Map<String, dynamic>> items = const [],
    bool evidenceMissing = false,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(ctx).size.height * 0.6,
        ),
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.all(DS.md),
              child: Row(
                children: [
                  Text(context.l10n.memEvidenceRecord, style: DS.titleMedium),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
            ),
            Flexible(
              child: EvidenceDrawer(
                refs: refs,
                items: items,
                evidenceMissing: evidenceMissing,
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final allItems = [
      ...items,
      ...refs.map((r) => {'summary': '${r.type}: ${r.id}'}),
    ];

    if (allItems.isEmpty && !evidenceMissing) {
      return Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Text(
          '暂无证据记录',
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
      );
    }

    if (evidenceMissing) {
      return Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Text(
          '证据不足',
          style: DS.bodySmall.copyWith(color: DS.semanticWarning),
        ),
      );
    }

    return ListView(
      shrinkWrap: true,
      padding: const EdgeInsets.symmetric(horizontal: DS.md),
      children: allItems
          .map(
            (item) => ListTile(
              dense: true,
              title: Text(
                item['summary']?.toString() ?? '证据条目',
                style: DS.bodySmall,
              ),
              subtitle: item['source'] != null
                  ? Text(item['source'].toString(), style: DS.labelSmall)
                  : null,
            ),
          )
          .toList(),
    );
  }
}
