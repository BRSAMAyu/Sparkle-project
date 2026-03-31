import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';

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
  continuous,
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

enum BgmLibrarySourceKind {
  curated,
  imported,
  bundled,
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
    this.title,
    this.artist,
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
      title: json['title']?.toString(),
      artist: json['artist']?.toString(),
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
  final String? title;
  final String? artist;

  String get displayTitle {
    if (title case final String explicitTitle when explicitTitle.isNotEmpty) {
      return explicitTitle;
    }
    final fromAssetPath = p.basenameWithoutExtension(assetPath);
    final descriptiveSegment =
        fromAssetPath.contains('__') ? fromAssetPath.split('__').last : id;
    final segments =
        descriptiveSegment.split('_').where((segment) => segment.isNotEmpty);
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
    this.trackTitle,
    this.artist,
    this.trackId,
    this.assetPath,
    this.album,
  });

  final bool enabled;
  final BgmTrack? track;
  final BgmSceneProfile? scene;
  final String? trackTitle;
  final String? artist;
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

@immutable
class BgmLibraryEntry {
  const BgmLibraryEntry({
    required this.id,
    required this.title,
    required this.album,
    required this.path,
    required this.sourceKind,
    required this.isAsset,
    required this.sceneTags,
    required this.paletteTags,
    required this.energy,
    required this.density,
    required this.baseGain,
    this.artist,
    this.addedAt,
  });

  final String id;
  final String title;
  final String album;
  final String path;
  final BgmLibrarySourceKind sourceKind;
  final bool isAsset;
  final List<String> sceneTags;
  final List<String> paletteTags;
  final double energy;
  final double density;
  final double baseGain;
  final String? artist;
  final DateTime? addedAt;

  String get sourceLabel => switch (sourceKind) {
        BgmLibrarySourceKind.curated => album,
        BgmLibrarySourceKind.imported => '本地导入',
        BgmLibrarySourceKind.bundled => '系统内置',
      };
}

@immutable
class BgmLibrarySnapshot {
  const BgmLibrarySnapshot({
    required this.entries,
    required this.curatedCount,
    required this.importedCount,
    required this.bundledCount,
    required this.importDirectoryPath,
    required this.downloadDirectoryPath,
  });

  final List<BgmLibraryEntry> entries;
  final int curatedCount;
  final int importedCount;
  final int bundledCount;
  final String importDirectoryPath;
  final String downloadDirectoryPath;

  int get totalCount => entries.length;
}

@immutable
class _BgmScenePlaybackState {
  const _BgmScenePlaybackState({
    required this.queueCursor,
    this.assetKey,
    this.trackId,
    this.position = Duration.zero,
    this.completed = false,
    this.lastUpdatedAt,
    this.palette,
    this.intensity,
    this.variety,
  });

  factory _BgmScenePlaybackState.fromJson(Map<String, dynamic> json) {
    DateTime? readTimestamp(Object? value) {
      if (value is String && value.isNotEmpty) {
        return DateTime.tryParse(value);
      }
      return null;
    }

    return _BgmScenePlaybackState(
      queueCursor: (json['queueCursor'] as num?)?.toInt() ?? 0,
      assetKey: json['assetKey']?.toString(),
      trackId: json['trackId']?.toString(),
      position: Duration(
        milliseconds: (json['positionMs'] as num?)?.toInt() ?? 0,
      ),
      completed: json['completed'] == true,
      lastUpdatedAt: readTimestamp(json['lastUpdatedAt']),
      palette: json['palette']?.toString(),
      intensity: json['intensity']?.toString(),
      variety: json['variety']?.toString(),
    );
  }

  final String? assetKey;
  final String? trackId;
  final Duration position;
  final int queueCursor;
  final bool completed;
  final DateTime? lastUpdatedAt;
  final String? palette;
  final String? intensity;
  final String? variety;

  _BgmScenePlaybackState copyWith({
    Object? assetKey = _unset,
    Object? trackId = _unset,
    Duration? position,
    int? queueCursor,
    bool? completed,
    Object? lastUpdatedAt = _unset,
    Object? palette = _unset,
    Object? intensity = _unset,
    Object? variety = _unset,
  }) =>
      _BgmScenePlaybackState(
        assetKey:
            identical(assetKey, _unset) ? this.assetKey : assetKey as String?,
        trackId: identical(trackId, _unset) ? this.trackId : trackId as String?,
        position: position ?? this.position,
        queueCursor: queueCursor ?? this.queueCursor,
        completed: completed ?? this.completed,
        lastUpdatedAt: identical(lastUpdatedAt, _unset)
            ? this.lastUpdatedAt
            : lastUpdatedAt as DateTime?,
        palette: identical(palette, _unset) ? this.palette : palette as String?,
        intensity: identical(intensity, _unset)
            ? this.intensity
            : intensity as String?,
        variety: identical(variety, _unset) ? this.variety : variety as String?,
      );

  Map<String, dynamic> toJson() => <String, dynamic>{
        'assetKey': assetKey,
        'trackId': trackId,
        'positionMs': position.inMilliseconds,
        'queueCursor': queueCursor,
        'completed': completed,
        'lastUpdatedAt': lastUpdatedAt?.toIso8601String(),
        'palette': palette,
        'intensity': intensity,
        'variety': variety,
      };

  bool matchesTuning({
    required BgmPalette palette,
    required BgmIntensity intensity,
    required BgmVariety variety,
  }) =>
      this.palette == palette.name &&
      this.intensity == intensity.name &&
      this.variety == variety.name;

  static const Object _unset = Object();
}

class _BgmRegistration {
  const _BgmRegistration({
    required this.track,
    required this.priority,
    required this.sequence,
    required this.switchBehavior,
  });

  final BgmTrack track;
  final BgmPriority priority;
  final int sequence;
  final SceneBgmSwitchBehavior switchBehavior;
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
    this.resumePosition = Duration.zero,
    this.readingProtectionApplied = false,
    this.focusPriorityApplied = false,
    this.styleLocked = false,
  });

  final _ResolvedBgmSource source;
  final BgmLibraryEntry? entry;
  final BgmSceneProfile scene;
  final String sourceLabel;
  final String reason;
  final Duration resumePosition;
  final bool readingProtectionApplied;
  final bool focusPriorityApplied;
  final bool styleLocked;
}

@immutable
class _ImportedBgmTrack {
  const _ImportedBgmTrack({
    required this.id,
    required this.filePath,
    required this.title,
    required this.album,
    required this.sceneTags,
    required this.paletteTags,
    required this.energy,
    required this.density,
    required this.baseGain,
    required this.addedAt,
    this.artist,
  });

  factory _ImportedBgmTrack.fromJson(Map<String, dynamic> json) {
    List<String> readTags(Object? raw) {
      if (raw is List) {
        return raw.map((item) => item.toString()).toList(growable: false);
      }
      return const <String>[];
    }

    return _ImportedBgmTrack(
      id: json['id']?.toString() ?? '',
      filePath: json['filePath']?.toString() ?? '',
      title: json['title']?.toString() ?? 'Imported Track',
      album: json['album']?.toString() ?? '本地导入',
      sceneTags: readTags(json['sceneTags']),
      paletteTags: readTags(json['paletteTags']),
      energy: ((json['energy'] as num?)?.toDouble() ?? 0.32).clamp(0.0, 1.0),
      density: ((json['density'] as num?)?.toDouble() ?? 0.24).clamp(0.0, 1.0),
      baseGain:
          ((json['baseGain'] as num?)?.toDouble() ?? 0.90).clamp(0.1, 1.2),
      addedAt: DateTime.tryParse(json['addedAt']?.toString() ?? '') ??
          DateTime.fromMillisecondsSinceEpoch(0),
      artist: json['artist']?.toString(),
    );
  }

  final String id;
  final String filePath;
  final String title;
  final String album;
  final List<String> sceneTags;
  final List<String> paletteTags;
  final double energy;
  final double density;
  final double baseGain;
  final DateTime addedAt;
  final String? artist;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'filePath': filePath,
        'title': title,
        'album': album,
        'sceneTags': sceneTags,
        'paletteTags': paletteTags,
        'energy': energy,
        'density': density,
        'baseGain': baseGain,
        'addedAt': addedAt.toIso8601String(),
        'artist': artist,
      };

  BgmLibraryEntry toLibraryEntry() => BgmLibraryEntry(
        id: id,
        title: title,
        album: album,
        path: filePath,
        sourceKind: BgmLibrarySourceKind.imported,
        isAsset: false,
        sceneTags: sceneTags,
        paletteTags: paletteTags,
        energy: energy,
        density: density,
        baseGain: baseGain,
        artist: artist,
        addedAt: addedAt,
      );
}

BgmLibraryEntry _libraryEntryFromCatalogEntry(BgmCatalogEntry entry) =>
    BgmLibraryEntry(
      id: entry.id,
      title: entry.displayTitle,
      album: entry.album,
      path: entry.assetPath,
      sourceKind: BgmLibrarySourceKind.curated,
      isAsset: true,
      sceneTags: entry.sceneTags,
      paletteTags: entry.paletteTags,
      energy: entry.energy,
      density: entry.density,
      baseGain: entry.baseGain,
      artist: entry.artist,
    );

class _BgmLibraryDirectories {
  const _BgmLibraryDirectories({
    required this.rootDirectory,
    required this.importDirectory,
    required this.downloadDirectory,
  });

  final Directory rootDirectory;
  final Directory importDirectory;
  final Directory downloadDirectory;
}

class BgmService {
  BgmService._();

  static const _catalogAssetBundlePath = 'assets/audio/bgm/bgm_catalog.json';
  static const _fallbackBgmAssetPath = 'audio/bgm/calm_track_loop.m4a';
  static const _dashboardAsset = 'audio/bgm/relax_background1.m4a';
  static const _warmAsset = 'audio/bgm/sunset_walk.m4a';
  static const _airyAsset = 'audio/bgm/oceanic_drift.m4a';
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
  static const _scenePlaybackStateKey = 'bgm.scene_playback_state_v3';
  static const _importedTracksKey = 'bgm.imported_tracks_v1';
  static const _libraryImportDirectoryName = 'imported';
  static const _libraryDownloadDirectoryName = 'downloads';

  static AudioPlayer? _player;
  static AudioPlayer? _preloadPlayer;
  static SharedPreferences? _prefs;
  static final WidgetsBindingObserver _lifecycleObserver =
      _BgmLifecycleObserver();
  static final Map<Object, _BgmRegistration> _registrations = {};
  static final Set<String> _missingAssetPaths = <String>{};
  static final Map<BgmTrack, _BgmScenePlaybackState> _scenePlaybackStates =
      <BgmTrack, _BgmScenePlaybackState>{};
  static int _sequence = 0;
  static bool _isRefreshing = false;
  static bool _refreshQueued = false;
  static bool _shutdownRequested = false;
  static int _duckSequence = 0;
  static bool _observerRegistered = false;
  static bool _persistentStateLoaded = false;
  static bool _catalogLoaded = false;
  static List<BgmCatalogEntry>? _catalogOverride;
  static bool _importedTracksLoaded = false;
  static List<_ImportedBgmTrack> _importedTracks = const <_ImportedBgmTrack>[];
  static bool? _preferBundledPlaybackOverride;
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
  static BgmLibraryEntry? _currentLibraryEntry;
  static String _currentSourceLabel = 'Bundled fallback';
  static String _currentSelectionReason = '使用当前场景默认音乐';
  static bool _currentReadingProtectionApplied = false;
  static bool _currentFocusPriorityApplied = false;
  static bool _currentStyleLocked = false;

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
      _dashboardAsset,
      _warmAsset,
      _thinkingAsset,
    ],
    BgmTrack.chat: <String>[
      _thinkingAsset,
      _dashboardAsset,
    ],
    BgmTrack.plan: <String>[
      _dashboardAsset,
      _thinkingAsset,
      _airyAsset,
    ],
    BgmTrack.task: <String>[
      _dashboardAsset,
      _thinkingAsset,
      _airyAsset,
    ],
    BgmTrack.calendar: <String>[
      _dashboardAsset,
      _airyAsset,
      _thinkingAsset,
    ],
    BgmTrack.community: <String>[
      _warmAsset,
      _dashboardAsset,
      _thinkingAsset,
    ],
    BgmTrack.achievement: <String>[
      _warmAsset,
      _airyAsset,
      _thinkingAsset,
    ],
    BgmTrack.galaxy: <String>[
      _airyAsset,
      _thinkingAsset,
      _dashboardAsset,
    ],
    BgmTrack.insights: <String>[
      _thinkingAsset,
      _dashboardAsset,
      _warmAsset,
    ],
    BgmTrack.seeds: <String>[
      _thinkingAsset,
      _dashboardAsset,
      _warmAsset,
    ],
    BgmTrack.tools: <String>[
      _dashboardAsset,
      _thinkingAsset,
      _airyAsset,
    ],
    BgmTrack.profile: <String>[
      _thinkingAsset,
      _warmAsset,
      _dashboardAsset,
    ],
    BgmTrack.focusStart: <String>[
      _airyAsset,
      _thinkingAsset,
      _fallbackBgmAssetPath,
    ],
    BgmTrack.focus: <String>[
      _airyAsset,
      _thinkingAsset,
      _fallbackBgmAssetPath,
    ],
    BgmTrack.focusDeep: <String>[
      _airyAsset,
      _thinkingAsset,
      _fallbackBgmAssetPath,
    ],
    BgmTrack.thinking: <String>[
      _thinkingAsset,
      _dashboardAsset,
      _airyAsset,
    ],
    BgmTrack.celebration: <String>[
      _warmAsset,
      _airyAsset,
      _thinkingAsset,
    ],
    BgmTrack.visualUnlock: <String>[
      _warmAsset,
      _airyAsset,
      _thinkingAsset,
    ],
  };

  static Future<void> init() async {
    _shutdownRequested = false;
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
        entry: _currentLibraryEntry,
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
      trackTitle: _currentLibraryEntry?.title,
      artist: _currentLibraryEntry?.artist,
      trackId: _currentLibraryEntry?.id,
      assetPath: _currentLibraryEntry?.path ?? _currentSourceKey,
      album: _currentLibraryEntry?.album,
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

  static Future<BgmLibrarySnapshot> librarySnapshot() async {
    final directories = await _ensureLibraryDirectories();
    final curatedEntries =
        (await _loadCatalogEntries()).map(_libraryEntryFromCatalogEntry).toList(
              growable: false,
            );
    final importedEntries = (await _loadImportedTracks())
        .map((entry) => entry.toLibraryEntry())
        .toList(growable: false);
    final bundledEntries = _bundledLibraryEntries();
    return BgmLibrarySnapshot(
      entries: <BgmLibraryEntry>[
        ...curatedEntries,
        ...importedEntries,
        ...bundledEntries,
      ],
      curatedCount: curatedEntries.length,
      importedCount: importedEntries.length,
      bundledCount: bundledEntries.length,
      importDirectoryPath: directories.importDirectory.path,
      downloadDirectoryPath: directories.downloadDirectory.path,
    );
  }

  static Future<List<BgmLibraryEntry>> libraryEntries() async =>
      (await librarySnapshot()).entries;

  static Future<List<BgmLibraryEntry>> importTracksFromPicker() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: true,
      type: FileType.custom,
      allowedExtensions: const <String>[
        'm4a',
        'aac',
        'mp3',
        'wav',
        'flac',
        'ogg',
      ],
    );
    if (result == null || result.files.isEmpty) {
      return const <BgmLibraryEntry>[];
    }

    final directories = await _ensureLibraryDirectories();
    final importedTracks =
        List<_ImportedBgmTrack>.from(await _loadImportedTracks());
    final importedEntries = <BgmLibraryEntry>[];
    final seenPaths = importedTracks.map((item) => item.filePath).toSet();

    for (final file in result.files) {
      final sourcePath = file.path;
      if (sourcePath == null || sourcePath.isEmpty) {
        continue;
      }
      final sourceFile = File(sourcePath);
      if (!await sourceFile.exists()) {
        continue;
      }
      final targetBaseName =
          _slugifyFileStem(p.basenameWithoutExtension(sourcePath));
      final extension = p.extension(sourcePath).toLowerCase();
      final targetPath = p.join(
        directories.importDirectory.path,
        '${DateTime.now().microsecondsSinceEpoch}_${targetBaseName.isEmpty ? 'track' : targetBaseName}$extension',
      );
      if (seenPaths.contains(targetPath)) {
        continue;
      }
      final copiedFile = await sourceFile.copy(targetPath);
      final importedTrack = _buildImportedTrackFromFile(copiedFile);
      importedTracks.add(importedTrack);
      importedEntries.add(importedTrack.toLibraryEntry());
      seenPaths.add(targetPath);
    }

    _importedTracks = importedTracks;
    _importedTracksLoaded = true;
    await _persistImportedTracks();
    await _refreshPlayback(force: true);
    return importedEntries;
  }

  static Future<void> removeImportedTrack(String id) async {
    final importedTracks =
        List<_ImportedBgmTrack>.from(await _loadImportedTracks());
    final targetIndex = importedTracks.indexWhere((entry) => entry.id == id);
    if (targetIndex < 0) {
      return;
    }
    final target = importedTracks.removeAt(targetIndex);
    try {
      final file = File(target.filePath);
      if (await file.exists()) {
        await file.delete();
      }
    } catch (_) {}
    _importedTracks = importedTracks;
    _importedTracksLoaded = true;
    await _persistImportedTracks();
    if (_currentLibraryEntry?.id == id) {
      _currentLibraryEntry = null;
      _currentSourceKey = null;
      await _refreshPlayback(force: true);
    }
  }

  static Future<void> playLibraryEntry(BgmLibraryEntry entry) async {
    await init();
    if (_shutdownRequested) {
      return;
    }
    final effectiveTrack = _currentTrack ?? BgmTrack.profile;
    final selection = _ResolvedBgmSelection(
      source: entry.isAsset
          ? _ResolvedBgmSource.asset(entry.path)
          : _ResolvedBgmSource.device(entry.path),
      entry: entry,
      scene: _sceneProfileForTrack(effectiveTrack),
      sourceLabel: entry.sourceLabel,
      reason: '手动播放曲库曲目',
    );
    await _switchToPreparedSelection(
      effectiveTrack,
      selection: selection,
      allowRecovery: false,
      switchBehavior: SceneBgmSwitchBehavior.keepPlaying,
    );
  }

  static Object activate(
    BgmTrack track, {
    BgmPriority priority = BgmPriority.route,
    SceneBgmSwitchBehavior switchBehavior =
        SceneBgmSwitchBehavior.switchOnEnter,
  }) {
    final token = Object();
    _registrations[token] = _BgmRegistration(
      track: track,
      priority: priority,
      sequence: ++_sequence,
      switchBehavior: switchBehavior,
    );
    unawaited(_refreshPlayback());
    return token;
  }

  static Future<void> update(
    Object token, {
    required BgmTrack track,
    BgmPriority priority = BgmPriority.route,
    SceneBgmSwitchBehavior switchBehavior =
        SceneBgmSwitchBehavior.switchOnEnter,
  }) async {
    if (!_registrations.containsKey(token)) {
      return;
    }
    _registrations[token] = _BgmRegistration(
      track: track,
      priority: priority,
      sequence: ++_sequence,
      switchBehavior: switchBehavior,
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
    if (kDebugMode &&
        (defaultTargetPlatform == TargetPlatform.iOS ||
            defaultTargetPlatform == TargetPlatform.android)) {
      return;
    }

    final sequence = ++_duckSequence;
    final targetVolume = await _targetVolume(
      currentTrack,
      entry: _currentLibraryEntry,
    );
    final duckFactor = isBackNavigation ? 0.84 : 0.70;
    final duckDuration = isBackNavigation
        ? const Duration(milliseconds: 90)
        : const Duration(milliseconds: 110);
    final settleDuration = isBackNavigation
        ? const Duration(milliseconds: 90)
        : const Duration(milliseconds: 130);

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
      entry: _currentLibraryEntry,
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
      entry: _currentLibraryEntry,
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
    _shutdownRequested = true;
    _registrations.clear();
    _refreshQueued = false;
    _isRefreshing = false;
    _duckSequence++;
    await _captureCurrentPlaybackPosition();
    if (_observerRegistered) {
      WidgetsBinding.instance.removeObserver(_lifecycleObserver);
      _observerRegistered = false;
    }
    await _playerCompletionSubscription?.cancel();
    await _preloadCompletionSubscription?.cancel();
    _playerCompletionSubscription = null;
    _preloadCompletionSubscription = null;
    try {
      await _player?.stop();
    } catch (_) {}
    try {
      await _preloadPlayer?.stop();
    } catch (_) {}
    await _player?.dispose();
    await _preloadPlayer?.dispose();
    _player = null;
    _preloadPlayer = null;
    _currentTrack = null;
    _currentSourceKey = null;
    _preloadedSourceKey = null;
    _currentLibraryEntry = null;
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
    _importedTracksLoaded = false;
    _importedTracks = const <_ImportedBgmTrack>[];
    _nowProvider = DateTime.now;
    _prefs = null;
    _persistentStateLoaded = false;
    _missingAssetPaths.clear();
    _manualDuckFactor = 1.0;
    _readingActivityActive = false;
    _thinkingActivityActive = false;
    _focusSessionActive = false;
    _currentLibraryEntry = null;
    _currentSceneProfile = null;
    _currentSourceKey = null;
    _currentTrack = null;
    _currentReadingProtectionApplied = false;
    _currentFocusPriorityApplied = false;
    _currentStyleLocked = false;
    _preferBundledPlaybackOverride = null;
    _scenePlaybackStates.clear();
    await dispose();
  }

  @visibleForTesting
  static void debugSetPreferBundledPlayback(bool? value) {
    _preferBundledPlaybackOverride = value;
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
    Duration position = Duration.zero,
    int queueCursor = 0,
    bool completed = false,
  }) {
    final resolvedSourceKey =
        sourceKey ?? 'asset:${entry?.assetPath ?? _fallbackBgmAssetPath}';
    _currentTrack = track;
    _currentSceneProfile = _sceneProfileForTrack(track);
    _currentLibraryEntry =
        entry == null ? null : _libraryEntryFromCatalogEntry(entry);
    _currentSourceKey = resolvedSourceKey;
    _currentSourceLabel = entry?.album ?? 'Bundled fallback';
    _scenePlaybackStates[track] = _buildScenePlaybackState(
      assetKey: resolvedSourceKey,
      trackId: entry?.id,
      position: position,
      queueCursor: queueCursor,
      completed: completed,
      palette: BgmPalette.adaptive,
      intensity: BgmIntensity.gentle,
      variety: BgmVariety.balanced,
    );
  }

  @visibleForTesting
  static void debugSeedSceneState({
    required BgmTrack track,
    BgmCatalogEntry? entry,
    String? sourceKey,
    Duration position = Duration.zero,
    int queueCursor = 0,
    bool completed = false,
    BgmPalette palette = BgmPalette.adaptive,
    BgmIntensity intensity = BgmIntensity.gentle,
    BgmVariety variety = BgmVariety.balanced,
  }) {
    final resolvedSourceKey =
        sourceKey ?? 'asset:${entry?.assetPath ?? _fallbackBgmAssetPath}';
    _scenePlaybackStates[track] = _buildScenePlaybackState(
      assetKey: resolvedSourceKey,
      trackId: entry?.id,
      position: position,
      queueCursor: queueCursor,
      completed: completed,
      palette: palette,
      intensity: intensity,
      variety: variety,
    );
  }

  @visibleForTesting
  static BgmCatalogEntry? debugPickCatalogEntry({
    required List<BgmCatalogEntry> entries,
    required BgmTrack track,
    required BgmPalette palette,
    required BgmUserTuning tuning,
  }) {
    final queue = _buildCatalogQueue(
      entries: entries,
      scene: _sceneProfileForTrack(track),
      palette: palette,
      tuning: tuning,
    );
    return queue.isEmpty ? null : queue.first;
  }

  @visibleForTesting
  static Future<String> debugResolveSelectionReason(
    BgmTrack track, {
    bool force = false,
    BgmPalette? palette,
    SceneBgmSwitchBehavior switchBehavior =
        SceneBgmSwitchBehavior.switchOnEnter,
  }) async =>
      (await _resolveSelection(
        track,
        force: force,
        paletteOverride: palette,
        switchBehavior: switchBehavior,
      ))
          .reason;

  @visibleForTesting
  static Future<String> debugResolveSelectionAssetPath(
    BgmTrack track, {
    bool force = false,
    BgmPalette? palette,
    SceneBgmSwitchBehavior switchBehavior =
        SceneBgmSwitchBehavior.switchOnEnter,
  }) async =>
      (await _resolveSelection(
        track,
        force: force,
        paletteOverride: palette,
        switchBehavior: switchBehavior,
      ))
          .source
          .path;

  @visibleForTesting
  static Map<String, Object?> debugSceneStateForTrack(BgmTrack track) {
    final state = _scenePlaybackStates[track];
    return <String, Object?>{
      'assetKey': state?.assetKey,
      'trackId': state?.trackId,
      'positionMs': state?.position.inMilliseconds,
      'queueCursor': state?.queueCursor,
      'completed': state?.completed,
      'palette': state?.palette,
      'intensity': state?.intensity,
      'variety': state?.variety,
    };
  }

  @visibleForTesting
  static List<String> debugCatalogQueueIds({
    required List<BgmCatalogEntry> entries,
    required BgmTrack track,
    required BgmPalette palette,
    required BgmUserTuning tuning,
  }) =>
      _buildCatalogQueue(
        entries: entries,
        scene: _sceneProfileForTrack(track),
        palette: palette,
        tuning: tuning,
      ).map((entry) => entry.id).toList(growable: false);

  @visibleForTesting
  static void debugAdvanceSceneQueue(
    BgmTrack track, {
    required int playlistLength,
    BgmVariety variety = BgmVariety.balanced,
  }) {
    _advanceSceneQueueCursor(
      track,
      queueLength: playlistLength,
      variety: variety,
    );
  }

  @visibleForTesting
  static Future<double> debugEffectiveDuckFactor() => _effectiveDuckFactor();

  static Future<void> _refreshPlayback({bool force = false}) async {
    if (_shutdownRequested) {
      return;
    }
    await init();
    if (_shutdownRequested) {
      return;
    }

    if (_isRefreshing) {
      _refreshQueued = true;
      return;
    }

    _isRefreshing = true;
    try {
      final desiredRegistration = await _resolveDesiredRegistration();
      final enabled = await isEnabled();

      if (!enabled || desiredRegistration == null) {
        if (_player != null) {
          await _captureCurrentPlaybackPosition();
          await _fadeTo(0, duration: const Duration(milliseconds: 420));
          if (_shutdownRequested || _player == null) {
            return;
          }
          await _player!.stop();
        }
        _currentTrack = null;
        _currentLibraryEntry = null;
        _currentSceneProfile = null;
        _currentOutputVolume = 0;
        _currentSourceKey = null;
      } else if (!force && desiredRegistration.track == _currentTrack) {
        await _applyDynamicMix(duration: const Duration(milliseconds: 180));
      } else {
        await _switchTrack(
          desiredRegistration.track,
          force: force,
          switchBehavior: desiredRegistration.switchBehavior,
        );
      }
      if (!_shutdownRequested && desiredRegistration != null) {
        unawaited(_preloadLikelyNextTrack(desiredRegistration.track));
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

  static Future<_BgmRegistration?> _resolveDesiredRegistration() async {
    final registration = _resolveRegistration();
    final mode = await getMode();
    if (mode == BgmMode.silent) {
      return null;
    }
    if (mode == BgmMode.continuous && _currentTrack != null) {
      return _BgmRegistration(
        track: _currentTrack!,
        priority: registration?.priority ?? BgmPriority.route,
        sequence: registration?.sequence ?? _sequence,
        switchBehavior: SceneBgmSwitchBehavior.keepPlaying,
      );
    }
    if (registration == null) {
      return null;
    }
    if (mode == BgmMode.focusOnly && !_isFocusTrack(registration.track)) {
      return null;
    }
    return registration;
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
    SceneBgmSwitchBehavior switchBehavior =
        SceneBgmSwitchBehavior.switchOnEnter,
  }) async {
    final selection = await _resolveSelection(
      track,
      force: force,
      switchBehavior: switchBehavior,
    );
    await _switchToPreparedSelection(
      track,
      selection: selection,
      allowRecovery: allowRecovery,
      switchBehavior: switchBehavior,
    );
  }

  static Future<void> _switchToPreparedSelection(
    BgmTrack track, {
    required _ResolvedBgmSelection selection,
    bool allowRecovery = true,
    SceneBgmSwitchBehavior switchBehavior =
        SceneBgmSwitchBehavior.switchOnEnter,
  }) async {
    if (_shutdownRequested) {
      return;
    }
    final activePlayer = _player;
    final standbyPlayer = _preloadPlayer;
    if (activePlayer == null || standbyPlayer == null) {
      return;
    }

    final previousScene = _currentSceneProfile;
    if (_shutdownRequested || _player == null || _preloadPlayer == null) {
      return;
    }
    final fadeDuration = _fadeDurationForTransition(
      from: previousScene,
      to: selection.scene,
    );

    if (_currentSourceKey == selection.source.cacheKey) {
      _currentTrack = track;
      _currentSceneProfile = selection.scene;
      _currentLibraryEntry = selection.entry;
      _currentSourceLabel = selection.sourceLabel;
      _currentSelectionReason = selection.reason;
      _currentReadingProtectionApplied = selection.readingProtectionApplied;
      _currentFocusPriorityApplied = selection.focusPriorityApplied;
      _currentStyleLocked = selection.styleLocked;
      if (selection.resumePosition > Duration.zero) {
        await activePlayer.seek(selection.resumePosition);
      }
      await activePlayer.resume();
      await _fadeTo(
        await _targetVolume(track, entry: selection.entry),
        duration: fadeDuration,
      );
      _saveScenePlaybackState(
        track,
        _buildScenePlaybackState(
          assetKey: selection.source.cacheKey,
          trackId: selection.entry?.id,
          position: selection.resumePosition,
          queueCursor: _sceneStateForTrack(track).queueCursor,
          completed: false,
          palette: await getPalette(),
          intensity: (await getUserTuning()).intensity,
          variety: (await getUserTuning()).variety,
        ),
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
      if (_shutdownRequested) {
        await standbyPlayer.stop();
        return;
      }
      if (selection.resumePosition > Duration.zero) {
        await standbyPlayer.seek(selection.resumePosition);
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
      _currentLibraryEntry = selection.entry;
      _currentSourceLabel = selection.sourceLabel;
      _currentSelectionReason = selection.reason;
      _currentReadingProtectionApplied = selection.readingProtectionApplied;
      _currentFocusPriorityApplied = selection.focusPriorityApplied;
      _currentStyleLocked = selection.styleLocked;
      _currentOutputVolume = nextTargetVolume;
      _preloadedSourceKey = null;
      _saveScenePlaybackState(
        track,
        _buildScenePlaybackState(
          assetKey: selection.source.cacheKey,
          trackId: selection.entry?.id,
          position: selection.resumePosition,
          queueCursor: _sceneStateForTrack(track).queueCursor,
          completed: false,
          palette: await getPalette(),
          intensity: (await getUserTuning()).intensity,
          variety: (await getUserTuning()).variety,
        ),
      );
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
            switchBehavior: switchBehavior,
          );
          return;
        }
        if (selection.source.path != _fallbackBgmAssetPath) {
          try {
            await _switchTrack(
              track,
              force: true,
              allowRecovery: false,
              switchBehavior: switchBehavior,
            );
            return;
          } catch (_) {}
        }
      } else if (kDebugMode) {
        debugPrint('BGM switch error for ${selection.source.path}: $e');
      }
      _currentTrack = null;
      _currentSourceKey = null;
      _currentLibraryEntry = null;
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
    if (_shutdownRequested) {
      return;
    }
    final preloadPlayer = _preloadPlayer;
    if (preloadPlayer == null) {
      return;
    }
    final nextTrack = _likelyNextTrack(currentTrack);
    if (nextTrack == null) {
      return;
    }
    final resolvedSource = (await _resolveSelection(
      nextTrack,
      switchBehavior: SceneBgmSwitchBehavior.switchOnEnter,
    ))
        .source;
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
    BgmLibraryEntry? entry,
  }) async {
    final effectiveDuck = await _effectiveDuckFactor();
    return (await getVolume()) *
        track.mixVolume *
        (entry?.baseGain ?? 1.0) *
        effectiveDuck;
  }

  static _BgmScenePlaybackState _sceneStateForTrack(BgmTrack track) =>
      _scenePlaybackStates[track] ??
      const _BgmScenePlaybackState(queueCursor: 0);

  static _BgmScenePlaybackState _buildScenePlaybackState({
    required String? assetKey,
    required String? trackId,
    required Duration position,
    required int queueCursor,
    required bool completed,
    required BgmPalette palette,
    required BgmIntensity intensity,
    required BgmVariety variety,
  }) =>
      _BgmScenePlaybackState(
        assetKey: assetKey,
        trackId: trackId,
        position: position,
        queueCursor: queueCursor,
        completed: completed,
        lastUpdatedAt: _nowProvider(),
        palette: palette.name,
        intensity: intensity.name,
        variety: variety.name,
      );

  static void _saveScenePlaybackState(
    BgmTrack track,
    _BgmScenePlaybackState state,
  ) {
    _scenePlaybackStates[track] = state;
  }

  static Future<void> _captureCurrentPlaybackPosition() async {
    if (_shutdownRequested) {
      return;
    }
    final player = _player;
    final currentTrack = _currentTrack;
    final sourceKey = _currentSourceKey;
    if (player == null || sourceKey == null || currentTrack == null) {
      return;
    }
    try {
      final position = await player.getCurrentPosition() ?? Duration.zero;
      final palette = await getPalette();
      final tuning = await getUserTuning();
      _saveScenePlaybackState(
        currentTrack,
        _buildScenePlaybackState(
          assetKey: sourceKey,
          trackId: _currentLibraryEntry?.id,
          position: position,
          queueCursor: _sceneStateForTrack(currentTrack).queueCursor,
          completed: false,
          palette: palette,
          intensity: tuning.intensity,
          variety: tuning.variety,
        ),
      );
      await _persistPlaybackState();
    } catch (_) {
      // Ignore progress snapshot failures and keep playback flowing.
    }
  }

  static Future<_ResolvedBgmSelection> _resolveSelection(
    BgmTrack track, {
    bool force = false,
    BgmPalette? paletteOverride,
    SceneBgmSwitchBehavior switchBehavior =
        SceneBgmSwitchBehavior.switchOnEnter,
  }) async {
    final scene = _sceneProfileForTrack(track);
    final palette = paletteOverride ?? await getPalette();
    final tuning = await getUserTuning();
    final sceneState = _sceneStateForTrack(track);

    if (!force) {
      final resumeSelection = await _resolveSceneResumeSelection(
        track,
        scene: scene,
        palette: palette,
        tuning: tuning,
        sceneState: sceneState,
      );
      if (resumeSelection != null) {
        return resumeSelection;
      }
    }

    final retainedSelection = await _resolveRetainedSelection(
      scene,
      tuning: tuning,
      force: force,
      switchBehavior: switchBehavior,
    );
    if (retainedSelection != null) {
      return retainedSelection;
    }

    final libraryQueue = await _buildPreferredLibraryQueue(
      scene: scene,
      palette: palette,
      tuning: tuning,
    );
    if (!_shouldPreferBundledPlayback() && libraryQueue.isNotEmpty) {
      final entry = libraryQueue[
          _queueCursorForLength(track, libraryQueue.length, tuning.variety)];
      return _ResolvedBgmSelection(
        source: entry.isAsset
            ? _ResolvedBgmSource.asset(entry.path)
            : _ResolvedBgmSource.device(entry.path),
        entry: entry,
        scene: scene,
        sourceLabel: entry.sourceLabel,
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

    final localSelection = await _resolveLocalSelection(
      track,
      scene: scene,
      palette: palette,
      tuning: tuning,
    );
    if (localSelection != null) {
      return localSelection;
    }

    final source = await _resolvePlayableSource(
      track,
      paletteOverride: palette,
      variety: tuning.variety,
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
    required BgmUserTuning tuning,
  }) async {
    final localPlaylist = await _resolveLocalOverridePlaylist(
      track,
      paletteOverride: palette,
    );
    if (localPlaylist.isEmpty) {
      return null;
    }
    final fileName = localPlaylist[
        _queueCursorForLength(track, localPlaylist.length, tuning.variety)];
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
    required SceneBgmSwitchBehavior switchBehavior,
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
        entry: _currentLibraryEntry,
        scene: targetScene,
        sourceLabel: _currentSourceLabel,
        reason: '已锁定当前风格，延续当前音乐气质',
        readingProtectionApplied:
            tuning.readingProtection && targetScene.readingFriendly,
        focusPriorityApplied: false,
        styleLocked: true,
      );
    }

    if (switchBehavior == SceneBgmSwitchBehavior.keepPlaying) {
      final currentSource = await _sourceForCurrentSelection();
      if (currentSource == null) {
        return null;
      }
      return _ResolvedBgmSelection(
        source: currentSource,
        entry: _currentLibraryEntry,
        scene: targetScene,
        sourceLabel: _currentSourceLabel,
        reason: '页面策略要求延续当前音乐',
        readingProtectionApplied:
            tuning.readingProtection && targetScene.readingFriendly,
        focusPriorityApplied: tuning.focusPriority && targetScene.focusCritical,
      );
    }

    final isAdjacentFamily = currentScene.family == targetScene.family ||
        currentScene.adjacentFamilies.contains(targetScene.family) ||
        targetScene.adjacentFamilies.contains(currentScene.family);
    if (switchBehavior == SceneBgmSwitchBehavior.retainIfAdjacent &&
        isAdjacentFamily) {
      final currentSource = await _sourceForCurrentSelection();
      if (currentSource == null) {
        return null;
      }
      return _ResolvedBgmSelection(
        source: currentSource,
        entry: _currentLibraryEntry,
        scene: targetScene,
        sourceLabel: _currentSourceLabel,
        reason: '相邻场景延续当前音乐',
        readingProtectionApplied:
            tuning.readingProtection && targetScene.readingFriendly,
        focusPriorityApplied: tuning.focusPriority && targetScene.focusCritical,
      );
    }
    return null;
  }

  static bool _shouldPreferBundledPlayback() {
    final override = _preferBundledPlaybackOverride;
    if (override != null) {
      return override;
    }
    return false;
  }

  static Future<_ResolvedBgmSource?> _sourceForCurrentSelection() async {
    final currentSourceKey = _currentSourceKey;
    if (currentSourceKey == null) {
      return null;
    }
    return _resolvedSourceFromCacheKey(currentSourceKey);
  }

  static _ResolvedBgmSource? _resolvedSourceFromCacheKey(String cacheKey) {
    final separator = cacheKey.indexOf(':');
    if (separator <= 0) {
      return null;
    }
    final kind = cacheKey.substring(0, separator);
    final path = cacheKey.substring(separator + 1);
    if (kind == 'asset') {
      return _ResolvedBgmSource.asset(path);
    }
    return _ResolvedBgmSource.device(path);
  }

  static Future<_ResolvedBgmSelection?> _resolveSceneResumeSelection(
    BgmTrack track, {
    required BgmSceneProfile scene,
    required BgmPalette palette,
    required BgmUserTuning tuning,
    required _BgmScenePlaybackState sceneState,
  }) async {
    if (sceneState.completed ||
        !sceneState.matchesTuning(
          palette: palette,
          intensity: tuning.intensity,
          variety: tuning.variety,
        )) {
      return null;
    }

    final readingProtectionApplied =
        tuning.readingProtection && scene.readingFriendly;
    final focusPriorityApplied = tuning.focusPriority && scene.focusCritical;
    final entries = await _libraryEntriesForSelection();

    if (sceneState.trackId case final String trackId) {
      for (final entry in entries) {
        if (entry.id == trackId &&
            (!entry.isAsset || !_missingAssetPaths.contains(entry.path))) {
          return _ResolvedBgmSelection(
            source: entry.isAsset
                ? _ResolvedBgmSource.asset(entry.path)
                : _ResolvedBgmSource.device(entry.path),
            entry: entry,
            scene: scene,
            sourceLabel: entry.sourceLabel,
            reason: '恢复 ${scene.name} 上次播放断点',
            resumePosition: sceneState.position,
            readingProtectionApplied: readingProtectionApplied,
            focusPriorityApplied: focusPriorityApplied,
          );
        }
      }
    }

    final assetKey = sceneState.assetKey;
    if (assetKey == null || assetKey.isEmpty) {
      return null;
    }
    final source = _resolvedSourceFromCacheKey(assetKey);
    if (source == null) {
      return null;
    }
    if (source.isAsset && _missingAssetPaths.contains(source.path)) {
      return null;
    }
    return _ResolvedBgmSelection(
      source: source,
      scene: scene,
      sourceLabel: _sourceLabelForResume(source, entries),
      reason: '恢复 ${scene.name} 上次播放断点',
      resumePosition: sceneState.position,
      readingProtectionApplied: readingProtectionApplied,
      focusPriorityApplied: focusPriorityApplied,
    );
  }

  static String _sourceLabelForResume(
    _ResolvedBgmSource source,
    List<BgmLibraryEntry> entries,
  ) {
    final matchedEntry = entries.where((entry) => entry.path == source.path);
    if (matchedEntry.isNotEmpty) {
      return matchedEntry.first.sourceLabel;
    }
    return source.isAsset ? '系统内置' : '本地导入';
  }

  static Future<List<BgmLibraryEntry>> _libraryEntriesForSelection() async {
    final curated =
        (await _loadCatalogEntries()).map(_libraryEntryFromCatalogEntry);
    final imported =
        (await _loadImportedTracks()).map((entry) => entry.toLibraryEntry());
    return <BgmLibraryEntry>[
      ...curated,
      ...imported,
    ];
  }

  static Future<List<BgmLibraryEntry>> _buildPreferredLibraryQueue({
    required BgmSceneProfile scene,
    required BgmPalette palette,
    required BgmUserTuning tuning,
  }) async =>
      _buildLibraryQueue(
        entries: await _libraryEntriesForSelection(),
        scene: scene,
        palette: palette,
        tuning: tuning,
      );

  static List<BgmLibraryEntry> _buildLibraryQueue({
    required Iterable<BgmLibraryEntry> entries,
    required BgmSceneProfile scene,
    required BgmPalette palette,
    required BgmUserTuning tuning,
  }) {
    final approvedEntries = entries.where((entry) {
      if (entry.isAsset) {
        return !_missingAssetPaths.contains(entry.path);
      }
      return File(entry.path).existsSync();
    }).toList(growable: false);
    if (approvedEntries.isEmpty) {
      return const <BgmLibraryEntry>[];
    }

    final sceneCandidates = approvedEntries.where((entry) {
      final tags = entry.sceneTags.toSet();
      return tags.contains(scene.family) ||
          tags.intersection(scene.sceneTags.toSet()).isNotEmpty;
    }).toList();
    final candidates =
        sceneCandidates.isNotEmpty ? sceneCandidates : approvedEntries;

    final scored = candidates.map((entry) {
      return MapEntry(
          entry, _scoreEntryForScene(entry, scene, palette, tuning));
    }).toList()
      ..sort((a, b) {
        final scoreCompare = b.value.compareTo(a.value);
        if (scoreCompare != 0) {
          return scoreCompare;
        }
        return a.key.id.compareTo(b.key.id);
      });
    return scored.map((item) => item.key).toList(growable: false);
  }

  static double _scoreEntryForScene(
    BgmLibraryEntry entry,
    BgmSceneProfile scene,
    BgmPalette palette,
    BgmUserTuning tuning,
  ) {
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
    var score = 0.0;
    final tagSet = entry.sceneTags.toSet();
    final paletteSet = entry.paletteTags.toSet();
    score += 40.0 * tagSet.intersection(scene.sceneTags.toSet()).length;
    if (tagSet.contains(scene.family)) {
      score += 24.0;
    }
    if (paletteSet.contains(palette.name) || paletteSet.contains('adaptive')) {
      score += 18.0;
    }
    score += (1.0 - (entry.energy - targetEnergy).abs()).clamp(0.0, 1.0) * 16.0;
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
    if (entry.sourceKind == BgmLibrarySourceKind.curated) {
      score += 3.0;
    }
    return score;
  }

  static List<BgmCatalogEntry> _buildCatalogQueue({
    required List<BgmCatalogEntry> entries,
    required BgmSceneProfile scene,
    required BgmPalette palette,
    required BgmUserTuning tuning,
  }) {
    final approvedEntries =
        entries.where((entry) => entry.releaseApproved).toList(growable: false);
    if (approvedEntries.isEmpty) {
      return const <BgmCatalogEntry>[];
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

    return scored.map((entry) => entry.key).toList(growable: false);
  }

  static int _queueCursorForLength(
    BgmTrack track,
    int queueLength,
    BgmVariety variety,
  ) {
    if (queueLength <= 0) {
      return 0;
    }
    final activeLength = _activeQueueLength(queueLength, variety);
    final cursor = _sceneStateForTrack(track).queueCursor;
    return activeLength <= 0 ? 0 : cursor % activeLength;
  }

  static void _advanceSceneQueueCursor(
    BgmTrack track, {
    required int queueLength,
    required BgmVariety variety,
  }) {
    if (queueLength <= 0) {
      return;
    }
    final state = _sceneStateForTrack(track);
    final activeLength = _activeQueueLength(queueLength, variety);
    final currentCursor =
        activeLength <= 0 ? 0 : state.queueCursor % activeLength;
    final nextCursor = activeLength <= 1
        ? 0
        : (currentCursor + _rotationStep(activeLength, variety)) % activeLength;
    _saveScenePlaybackState(
      track,
      state.copyWith(
        queueCursor: nextCursor,
        position: Duration.zero,
        completed: true,
        lastUpdatedAt: _nowProvider(),
      ),
    );
  }

  static int _activeQueueLength(int queueLength, BgmVariety variety) {
    if (queueLength <= 0) {
      return 0;
    }
    return switch (variety) {
      BgmVariety.steady => queueLength < 3 ? queueLength : 3,
      BgmVariety.balanced || BgmVariety.dynamic => queueLength,
    };
  }

  static int _rotationStep(int queueLength, BgmVariety variety) {
    if (queueLength <= 1 || variety != BgmVariety.dynamic) {
      return 1;
    }
    for (var candidate = queueLength - 1; candidate >= 2; candidate--) {
      if (_greatestCommonDivisor(candidate, queueLength) == 1) {
        return candidate;
      }
    }
    return 1;
  }

  static int _greatestCommonDivisor(int a, int b) {
    var left = a.abs();
    var right = b.abs();
    while (right != 0) {
      final next = left % right;
      left = right;
      right = next;
    }
    return left;
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
    if (_shutdownRequested || !identical(player, _player) || _isRefreshing) {
      return;
    }
    final currentTrack = _currentTrack;
    if (currentTrack == null) {
      return;
    }
    final tuning = await getUserTuning();
    final queueLength = await _queueLengthForTrack(
      currentTrack,
      paletteOverride: await getPalette(),
      tuning: tuning,
    );
    if (_currentLibraryEntry == null && queueLength <= 1) {
      try {
        await player.seek(Duration.zero);
        await player.resume();
      } catch (error, stackTrace) {
        debugPrint(
          'BgmService failed to restart single-track playback: $error',
        );
        debugPrintStack(stackTrace: stackTrace);
      }
      return;
    }
    _advanceSceneQueueCursor(
      currentTrack,
      queueLength: queueLength,
      variety: tuning.variety,
    );
    await _persistPlaybackState();
    await _refreshPlayback(force: true);
  }

  static Future<int> _queueLengthForTrack(
    BgmTrack track, {
    BgmPalette? paletteOverride,
    BgmUserTuning? tuning,
  }) async {
    final palette = paletteOverride ?? await getPalette();
    final resolvedTuning = tuning ?? await getUserTuning();
    if (!_shouldPreferBundledPlayback()) {
      final libraryQueue = await _buildPreferredLibraryQueue(
        scene: _sceneProfileForTrack(track),
        palette: palette,
        tuning: resolvedTuning,
      );
      if (libraryQueue.isNotEmpty) {
        return libraryQueue.length;
      }
    }
    final playlist = await _resolveEffectivePlaylist(
      track,
      paletteOverride: palette,
    );
    return playlist.length;
  }

  static Future<List<String>> _resolveEffectivePlaylist(
    BgmTrack track, {
    BgmPalette? paletteOverride,
  }) async {
    final localPlaylist = await _resolveLocalOverridePlaylist(
      track,
      paletteOverride: paletteOverride,
    );
    if (localPlaylist.isNotEmpty) {
      return localPlaylist;
    }
    final assetPlaylist = await _resolveAssetPlaylist(
      track,
      paletteOverride: paletteOverride,
    );
    if (assetPlaylist.isNotEmpty) {
      return assetPlaylist;
    }
    return <String>[
      await _resolvePlayableAssetPath(
        track,
        paletteOverride: paletteOverride,
      ),
    ];
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
    BgmVariety variety = BgmVariety.balanced,
  }) async {
    final assetPlaylist = await _resolveAssetPlaylist(
      track,
      paletteOverride: paletteOverride,
    );
    if (assetPlaylist.isNotEmpty) {
      final assetPath = assetPlaylist[
          _queueCursorForLength(track, assetPlaylist.length, variety)];
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
    final thinkingAsset = _platformThinkingAsset();
    switch (track) {
      case BgmTrack.dashboard:
        return switch (palette) {
          BgmPalette.adaptive => _dashboardAsset,
          BgmPalette.classical => _dashboardAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
        };
      case BgmTrack.plan:
        return switch (palette) {
          BgmPalette.classical => _dashboardAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _dashboardAsset,
        };
      case BgmTrack.chat:
        return switch (palette) {
          BgmPalette.classical => thinkingAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          _ => thinkingAsset,
        };
      case BgmTrack.community:
        return switch (palette) {
          BgmPalette.classical => _warmAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _dashboardAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _warmAsset,
        };
      case BgmTrack.task:
        return switch (palette) {
          BgmPalette.classical => _dashboardAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _dashboardAsset,
        };
      case BgmTrack.calendar:
        return switch (palette) {
          BgmPalette.classical => _dashboardAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _dashboardAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _dashboardAsset,
        };
      case BgmTrack.achievement:
        return switch (palette) {
          BgmPalette.classical => _warmAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _warmAsset,
        };
      case BgmTrack.galaxy:
        return switch (palette) {
          BgmPalette.classical => _airyAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _airyAsset,
        };
      case BgmTrack.celebration:
        return switch (palette) {
          BgmPalette.classical => _warmAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _warmAsset,
        };
      case BgmTrack.insights:
        return switch (palette) {
          BgmPalette.classical => thinkingAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          _ => thinkingAsset,
        };
      case BgmTrack.seeds:
        return switch (palette) {
          BgmPalette.classical => thinkingAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          _ => thinkingAsset,
        };
      case BgmTrack.tools:
        return switch (palette) {
          BgmPalette.classical => _dashboardAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _dashboardAsset,
        };
      case BgmTrack.profile:
        return switch (palette) {
          BgmPalette.classical => thinkingAsset,
          BgmPalette.airy => _dashboardAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.adaptive => thinkingAsset,
        };
      case BgmTrack.focusStart:
        return switch (palette) {
          BgmPalette.classical => _airyAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.adaptive => _airyAsset,
        };
      case BgmTrack.focus:
        return switch (palette) {
          BgmPalette.classical => _airyAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.warm => _warmAsset,
          _ => _airyAsset,
        };
      case BgmTrack.focusDeep:
        return switch (palette) {
          BgmPalette.classical => _airyAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.warm => _warmAsset,
          _ => _airyAsset,
        };
      case BgmTrack.thinking:
        return switch (palette) {
          BgmPalette.classical => thinkingAsset,
          BgmPalette.adaptive => thinkingAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
        };
      case BgmTrack.visualUnlock:
        return switch (palette) {
          BgmPalette.classical => _warmAsset,
          BgmPalette.piano => thinkingAsset,
          BgmPalette.airy => _airyAsset,
          BgmPalette.warm => _warmAsset,
          BgmPalette.adaptive => _warmAsset,
        };
    }
  }

  static String _platformThinkingAsset() {
    if (!kIsWeb && Platform.isAndroid) {
      return _dashboardAsset;
    }
    return _thinkingAsset;
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
    if (_shutdownRequested ||
        player == null ||
        currentTrack == null ||
        _isRefreshing) {
      return;
    }
    await _fadeTo(
      await _targetVolume(currentTrack, entry: _currentLibraryEntry),
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

  static Future<List<_ImportedBgmTrack>> _loadImportedTracks() async {
    if (_importedTracksLoaded) {
      return _importedTracks;
    }
    final prefs = await _getPrefs();
    final raw = prefs.getString(_importedTracksKey);
    if (raw == null || raw.isEmpty) {
      _importedTracksLoaded = true;
      _importedTracks = const <_ImportedBgmTrack>[];
      return _importedTracks;
    }
    try {
      final decoded = jsonDecode(raw);
      if (decoded is List) {
        _importedTracks = decoded
            .whereType<Map<String, dynamic>>()
            .map(_ImportedBgmTrack.fromJson)
            .toList(growable: false);
      } else {
        _importedTracks = const <_ImportedBgmTrack>[];
      }
    } catch (_) {
      _importedTracks = const <_ImportedBgmTrack>[];
    }
    _importedTracksLoaded = true;
    return _importedTracks;
  }

  static Future<void> _persistImportedTracks() async {
    final prefs = await _getPrefs();
    await prefs.setString(
      _importedTracksKey,
      jsonEncode(_importedTracks.map((entry) => entry.toJson()).toList()),
    );
  }

  static Future<_BgmLibraryDirectories> _ensureLibraryDirectories() async {
    final root = await getApplicationDocumentsDirectory();
    final bgmRoot = Directory(p.join(root.path, 'bgm_library'));
    final importDirectory =
        Directory(p.join(bgmRoot.path, _libraryImportDirectoryName));
    final downloadDirectory =
        Directory(p.join(bgmRoot.path, _libraryDownloadDirectoryName));
    if (!await bgmRoot.exists()) {
      await bgmRoot.create(recursive: true);
    }
    if (!await importDirectory.exists()) {
      await importDirectory.create(recursive: true);
    }
    if (!await downloadDirectory.exists()) {
      await downloadDirectory.create(recursive: true);
    }
    return _BgmLibraryDirectories(
      rootDirectory: bgmRoot,
      importDirectory: importDirectory,
      downloadDirectory: downloadDirectory,
    );
  }

  static _ImportedBgmTrack _buildImportedTrackFromFile(File file) {
    final fileStem = p.basenameWithoutExtension(file.path);
    final normalizedStem = fileStem.replaceFirst(RegExp(r'^\d+_'), '');
    final title = normalizedStem
        .split(RegExp(r'[_-]+'))
        .where((part) => part.isNotEmpty)
        .map((part) => '${part[0].toUpperCase()}${part.substring(1)}')
        .join(' ');
    return _ImportedBgmTrack(
      id: 'imported_${_slugifyFileStem(fileStem)}_${file.lengthSync()}',
      filePath: file.path,
      title: title.isEmpty ? 'Imported Track' : title,
      album: '本地导入',
      sceneTags: const <String>[
        'dashboard',
        'reading',
        'reflection',
        'chat',
        'insights',
        'profile',
        'plan',
        'task',
        'calendar',
        'focus',
        'warm',
      ],
      paletteTags: const <String>[
        'adaptive',
        'classical',
        'piano',
        'airy',
        'warm',
      ],
      energy: 0.30,
      density: 0.24,
      baseGain: 0.90,
      addedAt: _nowProvider(),
    );
  }

  static String _slugifyFileStem(String raw) => raw
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '_')
      .replaceAll(RegExp(r'^_+|_+$'), '');

  static List<BgmLibraryEntry> _bundledLibraryEntries() {
    final seenPaths = <String>{};
    final base = <BgmLibraryEntry>[
      _bundledEntry(
        id: 'bundled_relax_background1',
        title: 'Relax Background',
        path: _dashboardAsset,
        sceneTags: const <String>['dashboard', 'home', 'warm', 'stable'],
        paletteTags: const <String>['adaptive', 'classical', 'warm'],
      ),
      _bundledEntry(
        id: 'bundled_sunset_walk',
        title: 'Sunset Walk',
        path: _warmAsset,
        sceneTags: const <String>['warm', 'community', 'celebration'],
        paletteTags: const <String>['adaptive', 'warm'],
      ),
      _bundledEntry(
        id: 'bundled_oceanic_drift',
        title: 'Oceanic Drift',
        path: _airyAsset,
        sceneTags: const <String>['focus', 'insights', 'galaxy'],
        paletteTags: const <String>['adaptive', 'airy'],
      ),
      _bundledEntry(
        id: 'bundled_thinking',
        title: 'Thinking',
        path: _thinkingAsset,
        sceneTags: const <String>['chat', 'reading', 'insights'],
        paletteTags: const <String>['adaptive', 'piano'],
      ),
      _bundledEntry(
        id: 'bundled_calm_track_loop',
        title: 'Calm Track Loop',
        path: _fallbackBgmAssetPath,
        sceneTags: const <String>['focus', 'task', 'dashboard'],
        paletteTags: const <String>['adaptive', 'classical'],
      ),
      ..._adaptiveLocalOverrideFiles.entries.map(
        (entry) => _bundledEntry(
          id: 'bundled_${entry.key.name}',
          title: _humanizeTrackName(entry.key.name),
          path: 'audio/bgm/${entry.value}',
          sceneTags: _sceneProfileForTrack(entry.key).sceneTags,
          paletteTags: const <String>['adaptive', 'classical', 'piano'],
        ),
      ),
      _bundledEntry(
        id: 'bundled_heavenly_loop',
        title: 'Heavenly Loop',
        path: 'audio/bgm/heavenly_loop.m4a',
        sceneTags: const <String>['focus', 'insights'],
        paletteTags: const <String>['airy', 'adaptive'],
      ),
      _bundledEntry(
        id: 'bundled_loop_city',
        title: 'Loop City',
        path: 'audio/bgm/loop_city.m4a',
        sceneTags: const <String>['dashboard', 'community'],
        paletteTags: const <String>['warm', 'adaptive'],
      ),
      _bundledEntry(
        id: 'bundled_classical_piano_loop',
        title: 'Classical Piano Loop',
        path: 'audio/bgm/classical_piano_loop.m4a',
        sceneTags: const <String>['plan', 'task', 'calendar'],
        paletteTags: const <String>['classical', 'piano', 'adaptive'],
      ),
    ];
    return base
        .where((entry) => seenPaths.add(entry.path))
        .toList(growable: false);
  }

  static BgmLibraryEntry _bundledEntry({
    required String id,
    required String title,
    required String path,
    required List<String> sceneTags,
    required List<String> paletteTags,
  }) =>
      BgmLibraryEntry(
        id: id,
        title: title,
        album: '系统内置',
        path: path,
        sourceKind: BgmLibrarySourceKind.bundled,
        isAsset: true,
        sceneTags: sceneTags,
        paletteTags: paletteTags,
        energy: 0.34,
        density: 0.28,
        baseGain: 1.0,
      );

  static String _humanizeTrackName(String raw) => raw
      .replaceAllMapped(
        RegExp(r'([a-z])([A-Z])'),
        (match) => '${match.group(1)} ${match.group(2)}',
      )
      .split('_')
      .map((part) =>
          part.isEmpty ? part : '${part[0].toUpperCase()}${part.substring(1)}')
      .join(' ');

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
    if (_shutdownRequested || player == null) {
      return;
    }

    final current = _currentOutputVolume;
    for (var i = 1; i <= steps; i++) {
      if (_shutdownRequested || !identical(player, _player)) {
        return;
      }
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
      if (_shutdownRequested) {
        return;
      }
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
    final raw = prefs.getString(_scenePlaybackStateKey);
    if (raw != null && raw.isNotEmpty) {
      try {
        final decoded = jsonDecode(raw);
        if (decoded is Map<String, dynamic>) {
          for (final entry in decoded.entries) {
            final track =
                BgmTrack.values.where((value) => value.name == entry.key);
            if (track.isEmpty) {
              continue;
            }
            final payload = entry.value;
            if (payload is Map<String, dynamic>) {
              _scenePlaybackStates[track.first] =
                  _BgmScenePlaybackState.fromJson(payload);
            } else if (payload is Map) {
              _scenePlaybackStates[track.first] =
                  _BgmScenePlaybackState.fromJson(
                Map<String, dynamic>.from(payload),
              );
            }
          }
        }
      } catch (_) {
        _scenePlaybackStates.clear();
      }
    }
    _persistentStateLoaded = true;
  }

  static Future<void> _persistPlaybackState() async {
    final prefs = await _getPrefs();
    final payload = <String, Map<String, dynamic>>{};
    for (final entry in _scenePlaybackStates.entries) {
      payload[entry.key.name] = entry.value.toJson();
    }
    await prefs.setString(_scenePlaybackStateKey, jsonEncode(payload));
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
