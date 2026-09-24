import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/services/agent_run_read_service.dart';
import 'package:sparkle/shared/widgets/action_proposal/awaiting_step_resume_card.dart';

import '../../../shared/i18n_test_helper.dart';

/// X-07 · AwaitingStepResumeCard：恢复到 awaiting step / ownership 可视化 /
/// 幂等防抖 / 取消-过期明确呈现（GJ07 移动端面）.
void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });
  tearDown(tearDownI18n);

  Widget host(Widget child) => testMaterialApp(
        theme: ThemeData.light()
            .copyWith(extensions: [SparkleThemeExtension.light()]),
        home: Scaffold(
          body: SingleChildScrollView(
            child: Padding(padding: const EdgeInsets.all(16), child: child),
          ),
        ),
      );

  AgentRunAwaitingStep step({
    String stepId = 's2-decide',
    String owner = 'human',
    String state = 'awaiting',
    String? prompt = 'Agent 已备好 5 张复习卡，请挑选',
    List<AgentRunArtifactRef> artifacts = const <AgentRunArtifactRef>[
      AgentRunArtifactRef(scheme: 'action_proposal', ref: 'p-1'),
    ],
  }) =>
      AgentRunAwaitingStep(
        stepId: stepId,
        ordinal: 2,
        owner: owner,
        state: state,
        label: '挑出今日复习卡',
        prompt: prompt,
        artifactRefs: artifacts,
      );

  testWidgets('awaiting + human owner：轮到你了 / 你做 / 确认，继续（GJ07）',
      (tester) async {
    final confirmKeys = <String>[];
    await tester.pumpWidget(host(AwaitingStepResumeCard(
      runId: 'run-1',
      step: step(),
      onConfirm: (key) async => confirmKeys.add(key),
      onCancel: (_) async {},
    ),),);
    await tester.pump();

    // 「轮到谁」非技术化呈现；HUMAN 态可达（U-04 P2 解锁）。
    expect(find.text('你做'), findsOneWidget);
    expect(find.text('轮到你了'), findsOneWidget);
    expect(find.text('挑出今日复习卡\nAgent 已备好 5 张复习卡，请挑选'),
        findsOneWidget,);
    // Agent 产物引用可见（本体在既有机制，卡片只展示引用）。
    expect(find.text('Sparkle 准备好了这些'), findsOneWidget);
    expect(find.text('action_proposal://p-1'), findsOneWidget);
    expect(find.text('这一步轮到你，完成后 Sparkle 接着做'), findsOneWidget);
    expect(find.text('确认，继续'), findsOneWidget);
    expect(find.text('取消'), findsOneWidget);

    // 确认 → 稳定幂等键透传（确定性推导：重建/重进后同键）。
    await tester.tap(find.text('确认，继续'));
    await tester.pumpAndSettle();
    expect(confirmKeys, <String>['x07:run-1:s2-decide:confirm']);
  });

  testWidgets('在途防抖：双击只发一次命令（服务端幂等之外的第二道防线）',
      (tester) async {
    var calls = 0;
    await tester.pumpWidget(host(AwaitingStepResumeCard(
      runId: 'run-1',
      step: step(),
      onConfirm: (key) async {
        calls += 1;
        await Future<void>.delayed(const Duration(milliseconds: 200));
      },
    ),),);
    await tester.pump();

    await tester.tap(find.text('确认，继续'), warnIfMissed: false);
    await tester.pump(const Duration(milliseconds: 50));
    await tester.tap(find.text('确认，继续'), warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(calls, 1);
  });

  testWidgets('hybrid owner：一起做', (tester) async {
    await tester.pumpWidget(host(AwaitingStepResumeCard(
      runId: 'run-1',
      step: step(owner: 'hybrid'),
      onConfirm: (_) async {},
    ),),);
    await tester.pump();
    expect(find.text('一起做'), findsOneWidget);
  });

  testWidgets('expired：已过期明确呈现，不给确认入口（acceptance ②）',
      (tester) async {
    await tester.pumpWidget(host(AwaitingStepResumeCard(
      runId: 'run-1',
      step: step(state: 'expired'),
      onConfirm: (_) async {},
    ),),);
    await tester.pump();
    expect(find.text('已过期'), findsOneWidget);
    expect(find.text('这次确认已经过期，需要的话可以重新发起'), findsOneWidget);
    expect(find.text('确认，继续'), findsNothing);
    expect(find.text('取消'), findsNothing);
  });

  testWidgets('cancelled：已取消明确呈现，不给确认入口', (tester) async {
    await tester.pumpWidget(host(AwaitingStepResumeCard(
      runId: 'run-1',
      step: step(state: 'cancelled'),
      onConfirm: (_) async {},
    ),),);
    await tester.pump();
    expect(find.text('已取消'), findsOneWidget);
    expect(find.text('这一步已取消，没有执行'), findsOneWidget);
    expect(find.text('确认，继续'), findsNothing);
  });

  testWidgets('取消回调收到稳定幂等键', (tester) async {
    String? cancelKey;
    await tester.pumpWidget(host(AwaitingStepResumeCard(
      runId: 'run-1',
      step: step(),
      onConfirm: (_) async {},
      onCancel: (key) async => cancelKey = key,
    ),),);
    await tester.pump();
    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(cancelKey, 'x07:run-1:s2-decide:cancel');
  });

  testWidgets('AgentRunView wire 投影：awaiting_step / steps 解析（冷启动恢复面）',
      (tester) async {
    final view = AgentRunView.fromJson(<String, dynamic>{
      'run_id': 'run-9',
      'status': 'AWAITING_USER',
      'is_terminal': false,
      'objective': '错题变复习卡',
      'wait_kind': 'user_step',
      'steps': [
        {
          'step_id': 's1',
          'ordinal': 1,
          'owner': 'agent',
          'completed': true,
          'completion_condition': {'kind': 'agent_output'},
          'completion': {'by': 'agent'},
        },
        {
          'step_id': 's2',
          'ordinal': 2,
          'owner': 'human',
          'completed': false,
          'ownership': 'human',
          'completion_condition': {'kind': 'user_confirmation'},
        },
      ],
      'awaiting_step': {
        'step_id': 's2',
        'ordinal': 2,
        'owner': 'human',
        'ownership': 'human',
        'state': 'awaiting',
        'label': '挑出今日复习卡',
        'prompt': '请挑选',
        'expires_at': '2026-09-21T20:00:00',
        'artifacts': [
          {'scheme': 'action_proposal', 'ref': 'p-9'},
        ],
      },
    });

    expect(view.isAwaitingUser, isTrue);
    expect(view.steps.length, 2);
    expect(view.steps[0].completed, isTrue);
    expect(view.steps[1].owner, 'human');
    expect(view.awaitingStep, isNotNull);
    expect(view.awaitingStep!.isAwaiting, isTrue);
    expect(view.awaitingStep!.owner, 'human');
    expect(view.awaitingStep!.artifactRefs.first.label, 'action_proposal://p-9');
    expect(
      runStepIdempotencyKey('run-9', 's2', 'confirm'),
      'x07:run-9:s2:confirm',
    );
  });

  testWidgets('无障碍：ownership pill 有语义标签', (tester) async {
    await tester.pumpWidget(host(AwaitingStepResumeCard(
      runId: 'run-1',
      step: step(),
      onConfirm: (_) async {},
    ),),);
    await tester.pump();
    // SemanticPill 渲染 ownership 文案；按钮带确认 CTA——GJ07「无需读日志知道轮到谁」。
    expect(find.byType(SemanticPill), findsAtLeastNWidgets(2));
    expect(find.byIcon(Icons.person_outline), findsOneWidget);
  });
}
