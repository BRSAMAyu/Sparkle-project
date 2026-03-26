import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
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

enum BgmIntensity {
  gentle,
  balanced,
  lush,
}

enum BgmVariety {
  steady,
  balanced,
  dynamic,
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

@immutable
class BgmUserTuning {
  const BgmUserTuning({
    this.intensity = BgmIntensity.gentle,
    this.variety = BgmVariety.balanced,
    this.readingProtection = true,
    this.focusPriority = true,
    this.lockCurrentStyle = false,
  });

  final BgmIntensity intensity;
  final BgmVariety variety;
  final bool readingProtection;
  final bool focusPriority;
  final bool lockCurrentStyle;

  BgmUserTuning copyWith({
    BgmIntensity? intensity,
    BgmVariety? variety,
    bool? readingProtection,
    bool? focusPriority,
    bool? lockCurrentStyle,
  }) =>
      BgmUserTuning(
        intensity: intensity ?? this.intensity,
        variety: variety ?? this.variety,
        readingProtection: readingProtection ?? this.readingProtection,
        focusPriority: focusPriority ?? this.focusPriority,
        lockCurrentStyle: lockCurrentStyle ?? this.lockCurrentStyle,
      );
}

@immutable
class BgmCatalogEntry {
  const BgmCatalogEntry({
    required this.id,
    required this.assetPath,
    required this.album,
    required this.sceneTags,
    required this.paletteTags,
    required this.energy,
    required this.density,
    required this.baseGain,
    required this.loopable,
    required this.releaseApproved,
  });

  factory BgmCatalogEntry.fromJson(Map<String, dynamic> json) {
    double readNumber(Object? value, double fallback) {
      if (value is num) {
        return value.toDouble();
      }
      if (value is String) {
        return double.tryParse(value) ?? fallback;
      }
      return fallback;
    }

    List<String> readTags(Object? raw) {
      if (raw is List) {
        return raw.map((item) => item.toString()).toList(growable: false);
      }
      return const <String>[];
    }

    return BgmCatalogEntry(
      id: json['id']?.toString() ?? 'unknown',
      assetPath: json['assetPath']?.toString() ?? '',
      album: json['album']?.toString() ?? 'Bundled',
      sceneTags: readTags(json['sceneTags']),
      paletteTags: readTags(json['paletteTags']),
      energy: readNumber(json['energy'], 0.4).clamp(0.0, 1.0),
      density: readNumber(json['density'], 0.4).clamp(0.0, 1.0),
      baseGain: readNumber(json['baseGain'], 1.0).clamp(0.1, 1.2),
      loopable: json['loopable'] == true,
      releaseApproved: json['releaseApproved'] == true,
    );
  }

  final String id;
  final String assetPath;
  final String album;
  final List<String> sceneTags;
  final List<String> paletteTags;
  final double energy;
  final double density;
  final double baseGain;
  final bool loopable;
  final bool releaseApproved;

  String get title {
    final segments = id.split('_').where((segment) => segment.isNotEmpty);
    return segments
        .map((segment) =>
            '${segment[0].toUpperCase()}${segment.substring(1).toLowerCase()}')
        .join(' ');
  }
}

@immutable
class BgmSceneProfile {
  const BgmSceneProfile({
    required this.track,
    required this.name,
    required this.family,
    required this.sceneTags,
    required this.adjacentFamilies,
    this.readingFriendly = false,
    this.focusCritical = false,
    this.celebratory = false,
  });

  final BgmTrack track;
  final String name;
  final String family;
  final List<String> sceneTags;
  final List<String> adjacentFamilies;
  final bool readingFriendly;
  final bool focusCritical;
  final bool celebratory;

  bool get isCritical => focusCritical || celebratory;
}

@immutable
class BgmPlaybackSnapshot {
  const BgmPlaybackSnapshot({
    required this.enabled,
    required this.track,
    required this.scene,
    required this.sourceLabel,
    required this.selectionReason,
    required this.readingProtectionApplied,
    required this.focusPriorityApplied,
    required this.styleLocked,
    required this.palette,
    required this.intensity,
    required this.variety,
    this.trackId,
    this.assetPath,
    this.album,
  });

  final bool enabled;
  final BgmTrack? track;
  final BgmSceneProfile? scene;
  final String? trackId;
  final String? assetPath;
  final String? album;
  final String sourceLabel;
  final String selectionReason;
  final bool readingProtectionApplied;
  final bool focusPriorityApplied;
  final bool styleLocked;
  final BgmPalette palette;
  final BgmIntensity intensity;
  final BgmVariety variety;
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

class _ResolvedBgmSelection {
  const _ResolvedBgmSelection({
    required this.source,
    required this.scene,
    required this.sourceLabel,
    required this.reason,
    this.entry,
    this.readingProtectionApplied = false,
    this.focusPriorityApplied = false,
    this.styleLocked = false,
  });

  final _ResolvedBgmSource source;
  final BgmCatalogEntry? entry;
  final BgmSceneProfile scene;
  final String sourceLabel;
  final String reason;
  final bool readingProtectionApplied;
  final bool focusPriorityApplied;
  final bool styleLocked;
}

class BgmService {
  BgmService._();

  static const _catalogAssetBundlePath = 'assets/audio/bgm/bgm_catalog.json';
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
  static const _intensityKey = 'bgm.intensity';
  static const _varietyKey = 'bgm.variety';
  static const _readingProtectionKey = 'bgm.reading_protection';
  static const _focusPriorityKey = 'bgm.focus_priority';
  static const _lockCurrentStyleKey = 'bgm.lock_current_style';
  static const _savedPositionsKey = 'bgm.saved_positions_v2';
  static const _playlistIndicesKey = 'bgm.playlist_indices_v2';
  static const _sameFamilyRetention = Duration(seconds: 20);

  static AudioPlayer? _player;
  static AudioPlayer? _preloadPlayer;
  static SharedPreferences? _prefs;
  static final WidgetsBindingObserver _lifecycleObserver =
      _BgmLifecycleObserver();
  static final Map<Object, _BgmRegistration> _registrations = {};
  static final Set<String> _missingAssetPaths = <String>{};
  static final Map<String, Duration> _savedPositions = <String, Duration>{};
  static final Map<BgmTrack, int> _trackPlaylistIndices = <BgmTrack, int>{};
  static final List<String> _recentCatalogEntryIds = <String>[];
  static int _sequence = 0;
  static bool _isRefreshing = false;
  static bool _refreshQueued = false;
  static int _duckSequence = 0;
  static bool _observerRegistered = false;
  static bool _persistentStateLoaded = false;
  static bool _catalogLoaded = false;
  static List<BgmCatalogEntry>? _catalogOverride;
  static DateTime Function() _nowProvider = DateTime.now;
  static StreamSubscription<void>? _playerCompletionSubscription;
  static StreamSubscription<void>? _preloadCompletionSubscription;

  static BgmTrack? _currentTrack;
  static String? _currentSourceKey;
  static String? _preloadedSourceKey;
  static double _currentOutputVolume = 0;
  static double _manualDuckFactor = 1.0;
  static bool _readingActivityActive = false;
  static bool _thinkingActivityActive = false;
  static bool _focusSessionActive = false;
  static BgmSceneProfile? _currentSceneProfile;
  static BgmCatalogEntry? _currentCatalogEntry;
  static String _currentSourceLabel = 'Bundled fallback';
  static String _currentSelectionReason = '使用当前场景默认音乐';
  static bool _currentReadingProtectionApplied = false;
  static bool _currentFocusPriorityApplied = false;
  static bool _currentStyleLocked = false;
  static DateTime? _currentSceneStartedAt;

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
    await _playerCompletionSubscription?.cancel();
    await _preloadCompletionSubscription?.cancel();
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
    await _loadCatalogEntries();
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
      final target = await _targetVolume(
        _currentTrack!,
        entry: _currentCatalogEntry,
      );
      await player.setVolume(target);
      _currentOutputVolume = target;
    }
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

  static Future<BgmIntensity> getIntensity() async {
    final raw = (await _getPrefs()).getString(_intensityKey);
    return BgmIntensity.values.firstWhere(
      (value) => value.name == raw,
      orElse: () => BgmIntensity.gentle,
    );
  }

  static Future<BgmVariety> getVariety() async {
    final raw = (await _getPrefs()).getString(_varietyKey);
    return BgmVariety.values.firstWhere(
      (value) => value.name == raw,
      orElse: () => BgmVariety.balanced,
    );
  }

  static Future<BgmUserTuning> getUserTuning() async {
    final prefs = await _getPrefs();
    return BgmUserTuning(
      intensity: await getIntensity(),
      variety: await getVariety(),
      readingProtection: prefs.getBool(_readingProtectionKey) ?? true,
      focusPriority: prefs.getBool(_focusPriorityKey) ?? true,
      lockCurrentStyle: prefs.getBool(_lockCurrentStyleKey) ?? false,
    );
  }

  static Future<void> setUserTuning(BgmUserTuning tuning) async {
    final prefs = await _getPrefs();
    await Future.wait<void>(<Future<void>>[
      prefs.setString(_intensityKey, tuning.intensity.name),
      prefs.setString(_varietyKey, tuning.variety.name),
      prefs.setBool(_readingProtectionKey, tuning.readingProtection),
      prefs.setBool(_focusPriorityKey, tuning.focusPriority),
      prefs.setBool(_lockCurrentStyleKey, tuning.lockCurrentStyle),
    ]);
    await _refreshPlayback(force: true);
  }

  static Future<void> setIntensity(BgmIntensity intensity) async {
    await setUserTuning((await getUserTuning()).copyWith(intensity: intensity));
  }

  static Future<void> setVariety(BgmVariety variety) async {
    await setUserTuning((await getUserTuning()).copyWith(variety: variety));
  }

  static Future<void> setReadingProtection(bool enabled) async {
    await setUserTuning(
      (await getUserTuning()).copyWith(readingProtection: enabled),
    );
  }

  static Future<void> setFocusPriority(bool enabled) async {
    await setUserTuning(
      (await getUserTuning()).copyWith(focusPriority: enabled),
    );
  }

  static Future<void> setLockCurrentStyle(bool enabled) async {
    await setUserTuning(
      (await getUserTuning()).copyWith(lockCurrentStyle: enabled),
    );
  }

  static Future<BgmPlaybackSnapshot> currentPlaybackSnapshot() async {
    final tuning = await getUserTuning();
    return BgmPlaybackSnapshot(
      enabled: await isEnabled(),
      track: _currentTrack,
      scene: _currentSceneProfile,
      trackId: _currentCatalogEntry?.id,
      assetPath: _currentCatalogEntry?.assetPath ?? _currentSourceKey,
      album: _currentCatalogEntry?.album,
      sourceLabel: _currentSourceLabel,
      selectionReason: _currentSelectionReason,
      readingProtectionApplied: _currentReadingProtectionApplied,
      focusPriorityApplied: _currentFocusPriorityApplied,
      styleLocked: _currentStyleLocked,
      palette: await getPalette(),
      intensity: tuning.intensity,
      variety: tuning.variety,
    );
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

  static Future<void> setReadingActivity(
    bool active, {
    Duration duration = const Duration(milliseconds: 220),
  }) async {
    _readingActivityActive = active;
    await _applyDynamicMix(duration: duration);
  }

  static Future<void> setThinkingActivity(
    bool active, {
    Duration duration = const Duration(milliseconds: 220),
  }) async {
    _thinkingActivityActive = active;
    await _applyDynamicMix(duration: duration);
  }

  static Future<void> setFocusSession(
    bool active, {
    Duration duration = const Duration(milliseconds: 320),
  }) async {
    _focusSessionActive = active;
    await _applyDynamicMix(duration: duration);
  }

  static Future<void> setPersistentDuckFactor(
    double factor, {
    Duration duration = const Duration(milliseconds: 220),
  }) async {
    final normalized = factor.clamp(0.0, 1.0);
    if ((_manualDuckFactor - normalized).abs() < 0.001) {
      return;
    }
    _manualDuckFactor = normalized;
    await _applyDynamicMix(duration: duration);
  }

  static Future<void> previewPalette(
    BgmPalette palette, {
    Duration segmentDuration = const Duration(milliseconds: 1100),
  }) async {
    final player = AudioPlayer();
    try {
      await player.setReleaseMode(ReleaseMode.stop);
      for (final track in const <BgmTrack>[
        BgmTrack.dashboard,
        BgmTrack.chat,
        BgmTrack.focusDeep,
      ]) {
        final selection = await _resolveSelection(
          track,
          force: true,
          paletteOverride: palette,
        );
        await player.play(
          selection.source.source,
          volume: (0.60 * (selection.entry?.baseGain ?? 1.0)).clamp(0.15, 0.9),
          mode: PlayerMode.mediaPlayer,
        );
        await Future<void>.delayed(segmentDuration);
        await player.stop();
      }
    } catch (e) {
      if (kDebugMode) {
        debugPrint('BGM preview error for ${palette.name}: $e');
      }
    } finally {
      await player.dispose();
    }
  }

  static Future<void> previewSceneSample(
    BgmTrack track, {
    BgmPalette? palette,
    Duration duration = const Duration(milliseconds: 1200),
  }) async {
    final player = AudioPlayer();
    try {
      await player.setReleaseMode(ReleaseMode.stop);
      final selection = await _resolveSelection(
        track,
        force: true,
        paletteOverride: palette,
      );
      await player.play(
        selection.source.source,
        volume: 0.62,
        mode: PlayerMode.mediaPlayer,
      );
      await Future<void>.delayed(duration);
      await player.stop();
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
    final targetVolume = await _targetVolume(
      currentTrack,
      entry: _currentCatalogEntry,
    );
    final duckFactor = isBackNavigation ? 0.84 : 0.70;
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
    await _applyDynamicMix(duration: const Duration(milliseconds: 180));
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
    final targetVolume = await _targetVolume(
      currentTrack,
      entry: _currentCatalogEntry,
    );
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
    await _applyDynamicMix(duration: fadeDuration);
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
    final baseTarget = await _targetVolume(
      currentTrack,
      entry: _currentCatalogEntry,
    );
    final boosted = (baseTarget * factor).clamp(0.0, 1.0);

    await _fadeTo(boosted, duration: fadeDuration, steps: steps);
    await Future<void>.delayed(holdDuration);

    if (sequence != _duckSequence || _isRefreshing || _player == null) {
      return;
    }
    await _applyDynamicMix(duration: fadeDuration);
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
    _currentCatalogEntry = null;
    _currentSceneProfile = null;
    _currentSourceLabel = 'Bundled fallback';
    _currentSelectionReason = '使用当前场景默认音乐';
  }

  @visibleForTesting
  static void debugSetCatalogEntries(List<BgmCatalogEntry>? entries) {
    _catalogOverride = entries;
    _catalogLoaded = entries != null;
  }

  @visibleForTesting
  static void debugSetNowProvider(DateTime Function() provider) {
    _nowProvider = provider;
  }

  @visibleForTesting
  static Future<void> debugResetState() async {
    _catalogOverride = null;
    _catalogLoaded = false;
    _nowProvider = DateTime.now;
    _recentCatalogEntryIds.clear();
    _missingAssetPaths.clear();
    _manualDuckFactor = 1.0;
    _readingActivityActive = false;
    _thinkingActivityActive = false;
    _focusSessionActive = false;
    _currentCatalogEntry = null;
    _currentSceneProfile = null;
    _currentSourceKey = null;
    _currentTrack = null;
    _currentSceneStartedAt = null;
    _currentReadingProtectionApplied = false;
    _currentFocusPriorityApplied = false;
    _currentStyleLocked = false;
    _savedPositions.clear();
    _trackPlaylistIndices.clear();
    await dispose();
  }

  @visibleForTesting
  static void debugMarkAssetMissing(String assetPath) {
    _missingAssetPaths.add(assetPath);
  }

  @visibleForTesting
  static BgmSceneProfile debugSceneProfileForTrack(BgmTrack track) =>
      _sceneProfileForTrack(track);

  @visibleForTesting
  static void debugSeedCurrentSelection({
    required BgmTrack track,
    BgmCatalogEntry? entry,
    String? sourceKey,
    DateTime? startedAt,
  }) {
    _currentTrack = track;
    _currentSceneProfile = _sceneProfileForTrack(track);
    _currentCatalogEntry = entry;
    _currentSourceKey =
        sourceKey ?? 'asset:${entry?.assetPath ?? _fallbackBgmAssetPath}';
    _currentSceneStartedAt = startedAt ?? _nowProvider();
    _currentSourceLabel = entry?.album ?? 'Bundled fallback';
  }

  @visibleForTesting
  static BgmCatalogEntry? debugPickCatalogEntry({
    required List<BgmCatalogEntry> entries,
    required BgmTrack track,
    required BgmPalette palette,
    required BgmUserTuning tuning,
    List<String> recentIds = const <String>[],
    BgmCatalogEntry? currentEntry,
  }) =>
      _pickCatalogEntry(
        entries: entries,
        scene: _sceneProfileForTrack(track),
        palette: palette,
        tuning: tuning,
        recentIds: recentIds,
        currentEntry: currentEntry,
      );

  @visibleForTesting
  static Future<String> debugResolveSelectionReason(
    BgmTrack track, {
    bool force = false,
    BgmPalette? palette,
  }) async =>
      (await _resolveSelection(track, force: force, paletteOverride: palette))
          .reason;

  @visibleForTesting
  static Future<double> debugEffectiveDuckFactor() => _effectiveDuckFactor();

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
          await _fadeTo(0, duration: const Duration(milliseconds: 420));
          await _player!.stop();
        }
        _currentTrack = null;
        _currentCatalogEntry = null;
        _currentSceneProfile = null;
        _currentOutputVolume = 0;
        _currentSourceKey = null;
      } else if (!force && desiredTrack == _currentTrack) {
        await _applyDynamicMix(duration: const Duration(milliseconds: 180));
      } else {
        await _switchTrack(desiredTrack, force: force);
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

  static Future<void> _switchTrack(
    BgmTrack track, {
    bool force = false,
    bool allowRecovery = true,
  }) async {
    final activePlayer = _player;
    final standbyPlayer = _preloadPlayer;
    if (activePlayer == null || standbyPlayer == null) {
      return;
    }

    final previousScene = _currentSceneProfile;
    final selection = await _resolveSelection(track, force: force);
    final fadeDuration = _fadeDurationForTransition(
      from: previousScene,
      to: selection.scene,
    );

    if (_currentSourceKey == selection.source.cacheKey) {
      _currentTrack = track;
      _currentSceneProfile = selection.scene;
      _currentCatalogEntry = selection.entry;
      _currentSourceLabel = selection.sourceLabel;
      _currentSelectionReason = selection.reason;
      _currentReadingProtectionApplied = selection.readingProtectionApplied;
      _currentFocusPriorityApplied = selection.focusPriorityApplied;
      _currentStyleLocked = selection.styleLocked;
      _currentSceneStartedAt ??= _nowProvider();
      await activePlayer.resume();
      await _fadeTo(
        await _targetVolume(track, entry: selection.entry),
        duration: fadeDuration,
      );
      await _persistPlaybackState();
      return;
    }

    try {
      await _captureCurrentPlaybackPosition();
      await standbyPlayer.setReleaseMode(ReleaseMode.release);
      await standbyPlayer.play(
        selection.source.source,
        volume: 0,
        mode: PlayerMode.mediaPlayer,
      );
      final savedPosition = _savedPositions[selection.source.cacheKey];
      if (savedPosition != null && savedPosition > Duration.zero) {
        await standbyPlayer.seek(savedPosition);
      }
      final nextTargetVolume =
          await _targetVolume(track, entry: selection.entry);
      await Future.wait<void>(<Future<void>>[
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
      _currentTrack = track;
      _currentSourceKey = selection.source.cacheKey;
      _currentSceneProfile = selection.scene;
      _currentCatalogEntry = selection.entry;
      _currentSourceLabel = selection.sourceLabel;
      _currentSelectionReason = selection.reason;
      _currentReadingProtectionApplied = selection.readingProtectionApplied;
      _currentFocusPriorityApplied = selection.focusPriorityApplied;
      _currentStyleLocked = selection.styleLocked;
      _currentOutputVolume = nextTargetVolume;
      _currentSceneStartedAt = _nowProvider();
      _preloadedSourceKey = null;
      if (selection.entry != null) {
        _rememberCatalogEntry(selection.entry!.id);
      }
      await _persistPlaybackState();
    } catch (e) {
      if (selection.source.isAsset && _isAssetLoadFailure(e)) {
        _missingAssetPaths.add(selection.source.path);
        if (allowRecovery) {
          if (kDebugMode) {
            debugPrint(
              'BGM asset failed for ${track.name} (${selection.source.path}), retrying with fallback.',
            );
          }
          await _switchTrack(
            track,
            force: true,
            allowRecovery: false,
          );
          return;
        }
      } else if (kDebugMode) {
        debugPrint('BGM switch error for ${selection.source.path}: $e');
      }
      _currentTrack = null;
      _currentSourceKey = null;
      _currentCatalogEntry = null;
      _currentSceneProfile = null;
      _currentOutputVolume = 0;
    }
  }

  static bool _isAssetLoadFailure(Object error) {
    final message = error.toString();
    return message.contains('Unable to load asset') ||
        message.contains('Failed to set source') ||
        message.contains('Failed to load audio');
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

  static Future<double> _targetVolume(
    BgmTrack track, {
    BgmCatalogEntry? entry,
  }) async {
    final effectiveDuck = await _effectiveDuckFactor();
    return (await getVolume()) *
        track.mixVolume *
        (entry?.baseGain ?? 1.0) *
        effectiveDuck;
  }

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

  static Future<_ResolvedBgmSelection> _resolveSelection(
    BgmTrack track, {
    bool force = false,
    BgmPalette? paletteOverride,
  }) async {
    final scene = _sceneProfileForTrack(track);
    final palette = paletteOverride ?? await getPalette();
    final tuning = await getUserTuning();
    final localSelection = await _resolveLocalSelection(
      track,
      scene: scene,
      palette: palette,
    );
    if (localSelection != null) {
      return localSelection;
    }

    final retainedSelection = await _resolveRetainedSelection(
      scene,
      tuning: tuning,
      force: force,
    );
    if (retainedSelection != null) {
      return retainedSelection;
    }

    final entries = await _loadCatalogEntries();
    final entry = _pickCatalogEntry(
      entries: entries,
      scene: scene,
      palette: palette,
      tuning: tuning,
      recentIds: _recentCatalogEntryIds,
      currentEntry: _currentCatalogEntry,
    );
    if (entry != null && !_missingAssetPaths.contains(entry.assetPath)) {
      return _ResolvedBgmSelection(
        source: _ResolvedBgmSource.asset(entry.assetPath),
        entry: entry,
        scene: scene,
        sourceLabel: entry.album,
        reason: _buildSelectionReason(
          scene: scene,
          palette: palette,
          tuning: tuning,
          readingProtectionApplied:
              tuning.readingProtection && scene.readingFriendly,
          focusPriorityApplied: tuning.focusPriority && scene.focusCritical,
        ),
        readingProtectionApplied:
            tuning.readingProtection && scene.readingFriendly,
        focusPriorityApplied: tuning.focusPriority && scene.focusCritical,
      );
    }

    final source = await _resolvePlayableSource(
      track,
      paletteOverride: palette,
    );
    return _ResolvedBgmSelection(
      source: source,
      scene: scene,
      sourceLabel: 'Bundled fallback',
      reason: _buildSelectionReason(
        scene: scene,
        palette: palette,
        tuning: tuning,
        fallback: true,
        readingProtectionApplied:
            tuning.readingProtection && scene.readingFriendly,
        focusPriorityApplied: tuning.focusPriority && scene.focusCritical,
      ),
      readingProtectionApplied:
          tuning.readingProtection && scene.readingFriendly,
      focusPriorityApplied: tuning.focusPriority && scene.focusCritical,
    );
  }

  static Future<_ResolvedBgmSelection?> _resolveLocalSelection(
    BgmTrack track, {
    required BgmSceneProfile scene,
    required BgmPalette palette,
  }) async {
    final localPlaylist = await _resolveLocalOverridePlaylist(
      track,
      paletteOverride: palette,
    );
    if (localPlaylist.isEmpty) {
      return null;
    }
    final fileName = _selectPlaylistEntry(track, localPlaylist);
    final file = File('$_localOverrideRoot/$fileName');
    if (!await file.exists()) {
      return null;
    }
    return _ResolvedBgmSelection(
      source: _ResolvedBgmSource.device(file.path),
      scene: scene,
      sourceLabel: 'Local override',
      reason: '使用本机乐库覆盖当前场景音乐',
    );
  }

  static Future<_ResolvedBgmSelection?> _resolveRetainedSelection(
    BgmSceneProfile targetScene, {
    required BgmUserTuning tuning,
    required bool force,
  }) async {
    if (force || _currentSourceKey == null || _currentSceneProfile == null) {
      return null;
    }
    final currentScene = _currentSceneProfile!;
    if (_currentTrack == null) {
      return null;
    }

    if (tuning.lockCurrentStyle &&
        !currentScene.isCritical &&
        !targetScene.isCritical) {
      final currentSource = await _sourceForCurrentSelection();
      if (currentSource == null) {
        return null;
      }
      return _ResolvedBgmSelection(
        source: currentSource,
        entry: _currentCatalogEntry,
        scene: targetScene,
        sourceLabel: _currentSourceLabel,
        reason: '已锁定当前风格，延续当前音乐气质',
        readingProtectionApplied:
            tuning.readingProtection && targetScene.readingFriendly,
        focusPriorityApplied: false,
        styleLocked: true,
      );
    }

    final startedAt = _currentSceneStartedAt;
    final withinRetention = startedAt != null &&
        _nowProvider().difference(startedAt) <= _sameFamilyRetention;
    if (withinRetention && currentScene.family == targetScene.family) {
      final currentSource = await _sourceForCurrentSelection();
      if (currentSource == null) {
        return null;
      }
      return _ResolvedBgmSelection(
        source: currentSource,
        entry: _currentCatalogEntry,
        scene: targetScene,
        sourceLabel: _currentSourceLabel,
        reason: '同一氛围家族在 20 秒内延续当前音乐',
        readingProtectionApplied:
            tuning.readingProtection && targetScene.readingFriendly,
        focusPriorityApplied: tuning.focusPriority && targetScene.focusCritical,
      );
    }
    return null;
  }

  static Future<_ResolvedBgmSource?> _sourceForCurrentSelection() async {
    final currentSourceKey = _currentSourceKey;
    if (currentSourceKey == null) {
      return null;
    }
    final separator = currentSourceKey.indexOf(':');
    if (separator <= 0) {
      return null;
    }
    final kind = currentSourceKey.substring(0, separator);
    final path = currentSourceKey.substring(separator + 1);
    if (kind == 'asset') {
      return _ResolvedBgmSource.asset(path);
    }
    return _ResolvedBgmSource.device(path);
  }

  static BgmCatalogEntry? _pickCatalogEntry({
    required List<BgmCatalogEntry> entries,
    required BgmSceneProfile scene,
    required BgmPalette palette,
    required BgmUserTuning tuning,
    required List<String> recentIds,
    required BgmCatalogEntry? currentEntry,
  }) {
    final approvedEntries =
        entries.where((entry) => entry.releaseApproved).toList(growable: false);
    if (approvedEntries.isEmpty) {
      return null;
    }

    final sceneCandidates = approvedEntries.where((entry) {
      final tags = entry.sceneTags.toSet();
      return tags.contains(scene.family) ||
          tags.intersection(scene.sceneTags.toSet()).isNotEmpty;
    }).toList();
    final candidates =
        sceneCandidates.isNotEmpty ? sceneCandidates : approvedEntries;

    double intensityTargetEnergy(BgmIntensity intensity) => switch (intensity) {
          BgmIntensity.gentle => 0.28,
          BgmIntensity.balanced => 0.48,
          BgmIntensity.lush => 0.68,
        };

    double intensityTargetDensity(BgmIntensity intensity) =>
        switch (intensity) {
          BgmIntensity.gentle => 0.28,
          BgmIntensity.balanced => 0.46,
          BgmIntensity.lush => 0.64,
        };

    final targetEnergy = intensityTargetEnergy(tuning.intensity);
    final targetDensity = intensityTargetDensity(tuning.intensity);

    final scored = candidates.map((entry) {
      var score = 0.0;
      final tagSet = entry.sceneTags.toSet();
      final paletteSet = entry.paletteTags.toSet();
      score += 40.0 * tagSet.intersection(scene.sceneTags.toSet()).length;
      if (tagSet.contains(scene.family)) {
        score += 24.0;
      }
      if (paletteSet.contains(palette.name) ||
          paletteSet.contains('adaptive')) {
        score += 18.0;
      }
      score +=
          (1.0 - (entry.energy - targetEnergy).abs()).clamp(0.0, 1.0) * 16.0;
      score +=
          (1.0 - (entry.density - targetDensity).abs()).clamp(0.0, 1.0) * 14.0;

      if (tuning.readingProtection && scene.readingFriendly) {
        score += (1.0 - entry.density).clamp(0.0, 1.0) * 14.0;
        score += (1.0 - entry.energy).clamp(0.0, 1.0) * 8.0;
      }
      if (tuning.focusPriority && scene.focusCritical) {
        score += (1.0 - entry.energy).clamp(0.0, 1.0) * 12.0;
        score += (1.0 - entry.density).clamp(0.0, 1.0) * 12.0;
      }

      if (currentEntry != null && currentEntry.id == entry.id) {
        score += switch (tuning.variety) {
          BgmVariety.steady => 16.0,
          BgmVariety.balanced => 6.0,
          BgmVariety.dynamic => 0.0,
        };
      }
      if (recentIds.contains(entry.id)) {
        score -= switch (tuning.variety) {
          BgmVariety.steady => 10.0,
          BgmVariety.balanced => 18.0,
          BgmVariety.dynamic => 28.0,
        };
      }
      if (entry.loopable) {
        score += 3.0;
      }
      return MapEntry(entry, score);
    }).toList()
      ..sort((a, b) {
        final scoreCompare = b.value.compareTo(a.value);
        if (scoreCompare != 0) {
          return scoreCompare;
        }
        return a.key.id.compareTo(b.key.id);
      });

    return scored.isEmpty ? null : scored.first.key;
  }

  static String _buildSelectionReason({
    required BgmSceneProfile scene,
    required BgmPalette palette,
    required BgmUserTuning tuning,
    bool fallback = false,
    bool readingProtectionApplied = false,
    bool focusPriorityApplied = false,
  }) {
    final segments = <String>[
      '场景 ${scene.name}',
      switch (palette) {
        BgmPalette.adaptive => '自适应风格',
        BgmPalette.classical => '精选古典',
        BgmPalette.piano => '钢琴优先',
        BgmPalette.airy => '空灵氛围',
        BgmPalette.warm => '温暖轻快',
      },
      switch (tuning.intensity) {
        BgmIntensity.gentle => '柔和强度',
        BgmIntensity.balanced => '平衡强度',
        BgmIntensity.lush => '丰盈强度',
      },
      switch (tuning.variety) {
        BgmVariety.steady => '稳定轮换',
        BgmVariety.balanced => '均衡轮换',
        BgmVariety.dynamic => '灵动轮换',
      },
      if (readingProtectionApplied) '阅读保护',
      if (focusPriorityApplied) '专注优先',
      if (fallback) '内置兜底',
    ];
    return segments.join(' · ');
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
    if (playlist.length <= 1 && _currentCatalogEntry == null) {
      try {
        await player.seek(Duration.zero);
        await player.resume();
      } catch (_) {}
      return;
    }
    if (_currentCatalogEntry != null) {
      _rememberCatalogEntry(_currentCatalogEntry!.id);
    }
    final currentIndex = _trackPlaylistIndices[currentTrack] ?? 0;
    _trackPlaylistIndices[currentTrack] = (currentIndex + 1) % playlist.length;
    await _persistPlaybackState();
    await _refreshPlayback(force: true);
  }

  static void _rememberCatalogEntry(String id) {
    _recentCatalogEntryIds.remove(id);
    _recentCatalogEntryIds.insert(0, id);
    if (_recentCatalogEntryIds.length > 6) {
      _recentCatalogEntryIds.removeRange(6, _recentCatalogEntryIds.length);
    }
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
    BgmTrack track, {
    BgmPalette? paletteOverride,
  }) async {
    if (!kDebugMode || _localOverrideRoot.isEmpty) {
      return const <String>[];
    }
    final palette = paletteOverride ?? await getPalette();
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

  static Future<List<String>> _resolveAssetPlaylist(
    BgmTrack track, {
    BgmPalette? paletteOverride,
  }) async {
    final palette = paletteOverride ?? await getPalette();
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

  static Future<_ResolvedBgmSource> _resolvePlayableSource(
    BgmTrack track, {
    BgmPalette? paletteOverride,
  }) async {
    final localOverride = await _resolveLocalOverride(
      track,
      paletteOverride: paletteOverride,
    );
    if (localOverride != null) {
      return localOverride;
    }
    final assetPlaylist = await _resolveAssetPlaylist(
      track,
      paletteOverride: paletteOverride,
    );
    if (assetPlaylist.isNotEmpty) {
      final assetPath = _selectPlaylistEntry(track, assetPlaylist);
      if (!_missingAssetPaths.contains(assetPath)) {
        return _ResolvedBgmSource.asset(assetPath);
      }
    }
    return _ResolvedBgmSource.asset(
      await _resolvePlayableAssetPath(
        track,
        paletteOverride: paletteOverride,
      ),
    );
  }

  static Future<_ResolvedBgmSource?> _resolveLocalOverride(
    BgmTrack track, {
    BgmPalette? paletteOverride,
  }) async {
    if (!kDebugMode || _localOverrideRoot.isEmpty) {
      return null;
    }
    final palette = paletteOverride ?? await getPalette();
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

  static Future<String> _resolvePlayableAssetPath(
    BgmTrack track, {
    BgmPalette? paletteOverride,
  }) async {
    final primary =
        await _resolveAssetPath(track, paletteOverride: paletteOverride);
    if (!_missingAssetPaths.contains(primary)) {
      return primary;
    }
    return _fallbackBgmAssetPath;
  }

  static Future<String> _resolveAssetPath(
    BgmTrack track, {
    BgmPalette? paletteOverride,
  }) async {
    final palette = paletteOverride ?? await getPalette();
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

  static Future<void> _applyDynamicMix({
    Duration duration = const Duration(milliseconds: 220),
  }) async {
    final player = _player;
    final currentTrack = _currentTrack;
    if (player == null || currentTrack == null || _isRefreshing) {
      return;
    }
    await _fadeTo(
      await _targetVolume(currentTrack, entry: _currentCatalogEntry),
      duration: duration,
      steps: 5,
    );
  }

  static Future<double> _effectiveDuckFactor() async {
    final tuning = await getUserTuning();
    final factors = <double>[
      _manualDuckFactor,
      if (_readingActivityActive) tuning.readingProtection ? 0.62 : 0.78,
      if (_thinkingActivityActive) tuning.readingProtection ? 0.54 : 0.70,
      if (_focusSessionActive) tuning.focusPriority ? 0.82 : 0.90,
    ];
    return factors.fold<double>(
        1.0, (current, next) => current < next ? current : next);
  }

  static Future<List<BgmCatalogEntry>> _loadCatalogEntries() async {
    if (_catalogOverride != null) {
      return _catalogOverride!;
    }
    if (_catalogLoaded) {
      return _catalogOverride ?? const <BgmCatalogEntry>[];
    }
    _catalogLoaded = true;
    try {
      final raw = await rootBundle.loadString(_catalogAssetBundlePath);
      final decoded = jsonDecode(raw);
      final items = switch (decoded) {
        {'entries': final List<dynamic> entries} => entries,
        final List<dynamic> entries => entries,
        _ => const <dynamic>[],
      };
      _catalogOverride = items
          .whereType<Map<String, dynamic>>()
          .map(BgmCatalogEntry.fromJson)
          .toList(growable: false);
      return _catalogOverride!;
    } catch (e) {
      if (kDebugMode) {
        debugPrint('BGM catalog load failed: $e');
      }
      _catalogOverride = const <BgmCatalogEntry>[];
      return _catalogOverride!;
    }
  }

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

  static Duration _fadeDurationForTransition({
    required BgmSceneProfile? from,
    required BgmSceneProfile to,
  }) {
    if (to.focusCritical || to.celebratory) {
      return const Duration(milliseconds: 820);
    }
    if (from != null && from.family == to.family) {
      return const Duration(milliseconds: 240);
    }
    if (from != null &&
        (from.adjacentFamilies.contains(to.family) ||
            to.adjacentFamilies.contains(from.family))) {
      return const Duration(milliseconds: 420);
    }
    return const Duration(milliseconds: 500);
  }

  static BgmSceneProfile _sceneProfileForTrack(BgmTrack track) {
    switch (track) {
      case BgmTrack.dashboard:
        return const BgmSceneProfile(
          track: BgmTrack.dashboard,
          name: '首页',
          family: 'dashboard',
          sceneTags: <String>['dashboard', 'home', 'warm', 'stable'],
          adjacentFamilies: <String>['reflection', 'productivity'],
          readingFriendly: true,
        );
      case BgmTrack.plan:
        return const BgmSceneProfile(
          track: BgmTrack.plan,
          name: '计划',
          family: 'productivity',
          sceneTags: <String>['plan', 'calendar', 'task', 'structured'],
          adjacentFamilies: <String>['dashboard', 'focus', 'reflection'],
          readingFriendly: true,
        );
      case BgmTrack.chat:
        return const BgmSceneProfile(
          track: BgmTrack.chat,
          name: '聊天',
          family: 'reading',
          sceneTags: <String>['chat', 'reading', 'soft', 'assistant'],
          adjacentFamilies: <String>['dashboard', 'reflection'],
          readingFriendly: true,
        );
      case BgmTrack.community:
        return const BgmSceneProfile(
          track: BgmTrack.community,
          name: '社区',
          family: 'social',
          sceneTags: <String>['community', 'social', 'warm', 'light'],
          adjacentFamilies: <String>['dashboard', 'celebration'],
        );
      case BgmTrack.task:
        return const BgmSceneProfile(
          track: BgmTrack.task,
          name: '任务执行',
          family: 'productivity',
          sceneTags: <String>['task', 'focus', 'structured', 'flow'],
          adjacentFamilies: <String>['plan', 'focus', 'dashboard'],
          readingFriendly: true,
        );
      case BgmTrack.calendar:
        return const BgmSceneProfile(
          track: BgmTrack.calendar,
          name: '日历',
          family: 'productivity',
          sceneTags: <String>['calendar', 'plan', 'structured', 'light'],
          adjacentFamilies: <String>['dashboard', 'productivity'],
          readingFriendly: true,
        );
      case BgmTrack.achievement:
        return const BgmSceneProfile(
          track: BgmTrack.achievement,
          name: '成就',
          family: 'celebration',
          sceneTags: <String>['achievement', 'warm', 'uplift', 'celebration'],
          adjacentFamilies: <String>['social', 'dashboard'],
          celebratory: true,
        );
      case BgmTrack.galaxy:
        return const BgmSceneProfile(
          track: BgmTrack.galaxy,
          name: '星图',
          family: 'exploration',
          sceneTags: <String>['galaxy', 'space', 'exploration', 'airy'],
          adjacentFamilies: <String>['reflection', 'focus'],
          readingFriendly: true,
        );
      case BgmTrack.insights:
        return const BgmSceneProfile(
          track: BgmTrack.insights,
          name: '洞察',
          family: 'reflection',
          sceneTags: <String>['insights', 'reflective', 'mist', 'reading'],
          adjacentFamilies: <String>['dashboard', 'exploration', 'reading'],
          readingFriendly: true,
        );
      case BgmTrack.seeds:
        return const BgmSceneProfile(
          track: BgmTrack.seeds,
          name: '种子库',
          family: 'reflection',
          sceneTags: <String>['seeds', 'nature', 'growth', 'soft'],
          adjacentFamilies: <String>['insights', 'dashboard'],
          readingFriendly: true,
        );
      case BgmTrack.tools:
        return const BgmSceneProfile(
          track: BgmTrack.tools,
          name: '工具',
          family: 'productivity',
          sceneTags: <String>['tools', 'task', 'utility', 'structured'],
          adjacentFamilies: <String>['plan', 'focus', 'dashboard'],
          readingFriendly: true,
        );
      case BgmTrack.profile:
        return const BgmSceneProfile(
          track: BgmTrack.profile,
          name: '个人主页',
          family: 'reflection',
          sceneTags: <String>['profile', 'personal', 'reflective', 'soft'],
          adjacentFamilies: <String>['dashboard', 'reading'],
          readingFriendly: true,
        );
      case BgmTrack.focusStart:
        return const BgmSceneProfile(
          track: BgmTrack.focusStart,
          name: '专注准备',
          family: 'focus',
          sceneTags: <String>['focus', 'start', 'deep', 'minimal'],
          adjacentFamilies: <String>['productivity'],
          focusCritical: true,
        );
      case BgmTrack.focus:
        return const BgmSceneProfile(
          track: BgmTrack.focus,
          name: '专注',
          family: 'focus',
          sceneTags: <String>['focus', 'deep', 'minimal', 'binaural'],
          adjacentFamilies: <String>['focus', 'productivity'],
          focusCritical: true,
        );
      case BgmTrack.focusDeep:
        return const BgmSceneProfile(
          track: BgmTrack.focusDeep,
          name: '深度专注',
          family: 'focus',
          sceneTags: <String>['focus', 'deep', 'immersive', 'minimal'],
          adjacentFamilies: <String>['focus', 'productivity'],
          focusCritical: true,
        );
      case BgmTrack.thinking:
        return const BgmSceneProfile(
          track: BgmTrack.thinking,
          name: '思考中',
          family: 'reading',
          sceneTags: <String>['thinking', 'reading', 'soft', 'reflective'],
          adjacentFamilies: <String>['chat', 'insights'],
          readingFriendly: true,
        );
      case BgmTrack.celebration:
        return const BgmSceneProfile(
          track: BgmTrack.celebration,
          name: '庆祝',
          family: 'celebration',
          sceneTags: <String>['celebration', 'achievement', 'uplift', 'warm'],
          adjacentFamilies: <String>['social', 'dashboard'],
          celebratory: true,
        );
      case BgmTrack.visualUnlock:
        return const BgmSceneProfile(
          track: BgmTrack.visualUnlock,
          name: '视觉解锁',
          family: 'celebration',
          sceneTags: <String>['unlock', 'achievement', 'warm', 'uplift'],
          adjacentFamilies: <String>['social', 'dashboard'],
          celebratory: true,
        );
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
