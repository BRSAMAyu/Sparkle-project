import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/user_state_models.dart';

void main() {
  test('UserStateV1Model preserves backend-only envelopes for declared fields',
      () {
    final model = UserStateV1Model.fromJson({
      'commitment_summary': {
        'value': {
          'overdue_count': 1,
          'pending_commitment_ids': ['c1'],
        },
      },
      'task_sufficiency_summary': {
        'value': {
          'score': 0.4,
          'top_missing_dimensions': ['deadline'],
        },
      },
      'calendar_context': {
        'value': {
          'workload_density': 'medium',
        },
      },
    });

    expect(model.commitmentSummary?.value['overdue_count'], 1);
    expect(
      model.taskSufficiencySummary?.value['top_missing_dimensions'],
      ['deadline'],
    );
    expect(model.calendarContext?.value['workload_density'], 'medium');
  });
}
