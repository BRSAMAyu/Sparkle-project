/*
FIX-584 · G5 校准投影缺口回归（V4-Q01 揭案）：

向导直达面（wizard-direct）此前零任务列表投影填充——`_createGoal` 服务端
建 goal+plan+tasks 后，「开始第一个任务」CTA 直达执行面，而恢复校准区时长
锚点（`stuck_journey_sheet._resolveBaselineMinutes` 只读 `taskListProvider`
投影）解析不到新任务 → baselineMinutes=null →「调整这次行动」结构性缺席
（hasAnchor 门如实不出假入口；Q01 attempt10/r5 DB+console 实证：calibration
runs 落账在场、tasks 4 行 estimated_minutes=25，缺的只是客户端投影）。
种子面（pilot）无此缺口：任务先于投影构造存在，构造期 loadTasks 即含锚点。

本测试在传输边界 mock（与 O11 submit-chain 同款手法：真仓库 + 真向导屏 +
真 TaskNotifier/TaskRepository，只 mock HttpClientAdapter），服务端真值
模拟对齐 Q01 r5 console 实证：GET /tasks 无 today 过滤、向导任务 due_date
=null 且创建后即可从全量列表读回；goal 创建前列表为空（fresh guest）。

两钉：
① 填充钉——创建成功后 taskListProvider 投影含新任务（修前 RED：向导
   分支零填充调用，投影停留在构造期空列表）；
② 锚点钉——同容器投影水化后挂真实 StuckJourneySheetBody（G5 面），
   纠正提交进 scopeChoice 相后「调整这次行动」在场、「无任务锚点」如实
   缺席文案不在场（baselineMinutes 非 null 的端到端可观察面）。
*/
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/auth/data/models/token_model.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show sharedPreferencesProvider;
import 'package:sparkle/features/goal/presentation/screens/goal_creation_wizard_screen.dart';
import 'package:sparkle/features/recovery/data/models/stuck_journey_models.dart';
import 'package:sparkle/features/recovery/data/repositories/stuck_journey_repository.dart';
import 'package:sparkle/features/recovery/presentation/widgets/stuck_journey_sheet.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';

import '../../../shared/i18n_test_helper.dart';

const String _kAnchorTaskId = 'task-fix584-1';
const int _kAnchorMinutes = 25;

/// 服务端真值模拟：任务只在本 worktree 的 goal 创建成功后才存在（fresh
/// guest 时间线）；GET /tasks 返回全量分页列表（后端无 today 过滤——Q01
/// r5 console line369 实证 4 个 due_date=null 的向导任务全量可读回）。
class _ServerTruthAdapter implements HttpClientAdapter {
  final List<_RecordedRequest> requests = <_RecordedRequest>[];

  bool goalCreated = false;

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(_RecordedRequest(method: options.method, path: options.path));
    // 意图分析 404 → 向导走文档化 legacy 回退（O11 同款驾驶路径）。
    if (options.method == 'POST' && options.path == '/goals/analyze-intent') {
      return _jsonBody(404, <String, dynamic>{'error': 'route not found'});
    }
    if (options.method == 'POST' &&
        options.path == '/goals/decompose-preview') {
      return _jsonBody(200, <String, dynamic>{
        'goal_type': 'exam',
        'time_horizon': 'short',
        'suggested_target_date': '2026-10-10',
        'rationale': 'Visible checkpoints keep the goal editable.',
        'milestones': <Map<String, dynamic>>[
          <String, dynamic>{
            'id': 'm1',
            'title': 'Map the baseline',
            'description': 'Confirm weak topics.',
            'estimated_days': 7,
            'acceptance_criteria': <String>['Baseline exists'],
          },
        ],
      });
    }
    if (options.method == 'POST' && (options.path == '/goals/' || options.path == '/goals')) {
      goalCreated = true;
      return _jsonBody(200, <String, dynamic>{
        'id': 'goal-fix584',
        'title': '通过高数考试',
        'goal_type': 'exam',
        'status': 'active',
        'first_task_id': _kAnchorTaskId,
      });
    }
    // 任务全量列表：创建前空（投影构造期真值），创建后含向导任务
    //（due_date=null——锚点只能从全量 tasks 解析，today 永不含它）。
    if (options.method == 'GET' &&
        (options.path.startsWith('/tasks?') || options.path == '/tasks')) {
      final tasks = goalCreated
          ? <Map<String, dynamic>>[_wizardTaskJson()]
          : <Map<String, dynamic>>[];
      return _jsonBody(200, <String, dynamic>{
        'data': tasks,
        'meta': <String, dynamic>{
          'total': tasks.length,
          'page': 1,
          'page_size': 50,
        },
      });
    }
    if (options.method == 'GET' && options.path == '/tasks/today') {
      // 向导任务无 due date——今日面恒不含（与 r5 console 一致）。
      return _jsonBody(200, <dynamic>[]);
    }
    if (options.method == 'GET' && options.path == '/tasks/recommended') {
      return _jsonBody(200, <dynamic>[]);
    }
    // 其余（场景包匹配等）——空成功载荷。
    return _jsonBody(200, <String, dynamic>{});
  }

  static Map<String, dynamic> _wizardTaskJson() => <String, dynamic>{
        'id': _kAnchorTaskId,
        'created_at': '2026-09-29T10:38:36.383807',
        'updated_at': '2026-09-29T10:38:36.383809',
        'title': 'Map the baseline',
        'type': 'LEARNING',
        'status': 'PENDING',
        'tags': <String>['goal_milestone', 'goal_milestone:m4'],
        'estimated_minutes': _kAnchorMinutes,
        'difficulty': 3,
        'energy_cost': 2,
        'priority': 0,
        'due_date': null,
        'user_id': 'user-fix584',
        'plan_id': 'plan-fix584',
        'guide_content': null,
        'started_at': null,
        'confirmed_at': null,
        'completed_at': null,
        'paused_at': null,
        'paused_reason': null,
        'actual_minutes': null,
        'user_note': null,
        'knowledge_node_id': null,
        'tool_result_id': null,
        'execution_mode': null,
        'order_index': 0,
        'subtasks_total': 0,
        'subtasks_completed': 0,
        'guide_json': null,
        'ai_prompt': null,
        'source_planning_session_id': null,
        'phase_index': null,
        'success_criteria': null,
        'action_plan': null,
        'bound_sources': <dynamic>[],
        'is_example': false,
      };

  static ResponseBody _jsonBody(int code, Object body) => ResponseBody.fromString(
        jsonEncode(body),
        code,
        headers: <String, List<String>>{
          Headers.contentTypeHeader: <String>['application/json'],
        },
      );
}

class _RecordedRequest {
  const _RecordedRequest({required this.method, required this.path});

  final String method;
  final String path;
}

class _FakeAuthRepository implements AuthRepository {
  @override
  Future<String?> getAccessToken() async => 'test-access';

  @override
  Future<String?> getToken() async => 'test-access';

  @override
  Future<String?> getRefreshToken() async => 'test-refresh';

  @override
  Future<TokenResponse> refreshToken() async => TokenResponse(
        accessToken: 'test-access',
        refreshToken: 'test-refresh',
      );

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// abstain 载荷（校准区恒渲染语义：旅程判定无关纠正在场性）。
class _FakeStuckRepository implements StuckJourneyRepository {
  @override
  Future<StuckJourneyPayload> startJourney({
    required String surface,
    String? goalId,
    String? taskId,
  }) async =>
      StuckJourneyPayload.fromJson(<String, dynamic>{
        'version': 'stuck_journey.v1',
        'surface': surface,
        'outcome': 'abstain',
        'friction_type': 'unknown',
        'question': null,
        'main_intervention': null,
        'uncertain': false,
        'context': <String, dynamic>{
          'goal': <String, dynamic>{'id': 'goal-fix584', 'title': '通过高数考试'},
          'task': <String, dynamic>{
            'id': _kAnchorTaskId,
            'title': 'Map the baseline',
          },
          'recent_failures': <String, dynamic>{'count': 0, 'titles': <String>[]},
        },
        'receipt': <String, dynamic>{},
        'annotations': <String, dynamic>{},
      });

  @override
  Future<StuckJourneyPayload> answerQuestion({
    required String surface,
    required String questionId,
    required String branchKey,
    String? goalId,
    String? taskId,
  }) async =>
      throw UnimplementedError('FIX-584 用例不触 answer');

  @override
  Future<StuckJourneyCorrectionResult> correct({
    required String surface,
    required String frictionType,
    String? interventionKey,
    String? goalId,
    String? taskId,
    String? reasonText,
  }) async =>
      throw UnimplementedError('FIX-584 用例不触 correct');
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  /// 与 O11 submit-chain 同款环境：真 ApiClient（mock 传输）+ 真向导屏 +
  /// 真 TaskNotifier/TaskRepository（单容器共享，测试可直接读投影状态）。
  Future<(ProviderContainer, _ServerTruthAdapter)> buildWorld(
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final prefs = await SharedPreferences.getInstance();
    final container = ProviderContainer(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
        // 真仓库 + mock 传输；不牵 SyncEngine/读缓存（本卡语义无关）。
        taskRepositoryProvider.overrideWith(
          (ref) => TaskRepository(ref.watch(apiClientProvider)),
        ),
        // 旅程仓库注入 abstain 载荷（G5 面用；向导阶段不触它，无害）。
        stuckJourneyRepositoryProvider.overrideWithValue(
          _FakeStuckRepository(),
        ),
      ],
    );
    addTearDown(container.dispose);
    final client = container.read(apiClientProvider);
    final adapter = _ServerTruthAdapter();
    client.dio.httpClientAdapter = adapter;
    return (container, adapter);
  }

  /// 种子投影（模拟首页驾驶舱先行构造 taskListProvider：fresh guest 空
  /// 列表）——没有这一步，断言时懒构造也会拿到新数据，修前形态测不红。
  /// 构造期三读是纯微任务 + 零长定时器：testWidgets 的 FakeAsync 区里
  /// 定时器只能由 pump 驱动（Future.delayed 直 await = 永久死等）。
  Future<void> warmProjection(
    ProviderContainer container,
    WidgetTester tester,
  ) async {
    container.read(taskListProvider);
    await tester.pump();
    await tester.pump();
  }

  /// 驾驶向导走 legacy 全路径到创建成功（O11 submit-chain 同款步法）。
  Future<void> driveWizardToCreated(WidgetTester tester) async {
    await tester.enterText(find.byType(TextField), '通过高数考试');
    await tester.tap(find.widgetWithText(FilledButton, '让我先看看你的情况'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '继续'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).at(0), '通过高数考试');
    await tester.pump();
    await tester.enterText(find.byType(TextField).at(1), '奖学金需要这门成绩');
    await tester.pump();
    await tester.tap(find.widgetWithText(FilledButton, '继续'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '继续'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('继续'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('创建'));
    await tester.pumpAndSettle();
  }

  testWidgets('FIX-584 ①: 向导创建成功后任务列表投影含新任务（填充钉）',
      (tester) async {
    final (container, adapter) = await buildWorld(tester);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: testMaterialApp(
          home: GoalCreationWizardScreen(
            onCreated: (goal) {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // fresh guest 时间线：投影构造期列表为空（服务端还没有任务）。
    await warmProjection(container, tester);
    expect(
      container.read(taskListProvider).tasks,
      isEmpty,
      reason: '前置：创建前投影为空（fresh guest），否则填充钉测不中缺口',
    );

    await driveWizardToCreated(tester);

    // 填充钉：创建成功后投影已含向导任务（服务端真值经单一填充函数
    // TaskNotifier.refreshTasks 进投影；修前零填充调用 → 停留空列表 RED）。
    final tasks = container.read(taskListProvider).tasks;
    expect(
      tasks.where((t) => t.id == _kAnchorTaskId),
      hasLength(1),
      reason: '向导直达分支创建成功后必须填充任务列表投影'
          '（G5：校准锚点只读该投影，缺口=baselineMinutes=null）',
    );
    expect(
      tasks.firstWhere((t) => t.id == _kAnchorTaskId).estimatedMinutes,
      _kAnchorMinutes,
    );
    // 填充走的是真实读侧：传输层确实发生过 GET /tasks。
    expect(
      adapter.requests
          .where((r) => r.method == 'GET' && r.path.startsWith('/tasks'))
          .isNotEmpty,
      isTrue,
    );
  });

  testWidgets('FIX-584 ②: 向导直达面校准锚点非 null——「调整这次行动」在场（G5 面）',
      (tester) async {
    final (container, _) = await buildWorld(tester);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: testMaterialApp(
          home: GoalCreationWizardScreen(
            onCreated: (goal) {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await warmProjection(container, tester);
    await driveWizardToCreated(tester);
    await tester.pump();
    await tester.pump();

    // G5 现场复原：向导任务创建后（投影已按修复填充），在执行面挂真实
    // 恢复 sheet——校准区时长锚点从任务列表投影解析（旅程仓库 abstain
    // 载荷已在容器 override 注入；校准区恒渲染与旅程判定无关）。
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: testMaterialApp(
          home: const Scaffold(
            body: SingleChildScrollView(
              child: StuckJourneySheetBody(
                request: StuckJourneyRequest(
                  surface: 'action',
                  taskId: _kAnchorTaskId,
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // 提交纠正原话 → scopeChoice 相：hasAnchor 门打开（baselineMinutes
    // 非 null 的端到端可观察面）。
    await tester.enterText(
      find.byKey(const Key('recovery-calibration-input-field')),
      '不是不会，今天只有十五分钟',
    );
    await tester.tap(find.byKey(const Key('recovery-calibration-submit')));
    await tester.pumpAndSettle();

    expect(
      find.text('调整这次行动'),
      findsOneWidget,
      reason: '向导直达面（wizard-direct）baselineMinutes 必须非 null：'
          '投影填充后校准区「仅本次」入口结构性在场（Q01 G5 缺口反面）',
    );
    expect(
      find.text('仅本次调整需要一个具体任务作锚点；当前入口没有任务锚点，'
          '可以先保存偏好或直接关闭'),
      findsNothing,
      reason: '有锚点时「无任务锚点」如实缺席文案不得在场（hasAnchor 门单侧）',
    );
  });
}
