import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/services/agent_run_command_service.dart';
import 'package:sparkle/features/journey/data/models/hybrid_journey_models.dart';
import 'package:sparkle/features/journey/data/repositories/hybrid_journey_repository.dart';
import 'package:sparkle/features/journey/presentation/widgets/hybrid_journey_sheet.dart';
import 'package:sparkle/shared/widgets/action_proposal/awaiting_step_resume_card.dart';

import '../../shared/i18n_test_helper.dart';

/// J-06 · Hybrid 旗舰旅程移动端行为契约（统一 Runtime/UI，不另起交接面）：
/// ① 判断段显式说明「为什么需要你决定」，空选择时提交键结构性禁用（AI 不
///    代决的客户端呈现）；提交携带**真实选中的 source_ref**（非静态阅读）；
/// ② 交付确认 = X-07 统一 AwaitingStepResumeCard（同一 awaiting-step 面 +
///    同一幂等键推导），点确认走 /journey/hybrid/{run}/outcome/confirm；
/// ③ 完成面呈现来源引用计数（每段产物可溯源）。
class _FakeRepository implements HybridJourneyRepository {
  _FakeRepository(
    this.startPayload,
    this.judgedPayload,
    this.confirmedPayload, {
    Map<String, dynamic>? fetchStatePayload,
  }) : _fetchStatePayload = fetchStatePayload;

  final Map<String, dynamic> startPayload;
  final Map<String, dynamic> judgedPayload;
  final Map<String, dynamic> confirmedPayload;
  final Map<String, dynamic>? _fetchStatePayload;

  final List<Map<String, Object?>> judgmentCalls = <Map<String, Object?>>[];
  final List<Map<String, Object?>> confirmCalls = <Map<String, Object?>>[];
  int startCalls = 0;

  @override
  Future<HybridJourneyPayload> start({
    required String idempotencyKey,
    String? taskId,
  }) async {
    startCalls += 1;
    return HybridJourneyPayload.fromJson(startPayload);
  }

  @override
  Future<HybridJourneyPayload> submitJudgment({
    required String runId,
    required List<String> selectedRefs,
    required String idempotencyKey,
    String? focusNote,
  }) async {
    judgmentCalls.add(<String, Object?>{
      'run_id': runId,
      'selected_refs': List<String>.of(selectedRefs),
      'idempotency_key': idempotencyKey,
      'focus_note': focusNote,
    });
    return HybridJourneyPayload.fromJson(judgedPayload);
  }

  @override
  Future<HybridJourneyPayload> confirmOutcome({
    required String runId,
    required String idempotencyKey,
    String? note,
  }) async {
    confirmCalls.add(<String, Object?>{
      'run_id': runId,
      'idempotency_key': idempotencyKey,
    });
    return HybridJourneyPayload.fromJson(confirmedPayload);
  }

  @override
  Future<HybridJourneyPayload?> fetchState({required String runId}) async {
    final payload = _fetchStatePayload ?? startPayload;
    return HybridJourneyPayload.fromJson(payload);
  }
}

Map<String, dynamic> citation(String id, String ref, String file) =>
    <String, dynamic>{
      'citation_id': id,
      'scheme': 'document_chunk',
      'ref': ref,
      'source_ref': 'document_chunk://$ref',
      'file_id': 'file-1',
      'file_name': file,
      'page_numbers': <int>[2],
      'score': 0.87,
      'snippet': '联邦学习通过仅共享梯度更新来保护数据隐私。',
    };

Map<String, dynamic> awaitingJudgmentPayload() => <String, dynamic>{
      'version': 'hybrid_journey.v1',
      'run': <String, dynamic>{
        'run_id': 'run-1',
        'status': 'AWAITING_USER',
        'steps': <dynamic>[
          <String, dynamic>{
            'step_id': 'prep',
            'ordinal': 1,
            'owner': 'agent',
            'completed': true,
          },
          <String, dynamic>{
            'step_id': 'judgment',
            'ordinal': 2,
            'owner': 'human',
            'completed': false,
          },
          <String, dynamic>{
            'step_id': 'execute_check',
            'ordinal': 3,
            'owner': 'agent',
            'completed': false,
          },
          <String, dynamic>{
            'step_id': 'outcome',
            'ordinal': 4,
            'owner': 'hybrid',
            'completed': false,
          },
        ],
        'awaiting_step': <String, dynamic>{
          'step_id': 'judgment',
          'ordinal': 2,
          'owner': 'human',
          'state': 'awaiting',
          'label': '你来研判',
        },
      },
      'goal': <String, dynamic>{'goal_id': 'g1', 'title': '写一篇联邦学习综述'},
      'task': <String, dynamic>{'id': 't1', 'title': '完成综述大纲'},
      'citations': <dynamic>[
        citation('S1', 'chunk-a', '联邦学习笔记.pdf'),
        citation('S2', 'chunk-b', '差分隐私讲义.pdf'),
      ],
      'judgment_brief': <String, dynamic>{
        'why_human_key': 'hybridJourneyJudgmentWhyHuman',
        'why_human': '选哪些材料定义你自己的方向，必须由你决定。',
        'options': <dynamic>[
          citation('S1', 'chunk-a', '联邦学习笔记.pdf'),
          citation('S2', 'chunk-b', '差分隐私讲义.pdf'),
        ],
      },
      'artifacts': <dynamic>[],
    };

Map<String, dynamic> awaitingOutcomePayload() => <String, dynamic>{
      'version': 'hybrid_journey.v1',
      'run': <String, dynamic>{
        'run_id': 'run-1',
        'status': 'AWAITING_USER',
        'steps': <dynamic>[
          <String, dynamic>{
            'step_id': 'prep',
            'ordinal': 1,
            'owner': 'agent',
            'completed': true,
          },
          <String, dynamic>{
            'step_id': 'judgment',
            'ordinal': 2,
            'owner': 'human',
            'completed': true,
          },
          <String, dynamic>{
            'step_id': 'execute_check',
            'ordinal': 3,
            'owner': 'agent',
            'completed': true,
          },
          <String, dynamic>{
            'step_id': 'outcome',
            'ordinal': 4,
            'owner': 'hybrid',
            'completed': false,
          },
        ],
        'awaiting_step': <String, dynamic>{
          'step_id': 'outcome',
          'ordinal': 4,
          'owner': 'hybrid',
          'state': 'awaiting',
          'label': '确认交付',
          'artifacts': <dynamic>[
            <String, dynamic>{'scheme': 'journey_artifact', 'ref': 'a-9'},
          ],
        },
      },
      'goal': <String, dynamic>{'goal_id': 'g1', 'title': '写一篇联邦学习综述'},
      'task': <String, dynamic>{'id': 't1', 'title': '完成综述大纲'},
      'artifacts': <dynamic>[
        <String, dynamic>{
          'id': 'a-9',
          'stage': 'execute_check',
          'artifact_kind': 'checked_outline',
          'citations': <dynamic>[
            citation('S1', 'chunk-a', '联邦学习笔记.pdf'),
          ],
          'payload': <String, dynamic>{
            'outline_markdown': '## 大纲',
            'check': <String, dynamic>{
              'passed': true,
              'cited_ids': <dynamic>['S1'],
            },
          },
        },
      ],
    };

Map<String, dynamic> succeededPayload() => <String, dynamic>{
      'version': 'hybrid_journey.v1',
      'run': <String, dynamic>{
        'run_id': 'run-1',
        'status': 'SUCCEEDED',
        'steps': <dynamic>[],
      },
      'goal': <String, dynamic>{'goal_id': 'g1', 'title': '写一篇联邦学习综述'},
      'task': <String, dynamic>{'id': 't1', 'title': '完成综述大纲'},
      'artifacts': <dynamic>[
        <String, dynamic>{
          'id': 'a-9',
          'stage': 'execute_check',
          'artifact_kind': 'checked_outline',
          'citations': <dynamic>[
            citation('S1', 'chunk-a', '联邦学习笔记.pdf'),
            citation('S2', 'chunk-b', '差分隐私讲义.pdf'),
          ],
          'payload': <String, dynamic>{},
        },
      ],
    };

Widget host(Widget child) => testMaterialApp(
      theme: ThemeData.light().copyWith(
        extensions: [SparkleThemeExtension.light()],
      ),
      home: Scaffold(
        body: SingleChildScrollView(
          child: Padding(padding: const EdgeInsets.all(16), child: child),
        ),
      ),
    );

void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });
  tearDown(tearDownI18n);

  testWidgets('判断段：说明为什么需要你决定 + 空选择提交键禁用（AI 不代决）',
      (tester) async {
    final repo = _FakeRepository(
      awaitingJudgmentPayload(),
      awaitingOutcomePayload(),
      succeededPayload(),
    );
    await tester.pumpWidget(host(HybridJourneySheetBody(repository: repo)));
    await tester.pumpAndSettle();

    // 「为什么需要你决定」显式呈现（卡魂：判断归属说明）。
    expect(find.text('这一步需要你决定'), findsOneWidget);
    expect(find.text('就按这些来'), findsOneWidget);
    // 真实材料选项渲染（文件名 + 引用编号来自服务端真实 citation 结构）。
    expect(find.text('[S1] 联邦学习笔记.pdf · p.2'), findsOneWidget);
    expect(find.text('[S2] 差分隐私讲义.pdf · p.2'), findsOneWidget);

    // 空选择：提交键结构性禁用（onPressed == null），点了也不发请求。
    final submitFinder = find.byKey(const Key('hybrid-journey-submit-judgment'));
    final submitButtonBefore =
        tester.widget<SparkleButton>(submitFinder);
    expect(
      submitButtonBefore.disabled,
      isTrue,
      reason: '空选择时提交键必须禁用——AI 不代决的客户端呈现',
    );
    await tester.tap(submitFinder, warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(repo.judgmentCalls, isEmpty, reason: '空选择绝不产生判断提交');
  });

  testWidgets('判断段：选择真实材料 → 提交携带选中 source_ref（真实请求参数）',
      (tester) async {
    final repo = _FakeRepository(
      awaitingJudgmentPayload(),
      awaitingOutcomePayload(),
      succeededPayload(),
    );
    await tester.pumpWidget(host(HybridJourneySheetBody(repository: repo)));
    await tester.pumpAndSettle();

    await tester.tap(find.text('[S1] 联邦学习笔记.pdf · p.2'));
    await tester.pump();
    await tester.tap(find.byKey(const Key('hybrid-journey-submit-judgment')));
    await tester.pumpAndSettle();

    expect(repo.judgmentCalls, hasLength(1));
    final call = repo.judgmentCalls.single;
    expect(call['run_id'], 'run-1');
    expect(
      call['selected_refs'],
      <String>['document_chunk://chunk-a'],
      reason: '提交的是真实选中的 chunk 引用，不是静态阅读',
    );
    // 判断完成后进入交付确认：统一 X-07 awaiting-step 卡渲染（轮到你了）。
    expect(find.byType(AwaitingStepResumeCard), findsOneWidget);
  });

  testWidgets('交付确认：统一 X-07 卡 → 确认走旅程 confirm（幂等键确定性推导）',
      (tester) async {
    final repo = _FakeRepository(
      awaitingOutcomePayload(),
      awaitingOutcomePayload(),
      succeededPayload(),
      fetchStatePayload: awaitingOutcomePayload(),
    );
    await tester.pumpWidget(
      host(
        HybridJourneySheetBody(
          repository: repo,
          runId: 'run-1',
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(AwaitingStepResumeCard), findsOneWidget);
    expect(find.text('已核对：1 条引用全部来自你选的材料'), findsOneWidget);

    await tester.tap(find.text('确认，继续'));
    await tester.pumpAndSettle();

    expect(repo.confirmCalls, hasLength(1));
    expect(
      repo.confirmCalls.single['idempotency_key'],
      runStepActionIdempotencyKey('run-1', 'outcome', 'confirm'),
      reason: '与统一 awaiting-step 面同一幂等键推导（x07:run:step:action）',
    );
    // 完成面：来源引用计数可见（每段产物可溯源）。
    expect(find.text('已完成：交付记入你的成长图谱（2 条来源引用）'), findsOneWidget);
  });
}
