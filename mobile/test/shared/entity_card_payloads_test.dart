import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

void main() {
  group('EntityCardPayload', () {
    test('parses unified task entity payload', () {
      final payload = EntityCardPayload.fromRaw(
        {
          'entity_card': {
            'entity_type': 'task',
            'entity_id': 'task-1',
            'title': '复习积分',
            'summary': '完成 3 道典型题',
            'feedback': {
              'tool_result_id': 'tool-1',
              'confirmation_required': true,
            },
            'share': {
              'resource_type': 'task',
              'resource_id': 'task-1',
              'title': '复习积分',
            },
            'metrics': {
              'estimated_minutes': 25,
            },
            'raw': {
              'id': 'task-1',
              'title': '复习积分',
              'type': 'learning',
              'status': 'pending',
            },
          },
        },
        fallbackType: 'task',
      );

      expect(payload.entityType, 'task');
      expect(payload.entityId, 'task-1');
      expect(payload.toolResultId, 'tool-1');
      expect(payload.share?.resourceType, 'task');
    });

    test('falls back from legacy task list payload', () {
      final payload = EntityCardPayload.fromRaw(
        {
          'tasks': [
            {
              'id': 'task-a',
              'title': '任务 A',
              'type': 'learning',
              'status': 'pending',
            },
          ],
          'plan_id': 'plan-1',
          'plan_title': '概率论计划',
          'tool_result_id': 'tool-list-1',
        },
        fallbackType: 'task_list',
      );

      expect(payload.entityType, 'task_list');
      expect(payload.planId, 'plan-1');
      expect(payload.children, hasLength(1));
      expect(payload.children.first.entityType, 'task');
    });

    test('builds task model from unified payload', () {
      final task = taskModelFromEntityPayload({
        'entity_card': {
          'entity_type': 'task',
          'entity_id': 'task-7',
          'title': '阅读一章线代',
          'summary': '做笔记并标注疑问',
          'status': 'PENDING',
          'metrics': {
            'estimated_minutes': 35,
            'priority': 2,
            'difficulty': 3,
          },
          'raw': {
            'id': 'task-7',
            'title': '阅读一章线代',
            'type': 'learning',
            'status': 'pending',
          },
        },
      });

      expect(task, isNotNull);
      expect(task!.id, 'task-7');
      expect(task.title, '阅读一章线代');
    });

    test('parses learning path entity payload with nested plan and task list',
        () {
      final payload = EntityCardPayload.fromRaw(
        {
          'entity_card': {
            'entity_type': 'learning_path',
            'entity_id': 'plan-lp-1',
            'title': '学习路径：概率论',
            'linked_entities': {'target_name': '概率论', 'plan_id': 'plan-lp-1'},
            'children': [
              {
                'entity_type': 'plan',
                'entity_id': 'plan-lp-1',
                'title': '学习路径：概率论',
              },
              {
                'entity_type': 'task_list',
                'entity_id': 'tool-1',
                'title': '2 个可执行任务',
              },
            ],
          },
        },
        fallbackType: 'learning_path',
      );

      expect(payload.entityType, 'learning_path');
      expect(payload.planId, 'plan-lp-1');
      expect(payload.children, hasLength(2));
      expect(payload.children.last.entityType, 'task_list');
    });

    test('adapts card protocol plan payload into plan card payload', () {
      final plan = PlanCardPayload.fromMap({
        'card_id': 'card-plan-1',
        'card_type': 'PLAN',
        'lifecycle_status': 'ACTIVE',
        'tags': ['growth'],
        'metadata': {
          'legacy_plan_id': 'plan-1',
          'name': '概率论冲刺',
          'description': '7 天复习',
          'plan_kind': 'GROWTH',
          'subject': '概率论',
          'progress': 0.42,
        },
      });

      expect(plan.cardId, 'card-plan-1');
      expect(plan.id, 'plan-1');
      expect(plan.title, '概率论冲刺');
      expect(plan.type, 'growth');
      expect(plan.subject, '概率论');
      expect(plan.progress, 0.42);
    });

    test('adapts card protocol task payload into legacy task model', () {
      final task = taskModelFromEntityPayload({
        'card_id': 'card-task-1',
        'card_type': 'TASK',
        'lifecycle_status': 'ACTIVE',
        'tags': ['day:1'],
        'metadata': {
          'legacy_task_id': 'task-1',
          'legacy_plan_id': 'plan-1',
          'title': '闭卷复述贝叶斯公式',
          'task_kind': 'learning',
          'effort_minutes_default': 35,
          'difficulty': 3,
          'energy_cost': 2,
        },
      });

      expect(task, isNotNull);
      expect(task!.id, 'task-1');
      expect(task.planId, 'plan-1');
      expect(task.title, '闭卷复述贝叶斯公式');
      expect(task.estimatedMinutes, 35);
      expect(task.status, TaskStatus.pending);
    });

    test('fallback review card carries a routable primary action', () {
      final payload = EntityCardPayload.fromRaw(
        {
          'review_id': 'review-1',
          'title': '今天复盘条件概率',
          'plan_id': 'plan-1',
          'subject': 'math',
          'score': 0.72,
        },
        fallbackType: 'review',
      );

      expect(payload.entityType, 'review');
      expect(payload.entityId, 'review-1');
      expect(payload.detailRoute, contains('/review?'));
      expect(payload.detailRoute, contains('mode=today'));
      expect(payload.share?.resourceType, 'review');
    });

    test('fallback vocabulary card opens lookup and wordbook actions', () {
      final payload = EntityCardPayload.fromRaw(
        {
          'word_id': 'word-1',
          'word': 'derive',
          'definition': 'to obtain from a source',
          'in_wordbook': true,
        },
        fallbackType: 'vocabulary',
      );

      expect(payload.entityType, 'vocabulary');
      expect(payload.entityId, 'word-1');
      expect(payload.detailRoute, '/tools/vocabulary_lookup?word=derive');
      expect(payload.secondaryActions.single.route, '/tools/wordbook');
      expect(payload.share?.resourceType, 'vocabulary');
    });

    test('fallback seed card remains adoptable', () {
      final seed = EntityCardPayload.fromRaw(
        {
          'library_id': 'seed-1',
          'name': '概率论高频错题种子',
          'description': '可生成复盘任务的题型包',
        },
        fallbackType: 'seed',
      );

      expect(seed.detailRoute, '/seed-libraries/seed-1');
      expect(seed.secondaryActions.first.type, 'adopt_resource');
      expect(seed.share?.resourceType, 'seed');
    });

    test('parses first-class shared resource protocol fields', () {
      final payload = EntityCardPayload.fromRaw(
        {
          'entity_card': {
            'entity_type': 'shared_resource',
            'entity_id': 'share-1',
            'title': '概率论复习计划',
            'execution_state': 'available',
            'share': {
              'resource_type': 'plan',
              'resource_id': 'plan-1',
              'title': '概率论复习计划',
              'owner': {'user_id': 'user-1', 'display_name': 'Ada'},
              'visibility': 'group',
              'preview': {'title': '概率论复习计划'},
              'source_receipt': {
                'shared_resource_id': 'share-1',
                'channel': 'community_share',
              },
              'adoption_action': {
                'id': 'adopt_shared_resource',
                'type': 'adopt_resource',
                'route': '/community/shared-resources/share-1/adopt',
                'label': '采纳到我的空间',
                'payload': {'shared_resource_id': 'share-1'},
              },
              'expires_at': '2026-05-03T12:00:00Z',
              'availability': 'available',
            },
          },
        },
        fallbackType: 'shared_resource',
      );

      expect(payload.share?.resourceType, 'plan');
      expect(payload.share?.owner['display_name'], 'Ada');
      expect(payload.share?.visibility, 'group');
      expect(payload.share?.sourceReceipt['shared_resource_id'], 'share-1');
      expect(
        payload.share?.adoptionAction?.route,
        '/community/shared-resources/share-1/adopt',
      );
      expect(payload.share?.availability, 'available');
      expect(payload.share?.expiresAt, isNotNull);
    });

    test('legacy revoked shared resource hides adoption action', () {
      final payload = EntityCardPayload.fromRaw(
        {
          'id': 'share-2',
          'resource_type': 'task',
          'resource_id': 'task-2',
          'resource_title': '过期任务',
          'availability': 'revoked',
          'revoked_at': '2026-05-02T09:00:00Z',
        },
        fallbackType: 'shared_resource',
      );

      expect(payload.executionState, 'revoked');
      expect(payload.secondaryActions, isEmpty);
      expect(payload.share?.availability, 'revoked');
      expect(payload.share?.revokedAt, isNotNull);
    });
  });
}
