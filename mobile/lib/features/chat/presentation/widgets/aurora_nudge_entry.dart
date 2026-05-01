import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/aurora/data/models/aurora_core_session.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_core_session_sheet.dart';

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
    final ctaLabel =
        data['cta_label']?.toString() ?? context.l10n.chatNudgeStartReview;
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
            child: Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                FilledButton.tonal(
                  onPressed: onWidgetAction == null || debriefContext.isEmpty
                      ? null
                      : () => unawaited(
                            onWidgetAction!(
                              'checkpoint_debrief_start',
                              {
                                'prompt': context.l10n.chatReviewStart,
                                'debrief_context': debriefContext,
                              },
                            ),
                          ),
                  child: Text(ctaLabel),
                ),
                TextButton.icon(
                  onPressed: () => unawaited(
                    showAuroraCoreSession(
                      context: context,
                      bandStatus: 'calibration_available',
                      wakeReasons: const ['checkpoint_due'],
                      entryReason: AuroraCoreSessionEntryReason(
                        triggerSource: 'checkpoint_card',
                        observedSignals: [description],
                        suggestedAgendaPreview: const [
                          '确认 checkpoint 进度差异',
                          '校准接下来的计划节奏',
                        ],
                        whyNow: context.l10n.auroraCheckpointWhyNow,
                        estimatedMinutes: 4,
                      ),
                      scope: description.isNotEmpty ? description : null,
                      sessionType: 'strategy_recalibration',
                    ),
                  ),
                  icon: const Icon(Icons.auto_fix_high_rounded, size: 16),
                  label: Text(context.l10n.auroraCoreCheckpointCta),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
