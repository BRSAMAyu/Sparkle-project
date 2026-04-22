import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/user_state_models.dart';

void main() {
  test('UserStateV1Model falls back to top-level metacognition payload', () {
    final model = UserStateV1Model.fromProfileContext({
      'metacognition_profile': {
        'items': [
          {
            'dim': 'time_estimation_bias',
            'sample_size': 6,
            'bias_mean': -0.8,
            'trend': 'stable',
          },
        ],
      },
    });

    expect(model.metacognitionProfile, isNotNull);
    expect(model.metacognitionProfile?.value.items.single.dim,
        'time_estimation_bias');
  });
}
