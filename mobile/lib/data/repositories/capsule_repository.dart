import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/data/models/curiosity_capsule_model.dart';

class CapsuleRepository {
  final ApiClient _apiClient;

  CapsuleRepository(this._apiClient);

  Future<List<CuriosityCapsuleModel>> getTodayCapsules() async {
    final response = await _apiClient.get('/capsules/today');
    return (response.data as List).map((e) => CuriosityCapsuleModel.fromJson(e)).toList();
  }

  Future<void> markAsRead(String id) async {
    await _apiClient.post('/capsules/$id/read');
  }
}

final capsuleRepositoryProvider = Provider<CapsuleRepository>((ref) {
  return CapsuleRepository(ref.watch(apiClientProvider));
});
