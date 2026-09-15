import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/aurora/data/models/aurora_core_session.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_core_session_sheet.dart';

class TaskStuckCard extends StatelessWidget {
  const TaskStuckCard({
    required this.data,
    this.onWidgetAction,
    super.key,
  });

  final Map<String, dynamic> data;
  final Future<void> Function(String actionType, Map<String, dynamic> payload)?
      onWidgetAction;

  @override
  Widget build(BuildContext context) {
    final interventionId = data['intervention_id']?.toString() ?? '';
    final message =
        data['message']?.toString().trim() ?? context.l10n.stuckHelpTitle;
    final pattern = data['observed_pattern']?.toString().trim() ?? '';
    final taskTitles = (data['task_titles'] as List<dynamic>? ?? const [])
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .take(3)
        .toList();

    return Semantics(
      container: true,
      label: message,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            message,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.textPrimary,
                  height: 1.45,
                ),
          ),
          if (taskTitles.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing6,
              runSpacing: DS.spacing6,
              children: [
                for (final title in taskTitles) _QuietChip(label: title),
              ],
            ),
          ],
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              FilledButton.icon(
                onPressed: () => _startLightSession(
                  context,
                  interventionId: interventionId,
                  message: message,
                  pattern: pattern,
                ),
                icon: const Icon(Icons.auto_fix_high_rounded, size: 16),
                label: Text(context.l10n.stuckHelpChatWithSparkle),
              ),
              OutlinedButton(
                onPressed: interventionId.isEmpty
                    ? null
                    : () => unawaited(_sendFeedback(
                          action: 'snoozed',
                          interventionId: interventionId,
                          extra: const {'snooze_hours': 24},
                        )),
                child: Text(context.l10n.interventionLater),
              ),
              TextButton(
                onPressed: interventionId.isEmpty
                    ? null
                    : () => unawaited(_sendFeedback(
                          action: 'dismissed',
                          interventionId: interventionId,
                        )),
                child: Text(context.l10n.chatNotNeeded),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _sendFeedback({
    required String action,
    required String interventionId,
    Map<String, dynamic> extra = const {},
  }) async {
    await onWidgetAction?.call(
      'intervention_feedback',
      {
        'intervention_id': interventionId,
        'feedback_action': action,
        'message': '',
        ...extra,
      },
    );
  }

  void _startLightSession(
    BuildContext context, {
    required String interventionId,
    required String message,
    required String pattern,
  }) {
    if (interventionId.isNotEmpty) {
      unawaited(_sendFeedback(
        action: 'accepted',
        interventionId: interventionId,
      ));
    }
    final microSession = data['micro_session'] is Map
        ? Map<String, dynamic>.from(data['micro_session'] as Map)
        : const <String, dynamic>{};
    final entryRaw = microSession['entry_reason'] is Map
        ? Map<String, dynamic>.from(microSession['entry_reason'] as Map)
        : const <String, dynamic>{};
    unawaited(showAuroraCoreSession(
      context: context,
      bandStatus: 'calibration_available',
      wakeReasons: const ['task_stuck_pattern'],
      entryReason: entryRaw.isNotEmpty
          ? AuroraCoreSessionEntryReason.fromJson(entryRaw)
          : AuroraCoreSessionEntryReason(
              triggerSource: 'task_stuck_card',
              observedSignals: [pattern.isNotEmpty ? pattern : message],
              suggestedAgendaPreview: [
                context.l10n.chatAgendaConfirmTaskBlockCause,
                context.l10n.chatAgendaAdjustNextTaskEasier,
              ],
              whyNow: context.l10n.auroraTaskStuckWhyNow,
              estimatedMinutes: 2,
            ),
      scope: pattern.isNotEmpty ? pattern : message,
      sessionType: 'task_stuck_light',
    ));
  }
}

class _QuietChip extends StatelessWidget {
  const _QuietChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(maxWidth: 220),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary.withValues(alpha: 0.7),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
      );
}
