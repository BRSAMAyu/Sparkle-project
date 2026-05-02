import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/goal/data/models/goal_creation_models.dart';

final goalRepositoryProvider = Provider<GoalRepository>(
  (ref) => ApiGoalRepository(ref.read(apiClientProvider)),
);

abstract class GoalRepository {
  Future<GoalDecompositionPreview> decomposePreview({
    required String goalType,
    required String title,
    required String motivation,
    required String timeHorizon,
  });

  Future<CreatedGoal> createGoal({
    required String goalType,
    required String title,
    required String motivation,
    required String timeHorizon,
    required List<GoalMilestoneDraft> milestones,
    String? description,
  });
}

class ApiGoalRepository implements GoalRepository {
  const ApiGoalRepository(this._apiClient);

  final ApiClient _apiClient;

  @override
  Future<GoalDecompositionPreview> decomposePreview({
    required String goalType,
    required String title,
    required String motivation,
    required String timeHorizon,
  }) async {
    final response = await _apiClient.post<dynamic>(
      '/goals/decompose-preview',
      data: {
        'goal_type': goalType,
        'title': title,
        'motivation': motivation,
        'time_horizon': timeHorizon,
      },
    );
    return GoalDecompositionPreview.fromJson(_asMap(response.data));
  }

  @override
  Future<CreatedGoal> createGoal({
    required String goalType,
    required String title,
    required String motivation,
    required String timeHorizon,
    required List<GoalMilestoneDraft> milestones,
    String? description,
  }) async {
    final response = await _apiClient.post<dynamic>(
      '/goals',
      data: {
        'goal_type': goalType,
        'title': title,
        'motivation': motivation,
        'time_horizon': timeHorizon,
        'description': description,
        'milestones': [for (final milestone in milestones) milestone.toJson()],
      },
    );
    return CreatedGoal.fromJson(_asMap(response.data));
  }
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return const {};
}
