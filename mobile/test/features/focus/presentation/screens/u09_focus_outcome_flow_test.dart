import 'dart:async';
import 'dart:convert';

import 'package:connectivity_plus_platform_interface/connectivity_plus_platform_interface.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/providers/release_flags_provider.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';
import 'package:sparkle/features/cognitive/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/cognitive_repository.dart'
    show cognitiveRepositoryProvider;
import 'package:sparkle/features/cognitive/data/repositories/i_cognitive_repository.dart';
import 'package:sparkle/features/focus/data/models/focus_session_model.dart';
import 'package:sparkle/features/focus/data/repositories/focus_repository.dart'
    show LoggedFocusSession;
import 'package:sparkle/features/focus/data/services/prediction_service.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart';
import 'package:sparkle/features/focus/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/features/focus/presentation/screens/mindfulness_mode_screen.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/visual_elements/data/repositories/visual_element_repository.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

import '../../../../shared/i18n_test_helper.dart';

/// V4-U09 验收面（widget 层，专注正念结束动线）：
/// - 结束可记录成果或跳过，不强制长反思——「跳过」是一等路径（可见按钮
///   +barrier 可关），留空点「记录」视同跳过，零输入可离开。
/// - 无声音动效仍完整可用（减弱动效+提示音/背景声全关，完整走通
///   暂停/恢复/退出/结算/成果-跳过，无无限动画）；失败不显示庆祝
///   （saveSession 失败→无成果面、无奖励摘要、错误如实呈现、快照保留）。
/// - 估计和实际分开（用户可见面）：结果面实测主行+估时对照注脚分列。

const String _sessionKey = 'mindfulness.active_session';

TaskModel _task() => TaskModel(
      id: 'u09-focus-task',
      userId: 'u1',
      title: '状态机错题重练',
      type: TaskType.learning,
      estimatedMinutes: 25,
      difficulty: 1,
      energyCost: 1,
      priority: 1,
      tags: const [],
      status: TaskStatus.inProgress,
      createdAt: DateTime(2026, 9),
      updatedAt: DateTime(2026, 9),
    );

/// saveSession 调用的共享记录器（跨 provider 元素重建共享断言状态）。
class _SaveSink {
  bool throwOnNextCall = false;
  final List<Map<String, dynamic>> calls = <Map<String, dynamic>>[];
  final List<int> successfulWrites = <int>[];
}

/// 可切换成功/失败的 saveSession 假统计通知器。
/// riverpod 元素重建时会再次调 build 取 notifier——必须给新实例
/// （StateNotifier._element 是 late final，复用实例=二次初始化必炸）；
/// 断言状态放 [_SaveSink] 共享。
class _FakeFocusStatistics extends FocusStatistics {
  _FakeFocusStatistics(this._sink);

  final _SaveSink _sink;

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
    _sink.calls.add(<String, dynamic>{
      'durationMinutes': durationMinutes,
      'taskId': taskId,
    });
    if (_sink.throwOnNextCall) {
      throw StateError('save unavailable (test)');
    }
    _sink.successfulWrites.add(durationMinutes);
    return const LoggedFocusSession(
      response: FocusSessionResponse(
        success: true,
        id: 'focus-session-u09-ui',
        rewards: FocusSessionRewards(
          flameEarned: 0,
          leveledUp: false,
          newLevel: 1,
        ),
      ),
    );
  }
}

/// 记录 createFragment 的假认知仓储。
class _RecordingCognitiveRepository implements ICognitiveRepository {
  _RecordingCognitiveRepository();

  final List<CognitiveFragmentCreate> creates = <CognitiveFragmentCreate>[];

  @override
  Future<CognitiveFragmentModel> createFragment(
    CognitiveFragmentCreate data,
  ) async {
    creates.add(data);
    return CognitiveFragmentModel(
      id: 'frag-u09',
      userId: 'u1',
      sourceType: data.sourceType,
      content: data.content,
      createdAt: DateTime(2026, 9),
      taskId: data.taskId,
    );
  }

  @override
  Future<List<CognitiveFragmentModel>> getFragments({
    int limit = 20,
    int skip = 0,
  }) async =>
      const <CognitiveFragmentModel>[];

  @override
  Future<List<BehaviorPatternModel>> getBehaviorPatterns() async =>
      const <BehaviorPatternModel>[];
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

class _SilentConnectivityPlatform extends ConnectivityPlatform {
  @override
  Stream<List<ConnectivityResult>> get onConnectivityChanged =>
      const Stream<Object?>.empty() as Stream<List<ConnectivityResult>>;

  @override
  Future<List<ConnectivityResult>> checkConnectivity() async =>
      <ConnectivityResult>[ConnectivityResult.none];
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StubTaskRepository extends TaskRepository {
  _StubTaskRepository() : super(_UnusedApiClient());
}

class _StubVisualElementRepository extends VisualElementRepository {
  _StubVisualElementRepository() : super(_UnusedApiClient());

  @override
  Future<List<VisualElementModel>> unlockByAchievement(
    String achievementId,
  ) async =>
      const <VisualElementModel>[];
}

Future<void> _seedRunningSession() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString(
    _sessionKey,
    jsonEncode(<String, dynamic>{
      'isActive': true,
      'startTime': DateTime.now()
          .subtract(const Duration(minutes: 6))
          .toIso8601String(),
      'elapsedSeconds': 360,
      'interruptionCount': 0,
      'interruptions': const <dynamic>[],
      'isDNDEnabled': false,
      'currentTask': _task().toJson(),
      'isPaused': false,
      'accumulatedPausedSeconds': 0,
      'translationRequestCount': 0,
      'lastTranslationGranularity': 'word',
    }),
  );
}

class _Harness {
  _Harness(this.container, this.router);
  final ProviderContainer container;
  final GoRouter router;
}

Future<_Harness> _pumpScreen(
  WidgetTester tester, {
  required _SaveSink sink,
  required _RecordingCognitiveRepository cognitive,
  bool reduceMotion = false,
}) async {
  if (reduceMotion) {
    // N33 同口径：disableAnimations（系统级减动效）→ context.reduceMotion。
    tester.binding.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(
      tester.binding.platformDispatcher.clearAccessibilityFeaturesTestValue,
    );
  }

  final container = ProviderContainer(
    overrides: [
      apiClientProvider.overrideWithValue(_UnusedApiClient()),
      // 预置 release flags（fail-closed=off）：避免 stop() 里 ensureLoaded
      // 走真实拉取面（测试环境无网络，二次读取会撞 riverpod 重建）。

      currentUserProvider.overrideWithValue(null),
      notificationServiceProvider.overrideWith(
        (ref) => NotificationService(ref, autoInitialize: false),
      ),
      cognitiveRepositoryProvider.overrideWithValue(cognitive),
      focusStatisticsProvider.overrideWith(() => _FakeFocusStatistics(sink)),
      taskDetailProvider.overrideWith((ref, id) async => _task()),
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
  addTearDown(container.dispose);

  final router = GoRouter(
    // 与真实导航同构：来源页在栈底，专注页是被 push 的一层——
    // 结束动线里的 context.pop() 才有可弹栈。
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (_, __) => const Scaffold(
          key: Key('u09-home-destination'),
          body: Center(child: Text('回到首页')),
        ),
      ),
      GoRoute(
        path: '/focus/mindfulness/:id',
        builder: (_, state) =>
            MindfulnessModeScreen(taskId: state.pathParameters['id']!),
      ),
    ],
  );

  container.read(releaseFlagsProvider.notifier).seed(const ReleaseFlags());

  // 先建 notifier 并让构造器的 _restoreSession 落地（F7-17 时序）：
  // 屏幕挂载时 _initializeWithTask 才会识别「已恢复的进行中会话」并跳过
  // start()——否则 6 分钟会话被清零重开。
  final notifier = container.read(mindfulnessProvider.notifier);
  // testWidgets 的 FakeAsync 区里 Duration.zero 定时器不随语句推进——用
  // runAsync 走真实事件循环让构造器 restore 落地。
  await tester.runAsync(() async {
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(const Duration(milliseconds: 5));
  });
  expect(notifier.state.isActive, isTrue, reason: '恢复的进行中会话应已就位');
  expect(notifier.state.elapsedSeconds, greaterThanOrEqualTo(360));

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp.router(
        theme: ThemeData.light(),
        locale: const Locale('zh'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        routerConfig: router,
      ),
    ),
  );
  await tester.pump();
  unawaited(router.push('/focus/mindfulness/u09-focus-task'));
  // 等任务加载 + 入场动画（560ms）+ 星空背景落定。
  await tester.pump(const Duration(milliseconds: 100));
  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 120));
  }
  return _Harness(container, router);
}

Future<void> _confirmExit(WidgetTester tester) async {
  await tester.tap(find.text('退出正念模式'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 240));
  await tester.tap(find.text('确定退出'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 240));
}

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    ConnectivityPlatform.instance = _SilentConnectivityPlatform();
    setUpI18nForTesting();
  });

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, String>{});
    TestWidgetsFlutterBinding.ensureInitialized().defaultBinaryMessenger
      ..setMockMethodCallHandler(
        const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
        (call) async => null,
      )
      ..setMockMethodCallHandler(
        const MethodChannel('dexterous.com/flutter/local_notifications'),
        (call) async => null,
      );
  });

  testWidgets(
      '结束面：实测/估时分列，「跳过」一等路径零写入离开，结算恰好一次',
      (tester) async {
    await _seedRunningSession();
    final sink = _SaveSink();
    final cognitive = _RecordingCognitiveRepository();

    await _pumpScreen(
      tester,
      sink: sink,
      cognitive: cognitive,
    );
    expect(tester.takeException(), isNull);

    await _confirmExit(tester);

    // 结束面出现：实测为主行、估时为对照注脚（分列，估时不顶替实测）。
    expect(find.text('实际专注 6 分钟'), findsOneWidget);
    expect(find.text('计划 25 分钟'), findsOneWidget);
    expect(find.byKey(const Key('focus-outcome-skip')), findsOneWidget);
    expect(find.byKey(const Key('focus-outcome-record')), findsOneWidget);

    // 跳过 = 一等路径：零输入直接离开，不写任何认知碎片。
    await tester.tap(find.byKey(const Key('focus-outcome-skip')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 240));

    expect(
      cognitive.creates,
      isEmpty,
      reason: '跳过路径不得写任何记录',
    );
    expect(
      find.byKey(const Key('u09-home-destination')),
      findsOneWidget,
      reason: '跳过后正常回到来源页',
    );
    // 结算恰好一次，且时长为实测（6 分钟，非估时 25）。
    expect(sink.calls, hasLength(1));
    expect(sink.calls.single['durationMinutes'], 6);
  });

  testWidgets(
      '不强制反思钉：无必填字段，留空点「记录」视同跳过（零输入可离开）',
      (tester) async {
    await _seedRunningSession();
    final sink = _SaveSink();
    final cognitive = _RecordingCognitiveRepository();

    await _pumpScreen(tester, sink: sink, cognitive: cognitive);
    await _confirmExit(tester);

    // 不输入任何内容直接点「记录成果」——旧行为（卡点字段必填的强制长
    // 反思）下该路径不可用；现在留空视同跳过，零写入离开。
    await tester.tap(find.byKey(const Key('focus-outcome-record')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 240));

    expect(cognitive.creates, isEmpty, reason: '留空记录=跳过，不强制输入');
    expect(find.byKey(const Key('u09-home-destination')), findsOneWidget);
  });

  testWidgets('记录成果：写入带溯源头的一句成果（任务名+实测分钟+原文）',
      (tester) async {
    await _seedRunningSession();
    final sink = _SaveSink();
    final cognitive = _RecordingCognitiveRepository();

    await _pumpScreen(tester, sink: sink, cognitive: cognitive);
    await _confirmExit(tester);

    await tester.enterText(
      find.byKey(const Key('focus-outcome-field')),
      '搞懂了中断恢复为什么不能双结算',
    );
    await tester.tap(find.byKey(const Key('focus-outcome-record')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 240));
    // 让成功 snackbar 的计时器走完，避免测试收尾挂起 Timer。
    await tester.pump(const Duration(seconds: 4));

    expect(cognitive.creates, hasLength(1));
    final created = cognitive.creates.single;
    expect(created.sourceType, 'reflection');
    expect(created.content, contains('搞懂了中断恢复为什么不能双结算'));
    expect(created.content, contains('状态机错题重练'));
    expect(created.content, contains('实际 6 分钟'));
    expect(created.taskId, 'u09-focus-task');
    expect(find.byKey(const Key('u09-home-destination')), findsOneWidget);
  });

  testWidgets(
      '失败不庆祝钉+重试单结算：保存失败→无成果面无奖励摘要、错误如实呈现；'
      '重试恰好补结算一次',
      (tester) async {
    await _seedRunningSession();
    final sink = _SaveSink()..throwOnNextCall = true;
    final cognitive = _RecordingCognitiveRepository();

    final harness = await _pumpScreen(
      tester,
      sink: sink,
      cognitive: cognitive,
    );
    await _confirmExit(tester);
    await tester.pump(const Duration(milliseconds: 240));

    // 失败路径不渲染任何成功/庆祝面。
    expect(
      find.text('实际专注 6 分钟'),
      findsNothing,
      reason: '保存失败不得进入成果面',
    );
    expect(
      find.text('专注完成'),
      findsNothing,
      reason: '失败不得出现奖励摘要/庆祝',
    );
    // 错误如实呈现（error snackbar）。
    expect(find.textContaining('保存失败'), findsOneWidget);
    // 快照保留（R2-03 可恢复），不产生假成功。
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString(_sessionKey), isNotNull);
    expect(sink.calls, hasLength(1), reason: '尝试过一次保存（失败）');
    expect(sink.successfulWrites, isEmpty, reason: '失败=零写入，不假保存');
    expect(cognitive.creates, isEmpty);
    // 让错误 snackbar（6s）计时器走完。
    await tester.pump(const Duration(seconds: 7));

    // 失败按既有行为返回来源页（会话仍在后台可续结）。
    expect(find.byKey(const Key('u09-home-destination')), findsOneWidget);

    // 收起错误 snackbar（悬浮层会挡住底部按钮的命中测试）。
    tester
        .state<ScaffoldMessengerState>(find.byType(ScaffoldMessenger).first)
        .hideCurrentSnackBar();
    await tester.pump(const Duration(milliseconds: 300));

    // 用户重开专注页（R2-03 恢复设计：会话快照仍在，重开续结）后重试
    // 退出：第二次结算成功——总共恰好一次成功写入（失败那次没有落账），
    // 结果面正常出现、跳过零写入。
    sink.throwOnNextCall = false;
    unawaited(harness.router.push('/focus/mindfulness/u09-focus-task'));
    await tester.pump(const Duration(milliseconds: 100));
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 120));
    }
    await _confirmExit(tester);
    expect(find.text('实际专注 6 分钟'), findsOneWidget);
    await tester.tap(find.byKey(const Key('focus-outcome-skip')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 240));
    expect(find.byKey(const Key('u09-home-destination')), findsOneWidget);
    expect(
      sink.successfulWrites,
      hasLength(1),
      reason: '失败重试后恰好一次成功结算（不重复结算）',
    );
  });

  testWidgets(
      '无声音动效仍完整可用：减弱动效+声音全关下暂停/退出/结算/跳过全通',
      (tester) async {
    await _seedRunningSession();
    final sink = _SaveSink();
    final cognitive = _RecordingCognitiveRepository();

    // 声音全关：提示音、背景声独立开关与场景全部归零（U14 偏好键）。
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('sensory_feedback.sound_enabled', false);
    await prefs.setBool('sensory_feedback.ambient_enabled', false);
    await prefs.setInt('sensory_feedback.ambient_scene', 0);

    await _pumpScreen(
      tester,
      sink: sink,
      cognitive: cognitive,
      reduceMotion: true,
    );
    expect(tester.takeException(), isNull);

    // 减动效下无无限动画：入场动画结束后零 transient callback
    // （火苗走静态支、星空静止——画面仍在，循环停）。
    await tester.pump(const Duration(milliseconds: 200));
    expect(
      tester.binding.transientCallbackCount,
      0,
      reason: '减弱动效下不允许任何持续动画在跑',
    );

    // 暂停→恢复照常（无声也无碍；接 U14 ambient 状态门控）。
    await tester.tap(find.byIcon(Icons.pause_rounded));
    await tester.pump(const Duration(milliseconds: 100));
    await tester.tap(find.byIcon(Icons.play_arrow_rounded));
    await tester.pump(const Duration(milliseconds: 100));

    // 完整退出闭环（含成果面跳过）。
    await _confirmExit(tester);
    expect(find.text('实际专注 6 分钟'), findsOneWidget);
    await tester.tap(find.byKey(const Key('focus-outcome-skip')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 240));
    expect(find.byKey(const Key('u09-home-destination')), findsOneWidget);
    expect(sink.calls, hasLength(1));
  });
}
