import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/services/i18n_service.dart';

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

enum AuroraSensoryEvent {
  coreSessionOpen,
  correctionCompleted,
  statusChanged,
  achievementUnlocked,
  streakContinued,
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
  String get label {
    final zh = I18nService.instance.isChinese;
    return switch (this) {
      AmbientScene.none => zh ? '无背景音' : 'No Background',
      AmbientScene.rain => zh ? '雨声' : 'Rain',
      AmbientScene.ocean => zh ? '海浪' : 'Ocean Waves',
      AmbientScene.whiteNoise => zh ? '白噪音' : 'White Noise',
      AmbientScene.cafe => zh ? '咖啡馆' : 'Cafe',
      AmbientScene.piano => zh ? '轻钢琴' : 'Soft Piano',
    };
  }

  String? get assetPath => switch (this) {
        AmbientScene.none => null,
        AmbientScene.rain => 'audio/ambient/rain.ogg',
        AmbientScene.ocean => 'audio/ambient/ocean_waves.ogg',
        AmbientScene.whiteNoise => 'audio/ambient/white_noise.ogg',
        AmbientScene.cafe => 'audio/ambient/cafe.ogg',
        AmbientScene.piano => 'audio/ambient/piano.ogg',
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

  @visibleForTesting
  static bool forceNativeDebugSoundFallback = true;

  // ── Preferences keys ──────────────────────────────────────────────────────
  static const _soundEnabledKey = 'sensory_feedback.sound_enabled';
  static const _hapticEnabledKey = 'sensory_feedback.haptic_enabled';
  static const _ambientEnabledKey = 'sensory_feedback.ambient_enabled';
  static const _ambientVolumeKey = 'sensory_feedback.ambient_volume';
  static const _ambientSceneKey = 'sensory_feedback.ambient_scene';
  static const _auroraLinkageEnabledKey =
      'sensory_feedback.aurora_linkage_enabled';

  // ── U14 音频诚实降级状态 ───────────────────────────────────────────────────
  // 「系统拒绝播放时降级静音并保持任务正常」（MOTION_AUDIO_HAPTICS 声音设计）：
  // 连续播放失败（渠道/系统拒绝，缺资产另有静默清单）达到阈值后置降级位——
  // 后续提示音不再逐事件重试（不连锁蜂鸣），触觉与视觉不受影响；任务流
  // 恒不受影响（本服务从不向调用方抛播放异常）。用户重新开启提示音即重试。
  static const int _audioDegradationThreshold = 2;
  static int _audioPlaybackFailureStreak = 0;
  static bool _audioPlaybackDegraded = false;

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
  static bool _auroraLinkageEnabledCache = true;

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

  /// U14：背景声独立开关。
  ///
  /// 卡验收 1（动效/背景声/提示音/触觉独立偏好）：背景声不再寄生于提示音
  /// 开关。键未落时向后兼容地继承既有「提示音开关」对背景声的事实门控
  /// （老用户关了提示音，背景声保持静音，不被升级悄悄打开）；用户首次
  /// 显式切换背景声后即独立。开启本开关**不自动续播**（默认不自动播放；
  /// 播放仍只由用户显式选场景/开始专注触发）。
  static Future<bool> isAmbientEnabled() async {
    final prefs = await _getPrefs();
    final saved = prefs.getBool(_ambientEnabledKey);
    if (saved != null) return saved;
    return isSoundEnabled();
  }

  static Future<void> setAmbientEnabled(bool enabled) async {
    await (await _getPrefs()).setBool(_ambientEnabledKey, enabled);
    if (!enabled) {
      await stopAmbient();
    }
    // enabled=true 不自动续播：尊重「默认不自动播放；重开不自行续播」。
  }

  /// U14：音频播放是否已处于降级（静音）态（设置页诚实呈现用）。
  static bool get audioPlaybackDegraded => _audioPlaybackDegraded;

  @visibleForTesting
  // ignore: use_setters_to_change_properties
  static void debugSetAudioPlaybackDegraded(bool degraded) {
    _audioPlaybackDegraded = degraded;
    _audioPlaybackFailureStreak = degraded ? _audioDegradationThreshold : 0;
  }

  static Future<bool> isAuroraLinkageEnabled() async {
    try {
      final saved = (await _getPrefs()).getBool(_auroraLinkageEnabledKey);
      if (saved != null) {
        _auroraLinkageEnabledCache = saved;
      }
    } catch (_) {
      // Widget tests and early startup can ask before SharedPreferences is
      // wired. Use the last known value rather than dropping the UI event.
    }
    return _auroraLinkageEnabledCache;
  }

  static Future<void> setAuroraLinkageEnabled(bool enabled) async {
    _auroraLinkageEnabledCache = enabled;
    await (await _getPrefs()).setBool(_auroraLinkageEnabledKey, enabled);
  }

  static Future<void> _setSoundEnabled(bool enabled) async {
    await (await _getPrefs()).setBool(_soundEnabledKey, enabled);
    if (enabled) {
      // U14：用户显式重开提示音 = 显式重试 → 清降级位。
      _audioPlaybackDegraded = false;
      _audioPlaybackFailureStreak = 0;
      // U14：提示音与背景声独立——开启提示音不再连带续播背景声；
      // 背景声由其独立开关与用户显式的场景/专注动作决定。
      return;
    }
    for (final player in _pool) {
      await player.stop();
    }
    // U14：关提示音只停 UI 提示音池，不再强制停掉背景声（独立偏好）。
    // 若用户想一并静音背景声，用背景声独立开关（setAmbientEnabled(false)）。
  }

  static Future<double> getAmbientVolume() async =>
      (await _getPrefs()).getDouble(_ambientVolumeKey) ?? 0.5;

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

    final soundAllowed =
        enableSound && await isSoundEnabled() && !_audioPlaybackDegraded;
    final hapticAllowed = enableHaptic && await isHapticEnabled();

    if (soundAllowed &&
        _consumeBudget(
          _recentSoundEvents,
          _soundBudgetWindow,
          _soundBudgetLimit,
        )) {
      unawaited(_playSound(event));
    }
    if (hapticAllowed &&
        _consumeBudget(
          _recentHapticEvents,
          _hapticBudgetWindow,
          _hapticBudgetLimit,
        )) {
      unawaited(_playHaptic(event));
    }
  }

  static Future<void> emitSeries(
    List<SensoryFeedbackEvent> events, {
    Duration gap = const Duration(milliseconds: 140),
    bool enableSound = true,
    bool enableHaptic = true,
  }) async {
    for (var i = 0; i < events.length; i++) {
      await emit(
        events[i],
        enableSound: enableSound,
        enableHaptic: enableHaptic,
      );
      if (i < events.length - 1) {
        await Future<void>.delayed(gap);
      }
    }
  }

  static Future<void> emitAuroraEvent(
    AuroraSensoryEvent event, {
    bool enableSound = true,
    bool enableHaptic = true,
  }) async {
    if (!await isAuroraLinkageEnabled()) {
      return;
    }
    await emit(
      _feedbackEventForAurora(event),
      enableSound: enableSound,
      enableHaptic: enableHaptic,
    );
  }

  @visibleForTesting
  static SensoryFeedbackEvent debugFeedbackEventForAurora(
    AuroraSensoryEvent event,
  ) =>
      _feedbackEventForAurora(event);

  @visibleForTesting
  // ignore: use_setters_to_change_properties
  static void debugSetAuroraLinkageEnabledCache(bool enabled) {
    _auroraLinkageEnabledCache = enabled;
  }

  static SensoryFeedbackEvent _feedbackEventForAurora(
    AuroraSensoryEvent event,
  ) {
    switch (event) {
      case AuroraSensoryEvent.coreSessionOpen:
        return SensoryFeedbackEvent.sheetOpen;
      case AuroraSensoryEvent.correctionCompleted:
        return SensoryFeedbackEvent.confirm;
      case AuroraSensoryEvent.statusChanged:
        return SensoryFeedbackEvent.selection;
      case AuroraSensoryEvent.achievementUnlocked:
        return SensoryFeedbackEvent.achievementRare;
      case AuroraSensoryEvent.streakContinued:
        return SensoryFeedbackEvent.checkin;
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

    // U14：背景声只受其独立开关门控（提示音开关不再连带背景声）。
    if (!await isAmbientEnabled()) return;

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
    _missingSoundAssets.clear();
    _prefs = null;
    _auroraLinkageEnabledCache = true;
    _audioPlaybackDegraded = false;
    _audioPlaybackFailureStreak = 0;
  }

  // ---------------------------------------------------------------------------
  // Internal: sound spec table
  // ---------------------------------------------------------------------------

  static const String _ui = 'audio/ui/';

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

    // Local debug builds on mobile simulators/emulators are noticeably more
    // stable and responsive when short UI sounds use the native system click
    // instead of going through AudioPlayer asset setup on every interaction.
    if (shouldUseNativeDebugSoundFallback) {
      try {
        await SystemSound.play(spec.fallback);
      } catch (_) {}
      return;
    }

    // Ensure pool is ready (lazy init if init() was not called)
    if (!_poolReady) await init();
    if (_pool.isEmpty) {
      return;
    }

    final player = _pool[_poolIndex % _poolSize];
    _poolIndex++;

    try {
      await player.stop();
      await player.play(
        AssetSource(spec.assetPath),
        volume: spec.volume,
        mode: PlayerMode.lowLatency,
      );
      // U14：播放成功 → 清降级计数（能力恢复）。
      _audioPlaybackFailureStreak = 0;
    } catch (e, st) {
      final isMissingAsset = e.toString().contains('Unable to load asset');
      if (isMissingAsset) {
        _missingSoundAssets.add(spec.assetPath);
      }
      if (kDebugMode && !isMissingAsset) {
        debugPrint('SensoryFeedback sound error: $e');
        debugPrintStack(stackTrace: st);
      }
      if (!isMissingAsset) {
        // U14 诚实降级：渠道/系统拒绝（非缺资产）→ 计入连续失败，
        // 达阈值后置降级位（后续事件不再逐次重试，不连锁蜂鸣）。
        _audioPlaybackFailureStreak++;
        if (_audioPlaybackFailureStreak >= _audioDegradationThreshold) {
          _audioPlaybackDegraded = true;
        }
      }
      // Graceful fallback to system sound
      try {
        await SystemSound.play(spec.fallback);
      } catch (_) {}
    }
  }

  @visibleForTesting
  static bool get shouldUseNativeDebugSoundFallback =>
      forceNativeDebugSoundFallback &&
      kDebugMode &&
      (defaultTargetPlatform == TargetPlatform.iOS ||
          defaultTargetPlatform == TargetPlatform.android);

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
