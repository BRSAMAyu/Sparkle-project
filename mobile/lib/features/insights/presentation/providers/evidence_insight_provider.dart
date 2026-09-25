import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/insights/data/models/evidence_insight_card.dart';
import 'package:sparkle/features/insights/data/repositories/evidence_insight_repository.dart';

/// D-07 证据洞察卡：每次进入洞察总览时从 `/insights/evidence-cards`
/// 现取（后端每次请求现算，纠正落库后重进即更新）。
final evidenceInsightCardsProvider =
    FutureProvider.autoDispose<List<EvidenceInsightCardData>>((ref) async {
  final repository = ref.watch(evidenceInsightRepositoryProvider);
  return repository.getEvidenceCards();
});
