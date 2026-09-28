import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/home/data/episode_resume_models.dart';
import 'package:sparkle/features/home/presentation/providers/episode_resume_provider.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';

/// V4-U01 · episodeResumeProvider 测试——I01 读模型 + I06 回执读面的
/// 组合门（角色门/任务门/降级门；每面一正一反，全部可失败）。
class _StubApiClient implements ApiClient {
  _StubApiClient(this.response, {this.getError});

  Object? response;
  DioException? getError;
  final List<({String path, Map<String, dynamic>? query})> gets = [];

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    gets.add((path: path, query: queryParameters));
    final error = getError;
    if (error != null) {
      throw error;
    }
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: response as T,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('stub only implements get');
}

Map<String, dynamic> _receiptPayload({String role = 'resume_view'}) => {
      'mode': 'live',
      'schema_version': 'context_selection_receipt.v1',
      'receipt': {
        'schema_version': 'context_selection_receipt.v1',
        'receipt_id': 'csr_U01TEST',
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

Map<String, dynamic> _resumeViewPayload({
  String schemaVersion = kEpisodeResumeViewSchemaVersion,
  String taskRef = 'task://t1',
  String expiresAt = '2099-01-01T00:00:00',
}) =>
    {
      'view': {
        'schema_version': schemaVersion,
        'goal_ref': 'goal://g1',
        'task_ref': taskRef,
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
        'expires_at': expiresAt,
        'freshness': {
          'context_receipt_ref': 'context_selection://csr_U01TEST',
          'computed_at': '2026-09-28T12:00:00',
          'memory_epoch_at_compute': 3,
        },
      },
      'reason_code': null,
      'warnings': <String>[],
    };

/// 组装容器并等待接续状态落定；返回（状态, 接续端点桩）。
Future<({EpisodeResumeState state, _StubApiClient api})> _pumpResume({
  Object? receiptPayload,
  Object? resumePayload,
  DioException? resumeError,
  bool withTask = true,
}) async {
  final resumeApi = _StubApiClient(
    resumePayload ?? _resumeViewPayload(),
    getError: resumeError,
  );
  final container = ProviderContainer(
    overrides: [
      contextReceiptProvider.overrideWith(
        (ref) => ContextReceiptNotifier(
          _StubApiClient(
            receiptPayload ?? _receiptPayload(),
          ),
        ),
      ),
      apiClientProvider.overrideWithValue(resumeApi),
      homeGrowthStateProvider.overrideWith(
        (ref) => withTask
            ? const HomeGrowthState(
                planHealth: 0.8,
                tasksTotal: 3,
                tasksCompleted: 0,
                streak: 0,
                nextAction: HomeGrowthTask(
                  id: 't1',
                  title: 'Read chapter 3',
                  priority: 4,
                  isCompleted: false,
                ),
              )
            : const HomeGrowthState.empty(),
      ),
    ],
  );
  addTearDown(container.dispose);
  // 回执读面 load 完成后再读接续 provider：消除「首帧 receipt=loading →
  // hidden 快照」的竞态（真实 app 中 Riverpod 会在 receipt 落定后重算）。
  await container.read(contextReceiptProvider.notifier).load();
  final state = await container.read(episodeResumeProvider.future);
  return (state: state, api: resumeApi);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('正：ready 回执（role=resume_view）+ 任务 → ready，且请求 I01 端点携带 receipt ref', () async {
    final (:state, :api) = await _pumpResume();

    expect(state.phase, EpisodeResumePhase.ready);
    expect(state.taskId, 't1');
    expect(state.view?.lastConfirmedStep?.description, '读完第三章前两节');
    expect(api.gets, hasLength(1));
    expect(api.gets.single.path, ApiEndpoints.episodeResumeTask('t1'));
    expect(
      api.gets.single.query?['context_receipt_ref'],
      'context_selection://csr_U01TEST',
    );
  });

  test('反：回执角色非 resume_view（chat_context）→ hidden 且零请求（归因错置不做）', () async {
    final (:state, :api) = await _pumpResume(
      receiptPayload: _receiptPayload(role: 'chat_context'),
      resumePayload: const <String, dynamic>{},
    );

    expect(state.phase, EpisodeResumePhase.hidden);
    expect(api.gets, isEmpty);
  });

  test('反：回执读面 off（modeGated）→ hidden 且零请求（读未开不造接续）', () async {
    final (:state, :api) = await _pumpResume(
      receiptPayload: {
        'mode': 'off',
        'schema_version': 'context_selection_receipt.v1',
        'receipt': null,
      },
      resumePayload: const <String, dynamic>{},
    );

    expect(state.phase, EpisodeResumePhase.hidden);
    expect(api.gets, isEmpty);
  });

  test('反：无 nextAction 任务（新用户/空态）→ hidden 且零请求（零假历史）', () async {
    final (:state, :api) = await _pumpResume(
      withTask: false,
      resumePayload: const <String, dynamic>{},
    );

    expect(state.phase, EpisodeResumePhase.hidden);
    expect(api.gets, isEmpty);
  });

  test('反：端点降级（view=null + reason_code）→ hidden（类型化原因不渲染半真视图）', () async {
    final result = await _pumpResume(
      resumePayload: {
        'view': null,
        'reason_code': 'goal_changed_requires_calibration',
        'warnings': <String>[],
      },
    );

    expect(result.state.phase, EpisodeResumePhase.hidden);
  });

  test('反：视图 schema 损坏（版本不符）→ hidden（解析 fail-closed）', () async {
    final result = await _pumpResume(
      resumePayload: _resumeViewPayload(schemaVersion: 'episode_resume_view.v2'),
    );

    expect(result.state.phase, EpisodeResumePhase.hidden);
  });

  test('反：端点网络失败（DioException）→ hidden（读面降级是缺席不是错误）', () async {
    final result = await _pumpResume(
      resumeError: DioException(requestOptions: RequestOptions(path: '/x')),
    );

    expect(result.state.phase, EpisodeResumePhase.hidden);
  });

  group('EpisodeResumeState.continueStepFor 主行动收敛门', () {
    final view = EpisodeResumeViewData.tryParse(
      _resumeViewPayload()['view'] as Map<String, dynamic>,
    )!;

    test('正：同任务 + 新鲜 + pending step → 返回下一步文案', () {
      final state = EpisodeResumeState.ready(view: view, taskId: 't1');

      expect(
        state.continueStepFor('t1', now: DateTime.parse('2026-09-28T12:01:00')),
        '做第三章末尾的三道练习题',
      );
    });

    test('反：任务不绑定 / 过期 → null（主行动不得被改写）', () {
      final state = EpisodeResumeState.ready(view: view, taskId: 't1');

      // 错绑任务：不收敛。
      expect(
        state.continueStepFor('t2', now: DateTime.parse('2026-09-28T12:01:00')),
        isNull,
      );
      // 过期视图：stale 不接续。
      expect(
        state.continueStepFor('t1', now: DateTime.parse('2099-01-02T00:00:00')),
        isNull,
      );
    });
  });
}
