import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

// ---------------------------------------------------------------------------
// Event taxonomy
// ---------------------------------------------------------------------------

/// Semantic sensory events — one per distinct interaction type.
///
/// Rules:
/// - Same-level UI actions (all primary-button taps) → same event
/// - Distinct outcomes (tap vs. success vs. achievement) → distinct events
/// - High-value moments get richer feedback than routine actions
enum SensoryFeedbackEvent {
  // ── Routine interactions ─────────────────────────────────────────────────
  /// Generic primary-button / list-row tap
  tap,

  /// Toggle switch, ChoiceChip, FilterChip state change
  toggle,

  /// Tab switch, segment-control selection
  selection,

  // ── Navigation ───────────────────────────────────────────────────────────
  /// Any push/pop route transition
  navigation,

  /// Bottom-sheet / modal opens
  sheetOpen,

  /// Dialog opens
  dialogOpen,

  // ── Confirmations & outcomes ─────────────────────────────────────────────
  /// Generic confirm (save, submit)
  confirm,

  /// A task or step completes successfully
  success,

  /// Soft warning (destructive action preview, low flame)
  warning,

  /// Hard error (network fail, validation block)
  error,

  // ── High-value moments ───────────────────────────────────────────────────
  /// Daily check-in recorded
  checkin,

  /// Focus / Pomodoro session ends
  focusComplete,

  /// Galaxy star / knowledge node unlocked
  starUnlock,

  /// Achievement unlocked — common rarity
  achievementCommon,

  /// Achievement unlocked — rare rarity
  achievementRare,

  /// Achievement unlocked — epic rarity
  achievementEpic,

  /// Achievement unlocked — legendary rarity
  achievementLegendary,

  /// Streak milestone reached (7-day, 30-day …)
  streak,

  // ── Content interactions ─────────────────────────────────────────────────
  /// Message send in chat
  messageSend,

  /// AI response starts streaming
  aiResponseStart,

  /// Card flip / reveal
  cardFlip,

  /// Drag-and-drop: item picked up
  dragStart,

  /// Drag-and-drop: item dropped onto target
  dragDrop,
}

// ---------------------------------------------------------------------------
// Ambient audio scenes
// ---------------------------------------------------------------------------

/// Background ambient scenes for focus mode.
enum AmbientScene {
  none,
  rain,
  ocean,
  whiteNoise,
  cafe,
  piano,
}

extension AmbientSceneLabel on AmbientScene {
  String get label => switch (this) {
        AmbientScene.none => '无背景音',
        AmbientScene.rain => '雨声',
        AmbientScene.ocean => '海浪',
        AmbientScene.whiteNoise => '白噪音',
        AmbientScene.cafe => '咖啡馆',
        AmbientScene.piano => '轻钢琴',
      };

  String? get assetPath => switch (this) {
        AmbientScene.none => null,
        AmbientScene.rain => 'assets/audio/ambient/rain.ogg',
        AmbientScene.ocean => 'assets/audio/ambient/ocean_waves.ogg',
        AmbientScene.whiteNoise => 'assets/audio/ambient/white_noise.ogg',
        AmbientScene.cafe => 'assets/audio/ambient/cafe.ogg',
        AmbientScene.piano => 'assets/audio/ambient/piano.ogg',
      };
}

// ---------------------------------------------------------------------------
// Internal spec
// ---------------------------------------------------------------------------

class _SoundSpec {
  const _SoundSpec({
    required this.assetPath,
    required this.volume,
    required this.minInterval,
    this.fallback = SystemSoundType.click,
  });
  final String assetPath;
  final double volume;
  final Duration minInterval;
  final SystemSoundType fallback;
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

/// Unified sensory feedback service.
///
/// Architecture:
/// - **UI sound pool**: 3 `AudioPlayer` instances recycled round-robin for
///   rapid fire-and-forget sounds. Prevents the latency of creating a new
///   player on every tap.
/// - **Ambient player**: a single long-lived player for looping background
///   audio in focus mode.
/// - All API is static for call-site simplicity; state lives in _instance.
class SensoryFeedbackService {
  SensoryFeedbackService._();

  // ── Preferences keys ──────────────────────────────────────────────────────
  static const _soundEnabledKey = 'sensory_feedback.sound_enabled';
  static const _hapticEnabledKey = 'sensory_feedback.haptic_enabled';
  static const _ambientVolumeKey = 'sensory_feedback.ambient_volume';
  static const _ambientSceneKey = 'sensory_feedback.ambient_scene';

  // ── Player pool ───────────────────────────────────────────────────────────
  static const int _poolSize = 3;
  static final List<AudioPlayer> _pool = [];
  static int _poolIndex = 0;
  static bool _poolReady = false;

  // ── Ambient player ────────────────────────────────────────────────────────
  static AudioPlayer? _ambientPlayer;
  static AmbientScene _currentScene = AmbientScene.none;
  static double _currentAmbientOutputVolume = 0;

  // ── Throttle ──────────────────────────────────────────────────────────────
  static final Map<SensoryFeedbackEvent, DateTime> _lastEmission = {};
  static final List<DateTime> _recentSoundEvents = [];
  static final List<DateTime> _recentHapticEvents = [];
  static final Set<String> _missingSoundAssets = <String>{};
  static const Duration _soundBudgetWindow = Duration(milliseconds: 2200);
  static const Duration _hapticBudgetWindow = Duration(milliseconds: 1600);
  static const int _soundBudgetLimit = 5;
  static const int _hapticBudgetLimit = 3;

  // ── Prefs cache ───────────────────────────────────────────────────────────
  static SharedPreferences? _prefs;

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------

  /// Call once at app startup (e.g. in main.dart after WidgetsFlutterBinding).
  static Future<void> init() async {
    if (_poolReady) return;
    for (var i = 0; i < _poolSize; i++) {
      final player = AudioPlayer();
      await player.setReleaseMode(ReleaseMode.stop);
      _pool.add(player);
    }
    _poolReady = true;

    _ambientPlayer = AudioPlayer();
    await _ambientPlayer!.setReleaseMode(ReleaseMode.loop);
  }

  // ---------------------------------------------------------------------------
  // Preferences
  // ---------------------------------------------------------------------------

  static Future<SharedPreferences> _getPrefs() async =>
      _prefs ??= await SharedPreferences.getInstance();

  static Future<bool> isSoundEnabled() async =>
      (await _getPrefs()).getBool(_soundEnabledKey) ?? true;

  static Future<bool> isHapticEnabled() async =>
      (await _getPrefs()).getBool(_hapticEnabledKey) ?? true;

  static Future<void> setSoundEnabled(bool enabled) async =>
      _setSoundEnabled(enabled);

  static Future<void> setHapticEnabled(bool enabled) async =>
      (await _getPrefs()).setBool(_hapticEnabledKey, enabled);

  static Future<void> _setSoundEnabled(bool enabled) async {
    await (await _getPrefs()).setBool(_soundEnabledKey, enabled);
    if (enabled) {
      final scene = await getSavedAmbientScene();
      if (scene != AmbientScene.none) {
        await playAmbient(scene);
      }
      return;
    }
    for (final player in _pool) {
      await player.stop();
    }
    await _ambientPlayer?.stop();
    _currentScene = AmbientScene.none;
  }

  static Future<double> getAmbientVolume() async =>
      (await _getPrefs()).getDouble(_ambientVolumeKey) ?? 0.35;

  static Future<void> setAmbientVolume(double volume) async {
    await (await _getPrefs()).setDouble(_ambientVolumeKey, volume);
    _currentAmbientOutputVolume = volume;
    await _ambientPlayer?.setVolume(volume);
  }

  static Future<void> setAmbientScene(
    AmbientScene scene, {
    bool autoplay = false,
  }) async {
    await _saveAmbientScene(scene);
    if (!autoplay) {
      if (scene == AmbientScene.none && _currentScene != AmbientScene.none) {
        await stopAmbient();
      }
      return;
    }
    if (scene == AmbientScene.none) {
      await stopAmbient();
      return;
    }
    await playAmbient(scene);
  }

  static Future<AmbientScene> getSavedAmbientScene() async {
    final prefs = await _getPrefs();
    final index = prefs.getInt(_ambientSceneKey) ?? 0;
    return AmbientScene.values[index.clamp(0, AmbientScene.values.length - 1)];
  }

  static Future<void> _saveAmbientScene(AmbientScene scene) async =>
      (await _getPrefs()).setInt(_ambientSceneKey, scene.index);

  // ---------------------------------------------------------------------------
  // UI sound emission
  // ---------------------------------------------------------------------------

  static Future<void> emit(
    SensoryFeedbackEvent event, {
    bool enableSound = true,
    bool enableHaptic = true,
  }) async {
    if (!_shouldEmit(event)) return;

    final soundAllowed = enableSound && await isSoundEnabled();
    final hapticAllowed = enableHaptic && await isHapticEnabled();

    if (soundAllowed && _consumeBudget(_recentSoundEvents, _soundBudgetWindow, _soundBudgetLimit)) {
      unawaited(_playSound(event));
    }
    if (hapticAllowed && _consumeBudget(_recentHapticEvents, _hapticBudgetWindow, _hapticBudgetLimit)) {
      unawaited(_playHaptic(event));
    }
  }

  static bool _shouldEmit(SensoryFeedbackEvent event) {
    final spec = _spec(event);
    final now = DateTime.now();
    final last = _lastEmission[event];
    if (last != null && now.difference(last) < spec.minInterval) return false;
    _lastEmission[event] = now;
    return true;
  }

  static bool _consumeBudget(
    List<DateTime> history,
    Duration window,
    int limit,
  ) {
    final now = DateTime.now();
    history.removeWhere((ts) => now.difference(ts) >= window);
    if (history.length >= limit) {
      return false;
    }
    history.add(now);
    return true;
  }

  // ---------------------------------------------------------------------------
  // Ambient audio (background loop for focus mode)
  // ---------------------------------------------------------------------------

  static AmbientScene get currentScene => _currentScene;

  static Future<void> playAmbient(AmbientScene scene) async {
    if (scene == _currentScene) return;
    final player = _ambientPlayer;
    if (player == null) return;
    final previousScene = _currentScene;
    _currentScene = scene;
    await _saveAmbientScene(scene);

    final path = scene.assetPath;
    if (path == null) return;

    if (!await isSoundEnabled()) return;

    final volume = await getAmbientVolume();
    if (previousScene != AmbientScene.none) {
      await _fadeAmbientTo(0);
      await player.stop();
    }
    await player.setVolume(0);
    await player.play(AssetSource(path));
    _currentAmbientOutputVolume = 0;
    await _fadeAmbientTo(volume);
  }

  static Future<void> stopAmbient() async {
    _currentScene = AmbientScene.none;
    final player = _ambientPlayer;
    if (player == null) return;
    await _fadeAmbientTo(0);
    await player.stop();
  }

  static Future<void> pauseAmbient() async => _ambientPlayer?.pause();

  static Future<void> resumeAmbient() async {
    if (_currentScene == AmbientScene.none) return;
    await _ambientPlayer?.resume();
  }

  static Future<void> dispose() async {
    for (final p in _pool) {
      await p.dispose();
    }
    _pool.clear();
    _poolReady = false;
    await _ambientPlayer?.dispose();
    _ambientPlayer = null;
    _currentScene = AmbientScene.none;
    _currentAmbientOutputVolume = 0;
    _lastEmission.clear();
    _recentSoundEvents.clear();
    _recentHapticEvents.clear();
  }

  // ---------------------------------------------------------------------------
  // Internal: sound spec table
  // ---------------------------------------------------------------------------

  static const String _ui = 'assets/audio/ui/';

  static _SoundSpec _spec(SensoryFeedbackEvent event) {
    switch (event) {
      // Routine
      case SensoryFeedbackEvent.tap:
        return const _SoundSpec(
          assetPath: '${_ui}tap.ogg',
          volume: 0.18,
          minInterval: Duration(milliseconds: 80),
        );
      case SensoryFeedbackEvent.toggle:
        return const _SoundSpec(
          assetPath: '${_ui}toggle.ogg',
          volume: 0.16,
          minInterval: Duration(milliseconds: 100),
        );
      case SensoryFeedbackEvent.selection:
        return const _SoundSpec(
          assetPath: '${_ui}select.ogg',
          volume: 0.15,
          minInterval: Duration(milliseconds: 100),
        );
      // Navigation
      case SensoryFeedbackEvent.navigation:
        return const _SoundSpec(
          assetPath: '${_ui}nav.ogg',
          volume: 0.13,
          minInterval: Duration(milliseconds: 200),
        );
      case SensoryFeedbackEvent.sheetOpen:
        return const _SoundSpec(
          assetPath: '${_ui}sheet_open.ogg',
          volume: 0.14,
          minInterval: Duration(milliseconds: 150),
        );
      case SensoryFeedbackEvent.dialogOpen:
        return const _SoundSpec(
          assetPath: '${_ui}dialog_open.ogg',
          volume: 0.14,
          minInterval: Duration(milliseconds: 150),
        );
      // Confirmations
      case SensoryFeedbackEvent.confirm:
        return const _SoundSpec(
          assetPath: '${_ui}confirm.ogg',
          volume: 0.20,
          minInterval: Duration(milliseconds: 200),
          fallback: SystemSoundType.alert,
        );
      case SensoryFeedbackEvent.success:
        return const _SoundSpec(
          assetPath: '${_ui}success.ogg',
          volume: 0.22,
          minInterval: Duration(milliseconds: 300),
          fallback: SystemSoundType.alert,
        );
      case SensoryFeedbackEvent.warning:
        return const _SoundSpec(
          assetPath: '${_ui}warning.ogg',
          volume: 0.20,
          minInterval: Duration(milliseconds: 250),
          fallback: SystemSoundType.alert,
        );
      case SensoryFeedbackEvent.error:
        return const _SoundSpec(
          assetPath: '${_ui}error.ogg',
          volume: 0.22,
          minInterval: Duration(milliseconds: 300),
          fallback: SystemSoundType.alert,
        );
      // High-value moments
      case SensoryFeedbackEvent.checkin:
        return const _SoundSpec(
          assetPath: '${_ui}checkin.ogg',
          volume: 0.28,
          minInterval: Duration(seconds: 2),
          fallback: SystemSoundType.alert,
        );
      case SensoryFeedbackEvent.focusComplete:
        return const _SoundSpec(
          assetPath: '${_ui}focus_complete.ogg',
          volume: 0.30,
          minInterval: Duration(seconds: 5),
          fallback: SystemSoundType.alert,
        );
      case SensoryFeedbackEvent.starUnlock:
        return const _SoundSpec(
          assetPath: '${_ui}star_unlock.ogg',
          volume: 0.32,
          minInterval: Duration(seconds: 1),
          fallback: SystemSoundType.alert,
        );
      case SensoryFeedbackEvent.achievementCommon:
        return const _SoundSpec(
          assetPath: '${_ui}achievement_common.ogg',
          volume: 0.28,
          minInterval: Duration(seconds: 2),
          fallback: SystemSoundType.alert,
        );
      case SensoryFeedbackEvent.achievementRare:
        return const _SoundSpec(
          assetPath: '${_ui}achievement_rare.ogg',
          volume: 0.32,
          minInterval: Duration(seconds: 2),
          fallback: SystemSoundType.alert,
        );
      case SensoryFeedbackEvent.achievementEpic:
        return const _SoundSpec(
          assetPath: '${_ui}achievement_epic.ogg',
          volume: 0.36,
          minInterval: Duration(seconds: 2),
          fallback: SystemSoundType.alert,
        );
      case SensoryFeedbackEvent.achievementLegendary:
        return const _SoundSpec(
          assetPath: '${_ui}achievement_legendary.ogg',
          volume: 0.42,
          minInterval: Duration(seconds: 3),
          fallback: SystemSoundType.alert,
        );
      case SensoryFeedbackEvent.streak:
        return const _SoundSpec(
          assetPath: '${_ui}streak.ogg',
          volume: 0.30,
          minInterval: Duration(seconds: 2),
          fallback: SystemSoundType.alert,
        );
      // Content
      case SensoryFeedbackEvent.messageSend:
        return const _SoundSpec(
          assetPath: '${_ui}message_send.ogg',
          volume: 0.16,
          minInterval: Duration(milliseconds: 300),
        );
      case SensoryFeedbackEvent.aiResponseStart:
        return const _SoundSpec(
          assetPath: '${_ui}ai_start.ogg',
          volume: 0.12,
          minInterval: Duration(milliseconds: 500),
        );
      case SensoryFeedbackEvent.cardFlip:
        return const _SoundSpec(
          assetPath: '${_ui}card_flip.ogg',
          volume: 0.18,
          minInterval: Duration(milliseconds: 150),
        );
      case SensoryFeedbackEvent.dragStart:
        return const _SoundSpec(
          assetPath: '${_ui}drag_start.ogg',
          volume: 0.14,
          minInterval: Duration(milliseconds: 200),
        );
      case SensoryFeedbackEvent.dragDrop:
        return const _SoundSpec(
          assetPath: '${_ui}drag_drop.ogg',
          volume: 0.18,
          minInterval: Duration(milliseconds: 200),
        );
    }
  }

  // ---------------------------------------------------------------------------
  // Internal: playback
  // ---------------------------------------------------------------------------

  static Future<void> _playSound(SensoryFeedbackEvent event) async {
    final spec = _spec(event);
    if (_missingSoundAssets.contains(spec.assetPath)) {
      return;
    }

    // Ensure pool is ready (lazy init if init() was not called)
    if (!_poolReady) await init();

    final player = _pool[_poolIndex % _poolSize];
    _poolIndex++;

    try {
      await player.stop();
      await player.play(
        AssetSource(spec.assetPath),
        volume: spec.volume,
        mode: PlayerMode.lowLatency,
      );
    } catch (e, st) {
      final isMissingAsset = e.toString().contains('Unable to load asset');
      if (isMissingAsset) {
        _missingSoundAssets.add(spec.assetPath);
      }
      if (kDebugMode && !isMissingAsset) {
        debugPrint('SensoryFeedback sound error: $e');
        debugPrintStack(stackTrace: st);
      }
      // Graceful fallback to system sound
      try {
        await SystemSound.play(spec.fallback);
      } catch (_) {}
    }
  }

  // ---------------------------------------------------------------------------
  // Internal: haptic table
  // ---------------------------------------------------------------------------

  static Future<void> _playHaptic(SensoryFeedbackEvent event) {
    switch (event) {
      // Light — routine, non-destructive
      case SensoryFeedbackEvent.tap:
      case SensoryFeedbackEvent.sheetOpen:
      case SensoryFeedbackEvent.dialogOpen:
      case SensoryFeedbackEvent.cardFlip:
      case SensoryFeedbackEvent.aiResponseStart:
        return HapticFeedback.lightImpact();

      // Selection click — state changes, navigation
      case SensoryFeedbackEvent.selection:
      case SensoryFeedbackEvent.toggle:
      case SensoryFeedbackEvent.navigation:
      case SensoryFeedbackEvent.dragStart:
        return HapticFeedback.selectionClick();

      // Medium — confirms, successes, drops
      case SensoryFeedbackEvent.confirm:
      case SensoryFeedbackEvent.success:
      case SensoryFeedbackEvent.checkin:
      case SensoryFeedbackEvent.messageSend:
      case SensoryFeedbackEvent.dragDrop:
        return HapticFeedback.mediumImpact();

      // Heavy — high-value moments, errors
      case SensoryFeedbackEvent.warning:
      case SensoryFeedbackEvent.error:
      case SensoryFeedbackEvent.focusComplete:
      case SensoryFeedbackEvent.starUnlock:
      case SensoryFeedbackEvent.achievementCommon:
      case SensoryFeedbackEvent.achievementRare:
      case SensoryFeedbackEvent.streak:
        return HapticFeedback.heavyImpact();

      // Epic/legendary: heavy + delayed second pulse (handled in caller)
      case SensoryFeedbackEvent.achievementEpic:
      case SensoryFeedbackEvent.achievementLegendary:
        unawaited(HapticFeedback.heavyImpact());
        return Future.delayed(
          const Duration(milliseconds: 180),
          HapticFeedback.heavyImpact,
        );
    }
  }

  static Future<void> _fadeAmbientTo(
    double target, {
    Duration duration = const Duration(milliseconds: 260),
    int steps = 6,
  }) async {
    final player = _ambientPlayer;
    if (player == null) {
      return;
    }

    final current = _currentAmbientOutputVolume;
    for (var i = 1; i <= steps; i++) {
      final t = i / steps;
      final next = current + (target - current) * t;
      final clamped = next.clamp(0.0, 1.0);
      await player.setVolume(clamped);
      _currentAmbientOutputVolume = clamped;
      await Future<void>.delayed(duration ~/ steps);
    }
  }
}
