import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart';
import 'package:sparkle/features/tools/presentation/widgets/focus_stats_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';

import '../../../../shared/i18n_test_helper.dart';

/// EE-G5（A-SPEC3 §4.4.2 改造 #5）验收：FocusStatsTool 首路径加载期
/// 呈现贴布局骨架（有结构），裸 spinner 不再出现。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets('加载期：骨架结构在位（指标行 + 区块卡），无裸 spinner',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          focusStatisticsProvider.overrideWith(_LoadingFocusStatistics.new),
        ],
        child: testMaterialApp(
          home: const Scaffold(body: FocusStatsTool()),
        ),
      ),
    );
    // 首帧 + postFrame 回调（stub 的 load* 均为 no-op，不触网）。
    await tester.pump();
    await tester.pump();

    expect(find.byType(SparkleSkeleton), findsWidgets);
    expect(find.byType(ToolMetricRow), findsOneWidget);
    expect(find.byType(ToolSectionCard), findsWidgets);
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });
}

/// 恒定 loading 态的 stub：绕开仓库/网络依赖，只验加载期 UI 形态。
class _LoadingFocusStatistics extends FocusStatistics {
  @override
  FocusStatisticsState build() => const FocusStatisticsState(isLoading: true);

  @override
  Future<void> loadTodayStats() async {}

  @override
  Future<void> loadWeeklyStats() async {}

  @override
  Future<void> loadSessionHistory({int limit = 20}) async {}
}
