import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/home/data/episode_resume_models.dart';
import 'package:sparkle/features/home/presentation/providers/episode_resume_provider.dart';
import 'package:sparkle/features/journey/data/repositories/first_action_repository.dart';
import 'package:sparkle/features/journey/presentation/widgets/first_action_card.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';
import 'package:sparkle/features/task/data/repositories/action_proposal_repository.dart';

import '../../shared/i18n_test_helper.dart';

/// V4-U06 验收② · 首卡确认反馈与 W2 bootstrap（FIX-567 触发链）——
/// 「首卡与确认文案、DB 同一次 receipt 一致」+「新手确认后真实 receipt 可見」。
///
/// 面一（重开回放一致性）：已 commit 面 → 回执行（`first-action-receipt-line`）
/// 的回执身份 = 同一 GET 读面（/journey/first-action）投影的 proposal_id，
/// 禁本地拼装；未确认零 I01。
/// 面二（W2 bootstrap 正，真实 UI 动作）：PENDING → 用户点「开始这一步」→
/// 一次性 I01（既有 episodeResumeTask 端点，零新端点）携带既有
/// `context_selection://<latest>` ref → 服务端落账首条 resume_view →
/// 回执读面刷新；U01 角色门原样（夹具仍回 chat_context → 派生面 hidden）。
/// 面三（诚实门，反）：
///   a) mode off（modeGated）→ bootstrap 零请求（不预造、不旁路）；
///   b) bootstrap I01 网络失败 → 不上抛、不假成功；
///   c) 无任务（tasks 空）→ commit 面缺席（守门）+ bootstrap 零请求。
class _RecordingApi implements ApiClient {
  _RecordingApi({this.viewPayload, this.error});

  Object? viewPayload;
  DioException? error;
  final List<({String path, Map<String, dynamic>? query})> gets = [];

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    gets.add((path: path, query: queryParameters));
    final err = error;
    if (err != null) {
      throw err;
    }
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: viewPayload as T?,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('stub only implements get');
}

/// 脚本化仓库：approve 前返回 PENDING 状态，approve 后返回 COMMITTED 状态
/// （幂等键记录留痕——确认必须真实到达 command 层）。
class _ScriptedRepository extends FirstActionRepository {
  _ScriptedRepository(this.pending, this.committed)
      : super(_FakeApi(), _FakeProposalRepo());

  final FirstActionState pending;
  final FirstActionState committed;

  final approved = <String>[];

  @override
  Future<Map<String, dynamic>?> approve(
    String proposalId,
    String idempotencyKey,
  ) async {
    approved.add(proposalId);
    return const <String, dynamic>{};
  }

  @override
  Future<FirstActionState?> fetchState() async =>
      approved.isEmpty ? pending : committed;
}

class _FakeApi extends Fake implements ApiClient {}

class _FakeProposalRepo extends Fake implements ActionProposalRepository {}

Map<String, dynamic> _receiptPayload({String role = 'chat_context'}) => {
      'mode': 'live',
      'schema_version': 'context_selection_receipt.v1',
      'receipt': {
        'schema_version': 'context_selection_receipt.v1',
        'receipt_id': 'csr_U06BOOT',
        'selection_role': role,
        'decision_id': null,
        'input_versions': {
          'memory_epoch': 3,
          'selector_version': 'context_pack.v4-i06.v1',
        },
        'candidates': <Map<String, dynamic>>[
          {'ref': 'task://t1', 'status': 'selected', 'reason_code': null, 'note': null},
        ],
        'budget': {'candidate_scan_limit': 12, 'selected_max': 6, 'clarifications_used': 0},
        'why_now': null,
      },
      'source_verification': <Map<String, dynamic>>[],
      'resolved_selected_count': 1,
    };

Map<String, dynamic> _resumePayload({String taskId = 'task-new-1'}) => {
      'view': {
        'schema_version': kEpisodeResumeViewSchemaVersion,
        'goal_ref': 'goal://g1',
        'task_ref': 'task://$taskId',
        'run_ref': null,
        'last_valid_outcome': null,
        'last_confirmed_step': {
          'step_ref': 'subtask://s1',
          'description': '读完第三章前两节',
          'confirmed_at': '2026-09-28T10:05:00',
          'version_token': 'tok-1',
        },
        'pending_human_step': {
          'description': '做第三章末尾的三道练习题',
          'cognitive_ownership': 'user_led',
          'execution_mode': 'assisted',
        },
        'why_now': null,
        'expires_at': '2099-01-01T00:00:00',
        'freshness': {
          'context_receipt_ref': 'context_selection://csr_U06BOOT',
          'computed_at': '2026-09-28T12:00:00',
          'memory_epoch_at_compute': 3,
        },
      },
      'reason_code': null,
      'warnings': <String>[],
    };

FirstActionState _pendingState() => const FirstActionState(
      goal: FirstActionGoal(goalId: 'g1', title: '两周内做出可展示的比赛 demo'),
      proposal: <String, dynamic>{
        'proposal_id': 'p-receipt-1',
        'status': 'PENDING',
        'payload': <String, dynamic>{
          'tasks': <Map<String, dynamic>>[
            <String, dynamic>{
              'title': '写下 demo 的 30 秒演示脚本',
              'estimated_minutes': 30,
              'action_plan': <String, dynamic>{
                'desired_outcome': '30 秒演示脚本草稿',
                'smallest_useful_step': <String, dynamic>{
                  'description': '用一页纸写清评委将看到的三个画面',
                  'useful_because': <String>['produces_artifact'],
                },
                'completion_evidence': <Map<String, dynamic>>[
                  <String, dynamic>{'evidence_kind': 'artifact'},
                ],
                'execution_mode': 'hybrid',
                'cognitive_ownership': 'user_core',
              },
            },
          ],
        },
      },
    );

FirstActionState _committedState({String taskId = 'task-new-1'}) =>
    FirstActionState(
      goal: const FirstActionGoal(goalId: 'g1', title: '两周内做出可展示的比赛 demo'),
      proposal: const <String, dynamic>{
        'proposal_id': 'p-receipt-1',
        'status': 'COMMITTED',
        'payload': <String, dynamic>{},
      },
      tasks: [
        FirstActionTaskRef(
          id: taskId,
          title: '写下 demo 的 30 秒演示脚本',
          status: 'todo',
        ),
      ],
    );

void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });
  tearDown(tearDownI18n);

  late _ScriptedRepository repository;
  late _RecordingApi resumeApi;

  Future<ProviderContainer> pumpCard(
    WidgetTester tester, {
    Object? receiptPayload,
    DioException? resumeError,
  }) async {
    resumeApi = _RecordingApi(
      viewPayload: _resumePayload(),
      error: resumeError,
    );
    final container = ProviderContainer(
      overrides: [
        firstActionRepositoryProvider.overrideWithValue(repository),
        apiClientProvider.overrideWithValue(resumeApi),
        contextReceiptProvider.overrideWith(
          (ref) => ContextReceiptNotifier(
            _RecordingApi(viewPayload: receiptPayload ?? _receiptPayload()),
          ),
        ),
      ],
    );
    addTearDown(container.dispose);
    // 预热回执读面（bootstrap 携带 ref 的来源；真实 app 中 provider 创建即 load）。
    await container.read(contextReceiptProvider.notifier).load();
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: testMaterialApp(
          theme: ThemeData.light()
              .copyWith(extensions: [SparkleThemeExtension.light()]),
          home: const Scaffold(
            body: SingleChildScrollView(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: FirstActionCard(),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    return container;
  }

  testWidgets('面一：重开回放——commit 面回执行与同一 GET 读面一致，未确认零 I01',
      (tester) async {
    resumeApi = _RecordingApi(viewPayload: _resumePayload());
    final committedOnlyRepo = _CommittedOnlyRepo();
    final container = ProviderContainer(
      overrides: [
        firstActionRepositoryProvider.overrideWithValue(committedOnlyRepo),
        apiClientProvider.overrideWithValue(resumeApi),
        contextReceiptProvider.overrideWith(
          (ref) =>
              ContextReceiptNotifier(_RecordingApi(viewPayload: _receiptPayload())),
        ),
      ],
    );
    addTearDown(container.dispose);
    await container.read(contextReceiptProvider.notifier).load();
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: testMaterialApp(
          theme: ThemeData.light()
              .copyWith(extensions: [SparkleThemeExtension.light()]),
          home: const Scaffold(
            body: SingleChildScrollView(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: FirstActionCard(),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('已创建任务：写下 demo 的 30 秒演示脚本'), findsOneWidget);
    final receiptLine = find.byKey(const ValueKey('first-action-receipt-line'));
    expect(receiptLine, findsOneWidget,
        reason: '确认后真实 receipt 必须可见（本卡前仅 invalidate 无反馈）',);
    expect(
      tester.widget<Text>(receiptLine).data,
      contains('p-receip'),
      reason: '回执身份与同一 GET 读面的 proposal_id 一致（展示级截断，非本地拼装）',
    );
    expect(resumeApi.gets, isEmpty, reason: '纯回放面零 I01 请求');
  });

  testWidgets('面二（W2 bootstrap 正）：确认 → 一次性 I01 携既有 ref，latest 读面刷新',
      (tester) async {
    repository = _ScriptedRepository(_pendingState(), _committedState());
    final container = await pumpCard(tester);

    // PENDING 确认面 → 用户真实点击「开始这一步」。
    expect(find.text('开始这一步'), findsOneWidget);
    await tester.tap(find.text('开始这一步'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(repository.approved, ['p-receipt-1'],
        reason: '确认必须真实到达 command 层（真实 UI 动作，非 provider 直捅）',);

    // W2 bootstrap：一次性 I01，taskId = 新任务，ref = 既有 latest 回执
    // （chat_context 角色——服务端只校验 scheme，产出首条 resume_view）。
    expect(resumeApi.gets.length, 1, reason: 'bootstrap 恰一次 I01（一次性生产触发）');
    expect(
      resumeApi.gets.single.path,
      ApiEndpoints.episodeResumeTask('task-new-1'),
    );
    expect(
      resumeApi.gets.single.query?['context_receipt_ref'],
      'context_selection://csr_U06BOOT',
      reason: '携带既有 context_selection:// ref（scheme 契约；角色由服务端裁决落账）',
    );

    // 确认后 commit 面浮现 + 回执行投影同一 GET。
    expect(find.text('已创建任务：写下 demo 的 30 秒演示脚本'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('first-action-receipt-line')),
      findsOneWidget,
    );

    // U01 角色门原样：夹具 latest 仍是 chat_context → 派生面保持 hidden
    // （bootstrap 是独立生产触发，不是门的旁路——反例语义与
    // episode_resume_provider_test 的角色门套件同源）。
    final resume = await container.read(episodeResumeProvider.future);
    expect(resume.phase, EpisodeResumePhase.hidden);
  });

  testWidgets('反 a：mode off（modeGated）→ 确认后 bootstrap 零请求（不预造接续）',
      (tester) async {
    repository = _ScriptedRepository(_pendingState(), _committedState());
    await pumpCard(
      tester,
      receiptPayload: {
        'mode': 'off',
        'schema_version': 'context_selection_receipt.v1',
        'receipt': null,
      },
    );

    await tester.tap(find.text('开始这一步'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(repository.approved, ['p-receipt-1']);
    expect(resumeApi.gets, isEmpty,
        reason: 'mode off → 无回执可携 → 零 I01（接续条诚实缺席，B05§2 客户端不预造）',);
  });

  testWidgets('反 b：bootstrap I01 网络失败 → 不上抛、不假成功', (tester) async {
    repository = _ScriptedRepository(_pendingState(), _committedState());
    await pumpCard(
      tester,
      resumeError: DioException(requestOptions: RequestOptions(path: '/x')),
    );

    await tester.tap(find.text('开始这一步'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(resumeApi.gets.length, 1, reason: 'bootstrap 诚实尝试一次');
    expect(find.text('已创建任务：写下 demo 的 30 秒演示脚本'), findsOneWidget,
        reason: '已确认事实照常呈现；网络失败只让接续读面诚实缺席，不渲染成功视觉之外的谎言',);
  });

  testWidgets('反 c：已建任务缺失（tasks 空）→ bootstrap 零请求（接续不冒充）',
      (tester) async {
    repository = _ScriptedRepository(
      _pendingState(),
      const FirstActionState(
        goal: FirstActionGoal(goalId: 'g1', title: '两周内做出可展示的比赛 demo'),
        proposal: <String, dynamic>{
          'proposal_id': 'p-receipt-1',
          'status': 'COMMITTED',
          'payload': <String, dynamic>{},
        },
      ),
    );
    await pumpCard(tester);

    await tester.tap(find.text('开始这一步'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(repository.approved, ['p-receipt-1']);
    expect(resumeApi.gets, isEmpty,
        reason: '无 taskId → 零 I01（无任务的确认不冒充首程接续）',);
  });
}

/// 只回 commit 态的仓库（面一的重开回放夹具）。
class _CommittedOnlyRepo extends FirstActionRepository {
  _CommittedOnlyRepo() : super(_FakeApi(), _FakeProposalRepo());

  @override
  Future<FirstActionState?> fetchState() async => _committedState();
}
