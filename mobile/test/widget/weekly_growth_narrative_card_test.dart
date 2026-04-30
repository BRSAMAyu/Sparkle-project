import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/insights/data/models/weekly_growth_narrative.dart';
import 'package:sparkle/features/insights/presentation/providers/weekly_growth_narrative_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/weekly_growth_narrative_card.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('weekly growth narrative card expands concrete data',
      (tester) async {
    const narrative = WeeklyGrowthNarrative(
      period: '本周成长故事',
      weekStart: '2026-04-20',
      weekEnd: '2026-04-26',
      body:
          '这周你学习了 5 天。掌握了 TCP 三次握手、子网划分 等知识点。还修复了 2 个反复出现的错误。最大的进步：路由算法 的掌握度从 30% 提升到了 65%。下周目标：继续把网络层相关的核心概念吃透。',
      sentences: <String>[
        '这周你学习了 5 天。',
        '掌握了 TCP 三次握手、子网划分 等知识点。',
        '还修复了 2 个反复出现的错误。',
      ],
      highlights: <String>[
        '这周你学习了 5 天。',
        '掌握了 TCP 三次握手、子网划分 等知识点。',
        '还修复了 2 个反复出现的错误。',
      ],
      biggestImprovement: <String, dynamic>{
        'node_name': '路由算法',
        'before_mastery': 30,
        'after_mastery': 65,
      },
      nextWeekSuggestion: '继续把网络层相关的核心概念吃透。',
      dataPoints: <String, dynamic>{
        'tasks_completed': 2,
        'errors_fixed': 2,
        'reflection_records': 1,
        'mastery_delta': 18.5,
        'study_days': 5,
      },
      sourceCounts: <String, int>{
        'task_completions': 2,
        'error_records': 2,
        'error_review_records': 2,
        'reflection_records': 1,
        'mastery_changes': 1,
        'study_days': 5,
      },
      isPlaceholder: false,
      generatedAt: '2026-04-25T10:00:00',
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          weeklyGrowthNarrativeProvider.overrideWith(
            (ref) async => narrative,
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: WeeklyGrowthNarrativeCard(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('本周成长故事'), findsOneWidget);
    expect(find.textContaining('TCP 三次握手'), findsOneWidget);

    await tester.tap(find.byTooltip('展开'));
    await tester.pumpAndSettle();

    expect(find.text('5 天学习'), findsOneWidget);
    expect(find.text('2 个任务'), findsOneWidget);
    expect(find.text('修复 2 个错误'), findsOneWidget);
    expect(find.text('1 次复盘'), findsOneWidget);
    expect(find.text('掌握 +18.5'), findsOneWidget);
    expect(find.textContaining('最大进步：路由算法 30% → 65%'), findsOneWidget);
    expect(
      find.textContaining('下周目标：继续把网络层相关的核心概念吃透'),
      findsWidgets,
    );
  });

  testWidgets('weekly growth narrative card shows first week placeholder',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          weeklyGrowthNarrativeProvider.overrideWith(
            (ref) async => WeeklyGrowthNarrative.placeholder(),
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: WeeklyGrowthNarrativeCard(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('这是你的第一周，先开始吧'), findsOneWidget);
  });

  testWidgets('weekly growth narrative card honors initial expanded state',
      (tester) async {
    const narrative = WeeklyGrowthNarrative(
      period: '本周成长故事',
      weekStart: '2026-04-20',
      weekEnd: '2026-04-26',
      body: '这周你学习了 5 天。',
      sentences: <String>['这周你学习了 5 天。'],
      highlights: <String>['高数错题复盘更稳定了。'],
      biggestImprovement: <String, dynamic>{},
      nextWeekSuggestion: '',
      dataPoints: <String, dynamic>{'study_days': 5},
      sourceCounts: <String, int>{'study_days': 5},
      isPlaceholder: false,
      generatedAt: '2026-04-25T10:00:00',
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          weeklyGrowthNarrativeProvider.overrideWith(
            (ref) async => narrative,
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: WeeklyGrowthNarrativeCard(initialExpanded: true),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byTooltip('收起'), findsOneWidget);
    expect(find.text('5 天学习'), findsOneWidget);
    expect(find.text('高数错题复盘更稳定了。'), findsOneWidget);
  });

  testWidgets('weekly growth narrative card expands when route state updates',
      (tester) async {
    const narrative = WeeklyGrowthNarrative(
      period: '本周成长故事',
      weekStart: '2026-04-20',
      weekEnd: '2026-04-26',
      body: '这周你学习了 5 天。',
      sentences: <String>['这周你学习了 5 天。'],
      highlights: <String>['高数错题复盘更稳定了。'],
      biggestImprovement: <String, dynamic>{},
      nextWeekSuggestion: '',
      dataPoints: <String, dynamic>{'study_days': 5},
      sourceCounts: <String, int>{'study_days': 5},
      isPlaceholder: false,
      generatedAt: '2026-04-25T10:00:00',
    );

    Widget buildCard({required bool initialExpanded}) {
      return ProviderScope(
        overrides: <Override>[
          weeklyGrowthNarrativeProvider.overrideWith(
            (ref) async => narrative,
          ),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: WeeklyGrowthNarrativeCard(
              initialExpanded: initialExpanded,
            ),
          ),
        ),
      );
    }

    await tester.pumpWidget(buildCard(initialExpanded: false));
    await tester.pumpAndSettle();
    expect(find.byTooltip('展开'), findsOneWidget);

    await tester.pumpWidget(buildCard(initialExpanded: true));
    await tester.pumpAndSettle();
    expect(find.byTooltip('收起'), findsOneWidget);
    expect(find.text('高数错题复盘更稳定了。'), findsOneWidget);
  });
}
