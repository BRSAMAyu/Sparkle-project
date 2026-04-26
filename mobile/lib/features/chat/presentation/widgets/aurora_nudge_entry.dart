import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class AuroraNudgeEntry extends StatelessWidget {
  const AuroraNudgeEntry({
    required this.data,
    this.onWidgetAction,
    super.key,
  });

  final Map<String, dynamic> data;
  final Future<void> Function(String actionType, Map<String, dynamic> payload)?
      onWidgetAction;

  @override
  Widget build(BuildContext context) {
    final description = data['checkpoint_description']?.toString() ??
        data['message']?.toString() ??
        '';
    final ctaLabel = data['cta_label']?.toString() ?? '开始复盘';
    final debriefContext = Map<String, dynamic>.from(
      data['debrief_context'] as Map? ?? const {},
    );

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            description,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.textPrimary,
                  height: 1.45,
                ),
          ),
          const SizedBox(height: DS.spacing12),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton.tonal(
              onPressed: onWidgetAction == null || debriefContext.isEmpty
                  ? null
                  : () => unawaited(
                        onWidgetAction!(
                          'checkpoint_debrief_start',
                          {
                            'prompt': '我来复盘一下',
                            'debrief_context': debriefContext,
                          },
                        ),
                      ),
              child: Text(ctaLabel),
            ),
          ),
        ],
      ),
    );
  }
}
