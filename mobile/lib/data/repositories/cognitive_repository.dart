import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/behavior_pattern_model.dart';
import 'package:sparkle/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/data/repositories/mock_cognitive_repository.dart';

class CognitiveRepository {

  // Modified constructor to allow null ApiClient for mock subclasses if needed,
  // though MockCognitiveRepository doesn't call super with arguments if it implements the interface.
  // Actually, since we are using 'implements' in MockCognitiveRepository, we don't strictly need to change the class definition here
  // unless we want to make _apiClient nullable.
  // However, the cleanest way to support the mock which implements the interface 
  // (implicit interface of this class) is to just change the provider.
  
  CognitiveRepository(this._apiClient);
  final ApiClient? _apiClient;

  Future<CognitiveFragmentModel> createFragment(CognitiveFragmentCreate data) async {
    try {
      final response = await _apiClient!.post(
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

  Future<List<CognitiveFragmentModel>> getFragments({int limit = 20, int skip = 0}) async {
    try {
      final response = await _apiClient!.get(
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

  Future<List<BehaviorPatternModel>> getBehaviorPatterns() async {
    try {
      final response = await _apiClient!.get(ApiEndpoints.cognitivePatterns);
      final List<dynamic> list = response.data is Map && response.data.containsKey('data') 
          ? response.data['data'] 
          : response.data;
      return list.map((e) => BehaviorPatternModel.fromJson(e)).toList();
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to get behavior patterns');
    }
  }
}

final cognitiveRepositoryProvider = Provider<CognitiveRepository>((ref) {
  // Demo Mode: Use Mock Repository
  return MockCognitiveRepository();
  
  // Real Implementation:
  // final apiClient = ref.watch(apiClientProvider);
  // return CognitiveRepository(apiClient);
});
