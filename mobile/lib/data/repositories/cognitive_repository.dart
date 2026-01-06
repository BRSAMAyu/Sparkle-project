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
  Future<CognitiveFragmentModel> createFragment(
      CognitiveFragmentCreate data,) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.cognitiveFragments,
        data: data.toJson(),
      );

      final rData = response.data;
      final responseData = rData is Map && rData.containsKey('data')
          ? rData['data']
          : rData;

      return CognitiveFragmentModel.fromJson(
        responseData as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      throw Exception(
          (e.response?.data as Map<String, dynamic>?)?['detail'] ?? 'Failed to create fragment',);
    }
  }

  @override
  Future<List<CognitiveFragmentModel>> getFragments(
      {int limit = 20, int skip = 0,}) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.cognitiveFragments,
        queryParameters: {'limit': limit, 'skip': skip},
      );
      final rData = response.data;
      final list = rData is Map && rData['data'] is List
          ? rData['data'] as List<dynamic>
          : rData as List<dynamic>;
      return list
          .map((e) => CognitiveFragmentModel.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(
        (e.response?.data as Map<String, dynamic>?)?['detail'] ??
            'Failed to get fragments',
      );
    }
  }

  @override
  Future<List<BehaviorPatternModel>> getBehaviorPatterns() async {
    try {
      final response =
          await _apiClient.get<dynamic>(ApiEndpoints.cognitivePatterns);
      final rData = response.data;
      final list = rData is Map && rData['data'] is List
          ? rData['data'] as List<dynamic>
          : rData as List<dynamic>;
      return list
          .map((e) => BehaviorPatternModel.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(
        (e.response?.data as Map<String, dynamic>?)?['detail'] ??
            'Failed to get behavior patterns',
      );
    }
  }
}

final cognitiveRepositoryProvider = Provider<ICognitiveRepository>((ref) {
  // Toggle between Mock and Real API
  // In production, this should be controlled by environment variables or build flags
  const useMock = bool.fromEnvironment('USE_MOCK');

  if (useMock) {
    return MockCognitiveRepository();
  }

  final apiClient = ref.watch(apiClientProvider);
  final apiRepo = ApiCognitiveRepository(apiClient);
  final localRepo = LocalCognitiveRepository();

  return SyncCognitiveRepository(apiRepo, localRepo);
});
