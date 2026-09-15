import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/design_system.dart';

class SrlPhaseBadgeCard extends StatelessWidget {
  const SrlPhaseBadgeCard({
    super.key,
    required this.phase,
    required this.helperText,
  });

  final String phase;
  final String helperText;

  static Map<String, String>? fromProfileContext(
    BuildContext context,
    Map<String, dynamic> profileContext,
  ) {
    final userInsightState =
        profileContext['user_insight_state'] as Map<String, dynamic>? ?? const {};
    final srlPhase = userInsightState['srl_phase'] as Map<String, dynamic>? ?? const {};
    final currentPhase = srlPhase['current_phase']?.toString() ?? '';
    if (currentPhase.isEmpty || currentPhase.toUpperCase() == 'UNKNOWN') {
      return null;
    }
    return {
      'phase': currentPhase,
      'helperText': _helperFor(context, currentPhase),
    };
  }

  static String _helperFor(BuildContext context, String phase) {
    switch (phase.toUpperCase()) {
      case 'FORETHOUGHT':
        return context.l10n.userSRLPlanHint;
      case 'PERFORMANCE':
        return context.l10n.userSRLEnforceHint;
      case 'SELF_REFLECTION':
        return context.l10n.userSRLReflectHint;
      default:
        return context.l10n.userSRLUnknownHint;
    }
  }

  String _label(BuildContext context) {
    switch (phase.toUpperCase()) {
      case 'FORETHOUGHT':
        return context.l10n.userSRLPlanning;
      case 'PERFORMANCE':
        return context.l10n.userSRLEnforcing;
      case 'SELF_REFLECTION':
        return context.l10n.userSRLReflecting;
      default:
        return context.l10n.userSRLUnknown;
    }
  }

  Color _color(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    switch (phase.toUpperCase()) {
      case 'FORETHOUGHT':
        return scheme.primary;
      case 'PERFORMANCE':
        return scheme.tertiary;
      case 'SELF_REFLECTION':
        return scheme.secondary;
      default:
        return scheme.outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _color(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                _label(context),
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: color,
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
            ),
            const SizedBox(height: 10),
            Text(
              helperText,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}
