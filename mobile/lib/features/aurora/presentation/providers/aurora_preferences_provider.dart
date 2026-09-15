import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

/// Core keepAlive provider: preferences are small user-scoped state and should
/// remain cached across tab switches.
final auroraPreferencesProvider =
    AsyncNotifierProvider<AuroraPreferencesNotifier, AuroraPreferences>(
  AuroraPreferencesNotifier.new,
);

class AuroraPreferences {
  const AuroraPreferences({
    this.analysisDepth = 'deep',
    this.directness = 'guided',
    this.explanationLevel = 'detailed',
    this.pressureStyle = 'motivating',
  });

  final String analysisDepth;
  final String directness;
  final String explanationLevel;
  final String pressureStyle;

  factory AuroraPreferences.fromJson(Map<String, dynamic> json) {
    return AuroraPreferences(
      analysisDepth: json['aurora_analysis_depth'] as String? ?? 'deep',
      directness: json['aurora_directness'] as String? ?? 'guided',
      explanationLevel:
          json['aurora_explanation_level'] as String? ?? 'detailed',
      pressureStyle: json['aurora_pressure_style'] as String? ?? 'motivating',
    );
  }

  Map<String, String> toUpdateMap(Set<String> keys) {
    final map = <String, String>{};
    if (keys.contains('aurora_analysis_depth')) {
      map['aurora_analysis_depth'] = analysisDepth;
    }
    if (keys.contains('aurora_directness')) {
      map['aurora_directness'] = directness;
    }
    if (keys.contains('aurora_explanation_level')) {
      map['aurora_explanation_level'] = explanationLevel;
    }
    if (keys.contains('aurora_pressure_style')) {
      map['aurora_pressure_style'] = pressureStyle;
    }
    return map;
  }
}

class AuroraPreferencesNotifier extends AsyncNotifier<AuroraPreferences> {
  @override
  Future<AuroraPreferences> build() async {
    final apiClient = ref.read(apiClientProvider);
    try {
      final response = await apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.auroraPreferences,
      );
      final data = response.data;
      if (data == null) return const AuroraPreferences();
      final prefs = data['preferences'] as Map<String, dynamic>? ?? {};
      return AuroraPreferences.fromJson(prefs);
    } catch (_) {
      return const AuroraPreferences();
    }
  }

  Future<void> updatePreference(String key, String value) async {
    final current = state.valueOrNull ?? const AuroraPreferences();
    final updated = _applyChange(current, key, value);
    state = AsyncData(updated);

    final apiClient = ref.read(apiClientProvider);
    try {
      await apiClient.put<Map<String, dynamic>>(
        ApiEndpoints.auroraPreferences,
        data: {key: value},
      );
    } catch (_) {
      state = AsyncData(current);
      rethrow;
    }
  }

  AuroraPreferences _applyChange(
    AuroraPreferences current,
    String key,
    String value,
  ) {
    switch (key) {
      case 'aurora_analysis_depth':
        return AuroraPreferences(
          analysisDepth: value,
          directness: current.directness,
          explanationLevel: current.explanationLevel,
          pressureStyle: current.pressureStyle,
        );
      case 'aurora_directness':
        return AuroraPreferences(
          analysisDepth: current.analysisDepth,
          directness: value,
          explanationLevel: current.explanationLevel,
          pressureStyle: current.pressureStyle,
        );
      case 'aurora_explanation_level':
        return AuroraPreferences(
          analysisDepth: current.analysisDepth,
          directness: current.directness,
          explanationLevel: value,
          pressureStyle: current.pressureStyle,
        );
      case 'aurora_pressure_style':
        return AuroraPreferences(
          analysisDepth: current.analysisDepth,
          directness: current.directness,
          explanationLevel: current.explanationLevel,
          pressureStyle: value,
        );
      default:
        return current;
    }
  }
}
