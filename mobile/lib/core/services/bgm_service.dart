import 'dart:async';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum BgmPriority {
  route,
  stage,
  component,
}

enum BgmPalette {
  adaptive,
  classical,
  piano,
  airy,
  warm,
}

enum BgmMode {
  adaptive,
  focusOnly,
  silent,
}

enum BgmTrack {
  dashboard,
  plan,
  chat,
  community,
  task,
  calendar,
  achievement,
  galaxy,
  insights,
  seeds,
  tools,
  profile,
  focusStart,
  focus,
  focusDeep,
  thinking,
  celebration,
  visualUnlock,
}

extension BgmTrackSpec on BgmTrack {
  double get mixVolume => switch (this) {
        BgmTrack.dashboard => 0.40,
        BgmTrack.plan => 0.36,
        BgmTrack.chat => 0.30,
        BgmTrack.community => 0.32,
        BgmTrack.task => 0.30,
        BgmTrack.calendar => 0.30,
        BgmTrack.achievement => 0.34,
        BgmTrack.galaxy => 0.30,
        BgmTrack.insights => 0.32,
        BgmTrack.seeds => 0.30,
        BgmTrack.tools => 0.28,
        BgmTrack.profile => 0.30,
        BgmTrack.focusStart => 0.26,
        BgmTrack.focus => 0.22,
        BgmTrack.focusDeep => 0.22,
        BgmTrack.thinking => 0.18,
        BgmTrack.celebration => 0.38,
        BgmTrack.visualUnlock => 0.30,
      };
}

class _BgmRegistration {
  const _BgmRegistration({
    required this.track,
    required this.priority,
    required this.sequence,
  });

  final BgmTrack track;
  final BgmPriority priority;
  final int sequence;
}

class _ResolvedBgmSource {
  _ResolvedBgmSource.asset(this.path)
      : source = AssetSource(path),
        isAsset = true;

  _ResolvedBgmSource.device(this.path)
      : source = DeviceFileSource(path),
        isAsset = false;

  final String path;
  final Source source;
  final bool isAsset;

  String get cacheKey => '${isAsset ? 'asset' : 'file'}:$path';
}

class BgmService {
  BgmService._();

  static const _fallbackBgmAssetPath = 'audio/bgm/calm_track_loop.m4a';
  static const _dashboardAsset = 'audio/bgm/relax_background1.m4a';
  static const _communityAsset = 'audio/bgm/loop_city.m4a';
  static const _warmAsset = 'audio/bgm/sunset_walk.m4a';
  static const _airyAsset = 'audio/bgm/oceanic_drift.m4a';
  static const _pianoAsset = 'audio/bgm/classical_piano_loop.m4a';
  static const _celebrationAsset = 'audio/bgm/heavenly_loop.m4a';
  static const _homeMorningAsset = 'audio/bgm/home_morning.m4a';
  static const _chatAmbientAsset = 'audio/bgm/chat_ambient.m4a';
  static const _taskFlowAsset = 'audio/bgm/task_flow.m4a';
  static const _focusDeepAsset = 'audio/bgm/focus_deep.m4a';
  static const _focusBinauralAsset = 'audio/bgm/focus_binaural.m4a';
  static const _galaxySpaceAsset = 'audio/bgm/galaxy_space.m4a';
  static const _achievementWarmAsset = 'audio/bgm/achievement_warm.m4a';
  static const _communityJazzAsset = 'audio/bgm/community_jazz.m4a';
  static const _calendarPlanAsset = 'audio/bgm/calendar_plan.m4a';
  static const _insightsHarpAsset = 'audio/bgm/insights_harp.m4a';
  static const _seedsNatureAsset = 'audio/bgm/seeds_nature.m4a';
  static const _profileReflectAsset = 'audio/bgm/profile_reflect.m4a';
  static const _thinkingAsset = 'audio/bgm/thinking.m4a';
  static const _localOverrideRoot = String.fromEnvironment(
    'SPARKLE_LOCAL_BGM_DIR',
    defaultValue:
        '/Users/brsama/code/GitHub/Sparkle-project/mobile/local_audio_overrides/bgm',
  );

  static const _enabledKey = 'bgm.enabled';
  static const _volumeKey = 'bgm.volume';
  static const _paletteKey = 'bgm.palette';
  static const _modeKey = 'bgm.mode';
  static const _savedPositionsKey = 'bgm.saved_positions_v1';
  static const _playlistIndicesKey = 'bgm.playlist_indices_v1';

  static AudioPlayer? _player;
  static AudioPlayer? _preloadPlayer;
  static SharedPreferences? _prefs;
  static final WidgetsBindingObserver _lifecycleObserver =
      _BgmLifecycleObserver();
  static final Map<Object, _BgmRegistration> _registrations = {};
  static int _sequence = 0;
  static bool _isRefreshing = false;
  static bool _refreshQueued = false;
  static int _duckSequence = 0;
  static bool _observerRegistered = false;
  static BgmTrack? _currentTrack;
  static BgmPriority? _currentPriority;
  static String? _currentSourceKey;
  static String? _preloadedSourceKey;
  static double _currentOutputVolume = 0;
  static double _persistentDuckFactor = 1.0;
  static final Set<String> _missingAssetPaths = <String>{};
  static final Map<String, Duration> _savedPositions = <String, Duration>{};
  static final Map<BgmTrack, int> _trackPlaylistIndices = <BgmTrack, int>{};
  static bool _persistentStateLoaded = false;
  static final Map<BgmTrack, String> _adaptiveLocalOverrideFiles =
      <BgmTrack, String>{
    BgmTrack.dashboard: 'home_morning.m4a',
    BgmTrack.chat: 'chat_ambient.m4a',
    BgmTrack.task: 'task_flow.m4a',
    BgmTrack.calendar: 'calendar_plan.m4a',
    BgmTrack.plan: 'calendar_plan.m4a',
    BgmTrack.focusStart: 'focus_deep.m4a',
    BgmTrack.focus: 'focus_binaural.m4a',
    BgmTrack.focusDeep: 'focus_deep.m4a',
    BgmTrack.galaxy: 'galaxy_space.m4a',
    BgmTrack.insights: 'insights_harp.m4a',
    BgmTrack.seeds: 'seeds_nature.m4a',
    BgmTrack.community: 'community_jazz.m4a',
    BgmTrack.achievement: 'achievement_warm.m4a',
    BgmTrack.celebration: 'achievement_warm.m4a',
    BgmTrack.visualUnlock: 'achievement_warm.m4a',
    BgmTrack.profile: 'profile_reflect.m4a',
    BgmTrack.thinking: 'thinking.m4a',
    BgmTrack.tools: 'calendar_plan.m4a',
  };
  static const Map<BgmTrack, List<String>> _classicalAssetPlaylists =
      <BgmTrack, List<String>>{
    BgmTrack.dashboard: <String>[
      _homeMorningAsset,
      _dashboardAsset,
      _warmAsset,
    ],
    BgmTrack.chat: <String>[
      _chatAmbientAsset,
      _thinkingAsset,
      _profileReflectAsset,
    ],
    BgmTrack.plan: <String>[
      _calendarPlanAsset,
      _taskFlowAsset,
      _profileReflectAsset,
    ],
    BgmTrack.task: <String>[
      _taskFlowAsset,
      _calendarPlanAsset,
      _pianoAsset,
    ],
    BgmTrack.calendar: <String>[
      _calendarPlanAsset,
      _taskFlowAsset,
      _pianoAsset,
    ],
    BgmTrack.community: <String>[
      _communityJazzAsset,
      _dashboardAsset,
      _warmAsset,
    ],
    BgmTrack.achievement: <String>[
      _achievementWarmAsset,
      _celebrationAsset,
      _warmAsset,
    ],
    BgmTrack.galaxy: <String>[
      _galaxySpaceAsset,
      _insightsHarpAsset,
      _airyAsset,
    ],
    BgmTrack.insights: <String>[
      _insightsHarpAsset,
      _thinkingAsset,
      _profileReflectAsset,
    ],
    BgmTrack.seeds: <String>[
      _seedsNatureAsset,
      _calendarPlanAsset,
      _profileReflectAsset,
    ],
    BgmTrack.tools: <String>[
      _calendarPlanAsset,
      _taskFlowAsset,
      _pianoAsset,
    ],
    BgmTrack.profile: <String>[
      _profileReflectAsset,
      _chatAmbientAsset,
      _insightsHarpAsset,
    ],
    BgmTrack.focusStart: <String>[
      _focusDeepAsset,
      _focusBinauralAsset,
    ],
    BgmTrack.focus: <String>[
      _focusBinauralAsset,
      _focusDeepAsset,
    ],
    BgmTrack.focusDeep: <String>[
      _focusDeepAsset,
      _focusBinauralAsset,
    ],
    BgmTrack.thinking: <String>[
      _thinkingAsset,
      _chatAmbientAsset,
      _insightsHarpAsset,
    ],
    BgmTrack.celebration: <String>[
      _achievementWarmAsset,
      _celebrationAsset,
      _warmAsset,
    ],
    BgmTrack.visualUnlock: <String>[
      _achievementWarmAsset,
      _celebrationAsset,
      _warmAsset,
    ],
  };
  static StreamSubscription<void>? _playerCompletionSubscription;
  static StreamSubscription<void>? _preloadCompletionSubscription;

  static Future<void> init() async {
    if (_player != null) {
      return;
    }
    _player = AudioPlayer();
    await _player!.setReleaseMode(ReleaseMode.release);
    _preloadPlayer = AudioPlayer();
    await _preloadPlayer!.setReleaseMode(ReleaseMode.stop);
    final primaryPlayer = _player!;
    final standbyPlayer = _preloadPlayer!;
    _playerCompletionSubscription?.cancel();
    _preloadCompletionSubscription?.cancel();
    _playerCompletionSubscription = primaryPlayer.onPlayerComplete.listen((_) {
      unawaited(_handleTrackCompletion(primaryPlayer));
    });
    _preloadCompletionSubscription = standbyPlayer.onPlayerComplete.listen((_) {
      unawaited(_handleTrackCompletion(standbyPlayer));
    });
    if (!_observerRegistered) {
      WidgetsBinding.instance.addObserver(_lifecycleObserver);
      _observerRegistered = true;
    }
    await _restorePersistentState();
  }

  static Future<SharedPreferences> _getPrefs() async =>
      _prefs ??= await SharedPreferences.getInstance();

  static Future<bool> isEnabled() async =>
      (await _getPrefs()).getBool(_enabledKey) ?? true;

  static Future<void> setEnabled(bool enabled) async {
    await (await _getPrefs()).setBool(_enabledKey, enabled);
    await _refreshPlayback(force: true);
  }

  static Future<double> getVolume() async =>
      (await _getPrefs()).getDouble(_volumeKey) ?? 0.85;

  static Future<void> setVolume(double volume) async {
    await (await _getPrefs()).setDouble(_volumeKey, volume.clamp(0.0, 1.0));
    final player = _player;
    if (_currentTrack != null && player != null) {
      final target = await _targetVolume(_currentTrack!);
      await player.setVolume(target);
      _currentOutputVolume = target;
    }
  }

  static Future<void> setPersistentDuckFactor(
    double factor, {
    Duration duration = const Duration(milliseconds: 220),
  }) async {
    final normalized = factor.clamp(0.0, 1.0);
    if ((_persistentDuckFactor - normalized).abs() < 0.001) {
      return;
    }
    _persistentDuckFactor = normalized;
    final currentTrack = _currentTrack;
    final player = _player;
    if (currentTrack == null || player == null || _isRefreshing) {
      return;
    }
    await _fadeTo(
      await _targetVolume(currentTrack),
      duration: duration,
      steps: 5,
    );
  }

  static Future<BgmPalette> getPalette() async {
    final raw = (await _getPrefs()).getString(_paletteKey);
    return BgmPalette.values.firstWhere(
      (value) => value.name == raw,
      orElse: () => BgmPalette.adaptive,
    );
  }

  static Future<void> setPalette(BgmPalette palette) async {
    await (await _getPrefs()).setString(_paletteKey, palette.name);
    await _refreshPlayback(force: true);
  }

  static Future<BgmMode> getMode() async {
    final raw = (await _getPrefs()).getString(_modeKey);
    return BgmMode.values.firstWhere(
      (value) => value.name == raw,
      orElse: () => BgmMode.adaptive,
    );
  }

  static Future<void> setMode(BgmMode mode) async {
    await (await _getPrefs()).setString(_modeKey, mode.name);
    await _refreshPlayback(force: true);
  }

  static Object activate(
    BgmTrack track, {
    BgmPriority priority = BgmPriority.route,
  }) {
    final token = Object();
    _registrations[token] = _BgmRegistration(
      track: track,
      priority: priority,
      sequence: ++_sequence,
    );
    unawaited(_refreshPlayback());
    return token;
  }

  static Future<void> update(
    Object token, {
    required BgmTrack track,
    BgmPriority priority = BgmPriority.route,
  }) async {
    if (!_registrations.containsKey(token)) {
      return;
    }
    _registrations[token] = _BgmRegistration(
      track: track,
      priority: priority,
      sequence: ++_sequence,
    );
    await _refreshPlayback();
  }

  static Future<void> deactivate(Object token) async {
    _registrations.remove(token);
    await _refreshPlayback();
  }

  static Future<void> pause() async {
    await _captureCurrentPlaybackPosition();
    await _player?.pause();
  }

  static Future<void> resume() async {
    if (!await isEnabled()) {
      return;
    }
    if (_registrations.isEmpty) {
      return;
    }
    await _refreshPlayback(force: true);
  }

  static Future<void> stop() async {
    await _captureCurrentPlaybackPosition();
    _registrations.clear();
    await _refreshPlayback(force: true);
  }

  static Future<void> previewPalette(
    BgmPalette palette, {
    Duration duration = const Duration(seconds: 3),
  }) async {
    final player = AudioPlayer();
    try {
      final source = await _previewSourceForPalette(palette);
      await player.setReleaseMode(ReleaseMode.stop);
      await player.play(
        source.source,
        volume: 0.65,
        mode: PlayerMode.mediaPlayer,
      );
      await Future<void>.delayed(duration);
      await player.stop();
    } catch (e) {
      if (kDebugMode) {
        debugPrint('BGM preview error for ${palette.name}: $e');
      }
    } finally {
      await player.dispose();
    }
  }

  static Future<void> duckForNavigation({bool isBackNavigation = false}) async {
    final player = _player;
    final currentTrack = _currentTrack;
    if (player == null || currentTrack == null || _isRefreshing) {
      return;
    }

    final sequence = ++_duckSequence;
    final targetVolume = await _targetVolume(currentTrack);
    final duckFactor = isBackNavigation ? 0.84 : 0.7;
    final duckDuration = isBackNavigation
        ? const Duration(milliseconds: 120)
        : const Duration(milliseconds: 160);
    final settleDuration = isBackNavigation
        ? const Duration(milliseconds: 120)
        : const Duration(milliseconds: 180);

    await _fadeTo(targetVolume * duckFactor, duration: duckDuration, steps: 4);
    await Future<void>.delayed(settleDuration);

    if (sequence != _duckSequence || _isRefreshing || _player == null) {
      return;
    }
    await _refreshPlayback();
  }

  static Future<void> duckTemporarily({
    double factor = 0.3,
    Duration fadeDuration = const Duration(milliseconds: 220),
    Duration holdDuration = const Duration(milliseconds: 720),
    int steps = 5,
  }) async {
    final player = _player;
    final currentTrack = _currentTrack;
    if (player == null || currentTrack == null || _isRefreshing) {
      return;
    }

    final sequence = ++_duckSequence;
    final targetVolume = await _targetVolume(currentTrack);
    final clampedFactor = factor.clamp(0.0, 1.0);

    await _fadeTo(
      targetVolume * clampedFactor,
      duration: fadeDuration,
      steps: steps,
    );
    await Future<void>.delayed(holdDuration);

    if (sequence != _duckSequence || _isRefreshing || _player == null) {
      return;
    }
    await _refreshPlayback();
  }

  static Future<void> boostTemporarily({
    double factor = 1.15,
    Duration holdDuration = const Duration(milliseconds: 800),
    Duration fadeDuration = const Duration(milliseconds: 160),
    int steps = 4,
  }) async {
    final player = _player;
    final currentTrack = _currentTrack;
    if (player == null || currentTrack == null || _isRefreshing) {
      return;
    }

    final sequence = ++_duckSequence;
    final baseTarget = await _targetVolume(currentTrack);
    final boosted = (baseTarget * factor).clamp(0.0, 1.0);

    await _fadeTo(boosted, duration: fadeDuration, steps: steps);
    await Future<void>.delayed(holdDuration);

    if (sequence != _duckSequence || _isRefreshing || _player == null) {
      return;
    }
    await _fadeTo(baseTarget, duration: fadeDuration, steps: steps);
  }

  static Future<void> dispose() async {
    _registrations.clear();
    await _captureCurrentPlaybackPosition();
    if (_observerRegistered) {
      WidgetsBinding.instance.removeObserver(_lifecycleObserver);
      _observerRegistered = false;
    }
    await _player?.dispose();
    await _preloadPlayer?.dispose();
    await _playerCompletionSubscription?.cancel();
    await _preloadCompletionSubscription?.cancel();
    _playerCompletionSubscription = null;
    _preloadCompletionSubscription = null;
    _player = null;
    _preloadPlayer = null;
    _currentTrack = null;
    _currentSourceKey = null;
    _preloadedSourceKey = null;
  }

  static Future<void> _refreshPlayback({bool force = false}) async {
    await init();

    if (_isRefreshing) {
      _refreshQueued = true;
      return;
    }

    _isRefreshing = true;
    try {
      final desiredTrack = await _resolveDesiredTrack();
      final enabled = await isEnabled();

      if (!enabled || desiredTrack == null) {
        if (_player != null) {
          await _fadeTo(
            0,
            duration: _fadeDurationForTrack(
              _currentTrack,
              _currentPriority,
            ),
          );
          await _player!.stop();
        }
        _currentTrack = null;
        _currentPriority = null;
        _currentOutputVolume = 0;
      } else if (!force && desiredTrack == _currentTrack) {
        await _player?.setVolume(await _targetVolume(desiredTrack));
      } else {
        await _switchTrack(desiredTrack);
      }
      if (desiredTrack != null) {
        unawaited(_preloadLikelyNextTrack(desiredTrack));
      }
    } finally {
      _isRefreshing = false;
      if (_refreshQueued) {
        _refreshQueued = false;
        unawaited(_refreshPlayback());
      }
    }
  }

  static _BgmRegistration? _resolveRegistration() {
    if (_registrations.isEmpty) {
      return null;
    }
    final values = _registrations.values.toList()
      ..sort((a, b) {
        final priorityCompare = b.priority.index.compareTo(a.priority.index);
        if (priorityCompare != 0) {
          return priorityCompare;
        }
        return b.sequence.compareTo(a.sequence);
      });
    return values.first;
  }

  static Future<BgmTrack?> _resolveDesiredTrack() async {
    final registration = _resolveRegistration();
    if (registration == null) {
      return null;
    }
    final mode = await getMode();
    if (mode == BgmMode.silent) {
      return null;
    }
    if (mode == BgmMode.focusOnly && !_isFocusTrack(registration.track)) {
      return null;
    }
    return registration.track;
  }

  static bool _isFocusTrack(BgmTrack track) {
    switch (track) {
      case BgmTrack.focusStart:
      case BgmTrack.focus:
      case BgmTrack.focusDeep:
        return true;
      default:
        return false;
    }
  }

  static Future<void> _switchTrack(BgmTrack track) async {
    final activePlayer = _player;
    final standbyPlayer = _preloadPlayer;
    if (activePlayer == null || standbyPlayer == null) {
      return;
    }

    final registration = _resolveRegistration();
    final fadeDuration = _fadeDurationForTrack(track, registration?.priority);
    final resolvedSource = await _resolvePlayableSource(track);

    if (_currentSourceKey == resolvedSource.cacheKey) {
      _currentTrack = track;
      _currentPriority = registration?.priority;
      await activePlayer.resume();
      await _fadeTo(await _targetVolume(track), duration: fadeDuration);
      await _persistPlaybackState();
      return;
    }

    try {
      await _captureCurrentPlaybackPosition();
      await standbyPlayer.setReleaseMode(ReleaseMode.release);
      await standbyPlayer.play(
        resolvedSource.source,
        volume: 0,
        mode: PlayerMode.mediaPlayer,
      );
      final savedPosition = _savedPositions[resolvedSource.cacheKey];
      if (savedPosition != null && savedPosition > Duration.zero) {
        await standbyPlayer.seek(savedPosition);
      }
      final nextTargetVolume = await _targetVolume(track);
      _currentTrack = track;
      _currentPriority = registration?.priority;
      _currentSourceKey = resolvedSource.cacheKey;
      await Future.wait([
        _fadePlayerVolume(
          activePlayer,
          from: _currentOutputVolume,
          to: 0,
          duration: fadeDuration,
        ),
        _fadePlayerVolume(
          standbyPlayer,
          from: 0,
          to: nextTargetVolume,
          duration: fadeDuration,
        ),
      ]);
      await activePlayer.stop();
      _player = standbyPlayer;
      _preloadPlayer = activePlayer;
      _currentOutputVolume = nextTargetVolume;
      _preloadedSourceKey = null;
      await _persistPlaybackState();
    } catch (e) {
      if (resolvedSource.isAsset &&
          e.toString().contains('Unable to load asset')) {
        _missingAssetPaths.add(resolvedSource.path);
      } else if (kDebugMode) {
        debugPrint('BGM switch error for ${resolvedSource.path}: $e');
      }
      _currentTrack = null;
      _currentPriority = null;
      _currentSourceKey = null;
      _currentOutputVolume = 0;
    }
  }

  static Future<void> _preloadLikelyNextTrack(BgmTrack currentTrack) async {
    final preloadPlayer = _preloadPlayer;
    if (preloadPlayer == null) {
      return;
    }
    final nextTrack = _likelyNextTrack(currentTrack);
    if (nextTrack == null) {
      return;
    }
    final resolvedSource = await _resolvePlayableSource(nextTrack);
    if (resolvedSource.cacheKey == _currentSourceKey ||
        resolvedSource.cacheKey == _preloadedSourceKey) {
      return;
    }
    try {
      await preloadPlayer.stop();
      if (resolvedSource.isAsset) {
        await preloadPlayer.setSourceAsset(resolvedSource.path);
      } else {
        await preloadPlayer.setSourceDeviceFile(resolvedSource.path);
      }
      _preloadedSourceKey = resolvedSource.cacheKey;
    } catch (e) {
      if (resolvedSource.isAsset &&
          e.toString().contains('Unable to load asset')) {
        _missingAssetPaths.add(resolvedSource.path);
      }
      _preloadedSourceKey = null;
    }
  }

  static BgmTrack? _likelyNextTrack(BgmTrack track) {
    switch (track) {
      case BgmTrack.dashboard:
        return BgmTrack.chat;
      case BgmTrack.chat:
        return BgmTrack.task;
      case BgmTrack.task:
        return BgmTrack.focusStart;
      case BgmTrack.focusStart:
      case BgmTrack.focus:
      case BgmTrack.focusDeep:
        return BgmTrack.achievement;
      case BgmTrack.achievement:
        return BgmTrack.community;
      case BgmTrack.community:
        return BgmTrack.dashboard;
      case BgmTrack.plan:
        return BgmTrack.task;
      case BgmTrack.calendar:
        return BgmTrack.task;
      case BgmTrack.galaxy:
        return BgmTrack.insights;
      case BgmTrack.insights:
        return BgmTrack.plan;
      case BgmTrack.seeds:
        return BgmTrack.insights;
      case BgmTrack.tools:
        return BgmTrack.focusStart;
      case BgmTrack.profile:
        return BgmTrack.dashboard;
      case BgmTrack.thinking:
        return BgmTrack.chat;
      case BgmTrack.celebration:
      case BgmTrack.visualUnlock:
        return BgmTrack.dashboard;
    }
  }

  static Future<double> _targetVolume(BgmTrack track) async =>
      (await getVolume()) * track.mixVolume * _persistentDuckFactor;

  static Future<void> _captureCurrentPlaybackPosition() async {
    final player = _player;
    final sourceKey = _currentSourceKey;
    if (player == null || sourceKey == null) {
      return;
    }
    try {
      final position = await player.getCurrentPosition();
      if (position != null && position > Duration.zero) {
        _savedPositions[sourceKey] = position;
        await _persistPlaybackState();
      }
    } catch (_) {
      // Ignore progress snapshot failures and keep playback flowing.
    }
  }

  static Future<_ResolvedBgmSource> _resolvePlayableSource(
      BgmTrack track) async {
    final localPlaylist = await _resolveLocalOverridePlaylist(track);
    if (localPlaylist.isNotEmpty) {
      final fileName = _selectPlaylistEntry(track, localPlaylist);
      final file = File('$_localOverrideRoot/$fileName');
      if (await file.exists()) {
        return _ResolvedBgmSource.device(file.path);
      }
    }
    final localOverride = await _resolveLocalOverride(track);
    if (localOverride != null) {
      return localOverride;
    }
    final assetPlaylist = await _resolveAssetPlaylist(track);
    if (assetPlaylist.isNotEmpty) {
      final assetPath = _selectPlaylistEntry(track, assetPlaylist);
      if (!_missingAssetPaths.contains(assetPath)) {
        return _ResolvedBgmSource.asset(assetPath);
      }
    }
    return _ResolvedBgmSource.asset(await _resolvePlayableAssetPath(track));
  }

  static Future<void> _handleTrackCompletion(AudioPlayer player) async {
    if (!identical(player, _player) || _isRefreshing) {
      return;
    }
    final currentTrack = _currentTrack;
    if (currentTrack == null) {
      return;
    }
    final playlist = await _resolveEffectivePlaylist(currentTrack);
    if (playlist.length <= 1) {
      try {
        await player.seek(Duration.zero);
        await player.resume();
      } catch (_) {}
      return;
    }
    final currentIndex = _trackPlaylistIndices[currentTrack] ?? 0;
    _trackPlaylistIndices[currentTrack] = (currentIndex + 1) % playlist.length;
    await _persistPlaybackState();
    await _refreshPlayback(force: true);
  }

  static String _selectPlaylistEntry(BgmTrack track, List<String> entries) {
    final index = _trackPlaylistIndices[track] ?? 0;
    final normalizedIndex = entries.isEmpty ? 0 : index % entries.length;
    _trackPlaylistIndices[track] = normalizedIndex;
    return entries[normalizedIndex];
  }

  static Future<List<String>> _resolveEffectivePlaylist(BgmTrack track) async {
    final localPlaylist = await _resolveLocalOverridePlaylist(track);
    if (localPlaylist.isNotEmpty) {
      return localPlaylist;
    }
    final assetPlaylist = await _resolveAssetPlaylist(track);
    if (assetPlaylist.isNotEmpty) {
      return assetPlaylist;
    }
    return <String>[await _resolvePlayableAssetPath(track)];
  }

  static Future<List<String>> _resolveLocalOverridePlaylist(
      BgmTrack track) async {
    if (!kDebugMode || _localOverrideRoot.isEmpty) {
      return const <String>[];
    }
    final palette = await getPalette();
    if (palette != BgmPalette.adaptive && palette != BgmPalette.classical) {
      return const <String>[];
    }
    final names = <String>{
      if (_adaptiveLocalOverrideFiles[track] case final String primary) primary,
      ...?_classicalAssetPlaylists[track]
          ?.map((assetPath) => assetPath.split('/').last),
    }.toList();
    final available = <String>[];
    for (final name in names) {
      final file = File('$_localOverrideRoot/$name');
      if (await file.exists()) {
        available.add(name);
      }
    }
    return available;
  }

  static Future<List<String>> _resolveAssetPlaylist(BgmTrack track) async {
    final palette = await getPalette();
    switch (palette) {
      case BgmPalette.classical:
      case BgmPalette.adaptive:
        return _classicalAssetPlaylists[track] ?? const <String>[];
      case BgmPalette.piano:
      case BgmPalette.airy:
      case BgmPalette.warm:
        return const <String>[];
    }
  }

  static Future<_ResolvedBgmSource?> _resolveLocalOverride(
      BgmTrack track) async {
    if (!kDebugMode || _localOverrideRoot.isEmpty) {
      return null;
    }
    final palette = await getPalette();
    if (palette != BgmPalette.adaptive && palette != BgmPalette.classical) {
      return null;
    }
    final fileName = _adaptiveLocalOverrideFiles[track];
    if (fileName == null) {
      return null;
    }
    final file = File('$_localOverrideRoot/$fileName');
    if (!await file.exists()) {
      return null;
    }
    return _ResolvedBgmSource.device(file.path);
  }

  static Future<String> _resolvePlayableAssetPath(BgmTrack track) async {
    final primary = await _resolveAssetPath(track);
    if (!_missingAssetPaths.contains(primary)) {
      return primary;
    }
    return _fallbackBgmAssetPath;
  }

  static Future<String> _resolveAssetPath(BgmTrack track) async {
    final palette = await getPalette();
    switch (track) {
      case BgmTrack.dashboard:
        return switch (palette) {
          BgmPalette.adaptive => _homeMorningAsset,
          BgmPalette.classical => _homeMorningAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
        };
      case BgmTrack.plan:
        return switch (palette) {
          BgmPalette.classical => _calendarPlanAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _calendarPlanAsset,
        };
      case BgmTrack.chat:
        return switch (palette) {
          BgmPalette.classical => _chatAmbientAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          _ => _chatAmbientAsset,
        };
      case BgmTrack.community:
        return switch (palette) {
          BgmPalette.classical => _communityJazzAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _dashboardAsset,
          BgmPalette.warm => _communityAsset,
          BgmPalette.adaptive => _communityJazzAsset,
        };
      case BgmTrack.task:
        return switch (palette) {
          BgmPalette.classical => _taskFlowAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _taskFlowAsset,
        };
      case BgmTrack.calendar:
        return switch (palette) {
          BgmPalette.classical => _calendarPlanAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _dashboardAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _calendarPlanAsset,
        };
      case BgmTrack.achievement:
        return switch (palette) {
          BgmPalette.classical => _achievementWarmAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _celebrationAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _achievementWarmAsset,
        };
      case BgmTrack.galaxy:
        return switch (palette) {
          BgmPalette.classical => _galaxySpaceAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _celebrationAsset,
          BgmPalette.adaptive => _galaxySpaceAsset,
        };
      case BgmTrack.celebration:
        return switch (palette) {
          BgmPalette.classical => _achievementWarmAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _celebrationAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _achievementWarmAsset,
        };
      case BgmTrack.insights:
        return switch (palette) {
          BgmPalette.classical => _insightsHarpAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          _ => _insightsHarpAsset,
        };
      case BgmTrack.seeds:
        return switch (palette) {
          BgmPalette.classical => _seedsNatureAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          _ => _seedsNatureAsset,
        };
      case BgmTrack.tools:
        return switch (palette) {
          BgmPalette.classical => _calendarPlanAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _taskFlowAsset,
        };
      case BgmTrack.profile:
        return switch (palette) {
          BgmPalette.classical => _profileReflectAsset,
          BgmPalette.airy => _dashboardAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.adaptive => _profileReflectAsset,
        };
      case BgmTrack.focusStart:
        return switch (palette) {
          BgmPalette.classical => _focusDeepAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.adaptive => _focusDeepAsset,
        };
      case BgmTrack.focus:
        return switch (palette) {
          BgmPalette.classical => _focusBinauralAsset,
          _ => _focusBinauralAsset,
        };
      case BgmTrack.focusDeep:
        return switch (palette) {
          BgmPalette.classical => _focusDeepAsset,
          _ => _focusDeepAsset,
        };
      case BgmTrack.thinking:
        return switch (palette) {
          BgmPalette.classical => _thinkingAsset,
          BgmPalette.adaptive => _thinkingAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _insightsHarpAsset,
          BgmPalette.warm => _chatAmbientAsset,
        };
      case BgmTrack.visualUnlock:
        return switch (palette) {
          BgmPalette.classical => _achievementWarmAsset,
          BgmPalette.piano => _pianoAsset,
          BgmPalette.airy => _celebrationAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _achievementWarmAsset,
        };
    }
  }

  static String _previewAssetPathForPalette(BgmPalette palette) =>
      switch (palette) {
        BgmPalette.adaptive => _homeMorningAsset,
        BgmPalette.classical => _chatAmbientAsset,
        BgmPalette.piano => _pianoAsset,
        BgmPalette.airy => _galaxySpaceAsset,
        BgmPalette.warm => _warmAsset,
      };

  static Future<_ResolvedBgmSource> _previewSourceForPalette(
    BgmPalette palette,
  ) async {
    if (palette == BgmPalette.adaptive || palette == BgmPalette.classical) {
      final previewFile = palette == BgmPalette.classical
          ? 'chat_ambient.m4a'
          : 'home_morning.m4a';
      final file = File('$_localOverrideRoot/$previewFile');
      if (kDebugMode && await file.exists()) {
        return _ResolvedBgmSource.device(file.path);
      }
    }
    return _ResolvedBgmSource.asset(_previewAssetPathForPalette(palette));
  }

  static Future<int> localAdaptiveOverrideCount() async {
    if (!kDebugMode) {
      return 0;
    }
    var count = 0;
    for (final fileName in _adaptiveLocalOverrideFiles.values.toSet()) {
      final file = File('$_localOverrideRoot/$fileName');
      if (await file.exists()) {
        count++;
      }
    }
    return count;
  }

  static Future<bool> hasLocalAdaptiveOverrides() async =>
      (await localAdaptiveOverrideCount()) > 0;

  static Future<void> _fadeTo(
    double target, {
    Duration duration = const Duration(milliseconds: 520),
    int steps = 12,
  }) async {
    final player = _player;
    if (player == null) {
      return;
    }

    final current = _currentOutputVolume;
    for (var i = 1; i <= steps; i++) {
      final t = Curves.easeInOutCubic.transform(i / steps);
      final next = current + (target - current) * t;
      await player.setVolume(next.clamp(0.0, 1.0));
      _currentOutputVolume = next.clamp(0.0, 1.0);
      await Future<void>.delayed(duration ~/ steps);
    }
  }

  static Future<void> _fadePlayerVolume(
    AudioPlayer player, {
    required double from,
    required double to,
    Duration duration = const Duration(milliseconds: 520),
    int steps = 12,
  }) async {
    for (var i = 1; i <= steps; i++) {
      final t = Curves.easeInOutCubic.transform(i / steps);
      final next = from + (to - from) * t;
      await player.setVolume(next.clamp(0.0, 1.0));
      await Future<void>.delayed(duration ~/ steps);
    }
  }

  static Duration _fadeDurationForTrack(
      BgmTrack? track, BgmPriority? priority) {
    if (track == BgmTrack.focusStart ||
        track == BgmTrack.focus ||
        track == BgmTrack.focusDeep) {
      return const Duration(milliseconds: 800);
    }
    switch (priority) {
      case BgmPriority.component:
        return const Duration(milliseconds: 200);
      case BgmPriority.stage:
        return const Duration(milliseconds: 300);
      case BgmPriority.route:
      case null:
        return const Duration(milliseconds: 500);
    }
  }

  static Future<void> _restorePersistentState() async {
    if (_persistentStateLoaded) {
      return;
    }
    final prefs = await _getPrefs();
    final savedPositionsRaw = prefs.getString(_savedPositionsKey);
    if (savedPositionsRaw != null && savedPositionsRaw.isNotEmpty) {
      final entries = savedPositionsRaw.split('|');
      for (final entry in entries) {
        final separator = entry.lastIndexOf('::');
        if (separator <= 0 || separator >= entry.length - 2) {
          continue;
        }
        final key = entry.substring(0, separator);
        final millis = int.tryParse(entry.substring(separator + 2));
        if (millis == null || millis <= 0) {
          continue;
        }
        _savedPositions[key] = Duration(milliseconds: millis);
      }
    }

    final playlistIndicesRaw = prefs.getString(_playlistIndicesKey);
    if (playlistIndicesRaw != null && playlistIndicesRaw.isNotEmpty) {
      final entries = playlistIndicesRaw.split('|');
      for (final entry in entries) {
        final separator = entry.indexOf('=');
        if (separator <= 0 || separator >= entry.length - 1) {
          continue;
        }
        final trackName = entry.substring(0, separator);
        final index = int.tryParse(entry.substring(separator + 1));
        if (index == null || index < 0) {
          continue;
        }
        final track = BgmTrack.values.where((value) => value.name == trackName);
        if (track.isNotEmpty) {
          _trackPlaylistIndices[track.first] = index;
        }
      }
    }
    _persistentStateLoaded = true;
  }

  static Future<void> _persistPlaybackState() async {
    final prefs = await _getPrefs();
    final savedPositions = _savedPositions.entries
        .where((entry) => entry.value > Duration.zero)
        .map((entry) => '${entry.key}::${entry.value.inMilliseconds}')
        .join('|');
    final playlistIndices = _trackPlaylistIndices.entries
        .map((entry) => '${entry.key.name}=${entry.value}')
        .join('|');
    await prefs.setString(_savedPositionsKey, savedPositions);
    await prefs.setString(_playlistIndicesKey, playlistIndices);
  }
}

class _BgmLifecycleObserver extends WidgetsBindingObserver {
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.inactive:
      case AppLifecycleState.hidden:
      case AppLifecycleState.paused:
      case AppLifecycleState.detached:
        unawaited(BgmService.pause());
        return;
      case AppLifecycleState.resumed:
        unawaited(BgmService.resume());
        return;
    }
  }
}
