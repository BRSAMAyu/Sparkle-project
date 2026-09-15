import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/home/data/models/prediction_insight_data.dart';

void main() {
  test('PredictionInsightData parses unified prediction payload', () {
    final result = PredictionInsightData.fromJson({
      'prediction_id': 'pred-1',
      'horizon': 'realtime',
      'title': '系统预测你想继续推进当前任务',
      'summary': '继续承接这件事最省力。',
      'confidence': 0.81,
      'predicted_action_type': 'resume_priority_task',
      'predicted_window': 'now',
      'reasons': ['当前仍有重点待办'],
      'suggested_prompt': '帮我继续推进今天的重点任务',
      'prediction_source': 'free_fast',
      'prediction_tier': 'glm-4.7-flash',
      'fallback_used': false,
      'explanations': {
        'recent_24h': ['最近24小时保持活跃'],
        'plan': ['当前仍有重点待办'],
      },
      'recommended_actions': [
        {
          'id': 'pred-1:primary',
          'label': '继续重点任务',
          'action_type': 'resume_priority_task',
          'target_route': '/chat',
          'suggested_prompt': '帮我继续推进今天的重点任务',
        },
      ],
      'tracking': {
        'candidate_id': 'pred-1',
        'action_type': 'resume_priority_task',
      },
      'entity_card': {
        'entity_type': 'prediction',
        'entity_id': 'pred-1',
        'title': '系统预测你想继续推进当前任务',
        'summary': '继续承接这件事最省力。',
      },
      'generated_at': '2026-03-20T12:00:00Z',
    });

    expect(result.predictionId, 'pred-1');
    expect(result.horizon, 'realtime');
    expect(result.recommendedActions.single.label, '继续重点任务');
    expect(result.allExplanationLines, contains('最近24小时保持活跃'));
    expect(result.trackingCandidateId, 'pred-1');
    expect(result.entityCard?.entityType, 'prediction');
  });
}
