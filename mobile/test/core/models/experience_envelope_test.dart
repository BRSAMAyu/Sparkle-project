import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/experience_envelope.dart';

void main() {
  test('parses user state and structured adjustments from metadata', () {
    final envelope = ExperienceEnvelope.fromMetadata({
      'trace_id': 'trace_1',
      'turn_id': 'turn_7',
      'profile_context': {
        'user_state_v1': {'fatigue_level': 'high'},
      },
      'structured_cognitive_adjustments': [
        {'target': 'task_size', 'value': 'smaller'},
      ],
    });

    expect(envelope.traceId, 'trace_1');
    expect(envelope.turnId, 'turn_7');
    expect(envelope.userState['fatigue_level'], 'high');
    expect(
      envelope.structuredCognitiveAdjustments.single['target'],
      'task_size',
    );
  });

  test('merge preserves previous state when next envelope omits adjustments',
      () {
    final first = ExperienceEnvelope.fromMetadata({
      'user_state_v1': {'stress': 'medium'},
      'structured_cognitive_adjustments': [
        {'target': 'tone', 'value': 'gentle'},
      ],
    });
    final second = ExperienceEnvelope.fromMetadata({
      'user_state_v1': {'fatigue': 'low'},
    });

    final merged = first.merge(second);

    expect(merged.userState['stress'], 'medium');
    expect(merged.userState['fatigue'], 'low');
    expect(merged.structuredCognitiveAdjustments.single['target'], 'tone');
  });

  test('parses dual core mode and belief summary from ux_turn', () {
    final envelope = ExperienceEnvelope.fromMetadata({
      'ux_turn': {
        'dual_core_mode': 'cognitive',
        'mode_reason': '负荷偏高',
        'belief_summary': {
          'label': 'Sparkle 感觉你现在可能负荷偏高。',
          'target': 'cognitive_load',
          'confidence': 0.83,
          'correction_options': [
            {'key': 'ready_to_execute', 'label': '我现在可以直接做'},
          ],
        },
      },
    });

    expect(envelope.dualCoreMode, 'cognitive');
    expect(envelope.modeReason, '负荷偏高');
    expect(envelope.hasBeliefSummary, isTrue);
    expect(envelope.beliefSummary['target'], 'cognitive_load');
    expect(envelope.isEmpty, isFalse);
  });
}
