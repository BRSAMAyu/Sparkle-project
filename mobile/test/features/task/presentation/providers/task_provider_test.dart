import 'package:flutter_test/flutter_test.dart';

import 'package:sparkle/features/task/data/models/execution_record_model.dart';
import 'package:sparkle/features/task/data/models/execution_template_model.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
import 'package:sparkle/features/task/data/models/next_action.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

void main() {
  // Initialize Flutter test bindings
  TestWidgetsFlutterBinding.ensureInitialized();

  group('TaskProvider Tests', () {
    group('Initial State', () {
      test('should start with default state', () {
        final state = TaskListState();

        expect(state.isLoading, isFalse);
        expect(state.tasks, isEmpty);
        expect(state.todayTasks, isEmpty);
        expect(state.recommendedTasks, isEmpty);
        expect(state.error, isNull);
      });

      test('should have empty task executions initially', () {
        final state = TaskListState();

        expect(state.taskExecutions, isEmpty);
        expect(state.taskExecutionRecords, isEmpty);
        expect(state.taskExecutionTemplates, isEmpty);
      });
    });

    group('State Management', () {
      test('should update loading state', () {
        final state = TaskListState().copyWith(isLoading: true);

        expect(state.isLoading, isTrue);
      });

      test('should update tasks list', () {
        final newTasks = [
          TaskModel(
            id: 'task-1',
            userId: 'user-1',
            title: 'Task 1',
            type: TaskType.learning,
            tags: ['study'],
            estimatedMinutes: 30,
            difficulty: 3,
            energyCost: 2,
            status: TaskStatus.pending,
            priority: 2,
            createdAt: DateTime.now(),
            updatedAt: DateTime.now(),
          ),
          TaskModel(
            id: 'task-2',
            userId: 'user-1',
            title: 'Task 2',
            type: TaskType.training,
            tags: ['practice'],
            estimatedMinutes: 45,
            difficulty: 2,
            energyCost: 1,
            status: TaskStatus.inProgress,
            priority: 1,
            createdAt: DateTime.now(),
            updatedAt: DateTime.now(),
          ),
        ];

        final state = TaskListState().copyWith(tasks: newTasks);

        expect(state.tasks.length, equals(2));
        expect(state.tasks[0].id, equals('task-1'));
        expect(state.tasks[1].id, equals('task-2'));
      });

      test('should update today tasks', () {
        final todayTasks = [
          TaskModel(
            id: 'task-today',
            userId: 'user-1',
            title: 'Today Task',
            type: TaskType.learning,
            tags: ['study'],
            estimatedMinutes: 30,
            difficulty: 3,
            energyCost: 2,
            status: TaskStatus.pending,
            priority: 2,
            dueDate: DateTime.now(),
            createdAt: DateTime.now(),
            updatedAt: DateTime.now(),
          ),
        ];

        final state = TaskListState().copyWith(todayTasks: todayTasks);

        expect(state.todayTasks.length, equals(1));
        expect(state.todayTasks.first.id, equals('task-today'));
      });

      test('should update error state', () {
        final state = TaskListState().copyWith(error: 'Test error');

        expect(state.error, equals('Test error'));
      });

      test('should clear error state', () {
        final state1 = TaskListState().copyWith(error: 'Some error');
        expect(state1.error, isNotNull);

        final state2 = state1.copyWith(clearError: true);
        expect(state2.error, isNull);
      });

      test('should update handoff in-flight state', () {
        final handoffSet = <String>{'task-1', 'task-2'};
        final state = TaskListState().copyWith(handoffInFlight: handoffSet);

        expect(state.handoffInFlight.contains('task-1'), isTrue);
        expect(state.handoffInFlight.contains('task-2'), isTrue);
        expect(state.handoffInFlight.length, equals(2));
      });

      test('should update execution decision in-flight state', () {
        final decisionSet = <String>{'task-1'};
        final state = TaskListState().copyWith(executionDecisionInFlight: decisionSet);

        expect(state.executionDecisionInFlight.contains('task-1'), isTrue);
      });

      test('should update task executions', () {
        final executions = {
          'task-1': ExecutionIntentModel(
            id: 'intent-1',
            taskId: 'task-1',
            executionMode: ExecutionMode.agent,
            executor: 'system',
            status: ExecutionIntentStatus.running,
            trustLevel: ExecutionTrustLevel.raw,
            goal: 'Complete task',
          ),
        };

        final state = TaskListState().copyWith(taskExecutions: executions);

        expect(state.taskExecutions['task-1']?.id, equals('intent-1'));
        expect(state.taskExecutions['task-1']?.status, equals(ExecutionIntentStatus.running));
      });

      test('should update task execution records', () {
        final records = {
          'task-1': ExecutionRecordModel(
            id: 'record-1',
            executionIntentId: 'intent-1',
            trustLevel: 'validated',
            artifacts: [],
            toolCallsCount: 5,
          ),
        };

        final state = TaskListState().copyWith(taskExecutionRecords: records);

        expect(state.taskExecutionRecords['task-1']?.id, equals('record-1'));
        expect(state.taskExecutionRecords['task-1']?.toolCallsCount, equals(5));
      });

      test('should update task execution templates', () {
        final templates = {
          'task-1': [
            ExecutionTemplateModel(
              templateId: 'template-1',
              name: 'Standard Template',
              description: 'Default execution template',
              executionMode: ExecutionMode.human,
              targetEnv: 'local',
              matchScore: 1.0,
              matchReasons: ['Task is simple'],
            ),
          ],
        };

        final state = TaskListState().copyWith(taskExecutionTemplates: templates);

        expect(state.taskExecutionTemplates['task-1']?.length, equals(1));
        expect(state.taskExecutionTemplates['task-1']?.first.templateId, equals('template-1'));
      });

      test('should update selected execution template IDs', () {
        final selectedIds = {
          'task-1': 'template-1',
          'task-2': 'template-2',
        };

        final state = TaskListState().copyWith(selectedExecutionTemplateIds: selectedIds);

        expect(state.selectedExecutionTemplateIds['task-1'], equals('template-1'));
        expect(state.selectedExecutionTemplateIds['task-2'], equals('template-2'));
      });
    });

    group('Next Actions Model', () {
      test('should create NextAction with all required fields', () {
        final action = NextAction(
          type: NextActionType.quickReview,
          title: 'Quick Review',
          description: 'Review the material',
          estimatedMinutes: 5,
          energyCost: 1,
          difficulty: 1,
          reason: 'Recommended for retention',
        );

        expect(action.type, equals(NextActionType.quickReview));
        expect(action.title, equals('Quick Review'));
        expect(action.estimatedMinutes, equals(5));
        expect(action.energyCost, equals(1));
        expect(action.difficulty, equals(1));
      });

      test('should support all NextActionType values', () {
        expect(NextActionType.quickReview, isNotNull);
        expect(NextActionType.lightExpand, isNotNull);
        expect(NextActionType.practiceApply, isNotNull);
        expect(NextActionType.restBreak, isNotNull);
        expect(NextActionType.continuePlan, isNotNull);
      });
    });

    group('Execution Record Model', () {
      test('should create ExecutionRecordModel with required fields', () {
        final record = ExecutionRecordModel(
          id: 'record-1',
          executionIntentId: 'intent-1',
          trustLevel: 'raw',
          artifacts: [],
          toolCallsCount: 0,
        );

        expect(record.id, equals('record-1'));
        expect(record.executionIntentId, equals('intent-1'));
        expect(record.trustLevel, equals('raw'));
        expect(record.artifacts, isEmpty);
        expect(record.toolCallsCount, equals(0));
      });

      test('should create ExecutionRecordModel with optional fields', () {
        final record = ExecutionRecordModel(
          id: 'record-2',
          executionIntentId: 'intent-2',
          trustLevel: 'validated',
          artifacts: [
            {'type': 'output', 'content': 'result'}
          ],
          toolCallsCount: 5,
          qualityScore: 0.85,
          durationMs: 30000,
          parsedOutput: {'summary': 'Task completed successfully'},
        );

        expect(record.id, equals('record-2'));
        expect(record.toolCallsCount, equals(5));
        expect(record.qualityScore, equals(0.85));
        expect(record.trustLevel, equals('validated'));
        expect(record.durationMs, equals(30000));
      });

      test('should calculate trust label correctly', () {
        final rawRecord = ExecutionRecordModel(
          id: 'raw-rec',
          executionIntentId: 'intent-1',
          trustLevel: 'raw',
          artifacts: [],
          toolCallsCount: 0,
        );

        final validatedRecord = ExecutionRecordModel(
          id: 'validated-rec',
          executionIntentId: 'intent-2',
          trustLevel: 'validated',
          artifacts: [],
          toolCallsCount: 0,
        );

        final trustedRecord = ExecutionRecordModel(
          id: 'trusted-rec',
          executionIntentId: 'intent-3',
          trustLevel: 'trusted',
          artifacts: [],
          toolCallsCount: 0,
        );

        expect(rawRecord.trustLabel, equals('原始结果'));
        expect(validatedRecord.trustLabel, equals('已校验'));
        expect(trustedRecord.trustLabel, equals('可信结果'));
      });
    });

    group('Task Completion Result Model', () {
      test('should create TaskCompletionResult with required fields', () {
        final result = TaskCompletionResult(
          task: {
            'id': 'task-1',
            'title': 'Completed Task',
            'status': 'completed',
          },
        );

        expect(result.task['id'], equals('task-1'));
        expect(result.task['status'], equals('completed'));
        expect(result.nextActions, isEmpty);
      });

      test('should create TaskCompletionResult with optional fields', () {
        final nextActions = [
          NextAction(
            type: NextActionType.quickReview,
            title: 'Quick Review',
            description: 'Review',
            estimatedMinutes: 5,
            energyCost: 1,
            difficulty: 1,
            reason: 'Recommended',
          ),
        ];

        final result = TaskCompletionResult(
          task: {
            'id': 'task-2',
            'status': 'completed',
          },
          feedback: 'Great job!',
          nextActions: nextActions,
          unlockedAchievements: ['achievement-1'],
        );

        expect(result.feedback, equals('Great job!'));
        expect(result.nextActions.length, equals(1));
        expect(result.unlockedAchievements.length, equals(1));
      });
    });

    group('Execution Template Model', () {
      test('should create ExecutionTemplateModel with required fields', () {
        final template = ExecutionTemplateModel(
          templateId: 'template-1',
          name: 'Standard Template',
          description: 'Default execution template',
          executionMode: ExecutionMode.human,
          targetEnv: 'local',
          matchScore: 1.0,
          matchReasons: ['Simple task'],
        );

        expect(template.templateId, equals('template-1'));
        expect(template.executionMode, equals(ExecutionMode.human));
        expect(template.targetEnv, equals('local'));
      });

      test('should support all ExecutionMode values', () {
        expect(ExecutionMode.human, isNotNull);
        expect(ExecutionMode.agent, isNotNull);
        expect(ExecutionMode.hybrid, isNotNull);
        expect(ExecutionMode.unknown, isNotNull);
      });
    });

    group('Execution Intent Model', () {
      test('should support all ExecutionIntentStatus values', () {
        expect(ExecutionIntentStatus.draft, isNotNull);
        expect(ExecutionIntentStatus.ready, isNotNull);
        expect(ExecutionIntentStatus.dispatched, isNotNull);
        expect(ExecutionIntentStatus.running, isNotNull);
        expect(ExecutionIntentStatus.waitingApproval, isNotNull);
        expect(ExecutionIntentStatus.succeeded, isNotNull);
        expect(ExecutionIntentStatus.partial, isNotNull);
        expect(ExecutionIntentStatus.failed, isNotNull);
        expect(ExecutionIntentStatus.canceled, isNotNull);
        expect(ExecutionIntentStatus.timedOut, isNotNull);
        expect(ExecutionIntentStatus.handedBack, isNotNull);
        expect(ExecutionIntentStatus.unknown, isNotNull);
      });

      test('should support all ExecutionTrustLevel values', () {
        expect(ExecutionTrustLevel.raw, isNotNull);
        expect(ExecutionTrustLevel.validated, isNotNull);
        expect(ExecutionTrustLevel.trusted, isNotNull);
        expect(ExecutionTrustLevel.unknown, isNotNull);
      });

      test('should support all ExecutionMode values for intent', () {
        expect(ExecutionMode.human, isNotNull);
        expect(ExecutionMode.agent, isNotNull);
        expect(ExecutionMode.hybrid, isNotNull);
        expect(ExecutionMode.unknown, isNotNull);
      });
    });

    group('Task Model Enums', () {
      test('should support all TaskType values', () {
        expect(TaskType.learning, isNotNull);
        expect(TaskType.training, isNotNull);
        expect(TaskType.errorFix, isNotNull);
        expect(TaskType.reflection, isNotNull);
        expect(TaskType.social, isNotNull);
        expect(TaskType.planning, isNotNull);
        expect(TaskType.ocr, isNotNull);
      });

      test('should support all TaskStatus values', () {
        expect(TaskStatus.pending, isNotNull);
        expect(TaskStatus.inProgress, isNotNull);
        expect(TaskStatus.completed, isNotNull);
        expect(TaskStatus.abandoned, isNotNull);
      });

      test('should support all TaskSyncStatus values', () {
        expect(TaskSyncStatus.synced, isNotNull);
        expect(TaskSyncStatus.pending, isNotNull);
        expect(TaskSyncStatus.failed, isNotNull);
      });
    });
  });
}
