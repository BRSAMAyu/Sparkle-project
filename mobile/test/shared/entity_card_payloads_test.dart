import 'package:flutter_test/flutter_test.dart';
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
  });
}
