import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

void main() {
  test(
      'GalaxyGraphResponse parses backend galaxy payload with relations and stable coordinates',
      () {
    final response = GalaxyGraphResponse.fromJson({
      'nodes': [
        {
          'id': 'node-1',
          'name': 'Calculus',
          'importance_level': 4,
          'sector_code': 'TECH',
          'base_color': '#5AB8CC',
          'is_seed': true,
          'parent_id': null,
          'description': 'Limits and derivatives',
          'tags': ['math', 'calculus', 'core'],
          'position_x': 128.5,
          'position_y': -64.25,
          'user_status': {
            'is_unlocked': true,
            'mastery_score': 76,
            'study_count': 9,
            'recent_error_count': 2,
            'review_urgency_score': 0.81,
            'is_review_recommended': true,
            'review_urgency_reason': 'review_window',
            'mastery_last_updated_at': '2026-04-18T09:30:00Z',
            'days_since_mastery_update': 7.0,
            'first_unlock_at': '2026-03-20T09:30:00Z',
          },
        },
      ],
      'relations': [
        {
          'source_node_id': 'node-1',
          'target_node_id': 'node-2',
          'relation_type': 'prerequisite',
          'strength': 0.9,
        },
      ],
    });

    expect(response.nodes, hasLength(1));
    expect(response.edges, hasLength(1));

    final node = response.nodes.first;
    expect(node.importance, 4);
    expect(node.baseColor, '#5AB8CC');
    expect(node.isUnlocked, isTrue);
    expect(node.masteryScore, 76);
    expect(node.studyCount, 9);
    expect(node.recentErrorCount, 2);
    expect(node.reviewUrgencyScore, 0.81);
    expect(node.isReviewRecommended, isTrue);
    expect(node.reviewUrgencyReason, 'review_window');
    expect(
      node.masteryLastUpdatedAt,
      DateTime.parse('2026-04-18T09:30:00Z'),
    );
    expect(node.daysSinceMasteryUpdate, 7.0);
    expect(node.shouldPulseForReview, isTrue);
    expect(node.firstUnlockAt, DateTime.parse('2026-03-20T09:30:00Z'));
    expect(node.positionX, 128.5);
    expect(node.positionY, -64.25);
    expect(node.hasStablePosition, isTrue);
    expect(node.autoTags, containsAll(['math', 'calculus', 'core']));

    final edge = response.edges.first;
    expect(edge.sourceId, 'node-1');
    expect(edge.targetId, 'node-2');
    expect(edge.relationType, EdgeRelationType.prerequisite);
    expect(edge.id, contains('node-1_node-2'));
  });
}
