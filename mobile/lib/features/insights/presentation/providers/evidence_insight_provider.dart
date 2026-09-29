import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/insights/data/models/evidence_insight_card.dart';
import 'package:sparkle/features/insights/data/repositories/evidence_insight_repository.dart';

/// D-07 证据洞察 feed：每次进入洞察总览时从 `/insights/evidence-cards`
/// 现取（后端每次请求现算，纠正落库后重进即更新）。
///
/// V4-U13：消费 D05 `insight.presentation.v1` 契约出口——feed 自带版本门
/// （unsupported）、无数据显式态（no_data）与夸大门扣下登记，三态互斥、
/// 诚实呈现；error/offline 由 AsyncValue 自身承载。
final evidenceInsightFeedProvider =
    FutureProvider.autoDispose<EvidenceInsightFeedData>((ref) async {
  final repository = ref.watch(evidenceInsightRepositoryProvider);
  return repository.getEvidenceFeed();
});
