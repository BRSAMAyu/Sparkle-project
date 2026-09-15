import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/openclaw_automation_service.dart';

void main() {
  group('OpenClawAutomationService', () {
    test('loads schedules and stores latest batch summary', () async {
      final service = OpenClawAutomationService(
        schedulesLoader: () async => <Map<String, dynamic>>[
          <String, dynamic>{
            'id': 'schedule-1',
            'user_id': 'user-1',
            'task_id': 'task-1',
            'intent_template': <String, dynamic>{'goal': '每日检查通知'},
            'trigger_type': 'cron',
            'trigger_config': <String, dynamic>{'cron': '00 08 * * *'},
            'is_active': true,
          },
        ],
        scheduleCreator: (payload) async => <String, dynamic>{
          'id': 'schedule-2',
          'user_id': 'user-1',
          ...payload,
        },
        schedulePauser: (scheduleId) async => <String, dynamic>{
          'id': scheduleId,
          'user_id': 'user-1',
          'task_id': 'task-1',
          'intent_template': <String, dynamic>{},
          'trigger_type': 'cron',
          'trigger_config': <String, dynamic>{'cron': '00 08 * * *'},
          'is_active': false,
        },
        scheduleResumer: (scheduleId) async => <String, dynamic>{
          'id': scheduleId,
          'user_id': 'user-1',
          'task_id': 'task-1',
          'intent_template': <String, dynamic>{},
          'trigger_type': 'cron',
          'trigger_config': <String, dynamic>{'cron': '00 08 * * *'},
          'is_active': true,
        },
        scheduleDeleter: (_) async {},
        taskBatchHandoff: (taskIds, executionStrategy) async => <String, dynamic>{
          'batch_id': 'batch-1',
          'status': 'completed',
          'requested_strategy': executionStrategy,
          'resolved_strategy': 'sequential',
          'task_ids': taskIds,
          'intent_ids': const <String>['intent-1'],
          'completed_count': taskIds.length,
          'failed_count': 0,
          'queued_count': 0,
          'items': <Map<String, dynamic>>[
            <String, dynamic>{
              'intent_id': 'intent-1',
              'task_id': taskIds.first,
              'status': 'succeeded',
            },
          ],
        },
      );

      await service.initialize();
      final ok = await service.handoffTaskBatch(const <String>['task-1', 'task-2']);

      expect(service.schedules, hasLength(1));
      expect(ok, isTrue);
      expect(service.latestBatch?.batchId, 'batch-1');
      expect(service.latestBatch?.completedCount, 2);
    });
  });
}
