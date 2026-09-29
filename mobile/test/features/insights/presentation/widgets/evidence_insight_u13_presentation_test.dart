import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/insights/data/models/evidence_insight_card.dart';
import 'package:sparkle/features/insights/presentation/widgets/evidence_insight_card.dart';

import '../../../../shared/i18n_test_helper.dart';

/// V4-U13 · 洞察卡呈现面守卫：原始数值与推断拆开，三态分别呈现。
///
/// 每面一正一反：
/// - 撤回排除显式成行（撤回≠静默消失）；计数为 0 → 无该行（不编造撤回）；
/// - 理解档三态分开呈现（无数据/证据不足/仅定性）；词表外 → 无行；
/// - 样本量真实定义行（去重后/原始/重放丢弃随行）；
/// - 零惩罚可拒绝行只在信封冻结常量成立时渲染；
/// - **夸大表述门继承反例钉**：3 例只有 2 例关联的真实计数卡，整树渲染
///   文案写不出「提升 67%」族因果百分比（D05 门语义在本呈现面继承）。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<void> pumpCard(WidgetTester tester, EvidenceInsightCardData card) =>
      tester.pumpWidget(
        testMaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: EvidenceInsightCardWidget(card: card),
            ),
          ),
        ),
      );

  EvidenceInsightCardData helpedCard({
    int withdrawn = 0,
    String band = 'qualitative_only',
    int censored = 0,
    int missing = 0,
    int samples = 0,
    int raw = 0,
    int dropped = 0,
    Map<String, dynamic>? nextStep,
  }) =>
      EvidenceInsightCardData.fromJson(<String, dynamic>{
        'id': 'interventions_that_helped:rescope:recall_gap',
        'kind': 'interventions_that_helped',
        'window_days': 30,
        'fact': <String, dynamic>{
          'intervention_type': 'rescope',
          'friction_tag': 'recall_gap',
          'n_exposed': 3,
          'n_accepted': 3,
          'n_observed': 2,
          'n_positive': 2,
          'n_negative': 0,
        },
        'interpretation': <String, dynamic>{
          'evidence_strength': 'accumulated',
          'direction': 'positive_association',
          'causal': false,
        },
        'uncertainty': <String, dynamic>{
          'qualifiers': <String>['correlation_not_causation'],
          'samples': samples,
          'outcome_samples_raw': raw,
          'duplicate_outcome_samples_dropped': dropped,
          'withdrawn_refs_excluded': withdrawn,
        },
        'understanding': <String, dynamic>{
          'claim_allowed': band == 'qualitative_only',
          'band': band,
          'samples': samples,
          'missing': missing,
          'censored': censored,
        },
        if (nextStep != null) 'next_step': nextStep,
        'evidence': <dynamic>[
          <String, dynamic>{
            'label_key': 'evidence_directive_log',
            'deep_link': '/learning/insights/directives',
            'refs': <String>['d1'],
          },
        ],
        'implication': <String, dynamic>{
          'action_key': 'review_directives',
          'deep_link': '/learning/insights/directives',
        },
      });

  group('撤回排除显式在册（验收②「撤回」呈现面）', () {
    testWidgets('撤回 2 条 → 显式成行「已排除 2 条…」', (tester) async {
      await pumpCard(tester, helpedCard(withdrawn: 2));
      expect(find.textContaining('已排除 2 条'), findsOneWidget);
    });

    testWidgets('撤回为 0 → 无撤回行（不编造撤回）', (tester) async {
      await pumpCard(tester, helpedCard());
      expect(find.textContaining('已排除'), findsNothing);
    });
  });

  group('理解档三态分别呈现（验收②「无数据/不足」呈现面）', () {
    testWidgets('no_data 档 → 「还没有可分析的数据，无法得出结论」', (tester) async {
      await pumpCard(tester, helpedCard(band: 'no_data'));
      expect(find.textContaining('还没有可分析的数据'), findsOneWidget);
    });

    testWidgets('incomplete 档（censored=1, missing=2）→ 双口径如实成行', (tester) async {
      await pumpCard(tester, helpedCard(band: 'incomplete_evidence', censored: 1, missing: 2));
      expect(find.textContaining('证据不足：1 条结果未到期、2 条来源已不可定位'), findsOneWidget);
    });

    testWidgets('allowed 档 → 「定性观察」措辞，绝不出「充分理解」宣称', (tester) async {
      await pumpCard(tester, helpedCard());
      expect(find.textContaining('定性观察'), findsOneWidget);
      expect(find.textContaining('充分理解'), findsNothing);
    });

    testWidgets('词表外档位 → 无理解行（不臆测档位）', (tester) async {
      await pumpCard(tester, helpedCard(band: 'fully_understood'));
      expect(find.textContaining('充分理解'), findsNothing);
      expect(find.textContaining('定性观察'), findsNothing);
      expect(find.textContaining('证据不足'), findsNothing);
    });
  });

  group('样本量真实定义（验收①「样本」呈现面）', () {
    testWidgets('raw=3 去重 1 丢 2 → 去重口径整行如实呈现', (tester) async {
      await pumpCard(
        tester,
        helpedCard(samples: 1, raw: 3, dropped: 2),
      );
      expect(
        find.textContaining('样本＝去重后方向观察 1 条（原始投递 3 条，重放重复 2 条不计入样本量）'),
        findsOneWidget,
      );
    });

    testWidgets('无方向观察 → 无样本定义行（不虚构样本）', (tester) async {
      await pumpCard(tester, helpedCard());
      expect(find.textContaining('样本＝去重后方向观察'), findsNothing);
    });
  });

  group('单主建议信封零惩罚面（fail-closed）', () {
    testWidgets('冻结常量成立 → 「可忽略且无任何影响」成行', (tester) async {
      await pumpCard(
        tester,
        helpedCard(
          nextStep: <String, dynamic>{
            'observation_id': 'card-1',
            'user_can_reject': true,
            'reject_penalty': 'none',
          },
        ),
      );
      expect(find.textContaining('可以忽略'), findsOneWidget);
    });

    testWidgets('契约漂移（penalty 非 none）→ 不渲染零惩罚宣称', (tester) async {
      await pumpCard(
        tester,
        helpedCard(
          nextStep: <String, dynamic>{
            'observation_id': 'card-1',
            'user_can_reject': true,
            'reject_penalty': 'photon_-10',
          },
        ),
      );
      expect(find.textContaining('可以忽略'), findsNothing);
    });
  });

  group('夸大表述门继承反例钉（D05 门语义在本呈现面继承）', () {
    testWidgets('3 例只有 2 例关联的真实计数卡：整树写不出因果百分比', (tester) async {
      await pumpCard(
        tester,
        EvidenceInsightCardData.fromJson(<String, dynamic>{
          'id': 'interventions_that_helped:rescope:recall_gap',
          'kind': 'interventions_that_helped',
          'window_days': 30,
          'fact': <String, dynamic>{
            'intervention_type': 'rescope',
            'friction_tag': 'recall_gap',
            'n_exposed': 3,
            'n_accepted': 2,
            'n_observed': 2,
            'n_positive': 2,
            'n_negative': 0,
          },
          'interpretation': <String, dynamic>{
            'evidence_strength': 'accumulated',
            'direction': 'positive_association',
            'causal': false,
          },
          'uncertainty': <String, dynamic>{
            'qualifiers': <String>[
              'correlation_not_causation',
              'small_sample',
            ],
            'samples': 2,
            'outcome_samples_raw': 2,
            'duplicate_outcome_samples_dropped': 0,
            'withdrawn_refs_excluded': 0,
          },
          'understanding': <String, dynamic>{
            'claim_allowed': false,
            'band': 'incomplete_evidence',
            'samples': 2,
            'missing': 1,
            'censored': 0,
          },
          'evidence': <dynamic>[],
          'implication': <String, dynamic>{
            'action_key': 'review_directives',
            'deep_link': '/learning/insights/directives',
          },
        }),
      );

      final renderedTexts = tester
          .widgetList<Text>(find.byType(Text))
          .map((t) => t.data ?? '')
          .join('\n');
      // 因果/成效措辞 × 百分比 双通道都不出现。
      expect(renderedTexts.contains('67%'), isFalse);
      expect(
        renderedTexts.contains('%'),
        isFalse,
        reason: 'D-07 卡契约禁百分比；呈现面不得引入',
      );
      for (final banned in const ['提升', '有效', '因此', '导致']) {
        expect(
          renderedTexts.contains(banned),
          isFalse,
          reason: '因果措辞「$banned」不得出现在计数卡',
        );
      }
    });
  });

  group('DS 令牌消费（UI 纪律）', () {
    testWidgets('卡面用 GraphiteCardSurface + DS 间距，不引像素装饰', (tester) async {
      await pumpCard(tester, helpedCard(withdrawn: 1));
      expect(find.byType(GraphiteCardSurface), findsOneWidget);
    });
  });
}
