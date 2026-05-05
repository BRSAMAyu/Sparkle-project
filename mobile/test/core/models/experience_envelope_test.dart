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
        envelope.structuredCognitiveAdjustments.single['target'], 'task_size');
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
}
