import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_cards.dart';

enum _EvidenceFilter { all, strong, weak, missing }

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
    return showSensoryModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => _EvidenceDrawerSheet(
        refs: refs,
        items: items,
        evidenceMissing: evidenceMissing,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;

    if (items.isEmpty && refs.isEmpty && !evidenceMissing) {
      return Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Text(
          zh ? '暂无证据记录' : 'No evidence records yet',
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
      );
    }

    if (evidenceMissing && items.isEmpty && refs.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: DS.semanticWarning,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: DS.spacing8),
            Text(
              zh ? '证据不足' : 'Insufficient evidence',
              style: DS.bodySmall.copyWith(color: DS.semanticWarning),
            ),
          ],
        ),
      );
    }

    return ListView(
      shrinkWrap: true,
      padding: const EdgeInsets.symmetric(horizontal: DS.md),
      children: [
        ...items
            .whereType<Map<String, dynamic>>()
            .map((item) => _buildEvidenceCard(context, item)),
        ...refs.map((r) => Padding(
              padding: const EdgeInsets.only(bottom: DS.sm),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(DS.spacing10),
                  child: Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: DS.semanticSuccess,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: DS.spacing8),
                      Expanded(
                        child: Text(
                          '${r.type}: ${r.id}',
                          style: DS.bodySmall.copyWith(color: DS.textPrimary),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            )),
      ],
    );
  }

  Widget _buildEvidenceCard(BuildContext context, Map<String, dynamic> item) {
    final type = item['type']?.toString() ?? '';
    final id = item['id']?.toString() ?? '';
    final status = item['status']?.toString() ?? 'ok';
    final evidenceItem = EvidenceResolveItem(
      type: type,
      id: id,
      status: status,
      redactionReason: item['redaction_reason'] as String?,
      payload: _extractPayload(item),
    );
    return EvidenceCard(
      item: evidenceItem,
      compact: true,
    );
  }

  Map<String, dynamic>? _extractPayload(Map<String, dynamic> item) {
    const payloadKeys = [
      'event', 'chat_turn', 'state', 'error', 'practice_outcome',
      'concept', 'strategy', 'task', 'summary',
    ];
    final payload = <String, dynamic>{};
    for (final key in payloadKeys) {
      if (item[key] is Map<String, dynamic>) {
        payload[key] = item[key];
      }
    }
    return payload.isEmpty ? null : payload;
  }
}

class _EvidenceDrawerSheet extends StatefulWidget {
  const _EvidenceDrawerSheet({
    required this.refs,
    required this.items,
    required this.evidenceMissing,
  });

  final List<EvidenceRefModel> refs;
  final List<Map<String, dynamic>> items;
  final bool evidenceMissing;

  @override
  State<_EvidenceDrawerSheet> createState() => _EvidenceDrawerSheetState();
}

class _EvidenceDrawerSheetState extends State<_EvidenceDrawerSheet> {
  _EvidenceFilter _filter = _EvidenceFilter.all;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;

    final resolvedItems = _resolveItems();
    final strongCount = resolvedItems.where((i) => _itemTier(i) == 'strong').length;
    final weakCount = resolvedItems.where((i) => _itemTier(i) == 'weak').length;
    final missingCount = resolvedItems.where((i) => _itemTier(i) == 'missing').length;

    final filtered = _filter == _EvidenceFilter.all
        ? resolvedItems
        : resolvedItems.where((i) => _itemTier(i) == _filter.name).toList();

    return ConstrainedBox(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.5,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: DS.md, vertical: DS.sm),
            child: Row(
              children: [
                Text(context.l10n.memEvidenceRecord, style: DS.titleMedium),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close, size: DS.iconSizeXs),
                  onPressed: () => Navigator.pop(context),
                  visualDensity: VisualDensity.compact,
                ),
              ],
            ),
          ),
          // Summary bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: DS.md),
            child: Row(
              children: [
                _SummaryChip(
                  label: zh ? '强' : 'Strong',
                  count: strongCount,
                  color: DS.semanticSuccess,
                ),
                const SizedBox(width: DS.spacing6),
                _SummaryChip(
                  label: zh ? '弱' : 'Weak',
                  count: weakCount,
                  color: DS.semanticWarning,
                ),
                const SizedBox(width: DS.spacing6),
                _SummaryChip(
                  label: zh ? '缺' : 'Missing',
                  count: missingCount,
                  color: DS.semanticError,
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing8),
          // Filter segment
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: DS.md),
            child: SizedBox(
              height: 32,
              child: SegmentedButton<_EvidenceFilter>(
                segments: [
                  ButtonSegment<_EvidenceFilter>(
                    value: _EvidenceFilter.all,
                    label: Text(
                      zh ? '全部' : 'All',
                      style: DS.labelSmall,
                    ),
                  ),
                  ButtonSegment<_EvidenceFilter>(
                    value: _EvidenceFilter.strong,
                    label: Text(
                      zh ? '强' : 'Strong',
                      style: DS.labelSmall,
                    ),
                  ),
                  ButtonSegment<_EvidenceFilter>(
                    value: _EvidenceFilter.weak,
                    label: Text(
                      zh ? '弱' : 'Weak',
                      style: DS.labelSmall,
                    ),
                  ),
                  ButtonSegment<_EvidenceFilter>(
                    value: _EvidenceFilter.missing,
                    label: Text(
                      zh ? '缺' : 'Missing',
                      style: DS.labelSmall,
                    ),
                  ),
                ],
                selected: {_filter},
                onSelectionChanged: (f) => setState(() => _filter = f.first),
                style: ButtonStyle(
                  visualDensity: VisualDensity.compact,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
            ),
          ),
          const SizedBox(height: DS.spacing8),
          // Pull-to-dismiss indicator
          Container(
            width: 32,
            height: 4,
            decoration: BoxDecoration(
              color: DS.borderSubtle,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: DS.spacing6),
          // Content
          Flexible(
            child: widget.evidenceMissing &&
                    widget.items.isEmpty &&
                    widget.refs.isEmpty
                ? Padding(
                    padding: const EdgeInsets.all(DS.md),
                    child: Text(
                      zh ? '证据不足' : 'Insufficient evidence',
                      style: DS.bodySmall.copyWith(color: DS.semanticWarning),
                    ),
                  )
                : filtered.isEmpty
                    ? Padding(
                        padding: const EdgeInsets.all(DS.lg),
                        child: Text(
                          zh ? '没有匹配的证据' : 'No matching evidence',
                          style: DS.bodySmall.copyWith(color: DS.textSecondary),
                        ),
                      )
                    : EvidenceDrawer(
                        items: filtered,
                        refs: _filter == _EvidenceFilter.all ||
                                _filter == _EvidenceFilter.strong
                            ? widget.refs
                            : [],
                        evidenceMissing:
                            _filter == _EvidenceFilter.all ||
                                    _filter == _EvidenceFilter.missing
                                ? widget.evidenceMissing
                                : false,
                      ),
          ),
        ],
      ),
    );
  }

  List<Map<String, dynamic>> _resolveItems() {
    final resolved = <Map<String, dynamic>>[];
    for (final item in widget.items) {
      resolved.add(item);
    }
    return resolved;
  }

  String _itemTier(Map<String, dynamic> item) {
    final status = item['status']?.toString() ?? 'ok';
    if (status == 'missing') return 'missing';
    if (status == 'redacted') return 'weak';
    var richness = 0;
    for (final key in [
      'event', 'chat_turn', 'error', 'practice_outcome',
      'concept', 'task', 'summary', 'state',
    ]) {
      if (item[key] is Map && (item[key] as Map).isNotEmpty) richness++;
    }
    return richness >= 2 ? 'strong' : 'weak';
  }
}

class _SummaryChip extends StatelessWidget {
  const _SummaryChip({
    required this.label,
    required this.count,
    required this.color,
  });

  final String label;
  final int count;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: DS.borderRadius6,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: DS.spacing4),
            Text('$label $count', style: DS.labelSmall.copyWith(color: color)),
          ],
        ),
      );
}
