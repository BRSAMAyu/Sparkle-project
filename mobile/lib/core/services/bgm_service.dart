import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum BgmPriority {
  route,
  stage,
  component,
}

enum BgmPalette {
  adaptive,
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
        BgmTrack.dashboard => 0.26,
        BgmTrack.plan => 0.24,
        BgmTrack.chat => 0.18,
        BgmTrack.community => 0.2,
        BgmTrack.task => 0.16,
        BgmTrack.calendar => 0.18,
        BgmTrack.achievement => 0.21,
        BgmTrack.galaxy => 0.18,
        BgmTrack.insights => 0.2,
        BgmTrack.tools => 0.16,
        BgmTrack.profile => 0.18,
        BgmTrack.focusStart => 0.16,
        BgmTrack.focus => 0.14,
        BgmTrack.focusDeep => 0.12,
        BgmTrack.thinking => 0.1,
        BgmTrack.celebration => 0.22,
        BgmTrack.visualUnlock => 0.18,
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

class BgmService {
  BgmService._();

  static const _enabledKey = 'bgm.enabled';
  static const _volumeKey = 'bgm.volume';
  static const _paletteKey = 'bgm.palette';
  static const _modeKey = 'bgm.mode';

  static AudioPlayer? _player;
  static SharedPreferences? _prefs;
  static final Map<Object, _BgmRegistration> _registrations = {};
  static int _sequence = 0;
  static bool _isRefreshing = false;
  static bool _refreshQueued = false;
  static int _duckSequence = 0;
  static BgmTrack? _currentTrack;
  static BgmPriority? _currentPriority;
  static double _currentOutputVolume = 0;

  static Future<void> init() async {
    if (_player != null) {
      return;
    }
    _player = AudioPlayer();
    await _player!.setReleaseMode(ReleaseMode.loop);
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
      (await _getPrefs()).getDouble(_volumeKey) ?? 0.68;

  static Future<void> setVolume(double volume) async {
    await (await _getPrefs()).setDouble(_volumeKey, volume.clamp(0.0, 1.0));
    if (_currentTrack != null && _player != null) {
      await _player!.setVolume(await _targetVolume(_currentTrack!));
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

  static Future<void> pause() async => _player?.pause();

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
    _registrations.clear();
    await _refreshPlayback(force: true);
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

  static Future<void> dispose() async {
    _registrations.clear();
    await _player?.dispose();
    _player = null;
    _currentTrack = null;
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
            duration: _fadeDurationForPriority(_currentPriority),
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
    final player = _player;
    if (player == null) {
      return;
    }

    final registration = _resolveRegistration();
    final fadeDuration = _fadeDurationForPriority(registration?.priority);

    await _fadeTo(0, duration: fadeDuration);
    await player.stop();
    await player.setReleaseMode(ReleaseMode.loop);
    await player.play(
      AssetSource(await _resolveAssetPath(track)),
      volume: 0,
      mode: PlayerMode.mediaPlayer,
    );
    _currentTrack = track;
    _currentPriority = registration?.priority;
    await _fadeTo(await _targetVolume(track), duration: fadeDuration);
  }

  static Future<double> _targetVolume(BgmTrack track) async =>
      (await getVolume()) * track.mixVolume;

  static Future<String> _resolveAssetPath(BgmTrack track) async {
    final palette = await getPalette();
    switch (track) {
      case BgmTrack.dashboard:
        return switch (palette) {
          BgmPalette.adaptive => 'audio/bgm/relax_background1.ogg',
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/oceanic_drift.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
        };
      case BgmTrack.plan:
        return switch (palette) {
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/heavenly_loop.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
          BgmPalette.adaptive => 'audio/bgm/sunset_walk.ogg',
        };
      case BgmTrack.chat:
        return switch (palette) {
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/oceanic_drift.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
          _ => 'audio/bgm/calm_track_loop.ogg',
        };
      case BgmTrack.community:
        return switch (palette) {
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/heavenly_loop.ogg',
          BgmPalette.warm => 'audio/bgm/loop_city.ogg',
          BgmPalette.adaptive => 'audio/bgm/loop_city.ogg',
        };
      case BgmTrack.task:
        return switch (palette) {
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/oceanic_drift.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
          BgmPalette.adaptive => 'audio/bgm/calm_track_loop.ogg',
        };
      case BgmTrack.calendar:
        return switch (palette) {
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/heavenly_loop.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
          BgmPalette.adaptive => 'audio/bgm/oceanic_drift.ogg',
        };
      case BgmTrack.achievement:
        return switch (palette) {
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/heavenly_loop.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
          BgmPalette.adaptive => 'audio/bgm/heavenly_loop.ogg',
        };
      case BgmTrack.galaxy:
        return switch (palette) {
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/oceanic_drift.ogg',
          BgmPalette.warm => 'audio/bgm/heavenly_loop.ogg',
          BgmPalette.adaptive => 'audio/bgm/heavenly_loop.ogg',
        };
      case BgmTrack.celebration:
        return switch (palette) {
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/heavenly_loop.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
          BgmPalette.adaptive => 'audio/bgm/heavenly_loop.ogg',
        };
      case BgmTrack.insights:
        return switch (palette) {
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/oceanic_drift.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
          _ => 'audio/bgm/relax_background1.ogg',
        };
      case BgmTrack.tools:
        return switch (palette) {
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/oceanic_drift.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
          BgmPalette.adaptive => 'audio/bgm/calm_track_loop.ogg',
        };
      case BgmTrack.profile:
        return switch (palette) {
          BgmPalette.airy => 'audio/bgm/heavenly_loop.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
          _ => 'audio/bgm/classical_piano_loop.ogg',
        };
      case BgmTrack.focusStart:
        return switch (palette) {
          BgmPalette.airy => 'audio/bgm/heavenly_loop.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.adaptive => 'audio/ambient/piano.ogg',
        };
      case BgmTrack.focus:
        return 'audio/ambient/piano.ogg';
      case BgmTrack.focusDeep:
        return 'audio/ambient/rain.ogg';
      case BgmTrack.thinking:
        return 'audio/ambient/piano.ogg';
      case BgmTrack.visualUnlock:
        return switch (palette) {
          BgmPalette.piano => 'audio/bgm/classical_piano_loop.ogg',
          BgmPalette.airy => 'audio/bgm/heavenly_loop.ogg',
          BgmPalette.warm => 'audio/bgm/sunset_walk.ogg',
          BgmPalette.adaptive => 'audio/bgm/heavenly_loop.ogg',
        };
    }
  }

  static Future<void> _fadeTo(
    double target, {
    Duration duration = const Duration(milliseconds: 420),
    int steps = 8,
  }) async {
    final player = _player;
    if (player == null) {
      return;
    }

    final current = _currentOutputVolume;
    for (var i = 1; i <= steps; i++) {
      final t = i / steps;
      final next = current + (target - current) * t;
      await player.setVolume(next.clamp(0.0, 1.0));
      _currentOutputVolume = next.clamp(0.0, 1.0);
      await Future<void>.delayed(duration ~/ steps);
    }
  }

  static Duration _fadeDurationForPriority(BgmPriority? priority) {
    switch (priority) {
      case BgmPriority.component:
        return const Duration(milliseconds: 260);
      case BgmPriority.stage:
        return const Duration(milliseconds: 380);
      case BgmPriority.route:
      case null:
        return const Duration(milliseconds: 560);
    }
  }
}
