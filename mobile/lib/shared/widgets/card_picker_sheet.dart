import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';

class CardPickerOption {
  const CardPickerOption({
    required this.id,
    required this.title,
    this.subtitle,
    this.group,
    this.icon,
    this.isSelected = false,
  });

  final String id;
  final String title;
  final String? subtitle;
  final String? group;
  final IconData? icon;
  final bool isSelected;
}

class CardPickerSheet extends StatefulWidget {
  const CardPickerSheet({
    required this.title,
    required this.options,
    this.allowEmptySelection = false,
    this.emptySelectionLabel = 'Unassigned',
    super.key,
  });

  final String title;
  final List<CardPickerOption> options;
  final bool allowEmptySelection;
  final String emptySelectionLabel;

  static Future<String?> show(
    BuildContext context, {
    required String title,
    required List<CardPickerOption> options,
    bool allowEmptySelection = false,
    String emptySelectionLabel = 'Unassigned',
  }) =>
      showSensoryModalBottomSheet<String?>(
        context: context,
        isScrollControlled: true,
        builder: (_) => CardPickerSheet(
          title: title,
          options: options,
          allowEmptySelection: allowEmptySelection,
          emptySelectionLabel: emptySelectionLabel,
        ),
      );

  @override
  State<CardPickerSheet> createState() => _CardPickerSheetState();
}

class _CardPickerSheetState extends State<CardPickerSheet> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final normalized = _query.trim().toLowerCase();
    final filtered = widget.options.where((option) {
      if (normalized.isEmpty) return true;
      return option.title.toLowerCase().contains(normalized) ||
          (option.subtitle ?? '').toLowerCase().contains(normalized) ||
          (option.group ?? '').toLowerCase().contains(normalized);
    }).toList();

    final grouped = <String, List<CardPickerOption>>{};
    for (final option in filtered) {
      final key = option.group ?? 'Other';
      grouped.putIfAbsent(key, () => []).add(option);
    }

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing8,
          DS.spacing16,
          DS.spacing24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.title,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing12),
            TextField(
              onChanged: (value) => setState(() => _query = value),
              decoration: InputDecoration(
                hintText: 'Search cards or plans',
                prefixIcon: const Icon(Icons.search_rounded),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            Flexible(
              child: filtered.isEmpty && normalized.isNotEmpty
                  ? Center(
                      child: Padding(
                        padding:
                            const EdgeInsets.symmetric(vertical: DS.spacing24),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.search_off_rounded,
                              size: 48,
                              color: DS.textSecondary,
                            ),
                            const SizedBox(height: DS.spacing12),
                            Text(
                              'No results for "$_query"',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                  ),
                            ),
                          ],
                        ),
                      ),
                    )
                  : ListView(
                      shrinkWrap: true,
                      children: [
                        if (widget.allowEmptySelection)
                          _PickerTile(
                            title: widget.emptySelectionLabel,
                            subtitle: 'Detach from current plan',
                            icon: Icons.link_off_rounded,
                            onTap: () => Navigator.of(context).pop(),
                          ),
                        for (final entry in grouped.entries) ...[
                          Padding(
                            padding: const EdgeInsets.only(
                              top: DS.spacing8,
                              bottom: DS.spacing6,
                            ),
                            child: Text(
                              entry.key,
                              style: Theme.of(context)
                                  .textTheme
                                  .labelLarge
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                    fontWeight: DS.fontWeightSemiBold,
                                  ),
                            ),
                          ),
                          ...entry.value.map(
                            (option) => _PickerTile(
                              title: option.title,
                              subtitle: option.subtitle,
                              icon: option.icon,
                              isSelected: option.isSelected,
                              onTap: () => Navigator.of(context).pop(option.id),
                            ),
                          ),
                        ],
                      ],
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PickerTile extends StatelessWidget {
  const _PickerTile({
    required this.title,
    required this.onTap,
    this.subtitle,
    this.icon,
    this.isSelected = false,
  });

  final String title;
  final String? subtitle;
  final IconData? icon;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: GraphiteCardSurface(
          child: ListTile(
            contentPadding: EdgeInsets.zero,
            onTap: onTap,
            leading: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(icon ?? Icons.layers_outlined, color: DS.primaryBase),
            ),
            title: Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightSemiBold,
                  ),
            ),
            subtitle: subtitle == null
                ? null
                : Text(
                    subtitle!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
            trailing: isSelected
                ? Icon(Icons.check_circle_rounded, color: DS.success)
                : const Icon(Icons.chevron_right_rounded),
          ),
        ),
      );
}
