import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/recovery/data/models/stuck_journey_models.dart';
import 'package:sparkle/features/recovery/data/repositories/stuck_journey_repository.dart';
import 'package:sparkle/features/recovery/presentation/providers/recovery_calibration_provider.dart';
import 'package:sparkle/features/recovery/presentation/widgets/recovery_calibration_section.dart';
import 'package:sparkle/features/recovery/presentation/widgets/stuck_journey_sheet.dart';
import 'package:sparkle/features/task/data/repositories/action_proposal_repository.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/widgets/action_proposal/proposal_card_models.dart';

/// V4-U02 ·「卡住 → 纠正 → 差异确认」垂直交互契约（每验收面一正一反）：
/// ① 三宿主同语义；abstain（无提案/系统不干预）纠正输入仍在场；
/// ② 保存偏好 ≠ 改任务（两写路径分离）；取消零写，原行动不变；
/// ③ 回执之后才成功反馈（时序反例钉）；unknown/版本冲突可恢复。
const String _kUnderstandingCorrectionsPath =
    '/experience/understanding-snapshot/corrections';

// ---------------------------------------------------------------------------
// fakes
// ---------------------------------------------------------------------------

/// X-03 统一 command path 的记录型假仓库（测试夹具，非生产行为）。
class _FakeProposalRepository implements ActionProposalRepository {
  _FakeProposalRepository();

  final List<Map<String, dynamic>> createCalls = <Map<String, dynamic>>[];
  final List<String> approveCalls = <String>[];
  final List<String> cancelCalls = <String>[];

  /// create 的返回（与真仓库同契约：**原始投影**，非 mutation 信封）。
  Map<String, dynamic> createResponse = _pendingProjection('p1');

  /// approve 的返回（可挂 Completer 做在途时序钉）。
  Completer<Map<String, dynamic>?>? approveGate;
  Object? approveResult;
  Exception? approveError;

  /// getProposal（重看权威面）的返回。
  Map<String, dynamic>? proposalDetail;

  @override
  Future<Map<String, dynamic>> createAdjustmentProposal({
    required String taskId,
    required Map<String, dynamic> fields,
    required String idempotencyKey,
    String? summary,
  }) async {
    createCalls.add(<String, dynamic>{
      'task_id': taskId,
      'fields': fields,
      'idempotency_key': idempotencyKey,
      'summary': summary,
    });
    return createResponse;
  }

  @override
  Future<Map<String, dynamic>?> getProposal(String proposalId) async =>
      proposalDetail;

  @override
  Future<Map<String, dynamic>?> approve(
    String proposalId,
    String idempotencyKey,
  ) async {
    approveCalls.add('$proposalId:$idempotencyKey');
    final gate = approveGate;
    if (gate != null && !gate.isCompleted) {
      return gate.future;
    }
    final error = approveError;
    if (error != null) throw error;
    return approveResult as Map<String, dynamic>?;
  }

  @override
  Future<Map<String, dynamic>?> cancel(
    String proposalId,
    String idempotencyKey,
  ) async {
    cancelCalls.add('$proposalId:$idempotencyKey');
    return <String, dynamic>{
      'proposal': _pendingProjection(proposalId)
        ..['status'] = 'CANCELLED',
    };
  }

  @override
  Future<List<ActionProposalCardData>> listForSubject(
    String subjectId, {
    String? status,
  }) async =>
      const <ActionProposalCardData>[];

  @override
  Future<Map<String, dynamic>?> reject(
    String proposalId,
    String idempotencyKey, {
    String? reason,
  }) async =>
      null;
}

/// 理解纠正面（M-08 写面）的记录型假 ApiClient。
class _RecordingApiClient extends ApiClient {
  _RecordingApiClient() : super(_UnusedRef());

  final List<Map<String, dynamic>> posts = <Map<String, dynamic>>[];
  Object? Function()? postResponse;

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    posts.add(<String, dynamic>{
      'path': path,
      if (data is Map) 'data': Map<String, dynamic>.from(data),
    });
    final body = postResponse?.call() ??
        <String, dynamic>{'status': 'updated', 'effect_on_policy': <String>[]};
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: body as T?,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 旅程读面的假仓库（abstain = main_intervention 恒 null）。
class _AbstainJourneyRepository implements StuckJourneyRepository {
  _AbstainJourneyRepository({this.throwOnStart = false});

  final bool throwOnStart;

  @override
  Future<StuckJourneyPayload> startJourney({
    required String surface,
    String? goalId,
    String? taskId,
  }) async {
    if (throwOnStart) throw Exception('network down');
    return StuckJourneyPayload.fromJson(_abstainPayload(surface));
  }

  @override
  Future<StuckJourneyPayload> answerQuestion({
    required String surface,
    required String questionId,
    required String branchKey,
    String? goalId,
    String? taskId,
  }) async =>
      StuckJourneyPayload.fromJson(_abstainPayload(surface));

  @override
  Future<StuckJourneyCorrectionResult> correct({
    required String surface,
    required String frictionType,
    String? interventionKey,
    String? goalId,
    String? taskId,
    String? reasonText,
  }) async =>
      StuckJourneyCorrectionResult.fromJson(<String, dynamic>{
        'journey': _abstainPayload(surface),
      });
}

// ---------------------------------------------------------------------------
// payloads / fixtures
// ---------------------------------------------------------------------------

Map<String, dynamic> _abstainPayload(String surface) => <String, dynamic>{
      'version': 'stuck_journey.v1',
      'surface': surface,
      'outcome': 'act',
      'friction_type': 'skill',
      'question': null,
      // abstain：系统这次不提案（无 intervention 可给）。
      'main_intervention': null,
      'uncertain': false,
      'context': <String, dynamic>{
        'goal': <String, dynamic>{'id': 'g1', 'title': '线代一轮复习'},
        'task': <String, dynamic>{'id': 't1', 'title': '特征值练习'},
        'recent_failures': <String, dynamic>{'count': 1, 'titles': <String>[]},
      },
      'receipt': <String, dynamic>{},
      'annotations': <String, dynamic>{},
    };

Map<String, dynamic> _pendingProjection(String id) => <String, dynamic>{
      'proposal_id': id,
      'status': 'PENDING',
      'command_type': 'task.update_fields',
      'source': 'recovery_sheet',
      'summary': '仅本次：今天只有十五分钟',
      'diff': <String, dynamic>{
        'before': <String, dynamic>{'estimated_minutes': 40},
        'after': <String, dynamic>{'estimated_minutes': 15},
        'changed_fields': <String>['estimated_minutes'],
      },
    };

Map<String, dynamic> committedMutationResponse({String receiptId = 'r-123'}) =>
    <String, dynamic>{
      'proposal': <String, dynamic>{
        ..._pendingProjection('p1'),
        'status': 'COMMITTED',
        'receipt': <String, dynamic>{
          'receipt_id': receiptId,
          'status': 'COMMITTED',
          'command_type': 'task.update_fields',
        },
      },
      'applied': true,
      'already_committed': false,
    };

/// 状态 committed 但**回执缺席**（回执门反例载荷）。
Map<String, dynamic> committedWithoutReceiptResponse() => <String, dynamic>{
      'proposal': <String, dynamic>{
        ..._pendingProjection('p1'),
        'status': 'COMMITTED',
        'receipt': null,
      },
      'applied': true,
    };

DioException dioConflict() => DioException(
      requestOptions: RequestOptions(path: '/action-proposals/p1/approve'),
      response: Response<void>(
        requestOptions: RequestOptions(path: '/action-proposals/p1/approve'),
        statusCode: 409,
      ),
      type: DioExceptionType.badResponse,
    );

TaskModel _anchorTask() => TaskModel(
      id: 't1',
      userId: 'user-1',
      title: '特征值练习',
      type: TaskType.learning,
      tags: const <String>['linear-algebra'],
      estimatedMinutes: 40,
      difficulty: 2,
      energyCost: 2,
      status: TaskStatus.stuck,
      priority: 1,
      createdAt: DateTime(2026, 9),
      updatedAt: DateTime(2026, 9, 20),
    );

class _StaticTaskListNotifier extends TaskNotifier {
  _StaticTaskListNotifier(List<TaskModel> tasks)
      : super(
          _UnusedTaskRepository(),
          _UnusedTaskNotificationScheduler(),
          _UnusedRef(),
        ) {
    state = TaskListState(tasks: tasks, todayTasks: tasks);
  }

  @override
  Future<void> loadTasks({TaskFilter? filter}) async {}

  @override
  Future<void> loadTodayTasks() async {}

  @override
  Future<void> loadRecommendedTasks() async {}

  @override
  Future<void> refreshTasks() async {}
}

class _UnusedTaskRepository extends TaskRepository {
  _UnusedTaskRepository() : super(_NoopApiClient());
}

class _UnusedTaskNotificationScheduler extends TaskNotificationScheduler {
  _UnusedTaskNotificationScheduler()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          _UnusedTaskNotificationIdMapper(),
        );
}

class _UnusedTaskNotificationIdMapper extends TaskNotificationIdMapper {}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedRef implements Ref {
  // dashboard_test_harness 同款占位：ApiClient 构造只把 read 结果丢进
  // interceptor 列表，不调用其成员——占位实例满足类型即可。
  @override
  T read<T>(ProviderListenable<T> provider) => InterceptorsWrapper() as T;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// harness
// ---------------------------------------------------------------------------

Future<ProviderContainer> _pumpSheet(
  WidgetTester tester, {
  required String surface,
  required _AbstainJourneyRepository journeyRepo,
  required _FakeProposalRepository proposalRepo,
  required _RecordingApiClient api,
  String? taskId = 't1',
  bool withAnchorTask = true,
}) async {
  final container = ProviderContainer(
    overrides: [
      stuckJourneyRepositoryProvider.overrideWithValue(journeyRepo),
      actionProposalRepositoryProvider.overrideWithValue(proposalRepo),
      apiClientProvider.overrideWithValue(api),
      taskListProvider.overrideWith(
        (ref) => _StaticTaskListNotifier(
          withAnchorTask ? [_anchorTask()] : const <TaskModel>[],
        ),
      ),
    ],
  );
  addTearDown(container.dispose);
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp(
        theme: ThemeData(extensions: [SparkleThemeExtension.light()]),
        locale: const Locale('zh'),
        supportedLocales: const [Locale('en'), Locale('zh')],
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: Scaffold(
          // 与真实 sheet 同构：DraggableScrollableSheet 内层是
          // SingleChildScrollView——测试 harness 同款包一层，内容超视口可滚达。
          body: SingleChildScrollView(
            child: StuckJourneySheetBody(
              request: StuckJourneyRequest(surface: surface, taskId: taskId),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return container;
}

Future<void> _submitConstraint(WidgetTester tester, String text) async {
  await tester.enterText(
    find.byKey(const Key('recovery-calibration-input-field')),
    text,
  );
  await tester.ensureVisible(
    find.byKey(const Key('recovery-calibration-submit')),
  );
  await tester.tap(find.byKey(const Key('recovery-calibration-submit')));
  await tester.pumpAndSettle();
}

/// 滚动可见后再点（校准区在 sheet 下半屏，超视口需先滚达）。
Future<void> _tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

/// 按宿主面 pump 一次（abstain 载荷；三宿主共用以钉同语义）。
Future<void> _pumpHost(
  WidgetTester tester,
  String surface, {
  required bool withAnchorTask,
  String? taskId,
}) async {
  await _pumpSheet(
    tester,
    surface: surface,
    taskId: taskId,
    journeyRepo: _AbstainJourneyRepository(),
    proposalRepo: _FakeProposalRepository(),
    api: _RecordingApiClient(),
    withAnchorTask: withAnchorTask,
  );
}

/// 三宿主同语义断言（同一组件、同一区标题、同一纠正输入）。
void _expectUnifiedSection() {
  expect(find.byType(RecoveryCalibrationSection), findsOneWidget);
  expect(find.text('说一句，就能调整'), findsOneWidget);
  expect(
    find.byKey(const Key('recovery-calibration-input-field')),
    findsOneWidget,
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
  });

  group('验收① 三宿主同语义 + abstain 纠正', () {
    testWidgets('正：home 宿主渲染同一校准区同一输入语义', (tester) async {
      await _pumpHost(tester, 'home', taskId: 't1', withAnchorTask: true);
      _expectUnifiedSection();
    });

    testWidgets('正：goal 宿主渲染同一校准区同一输入语义', (tester) async {
      await _pumpHost(tester, 'goal', withAnchorTask: false);
      _expectUnifiedSection();
    });

    testWidgets('正：action 宿主渲染同一校准区同一输入语义', (tester) async {
      await _pumpHost(tester, 'action', taskId: 't1', withAnchorTask: true);
      _expectUnifiedSection();
    });

    testWidgets('反例钉：abstain（系统不提案）时纠正输入仍在场', (tester) async {
      // abstain 载荷（main_intervention = null）。
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: _FakeProposalRepository(),
        api: _RecordingApiClient(),
      );
      expect(
        find.byKey(const Key('recovery-calibration-input-field')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('recovery-calibration-submit')),
        findsOneWidget,
      );
      // 反例钉：若有人把校准区重新挂回「有 intervention 才渲染」，此断言即红。
      expect(find.text('用一个练习把方法跑一遍'), findsNothing);
    });

    testWidgets('反例钉：旅程读面错误态下纠正输入同样在场', (tester) async {
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(throwOnStart: true),
        proposalRepo: _FakeProposalRepository(),
        api: _RecordingApiClient(),
      );
      expect(
        find.byKey(const Key('recovery-calibration-input-field')),
        findsOneWidget,
      );
    });

    testWidgets('正：提交纠正原话 → 约束/偏好分离选择（可不选）', (tester) async {
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: _FakeProposalRepository(),
        api: _RecordingApiClient(),
      );
      await _submitConstraint(tester, '不是不会，今天只有十五分钟');

      expect(find.text('你的纠正：不是不会，今天只有十五分钟'), findsOneWidget);
      expect(find.text('仅本次'), findsOneWidget);
      expect(find.text('保存为偏好'), findsOneWidget);
      expect(find.text('先都不用'), findsOneWidget);
      // 分离呈现：两条路径的后果说明并排可读。
      expect(find.text('只调整这一次行动，不改长期习惯'), findsOneWidget);
      expect(find.text('以后相似场景也参考；不改动当前任务'), findsOneWidget);
    });
  });

  group('验收② 保存偏好 ≠ 改任务；取消零写', () {
    testWidgets('正+反：保存为偏好只写理解纠正面，结构上零提案/任务写；中性 ack 无成功徽章',
        (tester) async {
      final proposalRepo = _FakeProposalRepository();
      final api = _RecordingApiClient();
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: api,
      );
      await _submitConstraint(tester, '以后这类情况先给小步骤');
      // 点卡片内的 CTA 按钮（容器中心不在按钮上）。
      await _tapVisible(tester, find.text('保存偏好'));
      await tester.pumpAndSettle();

      // 偏好写面：恰一次 POST 理解纠正（M-08 既有权威端点）。
      expect(api.posts, hasLength(1));
      expect(api.posts.single['path'], _kUnderstandingCorrectionsPath);
      expect(
        (api.posts.single['data'] as Map<String, dynamic>)['effect_scope'],
        'routing_policy',
      );
      expect(
        (api.posts.single['data'] as Map<String, dynamic>)['correction'],
        '以后这类情况先给小步骤',
      );

      // 反例钉（保存偏好 ≠ 改任务）：零提案创建/确认/取消，原行动不被触碰。
      expect(proposalRepo.createCalls, isEmpty);
      expect(proposalRepo.approveCalls, isEmpty);
      expect(proposalRepo.cancelCalls, isEmpty);

      // 中性 ack（非任务成功面孔）：文案在场，成功徽章类型结构性缺席。
      expect(find.textContaining('偏好已保存'), findsOneWidget);
      expect(find.textContaining('当前任务没有改动'), findsOneWidget);
      expect(find.byType(PixelSuccessBadge), findsNothing);
    });

    testWidgets('正：仅本次路径走 X-03 提案，偏好端点零调用；payload 钉死',
        (tester) async {
      final proposalRepo = _FakeProposalRepository();
      final api = _RecordingApiClient();
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: api,
      );
      await _submitConstraint(tester, '今天只有十五分钟');
      await _tapVisible(tester, find.text('调整这次行动'));
      await tester.pumpAndSettle();

      // 结构化调整：起点 = 基线 40（如实呈现当前值）。
      expect(find.text('40 分钟'), findsOneWidget);
      for (var i = 0; i < 5; i++) {
        await _tapVisible(
          tester,
          find.byKey(const Key('recovery-calibration-minutes-down')),
        );
      }
      expect(find.text('15 分钟'), findsOneWidget);
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-create-proposal')),
      );
      await tester.pumpAndSettle();

      // payload 钉：X-03 统一 command path（白名单字段 + source 标识）。
      expect(proposalRepo.createCalls, hasLength(1));
      expect(proposalRepo.createCalls.single['task_id'], 't1');
      expect(
        proposalRepo.createCalls.single['fields'],
        <String, dynamic>{'estimated_minutes': 15},
      );
      expect(
        proposalRepo.createCalls.single['idempotency_key'],
        startsWith('u02:t1:est:15:'),
      );
      // 反例钉（两写路径分离）：本路径零偏好写。
      expect(api.posts, isEmpty);

      // 服务端权威 diff 可读渲染（字段名进用户语言；值原文 40 → 15）。
      expect(find.text('调整前 → 调整后'), findsOneWidget);
      expect(find.text('预计时长（分）：'), findsOneWidget);
      expect(find.text('40 → 15'), findsOneWidget);
      // 生成提案 ≠ 改任务：零确认调用（等用户显式确认）。
      expect(proposalRepo.approveCalls, isEmpty);
    });

    testWidgets('正：无任务锚点时「仅本次」如实缺席（不出假入口），偏好路径照常',
        (tester) async {
      final proposalRepo = _FakeProposalRepository();
      final api = _RecordingApiClient();
      await _pumpSheet(
        tester,
        surface: 'goal',
        taskId: null,
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: api,
        withAnchorTask: false,
      );
      await _submitConstraint(tester, '先从定义开始');

      expect(
        find.byKey(const Key('recovery-calibration-this-time')),
        findsNothing,
      );
      expect(find.textContaining('没有任务锚点'), findsOneWidget);

      // 点卡片内的 CTA 按钮（容器中心不在按钮上）。
      await _tapVisible(tester, find.text('保存偏好'));
      await tester.pumpAndSettle();
      expect(find.textContaining('偏好已保存'), findsOneWidget);
      expect(proposalRepo.createCalls, isEmpty);
    });

    testWidgets('正：取消零写——scopeChoice「先都不用」与 diffReview「不调了」',
        (tester) async {
      final proposalRepo = _FakeProposalRepository();
      final api = _RecordingApiClient();
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: api,
      );
      await _submitConstraint(tester, '今天只有十五分钟');

      // (a) scopeChoice：先都不用 → 任何写路径零调用。
      await _tapVisible(tester, find.text('先都不用'));
      await tester.pumpAndSettle();
      expect(proposalRepo.createCalls, isEmpty);
      expect(api.posts, isEmpty);
      // 回到输入相，原话清空（会话内不残留半决策）。
      expect(
        find.byKey(const Key('recovery-calibration-input-field')),
        findsOneWidget,
      );

      // (b) diffReview：不调了 → 只取消提案（1 次），零 approve、零新 create。
      await _submitConstraint(tester, '今天只有十五分钟');
      await _tapVisible(tester, find.text('调整这次行动'));
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-create-proposal')),
      );
      await tester.pumpAndSettle();
      expect(proposalRepo.createCalls, hasLength(1));

      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-cancel-proposal')),
      );
      await tester.pumpAndSettle();
      expect(proposalRepo.cancelCalls, hasLength(1));
      expect(proposalRepo.approveCalls, isEmpty);
      expect(proposalRepo.createCalls, hasLength(1), reason: '不新增提案');
      expect(
        find.byKey(const Key('recovery-calibration-input-field')),
        findsOneWidget,
        reason: '回到输入相（原行动未被改动）',
      );
    });
  });

  group('验收③ 回执门 + unknown/版本冲突可恢复', () {
    testWidgets('正：确认后回执到场 → 才有成功面孔（含回执号）', (tester) async {
      final proposalRepo = _FakeProposalRepository()
        ..approveResult = committedMutationResponse(receiptId: 'r-abc');
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: _RecordingApiClient(),
      );
      await _submitConstraint(tester, '今天只有十五分钟');
      await _tapVisible(tester, find.text('调整这次行动'));
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-create-proposal')),
      );
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-confirm')),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('已按本次约束落账'), findsOneWidget);
      expect(find.textContaining('回执 r-abc'), findsOneWidget);
      expect(proposalRepo.approveCalls, hasLength(1));
    });

    testWidgets('反（时序钉）：回执到场之前零成功反馈——V3 AppFeedback.success '
        '反模式在此终结', (tester) async {
      final gate = Completer<Map<String, dynamic>?>();
      final proposalRepo = _FakeProposalRepository()..approveGate = gate;
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: _RecordingApiClient(),
      );
      await _submitConstraint(tester, '今天只有十五分钟');
      await _tapVisible(tester, find.text('调整这次行动'));
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-create-proposal')),
      );
      await tester.pumpAndSettle();

      // 确认按下 → 在途（approve 挂起）。
      // 在途态有 loading 指示器（永不 settle）——这里不能用 pumpAndSettle。
      await tester.ensureVisible(
        find.byKey(const Key('recovery-calibration-confirm')),
      );
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const Key('recovery-calibration-confirm')),
      );
      await tester.pump(const Duration(milliseconds: 100));

      // 时序反例钉：在途相**零**成功面孔、零成功 toast、零成功徽章。
      expect(find.textContaining('已按本次约束落账'), findsNothing);
      expect(find.byType(PixelSuccessBadge), findsNothing);
      expect(find.byType(SnackBar), findsNothing);
      expect(
        find.byKey(const Key('recovery-calibration-confirm')),
        findsOneWidget,
        reason: '确认钮仍在（loading 态）',
      );

      // 回执到场 → 成功面孔才出现（且只有这一刻）。
      gate.complete(committedMutationResponse(receiptId: 'r-late'));
      await tester.pumpAndSettle();
      expect(find.textContaining('已按本次约束落账'), findsOneWidget);
      expect(find.textContaining('回执 r-late'), findsOneWidget);
      expect(
        find.byType(SnackBar),
        findsNothing,
        reason: '成功呈现是回执驱动的状态相，不是动作驱动的 toast',
      );
    });

    testWidgets('反：状态 committed 但回执缺席 → 诚实 unknown，不给成功',
        (tester) async {
      final proposalRepo = _FakeProposalRepository()
        ..approveResult = committedWithoutReceiptResponse();
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: _RecordingApiClient(),
      );
      await _submitConstraint(tester, '今天只有十五分钟');
      await _tapVisible(tester, find.text('调整这次行动'));
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-create-proposal')),
      );
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-confirm')),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('没有收到回执'), findsOneWidget);
      expect(find.byType(PixelSuccessBadge), findsNothing);
      expect(find.textContaining('已按本次约束落账'), findsNothing);
      // 恢复出口在场：重新查看结果（读权威投影）。
      expect(
        find.byKey(const Key('recovery-calibration-recheck')),
        findsOneWidget,
      );
    });

    testWidgets('正：unknown → 重看权威投影拿到回执 → 补进成功相（真相赢，不重复写）',
        (tester) async {
      final proposalRepo = _FakeProposalRepository()
        ..approveResult = committedWithoutReceiptResponse()
        ..proposalDetail = committedMutationResponse()['proposal']
            as Map<String, dynamic>?;
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: _RecordingApiClient(),
      );
      await _submitConstraint(tester, '今天只有十五分钟');
      await _tapVisible(tester, find.text('调整这次行动'));
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-create-proposal')),
      );
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-confirm')),
      );
      await tester.pumpAndSettle();
      expect(find.textContaining('没有收到回执'), findsOneWidget);

      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-recheck')),
      );
      await tester.pumpAndSettle();
      expect(find.textContaining('已按本次约束落账'), findsOneWidget);
      expect(
        proposalRepo.approveCalls,
        hasLength(1),
        reason: '重看是读面，不重复确认',
      );
    });

    testWidgets('正+反：409 版本冲突 → 冲突面可恢复（无成功面孔）；按最新重调 = '
        '显式取消过期提案后回调整相', (tester) async {
      final proposalRepo = _FakeProposalRepository()
        ..approveError = dioConflict();
      final api = _RecordingApiClient();
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: api,
      );
      await _submitConstraint(tester, '今天只有十五分钟');
      await _tapVisible(tester, find.text('调整这次行动'));
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-create-proposal')),
      );
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-confirm')),
      );
      await tester.pumpAndSettle();

      // 冲突面（反例钉：冲突绝无成功视觉）。
      expect(find.textContaining('任务在这期间有变化'), findsOneWidget);
      expect(find.byType(PixelSuccessBadge), findsNothing);
      expect(find.textContaining('已按本次约束落账'), findsNothing);

      // 恢复路径 A：按最新状态重调（显式取消过期提案 → 回调整相）。
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-readjust')),
      );
      await tester.pumpAndSettle();
      expect(
        proposalRepo.cancelCalls,
        hasLength(1),
        reason: '过期提案显式取消（审计面留痕），不是静默丢弃',
      );
      expect(
        proposalRepo.createCalls,
        hasLength(1),
        reason: '尚未新建提案（新对照等用户再次生成）',
      );
      expect(
        find.text('40 分钟'),
        findsOneWidget,
        reason: '回到调整相（步进取值回到基线，等用户重新决定）',
      );

      // 恢复路径 B：冲突面直接取消 → 回输入相，零 approve。
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-create-proposal')),
      );
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-confirm')),
      );
      await tester.pumpAndSettle();
      expect(find.textContaining('任务在这期间有变化'), findsOneWidget);
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-cancel-proposal')),
      );
      await tester.pumpAndSettle();
      // 全程零成功确认：两次 approve 都被服务端 409 拒绝（假仓库记录的是
      // 拒绝的尝试）——任务从未被改动。
      expect(proposalRepo.approveCalls, hasLength(2));
      expect(
        find.byKey(const Key('recovery-calibration-input-field')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('recovery-calibration-input-field')),
        findsOneWidget,
      );
    });

    testWidgets('正：非冲突网络失败 → 回 diffReview + 如实错误行（幂等键不变可重试）',
        (tester) async {
      final proposalRepo = _FakeProposalRepository()
        ..approveError = DioException(
          requestOptions: RequestOptions(path: '/x'),
          type: DioExceptionType.connectionError,
        );
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: _RecordingApiClient(),
      );
      await _submitConstraint(tester, '今天只有十五分钟');
      await _tapVisible(tester, find.text('调整这次行动'));
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-create-proposal')),
      );
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-confirm')),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('没有连上'), findsOneWidget);
      expect(
        find.textContaining('没有收到回执'),
        findsNothing,
        reason: '网络失败 ≠ 结果未知：请求可能未达，不臆断结果',
      );
      expect(find.byType(PixelSuccessBadge), findsNothing);
      // 确认钮回到可用态（幂等键不变，重试安全）。
      expect(
        tester
            .widget<SparkleButton>(
              find.byKey(const Key('recovery-calibration-confirm')),
            )
            .onPressed,
        isNotNull,
      );
    });
  });

  group('控制器单元（fail-closed 细部）', () {
    testWidgets('分钟步进夹在 [5, 240]', (tester) async {
      final proposalRepo = _FakeProposalRepository();
      final container = await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: _RecordingApiClient(),
      );
      const args = RecoveryCalibrationArgs(taskId: 't1', baselineMinutes: 40);
      final notifier = container.read(recoveryCalibrationProvider(args).notifier);
      RecoveryCalibrationState stateOf() =>
          container.read(recoveryCalibrationProvider(args));
      // setAdjustedMinutes 只在 adjusting 相生效（守卫）；先进入该相。
      notifier.chooseThisTime();
      expect(stateOf().phase, RecoveryCalibrationPhase.adjusting);
      notifier.setAdjustedMinutes(2);
      expect(stateOf().adjustedMinutes, 5);
      notifier.setAdjustedMinutes(999);
      expect(stateOf().adjustedMinutes, 240);
    });

    testWidgets('approve 返回畸形载荷（缺 proposal 投影）→ unknown 不给成功',
        (tester) async {
      final proposalRepo = _FakeProposalRepository()
        ..approveResult = <String, dynamic>{'unexpected': true};
      await _pumpSheet(
        tester,
        surface: 'action',
        journeyRepo: _AbstainJourneyRepository(),
        proposalRepo: proposalRepo,
        api: _RecordingApiClient(),
      );
      await _submitConstraint(tester, '今天只有十五分钟');
      await _tapVisible(tester, find.text('调整这次行动'));
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-create-proposal')),
      );
      await tester.pumpAndSettle();
      await _tapVisible(
        tester,
        find.byKey(const Key('recovery-calibration-confirm')),
      );
      await tester.pumpAndSettle();
      expect(find.textContaining('没有收到回执'), findsOneWidget);
      expect(find.byType(PixelSuccessBadge), findsNothing);
    });
  });
}
