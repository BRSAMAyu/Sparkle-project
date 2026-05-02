import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';

const String kAccessibilitySettingsStorageKey =
    'settings_accessibility_central';
const String kAccessibilitySettingsUserSettingsKey = 'accessibility_settings';

enum TouchTargetSize {
  comfortable('comfortable', 48),
  large('large', 56),
  extraLarge('extra_large', 64);

  const TouchTargetSize(this.storageValue, this.minimumDimension);

  final String storageValue;
  final double minimumDimension;
}

TouchTargetSize normalizeTouchTargetSize(Object? rawValue) {
  final value = rawValue?.toString().trim().toLowerCase();
  return TouchTargetSize.values.firstWhere(
    (candidate) => candidate.storageValue == value,
    orElse: () => TouchTargetSize.comfortable,
  );
}

double normalizeFontScale(Object? rawValue) {
  if (rawValue is num) {
    return rawValue.toDouble().clamp(0.85, 1.4);
  }
  final parsed = double.tryParse(rawValue?.toString() ?? '');
  return (parsed ?? 1.0).clamp(0.85, 1.4);
}

bool _readBool(Object? rawValue, {required bool fallback}) {
  if (rawValue is bool) return rawValue;
  final value = rawValue?.toString().trim().toLowerCase();
  return switch (value) {
    'true' || '1' || 'yes' || 'on' => true,
    'false' || '0' || 'no' || 'off' => false,
    _ => fallback,
  };
}

class AccessibilitySettings {
  const AccessibilitySettings({
    this.fontScale = 1.0,
    this.highContrast = false,
    this.screenReaderOptimized = false,
    this.touchTargetSize = TouchTargetSize.comfortable,
    this.reduceMotion = false,
    this.colorBlindFriendly = false,
    this.ttsEnabled = false,
    this.hapticFeedback = true,
    this.lowLoadMode = false,
    this.isLoaded = false,
    this.isSaving = false,
    this.lastError,
  });

  factory AccessibilitySettings.fromJson(Map<String, dynamic> json) =>
      AccessibilitySettings(
        fontScale: normalizeFontScale(json['font_scale']),
        highContrast: _readBool(json['high_contrast'], fallback: false),
        screenReaderOptimized: _readBool(
          json['screen_reader_optimized'],
          fallback: false,
        ),
        touchTargetSize: normalizeTouchTargetSize(json['touch_target_size']),
        reduceMotion: _readBool(json['reduce_motion'], fallback: false),
        colorBlindFriendly: _readBool(
          json['color_blind_friendly'],
          fallback: false,
        ),
        ttsEnabled: _readBool(json['tts_enabled'], fallback: false),
        hapticFeedback: _readBool(json['haptic_feedback'], fallback: true),
        lowLoadMode: _readBool(json['low_load_mode'], fallback: false),
        isLoaded: true,
      );

  final double fontScale;
  final bool highContrast;
  final bool screenReaderOptimized;
  final TouchTargetSize touchTargetSize;
  final bool reduceMotion;
  final bool colorBlindFriendly;
  final bool ttsEnabled;
  final bool hapticFeedback;
  final bool lowLoadMode;
  final bool isLoaded;
  final bool isSaving;
  final String? lastError;

  Map<String, dynamic> toJson() => {
        'font_scale': double.parse(fontScale.toStringAsFixed(2)),
        'high_contrast': highContrast,
        'screen_reader_optimized': screenReaderOptimized,
        'touch_target_size': touchTargetSize.storageValue,
        'reduce_motion': reduceMotion,
        'color_blind_friendly': colorBlindFriendly,
        'tts_enabled': ttsEnabled,
        'haptic_feedback': hapticFeedback,
        'low_load_mode': lowLoadMode,
      };

  Map<String, dynamic> toUserSettingsPayload() => {
        kAccessibilitySettingsUserSettingsKey: toJson(),
        'haptics_enabled': hapticFeedback,
        'galaxy_accessibility_defaults': {
          'screen_reader_enabled': screenReaderOptimized,
          'reduce_motion': reduceMotion || lowLoadMode,
          'high_contrast': highContrast,
          'haptic_enabled': hapticFeedback,
        },
      };

  double get minimumTouchTargetSize => touchTargetSize.minimumDimension;

  AccessibilitySettings copyWith({
    double? fontScale,
    bool? highContrast,
    bool? screenReaderOptimized,
    TouchTargetSize? touchTargetSize,
    bool? reduceMotion,
    bool? colorBlindFriendly,
    bool? ttsEnabled,
    bool? hapticFeedback,
    bool? lowLoadMode,
    bool? isLoaded,
    bool? isSaving,
    String? lastError,
    bool clearError = false,
  }) =>
      AccessibilitySettings(
        fontScale: fontScale ?? this.fontScale,
        highContrast: highContrast ?? this.highContrast,
        screenReaderOptimized:
            screenReaderOptimized ?? this.screenReaderOptimized,
        touchTargetSize: touchTargetSize ?? this.touchTargetSize,
        reduceMotion: reduceMotion ?? this.reduceMotion,
        colorBlindFriendly: colorBlindFriendly ?? this.colorBlindFriendly,
        ttsEnabled: ttsEnabled ?? this.ttsEnabled,
        hapticFeedback: hapticFeedback ?? this.hapticFeedback,
        lowLoadMode: lowLoadMode ?? this.lowLoadMode,
        isLoaded: isLoaded ?? this.isLoaded,
        isSaving: isSaving ?? this.isSaving,
        lastError: clearError ? null : lastError ?? this.lastError,
      );

  AccessibilitySettings asLowLoadDefaults(bool enabled) {
    if (!enabled) {
      return copyWith(lowLoadMode: false);
    }
    return copyWith(
      lowLoadMode: true,
      reduceMotion: true,
      screenReaderOptimized: true,
      touchTargetSize: TouchTargetSize.large,
      fontScale: fontScale < 1.1 ? 1.1 : fontScale,
    );
  }
}

final accessibilitySettingsProvider =
    StateNotifierProvider<AccessibilitySettingsNotifier, AccessibilitySettings>(
  AccessibilitySettingsNotifier.new,
);

class AccessibilitySettingsNotifier
    extends StateNotifier<AccessibilitySettings> {
  AccessibilitySettingsNotifier(this._ref)
      : super(const AccessibilitySettings()) {
    unawaited(load());
  }

  final Ref _ref;

  Future<void> load() async {
    state = state.copyWith(clearError: true);
    await _loadLocalSettings();
    await _syncFromServer();
    state = state.copyWith(isLoaded: true);
  }

  Future<void> update(AccessibilitySettings nextSettings) async {
    final previous = state;
    final sanitized = nextSettings.copyWith(
      fontScale: normalizeFontScale(nextSettings.fontScale),
      isLoaded: true,
      isSaving: true,
      clearError: true,
    );
    state = sanitized;
    try {
      await _persistLocal(sanitized);
      await _syncToServer(sanitized);
      state = sanitized.copyWith(isSaving: false);
    } catch (error) {
      state = previous.copyWith(
        isSaving: false,
        lastError: error.toString(),
      );
      rethrow;
    }
  }

  Future<void> patch({
    double? fontScale,
    bool? highContrast,
    bool? screenReaderOptimized,
    TouchTargetSize? touchTargetSize,
    bool? reduceMotion,
    bool? colorBlindFriendly,
    bool? ttsEnabled,
    bool? hapticFeedback,
    bool? lowLoadMode,
  }) {
    final next = state.copyWith(
      fontScale: fontScale,
      highContrast: highContrast,
      screenReaderOptimized: screenReaderOptimized,
      touchTargetSize: touchTargetSize,
      reduceMotion: reduceMotion,
      colorBlindFriendly: colorBlindFriendly,
      ttsEnabled: ttsEnabled,
      hapticFeedback: hapticFeedback,
      lowLoadMode: lowLoadMode,
    );
    return update(next);
  }

  Future<void> setLowLoadMode(bool enabled) =>
      update(state.asLowLoadDefaults(enabled));

  Future<void> reset() => update(const AccessibilitySettings(isLoaded: true));

  Future<void> _loadLocalSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(kAccessibilitySettingsStorageKey);
      if (raw == null || raw.isEmpty) return;
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        state = AccessibilitySettings.fromJson(decoded);
      }
    } catch (_) {
      state = const AccessibilitySettings(isLoaded: true);
    }
  }

  Future<void> _persistLocal(AccessibilitySettings settings) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      kAccessibilitySettingsStorageKey,
      jsonEncode(settings.toJson()),
    );
  }

  Future<void> _syncFromServer() async {
    try {
      final settings =
          await _ref.read(userRepositoryProvider).fetchUserSettings();
      final rawAccessibility = settings[kAccessibilitySettingsUserSettingsKey];
      final parsed = _parseServerAccessibilitySettings(rawAccessibility);
      if (parsed != null) {
        state = parsed;
        await _persistLocal(parsed);
        return;
      }
      await _syncToServer(state.copyWith(isLoaded: true));
    } catch (_) {
      // Local settings are still usable offline and before backend rollout.
    }
  }

  AccessibilitySettings? _parseServerAccessibilitySettings(Object? rawValue) {
    if (rawValue is Map<String, dynamic>) {
      return AccessibilitySettings.fromJson(rawValue);
    }
    if (rawValue is Map) {
      return AccessibilitySettings.fromJson(
        rawValue.map((key, value) => MapEntry(key.toString(), value)),
      );
    }
    if (rawValue is String && rawValue.trim().isNotEmpty) {
      final decoded = jsonDecode(rawValue);
      if (decoded is Map<String, dynamic>) {
        return AccessibilitySettings.fromJson(decoded);
      }
    }
    return null;
  }

  Future<void> _syncToServer(AccessibilitySettings settings) async {
    try {
      await _ref
          .read(userRepositoryProvider)
          .updateUserSettings(settings.toUserSettingsPayload());
    } catch (_) {
      // Offline and signed-out users keep the local defaults; the next load
      // attempts account sync again once repository calls are available.
    }
  }
}
