import 'package:flutter/material.dart';
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
      'helperText': _helperFor(currentPhase),
    };
  }

  static String _helperFor(String phase) {
    switch (phase.toUpperCase()) {
      case 'FORETHOUGHT':
        return '当前更适合把目标、步骤和节奏先说清楚。';
      case 'PERFORMANCE':
        return '当前更适合维持执行节奏，减少额外切换。';
      case 'SELF_REFLECTION':
        return '当前更适合回看阻力、复盘并准备下一轮。';
      default:
        return '当前阶段信息不足，先保持默认支持方式。';
    }
  }

  String get _label {
    switch (phase.toUpperCase()) {
      case 'FORETHOUGHT':
        return 'SRL · 规划中';
      case 'PERFORMANCE':
        return 'SRL · 执行中';
      case 'SELF_REFLECTION':
        return 'SRL · 复盘中';
      default:
        return 'SRL · 未知';
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
                _label,
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
