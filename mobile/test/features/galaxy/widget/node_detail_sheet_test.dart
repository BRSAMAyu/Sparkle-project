import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/data/models/node_history_model.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/node_detail_sheet.dart';

void main() {
  testWidgets('NodeDetailSheet renders mastery, study count, and errors', (
    tester,
  ) async {
    Map<String, dynamic>? reviewContext;

    final history = GalaxyNodeHistory(
      nodeId: 'cn.tcp_flow',
      nodeLabel: 'TCP流量控制',
      mastery: 0.65,
      studyCount: 3,
      lastStudiedAt: DateTime.now().subtract(const Duration(days: 2)),
      relatedErrors: const [
        GalaxyNodeErrorItem(
          id: 'error-1',
          questionText: 'rwnd 和 cwnd 的区别是什么？',
          analysisSummary: '窗口变量混淆',
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: NodeDetailSheet(
              nodeId: 'cn.tcp_flow',
              nodeLabel: 'TCP流量控制',
              initialHistory: history,
              onStartReview: (context) => reviewContext = context,
            ),
          ),
        ),
      ),
    );

    expect(find.text('TCP流量控制'), findsOneWidget);
    expect(find.text('65%'), findsOneWidget);
    expect(find.text('已学习 3 次'), findsOneWidget);
    expect(find.text('相关错题 1 道'), findsOneWidget);
    expect(find.text('rwnd 和 cwnd 的区别是什么？'), findsOneWidget);

    await tester.tap(find.text('开始复习'));
    await tester.pump();

    expect(reviewContext, {
      'review_node': 'cn.tcp_flow',
      'node_label': 'TCP流量控制',
    });
  });

  testWidgets('NodeDetailSheet shows not studied when mastery is zero', (
    tester,
  ) async {
    const history = GalaxyNodeHistory(
      nodeId: 'cn.empty',
      nodeLabel: '空白节点',
      mastery: 0,
      studyCount: 0,
    );

    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: NodeDetailSheet(
              nodeId: 'cn.empty',
              nodeLabel: '空白节点',
              initialHistory: history,
            ),
          ),
        ),
      ),
    );

    expect(find.text('尚未学习'), findsWidgets);
    expect(find.text('0%'), findsNothing);
  });
}
