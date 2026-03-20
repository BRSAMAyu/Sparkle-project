import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum SensoryFeedbackEvent {
  tap,
  selection,
  sheetOpen,
  dialogOpen,
  confirm,
  success,
  warning,
  error,
  toggle,
  navigation,
}

class SensoryFeedbackService {
  SensoryFeedbackService._();

  static const _soundEnabledKey = 'sensory_feedback.sound_enabled';
  static const _hapticEnabledKey = 'sensory_feedback.haptic_enabled';
  static const _assetPrefix = 'audio/ui/';

  static SharedPreferences? _prefs;
  static final Map<SensoryFeedbackEvent, DateTime> _lastEmission = {};

  static Future<SharedPreferences> _preferences() async {
    final prefs = _prefs;
    if (prefs != null) return prefs;
    final loaded = await SharedPreferences.getInstance();
    _prefs = loaded;
    return loaded;
  }

  static Future<bool> isSoundEnabled() async {
    final prefs = await _preferences();
    return prefs.getBool(_soundEnabledKey) ?? true;
  }

  static Future<bool> isHapticEnabled() async {
    final prefs = await _preferences();
    return prefs.getBool(_hapticEnabledKey) ?? true;
  }

  static Future<void> setSoundEnabled(bool enabled) async {
    final prefs = await _preferences();
    await prefs.setBool(_soundEnabledKey, enabled);
  }

  static Future<void> setHapticEnabled(bool enabled) async {
    final prefs = await _preferences();
    await prefs.setBool(_hapticEnabledKey, enabled);
  }

  static Future<void> emit(
    SensoryFeedbackEvent event, {
    bool enableSound = true,
    bool enableHaptic = true,
  }) async {
    if (!_shouldEmit(event)) return;

    final soundAllowed = enableSound && await isSoundEnabled();
    final hapticAllowed = enableHaptic && await isHapticEnabled();

    if (soundAllowed) {
      unawaited(_playSound(event));
    }
    if (hapticAllowed) {
      unawaited(_playHaptic(event));
    }
  }

  static bool _shouldEmit(SensoryFeedbackEvent event) {
    final spec = _resolveSoundSpec(event);
    final now = DateTime.now();
    final last = _lastEmission[event];
    if (last != null && now.difference(last) < spec.minInterval) {
      return false;
    }
    _lastEmission[event] = now;
    return true;
  }

  static _FeedbackAudioSpec _resolveSoundSpec(SensoryFeedbackEvent event) {
    switch (event) {
      case SensoryFeedbackEvent.tap:
        return const _FeedbackAudioSpec(
          assetPath: '${_assetPrefix}button1.ogg',
          volume: 0.18,
          minInterval: Duration(milliseconds: 80),
          fallback: SystemSoundType.click,
        );
      case SensoryFeedbackEvent.selection:
      case SensoryFeedbackEvent.toggle:
        return const _FeedbackAudioSpec(
          assetPath: '${_assetPrefix}button2.ogg',
          volume: 0.16,
          minInterval: Duration(milliseconds: 100),
          fallback: SystemSoundType.click,
        );
      case SensoryFeedbackEvent.sheetOpen:
      case SensoryFeedbackEvent.dialogOpen:
      case SensoryFeedbackEvent.navigation:
        return const _FeedbackAudioSpec(
          assetPath: '${_assetPrefix}on.ogg',
          volume: 0.15,
          minInterval: Duration(milliseconds: 140),
          fallback: SystemSoundType.click,
        );
      case SensoryFeedbackEvent.confirm:
      case SensoryFeedbackEvent.success:
        return const _FeedbackAudioSpec(
          assetPath: '${_assetPrefix}complete.ogg',
          volume: 0.22,
          minInterval: Duration(milliseconds: 180),
          fallback: SystemSoundType.alert,
        );
      case SensoryFeedbackEvent.warning:
      case SensoryFeedbackEvent.error:
        return const _FeedbackAudioSpec(
          assetPath: '${_assetPrefix}off.ogg',
          volume: 0.18,
          minInterval: Duration(milliseconds: 200),
          fallback: SystemSoundType.alert,
        );
    }
  }

  static Future<void> _playSound(SensoryFeedbackEvent event) async {
    final spec = _resolveSoundSpec(event);
    try {
      final player = AudioPlayer();
      await player.setReleaseMode(ReleaseMode.stop);
      unawaited(
        player.onPlayerComplete.first.then((_) => player.dispose()).catchError((
          _,
        ) {
          unawaited(player.dispose());
        }),
      );
      await player.play(
        AssetSource(spec.assetPath),
        volume: spec.volume,
        mode: PlayerMode.lowLatency,
      );
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('SensoryFeedbackService sound fallback: $error');
        debugPrintStack(stackTrace: stackTrace);
      }
      await SystemSound.play(spec.fallback);
    }
  }

  static Future<void> _playHaptic(SensoryFeedbackEvent event) {
    switch (event) {
      case SensoryFeedbackEvent.tap:
      case SensoryFeedbackEvent.sheetOpen:
      case SensoryFeedbackEvent.dialogOpen:
        return HapticFeedback.lightImpact();
      case SensoryFeedbackEvent.selection:
      case SensoryFeedbackEvent.toggle:
      case SensoryFeedbackEvent.navigation:
        return HapticFeedback.selectionClick();
      case SensoryFeedbackEvent.confirm:
      case SensoryFeedbackEvent.success:
        return HapticFeedback.mediumImpact();
      case SensoryFeedbackEvent.warning:
        return HapticFeedback.mediumImpact();
      case SensoryFeedbackEvent.error:
        return HapticFeedback.heavyImpact();
    }
  }
}

class _FeedbackAudioSpec {
  const _FeedbackAudioSpec({
    required this.assetPath,
    required this.volume,
    required this.minInterval,
    required this.fallback,
  });

  final String assetPath;
  final double volume;
  final Duration minInterval;
  final SystemSoundType fallback;
}
