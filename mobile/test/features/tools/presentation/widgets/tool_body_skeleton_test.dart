import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_body_skeleton.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';

import '../../../../shared/i18n_test_helper.dart';

/// EE-G5（A-SPEC3 §4.4.2 改造 #5）验收：tool body 加载骨架是**结构化占位**
/// （贴 ToolMetricRow/ToolSectionCard 形状），不再是居中裸 spinner。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets('骨架期有结构：指标卡行 + 区块卡 + 灰条骨架，零 spinner',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: SingleChildScrollView(
            child: ToolBodySkeleton(
              metricCount: 3,
              sectionContentHeights: [168, 120],
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    // 结构占位：骨架灰条存在、内容容器（指标行/区块卡）存在。
    expect(find.byType(SparkleSkeleton), findsWidgets);
    expect(find.byType(ToolMetricRow), findsOneWidget);
    expect(find.byType(ToolSectionCard), findsNWidgets(2));

    // 裸 spinner 退役：首路径不允许再出现居中转圈。
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('指标卡占位数与区块数按参数生成（notes 形状：2 卡 1 区块）',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: SingleChildScrollView(
            child: ToolBodySkeleton(
              metricCount: 2,
              sectionContentHeights: [240],
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.byType(ToolMetricRow), findsOneWidget);
    expect(find.byType(ToolSectionCard), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });
}
