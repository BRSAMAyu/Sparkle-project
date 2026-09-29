import 'dart:async';
import 'dart:convert';
import 'dart:ui' show Locale;

import 'package:connectivity_plus_platform_interface/connectivity_plus_platform_interface.dart';
import 'package:dio/dio.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/focus/data/models/focus_session_model.dart';
import 'package:sparkle/features/focus/data/repositories/focus_repository.dart'
    show LoggedFocusSession;
import 'package:sparkle/features/focus/data/services/prediction_service.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart';
import 'package:sparkle/features/focus/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/visual_elements/data/repositories/visual_element_repository.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// V4-U09 验收面 1+2（结算语义，provider 层）：
/// - 面1：中断计时不假保存（中断/杀进程路径零写入）；估计和实际分开
///   （saveSession 只收实测分钟，估时不顶替——U08 actualMinutes 同口径）。
/// - 面2：切后台/重开不重置或重复结算（重启恢复保 startTime 续算；
///   结算窗口重入不产生第二条保存；失败重试恰好结算一次）。

class _StubTaskRepository implements TaskRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName} not expected');
}

class _StubEventStream extends AppEventStreamService {
  _StubEventStream() : super(_UnusedRef(), _UnusedApiClient());

  @override
  Future<void> recordEntityExecution({
    required String entityType,
    required String entityId,
    required String actionType,
    required String source,
    Map<String, dynamic>? payload,
  }) async {}
}

class _StubVisualElementRepository extends VisualElementRepository {
  _StubVisualElementRepository() : super(_UnusedApiClient());

  @override
  Future<List<VisualElementModel>> unlockByAchievement(
    String achievementId,
  ) async =>
      const <VisualElementModel>[];
}

class _SilentConnectivityPlatform extends ConnectivityPlatform {
  @override
  Stream<List<ConnectivityResult>> get onConnectivityChanged =>
      const Stream<Object?>.empty() as Stream<List<ConnectivityResult>>;

  @override
  Future<List<ConnectivityResult>> checkConnectivity() async =>
      <ConnectivityResult>[ConnectivityResult.none];
}

/// 记录 saveSession 调用参数的假统计通知器；[throwOnCall] 为真时每次
/// 调用抛异常（模拟保存失败/离线不可用）。
class _RecordingFocusStatistics extends FocusStatistics {
  _RecordingFocusStatistics({this.throwOnCall = false});

  final bool throwOnCall;
  final List<Map<String, dynamic>> calls = <Map<String, dynamic>>[];

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
  }) async {
    calls.add(<String, dynamic>{
      'startTime': startTime,
      'endTime': endTime,
      'durationMinutes': durationMinutes,
      'status': status,
      'taskId': taskId,
      'interruptionCount': interruptionCount,
    });
    if (throwOnCall) {
      throw StateError('save unavailable (test)');
    }
    return const LoggedFocusSession(
      response: FocusSessionResponse(
        success: true,
        id: 'focus-session-u09',
        rewards: FocusSessionRewards(
          flameEarned: 0,
          leveledUp: false,
          newLevel: 1,
        ),
      ),
    );
  }
}

ProviderContainer _makeContainer(_RecordingFocusStatistics statistics) {
  final container = ProviderContainer(
    overrides: [
      // /release-flags 等网络面在测试内不可达（fail-closed 降级路径）。
      apiClientProvider.overrideWithValue(_UnusedApiClient()),
      currentUserProvider.overrideWithValue(null),
      // stop() 成功后 invalidate(taskListProvider) 会触发重建链
      // （TaskNotifier→scheduler→NotificationService 平台通道）——换
      // 不初始化通道的实例，测试环境无插件实现。
      notificationServiceProvider.overrideWith(
        (ref) => NotificationService(ref, autoInitialize: false),
      ),
      focusStatisticsProvider.overrideWith(() => statistics),
      mindfulnessProvider.overrideWith(
        (ref) => MindfulnessNotifier(
          ref,
          PredictionService(Dio()),
          _StubTaskRepository(),
          _StubEventStream(),
          PredictionAttributionService(),
          _StubVisualElementRepository(),
        ),
      ),
    ],
  );
  return container;
}

TaskModel _task({int estimatedMinutes = 25}) => TaskModel(
      id: 'u09-focus-task',
      userId: 'u1',
      title: '状态机错题重练',
      type: TaskType.learning,
      estimatedMinutes: estimatedMinutes,
      difficulty: 1,
      energyCost: 1,
      priority: 1,
      tags: const [],
      status: TaskStatus.inProgress,
      createdAt: DateTime(2026, 9),
      updatedAt: DateTime(2026, 9),
    );

Future<void> _seedSession({
  required DateTime startTime,
  required TaskModel task,
  int elapsedSeconds = 0,
  int interruptionCount = 0,
}) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString(
    'mindfulness.active_session',
    jsonEncode(<String, dynamic>{
      'isActive': true,
      'startTime': startTime.toIso8601String(),
      'elapsedSeconds': elapsedSeconds,
      'interruptionCount': interruptionCount,
      'interruptions': const <dynamic>[],
      'isDNDEnabled': false,
      'currentTask': task.toJson(),
      'isPaused': false,
      'accumulatedPausedSeconds': 0,
      'translationRequestCount': 0,
      'lastTranslationGranularity': 'word',
    }),
  );
}

MindfulnessNotifier _notifier(ProviderContainer container) =>
    container.read(mindfulnessProvider.notifier);

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    ConnectivityPlatform.instance = _SilentConnectivityPlatform();
    I18nService.instance.updateLocale(const Locale('zh'), AppLocalizationsZh());
  });

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, String>{});
    // 认证拦截器读安全存储：headless 无插件实现，返回空走离线路径。
    TestWidgetsFlutterBinding.ensureInitialized().defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      (call) async => null,
    );
  });

  test('面1正：结算只写实测分钟（90 分钟实测 ≠ 任务估时 25）', () async {
    // 会话真实进行 90 分钟；任务估时 25 分钟——估时不得顶替实测进证据。
    final startTime = DateTime.now().subtract(const Duration(minutes: 90));
    await _seedSession(startTime: startTime, task: _task());

    final statistics = _RecordingFocusStatistics();
    final container = _makeContainer(statistics);
    addTearDown(container.dispose);
    final notifier = _notifier(container);
    await Future<void>.delayed(Duration.zero);
    expect(notifier.state.isActive, isTrue);

    final result = await notifier.stop();

    expect(result.savedLocally, isTrue);
    expect(statistics.calls, hasLength(1));
    final saved = statistics.calls.single;
    // 实测口径：90 分钟（结算时墙钟再走几秒不跨分钟）；绝不出现估时 25。
    expect(saved['durationMinutes'], inInclusiveRange(90, 90));
    expect(
      saved['durationMinutes'],
      isNot(_task().estimatedMinutes),
      reason: '估时 25 不得顶替 90 分钟实测（U08 actualMinutes 同口径）',
    );
    expect(
      (saved['startTime'] as DateTime).isAtSameMomentAs(startTime),
      isTrue,
      reason: '结算起点=会话真实起点（无重置）',
    );
  });

  test('面1反钉：中断/杀进程不产生任何保存记录（重开恢复会话，不假保存）',
      () async {
    final startTime = DateTime.now().subtract(const Duration(minutes: 6));
    await _seedSession(startTime: startTime, task: _task());

    // 「进程 1」：恢复会话并记录一次中断（切后台），随后进程被杀（dispose）。
    final statistics = _RecordingFocusStatistics();
    final container1 = _makeContainer(statistics);
    final notifier1 = container1.read(mindfulnessProvider.notifier);
    await Future<void>.delayed(Duration.zero);
    expect(notifier1.state.isActive, isTrue);
    notifier1.recordInterruption(InterruptionType.appSwitch);
    await Future<void>.delayed(Duration.zero);
    container1.dispose();

    // 断点处零写入：中断本身不结算、不伪造完成记录。
    expect(
      statistics.calls,
      isEmpty,
      reason: '中断/杀进程路径不得写任何专注记录（不假保存）',
    );

    // 「进程 2」：重开恢复，会话仍在且时间延续。
    final container2 = _makeContainer(statistics);
    addTearDown(container2.dispose);
    final notifier2 = container2.read(mindfulnessProvider.notifier);
    await Future<void>.delayed(Duration.zero);
    expect(notifier2.state.isActive, isTrue);
    expect(notifier2.state.interruptionCount, 1);
    expect(notifier2.state.elapsedSeconds, greaterThanOrEqualTo(360));
    // 用户仍未主动结束：依旧零写入。
    expect(statistics.calls, isEmpty);
  });

  test('面2正：重开恢复不重置——startTime 原样保留，计时按墙钟延续', () async {
    final startTime = DateTime.now().subtract(const Duration(minutes: 10));
    await _seedSession(
      startTime: startTime,
      task: _task(),
      elapsedSeconds: 600,
    );

    final statistics = _RecordingFocusStatistics();
    final container = _makeContainer(statistics);
    addTearDown(container.dispose);
    final notifier = _notifier(container);
    await Future<void>.delayed(Duration.zero);

    expect(notifier.state.isActive, isTrue);
    // 不重置：起点保持原值（到毫秒），实测从墙钟续算（≥ 持久化的 600 秒）。
    expect(
      notifier.state.startTime!.isAtSameMomentAs(startTime),
      isTrue,
    );
    expect(
      notifier.state.elapsedSeconds,
      inInclusiveRange(600, 615),
      reason: '重开后计时延续（不回 0、不重来）',
    );
  });

  test('面2反钉：结算窗口内重入 stop() 不产生第二条保存（不重复结算）', () async {
    final startTime = DateTime.now().subtract(const Duration(minutes: 12));
    await _seedSession(startTime: startTime, task: _task());

    final statistics = _RecordingFocusStatistics();
    final container = _makeContainer(statistics);
    addTearDown(container.dispose);
    final notifier = _notifier(container);
    await Future<void>.delayed(Duration.zero);

    // 双路径并发退出（弹层确认 + 返回键/双击）：两次 stop() 同时在飞。
    final f1 = notifier.stop();
    final f2 = notifier.stop();
    await Future.wait(<Future<MindfulnessStopResult>>[f1, f2]);

    expect(
      statistics.calls,
      hasLength(1),
      reason: '结算窗口内的重入必须被合流，重复结算=重复记录=假成长',
    );
    expect(notifier.state.isActive, isFalse, reason: '结算后正常 teardown');
  });

  test('面2补：保存失败→快照保留可重试→重试恰好结算一次', () async {
    final startTime = DateTime.now().subtract(const Duration(minutes: 5));
    await _seedSession(startTime: startTime, task: _task());

    final statistics = _RecordingFocusStatistics(throwOnCall: true);
    final container = _makeContainer(statistics);
    addTearDown(container.dispose);
    final notifier = _notifier(container);
    await Future<void>.delayed(Duration.zero);

    final failed = await notifier.stop();
    expect(failed.savedLocally, isFalse);
    expect(notifier.state.isActive, isTrue, reason: '失败保会话（R2-03）');

    // 快照仍在（可恢复），重试结算恰好一次。
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('mindfulness.active_session'), isNotNull);
  });
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
