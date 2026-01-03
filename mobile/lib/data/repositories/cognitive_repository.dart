import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/behavior_pattern_model.dart';
import 'package:sparkle/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/data/repositories/i_cognitive_repository.dart';
import 'package:sparkle/data/repositories/local_cognitive_repository.dart';
import 'package:sparkle/data/repositories/mock_cognitive_repository.dart';
import 'package:sparkle/data/repositories/sync_cognitive_repository.dart';

class ApiCognitiveRepository implements ICognitiveRepository {
  ApiCognitiveRepository(this._apiClient);
  
  final ApiClient _apiClient;

  @override
  Future<CognitiveFragmentModel> createFragment(CognitiveFragmentCreate data) async {
    try {
      final response = await _apiClient.post(
        ApiEndpoints.cognitiveFragments,
        data: data.toJson(),
      );
      
      final responseData = response.data is Map && response.data.containsKey('data') 
          ? response.data['data'] 
          : response.data;
          
      return CognitiveFragmentModel.fromJson(responseData);
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to create fragment');
    }
  }

  @override
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

  @override
  Future<List<BehaviorPatternModel>> getBehaviorPatterns() async {
    try {
      final response = await _apiClient.get(ApiEndpoints.cognitivePatterns);
      final List<dynamic> list = response.data is Map && response.data.containsKey('data') 
          ? response.data['data'] 
          : response.data;
      return list.map((e) => BehaviorPatternModel.fromJson(e)).toList();
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to get behavior patterns');
    }
  }
}

final cognitiveRepositoryProvider = Provider<ICognitiveRepository>((ref) {
  // Toggle between Mock and Real API
  // In production, this should be controlled by environment variables or build flags
  const useMock = false; 
  
  if (useMock) {
    return MockCognitiveRepository();
  }

  final apiClient = ref.watch(apiClientProvider);
  final apiRepo = ApiCognitiveRepository(apiClient);
  final localRepo = LocalCognitiveRepository();
  
  return SyncCognitiveRepository(apiRepo, localRepo);
});
