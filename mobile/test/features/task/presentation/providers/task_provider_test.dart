import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:riverpod/riverpod.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:sparkle/features/task/data/models/execution_template_model.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

// Mock Classes
@GenerateMocks([
  TaskRepository,
])
class MockTaskRepository extends Mock implements TaskRepository {}

void main() {
  group('TaskProvider Tests', () {
    late MockTaskRepository mockRepository;
    late ProviderContainer container;
    late TaskNotifier notifier;

    setUp(() {
      mockRepository = MockTaskRepository();

      provideDummy<TaskRepository>(mockRepository);

      container = ProviderContainer(
        overrides: [
          taskRepositoryProvider.overrideWithValue(mockRepository),
        ],
      );

      notifier = container.read(taskListProvider.notifier);
    });

    tearDown(() {
      container.dispose();
    });

    group('Task State Transitions', () {
      test('should load today tasks', () async {
        final tasks = [
          TaskModel(
            id: 'task-1',
            title: 'Test Task',
            status: TaskStatus.pending,
            createdAt: DateTime.now(),
          ),
        ];

        when(mockRepository.getTodayTasks())
            .thenAnswer((_) async => tasks);

        await notifier.loadTodayTasks();

        // Verify tasks were loaded
        expect(notifier.state.todayTasks.length, equals(1));
        expect(notifier.state.todayTasks.first.id, equals('task-1'));
      });

      test('should load recommended tasks', () async {
        final tasks = [
          TaskModel(
            id: 'task-2',
            title: 'Recommended Task',
            status: TaskStatus.pending,
            createdAt: DateTime.now(),
          ),
        ];

        when(mockRepository.getRecommendedTasks())
            .thenAnswer((_) async => tasks);

        await notifier.loadRecommendedTasks();

        // Verify tasks were loaded
        expect(notifier.state.recommendedTasks.length, equals(1));
      });
    });

    group('Task Creation', () {
      test('should create new task', () async {
        final newTask = TaskModel(
          id: 'task-new',
          title: 'New Task',
          status: TaskStatus.pending,
          createdAt: DateTime.now(),
        );

        when(mockRepository.createTask(any, generateGuide: anyNamed('generateGuide')))
            .thenAnswer((_) async => newTask);
        when(mockRepository.getTasks(filters: anyNamed('filters')))
            .thenAnswer((_) async => PaginatedResponse(items: [newTask], total: 1));
        when(mockRepository.getTodayTasks())
            .thenAnswer((_) async => [newTask]);
        when(mockRepository.getRecommendedTasks())
            .thenAnswer((_) async => []);

        await notifier.createTask(
          TaskCreate(title: 'New Task'),
          generateGuide: false,
        );

        // Verify task was created
        expect(notifier.state.tasks.any((t) => t.id == 'task-new'), isTrue);
      });

      test('should generate guide for task', () async {
        final taskWithGuide = TaskModel(
          id: 'task-1',
          title: 'Task with guide',
          status: TaskStatus.pending,
          aiGuide: 'Here is your guide',
          createdAt: DateTime.now(),
        );

        when(mockRepository.generateGuide('task-1'))
            .thenAnswer((_) async => taskWithGuide);

        final result = await notifier.generateGuide('task-1');

        expect(result.aiGuide, equals('Here is your guide'));
      });
    });

    group('Task Execution Template', () {
      test('should load execution templates', () async {
        final templates = [
          ExecutionTemplateModel(
            templateId: 'tpl-1',
            title: 'Quick Start',
            description: 'Fast execution',
            steps: ['Step 1', 'Step 2'],
          ),
        ];

        when(mockRepository.listExecutionTemplates('task-1'))
            .thenAnswer((_) async => templates);

        await notifier.loadTaskExecutionTemplates('task-1');

        // Verify templates were loaded
        expect(notifier.state.taskExecutionTemplates['task-1'], isNotNull);
        expect(notifier.state.taskExecutionTemplates['task-1']!.length, equals(1));
      });

      test('should handle template selection', () async {
        final templates = [
          ExecutionTemplateModel(
            templateId: 'tpl-a',
            title: 'Option A',
            steps: [],
          ),
          ExecutionTemplateModel(
            templateId: 'tpl-b',
            title: 'Option B',
            steps: [],
          ),
        ];

        when(mockRepository.listExecutionTemplates('task-select'))
            .thenAnswer((_) async => templates);

        await notifier.loadTaskExecutionTemplates('task-select');

        // Select template A
        notifier.selectExecutionTemplate('task-select', 'tpl-a');

        // Verify selection
        expect(
          notifier.state.selectedExecutionTemplateIds['task-select'],
          equals('tpl-a'),
        );
      });
    });

    group('AI Execution', () {
      test('should load task execution state', () async {
        final executionState = ExecutionIntentModel(
          id: 'exec-1',
          status: ExecutionStatus.inProgress,
          trustLevel: 0.9,
          currentStep: 'Executing step 2',
        );

        when(mockRepository.listExecutionIntents('task-1'))
            .thenAnswer((_) async => [executionState]);

        final result = await notifier.loadTaskExecutionState('task-1');

        expect(result, isNotNull);
        expect(result!.status, equals(ExecutionStatus.inProgress));
      });

      test('should handoff task to AI', () async {
        final intent = ExecutionIntentModel(
          id: 'exec-1',
          status: ExecutionStatus.pending,
          trustLevel: 0.8,
        );

        when(mockRepository.handoffTask(
          'task-1',
          goal: anyNamed('goal'),
          templateId: anyNamed('templateId'),
        )).thenAnswer((_) async => intent);

        // Mock connection check - assume not connected
        final mockConnection = createMockOpenClawConnection();
        container.read(openClawConnectionProvider); // This would need proper setup

        await notifier.handoffTaskToAi('task-1');

        // Verify the handoff was attempted
        verify(mockRepository.handoffTask(
          'task-1',
          goal: anyNamed('goal'),
          templateId: anyNamed('templateId'),
        )).called(1);
      });
    });

    group('Feedback Submission', () {
      test('should submit task feedback', () async {
        final feedback = TaskFeedbackSubmission(
          difficulty: TaskDifficulty.medium,
          energyCost: TaskEnergyCost.moderate,
          actualMinutes: 30,
        );

        when(mockRepository.submitTaskFeedback('task-1', feedback))
            .thenAnswer((_) async => {});

        await notifier.submitTaskFeedback('task-1', feedback);

        verify(mockRepository.submitTaskFeedback('task-1', feedback)).called(1);
      });

      test('should record next action selection', () async {
        final action = NextAction(
          id: 'action-1',
          type: NextActionType.quickReview,
          relatedTaskId: 'task-1',
          title: 'Review key concepts',
        );

        when(mockRepository.recordNextActionSelection(
          'task-1',
          any,
        )).thenAnswer((_) async => {});

        await notifier.recordNextActionSelection(
          'task-1',
          action,
          0,
          true,
          1,
        );

        verify(mockRepository.recordNextActionSelection(
          'task-1',
          any,
        )).called(1);
      });

      test('should record skip next actions', () async {
        when(mockRepository.recordNextActionsSkip('task-1', any))
            .thenAnswer((_) async => {});

        await notifier.recordNextActionsSkip('task-1', []);

        verify(mockRepository.recordNextActionsSkip('task-1', any)).called(1);
      });
    });

    group('Task Completion', () {
      test('should complete task optimistically', () async {
        final task = TaskModel(
          id: 'task-complete',
          title: 'Complete Test',
          status: TaskStatus.inProgress,
          createdAt: DateTime.now(),
        );

        when(mockRepository.completeTask('task-complete', 25, null))
            .thenAnswer((_) async => TaskCompletionResult(
              task: task.toJson(),
            ));

        when(mockRepository.getTasks(filters: anyNamed('filters')))
            .thenAnswer((_) async => PaginatedResponse(items: [], total: 0));
        when(mockRepository.getTodayTasks())
            .thenAnswer((_) async => []);
        when(mockRepository.getRecommendedTasks())
            .thenAnswer((_) async => []);

        // Mock cancel reminders
        final mockScheduler = createMockNotificationScheduler();
        container.read(taskNotificationSchedulerProvider);

        await notifier.completeTask('task-complete', 25, null);

        // Verify optimistic update - task should be marked completed locally
        final completedTask = notifier.state.tasks.firstWhere(
          (t) => t.id == 'task-complete',
          orElse: () => task,
        );
        expect(completedTask.status, equals(TaskStatus.completed));
        expect(completedTask.syncStatus, equals(TaskSyncStatus.pending));
      });

      test('should abandon task', () async {
        final task = TaskModel(
          id: 'task-abandon',
          title: 'Abandon Test',
          status: TaskStatus.inProgress,
          createdAt: DateTime.now(),
        );

        when(mockRepository.abandonTask('task-abandon'))
            .thenAnswer((_) async => task.copyWith(
                  status: TaskStatus.abandoned,
                ));
        when(mockRepository.getTasks(filters: anyNamed('filters')))
            .thenAnswer((_) async => PaginatedResponse(items: [], total: 0));
        when(mockRepository.getTodayTasks())
            .thenAnswer((_) async => []);
        when(mockRepository.getRecommendedTasks())
            .thenAnswer((_) async => []);

        await notifier.abandonTask('task-abandon');

        // Verify state was updated
        final abandonedTask = notifier.state.tasks.firstWhere(
          (t) => t.id == 'task-abandon',
          orElse: () => task,
        );
        expect(abandonedTask.status, equals(TaskStatus.abandoned));
      });

      test('should start task', () async {
        final task = TaskModel(
          id: 'task-start',
          title: 'Start Test',
          status: TaskStatus.pending,
          createdAt: DateTime.now(),
        );

        when(mockRepository.startTask('task-start'))
            .thenAnswer((_) async => task.copyWith(
                  status: TaskStatus.inProgress,
                  startedAt: DateTime.now(),
                ));

        await notifier.startTask('task-start');

        // Verify state transition
        final startedTask = notifier.state.tasks.firstWhere(
          (t) => t.id == 'task-start',
          orElse: () => task,
        );
        expect(startedTask.status, equals(TaskStatus.inProgress));
      });
    });

    group('Error Handling', () {
      test('should handle load tasks failure', () async {
        when(mockRepository.getTasks(filters: anyNamed('filters')))
            .thenThrow(Exception('Network error'));

        await notifier.loadTasks();

        // Verify error state
        expect(notifier.state.error, isNotNull);
        expect(notifier.state.error, contains('Network error'));
      });
    });

    group('Task Reordering', () {
      test('should reorder tasks', () async {
        final tasks = [
          TaskModel(
            id: 'task-1',
            title: 'Task 1',
            status: TaskStatus.pending,
            createdAt: DateTime.now(),
            orderIndex: 1000,
          ),
          TaskModel(
            id: 'task-2',
            title: 'Task 2',
            status: TaskStatus.pending,
            createdAt: DateTime.now(),
            orderIndex: 2000,
          ),
        ];

        // Setup initial state
        notifier.state = notifier.state.copyWith(tasks: tasks);

        when(mockRepository.reorderTasks(any))
            .thenAnswer((_) async => tasks.reversed);

        await notifier.reorderTasks(0, 1);

        // Verify reordering
        expect(notifier.state.tasks[0].id, equals('task-2'));
        expect(notifier.state.tasks[1].id, equals('task-1'));
      });
    });

    group('Task Deletion', () {
      test('should delete task', () async {
        final task = TaskModel(
          id: 'task-delete',
          title: 'Delete Test',
          status: TaskStatus.pending,
          createdAt: DateTime.now(),
        );

        notifier.state = notifier.state.copyWith(tasks: [task]);

        when(mockRepository.deleteTask('task-delete'))
            .thenAnswer((_) async => {});
        when(mockRepository.getTasks(filters: anyNamed('filters')))
            .thenAnswer((_) async => PaginatedResponse(items: [], total: 0));
        when(mockRepository.getTodayTasks())
            .thenAnswer((_) async => []);
        when(mockRepository.getRecommendedTasks())
            .thenAnswer((_) async => []);

        // Mock cancel reminders
        final mockScheduler = createMockNotificationScheduler();
        container.read(taskNotificationSchedulerProvider);

        await notifier.deleteTask('task-delete');

        // Verify task was removed
        expect(notifier.state.tasks.any((t) => t.id == 'task-delete'), isFalse);
      });
    });

    group('Task Update', () {
      test('should update task', () async {
        final task = TaskModel(
          id: 'task-update',
          title: 'Original Title',
          status: TaskStatus.pending,
          createdAt: DateTime.now(),
        );

        final updatedTask = task.copyWith(title: 'Updated Title');

        when(mockRepository.updateTask('task-update', any))
            .thenAnswer((_) async => updatedTask);
        when(mockRepository.getTasks(filters: anyNamed('filters')))
            .thenAnswer((_) async => PaginatedResponse(items: [updatedTask], total: 1));
        when(mockRepository.getTodayTasks())
            .thenAnswer((_) async => [updatedTask]);
        when(mockRepository.getRecommendedTasks())
            .thenAnswer((_) async => []);

        await notifier.updateTask('task-update', TaskUpdate(title: 'Updated Title'));

        // Verify update
        final foundTask = notifier.state.tasks.firstWhere(
          (t) => t.id == 'task-update',
        );
        expect(foundTask.title, equals('Updated Title'));
      });
    });

    group('Execution Confirmation', () {
      test('should confirm task execution result', () async {
        final record = ExecutionRecordModel(
          id: 'record-1',
          taskId: 'task-1',
          status: 'confirmed',
        );

        when(mockRepository.confirmExecutionResult('record-1'))
            .thenAnswer((_) async => record);
        when(mockRepository.listExecutionIntents('task-1'))
            .thenAnswer((_) async => []);
        when(mockRepository.getExecutionRecord('exec-1'))
            .thenAnswer((_) async => record);
        when(mockRepository.getTask('task-1'))
            .thenAnswer((_) async => TaskModel(
                id: 'task-1',
                title: 'Test',
                status: TaskStatus.completed,
                createdAt: DateTime.now(),
              ));

        final result = await notifier.confirmTaskExecutionResult('task-1');

        expect(result, isNotNull);
        expect(result!.status, equals('confirmed'));
      });

      test('should reject task execution result', () async {
        final record = ExecutionRecordModel(
          id: 'record-1',
          taskId: 'task-1',
          status: 'rejected',
        );

        when(mockRepository.rejectExecutionResult('record-1', reason: 'Not accurate'))
            .thenAnswer((_) async => record);
        when(mockRepository.listExecutionIntents('task-1'))
            .thenAnswer((_) async => []);
        when(mockRepository.getExecutionRecord('exec-1'))
            .thenAnswer((_) async => record);

        final result = await notifier.rejectTaskExecutionResult(
          'task-1',
          reason: 'Not accurate',
        );

        expect(result, isNotNull);
        expect(result!.status, equals('rejected'));
      });
    });

    group('Sync Status', () {
      test('should mark task as pending sync on completion', () async {
        final task = TaskModel(
          id: 'task-sync',
          title: 'Sync Test',
          status: TaskStatus.inProgress,
          createdAt: DateTime.now(),
        );

        when(mockRepository.completeTask('task-sync', 30, null))
            .thenAnswer((_) async => TaskCompletionResult(
              task: task.toJson(),
            ));

        when(mockRepository.getTasks(filters: anyNamed('filters')))
            .thenAnswer((_) async => PaginatedResponse(items: [], total: 0));
        when(mockRepository.getTodayTasks())
            .thenAnswer((_) async => []);
        when(mockRepository.getRecommendedTasks())
            .thenAnswer((_) async => []);

        // Mock cancel reminders
        createMockNotificationScheduler();
        container.read(taskNotificationSchedulerProvider);

        await notifier.completeTask('task-sync', 30, null);

        final syncTask = notifier.state.tasks.firstWhere(
          (t) => t.id == 'task-sync',
          orElse: () => task,
        );
        expect(syncTask.syncStatus, equals(TaskSyncStatus.pending));
      });
    });

    group('AI Handoff Loading States', () {
      test('should track handoff in-flight state', () async {
        when(mockRepository.listExecutionIntents('task-handoff'))
            .thenAnswer((_) async => []);
        when(mockRepository.handoffTask(
          'task-handoff',
          goal: anyNamed('goal'),
          templateId: anyNamed('templateId'),
        )).thenAnswer((_) async => null);

        // Mock disconnected connection
        final mockConnection = createMockOpenClawConnection();
        container.read(openClawConnectionProvider);

        await notifier.handoffTaskToAi('task-handoff');

        // Should track loading state
        expect(notifier.state.handoffInFlight, contains('task-handoff'));
      });
    });
  });
}

// Helper classes and mocks
class PaginatedResponse<T> {
  PaginatedResponse({
    required this.items,
    required this.total,
  });

  final List<T> items;
  final int total;
}

class MockOpenClawConnection {
  bool isConnected = false;
  final queuedRequests = [];

  void markExecutionAvailable() {}
  void markExecutionUnavailable(String message) {}
}

MockOpenClawConnection createMockOpenClawConnection() {
  return MockOpenClawConnection();
}

class MockNotificationScheduler {
  Future<void> scheduleTaskReminders(TaskModel task, dynamic config) async {}
  Future<void> cancelTaskReminders(String id) async {}
  Future<void> rescheduleTaskReminders(TaskModel task, dynamic config) async {}
}

MockNotificationScheduler createMockNotificationScheduler() {
  return MockNotificationScheduler();
}
