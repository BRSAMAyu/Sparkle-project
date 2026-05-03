import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/experience/data/experience_models.dart';

final experienceRepositoryProvider = Provider<ExperienceRepository>((ref) {
  return ExperienceRepository(ref.watch(apiClientProvider));
});

class ExperienceRepository {
  ExperienceRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<UnderstandingSnapshot> getUnderstandingSnapshot({
    String? conversationId,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.experienceUnderstandingSnapshot,
      queryParameters: {
        if (conversationId != null && conversationId.trim().isNotEmpty)
          'conversation_id': conversationId.trim(),
      },
    );
    return UnderstandingSnapshot.fromJson(_payload(response.data));
  }

  Future<GoalDetailSnapshot> getGoalDetail({String goalId = 'current'}) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.experienceGoalDetail(goalId),
    );
    return GoalDetailSnapshot.fromJson(_payload(response.data));
  }

  Future<ExperienceGrowthDashboard> getGrowthDashboard() async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.experienceGrowthDashboard,
    );
    return ExperienceGrowthDashboard.fromJson(_payload(response.data));
  }

  Future<CommunityAccountabilitySnapshot> getCommunityAccountability() async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.experienceCommunityAccountability,
    );
    return CommunityAccountabilitySnapshot.fromJson(_payload(response.data));
  }

  Map<String, dynamic> _payload(Object? data) {
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw FormatException(
      'experience: expected Map response, got ${data.runtimeType}',
    );
  }
}
