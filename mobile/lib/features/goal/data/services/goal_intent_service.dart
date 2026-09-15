import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/goal/data/models/goal_intent_models.dart';

/// Phase-1 Entry Wire — calls the FME `/goals/analyze-intent` endpoint.
///
/// Lives in its own service rather than extending [GoalRepository] so the
/// existing repository contract stays untouched and this feature can be
/// removed cleanly if rolled back.
///
/// Always returns a non-null [GoalIntentAnalysis]. On any transport or
/// parse error we return [GoalIntentAnalysis.disabled] so the wizard can
/// silently fall back to the legacy 5-step flow — same shape the server
/// returns when the kill switch is off/shadow.
class GoalIntentService {
  const GoalIntentService(this._apiClient);

  final ApiClient _apiClient;

  Future<GoalIntentAnalysis> analyze(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return GoalIntentAnalysis.disabled();
    try {
      final response = await _apiClient.post<dynamic>(
        '/goals/analyze-intent',
        data: {'text': trimmed},
      );
      final data = response.data;
      if (data is Map) {
        return GoalIntentAnalysis.fromJson(Map<String, dynamic>.from(data));
      }
      return GoalIntentAnalysis.disabled();
    } catch (_) {
      // Network/parse failure must not block the wizard — fall back to legacy.
      return GoalIntentAnalysis.disabled();
    }
  }
}

final goalIntentServiceProvider = Provider<GoalIntentService>(
  (ref) => GoalIntentService(ref.read(apiClientProvider)),
);
