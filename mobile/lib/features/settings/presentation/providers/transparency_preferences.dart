import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/services/user_preferences_service.dart';

part 'transparency_preferences.g.dart';

/// 透明模式（chat 过程信息展示）偏好状态层。
///
/// V3-FIX-183：自 `transparency_settings_screen.dart` 拆出——该屏体本身
/// 0 路由挂载/0 push/0 实例化（NAV-IA A-1 辩题3 裁「删按钮」）已删除，
/// 但本状态层被 chat_screen / chat_settings_screen / chat_bubble /
/// transparency_floating_capsule 持续消费，属在用代码，按职责落位 providers。
enum TransparencyDisplayMode {
  collapsedFloating,
  bottomSheet,
  detailOnly,
}

/// Safely parse [TransparencyDisplayMode] from a stored string.
/// Returns [TransparencyDisplayMode.collapsedFloating] for unknown values.
TransparencyDisplayMode _safeDisplayMode(String name) =>
    TransparencyDisplayMode.values.firstWhere(
      (e) => e.name == name,
      orElse: () => TransparencyDisplayMode.collapsedFloating,
    );

/// Transparency preferences model
class TransparencyPreferences {
  const TransparencyPreferences({
    required this.enabled,
    required this.showTokenUsage,
    required this.showAgentSwitching,
    required this.showReasoningSteps,
    required this.displayMode,
    required this.autoCollapseOnComplete,
    required this.allowPerTurnDismiss,
    this.showAuroraExperienceReceipts = true,
    this.showMemoryReferenceReceipts = true,
    this.showSourceContextReceipts = true,
    this.showNextActionChangedReceipts = true,
  });

  factory TransparencyPreferences.fromJson(Map<String, dynamic> json) =>
      TransparencyPreferences(
        enabled: json['enabled'] as bool? ?? false,
        showTokenUsage: json['showTokenUsage'] as bool? ?? true,
        showAgentSwitching: json['showAgentSwitching'] as bool? ?? true,
        showReasoningSteps: json['showReasoningSteps'] as bool? ?? true,
        displayMode: _safeDisplayMode(
          json['displayMode'] as String? ?? 'collapsedFloating',
        ),
        autoCollapseOnComplete: json['autoCollapseOnComplete'] as bool? ?? true,
        allowPerTurnDismiss: json['allowPerTurnDismiss'] as bool? ?? true,
        showAuroraExperienceReceipts:
            json['showAuroraExperienceReceipts'] as bool? ?? true,
        showMemoryReferenceReceipts:
            json['showMemoryReferenceReceipts'] as bool? ?? true,
        showSourceContextReceipts:
            json['showSourceContextReceipts'] as bool? ?? true,
        showNextActionChangedReceipts:
            json['showNextActionChangedReceipts'] as bool? ?? true,
      );

  final bool enabled;
  final bool showTokenUsage;
  final bool showAgentSwitching;
  final bool showReasoningSteps;
  final TransparencyDisplayMode displayMode;
  final bool autoCollapseOnComplete;
  final bool allowPerTurnDismiss;
  final bool showAuroraExperienceReceipts;
  final bool showMemoryReferenceReceipts;
  final bool showSourceContextReceipts;
  final bool showNextActionChangedReceipts;

  Set<String> get enabledReceiptTypes => {
        if (showAuroraExperienceReceipts) 'aurora_experience_receipt',
        if (showMemoryReferenceReceipts) 'memory_reference_receipt',
        if (showSourceContextReceipts) 'source_context_receipt',
        if (showNextActionChangedReceipts) 'next_action_changed_by_aurora',
      };

  Map<String, dynamic> toJson() => {
        'enabled': enabled,
        'showTokenUsage': showTokenUsage,
        'showAgentSwitching': showAgentSwitching,
        'showReasoningSteps': showReasoningSteps,
        'displayMode': displayMode.name,
        'autoCollapseOnComplete': autoCollapseOnComplete,
        'allowPerTurnDismiss': allowPerTurnDismiss,
        'showAuroraExperienceReceipts': showAuroraExperienceReceipts,
        'showMemoryReferenceReceipts': showMemoryReferenceReceipts,
        'showSourceContextReceipts': showSourceContextReceipts,
        'showNextActionChangedReceipts': showNextActionChangedReceipts,
      };

  TransparencyPreferences copyWith({
    bool? enabled,
    bool? showTokenUsage,
    bool? showAgentSwitching,
    bool? showReasoningSteps,
    TransparencyDisplayMode? displayMode,
    bool? autoCollapseOnComplete,
    bool? allowPerTurnDismiss,
    bool? showAuroraExperienceReceipts,
    bool? showMemoryReferenceReceipts,
    bool? showSourceContextReceipts,
    bool? showNextActionChangedReceipts,
  }) =>
      TransparencyPreferences(
        enabled: enabled ?? this.enabled,
        showTokenUsage: showTokenUsage ?? this.showTokenUsage,
        showAgentSwitching: showAgentSwitching ?? this.showAgentSwitching,
        showReasoningSteps: showReasoningSteps ?? this.showReasoningSteps,
        displayMode: displayMode ?? this.displayMode,
        autoCollapseOnComplete:
            autoCollapseOnComplete ?? this.autoCollapseOnComplete,
        allowPerTurnDismiss: allowPerTurnDismiss ?? this.allowPerTurnDismiss,
        showAuroraExperienceReceipts:
            showAuroraExperienceReceipts ?? this.showAuroraExperienceReceipts,
        showMemoryReferenceReceipts:
            showMemoryReferenceReceipts ?? this.showMemoryReferenceReceipts,
        showSourceContextReceipts:
            showSourceContextReceipts ?? this.showSourceContextReceipts,
        showNextActionChangedReceipts: showNextActionChangedReceipts ??
            this.showNextActionChangedReceipts,
      );
}

/// Notifier for transparency preferences
@riverpod
class TransparencyPreferencesNotifier
    extends _$TransparencyPreferencesNotifier {
  static const _defaults = TransparencyPreferences(
    enabled: true,
    showTokenUsage: true,
    showAgentSwitching: true,
    showReasoningSteps: true,
    displayMode: TransparencyDisplayMode.collapsedFloating,
    autoCollapseOnComplete: true,
    allowPerTurnDismiss: true,
  );

  Future<void> _updatePreferences(TransparencyPreferences prefs) async {
    state = AsyncValue.data(prefs);

    final service = ref.read(userPreferencesServiceProvider);
    await service.updatePreferences({
      'transparency': prefs.toJson(),
    });
  }

  Future<void> setEnabled(bool value) async {
    final current = state.valueOrNull ?? _defaults;
    await _updatePreferences(current.copyWith(enabled: value));
  }

  Future<void> setShowTokenUsage(bool value) async {
    final current = state.valueOrNull ?? _defaults;
    await _updatePreferences(current.copyWith(showTokenUsage: value));
  }

  Future<void> setShowAgentSwitching(bool value) async {
    final current = state.valueOrNull ?? _defaults;
    await _updatePreferences(current.copyWith(showAgentSwitching: value));
  }

  Future<void> setShowReasoningSteps(bool value) async {
    final current = state.valueOrNull ?? _defaults;
    await _updatePreferences(current.copyWith(showReasoningSteps: value));
  }

  Future<void> setShowAuroraExperienceReceipts(bool value) async {
    final current = state.valueOrNull ?? _defaults;
    await _updatePreferences(
      current.copyWith(showAuroraExperienceReceipts: value),
    );
  }

  Future<void> setShowMemoryReferenceReceipts(bool value) async {
    final current = state.valueOrNull ?? _defaults;
    await _updatePreferences(
      current.copyWith(showMemoryReferenceReceipts: value),
    );
  }

  Future<void> setShowSourceContextReceipts(bool value) async {
    final current = state.valueOrNull ?? _defaults;
    await _updatePreferences(
      current.copyWith(showSourceContextReceipts: value),
    );
  }

  Future<void> setShowNextActionChangedReceipts(bool value) async {
    final current = state.valueOrNull ?? _defaults;
    await _updatePreferences(
      current.copyWith(showNextActionChangedReceipts: value),
    );
  }

  Future<void> setDisplayMode(TransparencyDisplayMode value) async {
    final current = state.valueOrNull ?? _defaults;
    await _updatePreferences(current.copyWith(displayMode: value));
  }

  Future<void> setAutoCollapseOnComplete(bool value) async {
    final current = state.valueOrNull ?? _defaults;
    await _updatePreferences(current.copyWith(autoCollapseOnComplete: value));
  }

  Future<void> setAllowPerTurnDismiss(bool value) async {
    final current = state.valueOrNull ?? _defaults;
    await _updatePreferences(current.copyWith(allowPerTurnDismiss: value));
  }

  @override
  Future<TransparencyPreferences> build() async {
    try {
      final service = ref.watch(userPreferencesServiceProvider);
      final prefs = await service.getPreferences();

      final transparencyPrefs = prefs['transparency'] as Map<String, dynamic>?;

      if (transparencyPrefs != null) {
        return TransparencyPreferences.fromJson(transparencyPrefs);
      }

      return _defaults;
    } catch (error, stackTrace) {
      Error.throwWithStackTrace(error, stackTrace);
    }
  }
}
