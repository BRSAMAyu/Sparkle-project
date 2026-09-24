import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/shared/widgets/action_proposal/action_proposal_card.dart';

import '../../../shared/i18n_test_helper.dart';

/// U-04 · ActionProposalCard 状态矩阵 / ownership / 幂等防抖 / GJ06·GJ07 断言.
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

  ActionProposalCardData data({
    String proposalId = 'p-1',
    ProposalCardStatus status = ProposalCardStatus.awaitingUser,
    ProposalTurnOwnership ownership = ProposalTurnOwnership.hybrid,
    List<ProposalDiffEntry> diff = const <ProposalDiffEntry>[],
  }) =>
      ActionProposalCardData(
        proposalId: proposalId,
        status: status,
        ownership: ownership,
        title: '把错题整理成复习卡',
        diff: diff,
      );

  // ── 状态矩阵 ─────────────────────────────────────────────────────────────

  testWidgets('awaiting user: 等你确认 + 确认/拒绝按钮', (tester) async {
    await tester.pumpWidget(host(ActionProposalCard(
      data: data(),
      onApprove: (_) async {},
      onReject: (_) async {},
    ),),);
    await tester.pump();

    expect(find.text('等你确认'), findsOneWidget);
    expect(find.text('确认，就这样做'), findsOneWidget);
    expect(find.text('先不用'), findsOneWidget);
    // GJ07: hybrid handoff 文案——非技术化说明现在轮到谁。
    expect(find.text('一起做'), findsOneWidget);
    expect(find.text('你确认后，Sparkle 来执行'), findsOneWidget);
  });

  testWidgets('running: Sparkle 正在做，不出现确认按钮', (tester) async {
    await tester.pumpWidget(host(ActionProposalCard(
      data: data(status: ProposalCardStatus.running),
      onApprove: (_) async {},
      onReject: (_) async {},
    ),),);
    await tester.pump();

    expect(find.text('正在执行'), findsOneWidget);
    expect(find.text('Sparkle 正在做'), findsOneWidget);
    expect(find.text('确认，就这样做'), findsNothing);
  });

  testWidgets('partial: 部分完成，诚实说明剩余部分', (tester) async {
    await tester.pumpWidget(host(ActionProposalCard(
      data: data(status: ProposalCardStatus.partial),
      onApprove: (_) async {},
      onReject: (_) async {},
    ),),);
    await tester.pump();

    expect(find.text('部分完成'), findsOneWidget);
    expect(find.textContaining('只完成了一部分'), findsOneWidget);
    expect(find.text('已完成'), findsNothing);
  });

  testWidgets('unknown: 结果待确认——不显示成功（GJ06/GJ07 诚实性）', (tester) async {
    var refreshed = 0;
    await tester.pumpWidget(host(ActionProposalCard(
      data: data(status: ProposalCardStatus.unknown),
      onApprove: (_) async {},
      onReject: (_) async {},
      onRefresh: () => refreshed++,
    ),),);
    await tester.pump();

    expect(find.text('结果待确认'), findsOneWidget);
    expect(find.textContaining('先别当成已完成'), findsOneWidget);
    // 未知结果 ≠ 成功：不出现「已完成」文案，也不出现成功图标。
    expect(find.text('已完成'), findsNothing);
    expect(find.byIcon(Icons.check_circle_outline_rounded), findsNothing);

    await tester.tap(find.text('刷新结果'));
    await tester.pump();
    expect(refreshed, 1);
  });

  testWidgets('committed: 已完成 + 回执摘要', (tester) async {
    await tester.pumpWidget(host(ActionProposalCard(
      data: const ActionProposalCardData(
        proposalId: 'p-1',
        status: ProposalCardStatus.committed,
        title: '把错题整理成复习卡',
        receiptSummary: '已生成 12 张复习卡',
      ),
      onApprove: (_) async {},
      onReject: (_) async {},
    ),),);
    await tester.pump();

    expect(find.text('已完成'), findsOneWidget);
    expect(find.text('已完成并记录'), findsOneWidget);
    expect(find.text('已生成 12 张复习卡'), findsOneWidget);
  });

  testWidgets('cancelled / expired / rejected: 终态无确认入口', (tester) async {
    const terminal = <ProposalCardStatus, String>{
      ProposalCardStatus.cancelled: '已取消',
      ProposalCardStatus.expired: '已过期',
      ProposalCardStatus.rejected: '已拒绝',
    };
    for (final entry in terminal.entries) {
      await tester.pumpWidget(host(ActionProposalCard(
        data: data(status: entry.key),
        onApprove: (_) async {},
        onReject: (_) async {},
        onCancel: (_) async {},
      ),),);
      await tester.pump();
      expect(find.text(entry.value), findsOneWidget, reason: entry.key.name);
      expect(find.text('确认，就这样做'), findsNothing,
          reason: '${entry.key.name} 不应再提供确认入口',);
    }
  });

  testWidgets('conflict: 内容有更新 + 再看一遍 + diff 前后对照', (tester) async {
    var reviewed = 0;
    await tester.pumpWidget(host(ActionProposalCard(
      data: data(
        status: ProposalCardStatus.conflict,
        diff: const [
          ProposalDiffEntry(field: '截止时间', before: '周五', after: '周六'),
        ],
      ),
      onApprove: (_) async {},
      onReject: (_) async {},
      onReview: () => reviewed++,
    ),),);
    await tester.pump();

    expect(find.text('内容有更新'), findsOneWidget);
    expect(find.text('会改动什么'), findsOneWidget);
    expect(find.text('截止时间'), findsOneWidget);
    expect(find.textContaining('周五'), findsOneWidget);
    expect(find.textContaining('周六'), findsOneWidget);

    await tester.tap(find.text('再看一遍'));
    await tester.pump();
    expect(reviewed, 1);
  });

  // ── ownership 三态（GJ06/GJ07：无需读日志即知轮到谁） ────────────────────

  testWidgets('ownership 文案：你做 / Sparkle做 / 一起做 + a11y 轮次语义', (tester) async {
    final semantics = tester.ensureSemantics();
    final expected = <ProposalTurnOwnership, (String, String)>{
      // ownership → (ownership 文案, 当前轮次文案)
      ProposalTurnOwnership.human: ('你做', '轮到你了'),
      ProposalTurnOwnership.agent: ('Sparkle做', '你确认后，Sparkle 来执行'),
      ProposalTurnOwnership.hybrid: ('一起做', '你确认后，Sparkle 来执行'),
    };
    for (final entry in expected.entries) {
      await tester.pumpWidget(host(ActionProposalCard(
        data: data(ownership: entry.key),
        onApprove: (_) async {},
        onReject: (_) async {},
      ),),);
      await tester.pump();
      expect(find.text(entry.value.$1), findsOneWidget,
          reason: '${entry.key.name} 应显示「${entry.value.$1}」',);
      // 卡片容器节点会把子节点 label 合并（含换行），故用子串匹配。
      expect(
        find.bySemanticsLabel(RegExp('当前轮到：${entry.value.$1}')),
        findsOneWidget,
        reason: 'a11y 语义必须暴露当前 ownership（GJ06/GJ07）',
      );
      expect(
        find.bySemanticsLabel(RegExp('当前轮到：${entry.value.$2}')),
        findsOneWidget,
        reason: 'a11y 语义必须暴露当前轮次（GJ06/GJ07）',
      );
    }
    semantics.dispose();
  });

  // ── 幂等防抖：重复点击不产生重复 command ────────────────────────────────

  testWidgets('防抖：在途期间重复点击合并为一次 command；完成后进入待确认而非成功',
      (tester) async {
    var approveCalls = 0;
    final completer = Completer<void>();
    await tester.pumpWidget(host(ActionProposalCard(
      data: data(),
      onApprove: (_) async {
        approveCalls += 1;
        await completer.future;
      },
      onReject: (_) async {},
    ),),);
    await tester.pump();

    await tester.tap(find.text('确认，就这样做'));
    await tester.pump();

    // 在途态立即生效：主按钮切换为「正在处理…」（禁用），确认按钮消失。
    expect(find.text('正在处理…'), findsOneWidget);
    expect(find.text('确认，就这样做'), findsNothing);

    // 狂点在途态的禁用按钮——不得产生第二次 command。
    await tester.tap(find.text('正在处理…'), warnIfMissed: false);
    await tester.pump();
    await tester.tap(find.text('正在处理…'), warnIfMissed: false);
    await tester.pump();

    expect(approveCalls, 1, reason: '在途期间的重复点击不得产生第二次 command');

    completer.complete();
    await tester.pumpAndSettle();

    // 乐观态诚实：权威回执回来前不显示成功。
    expect(find.text('结果待确认'), findsOneWidget);
    expect(find.text('已完成'), findsNothing);
    expect(find.text('正在处理…'), findsNothing);
  });

  testWidgets('幂等键：同一 proposal 同一动作稳定推导，跨实例一致', (tester) async {
    final keys = <String>[];
    Widget buildCard() => host(ActionProposalCard(
          data: data(proposalId: 'abc-123'),
          onApprove: (key) async => keys.add(key),
          onReject: (_) async {},
        ),);

    await tester.pumpWidget(buildCard());
    await tester.pump();
    await tester.tap(find.text('确认，就这样做'));
    await tester.pumpAndSettle();

    // 卸载再重挂（模拟重进页面后的全新 State）。
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpWidget(buildCard());
    await tester.pump();
    await tester.tap(find.text('确认，就这样做'));
    await tester.pumpAndSettle();

    expect(keys, hasLength(2));
    expect(keys.first, 'u04:abc-123:approve');
    expect(keys.first, keys.last, reason: '重复点击/重建后的键必须一致，服务端据此幂等');
  });

  testWidgets('显式幂等键透传优先于推导键', (tester) async {
    var captured = '';
    await tester.pumpWidget(host(ActionProposalCard(
      data: const ActionProposalCardData(
        proposalId: 'p-9',
        status: ProposalCardStatus.awaitingUser,
        idempotencyKey: 'server-key-1',
      ),
      onApprove: (key) async => captured = key,
      onReject: (_) async {},
    ),),);
    await tester.pump();
    await tester.tap(find.text('确认，就这样做'));
    await tester.pumpAndSettle();
    expect(captured, 'server-key-1');
  });

  // ── 视图模型投影（后端词表 → 卡片状态） ─────────────────────────────────

  test('fromProjection：PENDING + expired 标志投为已过期；diff 保留 changed_fields',
      () {
    final parsed = ActionProposalCardData.fromProjection(const {
      'proposal_id': 'p-2',
      'status': 'PENDING',
      'expired': true,
      'summary': '调整任务时间',
      'authorization': {'mode': 'confirmation'},
      'diff': {
        'changed_fields': [
          {'field': 'due_at', 'before': '周五', 'after': '周六'},
        ],
      },
    });
    expect(parsed.status, ProposalCardStatus.expired);
    expect(parsed.diff.single.field, 'due_at');
  });

  test('fromProjection：auto 授权投为 Sparkle做（agent）', () {
    final parsed = ActionProposalCardData.fromProjection(const {
      'proposal_id': 'p-3',
      'status': 'PENDING',
      'authorization': {'mode': 'auto'},
    });
    expect(parsed.ownership, ProposalTurnOwnership.agent);
  });

  test('fromProjection：未知状态词表按 unknown 诚实处理', () {
    final parsed = ActionProposalCardData.fromProjection(const {
      'proposal_id': 'p-4',
      'status': 'SOMETHING_NEW',
    });
    expect(parsed.status, ProposalCardStatus.unknown);
  });
}
