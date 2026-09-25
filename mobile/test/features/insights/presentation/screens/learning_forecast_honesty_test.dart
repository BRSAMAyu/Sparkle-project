import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/predictive_service.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/insights/presentation/screens/learning_forecast_screen.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

import '../../../../shared/i18n_test_helper.dart';

/// D-07 诚实性红线（预测洞察面）：不得渲染无定义分数与假精确预测。
///
/// 红测口径：喂给屏幕包含 confidence/next_active_time/risk_score/
/// difficulty_score 的数据，断言这些假精确面【不】出现——base 上置信度
/// 百分比徽章（90%）、「预测下次学习时间」、「风险指数: 72/100」进度条
/// 全部真实渲染，本测试在 base 必红；重构后（定性词替代，M-10 口径）转绿。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets(
      'forecast screen renders no fake-precision scores, percentages or '
      'precise predictions when backend sends them', (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          predictiveServiceProvider.overrideWithValue(_FakePredictiveService()),
          achievementRepositoryProvider
              .overrideWithValue(_FakeAchievementRepository()),
          nightlyReviewProvider.overrideWith((ref) async => null),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const LearningForecastScreen(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));

    // 假精确红线：以下 face 一律不得出现。
    expect(
      find.textContaining('%'),
      findsNothing,
      reason: '置信度百分比徽章是假精确（M-10 清除口径），不得渲染',
    );
    expect(
      find.textContaining('/100'),
      findsNothing,
      reason: '风险指数 x/100 是无定义分数，不得渲染',
    );
    expect(
      find.textContaining('预测下次学习时间'),
      findsNothing,
      reason: '精确到时刻的下一次学习预测是假精确预测，不得渲染',
    );
    expect(
      find.textContaining('置信度'),
      findsNothing,
      reason: '置信度黑话不得出现（定性词替代）',
    );
    expect(
      find.textContaining('风险指数'),
      findsNothing,
      reason: '风险指数黑话不得出现',
    );

    // 分数条属于无定义分数渲染面。
    expect(
      find.byType(LinearProgressIndicator),
      findsNothing,
      reason: '0-1 分数进度条是无定义能力分数渲染面',
    );

    // 定性观察保留：流失风险档位文字仍可见（低/中/高定性词）。
    expect(find.textContaining('风险'), findsWidgets);
  });
}

class _FakePredictiveService implements PredictiveService {
  @override
  Future<Map<String, dynamic>> getDashboardData() async => <String, dynamic>{
        'engagement_forecast': <String, dynamic>{
          'confidence': 0.9,
          'next_active_time': '2026-09-26T15:00:00.000',
          'dropout_risk': 'low',
        },
        'dropout_risk': <String, dynamic>{
          'risk_score': 72,
          'risk_level': 'high',
          'intervention_suggestions': <String>['先完成一个小任务'],
        },
        'optimal_time': <String, dynamic>{
          'best_hours': <int>[9],
          'best_weekdays': <int>[1],
          'sample_size': 12,
          'confidence': 0.88,
          'reason': '近期记录',
          'data_status': 'ok',
        },
      };

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeAchievementRepository implements AchievementRepository {
  @override
  Future<List<StreakDayRecord>> getStreakHistory({int days = 90}) async =>
      const <StreakDayRecord>[];

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
