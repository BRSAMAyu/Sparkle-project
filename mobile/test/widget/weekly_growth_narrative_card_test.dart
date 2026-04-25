import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/insights/data/models/weekly_growth_narrative.dart';
import 'package:sparkle/features/insights/presentation/providers/weekly_growth_narrative_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/weekly_growth_narrative_card.dart';

void main() {
  testWidgets('weekly growth narrative card expands concrete data',
      (tester) async {
    const narrative = WeeklyGrowthNarrative(
      period: '本周成长故事',
      weekStart: '2026-04-20',
      weekEnd: '2026-04-26',
      body:
          '这周你主要把力气放在热力学上，完成了 2 个任务。卡点也很具体：热力学留下了 1 条错题。好消息是，热力学第一定律的掌握度累计往前推了 18.5。',
      sentences: <String>[
        '这周你主要把力气放在热力学上，完成了 2 个任务。',
        '卡点也很具体：热力学留下了 1 条错题。',
        '好消息是，热力学第一定律的掌握度累计往前推了 18.5。',
      ],
      dataPoints: <String, dynamic>{
        'tasks_completed': 2,
        'error_records': 1,
        'reflection_records': 1,
        'mastery_delta': 18.5,
      },
      sourceCounts: <String, int>{
        'task_completions': 2,
        'error_records': 1,
        'reflection_records': 1,
        'mastery_changes': 1,
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
    expect(find.textContaining('热力学'), findsOneWidget);

    await tester.tap(find.byTooltip('展开'));
    await tester.pumpAndSettle();

    expect(find.text('2 个任务'), findsOneWidget);
    expect(find.text('1 条错题'), findsOneWidget);
    expect(find.text('1 次复盘'), findsOneWidget);
    expect(find.text('掌握 +18.5'), findsOneWidget);
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
}
