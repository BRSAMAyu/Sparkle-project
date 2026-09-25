import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/insights/data/models/evidence_insight_card.dart';

final evidenceInsightRepositoryProvider = Provider<EvidenceInsightRepository>((
  ref,
) {
  final apiClient = ref.watch(apiClientProvider);
  return EvidenceInsightRepository(apiClient);
});

/// D-07 证据洞察卡仓库：只读消费 `/insights/evidence-cards`
/// （insights.evidence_cards.v1）。诚实抛错，无 mock fallback。
class EvidenceInsightRepository {
  EvidenceInsightRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<EvidenceInsightCardData>> getEvidenceCards() async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.insightsEvidenceCards,
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getEvidenceCards',
      );
      final windowDays =
          payload['window_days'] is num ? (payload['window_days'] as num).toInt() : 30;
      final cards = (payload['cards'] as List?) ?? const <dynamic>[];
      return cards.whereType<Map<dynamic, dynamic>>().map((item) {
        final json = Map<String, dynamic>.from(item);
        json['window_days'] = windowDays;
        return EvidenceInsightCardData.fromJson(json);
      }).toList(growable: false);
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
