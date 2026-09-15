import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class PlanStrategyCard extends StatefulWidget {
  const PlanStrategyCard({
    required this.data,
    this.onWidgetAction,
    super.key,
  });

  final Map<String, dynamic> data;
  final Future<void> Function(String actionType, Map<String, dynamic> payload)?
      onWidgetAction;

  @override
  State<PlanStrategyCard> createState() => _PlanStrategyCardState();
}

class _PlanStrategyCardState extends State<PlanStrategyCard> {
  final Set<int> _expandedPhases = <int>{};

  @override
  Widget build(BuildContext context) {
    final strategy = Map<String, dynamic>.from(
      widget.data['strategy'] as Map? ?? const {},
    );
    final phases = (strategy['phases'] as List<dynamic>? ?? const [])
        .whereType<Map<dynamic, dynamic>>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
    final checkpoints = (strategy['checkpoints'] as List<dynamic>? ?? const [])
        .whereType<Map<dynamic, dynamic>>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
    final actions = (widget.data['actions'] as List<dynamic>? ?? const [])
        .whereType<Map<dynamic, dynamic>>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.l10n.chatStrategySuggestPace,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
        ),
        const SizedBox(height: DS.spacing12),
        ...List.generate(phases.length, (index) {
          final phase = phases[index];
          final isExpanded = _expandedPhases.contains(index);
          return Container(
            margin: const EdgeInsets.only(bottom: DS.spacing10),
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.surfaceSecondary,
              borderRadius: DS.borderRadius12,
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${phase['label'] ?? context.l10n.chatStrategyPhaseLabel} · ${phase['days'] ?? ''}',
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                          ),
                          const SizedBox(height: DS.spacing4),
                          Text(
                            context.l10n.chatStrategyDailyHours(
                                '${phase['daily_hours'] ?? '-'}',
                                '${phase['focus'] ?? ''}'),
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(color: DS.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    TextButton(
                      onPressed: () {
                        setState(() {
                          if (isExpanded) {
                            _expandedPhases.remove(index);
                          } else {
                            _expandedPhases.add(index);
                          }
                        });
                      },
                      child: Text(isExpanded
                          ? context.l10n.chatStrategyCollapse
                          : context.l10n.chatStrategyExpand),
                    ),
                  ],
                ),
                if (isExpanded) ...[
                  const SizedBox(height: DS.spacing10),
                  Text(
                    context.l10n
                        .chatStrategyMethod(phase['method']?.toString() ?? ''),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textPrimary,
                          height: 1.45,
                        ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    context.l10n.chatStrategyPhaseOutput(
                        phase['output']?.toString() ?? ''),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                  ),
                ],
              ],
            ),
          );
        }),
        if (checkpoints.isNotEmpty) ...[
          const SizedBox(height: DS.spacing4),
          Text(
            context.l10n.chatStrategyCheckpoint,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          ...checkpoints.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing6),
              child: Text(
                'Day ${item['day'] ?? '-'} · ${item['description'] ?? ''}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ),
          ),
        ],
        if (actions.isNotEmpty) ...[
          const SizedBox(height: DS.spacing16),
          Row(
            children: actions.take(2).map((action) {
              final type = action['type']?.toString() ?? '';
              final label = action['label']?.toString() ??
                  context.l10n.chatStrategyContinue;
              return Expanded(
                child: Padding(
                  padding: EdgeInsets.only(
                    right: action == actions.first ? DS.spacing8 : 0,
                  ),
                  child: FilledButton.tonal(
                    onPressed: widget.onWidgetAction == null || type.isEmpty
                        ? null
                        : () => unawaited(
                              widget.onWidgetAction!(
                                type,
                                action,
                              ),
                            ),
                    child: Text(label),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ],
    );
  }
}
