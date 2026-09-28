import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/data/models/node_history_model.dart';
import 'package:sparkle/features/galaxy/domain/capability_channel.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/node_detail_sheet.dart';

import '../../../shared/i18n_test_helper.dart';

/// V4-U05 · 节点详情来源抽屉（能力证据与来源面）。
///
/// 卡面验收钉（每面一正一反）：
/// - 「节点点开来源与投影 version 一致」：verified 节点的抽屉渲染独立检验
///   标签 + 溯源行 + 投影版本（正）；数据面没有版本时不显示编造版本号
///   （反）。
/// - 「PRACTICED 不显示为已掌握」：练习星详情显示「练习过 · 未独立检验」
///   且全树无「独立检验通过/已掌握」声称（反例钉）。
/// - 「无数据不造进度」：无通道数据如实显示 unknown 面 + 「暂无来源记录」
///   （反）；掌握度 ≤0 时既有的「尚未学习」诚实面不被能力面破坏（正）。
/// - 200% 字体：能力面在超大字号下完整渲染无异常（可读性包容面）。
void main() {
  setUp(setUpI18nForTesting);

  Future<void> pumpSheet(
    WidgetTester tester, {
    required GalaxyNodeHistory history,
    GalaxyNodeCapabilityEvidence? capability,
    List<Map<String, dynamic>> graphEventSources = const [],
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: Scaffold(
            body: NodeDetailSheet(
              nodeId: 'cn.tcp_flow',
              nodeLabel: 'TCP流量控制',
              initialHistory: history,
              capability: capability,
              graphEventSources: graphEventSources,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  GalaxyNodeHistory historyOf(double mastery) => GalaxyNodeHistory(
        nodeId: 'cn.tcp_flow',
        nodeLabel: 'TCP流量控制',
        mastery: mastery,
        studyCount: 3,
      );

  testWidgets(
    'verified 节点：来源抽屉呈现独立检验 + 溯源行 + 投影版本（正）',
    (tester) async {
      await pumpSheet(
        tester,
        history: historyOf(0.85),
        capability: const GalaxyNodeCapabilityEvidence(
          channel: GalaxyCapabilityChannel.verified,
          hasChannelData: true,
          projectionVersion: 7,
          evidenceCount: 2,
        ),
        graphEventSources: const [
          {
            'source_type': 'quiz_feedback',
            'label': '第 3 章测验',
            'reference_id': 'quiz_1',
            'recorded_at': '2026-09-20T10:00:00.000Z',
          },
          {
            'source_type': 'outcome_ledger',
            'reference_id': 'outcome_9',
            'recorded_at': '2026-09-21T10:00:00.000Z',
          },
        ],
      );

      expect(find.text('能力证据与来源'), findsOneWidget);
      expect(find.text('独立检验通过'), findsOneWidget);
      expect(find.text('掌握度由独立检验（测验等）支撑。'), findsOneWidget);
      // 溯源行：封闭词表映射 + 原始码回退如实并存。
      expect(find.textContaining('独立测验'), findsOneWidget);
      expect(find.textContaining('学习成果记录'), findsOneWidget);
      // 投影版本 = 图快照版本（节点轨迹与来源同一投影）。
      expect(find.text('投影版本 v7'), findsOneWidget);
    },
  );

  testWidgets(
    '反例钉：practiced 高分（85%）星详情绝不显示已掌握/检验通过声称',
    (tester) async {
      await pumpSheet(
        tester,
        history: historyOf(0.85),
        capability: const GalaxyNodeCapabilityEvidence(
          channel: GalaxyCapabilityChannel.practiced,
          hasChannelData: true,
          projectionVersion: 4,
        ),
        graphEventSources: const [
          {
            'source_type': 'focus_session',
            'reference_id': 'focus_1',
            'recorded_at': '2026-09-22T08:00:00.000Z',
          },
        ],
      );

      // 通道如实：练习过 + 明示不代表已掌握；时长源=活动痕迹词。
      expect(find.text('练习过 · 未独立检验'), findsOneWidget);
      expect(find.textContaining('不代表已掌握'), findsOneWidget);
      expect(find.textContaining('学习时长记录'), findsOneWidget);
      expect(find.text('投影版本 v4'), findsOneWidget);

      // 反例钉：全树无掌握声称（标签面精确断言；诚实否定文案
      // 「不代表已掌握」是本通道的正确呈现，不算声称）。
      expect(find.text('独立检验通过'), findsNothing);
      expect(find.text('已掌握'), findsNothing);
      expect(find.textContaining('掌握度由独立检验'), findsNothing);
    },
  );

  testWidgets(
    '反例：无通道数据（null capability）诚实降级 unknown 面，不造版本不造来源',
    (tester) async {
      await pumpSheet(tester, history: historyOf(0.5));

      expect(find.text('证据通道未知'), findsOneWidget);
      expect(find.text('当前数据没有能力检验信息；这里不显示掌握进度。'), findsOneWidget);
      expect(find.text('暂无来源记录'), findsOneWidget);
      expect(find.text('投影版本未知'), findsOneWidget);
      // 无数据不造版本：树中不存在任何「投影版本 vN」编造。
      expect(find.textContaining(RegExp(r'投影版本 v\d')), findsNothing);
    },
  );

  testWidgets(
    '无数据不造进度（正）：掌握度 0 的未学习节点，能力面如实不显示进度声称',
    (tester) async {
      await pumpSheet(
        tester,
        history: historyOf(0),
        capability: const GalaxyNodeCapabilityEvidence(
          channel: GalaxyCapabilityChannel.traceOnly,
          hasChannelData: true,
        ),
        graphEventSources: const [
          {
            'source_type': 'study_record',
            'reference_id': 'rec_1',
            'recorded_at': '2026-09-25T08:00:00.000Z',
          },
        ],
      );

      // 既有诚实面保持：0 掌握度显示「尚未学习」而非 0%。
      expect(find.text('尚未学习'), findsWidgets);
      expect(find.text('0%'), findsNothing);
      // 痕迹通道如实：仅活动痕迹、不计入能力。
      expect(find.text('仅活动痕迹'), findsOneWidget);
      expect(find.text('只有学习时长等参与记录，不计入能力掌握。'), findsOneWidget);
    },
  );

  testWidgets(
    'non_human / trace_only 通道标签互异且如实（四态词表覆盖面）',
    (tester) async {
      await pumpSheet(
        tester,
        history: historyOf(0.4),
        capability: const GalaxyNodeCapabilityEvidence(
          channel: GalaxyCapabilityChannel.nonHuman,
          hasChannelData: true,
          projectionVersion: 9,
        ),
      );
      expect(find.text('Agent 产物'), findsOneWidget);
      expect(find.text('这项工作由 Agent 完成，不计入个人能力。'), findsOneWidget);
      expect(find.text('独立检验通过'), findsNothing);
    },
  );

  testWidgets(
    '200% 字体：能力面完整渲染，关键文案与版本行仍可见（包容面）',
    (tester) async {
      tester.view.physicalSize = const Size(1170, 2100);
      tester.view.devicePixelRatio = 3.0;
      tester.platformDispatcher.textScaleFactorTestValue = 2.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);

      await pumpSheet(
        tester,
        history: historyOf(0.85),
        capability: const GalaxyNodeCapabilityEvidence(
          channel: GalaxyCapabilityChannel.verified,
          hasChannelData: true,
          projectionVersion: 12,
        ),
        graphEventSources: const [
          {
            'source_type': 'quiz_feedback',
            'reference_id': 'quiz_1',
            'recorded_at': '2026-09-20T10:00:00.000Z',
          },
        ],
      );

      expect(tester.takeException(), isNull);
      expect(find.text('独立检验通过'), findsOneWidget);
      expect(find.text('投影版本 v12'), findsOneWidget);
    },
  );
}
