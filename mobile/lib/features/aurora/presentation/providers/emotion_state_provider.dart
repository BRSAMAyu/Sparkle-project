import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';

const String kEmotionAdaptiveModeKey = 'settings_emotion_adaptive_mode';

enum EmotionAdaptiveMode {
  auto,
  alwaysLow,
  alwaysNormal;

  String get storageValue => switch (this) {
        EmotionAdaptiveMode.auto => 'auto',
        EmotionAdaptiveMode.alwaysLow => 'always_low',
        EmotionAdaptiveMode.alwaysNormal => 'always_normal',
      };

  static EmotionAdaptiveMode fromStorageValue(Object? raw) {
    switch (raw?.toString().trim().toLowerCase()) {
      case 'always_low':
      case 'low':
      case 'low_stimulus':
        return EmotionAdaptiveMode.alwaysLow;
      case 'always_normal':
      case 'normal':
        return EmotionAdaptiveMode.alwaysNormal;
      case 'auto':
      default:
        return EmotionAdaptiveMode.auto;
    }
  }
}

@immutable
class EmotionState {
  const EmotionState({
    this.emotion,
    this.fatigueLevel = 0,
    this.cognitiveLoad = 0,
    this.stressSignal = 0,
    this.mode = EmotionAdaptiveMode.auto,
    this.updatedAt,
    this.source = 'local',
  });

  final String? emotion;
  final double fatigueLevel;
  final double cognitiveLoad;
  final double stressSignal;
  final EmotionAdaptiveMode mode;
  final DateTime? updatedAt;
  final String source;

  EmotionResponsiveConfig get responsiveConfig {
    final intensity = _resolvedIntensity;
    return intensity.isLowStimulus
        ? const EmotionResponsiveConfig.lowStimulus()
        : const EmotionResponsiveConfig.normal();
  }

  EmotionAdaptiveIntensity get _resolvedIntensity {
    switch (mode) {
      case EmotionAdaptiveMode.alwaysLow:
        return EmotionAdaptiveIntensity.lowStimulus;
      case EmotionAdaptiveMode.alwaysNormal:
        return EmotionAdaptiveIntensity.normal;
      case EmotionAdaptiveMode.auto:
        return _autoIntensity;
    }
  }

  EmotionAdaptiveIntensity get _autoIntensity {
    final normalizedEmotion = emotion?.trim().toLowerCase();
    final explicitLowStimulusEmotion = normalizedEmotion == 'fatigued' ||
        normalizedEmotion == 'tired' ||
        normalizedEmotion == 'overwhelmed' ||
        normalizedEmotion == 'stressed' ||
        normalizedEmotion == 'anxious';
    if (explicitLowStimulusEmotion ||
        fatigueLevel >= 0.62 ||
        cognitiveLoad >= 0.72 ||
        stressSignal >= 0.58) {
      return EmotionAdaptiveIntensity.lowStimulus;
    }
    return EmotionAdaptiveIntensity.normal;
  }

  EmotionState copyWith({
    String? emotion,
    double? fatigueLevel,
    double? cognitiveLoad,
    double? stressSignal,
    EmotionAdaptiveMode? mode,
    DateTime? updatedAt,
    String? source,
  }) =>
      EmotionState(
        emotion: emotion ?? this.emotion,
        fatigueLevel: fatigueLevel ?? this.fatigueLevel,
        cognitiveLoad: cognitiveLoad ?? this.cognitiveLoad,
        stressSignal: stressSignal ?? this.stressSignal,
        mode: mode ?? this.mode,
        updatedAt: updatedAt ?? this.updatedAt,
        source: source ?? this.source,
      );

  static EmotionState fromAuroraStateBandJson(
    Map<String, dynamic> json, {
    EmotionAdaptiveMode mode = EmotionAdaptiveMode.auto,
  }) {
    final payload = _payloadFrom(json);
    return EmotionState(
      emotion: _stringValue(payload, const ['emotion', 'emotion_state']),
      fatigueLevel: _signalValue(payload, const [
        'fatigue_level',
        'fatigueLevel',
        'fatigue',
      ]),
      cognitiveLoad: _signalValue(payload, const [
        'cognitive_load',
        'cognitiveLoad',
        'load',
      ]),
      stressSignal: _signalValue(payload, const [
        'stress_signal',
        'stressSignal',
        'stress',
      ]),
      mode: mode,
      updatedAt: DateTime.now(),
      source: 'aurora_state_band',
    );
  }

  static Map<String, dynamic> _payloadFrom(Map<String, dynamic> json) {
    final nested = json['payload'] ?? json['data'] ?? json['state'];
    if (nested is Map<String, dynamic>) {
      return nested;
    }
    if (nested is Map) {
      return Map<String, dynamic>.from(nested);
    }
    return json;
  }

  static String? _stringValue(Map<String, dynamic> json, List<String> keys) {
    for (final key in keys) {
      final value = json[key]?.toString().trim();
      if (value != null && value.isNotEmpty) {
        return value;
      }
    }
    return null;
  }

  static double _signalValue(Map<String, dynamic> json, List<String> keys) {
    for (final key in keys) {
      final parsed = _parseSignal(json[key]);
      if (parsed != null) {
        return parsed;
      }
    }
    return 0;
  }

  static double? _parseSignal(Object? raw) {
    if (raw == null) return null;
    if (raw is num) {
      final value = raw.toDouble();
      return value > 1 ? (value / 100).clamp(0, 1) : value.clamp(0, 1);
    }
    final normalized = raw.toString().trim().toLowerCase();
    switch (normalized) {
      case 'none':
      case 'low':
      case 'l0':
        return 0.2;
      case 'medium':
      case 'moderate':
      case 'l1':
        return 0.5;
      case 'high':
      case 'l2':
        return 0.75;
      case 'critical':
      case 'severe':
      case 'l3':
        return 0.95;
      default:
        final value = double.tryParse(normalized);
        if (value == null) return null;
        return value > 1 ? (value / 100).clamp(0, 1) : value.clamp(0, 1);
    }
  }
}

class EmotionStateNotifier extends StateNotifier<EmotionState> {
  EmotionStateNotifier({ApiClient? apiClient}) : super(const EmotionState()) {
    _apiClient = apiClient;
    unawaited(_loadMode());
  }

  ApiClient? _apiClient;

  Future<void> _loadMode() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      state = state.copyWith(
        mode: EmotionAdaptiveMode.fromStorageValue(
          prefs.getString(kEmotionAdaptiveModeKey),
        ),
      );
    } catch (error) {
      debugPrint('EmotionStateNotifier failed to load mode: $error');
    }
  }

  Future<void> setMode(EmotionAdaptiveMode mode) async {
    state = state.copyWith(mode: mode);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(kEmotionAdaptiveModeKey, mode.storageValue);
    } catch (error) {
      debugPrint('EmotionStateNotifier failed to persist mode: $error');
    }
    // A-07: 显式档位同步到引擎（aurora_stimulation_mode）。用户 explicit
    // setting 是最高权威——引擎侧主动面（如 comeback nudge 推送）据此衰减。
    // fire-and-forget：本地档位已生效，引擎侧失败不打扰用户。
    unawaited(_syncStimulationModeToEngine(mode));
  }

  /// explicit 档位 → 引擎偏好值（auto 保持引擎侧现状行为）。
  String _engineStimulationValue(EmotionAdaptiveMode mode) => switch (mode) {
        EmotionAdaptiveMode.alwaysLow => 'low',
        EmotionAdaptiveMode.alwaysNormal => 'standard',
        EmotionAdaptiveMode.auto => 'auto',
      };

  Future<void> _syncStimulationModeToEngine(EmotionAdaptiveMode mode) async {
    final client = _apiClient;
    if (client == null || DemoDataService.isDemoMode) {
      return;
    }
    try {
      await client.put<Map<String, dynamic>>(
        ApiEndpoints.auroraPreferences,
        data: <String, String>{
          'aurora_stimulation_mode': _engineStimulationValue(mode),
        },
      );
    } catch (error) {
      debugPrint(
        'EmotionStateNotifier failed to sync stimulation mode: $error',
      );
    }
  }

  void updateFromAuroraStateBand(Map<String, dynamic> json) {
    state = EmotionState.fromAuroraStateBandJson(
      json,
      mode: state.mode,
    );
  }
}

final emotionStateProvider =
    StateNotifierProvider<EmotionStateNotifier, EmotionState>(
  (ref) => EmotionStateNotifier(apiClient: ref.read(apiClientProvider)),
);

final emotionResponsiveConfigProvider = Provider<EmotionResponsiveConfig>(
  (ref) => ref.watch(emotionStateProvider).responsiveConfig,
);
