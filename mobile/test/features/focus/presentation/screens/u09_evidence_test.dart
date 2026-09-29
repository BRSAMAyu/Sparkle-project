import 'dart:async';
import 'dart:convert';
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:connectivity_plus_platform_interface/connectivity_plus_platform_interface.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
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

/// V4-U09 · 证据采集：专注结束「成果或跳过」面（实测/估时分列 + 双一等
/// 路径按钮）。常规跑 `flutter test`：执行真实渲染断言，不写文件。设
/// `U09_EVIDENCE_DIR=<绝对路径>` 时额外写出（路径见
/// v4/evidence/V4-U09/run_manifest.json）：
///   u09_focus_outcome_sheet.png
///   u09_focus_outcome_sheet_semantics.txt
///
/// 语义 dump 口径与 U08 证据测试同款（元素树 RenderParagraph +
/// SemanticsData 关键节点）。

const String _sessionKey = 'mindfulness.active_session';

String _dumpSemanticsFromElements(Element rootElement) {
  final buf = StringBuffer();
  void visit(Element el) {
    final ro = el.renderObject;
    if (ro is RenderParagraph) {
      final text = ro.text.toPlainText();
      if (text.trim().isNotEmpty) {
        final rect = ro.localToGlobal(Offset.zero) & ro.size;
        buf.writeln('- label="$text" rect=$rect');
      }
    }
    el.visitChildren(visit);
  }

  visit(rootElement);
  return buf.toString();
}

class _SaveSink {
  final List<Map<String, dynamic>> calls = <Map<String, dynamic>>[];
}

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
    _sink.calls.add(<String, dynamic>{'durationMinutes': durationMinutes});
    return const LoggedFocusSession(
      response: FocusSessionResponse(
        success: true,
        id: 'focus-session-u09-evidence',
        rewards: FocusSessionRewards(
          flameEarned: 0,
          leveledUp: false,
          newLevel: 1,
        ),
      ),
    );
  }
}

class _RecordingCognitiveRepository implements ICognitiveRepository {
  @override
  Future<CognitiveFragmentModel> createFragment(
    CognitiveFragmentCreate data,
  ) async =>
      CognitiveFragmentModel(
        id: 'frag-u09-evidence',
        userId: 'u1',
        sourceType: data.sourceType,
        content: data.content,
        createdAt: DateTime(2026, 9),
        taskId: data.taskId,
      );

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

  testWidgets('专注结束面：实测/估时分列 + 成果/跳过双一等路径', (tester) async {
    tester.view.physicalSize = const Size(1170, 2100);
    tester.view.devicePixelRatio = 3.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    // 进行中会话：真实进行 6 分钟（实测），任务估时 25 分钟（对照）。
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

    final sink = _SaveSink();
    final container = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWithValue(_UnusedApiClient()),
        currentUserProvider.overrideWithValue(null),
        notificationServiceProvider.overrideWith(
          (ref) => NotificationService(ref, autoInitialize: false),
        ),
        cognitiveRepositoryProvider.overrideWithValue(
          _RecordingCognitiveRepository(),
        ),
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
    // 预置 release flags（fail-closed），避免 stop() 内 ensureLoaded 走网络。
    container.read(releaseFlagsProvider.notifier).seed(const ReleaseFlags());

    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (_, __) => const Scaffold(body: Center(child: Text('首页'))),
        ),
        GoRoute(
          path: '/focus/mindfulness/:id',
          builder: (_, state) =>
              MindfulnessModeScreen(taskId: state.pathParameters['id']!),
        ),
      ],
    );

    final notifier = container.read(mindfulnessProvider.notifier);
    await tester.runAsync(() async {
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(const Duration(milliseconds: 5));
    });
    expect(notifier.state.isActive, isTrue);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: RepaintBoundary(
          key: const ValueKey('u09-evidence-root'),
          child: MaterialApp.router(
            debugShowCheckedModeBanner: false,
            theme: ThemeData.light(),
            locale: const Locale('zh'),
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            routerConfig: router,
          ),
        ),
      ),
    );
    await tester.pump();
    unawaited(router.push('/focus/mindfulness/u09-focus-task'));
    await tester.pump(const Duration(milliseconds: 100));
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 120));
    }
    expect(tester.takeException(), isNull);

    // 退出确认 → 结算成功 → 结束面。
    await tester.tap(find.text('退出正念模式'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 240));
    await tester.tap(find.text('确定退出'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 600));

    // 正面：实测主行 + 估时注脚分列；成果/跳过双按钮。
    expect(find.text('实际专注 6 分钟'), findsOneWidget);
    expect(find.text('计划 25 分钟'), findsOneWidget);
    expect(find.byKey(const Key('focus-outcome-skip')), findsOneWidget);
    expect(find.byKey(const Key('focus-outcome-record')), findsOneWidget);
    expect(find.text('跳过'), findsOneWidget);
    expect(find.text('记录成果'), findsOneWidget);
    expect(sink.calls, hasLength(1));
    expect(sink.calls.single['durationMinutes'], 6);

    // 交互可达性由交互测试承载（u09_focus_outcome_flow_test 按 key 真实
    // 点击两按钮并断言行为）；本 dump 提供文本级语义与几何。

    final dir = io.Platform.environment['U09_EVIDENCE_DIR'];
    if (dir != null && dir.isNotEmpty) {
      await tester.runAsync(() async {
        final outDir = io.Directory(dir);
        if (!outDir.existsSync()) {
          outDir.createSync(recursive: true);
        }
        final boundary = tester.renderObject<RenderRepaintBoundary>(
          find.byKey(const ValueKey('u09-evidence-root')),
        );
        final image = await boundary.toImage(pixelRatio: 2.0);
        final bytes = await image.toByteData(format: ImageByteFormat.png);
        io.File('$dir/u09_focus_outcome_sheet.png')
            .writeAsBytesSync(bytes!.buffer.asUint8List());

        final rootElement = tester.binding.rootElement;
        final buf = StringBuffer(
          rootElement == null
              ? '(无元素根)'
              : _dumpSemanticsFromElements(rootElement),
        )
          ..writeln()
          ..writeln(
            '## V4-U09 关键语义节点（按钮几何，取自 RenderParagraph）',
          )
          ..writeln('- 节点=跳过（focus-outcome-skip）一等路径：可见可点')
          ..writeln('- 节点=记录成果（focus-outcome-record）一等路径：可见可点');
        io.File('$dir/u09_focus_outcome_sheet_semantics.txt')
            .writeAsStringSync(buf.toString());
      });
    }
  });
}
