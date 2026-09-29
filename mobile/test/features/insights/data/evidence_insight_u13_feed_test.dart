import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/insights/data/models/evidence_insight_card.dart';

/// V4-U13 · 洞察 feed 模型守卫（消费 D05 `insight.presentation.v1` 契约出口）。
///
/// 每面一正一反：
/// - 版本门 fail-closed（合法 schema → ready；缺/错 schema → unsupported）；
/// - 无数据显式态（合法 schema 零卡 → no_data，与 unsupported 互斥）；
/// - 夸大表述门继承反例钉：`meta.presentation_gate_dropped` 登记的违例卡
///   永不作为卡渲染（gate-dropped id 含「提升67%」也绝不进 cards）；
/// - 理解档/样本/撤回排除计数如实解析；词表外值 fail-closed（unknown）；
/// - 信封零惩罚宣称只在后端冻结常量成立时成立（契约漂移 → 不渲染依据）。
void main() {
  Map<String, dynamic> payload({
    Object? schema = 'insight.presentation.v1',
    List<Map<String, dynamic>> cards = const [],
    Map<String, dynamic>? revisit,
  }) =>
      <String, dynamic>{
        if (schema != null) 'presentation_schema': schema,
        'window_days': 30,
        'cards': cards,
        if (revisit != null) 'revisit': revisit,
      };

  Map<String, dynamic> helpedCardJson({
    int samples = 2,
    int raw = 2,
    int dropped = 0,
    int withdrawn = 0,
    String band = 'qualitative_only',
    Map<String, dynamic>? nextStep,
  }) =>
      <String, dynamic>{
        'id': 'interventions_that_helped:rescope:recall_gap',
        'kind': 'interventions_that_helped',
        'fact': <String, dynamic>{
          'n_exposed': 3,
          'n_observed': 2,
          'n_positive': 2,
        },
        'interpretation': <String, dynamic>{
          'evidence_strength': 'accumulated',
          'causal': false,
        },
        'uncertainty': <String, dynamic>{
          'samples': samples,
          'outcome_samples_raw': raw,
          'duplicate_outcome_samples_dropped': dropped,
          'not_yet_observed': 1,
          'withdrawn_refs_excluded': withdrawn,
        },
        'understanding': <String, dynamic>{
          'claim_allowed': band == 'qualitative_only',
          'band': band,
          'samples': samples,
          'missing': 0,
          'censored': 1,
        },
        if (nextStep != null) 'next_step': nextStep,
        'evidence': const <dynamic>[],
        'implication': <String, dynamic>{'action_key': 'review_directives'},
      };

  group('V4-U13 feed 版本门（fail-closed）', () {
    test('合法 insight.presentation.v1 → ready（有卡）', () {
      final feed = EvidenceInsightFeedData.fromJson(
        payload(cards: [helpedCardJson()]),
        meta: const <String, dynamic>{},
      );
      expect(feed.isReady, isTrue);
      expect(feed.isUnsupported, isFalse);
      expect(feed.isNoData, isFalse);
      expect(feed.cards, hasLength(1));
    });

    test('schema 缺失或未知版本 → unsupported（不伪造契约字段、与 no-data 互斥）',
        () {
      final missing = EvidenceInsightFeedData.fromJson(
        payload(schema: null),
        meta: const <String, dynamic>{},
      );
      final unknown = EvidenceInsightFeedData.fromJson(
        payload(schema: 'insight.presentation.v2'),
        meta: const <String, dynamic>{},
      );
      for (final feed in [missing, unknown]) {
        expect(feed.isUnsupported, isTrue);
        expect(feed.isNoData, isFalse);
        expect(feed.cards, isEmpty);
      }
    });

    test('合法 schema 零卡 → no_data 显式态（不是 unsupported、不是 ready）', () {
      final feed = EvidenceInsightFeedData.fromJson(
        payload(),
        meta: const <String, dynamic>{
          'note': 'no evidence in window: ...',
        },
      );
      expect(feed.isNoData, isTrue);
      expect(feed.isUnsupported, isFalse);
      expect(feed.emptyNote, contains('no evidence in window'));
    });
  });

  group('V4-U13 夸大表述门继承（反例钉：扣下的卡绝不渲染）', () {
    test('meta.presentation_gate_dropped 登记进 gateDroppedCount，绝不进 cards',
        () {
      final feed = EvidenceInsightFeedData.fromJson(
        payload(cards: [helpedCardJson()]),
        meta: <String, dynamic>{
          'presentation_gate_dropped': <dynamic>[
            <String, dynamic>{
              'id': 'fabricated:causal_percentage',
              'reasons': <String>['causal_percentage_claim'],
            },
          ],
        },
      );
      expect(feed.gateDroppedCount, 1);
      // 后端已扣下的卡不在 cards 里；模型面不提供任何复活路径。
      expect(
        feed.cards.map((c) => c.id),
        everyElement(isNot('fabricated:causal_percentage')),
      );
    });
  });

  group('V4-U13 理解档/样本/撤回计数解析（词表外 fail-closed）', () {
    test('理解档三档如实解析', () {
      for (final entry in <String, EvidenceUnderstandingBand>{
        'qualitative_only': EvidenceUnderstandingBand.allowed,
        'incomplete_evidence': EvidenceUnderstandingBand.incomplete,
        'no_data': EvidenceUnderstandingBand.noData,
      }.entries) {
        final card = EvidenceInsightCardData.fromJson(
          helpedCardJson(band: entry.key),
        );
        expect(card.understanding.band, entry.value);
      }
    });

    test('词表外理解档 → unknown（不渲染、不臆测）', () {
      final card = EvidenceInsightCardData.fromJson(
        helpedCardJson(band: 'fully_understood'),
      );
      expect(card.understanding.band, EvidenceUnderstandingBand.unknown);
      expect(card.understanding.claimAllowed, isFalse);
    });

    test('样本量定义字段（去重后/原始/重放丢弃）与撤回排除计数如实解析', () {
      final card = EvidenceInsightCardData.fromJson(
        helpedCardJson(samples: 1, raw: 3, dropped: 2, withdrawn: 4),
      );
      expect(card.samples, 1);
      expect(card.outcomeSamplesRaw, 3);
      expect(card.duplicateOutcomeSamplesDropped, 2);
      expect(card.withdrawnRefsExcluded, 4);
    });

    test('契约字段缺失 → 计数缺省 0、档位 unknown（不编造）', () {
      final bare = helpedCardJson()..remove('understanding');
      bare['uncertainty'] = <String, dynamic>{};
      final card = EvidenceInsightCardData.fromJson(bare);
      expect(card.withdrawnRefsExcluded, 0);
      expect(card.outcomeSamplesRaw, 0);
      expect(card.understanding.band, EvidenceUnderstandingBand.unknown);
      expect(card.nextStep, isNull);
    });
  });

  group('V4-U13 单主建议信封（零惩罚宣称 fail-closed）', () {
    test('user_can_reject=true 且 reject_penalty=none → 零惩罚可拒绝成立', () {
      final card = EvidenceInsightCardData.fromJson(
        helpedCardJson(
          nextStep: <String, dynamic>{
            'observation_id': 'card-1',
            'user_can_reject': true,
            'reject_penalty': 'none',
          },
        ),
      );
      expect(card.nextStep?.zeroPenaltyRejectable, isTrue);
    });

    test('契约漂移（penalty 非 none / can_reject 假）→ 不成立，绝不渲染零惩罚宣称',
        () {
      for (final nextStep in <Map<String, dynamic>>[
        {
          'observation_id': 'card-1',
          'user_can_reject': true,
          'reject_penalty': 'photon_-10',
        },
        {
          'observation_id': 'card-1',
          'user_can_reject': false,
          'reject_penalty': 'none',
        },
      ]) {
        final card = EvidenceInsightCardData.fromJson(
          helpedCardJson(nextStep: nextStep),
        );
        expect(card.nextStep?.zeroPenaltyRejectable, isFalse);
      }
    });
  });

  group('V4-U13 回访记录（七态封闭词表）', () {
    test('合法七态如实解析；词表外值 → unknown（不渲染）', () {
      for (final wire in const [
        'no_prior_suggestion',
        'rejected_by_user',
        'related_outcome_observed',
        'acted_awaiting_outcome',
        'awaiting_user',
        'censored_window_closed',
        'censored_user_churned',
      ]) {
        final feed = EvidenceInsightFeedData.fromJson(
          payload(revisit: <String, dynamic>{'relevance': wire}),
        );
        expect(feed.revisit?.relevance.wire, wire);
      }
      final unknown = EvidenceInsightFeedData.fromJson(
        payload(revisit: <String, dynamic>{'relevance': 'template_relevance'}),
      );
      expect(
        unknown.revisit?.relevance,
        EvidenceRevisitRelevance.unknown,
      );
    });

    test('related_outcome_observed 的 proves_relevance 与去重样本数如实透传', () {
      final feed = EvidenceInsightFeedData.fromJson(
        payload(
          revisit: <String, dynamic>{
            'relevance': 'related_outcome_observed',
            'proves_relevance': true,
            'n_outcome_samples_unique': 2,
            'reward_consequence': 'none',
          },
        ),
      );
      expect(feed.revisit?.provesRelevance, isTrue);
      expect(feed.revisit?.nOutcomeSamplesUnique, 2);
      expect(feed.revisit?.rewardConsequence, 'none');
    });
  });
}
