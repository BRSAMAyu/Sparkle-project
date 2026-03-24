import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/widgets/recommendation_feedback_widgets.dart';

void main() {
  testWidgets('RecommendationFeedbackPromptCard renders friend prompt',
      (tester) async {
    final prompt = RecommendationFeedbackPrompt(
      promptId: 'prompt_friend_1',
      itemType: RecommendationItemType.friend,
      itemId: 'user_2',
      stage: RecommendationFeedbackStage.followUp,
      triggerAction: 'view',
      title: '看看这位责任伙伴候选人是否合拍',
      subtitle: '你浏览过这条推荐，帮我们判断它有没有击中你的标准。',
      dueAt: DateTime(2026, 3, 20, 12),
      user: UserBrief(
        id: 'user_2',
        username: 'lin',
        nickname: 'Lynn',
      ),
      reasonTags: const ['subject_overlap', 'preference_alignment'],
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppThemes.lightTheme,
        home: Scaffold(
          body: RecommendationFeedbackPromptCard(
            prompt: prompt,
            onRespond: () {},
          ),
        ),
      ),
    );

    expect(find.text('看看这位责任伙伴候选人是否合拍'), findsOneWidget);
    expect(find.textContaining('关于 Lynn 的跟进反馈'), findsOneWidget);
    expect(find.text('开始校准'), findsOneWidget);
    expect(find.text('主题重合'), findsOneWidget);
    expect(find.text('学习节奏接近'), findsOneWidget);
  });

  testWidgets('RecommendationFeedbackInsightCard renders group insight',
      (tester) async {
    final insight = RecommendationFeedbackInsight(
      itemType: RecommendationItemType.group,
      recentFeedbackCount: 6,
      averageScores: const {
        'interest_match_score': 4.3,
        'activity_score': 3.8,
      },
      topNegativeSignals: const ['want_more_tag_match'],
      globalAdjustments: const {
        'tag_score': 1.25,
        'quality': 1.12,
      },
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppThemes.lightTheme,
        home: Scaffold(
          body: RecommendationFeedbackInsightCard(insight: insight),
        ),
      ),
    );

    expect(find.text('你的社群推荐偏好'), findsOneWidget);
    expect(find.text('近 6 次'), findsOneWidget);
    expect(find.textContaining('兴趣匹配 4.3'), findsOneWidget);
    expect(find.textContaining('系统在回避：兴趣不够对口'), findsOneWidget);
    expect(find.textContaining('当前更偏向：标签匹配、质量'), findsOneWidget);
  });

}
