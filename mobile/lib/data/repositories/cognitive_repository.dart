import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/cognitive_fragment_model.dart';

class CognitiveRepository {
  final ApiClient _apiClient;

  CognitiveRepository(this._apiClient);

  Future<CognitiveFragmentModel> createFragment(CognitiveFragmentCreate data) async {
    try {
      final response = await _apiClient.post(
        ApiEndpoints.cognitiveFragments,
        data: data.toJson(),
      );
      // Depending on backend response structure (wrapped in data or not)
      // Standardize: If backend returns model directly or {data: model}
      // My backend code returns CognitiveFragmentResponse directly (Pydantic model)
      // But previous repos check for 'data'.
      // Backend: @router.post("/fragments", response_model=CognitiveFragmentResponse)
      // FastAPI usually returns JSON directly.
      // However, check existing API Client or Interceptor if they wrap response.
      // TaskRepository checks: response.data is Map && response.data.containsKey('data')
      
      final responseData = response.data is Map && response.data.containsKey('data') 
          ? response.data['data'] 
          : response.data;
          
      return CognitiveFragmentModel.fromJson(responseData);
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to create fragment');
    }
  }

  Future<List<CognitiveFragmentModel>> getFragments({int limit = 20, int skip = 0}) async {
    try {
      final response = await _apiClient.get(
        ApiEndpoints.cognitiveFragments,
        queryParameters: {'limit': limit, 'skip': skip},
      );
      final List<dynamic> list = response.data is Map && response.data.containsKey('data') 
          ? response.data['data'] 
          : response.data;
      return list.map((e) => CognitiveFragmentModel.fromJson(e)).toList();
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to get fragments');
    }
  }
}

final cognitiveRepositoryProvider = Provider<CognitiveRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CognitiveRepository(apiClient);
});
