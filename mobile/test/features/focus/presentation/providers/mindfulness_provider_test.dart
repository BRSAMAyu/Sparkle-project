import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/features/focus/data/services/prediction_service.dart';
import 'package:sparkle/features/focus/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/visual_elements/data/repositories/visual_element_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('start skips backend task start for local-only focus tasks', () async {
    final taskRepository = _RecordingTaskRepository();
    final notifier = _buildNotifier(taskRepository);

    notifier.start(
      TaskModel(
        id: 'quick_focus_local',
        userId: '',
        title: '自由专注',
        type: TaskType.learning,
        estimatedMinutes: 25,
        difficulty: 1,
        energyCost: 1,
        priority: 1,
        tags: const [],
        status: TaskStatus.pending,
        createdAt: DateTime(2026, 4, 1),
        updatedAt: DateTime(2026, 4, 1),
      ),
    );
    await Future<void>.delayed(Duration.zero);

    expect(taskRepository.startedTaskIds, isEmpty);
    notifier.dispose();
  });

  test('start still syncs real server tasks to backend', () async {
    final taskRepository = _RecordingTaskRepository();
    final notifier = _buildNotifier(taskRepository);

    notifier.start(
      TaskModel(
        id: '00000000-0000-0000-0000-000000000123',
        userId: '00000000-0000-0000-0000-000000000001',
        title: '真实任务',
        type: TaskType.learning,
        estimatedMinutes: 25,
        difficulty: 1,
        energyCost: 1,
        priority: 1,
        tags: const [],
        status: TaskStatus.pending,
        createdAt: DateTime(2026, 4, 1),
        updatedAt: DateTime(2026, 4, 1),
      ),
    );
    await Future<void>.delayed(Duration.zero);

    expect(
      taskRepository.startedTaskIds,
      ['00000000-0000-0000-0000-000000000123'],
    );
    notifier.dispose();
  });
}

MindfulnessNotifier _buildNotifier(_RecordingTaskRepository taskRepository) {
  final ref = _UnusedRef();
  return MindfulnessNotifier(
    ref,
    PredictionService(Dio()),
    taskRepository,
    AppEventStreamService(ref, _UnusedApiClient()),
    PredictionAttributionService(),
    VisualElementRepository(_UnusedApiClient()),
  );
}

class _RecordingTaskRepository extends TaskRepository {
  _RecordingTaskRepository() : super(_UnusedApiClient());

  final List<String> startedTaskIds = <String>[];

  @override
  Future<TaskModel> startTask(String id) async {
    startedTaskIds.add(id);
    return TaskModel(
      id: id,
      userId: '00000000-0000-0000-0000-000000000001',
      title: 'started',
      type: TaskType.learning,
      estimatedMinutes: 25,
      difficulty: 1,
      energyCost: 1,
      priority: 1,
      tags: const [],
      status: TaskStatus.inProgress,
      createdAt: DateTime(2026, 4, 1),
      updatedAt: DateTime(2026, 4, 1),
    );
  }
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
