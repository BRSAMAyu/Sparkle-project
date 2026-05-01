import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class GraphDiagnosticCard extends StatelessWidget {
  const GraphDiagnosticCard({
    required this.data,
    super.key,
    this.onAction,
  });

  final Map<String, dynamic> data;
  final Future<void> Function(String actionType, Map<String, dynamic> payload)?
      onAction;

  @override
  Widget build(BuildContext context) {
    final weakNodes = _mapList(data['weak_nodes']);
    final atRiskNodes = _mapList(data['at_risk_nodes']);
    final recommended = _mapList(data['recommended_next_review']);
    final summary = data['summary']?.toString() ?? '';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (summary.isNotEmpty) ...[
          Text(
            summary,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral700,
                  height: 1.45,
                ),
          ),
          const SizedBox(height: DS.spacing12),
        ],
        if (weakNodes.isNotEmpty) ...[
          _SectionTitle(
            title: context.l10n.chatGraphWeakestPoints,
            subtitle: context.l10n.chatGraphWeakestDesc,
          ),
          const SizedBox(height: DS.spacing8),
          ...weakNodes.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: _NodeTile(
                item: item,
                tone: const Color(0xFFF97316),
                onAction: onAction,
              ),
            ),
          ),
        ],
        if (atRiskNodes.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          _SectionTitle(
            title: context.l10n.chatGraphRiskZone,
            subtitle: context.l10n.chatGraphRiskDesc,
          ),
          const SizedBox(height: DS.spacing8),
          ...atRiskNodes.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: _NodeTile(
                item: item,
                tone: const Color(0xFFD97706),
                onAction: onAction,
              ),
            ),
          ),
        ],
        if (recommended.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          _SectionTitle(
            title: context.l10n.chatGraphNextStepSuggestion,
            subtitle: context.l10n.chatGraphNextStepDesc,
          ),
          const SizedBox(height: DS.spacing6),
          ...recommended.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing4),
              child: Text(
                '• ${item['node_name']} (${item['mastery']}%)',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral700,
                    ),
              ),
            ),
          ),
        ],
        if ((data['binding_note']?.toString() ?? '').isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            data['binding_note'].toString(),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral500,
                ),
          ),
        ],
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({
    required this.title,
    required this.subtitle,
  });

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: DS.fontWeightSemibold,
                color: DS.neutral900,
              ),
        ),
        const SizedBox(height: DS.spacing2),
        Text(
          subtitle,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: DS.neutral600,
              ),
        ),
      ],
    );
  }
}

class _NodeTile extends StatelessWidget {
  const _NodeTile({
    required this.item,
    required this.tone,
    this.onAction,
  });

  final Map<String, dynamic> item;
  final Color tone;
  final Future<void> Function(String actionType, Map<String, dynamic> payload)?
      onAction;

  @override
  Widget build(BuildContext context) {
    final actions = <Widget>[];
    final route = item['route']?.toString() ?? '';
    final prompt = item['prompt']?.toString() ?? '';
    if (route.isNotEmpty && onAction != null) {
      actions.add(
        CustomButton.secondary(
          text: context.l10n.chatGraphGoToGalaxy,
          onPressed: () => unawaited(onAction!(
            'route',
            {'route': route},
          )),
          size: CustomButtonSize.small,
        ),
      );
    }
    if (prompt.isNotEmpty && onAction != null) {
      actions.add(
        CustomButton.secondary(
          text: context.l10n.chatGraphContinueExplain,
          onPressed: () => unawaited(onAction!(
            'prompt',
            {'prompt': prompt},
          )),
          size: CustomButtonSize.small,
        ),
      );
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: tone.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  item['node_name']?.toString() ?? '',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: DS.fontWeightSemibold,
                        color: DS.neutral900,
                      ),
                ),
              ),
              const SizedBox(width: DS.spacing8),
              _Badge(
                label: '${item['mastery']}%',
                color: tone,
                background: tone.withValues(alpha: 0.12),
              ),
            ],
          ),
          if ((item['why']?.toString() ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              item['why'].toString(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral700,
                    height: 1.4,
                  ),
            ),
          ],
          if (_listString(item['prerequisite_names']).isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.chatGraphPrerequisites(
                  _listString(item['prerequisite_names']).join('、')),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral600,
                  ),
            ),
          ],
          if (_listString(item['downstream_names']).isNotEmpty) ...[
            const SizedBox(height: DS.spacing4),
            Text(
              context.l10n.chatGraphAffectedLater(
                  _listString(item['downstream_names']).join('、')),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral600,
                  ),
            ),
          ],
          if (actions.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: actions,
            ),
          ],
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({
    required this.label,
    required this.color,
    required this.background,
  });

  final String label;
  final Color color;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: DS.borderRadius20,
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color,
              fontWeight: DS.fontWeightSemibold,
            ),
      ),
    );
  }
}

List<Map<String, dynamic>> _mapList(dynamic raw) {
  if (raw is List) {
    return raw
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
  }
  return const <Map<String, dynamic>>[];
}

List<String> _listString(dynamic raw) {
  if (raw is List) {
    return raw
        .map((item) => item.toString())
        .where((item) => item.isNotEmpty)
        .toList();
  }
  return const <String>[];
}
