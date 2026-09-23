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

  test('GalaxyNodeModel.fromJson tolerates a missing name field (F7-10)', () {
    // 网关缓存/旧版本响应缺 name 时不应抛 TypeError，与 id 字段的
    // P1-13 防御保持一致。
    final node = GalaxyNodeModel.fromJson({
      'id': 'node-42',
      'importance_level': 2,
      'sector_code': 'TECH',
    });

    expect(node.id, 'node-42');
    expect(node.name, isEmpty);
  });

  group('sanitizeGalaxyNodeLabel（V13-RETEST 星图节点标签 raw ID 泄漏）', () {
    test('V13 实测的三类泄漏形态被清洗', () {
      // 复测 21 相邻帧：前缀含短 hash 的复合名 → 取冒号后的人类标题。
      expect(
        sanitizeGalaxyNodeLabel('验证专题2-83ffe1: 真题演练'),
        '真题演练',
      );
      // 复测：「专题6-2-462e51: …」→ 标题（保留章节号「专题6-2」结构）。
      expect(
        sanitizeGalaxyNodeLabel('专题6-2-462e51: 错因回看'),
        '错因回看',
      );
      // 无冒号的尾缀 ID 片段 → 剥离片段本身。
      expect(sanitizeGalaxyNodeLabel('专题6-2-462e51'), '专题6-2');
      // 复测：近乎全 ID 的名字清洗后无字母/汉字 → 诚实回退原名。
      expect(
        sanitizeGalaxyNodeLabel('d91d5df0-9-dd0bad'),
        'd91d5df0-9-dd0bad',
      );
    });

    test('正常业务名零改动（防误伤回归钉）', () {
      expect(sanitizeGalaxyNodeLabel('离散数学'), '离散数学');
      // 章节号短数字不是 hex 片段。
      expect(sanitizeGalaxyNodeLabel('专题6-2'), '专题6-2');
      // 全字母英文词（hex 字符组成但无数字）不是 ID。
      expect(sanitizeGalaxyNodeLabel('decade'), 'decade');
      expect(sanitizeGalaxyNodeLabel('facade 原则'), 'facade 原则');
      // 「12」太短，不构成 ID 片段，整名保留。
      expect(sanitizeGalaxyNodeLabel('Chapter 12: Graph Theory'),
          'Chapter 12: Graph Theory');
      expect(sanitizeGalaxyNodeLabel('  带空白的标题  '), '带空白的标题');
      expect(sanitizeGalaxyNodeLabel(''), '');
    });

    test('GalaxyNodeModel.fromJson 在解析单点应用清洗', () {
      final node = GalaxyNodeModel.fromJson({
        'id': 'node-leak',
        'name': '验证专题2-83ffe1: 真题演练',
        'importance_level': 3,
        'sector_code': 'LIFE',
      });
      expect(node.name, '真题演练');
    });
  });
}
