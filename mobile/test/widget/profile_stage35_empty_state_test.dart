import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/widgets/achievement_summary_card.dart';
import 'package:sparkle/features/user/presentation/widgets/active_skills_card.dart';
import 'package:sparkle/features/user/presentation/widgets/engagement_state_badge.dart';
import 'package:sparkle/features/user/presentation/widgets/foresight_card.dart';
import 'package:sparkle/features/user/presentation/widgets/working_memory_card.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('Stage35 cards render empty-state copy instead of blank content',
      (
    tester,
  ) async {
    await tester.pumpWidget(
      testMaterialApp(home: Scaffold(
          body: SingleChildScrollView(
            child: Column(
              children: [
                WorkingMemoryCard(snapshot: null),
                AchievementSummaryCard(summary: null),
                ActiveSkillsCard(summary: null),
                EngagementStateBadge(state: null),
                ForesightCard(hint: null),
              ],
            ),
          ),
        ),),
    );

    expect(find.text('最近没有需要继续挂在前台的工作记忆，先按当前节奏推进就好。'), findsOneWidget);
    expect(find.text('近期还没有新的高光或进度变化，继续推进会在这里留下痕迹。'), findsOneWidget);
    expect(find.text('这一轮还没有明显命中的技能摘要，先保持默认支持方式。'), findsOneWidget);
    expect(find.text('最近暂无记录'), findsOneWidget);
    expect(find.text('暂时还没有可展示的前瞻提示，后端会继续观察。'), findsOneWidget);
  });
}
