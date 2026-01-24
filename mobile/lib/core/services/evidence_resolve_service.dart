import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/network/api_client.dart';

class EvidenceResolveService {
  EvidenceResolveService(this._apiClient);

  final ApiClient _apiClient;

  Future<List<EvidenceResolveItem>> resolveEvidence(
    List<EvidenceRefModel> refs,
  ) async {
    if (refs.isEmpty) {
      return [];
    }
    final payload = {
      'items': refs.map((ref) => ref.toJson()).toList(),
    };
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/api/v1/events/evidence/resolve',
      data: payload,
    );
    final items = (response.data?['resolved'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(EvidenceResolveItem.fromJson)
        .toList();
    return items;
  }
}

final evidenceResolveServiceProvider = Provider<EvidenceResolveService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return EvidenceResolveService(apiClient);
});
