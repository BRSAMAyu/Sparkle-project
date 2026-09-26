import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/providers/release_flags_provider.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/features/focus/data/models/focus_session_model.dart';
import 'package:sparkle/features/focus/data/repositories/focus_repository.dart';
import 'package:sparkle/features/focus/data/services/prediction_service.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart';
import 'package:sparkle/features/focus/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/visual_elements/data/repositories/visual_element_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('start skips backend task start for local-only focus tasks', () async {
    final taskRepository = _RecordingTaskRepository();
    final notifier = _buildNotifier(taskRepository)
      ..start(
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
          createdAt: DateTime(2026, 4),
          updatedAt: DateTime(2026, 4),
        ),
      );
    await Future<void>.delayed(Duration.zero);

    expect(taskRepository.startedTaskIds, isEmpty);
    notifier.dispose();
  });

  test('start still syncs real server tasks to backend', () async {
    final taskRepository = _RecordingTaskRepository();
    final notifier = _buildNotifier(taskRepository)
      ..start(
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
          createdAt: DateTime(2026, 4),
          updatedAt: DateTime(2026, 4),
        ),
      );
    await Future<void>.delayed(Duration.zero);

    expect(
      taskRepository.startedTaskIds,
      ['00000000-0000-0000-0000-000000000123'],
    );
    notifier.dispose();
  });

  // F7-17 (round1 07-mobile-features / round2 R2-05) red-green: the
  // constructor fires `_restoreSession()` unawaited while the UI may call
  // `start()` immediately. The restore used to land after start() and
  // clobber the fresh session with the persisted one.
  test('in-flight restore does not clobber a live session started by UI',
      () async {
    SharedPreferences.setMockInitialValues({
      'mindfulness.active_session': jsonEncode({
        'isActive': true,
        'startTime': DateTime(2026, 4, 1, 8).toIso8601String(),
        'elapsedSeconds': 300,
        'interruptionCount': 0,
        'interruptions': <dynamic>[],
        'isDNDEnabled': false,
        'isPaused': false,
      }),
    });
    // Prime the SharedPreferences completer so the constructor's in-flight
    // restore deterministically resumes within the test window below.
    final primedPrefs = await SharedPreferences.getInstance();
    expect(
      primedPrefs.getString('mindfulness.active_session'),
      isNotNull,
    );
    final notifier = _buildNotifier(_RecordingTaskRepository());

    // Fresh session starts synchronously while the constructor's restore
    // is still suspended on SharedPreferences.getInstance().
    final freshTask = TaskModel(
      id: 'fresh_session_task',
      userId: 'u1',
      title: '新会话',
      type: TaskType.learning,
      estimatedMinutes: 25,
      difficulty: 1,
      energyCost: 1,
      priority: 1,
      tags: const [],
      status: TaskStatus.pending,
      createdAt: DateTime(2026, 4),
      updatedAt: DateTime(2026, 4),
    );
    notifier.start(freshTask);
    expect(notifier.state.isActive, isTrue);
    expect(notifier.state.currentTask?.id, 'fresh_session_task');

    // Let the in-flight restore land.
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);

    expect(notifier.state.isActive, isTrue);
    expect(notifier.state.currentTask?.id, 'fresh_session_task');
    notifier.dispose();
  });

  // V3-FIX-190 红：release flag 未拉到（fail-closed）时，正念完成动线不得再发
  // /visual-elements/unlock-by-achievement——后端 /visual-elements 组注册级闸
  // （RELEASE_ENABLE_VISUAL_ELEMENTS 默认 False→403 FEATURE_DISABLED）使该请求
  // 注定 403（客户端 try/catch 吞掉，但 403 噪声进监控）。base 上无短路 → 调用照发。
  test('flags unavailable fail-closed short-circuits achievement unlock call',
      () async {
    SharedPreferences.setMockInitialValues({
      'mindfulness.active_session': jsonEncode({
        'isActive': true,
        'startTime': DateTime.now()
            .subtract(const Duration(minutes: 7))
            .toIso8601String(),
        'elapsedSeconds': 420,
        'interruptionCount': 0,
        'interruptions': <dynamic>[],
        'isDNDEnabled': false,
        'isPaused': false,
      }),
    });
    final visualRepo = _RecordingVisualElementRepository();
    final container = ProviderContainer(
      overrides: [
        // /release-flags 拉取面在测试内快速失败（无网络）→ fail-closed 保持关
        apiClientProvider.overrideWithValue(_UnusedApiClient()),
        focusStatisticsProvider.overrideWith(
          () => _FakeFocusStatistics(_fakeSession),
        ),
        mindfulnessProvider.overrideWith(
          (ref) => MindfulnessNotifier(
            ref,
            PredictionService(Dio()),
            _RecordingTaskRepository(),
            _StubEventStreamService(),
            PredictionAttributionService(),
            visualRepo,
          ),
        ),
      ],
    );
    addTearDown(container.dispose);

    final notifier = container.read(mindfulnessProvider.notifier);
    // 等构造器的 in-flight restore 落地（F7-17 同款时序）
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);
    expect(notifier.state.isActive, isTrue);

    await notifier.stop();

    expect(
      visualRepo.unlockCalls,
      isEmpty,
      reason: 'release flag visual_elements off/unavailable（fail-closed）时'
          '不得再发注定 403 的 unlock 请求',
    );
  });

  // V3-FIX-190 邻域守卫：旗开（visual_elements=true）时解锁调用必须照发——
  // 短路只许关闸噪声，不许误伤 rollout 后的正常解锁。
  test('flag on proceeds with achievement unlock calls', () async {
    SharedPreferences.setMockInitialValues({
      'mindfulness.active_session': jsonEncode({
        'isActive': true,
        'startTime': DateTime.now()
            .subtract(const Duration(minutes: 7))
            .toIso8601String(),
        'elapsedSeconds': 420,
        'interruptionCount': 0,
        'interruptions': <dynamic>[],
        'isDNDEnabled': false,
        'isPaused': false,
      }),
    });
    final visualRepo = _RecordingVisualElementRepository();
    final container = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWithValue(_UnusedApiClient()),
        focusStatisticsProvider.overrideWith(
          () => _FakeFocusStatistics(_fakeSession),
        ),
        mindfulnessProvider.overrideWith(
          (ref) => MindfulnessNotifier(
            ref,
            PredictionService(Dio()),
            _RecordingTaskRepository(),
            _StubEventStreamService(),
            PredictionAttributionService(),
            visualRepo,
          ),
        ),
      ],
    );
    addTearDown(container.dispose);
    // 旗开：钉住 visual_elements=true
    container.read(releaseFlagsProvider.notifier).seed(
          const ReleaseFlags(visualElements: true),
        );

    final notifier = container.read(mindfulnessProvider.notifier);
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);
    expect(notifier.state.isActive, isTrue);

    await notifier.stop();

    expect(visualRepo.unlockCalls, ['ach_first_focus']);
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

/// V3-FIX-190：带成就解锁的会话结果（两测试共用）
const LoggedFocusSession _fakeSession = LoggedFocusSession(
  response: FocusSessionResponse(
    success: true,
    id: 'focus-session-1',
    rewards: FocusSessionRewards(
      flameEarned: 3,
      leveledUp: false,
      newLevel: 1,
    ),
  ),
  unlockedAchievements: [
    <String, dynamic>{'id': 'ach_first_focus'},
  ],
);

/// V3-FIX-190：记录 unlock-by-achievement 调用的假仓库
class _RecordingVisualElementRepository extends VisualElementRepository {
  _RecordingVisualElementRepository() : super(_UnusedApiClient());

  final List<String> unlockCalls = <String>[];

  @override
  Future<List<VisualElementModel>> unlockByAchievement(
    String achievementId,
  ) async {
    unlockCalls.add(achievementId);
    return const <VisualElementModel>[];
  }
}

/// V3-FIX-190：saveSession 假通知器（返回带成就解锁的会话结果）
class _FakeFocusStatistics extends FocusStatistics {
  _FakeFocusStatistics(this._response);

  final LoggedFocusSession _response;

  @override
  FocusStatisticsState build() => const FocusStatisticsState();

  @override
  Future<LoggedFocusSession?> saveSession({
    required DateTime startTime,
    required DateTime endTime,
    required int durationMinutes,
    String focusType = 'pomodoro',
    String status = 'completed',
    String? taskId,
    String? taskTitle,
    String? whiteNoiseType,
    int interruptionCount = 0,
    int? qualityScore,
  }) async =>
      _response;
}

/// V3-FIX-190：事件流桩（正念 stop 动线中 recordEntityExecution 置空）
class _StubEventStreamService extends AppEventStreamService {
  _StubEventStreamService() : super(_UnusedRef(), _UnusedApiClient());

  @override
  Future<void> recordEntityExecution({
    required String entityType,
    required String entityId,
    required String actionType,
    required String source,
    Map<String, dynamic>? payload,
  }) async {}
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
      createdAt: DateTime(2026, 4),
      updatedAt: DateTime(2026, 4),
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
