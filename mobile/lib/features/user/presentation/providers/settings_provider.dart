import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart'
    show TaskReminderConfig, taskNotificationSchedulerProvider;
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/home/data/repositories/prediction_repository.dart';
import 'package:sparkle/features/notification_center/data/repositories/notification_center_repository.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/shared/entities/user_model.dart';

/// Key for storing 'Enter to Send' preference in SharedPreferences
const String kEnterToSendKey = 'settings_enter_to_send';
const String kTransparentModeKey = 'settings_transparent_mode';
const String kTransparencyLevelKey = 'settings_transparency_level';
const String kOnboardingCompletedKey = 'settings_onboarding_completed';
const String kSystemUpdateLevelKey = 'settings_system_update_level';
const String kAiReasoningModeKey = 'settings_ai_reasoning_mode';
const String kShowChatContextToggleKey = 'settings_show_chat_context_toggle';
const String kShowChatPredictionDockKey = 'settings_show_chat_prediction_dock';
const String kShowChatTransparencyCapsuleKey =
    'settings_show_chat_transparency_capsule';
const String kChatPureModeKey = 'settings_chat_pure_mode';
const String kChatSeedLibraryEnabledKey = 'settings_chat_seed_library_enabled';
const String kMotionIntensityLevelPreferenceKey =
    'settings_motion_intensity_level';

/// Learning preferences model
class LearningPreferences {
  const LearningPreferences({
    required this.depth,
    required this.curiosity,
  });

  final double depth;
  final double curiosity;

  LearningPreferences copyWith({double? depth, double? curiosity}) =>
      LearningPreferences(
        depth: depth ?? this.depth,
        curiosity: curiosity ?? this.curiosity,
      );
}

/// Provider for learning preferences (depth and curiosity)
final learningPreferencesProvider =
    StateNotifierProvider<LearningPreferencesNotifier, LearningPreferences>(
  LearningPreferencesNotifier.new,
);

/// Provider for push notification preferences
final pushPreferencesProvider =
    StateNotifierProvider<PushPreferencesNotifier, PushPreferences>(
  PushPreferencesNotifier.new,
);

/// Provider for task reminder configuration
final taskReminderConfigProvider =
    StateNotifierProvider<TaskReminderConfigNotifier, TaskReminderConfig>(
  TaskReminderConfigNotifier.new,
);

/// Provider for notification center preferences
final notificationPreferenceSettingsProvider = StateNotifierProvider<
    NotificationPreferenceSettingsNotifier, NotificationPreferenceSettings>(
  NotificationPreferenceSettingsNotifier.new,
);

/// Provider for weekly agenda data
final weeklyAgendaProvider =
    StateNotifierProvider<WeeklyAgendaNotifier, Map<String, dynamic>>(
  WeeklyAgendaNotifier.new,
);

class NotificationPreferenceSettings {
  const NotificationPreferenceSettings({
    this.enableSystem = true,
    this.enableInterventions = true,
    this.notificationLevel = 'standard',
    this.quietHoursEnabled = false,
    this.quietHoursStart = '22:00',
    this.quietHoursEnd = '08:00',
    this.isLoaded = false,
  });

  final bool enableSystem;
  final bool enableInterventions;
  final String notificationLevel;
  final bool quietHoursEnabled;
  final String quietHoursStart;
  final String quietHoursEnd;
  final bool isLoaded;

  NotificationPreferenceSettings copyWith({
    bool? enableSystem,
    bool? enableInterventions,
    String? notificationLevel,
    bool? quietHoursEnabled,
    String? quietHoursStart,
    String? quietHoursEnd,
    bool? isLoaded,
  }) =>
      NotificationPreferenceSettings(
        enableSystem: enableSystem ?? this.enableSystem,
        enableInterventions: enableInterventions ?? this.enableInterventions,
        notificationLevel: notificationLevel ?? this.notificationLevel,
        quietHoursEnabled: quietHoursEnabled ?? this.quietHoursEnabled,
        quietHoursStart: quietHoursStart ?? this.quietHoursStart,
        quietHoursEnd: quietHoursEnd ?? this.quietHoursEnd,
        isLoaded: isLoaded ?? this.isLoaded,
      );

  static NotificationPreferenceSettings fromJson(Map<String, dynamic> json) =>
      NotificationPreferenceSettings(
        enableSystem: json['enable_system'] as bool? ?? true,
        enableInterventions: json['enable_interventions'] as bool? ?? true,
        notificationLevel: json['notification_level'] as String? ?? 'standard',
        quietHoursEnabled: json['quiet_hours_enabled'] as bool? ?? false,
        quietHoursStart: json['quiet_hours_start'] as String? ?? '22:00',
        quietHoursEnd: json['quiet_hours_end'] as String? ?? '08:00',
        isLoaded: true,
      );

  Map<String, dynamic> toJson() => {
        'enable_system': enableSystem,
        'enable_interventions': enableInterventions,
        'notification_level': notificationLevel,
        'quiet_hours_enabled': quietHoursEnabled,
        'quiet_hours_start': quietHoursStart,
        'quiet_hours_end': quietHoursEnd,
      };
}

class WeeklyAgendaNotifier extends StateNotifier<Map<String, dynamic>> {
  WeeklyAgendaNotifier(this._ref) : super({}) {
    unawaited(_loadFromSettings());
  }

  final Ref _ref;

  Future<void> _loadFromSettings() async {
    final user = _ref.read(authProvider).user;
    if (user?.schedulePreferences != null) {
      state = user!.schedulePreferences!;
    } else {
      state = {'grid': List.filled(168, 'relax')};
    }
  }

  Future<void> updateAgenda(Map<String, dynamic> data) async {
    final prevState = state;
    // Optimistic update
    state = data;

    // Save to backend via dedicated schedule preferences endpoint
    try {
      final repo = _ref.read(userRepositoryProvider);
      final updatedUser = await repo.updateSchedulePreferences(data);
      // Update auth state with new user data
      final authNotifier = _ref.read(authProvider.notifier);
      final currentAuthState = _ref.read(authProvider);
      authNotifier.state = currentAuthState.copyWith(user: updatedUser);
    } catch (e) {
      // Revert on error
      state = prevState;
      rethrow;
    }
  }
}

class TaskReminderConfigNotifier extends StateNotifier<TaskReminderConfig> {
  TaskReminderConfigNotifier(this._ref) : super(const TaskReminderConfig()) {
    _ref.listen<AuthState>(authProvider, (prev, next) {
      if (next.user != null && prev?.user?.id != next.user?.id) {
        unawaited(_loadFromSettings());
      }
    });
    unawaited(_loadFromSettings());
  }

  final Ref _ref;

  Future<void> _loadFromSettings() async {
    final user = _ref.read(authProvider).user;
    if (user == null) return;

    try {
      final repo = _ref.read(userRepositoryProvider);
      final settings = await repo.fetchUserSettings();
      final enabled = settings['task_reminders_enabled'] as bool? ?? true;
      final times =
          settings['task_reminder_times'] as List<dynamic>? ?? [1440, 60, 15];

      state = TaskReminderConfig(
        enabled: enabled,
        reminders: times.cast<int>(),
      );
    } catch (e) {
      // Keep default state on error
    }
  }

  Future<void> updateConfig({
    bool? enabled,
    List<int>? reminders,
  }) async {
    final prevState = state;
    final newState = TaskReminderConfig(
      enabled: enabled ?? prevState.enabled,
      reminders: reminders ?? prevState.reminders,
    );

    // Optimistic update
    state = newState;

    try {
      final repo = _ref.read(userRepositoryProvider);
      await repo.updateUserSettings({
        'task_reminders_enabled': newState.enabled,
        'task_reminder_times': newState.reminders,
      });
      final scheduler = _ref.read(taskNotificationSchedulerProvider);
      final taskRepo = _ref.read(taskRepositoryProvider);
      final tasks = await taskRepo.getTasks();
      await scheduler.refreshAllReminders(
        tasks.items,
        config: newState,
      );
    } catch (e) {
      // Revert on error
      state = prevState;
      rethrow;
    }
  }
}

class NotificationPreferenceSettingsNotifier
    extends StateNotifier<NotificationPreferenceSettings> {
  NotificationPreferenceSettingsNotifier(this._ref)
      : super(const NotificationPreferenceSettings()) {
    _ref.listen<AuthState>(authProvider, (prev, next) {
      if (next.user != null && prev?.user?.id != next.user?.id) {
        unawaited(_loadPreferences());
      }
    });
    unawaited(_loadPreferences());
  }

  final Ref _ref;

  Future<void> _loadPreferences() async {
    final user = _ref.read(authProvider).user;
    if (user == null) {
      state = const NotificationPreferenceSettings();
      return;
    }

    try {
      final repo = _ref.read(notificationCenterRepositoryProvider);
      final prefs = await repo.getPreferences();
      state = NotificationPreferenceSettings.fromJson(prefs);
    } catch (_) {
      state = state.copyWith(isLoaded: true);
    }
  }

  Future<void> updatePreferences({
    bool? enableSystem,
    bool? enableInterventions,
    String? notificationLevel,
    bool? quietHoursEnabled,
    String? quietHoursStart,
    String? quietHoursEnd,
  }) async {
    final previousState = state;
    final nextState = previousState.copyWith(
      enableSystem: enableSystem,
      enableInterventions: enableInterventions,
      notificationLevel: notificationLevel,
      quietHoursEnabled: quietHoursEnabled,
      quietHoursStart: quietHoursStart,
      quietHoursEnd: quietHoursEnd,
      isLoaded: true,
    );

    state = nextState;

    try {
      final repo = _ref.read(notificationCenterRepositoryProvider);
      final saved = await repo.updatePreferences(nextState.toJson());
      state = NotificationPreferenceSettings.fromJson(saved);
    } catch (e) {
      state = previousState;
      rethrow;
    }
  }
}

class PushPreferencesNotifier extends StateNotifier<PushPreferences> {
  PushPreferencesNotifier(this._ref)
      : super(
          PushPreferences(),
        ) {
    _ref.listen<AuthState>(authProvider, (prev, next) {
      if (next.user != null && prev?.user?.id != next.user?.id) {
        _loadFromUser(next.user);
      }
    });
    _loadFromUser(_ref.read(authProvider).user);
  }

  final Ref _ref;

  void _loadFromUser(UserModel? user) {
    if (user?.pushPreferences != null) {
      state = user!.pushPreferences!;
    }
  }

  Future<void> updatePreferences({
    bool? enableCuriosity,
    String? personaType,
    int? dailyCap,
    List<Map<String, String>>? activeSlots,
  }) async {
    final currentState = state;
    final updatedPrefs = PushPreferences(
      enableCuriosity: enableCuriosity ?? currentState.enableCuriosity,
      personaType: personaType ?? currentState.personaType,
      dailyCap: dailyCap ?? currentState.dailyCap,
      activeSlots: activeSlots ?? currentState.activeSlots,
      timezone: currentState.timezone,
    );

    // Optimistic update
    state = updatedPrefs;

    final user = _ref.read(authProvider).user;
    if (user == null) return;

    try {
      final apiClient = _ref.read(apiClientProvider);
      await apiClient.put<Map<String, dynamic>>(
        '/users/me/push-preference',
        data: updatedPrefs.toJson(),
      );

      // Refresh user to get updated data
      await _ref.read(authProvider.notifier).refreshUser();
    } catch (e) {
      // Revert on error
      state = currentState;
      rethrow;
    }
  }

  Future<void> toggleEnableCuriosity() async {
    await updatePreferences(
      enableCuriosity: !state.enableCuriosity,
    );
  }
}

class LearningPreferencesNotifier extends StateNotifier<LearningPreferences> {
  LearningPreferencesNotifier(this._ref)
      : super(const LearningPreferences(depth: 0.5, curiosity: 0.5)) {
    _ref.listen<AuthState>(authProvider, (prev, next) {
      if (next.user != null && prev?.user?.id != next.user?.id) {
        _loadFromUser(next.user);
      }
    });
    _loadFromUser(_ref.read(authProvider).user);
  }

  final Ref _ref;

  void _loadFromUser(UserModel? user) {
    if (user != null) {
      state = LearningPreferences(
        depth: user.depthPreference,
        curiosity: user.curiosityPreference,
      );
    }
  }

  void previewPreferences({
    double? depth,
    double? curiosity,
  }) {
    state = state.copyWith(depth: depth, curiosity: curiosity);
  }

  Future<void> updatePreferences({
    double? depth,
    double? curiosity,
  }) async {
    final prevState = state;
    final user = _ref.read(authProvider).user;
    if (user == null) return;

    final newState = state.copyWith(depth: depth, curiosity: curiosity);
    // Optimistic update
    state = newState;

    try {
      final repo = _ref.read(userRepositoryProvider);
      final updatedUser = await repo.updateUserPreferences(
        UserPreferences(
          depthPreference: newState.depth,
          curiosityPreference: newState.curiosity,
        ),
      );
      // Update auth state with new user data
      final authNotifier = _ref.read(authProvider.notifier);
      final currentAuthState = _ref.read(authProvider);
      authNotifier.state = currentAuthState.copyWith(user: updatedUser);
    } catch (e) {
      // Revert to previous state on error
      state = prevState;
      rethrow;
    }
  }
}

/// Provider to manage the 'Enter to Send' preference
final enterToSendProvider = StateNotifierProvider<EnterToSendNotifier, bool>(
  (ref) => EnterToSendNotifier(),
);

final transparencyLevelProvider =
    StateNotifierProvider<TransparencyLevelNotifier, int>(
  TransparencyLevelNotifier.new,
);

final transparentModeProvider = Provider<bool>(
  (ref) => ref.watch(transparencyLevelProvider) > 0,
);

final onboardingCompletedProvider =
    StateNotifierProvider<OnboardingCompletedNotifier, bool>(
  (ref) => OnboardingCompletedNotifier(ref),
);

final systemUpdateLevelProvider =
    StateNotifierProvider<SystemUpdateLevelNotifier, int>(
  SystemUpdateLevelNotifier.new,
);

final aiReasoningModeProvider =
    StateNotifierProvider<AiReasoningModeNotifier, String>(
  (ref) => AiReasoningModeNotifier(ref),
);

final showChatContextToggleProvider =
    StateNotifierProvider<SimpleBoolPreferenceNotifier, bool>(
  (ref) => SimpleBoolPreferenceNotifier(
    storageKey: kShowChatContextToggleKey,
    defaultValue: true,
  ),
);

final showChatPredictionDockProvider =
    StateNotifierProvider<SimpleBoolPreferenceNotifier, bool>(
  (ref) => SimpleBoolPreferenceNotifier(
    storageKey: kShowChatPredictionDockKey,
    defaultValue: true,
  ),
);

final showChatTransparencyCapsuleProvider =
    StateNotifierProvider<SimpleBoolPreferenceNotifier, bool>(
  (ref) => SimpleBoolPreferenceNotifier(
    storageKey: kShowChatTransparencyCapsuleKey,
    defaultValue: true,
  ),
);

final chatPureModeProvider =
    StateNotifierProvider<SimpleBoolPreferenceNotifier, bool>(
  (ref) => SimpleBoolPreferenceNotifier(
    storageKey: kChatPureModeKey,
    defaultValue: false,
  ),
);

final chatSeedLibraryEnabledProvider =
    StateNotifierProvider<SimpleBoolPreferenceNotifier, bool>(
  (ref) => SimpleBoolPreferenceNotifier(
    storageKey: kChatSeedLibraryEnabledKey,
    defaultValue: false,
  ),
);

final motionIntensityLevelProvider =
    StateNotifierProvider<MotionIntensityLevelNotifier, MotionIntensityLevel>(
  (ref) => MotionIntensityLevelNotifier(),
);

final aiUsageSummaryProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  final user = ref.watch(authProvider).user;
  if (user == null) {
    return {
      'current_mode': ref.watch(aiReasoningModeProvider),
      'items': <Map<String, dynamic>>[],
    };
  }
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchAiUsageSummary();
});

final aiOpsDashboardProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  final user = ref.watch(authProvider).user;
  if (user == null) {
    return {
      'window_days': 7,
      'items': <Map<String, dynamic>>[],
    };
  }
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchAiOpsDashboard();
});

final aiOpsExportProvider =
    FutureProvider.family<Map<String, dynamic>, int>((ref, days) async {
  final user = ref.watch(authProvider).user;
  if (user == null) {
    return {
      'window_days': days,
      'overview': <String, dynamic>{},
      'items': <Map<String, dynamic>>[],
      'trend_series': <Map<String, dynamic>>[],
    };
  }
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchAiOpsExport(days: days);
});

final predictionAnalyticsDashboardProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  final user = ref.watch(authProvider).user;
  if (user == null) {
    return {
      'window_days': 7,
      'overall': <String, dynamic>{},
      'funnel': <String, dynamic>{},
      'by_surface': <String, dynamic>{},
      'by_action_type': <String, dynamic>{},
      'top_actions': <Map<String, dynamic>>[],
    };
  }
  final repo = ref.watch(predictionRepositoryProvider);
  return repo.getPredictionAnalytics();
});

final predictionAnalyticsByDaysProvider =
    FutureProvider.family<Map<String, dynamic>, int>((ref, days) async {
  final user = ref.watch(authProvider).user;
  if (user == null) {
    return {
      'window_days': days,
      'overall': <String, dynamic>{},
      'funnel': <String, dynamic>{},
      'by_surface': <String, dynamic>{},
      'by_action_type': <String, dynamic>{},
      'top_actions': <Map<String, dynamic>>[],
    };
  }
  final repo = ref.watch(predictionRepositoryProvider);
  return repo.getPredictionAnalytics(days: days);
});

final clientTelemetrySummaryProvider =
    FutureProvider.family<Map<String, dynamic>, int>((ref, days) async {
  final user = ref.watch(authProvider).user;
  if (user == null) {
    return {
      'days': days,
      'overall': <String, dynamic>{},
      'daily_totals': <Map<String, dynamic>>[],
      'by_event_type': <Map<String, dynamic>>[],
      'recent_events': <Map<String, dynamic>>[],
    };
  }
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchClientTelemetrySummary(days: days);
});

final healthCapacityProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  final user = ref.watch(authProvider).user;
  if (user == null) {
    return {
      'database': <String, dynamic>{},
      'redis': <String, dynamic>{},
      'queues': <String, dynamic>{},
      'disk': <String, dynamic>{},
      'recommendations': <String>[],
    };
  }
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchHealthCapacity();
});

final prometheusAlertsProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  final user = ref.watch(authProvider).user;
  if (user == null) {
    return {
      'alerts': <Map<String, dynamic>>[],
      'firing': false,
    };
  }
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchPrometheusAlerts();
});

class EnterToSendNotifier extends StateNotifier<bool> {
  EnterToSendNotifier() : super(true) {
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
      // Default to enabled
      state = true;
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

class SimpleBoolPreferenceNotifier extends StateNotifier<bool> {
  SimpleBoolPreferenceNotifier({
    required this.storageKey,
    required this.defaultValue,
  }) : super(defaultValue) {
    _loadSettings();
  }

  final String storageKey;
  final bool defaultValue;

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final value = prefs.getBool(storageKey);
      state = value ?? defaultValue;
    } catch (_) {
      state = defaultValue;
    }
  }

  Future<void> setEnabled(bool enabled) async {
    if (state == enabled) return;
    state = enabled;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(storageKey, enabled);
    } catch (_) {
      // Silent fail for persistence
    }
  }
}

class MotionIntensityLevelNotifier extends StateNotifier<MotionIntensityLevel> {
  MotionIntensityLevelNotifier() : super(MotionIntensityLevel.high) {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final stored = prefs.getString(kMotionIntensityLevelPreferenceKey);
      final level = MotionIntensityLevel.values.firstWhere(
        (candidate) => candidate.storageValue == stored,
        orElse: () => MotionIntensityLevel.high,
      );
      state = level;
      await PerformanceService.instance.setMotionIntensityLevel(
        level,
        persist: false,
      );
    } catch (_) {
      state = MotionIntensityLevel.high;
    }
  }

  Future<void> setLevel(MotionIntensityLevel level) async {
    if (state == level) return;
    state = level;
    await PerformanceService.instance.setMotionIntensityLevel(level);
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
        if (level != null) 'transparency_level': level,
      });
    } catch (_) {
      // Silent fail
    }
  }
}

class OnboardingCompletedNotifier extends StateNotifier<bool> {
  OnboardingCompletedNotifier(this._ref) : super(false) {
    _ref.listen<AuthState>(authProvider, (prev, next) {
      if (prev?.user?.id != next.user?.id ||
          prev?.isAuthenticated != next.isAuthenticated) {
        unawaited(syncForUser(next.user));
      }
    });
    unawaited(syncForUser(_ref.read(authProvider).user));
  }

  final Ref _ref;

  String _storageKeyForUser(String userId) =>
      '${kOnboardingCompletedKey}_$userId';

  bool _inferCompletedFromProfileContext(Map<String, dynamic> payload) {
    final preferenceVersion = payload['preference_version'];
    final versionValue =
        preferenceVersion is num ? preferenceVersion.toInt() : 0;
    if (versionValue > 1) {
      return true;
    }

    final preferences = payload['preferences'];
    if (preferences is! Map<String, dynamic>) {
      return false;
    }

    return preferences.containsKey('study_time_preference') ||
        preferences.containsKey('knowledge_level') ||
        preferences.containsKey('response_style');
  }

  Future<void> syncForUser(UserModel? user) async {
    if (user == null) {
      state = false;
      return;
    }

    if (user.registrationSource == 'guest') {
      state = true;
      try {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setBool(_storageKeyForUser(user.id), true);
      } catch (_) {
        // Silent fail for persistence
      }
      return;
    }

    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getBool(_storageKeyForUser(user.id));
      if (saved != null) {
        state = saved;
        if (saved) {
          return;
        }
      } else {
        state = false;
      }

      final profileContext =
          await _ref.read(userRepositoryProvider).fetchProfileContext();
      final completed = _inferCompletedFromProfileContext(profileContext);
      state = completed;
      await prefs.setBool(_storageKeyForUser(user.id), completed);
    } catch (_) {
      state = false;
    }
  }

  Future<void> setCompleted(bool value) async {
    if (state == value) return;
    state = value;
    try {
      final prefs = await SharedPreferences.getInstance();
      final user = _ref.read(authProvider).user;
      if (user != null) {
        await prefs.setBool(_storageKeyForUser(user.id), value);
      }
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
        if (level != null) 'system_update_level': level,
      });
    } catch (_) {
      // Silent fail
    }
  }
}

class AiReasoningModeNotifier extends StateNotifier<String> {
  AiReasoningModeNotifier(this._ref) : super('balanced') {
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
      final value = prefs.getString(kAiReasoningModeKey);
      if (value != null && {'fast', 'balanced', 'deep'}.contains(value)) {
        state = value;
      }
    } catch (_) {
      state = 'balanced';
    }
    await _syncFromServer();
  }

  Future<void> setMode(String mode) async {
    final normalized =
        {'fast', 'balanced', 'deep'}.contains(mode) ? mode : 'balanced';
    if (state == normalized) return;
    final previous = state;
    state = normalized;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(kAiReasoningModeKey, normalized);
    } catch (_) {
      // Silent fail for persistence
    }
    try {
      final user = _ref.read(authProvider).user;
      if (user != null) {
        await _ref.read(userRepositoryProvider).updateUserSettings({
          'ai_reasoning_mode': normalized,
        });
      }
      _ref.invalidate(aiUsageSummaryProvider);
      _ref.invalidate(aiOpsDashboardProvider);
      _ref.invalidate(aiOpsExportProvider);
      _ref.invalidate(predictionAnalyticsDashboardProvider);
      _ref.invalidate(predictionAnalyticsByDaysProvider);
    } catch (_) {
      state = previous;
    }
  }

  Future<void> _syncFromServer() async {
    final user = _ref.read(authProvider).user;
    if (user == null) return;
    try {
      final settings =
          await _ref.read(userRepositoryProvider).fetchUserSettings();
      final value = settings['ai_reasoning_mode'] as String?;
      if (value != null && {'fast', 'balanced', 'deep'}.contains(value)) {
        state = value;
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(kAiReasoningModeKey, value);
      }
      _ref.invalidate(aiUsageSummaryProvider);
      _ref.invalidate(aiOpsDashboardProvider);
      _ref.invalidate(aiOpsExportProvider);
      _ref.invalidate(predictionAnalyticsDashboardProvider);
      _ref.invalidate(predictionAnalyticsByDaysProvider);
    } catch (_) {
      // Silent fail
    }
  }
}
