import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/insights/data/models/evidence_insight_card.dart';

final evidenceInsightRepositoryProvider = Provider<EvidenceInsightRepository>((
  ref,
) {
  final apiClient = ref.watch(apiClientProvider);
  return EvidenceInsightRepository(apiClient);
});

/// D-07 证据洞察 feed 仓库：只读消费 `/insights/evidence-cards`
/// （五要素卡 v1 + D05 `insight.presentation.v1` 呈现契约出口）。
/// 诚实抛错，无 mock fallback；版本门在 [EvidenceInsightFeedData.fromJson]
/// fail-closed（旧契约 → unsupported，不伪造契约字段）。
class EvidenceInsightRepository {
  EvidenceInsightRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<EvidenceInsightFeedData> getEvidenceFeed() async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.insightsEvidenceCards,
      );
      // 服务返回 {data: payload, meta: meta} 双层（meta 携带夸大门登记/空态
      // note）；unwrapMap 只回 data 会丢 meta，故这里显式拆双层。
      final raw = response.data;
      if (raw is! Map) {
        throw Exception('getEvidenceFeed response is not a map');
      }
      final envelope = Map<String, dynamic>.from(raw);
      final payload = envelope['data'] is Map
          ? Map<String, dynamic>.from(envelope['data'] as Map)
          : const <String, dynamic>{};
      final meta = envelope['meta'] is Map
          ? Map<String, dynamic>.from(envelope['meta'] as Map)
          : const <String, dynamic>{};
      return EvidenceInsightFeedData.fromJson(payload, meta: meta);
    } on DioException catch (e) {
      throw Exception(_extractDioMessage(e, 'Failed to load evidence insights'));
    } catch (_) {
      throw Exception('An unexpected error occurred');
    }
  }

  String _extractDioMessage(DioException error, String fallbackMessage) {
    final data = error.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) {
        return detail;
      }
      final message = data['message'];
      if (message is String && message.isNotEmpty) {
        return message;
      }
    }
    return fallbackMessage;
  }
}
