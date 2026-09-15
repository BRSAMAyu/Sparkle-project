import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/cognitive/data/models/strategy_migration_models.dart';

final strategyMigrationRepositoryProvider =
    Provider<StrategyMigrationRepository>(
  (ref) => ApiStrategyMigrationRepository(ref.read(apiClientProvider)),
);

final alternativeStrategiesProvider =
    FutureProvider.family<StrategySuggestionBundle, String>((ref, goalId) {
  return ref
      .read(strategyMigrationRepositoryProvider)
      .fetchAlternatives(goalId: goalId);
});

abstract class StrategyMigrationRepository {
  Future<StrategySuggestionBundle> fetchAlternatives({required String goalId});

  Future<StrategyMigrationResult> migrateStrategy({
    required String goalId,
    required String newStrategyId,
  });
}

class ApiStrategyMigrationRepository implements StrategyMigrationRepository {
  const ApiStrategyMigrationRepository(this._apiClient);

  final ApiClient _apiClient;

  @override
  Future<StrategySuggestionBundle> fetchAlternatives({
    required String goalId,
  }) async {
    final response = await _apiClient.get<dynamic>(
      '/cognitive/alternative-strategies',
      queryParameters: {'goal_id': goalId},
    );
    return StrategySuggestionBundle.fromJson(_asMap(response.data));
  }

  @override
  Future<StrategyMigrationResult> migrateStrategy({
    required String goalId,
    required String newStrategyId,
  }) async {
    final response = await _apiClient.post<dynamic>(
      '/cognitive/strategies/migrate',
      data: {
        'goal_id': goalId,
        'new_strategy_id': newStrategyId,
      },
    );
    return StrategyMigrationResult.fromJson(_asMap(response.data));
  }
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return const {};
}
