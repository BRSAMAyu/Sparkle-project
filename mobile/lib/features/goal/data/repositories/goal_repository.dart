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

  Future<void> updateGoal({
    required String goalId,
    String? title,
    String? description,
  });
}

class ApiGoalRepository implements GoalRepository {
  const ApiGoalRepository(this._apiClient);

  final ApiClient _apiClient;

  /// Flutter UI types → backend goal_type values.
  /// Flutter shows user-facing labels (academic, skill, habit, project, other)
  /// but the backend expects (exam, job_search, fitness, project, general).
  static const _typeMap = <String, String>{
    'academic': 'exam',
    'skill': 'job_search',
    'habit': 'fitness',
    'project': 'project',
    'other': 'general',
    // Backend types pass through unchanged.
    'exam': 'exam',
    'job_search': 'job_search',
    'fitness': 'fitness',
    'general': 'general',
    'startup': 'startup',
  };

  static String resolveType(String goalType) =>
      _typeMap[goalType] ?? 'general';

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
        'goal_type': resolveType(goalType),
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
        'goal_type': resolveType(goalType),
        'title': title,
        'motivation': motivation,
        'time_horizon': timeHorizon,
        'description': description,
        'milestones': [for (final milestone in milestones) milestone.toJson()],
      },
    );
    return CreatedGoal.fromJson(_asMap(response.data));
  }

  @override
  Future<void> updateGoal({
    required String goalId,
    String? title,
    String? description,
    String? targetDate,
  }) async {
    final data = <String, dynamic>{};
    if (title != null) data['title'] = title;
    if (description != null) data['description'] = description;
    if (targetDate != null) data['target_date'] = targetDate;
    await _apiClient.put<dynamic>(
      '/goals/$goalId',
      data: data,
    );
  }
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return const {};
}
