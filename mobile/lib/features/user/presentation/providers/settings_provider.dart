import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';

/// Key for storing 'Enter to Send' preference in SharedPreferences
const String kEnterToSendKey = 'settings_enter_to_send';
const String kTransparentModeKey = 'settings_transparent_mode';
const String kTransparencyLevelKey = 'settings_transparency_level';
const String kOnboardingCompletedKey = 'settings_onboarding_completed';
const String kSystemUpdateLevelKey = 'settings_system_update_level';

/// Provider to manage the 'Enter to Send' preference
final enterToSendProvider = StateNotifierProvider<EnterToSendNotifier, bool>(
    (ref) => EnterToSendNotifier(),);

final transparencyLevelProvider =
    StateNotifierProvider<TransparencyLevelNotifier, int>(
        (ref) => TransparencyLevelNotifier(ref),);

final transparentModeProvider = Provider<bool>(
  (ref) => ref.watch(transparencyLevelProvider) > 0,
);

final onboardingCompletedProvider =
    StateNotifierProvider<OnboardingCompletedNotifier, bool>(
        (ref) => OnboardingCompletedNotifier(),);

final systemUpdateLevelProvider =
    StateNotifierProvider<SystemUpdateLevelNotifier, int>(
        (ref) => SystemUpdateLevelNotifier(ref),);

class EnterToSendNotifier extends StateNotifier<bool> {
  EnterToSendNotifier() : super(false) {
    _loadSettings();
  }

  /// Load saved setting from SharedPreferences
  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final enabled = prefs.getBool(kEnterToSendKey);
      if (enabled != null) {
        state = enabled;
      }
    } catch (_) {
      // Default to false
      state = false;
    }
  }

  /// Update and persist the setting
  Future<void> setEnabled(bool enabled) async {
    if (state == enabled) return;

    state = enabled;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(kEnterToSendKey, enabled);
    } catch (_) {
      // Silent fail for persistence
    }
  }

  /// Toggle the setting
  void toggle() {
    setEnabled(!state);
  }
}

class TransparencyLevelNotifier extends StateNotifier<int> {
  TransparencyLevelNotifier(this._ref) : super(0) {
    _ref.listen<AuthState>(authProvider, (prev, next) {
      if (next.user != null && prev?.user?.id != next.user?.id) {
        _syncFromServer();
      }
    });
    _loadSettings();
  }

  final Ref _ref;

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final level = prefs.getInt(kTransparencyLevelKey);
      if (level != null) {
        state = level;
      } else {
        final enabled = prefs.getBool(kTransparentModeKey);
        if (enabled != null) {
          state = enabled ? 1 : 0;
          await prefs.setInt(kTransparencyLevelKey, state);
        }
      }
    } catch (_) {
      state = 0;
    }
    await _syncFromServer();
  }

  Future<void> setLevel(int level) async {
    if (state == level) return;
    state = level;
    await _persist(level);
    await _syncToServer(level: level);
  }

  Future<void> _persist(int level) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(kTransparencyLevelKey, level);
      await prefs.setBool(kTransparentModeKey, level > 0);
    } catch (_) {
      // Silent fail for persistence
    }
  }

  Future<void> _syncFromServer() async {
    final user = _ref.read(authProvider).user;
    if (user == null) return;
    try {
      final repo = _ref.read(userRepositoryProvider);
      final settings = await repo.fetchUserSettings();
      final level = settings['transparency_level'] as int?;
      if (level != null && level != state) {
        state = level;
        await _persist(level);
      }
    } catch (_) {
      // Silent fail
    }
  }

  Future<void> _syncToServer({int? level}) async {
    final user = _ref.read(authProvider).user;
    if (user == null) return;
    try {
      final repo = _ref.read(userRepositoryProvider);
      await repo.updateUserSettings({
        if (level != null) "transparency_level": level,
      });
    } catch (_) {
      // Silent fail
    }
  }
}

class OnboardingCompletedNotifier extends StateNotifier<bool> {
  OnboardingCompletedNotifier() : super(false) {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final enabled = prefs.getBool(kOnboardingCompletedKey);
      if (enabled != null) {
        state = enabled;
      }
    } catch (_) {
      state = false;
    }
  }

  Future<void> setCompleted(bool value) async {
    if (state == value) return;
    state = value;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(kOnboardingCompletedKey, value);
    } catch (_) {
      // Silent fail for persistence
    }
  }
}

class SystemUpdateLevelNotifier extends StateNotifier<int> {
  SystemUpdateLevelNotifier(this._ref) : super(1) {
    _ref.listen<AuthState>(authProvider, (prev, next) {
      if (next.user != null && prev?.user?.id != next.user?.id) {
        _syncFromServer();
      }
    });
    _loadSettings();
  }

  final Ref _ref;

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final value = prefs.getInt(kSystemUpdateLevelKey);
      if (value != null) {
        state = value;
      }
    } catch (_) {
      state = 1;
    }
    await _syncFromServer();
  }

  Future<void> setLevel(int level) async {
    if (state == level) return;
    state = level;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(kSystemUpdateLevelKey, level);
    } catch (_) {
      // Silent fail
    }
    await _syncToServer(level: level);
  }

  Future<void> _syncFromServer() async {
    final user = _ref.read(authProvider).user;
    if (user == null) return;
    try {
      final repo = _ref.read(userRepositoryProvider);
      final settings = await repo.fetchUserSettings();
      final level = settings['system_update_level'] as int?;
      if (level != null && level != state) {
        state = level;
        final prefs = await SharedPreferences.getInstance();
        await prefs.setInt(kSystemUpdateLevelKey, level);
      }
    } catch (_) {
      // Silent fail
    }
  }

  Future<void> _syncToServer({int? level}) async {
    final user = _ref.read(authProvider).user;
    if (user == null) return;
    try {
      final repo = _ref.read(userRepositoryProvider);
      await repo.updateUserSettings({
        if (level != null) "system_update_level": level,
      });
    } catch (_) {
      // Silent fail
    }
  }
}
