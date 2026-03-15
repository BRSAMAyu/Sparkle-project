import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class OrchestrationTracePanel extends StatefulWidget {
  const OrchestrationTracePanel({
    required this.traceData,
    super.key,
  });

  final Map<String, dynamic> traceData;

  @override
  State<OrchestrationTracePanel> createState() => _OrchestrationTracePanelState();
}

class _OrchestrationTracePanelState extends State<OrchestrationTracePanel> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final steps = (widget.traceData['steps'] as List<dynamic>?)
            ?.whereType<Map<String, dynamic>>()
            .toList() ??
        [];
    if (steps.isEmpty) {
      return const SizedBox.shrink();
    }

    final titleStyle = Theme.of(context).textTheme.titleSmall;
    final bodyStyle = Theme.of(context).textTheme.bodySmall;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8),
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: ExpansionTile(
        key: PageStorageKey<String>('orchestration_trace_${widget.hashCode}'),
        initiallyExpanded: _expanded,
        onExpansionChanged: (value) => setState(() => _expanded = value),
        title: Text(context.l10n.chatOrchestrationTraceTitle, style: titleStyle),
        children: [
          Padding(
            padding: const EdgeInsets.only(
              left: DS.md,
              right: DS.md,
              bottom: DS.md,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final step in steps)
                  Padding(
                    padding: const EdgeInsets.only(bottom: DS.sm),
                    child: _TraceStepTile(
                      label: step['label']?.toString() ?? '',
                      decision: step['decision']?.toString() ?? '',
                      reason: step['reason']?.toString() ?? '',
                      bodyStyle: bodyStyle,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TraceStepTile extends StatelessWidget {
  const _TraceStepTile({
    required this.label,
    required this.decision,
    required this.reason,
    required this.bodyStyle,
  });

  final String label;
  final String decision;
  final String reason;
  final TextStyle? bodyStyle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(DS.sm),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label.isNotEmpty ? label : context.l10n.chatOrchestrationTraceStep,
            style: theme.textTheme.bodyMedium,
          ),
          if (decision.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(decision, style: bodyStyle),
            ),
          if (reason.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(reason, style: bodyStyle?.copyWith(color: DS.neutral500)),
            ),
        ],
      ),
    );
  }
}
