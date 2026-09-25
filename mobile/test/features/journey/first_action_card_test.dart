import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/journey/data/repositories/first_action_repository.dart';
import 'package:sparkle/features/journey/presentation/widgets/first_action_card.dart';
import 'package:sparkle/features/task/data/repositories/action_proposal_repository.dart';

import '../../shared/i18n_test_helper.dart';

/// J-04 · First Meaningful Action 卡验收（headless 面三端一致断言）.
///
/// 覆盖（卡面 acceptance 一一对应）：
/// 1. **Action 三字段**：产出/完成证据/轮到谁（mode）逐项可见；
/// 2. **5 Persona 不模板化**：persona 专属内容（非通用文案）上卡可见，两个
///    persona 的同一张卡渲染不同 step/outcome/mode；
/// 3. **feedback 不静默**：拒绝带理由、编辑带 delta，都经 repository 下发；
/// 4. **失败诚实**：生成失败 → 错误可见 + 可重试 + 可跳过，永不渲染成功态；
/// 5. **重开回放**：卡片状态唯一来自服务端状态投影（firstActionStateProvider
///    的 GET /journey/first-action），已 commit 的链路重开原样可见，零本地
///    重生成。
void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });
  tearDown(tearDownI18n);

  /// 记录型假仓库（测试夹具，非生产行为）：可脚本化状态/失败/调用记录.
  late _RecordingRepository repository;

  Widget host({List<Override> overrides = const []}) => ProviderScope(
        overrides: overrides,
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
      );

  Future<List<Override>> overridesWith(FirstActionState state) async {
    final repoOverrides = await repository.overrides(state);
    return repoOverrides;
  }

  Map<String, dynamic> pendingProposal({
    required String proposalId,
    required String title,
    required String step,
    required String outcome,
    required String evidenceKind,
    required String mode,
    int? minutes,
  }) =>
      <String, dynamic>{
        'proposal_id': proposalId,
        'status': 'PENDING',
        'payload': <String, dynamic>{
          'tasks': <Map<String, dynamic>>[
            <String, dynamic>{
              'title': title,
              'estimated_minutes': minutes,
              'action_plan': <String, dynamic>{
                'desired_outcome': outcome,
                'smallest_useful_step': <String, dynamic>{
                  'description': step,
                  'useful_because': <String>['produces_artifact'],
                },
                'completion_evidence': <Map<String, dynamic>>[
                  <String, dynamic>{'evidence_kind': evidenceKind},
                ],
                'execution_mode': mode,
                'cognitive_ownership': 'user_core',
              },
            },
          ],
        },
      };

  testWidgets('PENDING 提案：三字段（产出/完成证据/轮到谁）逐项可见，persona 内容上卡',
      (tester) async {
    repository = _RecordingRepository();
    final state = FirstActionState(
      goal: const FirstActionGoal(
          goalId: 'g1', title: '两周内做出可展示的比赛 demo', goalType: 'project',),
      proposal: pendingProposal(
        proposalId: 'p-1',
        title: '写下 demo 的 30 秒演示脚本',
        step: '用一页纸写清评委将看到的三个画面',
        outcome: '30 秒演示脚本草稿',
        evidenceKind: 'artifact',
        mode: 'hybrid',
        minutes: 30,
      ),
    );
    await tester.pumpWidget(host(overrides: await overridesWith(state)));
    await tester.pump();

    // 三字段标签逐项可见（outcome / evidence / mode）
    expect(find.text('产出'), findsOneWidget);
    expect(find.text('完成证据'), findsOneWidget);
    expect(find.text('轮到谁'), findsOneWidget);
    // 三字段值 = 真实 persona 差异化内容（非模板通用文案）
    expect(find.text('写下 demo 的 30 秒演示脚本'), findsOneWidget);
    expect(find.text('30 秒演示脚本草稿'), findsOneWidget);
    expect(find.text('产出一件可见的东西'), findsOneWidget);
    expect(find.text('一起做 · 约 30 分钟'), findsOneWidget);
  });

  testWidgets('不同 persona 的同构 proposal 渲染不同内容：mode human → 你做',
      (tester) async {
    repository = _RecordingRepository();
    final state = FirstActionState(
      goal: const FirstActionGoal(
          goalId: 'g2', title: '三周后期末考，高数还没系统复习', goalType: 'exam',),
      proposal: pendingProposal(
        proposalId: 'p-2',
        title: '把考纲章节按会/不会分成两栏',
        step: '逐条过考纲并自评',
        outcome: '一张个人薄弱章节分布表',
        evidenceKind: 'self_report',
        mode: 'human',
        minutes: 15,
      ),
    );
    await tester.pumpWidget(host(overrides: await overridesWith(state)));
    await tester.pump();

    expect(find.text('把考纲章节按会/不会分成两栏'), findsOneWidget);
    expect(find.text('一张个人薄弱章节分布表'), findsOneWidget);
    expect(find.text('你的真实自评'), findsOneWidget);
    expect(find.text('你做 · 约 15 分钟'), findsOneWidget);
    // 上一 persona 的内容不得出现（模板撞车即红）
    expect(find.text('写下 demo 的 30 秒演示脚本'), findsNothing);
  });

  testWidgets('开始：经 repository 透传稳定幂等键 approve', (tester) async {
    repository = _RecordingRepository();
    final state = FirstActionState(
      goal: const FirstActionGoal(
          goalId: 'g1', title: '目标', goalType: 'skill',),
      proposal: pendingProposal(
        proposalId: 'p-approve',
        title: '列出 3 个项目素材',
        step: '为每个候选项目写一行说明',
        outcome: '项目素材清单',
        evidenceKind: 'artifact',
        mode: 'human',
      ),
    );
    await tester.pumpWidget(host(overrides: await overridesWith(state)));
    await tester.pump();

    await tester.tap(find.text('开始这一步'));
    await tester.pump();

    expect(repository.approvedProposalIds, ['p-approve']);
    expect(repository.approveKeys, ['u04:p-approve:approve']);
  });

  testWidgets('拒绝：理由随 reject 下发（feedback 不静默丢弃）', (tester) async {
    repository = _RecordingRepository();
    final state = FirstActionState(
      goal: const FirstActionGoal(
          goalId: 'g1', title: '目标', goalType: 'skill',),
      proposal: pendingProposal(
        proposalId: 'p-reject',
        title: '列出 3 个项目素材',
        step: '为每个候选项目写一行说明',
        outcome: '项目素材清单',
        evidenceKind: 'artifact',
        mode: 'human',
      ),
    );
    await tester.pumpWidget(host(overrides: await overridesWith(state)));
    await tester.pump();

    await tester.tap(find.text('这个不合适'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byType(TextField).first,
      '这个不合适，我还没有测验卷',
    );
    await tester.tap(find.text('拒绝并记录原因'));
    await tester.pumpAndSettle();

    expect(repository.rejectedProposalIds, ['p-reject']);
    expect(repository.rejectReasons, ['这个不合适，我还没有测验卷'],
        reason: '拒绝理由必须下发到服务端 feedback 审计面，不静默丢弃',);
  });

  testWidgets('编辑：编辑 delta（新标题）随 edit 下发，重新提案', (tester) async {
    repository = _RecordingRepository();
    final state = FirstActionState(
      goal: const FirstActionGoal(
          goalId: 'g1', title: '目标', goalType: 'creator',),
      proposal: pendingProposal(
        proposalId: 'p-edit',
        title: '写下第一期选题',
        step: '用三句话写出第一期要讲什么',
        outcome: '第一期选题草稿',
        evidenceKind: 'artifact',
        mode: 'human',
        minutes: 20,
      ),
    );
    await tester.pumpWidget(host(overrides: await overridesWith(state)));
    await tester.pump();

    await tester.tap(find.text('编辑'));
    await tester.pumpAndSettle();

    final titleField = find.byType(TextField).first;
    await tester.enterText(titleField, '列出 5 个身边可聊的人选');
    await tester.enterText(find.byType(TextField).at(2), '第一步还是太大，改小');
    await tester.tap(find.text('保存并重新提案'));
    await tester.pumpAndSettle();

    expect(repository.editedProposalIds, ['p-edit']);
    expect(repository.editedFields.single['title'], '列出 5 个身边可聊的人选');
    expect(repository.editReasons.single, '第一步还是太大，改小');
  });

  testWidgets('生成失败诚实：错误可见 + 重试成功；永不把失败渲染成成功', (tester) async {
    repository = _RecordingRepository()
      ..generateException = FirstActionGenerationException(
        error: 'first_action_generation_failed',
        retryable: true,
        statusCode: 503,
      );
    const state = FirstActionState(
      goal: FirstActionGoal(
          goalId: 'g1', title: '持续产出播客', goalType: 'creator',),
    );
    await tester.pumpWidget(host(overrides: await overridesWith(state)));
    await tester.pump();

    await tester.tap(find.text('生成我的第一步'));
    await tester.pump();

    // 失败可见（不静默），且没有任何成功态渲染
    expect(find.text('第一步生成失败'), findsOneWidget);
    expect(find.byIcon(Icons.check_circle_outline), findsNothing);
    expect(repository.generatedKeys, hasLength(1));

    // 可重试：恢复后重试即走生成并刷新状态
    repository.generateException = null;
    await tester.tap(find.text('重试'));
    await tester.pump();
    expect(repository.generatedKeys, hasLength(2));
  });

  testWidgets('重开回放：已 commit 链路从服务端状态原样可见（零重生成）', (tester) async {
    repository = _RecordingRepository();
    const state = FirstActionState(
      goal: FirstActionGoal(
          goalId: 'g1', title: '持续产出播客', goalType: 'creator',),
      proposal: <String, dynamic>{
        'proposal_id': 'p-committed',
        'status': 'COMMITTED',
      },
      tasks: [
        FirstActionTaskRef(
            id: 't-1', title: '写下第一期选题', status: 'TODO',),
      ],
    );
    await tester.pumpWidget(host(overrides: await overridesWith(state)));
    await tester.pump();

    expect(find.text('第一步已在任务账本里'), findsOneWidget);
    expect(find.text('已创建任务：写下第一期选题'), findsOneWidget);
    // 重开面只读服务端状态：无生成、无重提案
    expect(repository.generatedKeys, isEmpty);
    expect(find.text('生成我的第一步'), findsNothing);
  });

  testWidgets('FirstActionStep.fromProposal：解析层同样保真（无 action_plan → null）',
      (tester) async {
    expect(FirstActionStep.fromProposal(<String, dynamic>{}), isNull);
    expect(
      FirstActionStep.fromProposal(<String, dynamic>{
        'payload': <String, dynamic>{
          'tasks': <Map<String, dynamic>>[
            <String, dynamic>{'title': 'legacy 无契约块'},
          ],
        },
      }),
      isNull,
      reason: 'legacy 行（无 action_plan）不渲染三字段卡——诚实降级',
    );
  });
}

class _RecordingRepository extends FirstActionRepository {
  _RecordingRepository() : super(_FakeApiClient(), _FakeProposalRepository());

  /// 生成侧脚本化失败（null = 成功；记录幂等键供断言）
  FirstActionGenerationException? generateException;

  final generatedKeys = <String>[];

  final approvedProposalIds = <String>[];
  final approveKeys = <String>[];
  final rejectedProposalIds = <String>[];
  final rejectReasons = <String?>[];
  final editedProposalIds = <String>[];
  final editedFields = <Map<String, dynamic>>[];
  final editReasons = <String?>[];

  @override
  Future<FirstActionState> generate({required String idempotencyKey}) async {
    generatedKeys.add(idempotencyKey);
    final exception = generateException;
    if (exception != null) {
      throw exception;
    }
    return const FirstActionState();
  }

  @override
  Future<Map<String, dynamic>?> approve(
    String proposalId,
    String idempotencyKey,
  ) async {
    approvedProposalIds.add(proposalId);
    approveKeys.add(idempotencyKey);
    return null;
  }

  @override
  Future<Map<String, dynamic>?> reject(
    String proposalId,
    String idempotencyKey, {
    String? reason,
  }) async {
    rejectedProposalIds.add(proposalId);
    rejectReasons.add(reason);
    return null;
  }

  @override
  Future<Map<String, dynamic>?> edit(
    String proposalId, {
    required Map<String, dynamic> editedFields,
    required String idempotencyKey, String? reason,
  }) async {
    editedProposalIds.add(proposalId);
    this.editedFields.add(editedFields);
    editReasons.add(reason);
    return null;
  }

  Future<List<Override>> overrides(FirstActionState state) async => [
        firstActionRepositoryProvider.overrideWithValue(this),
        firstActionStateProvider.overrideWith((ref) async => state),
      ];
}

class _FakeApiClient extends Fake implements ApiClient {}

class _FakeProposalRepository extends Fake implements ActionProposalRepository {}
