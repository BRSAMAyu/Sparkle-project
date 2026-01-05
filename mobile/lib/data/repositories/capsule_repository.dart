import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/data/models/curiosity_capsule_model.dart';

class CapsuleRepository {
  CapsuleRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<List<CuriosityCapsuleModel>> getTodayCapsules() async {
    final response = await _apiClient.get('/capsules/today');
    return (response.data as List)
        .map((e) => CuriosityCapsuleModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> markAsRead(String id) async {
    await _apiClient.post('/capsules/$id/read');
  }
}

final capsuleRepositoryProvider = Provider<CapsuleRepository>(
    (ref) => CapsuleRepository(ref.watch(apiClientProvider)),);
