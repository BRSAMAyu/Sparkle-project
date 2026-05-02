import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/providers/locale_provider.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart'
    show TaskReminderConfig;
import 'package:sparkle/core/utils/chaos/chaos_control_dialog.dart';
import 'package:sparkle/features/aurora/presentation/providers/aurora_preferences_provider.dart';
import 'package:sparkle/features/aurora/presentation/providers/emotion_state_provider.dart';
import 'package:sparkle/features/cognitive/data/repositories/capsule_repository.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/cognitive/presentation/screens/capsule/capsule_detail_screen.dart';
import 'package:sparkle/features/cognitive/presentation/widgets/capsule/capsule_generation_preview.dart';
import 'package:sparkle/features/documents/documents_routes.dart';
import 'package:sparkle/features/settings/presentation/screens/accessibility_settings_screen.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/screens/ai_ops_analysis_screen.dart';
import 'package:sparkle/features/user/presentation/widgets/learning_mode_control.dart';
import 'package:sparkle/features/user/presentation/widgets/weekly_agenda_grid.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/features/visual_elements/visual_elements_routes.dart';
import 'package:sparkle/l10n/app_localizations.dart';

const Map<String, Set<String>> _notificationTypeAliases = {
  'reminder': {
    'reminder',
    'task_reminder',
    'sprint_reminder',
    'daily_sprint_reminder',
    'comeback_nudge',
    'fragmented_time',
  },
  'spaced_repetition': {
    'spaced_repetition',
    'spaced_repetition_reminder',
  },
  'weekly_report': {
    'weekly_report',
    'weekly_digest',
    'weekly_growth_narrative',
    'weekly_learning_report',
  },
  'milestone': {
    'milestone',
    'milestone_notification',
    'achievement',
    'achievement_progress',
  },
};

class UnifiedSettingsScreen extends ConsumerStatefulWidget {
  const UnifiedSettingsScreen({super.key});

  @override
  ConsumerState<UnifiedSettingsScreen> createState() =>
      _UnifiedSettingsScreenState();
}

class _UnifiedSettingsScreenState extends ConsumerState<UnifiedSettingsScreen> {
  bool _isGenerating = false;
  bool _weeklyAgendaExpanded = false;
  bool _sensoryExpanded = false;
  bool _learningExpanded = false;
  bool _bgmExpanded = false;
  bool _bgmAdvancedExpanded = false;
  bool _themeExpanded = false;
  bool _auroraPrefsExpanded = false;
  bool _bgmEnabled = true;
  bool _bgmReady = false;
  double _bgmVolume = 0.85;
  BgmPalette _bgmPalette = BgmPalette.adaptive;
  BgmMode _bgmMode = BgmMode.adaptive;
  BgmIntensity _bgmIntensity = BgmIntensity.gentle;
  BgmVariety _bgmVariety = BgmVariety.balanced;
  bool _bgmReadingProtection = true;
  bool _bgmFocusPriority = true;
  bool _bgmLockCurrentStyle = false;
  BgmPalette? _previewingPalette;
  BgmTrack? _previewingSceneTrack;
  BgmPlaybackSnapshot? _bgmPlaybackSnapshot;
  BgmLibrarySnapshot? _bgmLibrarySnapshot;
  bool _soundEnabled = true;
  bool _hapticEnabled = true;
  bool _auroraSensoryLinkEnabled = true;
  bool _sensoryReady = false;
  AmbientScene _ambientScene = AmbientScene.none;
  double _ambientVolume = 0.5;
  Timer? _learningPrefsDebounce;

  String? _learningPreferenceStatus;
  bool _learningPreferenceStatusIsError = false;

  @override
  void initState() {
    super.initState();
    unawaited(_loadBgmPreferences());
    unawaited(_loadSensoryPreferences());
  }

  @override
  void dispose() {
    _learningPrefsDebounce?.cancel();
    super.dispose();
  }

  Future<void> _loadBgmPreferences() async {
    final enabled = await BgmService.isEnabled();
    final volume = await BgmService.getVolume();
    final palette = await BgmService.getPalette();
    final mode = await BgmService.getMode();
    final tuning = await BgmService.getUserTuning();
    final snapshot = await BgmService.currentPlaybackSnapshot();
    final librarySnapshot = await BgmService.librarySnapshot();
    if (!mounted) {
      return;
    }
    setState(() {
      _bgmEnabled = enabled;
      _bgmVolume = volume;
      _bgmPalette = palette;
      _bgmMode = mode;
      _bgmIntensity = tuning.intensity;
      _bgmVariety = tuning.variety;
      _bgmReadingProtection = tuning.readingProtection;
      _bgmFocusPriority = tuning.focusPriority;
      _bgmLockCurrentStyle = tuning.lockCurrentStyle;
      _bgmPlaybackSnapshot = snapshot;
      _bgmLibrarySnapshot = librarySnapshot;
      _bgmReady = true;
    });
  }

  Future<void> _refreshBgmPlaybackSnapshot() async {
    final snapshot = await BgmService.currentPlaybackSnapshot();
    final librarySnapshot = await BgmService.librarySnapshot();
    if (!mounted) {
      return;
    }
    setState(() {
      _bgmPlaybackSnapshot = snapshot;
      _bgmLibrarySnapshot = librarySnapshot;
    });
  }

  Future<void> _openBgmLibrary() async {
    await context.push(UserRoutes.bgmLibrary);
    if (!mounted) {
      return;
    }
    await _loadBgmPreferences();
  }

  Future<void> _loadSensoryPreferences() async {
    final soundEnabled = await SensoryFeedbackService.isSoundEnabled();
    final hapticEnabled = await SensoryFeedbackService.isHapticEnabled();
    final auroraLinkEnabled =
        await SensoryFeedbackService.isAuroraLinkageEnabled();
    final ambientScene = await SensoryFeedbackService.getSavedAmbientScene();
    final ambientVolume = await SensoryFeedbackService.getAmbientVolume();
    if (!mounted) {
      return;
    }
    setState(() {
      _soundEnabled = soundEnabled;
      _hapticEnabled = hapticEnabled;
      _auroraSensoryLinkEnabled = auroraLinkEnabled;
      _ambientScene = ambientScene;
      _ambientVolume = ambientVolume;
      _sensoryReady = true;
    });
  }

  Future<void> _setBgmEnabled(bool value) async {
    setState(() => _bgmEnabled = value);
    await BgmService.setEnabled(value);
    await _refreshBgmPlaybackSnapshot();
    if (value) {
      await SensoryFeedbackService.emit(
        SensoryFeedbackEvent.confirm,
        enableHaptic: false,
      );
    }
  }

  Future<void> _setBgmVolume(double value) async {
    setState(() => _bgmVolume = value);
    await BgmService.setVolume(value);
    await _refreshBgmPlaybackSnapshot();
  }

  Future<void> _setBgmPalette(BgmPalette palette) async {
    setState(() => _bgmPalette = palette);
    await BgmService.setPalette(palette);
    await _refreshBgmPlaybackSnapshot();
    if (_bgmEnabled) {
      await SensoryFeedbackService.emit(
        SensoryFeedbackEvent.selection,
        enableHaptic: false,
      );
    }
  }

  Future<void> _previewBgmPalette(BgmPalette palette) async {
    setState(() => _previewingPalette = palette);
    try {
      await BgmService.previewPalette(palette);
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
            context, AppLocalizations.of(context)!.capsulePreviewFailed);
      }
    } finally {
      if (mounted) {
        setState(() => _previewingPalette = null);
      }
    }
  }

  Future<void> _setBgmMode(BgmMode mode) async {
    setState(() => _bgmMode = mode);
    await BgmService.setMode(mode);
    await _refreshBgmPlaybackSnapshot();
    if (_bgmEnabled && mode != BgmMode.silent) {
      await SensoryFeedbackService.emit(
        SensoryFeedbackEvent.selection,
        enableHaptic: false,
      );
    }
  }

  Future<void> _setBgmIntensity(BgmIntensity intensity) async {
    setState(() => _bgmIntensity = intensity);
    await BgmService.setIntensity(intensity);
    await _refreshBgmPlaybackSnapshot();
  }

  Future<void> _setBgmVariety(BgmVariety variety) async {
    setState(() => _bgmVariety = variety);
    await BgmService.setVariety(variety);
    await _refreshBgmPlaybackSnapshot();
  }

  Future<void> _setBgmReadingProtection(bool enabled) async {
    setState(() => _bgmReadingProtection = enabled);
    await BgmService.setReadingProtection(enabled);
    await _refreshBgmPlaybackSnapshot();
  }

  Future<void> _setBgmFocusPriority(bool enabled) async {
    setState(() => _bgmFocusPriority = enabled);
    await BgmService.setFocusPriority(enabled);
    await _refreshBgmPlaybackSnapshot();
  }

  Future<void> _setBgmLockCurrentStyle(bool enabled) async {
    setState(() => _bgmLockCurrentStyle = enabled);
    await BgmService.setLockCurrentStyle(enabled);
    await _refreshBgmPlaybackSnapshot();
  }

  Future<void> _previewCurrentScene() async {
    final track = _bgmPlaybackSnapshot?.track;
    if (track == null) {
      return;
    }
    setState(() => _previewingSceneTrack = track);
    try {
      await BgmService.previewSceneSample(track, palette: _bgmPalette);
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
            context, AppLocalizations.of(context)!.capsuleScenePreviewFailed);
      }
    } finally {
      if (mounted) {
        setState(() => _previewingSceneTrack = null);
      }
    }
  }

  Future<void> _setSoundEnabled(bool value) async {
    setState(() => _soundEnabled = value);
    await SensoryFeedbackService.setSoundEnabled(value);
    if (value) {
      await SensoryFeedbackService.emit(
        SensoryFeedbackEvent.confirm,
        enableHaptic: false,
      );
    }
  }

  Future<void> _setHapticEnabled(bool value) async {
    setState(() => _hapticEnabled = value);
    await SensoryFeedbackService.setHapticEnabled(value);
    if (value) {
      await SensoryFeedbackService.emit(
        SensoryFeedbackEvent.selection,
        enableSound: false,
      );
    }
  }

  Future<void> _setAuroraSensoryLinkEnabled(bool value) async {
    setState(() => _auroraSensoryLinkEnabled = value);
    await SensoryFeedbackService.setAuroraLinkageEnabled(value);
    if (value) {
      await SensoryFeedbackService.emitAuroraEvent(
        AuroraSensoryEvent.statusChanged,
        enableSound: false,
      );
    }
  }

  Future<void> _setAmbientScene(AmbientScene scene) async {
    setState(() => _ambientScene = scene);
    await SensoryFeedbackService.setAmbientScene(scene, autoplay: true);
  }

  Future<void> _setAmbientVolume(double value) async {
    setState(() => _ambientVolume = value);
    await SensoryFeedbackService.setAmbientVolume(value);
  }

  void _scheduleLearningPreferenceUpdate({
    required double depth,
    required double curiosity,
  }) {
    final notifier = ref.read(learningPreferencesProvider.notifier);
    notifier.previewPreferences(depth: depth, curiosity: curiosity);
    if (mounted) {
      setState(() {
        _learningPreferenceStatus =
            AppLocalizations.of(context)!.learningPreferenceSaving;
        _learningPreferenceStatusIsError = false;
      });
    }
    _learningPrefsDebounce?.cancel();
    _learningPrefsDebounce = Timer(const Duration(milliseconds: 220), () async {
      try {
        await notifier.updatePreferences(depth: depth, curiosity: curiosity);
        if (!mounted) {
          return;
        }
        setState(() {
          _learningPreferenceStatus =
              AppLocalizations.of(context)!.learningPreferenceSaved;
          _learningPreferenceStatusIsError = false;
        });
      } catch (e) {
        if (!mounted) {
          return;
        }
        final message = e.toString().replaceFirst('Exception: ', '').trim();
        final l10n = AppLocalizations.of(context)!;
        setState(() {
          _learningPreferenceStatus =
              l10n.learningPreferenceSaveFailed(message);
          _learningPreferenceStatusIsError = true;
        });
        AppFeedback.error(context, l10n.learningPreferenceSaveFailed(message));
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final isCompact = MediaQuery.sizeOf(context).width < 380;
    final enterToSend = ref.watch(enterToSendProvider);
    final transparentMode = ref.watch(transparentModeProvider);
    final transparencyLevel = normalizeTransparencyLevelSetting(
      ref.watch(transparencyLevelProvider),
    );
    final systemUpdateLevel = normalizeSystemUpdateLevelSetting(
      ref.watch(systemUpdateLevelProvider),
    );
    final aiReasoningMode = normalizeAiReasoningModeSetting(
      ref.watch(aiReasoningModeProvider),
    );
    final showChatContextToggle = ref.watch(showChatContextToggleProvider);
    final showChatPredictionDock = ref.watch(showChatPredictionDockProvider);
    final showChatTransparencyCapsule =
        ref.watch(showChatTransparencyCapsuleProvider);
    final chatPureMode = ref.watch(chatPureModeProvider);
    final motionIntensityLevel = ref.watch(motionIntensityLevelProvider);
    final emotionState = ref.watch(emotionStateProvider);
    final aiUsageSummary = ref.watch(aiUsageSummaryProvider);
    final aiOpsDashboard = ref.watch(aiOpsDashboardProvider);
    final predictionAnalytics = ref.watch(predictionAnalyticsDashboardProvider);
    final learningPrefs = ref.watch(learningPreferencesProvider);
    final pushPrefs = ref.watch(pushPreferencesProvider);
    final notificationPrefs = ref.watch(notificationPreferenceSettingsProvider);
    final notificationLevel = normalizeNotificationLevelSetting(
      notificationPrefs.notificationLevel,
    );
    final taskReminderConfig = ref.watch(taskReminderConfigProvider);
    final weeklyAgenda = ref.watch(weeklyAgendaProvider);

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(l10n.schedulePreferences),
        actions: [
          SparkleButton.ghost(
            label: l10n.confirm,
            onPressed: () {
              if (context.mounted) {
                context.pop();
              }
            },
          ),
        ],
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          padding: EdgeInsets.symmetric(
            vertical: DS.spacing12,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildCollapsibleHeader(
                      icon: Icons.tune_rounded,
                      title: l10n.sensoryFeedbackSectionTitle,
                      subtitle: _sensoryReady
                          ? l10n.sensoryFeedbackSectionSubtitle
                          : l10n.sensoryFeedbackLoadingSubtitle,
                      expanded: _sensoryExpanded,
                      onToggle: () =>
                          setState(() => _sensoryExpanded = !_sensoryExpanded),
                    ),
                    AnimatedCrossFade(
                      firstChild: const SizedBox(width: double.infinity),
                      secondChild: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(l10n.sensorySoundTitle),
                            subtitle: Text(l10n.sensorySoundSubtitle),
                            value: _soundEnabled,
                            onChanged: _sensoryReady
                                ? (value) => unawaited(_setSoundEnabled(value))
                                : null,
                            activeThumbColor: DS.primaryBase,
                          ),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(l10n.sensoryHapticTitle),
                            subtitle: Text(l10n.sensoryHapticSubtitle),
                            value: _hapticEnabled,
                            onChanged: _sensoryReady
                                ? (value) => unawaited(_setHapticEnabled(value))
                                : null,
                            activeThumbColor: DS.primaryBase,
                          ),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(l10n.sensoryAuroraLinkTitle),
                            subtitle: Text(l10n.sensoryAuroraLinkSubtitle),
                            value: _auroraSensoryLinkEnabled,
                            onChanged: _sensoryReady
                                ? (value) => unawaited(
                                      _setAuroraSensoryLinkEnabled(value),
                                    )
                                : null,
                            activeThumbColor: DS.primaryBase,
                          ),
                          const SizedBox(height: DS.spacing8),
                          Text(
                            l10n.sensoryAmbientSceneTitle,
                            style:
                                DS.labelSmall.copyWith(color: DS.textSecondary),
                          ),
                          const SizedBox(height: DS.spacing8),
                          Wrap(
                            spacing: DS.spacing8,
                            runSpacing: DS.spacing8,
                            children: AmbientScene.values
                                .map(
                                  (scene) => ChoiceChip(
                                    label: Text(scene.label),
                                    selected: _ambientScene == scene,
                                    onSelected: _sensoryReady
                                        ? (_) =>
                                            unawaited(_setAmbientScene(scene))
                                        : null,
                                  ),
                                )
                                .toList(),
                          ),
                          const SizedBox(height: DS.spacing10),
                          Text(
                            l10n.sensoryAmbientVolumeTitle,
                            style:
                                DS.labelSmall.copyWith(color: DS.textSecondary),
                          ),
                          Row(
                            children: [
                              const Icon(Icons.volume_mute_rounded, size: 18),
                              Expanded(
                                child: Slider(
                                  value: _ambientVolume,
                                  divisions: 10,
                                  onChanged: _sensoryReady && _soundEnabled
                                      ? (value) =>
                                          setState(() => _ambientVolume = value)
                                      : null,
                                  onChangeEnd: _sensoryReady && _soundEnabled
                                      ? (value) =>
                                          unawaited(_setAmbientVolume(value))
                                      : null,
                                ),
                              ),
                              const Icon(Icons.surround_sound_rounded,
                                  size: 18),
                            ],
                          ),
                        ],
                      ),
                      crossFadeState: _sensoryExpanded
                          ? CrossFadeState.showSecond
                          : CrossFadeState.showFirst,
                      duration: const Duration(milliseconds: 250),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.accessibility_new_rounded),
                  title: Text(
                    I18nService.instance.isChinese
                        ? '无障碍与低负荷'
                        : 'Accessibility',
                  ),
                  subtitle: Text(
                    I18nService.instance.isChinese
                        ? '字体、对比度、屏幕阅读、触控、动效、TTS 与震动反馈'
                        : 'Font scale, contrast, screen reader, touch, motion, TTS, and haptics',
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const AccessibilitySettingsScreen(),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildCollapsibleHeader(
                      icon: Icons.psychology,
                      title: l10n.learningMode,
                      subtitle: l10n.learningModeSubtitle,
                      expanded: _learningExpanded,
                      onToggle: () => setState(
                          () => _learningExpanded = !_learningExpanded),
                    ),
                    AnimatedCrossFade(
                      firstChild: const SizedBox(width: double.infinity),
                      secondChild: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SizedBox(height: DS.spacing12),
                          Text(
                            l10n.dragToAdjust,
                            style: DS.bodySmall.copyWith(
                              color: DS.textSecondary,
                            ),
                          ),
                          const SizedBox(height: DS.spacing12),
                          LearningModeControl(
                            depth: learningPrefs.depth,
                            curiosity: learningPrefs.curiosity,
                            onChanged: (d, c) {
                              _scheduleLearningPreferenceUpdate(
                                depth: d,
                                curiosity: c,
                              );
                            },
                          ),
                          const SizedBox(height: DS.spacing12),
                          _buildInlineStatusMessage(
                            _learningPreferenceStatus ??
                                l10n.learningPreferenceAutoSaveHint,
                            isError: _learningPreferenceStatusIsError,
                          ),
                          const SizedBox(height: DS.spacing24),
                          _buildSectionHeader(
                            Icons.auto_awesome,
                            l10n.capsuleGeneration,
                          ),
                          const SizedBox(height: DS.spacing12),
                          CapsuleGenerationPreview(
                            depthPreference: learningPrefs.depth,
                            curiosityPreference: learningPrefs.curiosity,
                          ),
                          const SizedBox(height: DS.spacing12),
                          SparkleButton(
                            expand: true,
                            label: _isGenerating
                                ? l10n.generating
                                : l10n.generateNow,
                            icon: _isGenerating
                                ? null
                                : const Icon(Icons.auto_awesome),
                            onPressed: _isGenerating
                                ? null
                                : () {
                                    unawaited(
                                      _requestCapsuleGeneration(context, l10n),
                                    );
                                  },
                            loading: _isGenerating,
                          ),
                          const SizedBox(height: DS.spacing24),
                          _buildSectionHeader(
                              Icons.schedule, l10n.weeklyAgenda),
                          const SizedBox(height: DS.spacing12),
                          _buildWeeklyAgendaSection(
                            context,
                            l10n,
                            weeklyAgenda,
                          ),
                        ],
                      ),
                      crossFadeState: _learningExpanded
                          ? CrossFadeState.showSecond
                          : CrossFadeState.showFirst,
                      duration: const Duration(milliseconds: 250),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.palette_outlined),
                  title: Text(l10n.visualElementsTitle),
                  subtitle: Text(l10n.visualElementsEntrySubtitle),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push(VisualElementsRoutes.basePath),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.auto_stories_outlined),
                  title: Text(l10n.studyMaterialsTitle),
                  subtitle: Text(l10n.studyMaterialsEntrySubtitle),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push(DocumentLibraryRoutes.library),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildCollapsibleHeader(
                      icon: Icons.music_note_rounded,
                      title: l10n.bgmSectionTitle,
                      subtitle: _bgmReady
                          ? _bgmSectionSubtitle()
                          : l10n.bgmLoadingSubtitle,
                      expanded: _bgmExpanded,
                      onToggle: () =>
                          setState(() => _bgmExpanded = !_bgmExpanded),
                    ),
                    AnimatedCrossFade(
                      firstChild: const SizedBox(width: double.infinity),
                      secondChild: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(l10n.bgmEnabledTitle),
                            subtitle: Text(l10n.bgmEnabledSubtitle),
                            value: _bgmEnabled,
                            onChanged: _bgmReady
                                ? (value) => unawaited(_setBgmEnabled(value))
                                : null,
                            activeThumbColor: DS.primaryBase,
                          ),
                          const SizedBox(height: DS.spacing8),
                          Text(
                            l10n.bgmPlaybackStrategyTitle,
                            style:
                                DS.labelSmall.copyWith(color: DS.textSecondary),
                          ),
                          const SizedBox(height: DS.spacing8),
                          Wrap(
                            spacing: DS.spacing8,
                            runSpacing: DS.spacing8,
                            children: BgmMode.values
                                .map(
                                  (mode) => ChoiceChip(
                                    label: Text(_bgmModeLabel(l10n, mode)),
                                    selected: _bgmMode == mode,
                                    onSelected: _bgmReady
                                        ? (_) => unawaited(_setBgmMode(mode))
                                        : null,
                                  ),
                                )
                                .toList(),
                          ),
                          const SizedBox(height: DS.spacing10),
                          _buildBgmLibrarySummaryCard(),
                          const SizedBox(height: DS.spacing12),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(DS.spacing12),
                            decoration: BoxDecoration(
                              borderRadius: DS.borderRadius12,
                              color: Color.alphaBlend(
                                DS.primaryBase.withValues(alpha: 0.06),
                                DS.surfaceSecondary,
                              ),
                            ),
                            child: Text(
                              _bgmModeDescription(l10n, _bgmMode),
                              style: DS.bodySmall.copyWith(
                                color: DS.textSecondary,
                                height: 1.4,
                              ),
                            ),
                          ),
                          const SizedBox(height: DS.spacing12),
                          _buildBgmNowPlayingCard(),
                          const SizedBox(height: DS.spacing12),
                          const SizedBox(height: DS.spacing8),
                          Text(
                            l10n.bgmVolume,
                            style:
                                DS.labelSmall.copyWith(color: DS.textSecondary),
                          ),
                          Row(
                            children: [
                              const Icon(Icons.volume_down_rounded, size: 18),
                              Expanded(
                                child: Slider(
                                  value: _bgmVolume,
                                  divisions: 10,
                                  onChanged: _bgmEnabled && _bgmReady
                                      ? (value) =>
                                          setState(() => _bgmVolume = value)
                                      : null,
                                  onChangeEnd: _bgmEnabled && _bgmReady
                                      ? (value) =>
                                          unawaited(_setBgmVolume(value))
                                      : null,
                                ),
                              ),
                              const Icon(Icons.volume_up_rounded, size: 18),
                            ],
                          ),
                          Text(
                            l10n.bgmScenePreference,
                            style:
                                DS.labelSmall.copyWith(color: DS.textSecondary),
                          ),
                          const SizedBox(height: DS.spacing8),
                          Wrap(
                            spacing: DS.spacing8,
                            runSpacing: DS.spacing8,
                            children: BgmPalette.values
                                .map(
                                  (palette) => Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: DS.spacing6,
                                      vertical: DS.spacing4,
                                    ),
                                    decoration: BoxDecoration(
                                      color: DS.surfaceSecondary,
                                      borderRadius: DS.borderRadius16,
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        ChoiceChip(
                                          label: Text(
                                              _bgmPaletteLabel(l10n, palette)),
                                          selected: _bgmPalette == palette,
                                          onSelected: _bgmReady
                                              ? (_) => unawaited(
                                                    _setBgmPalette(palette),
                                                  )
                                              : null,
                                        ),
                                        IconButton(
                                          tooltip: l10n.bgmPreviewTooltip(
                                              _bgmPaletteLabel(l10n, palette)),
                                          iconSize: 18,
                                          visualDensity: VisualDensity.compact,
                                          onPressed: _bgmEnabled && _bgmReady
                                              ? () => unawaited(
                                                    _previewBgmPalette(palette),
                                                  )
                                              : null,
                                          icon: _previewingPalette == palette
                                              ? const SizedBox(
                                                  width: 16,
                                                  height: 16,
                                                  child:
                                                      CircularProgressIndicator(
                                                    strokeWidth: 2,
                                                  ),
                                                )
                                              : const Icon(
                                                  Icons.play_arrow_rounded),
                                        ),
                                      ],
                                    ),
                                  ),
                                )
                                .toList(),
                          ),
                          const SizedBox(height: DS.spacing10),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(DS.spacing12),
                            decoration: BoxDecoration(
                              borderRadius: DS.borderRadius12,
                              color: Color.alphaBlend(
                                DS.info.withValues(alpha: 0.06),
                                DS.surfaceSecondary,
                              ),
                            ),
                            child: Text(
                              _bgmPaletteDescription(l10n, _bgmPalette),
                              style: DS.bodySmall.copyWith(
                                color: DS.textSecondary,
                                height: 1.4,
                              ),
                            ),
                          ),
                          const SizedBox(height: DS.spacing12),
                          InkWell(
                            borderRadius: DS.borderRadius12,
                            onTap: () => setState(() =>
                                _bgmAdvancedExpanded = !_bgmAdvancedExpanded),
                            child: Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(DS.spacing12),
                              decoration: BoxDecoration(
                                borderRadius: DS.borderRadius12,
                                color: Color.alphaBlend(
                                  DS.brandPrimary.withValues(alpha: 0.05),
                                  DS.surfaceSecondary,
                                ),
                                border: Border.all(
                                  color:
                                      DS.brandPrimary.withValues(alpha: 0.14),
                                ),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.tune_rounded, size: 18),
                                  const SizedBox(width: DS.spacing10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          l10n.bgmAdvancedControls,
                                          style: DS.bodyLarge,
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          l10n.bgmAdvancedControlsSubtitle,
                                          style: DS.bodySmall.copyWith(
                                            color: DS.textSecondary,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Icon(
                                    _bgmAdvancedExpanded
                                        ? Icons.expand_less_rounded
                                        : Icons.expand_more_rounded,
                                  ),
                                ],
                              ),
                            ),
                          ),
                          AnimatedCrossFade(
                            firstChild: const SizedBox(width: double.infinity),
                            secondChild: Padding(
                              padding: const EdgeInsets.only(top: DS.spacing12),
                              child: _buildBgmAdvancedControls(),
                            ),
                            crossFadeState: _bgmAdvancedExpanded
                                ? CrossFadeState.showSecond
                                : CrossFadeState.showFirst,
                            duration: const Duration(milliseconds: 220),
                          ),
                        ],
                      ),
                      crossFadeState: _bgmExpanded
                          ? CrossFadeState.showSecond
                          : CrossFadeState.showFirst,
                      duration: const Duration(milliseconds: 250),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              GraphiteCardSurface(
                child: Column(
                  children: [
                    _buildCollapsibleHeader(
                      icon: Icons.brightness_6_outlined,
                      title: '${l10n.theme} & AI',
                      subtitle: l10n.themeAiSectionSubtitle,
                      expanded: _themeExpanded,
                      onToggle: () =>
                          setState(() => _themeExpanded = !_themeExpanded),
                    ),
                    AnimatedCrossFade(
                      firstChild: const SizedBox(width: double.infinity),
                      secondChild: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildSettingsDropdownField<AppThemeMode>(
                            value: ref.watch(appThemeModeProvider),
                            items: [
                              DropdownMenuItem(
                                value: AppThemeMode.system,
                                child: Text(l10n.followSystem),
                              ),
                              DropdownMenuItem(
                                value: AppThemeMode.light,
                                child: Text(l10n.lightMode),
                              ),
                              DropdownMenuItem(
                                value: AppThemeMode.dark,
                                child: Text(l10n.darkMode),
                              ),
                            ],
                            onChanged: (newValue) {
                              if (newValue != null) {
                                ref
                                    .read(themeManagerProvider)
                                    .setAppThemeMode(newValue);
                              }
                            },
                          ),
                          const Divider(height: DS.spacing24),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(l10n.enterToSend),
                            subtitle: Text(l10n.enterToSendDescription),
                            value: enterToSend,
                            onChanged: (v) => ref
                                .read(enterToSendProvider.notifier)
                                .setEnabled(v),
                            activeThumbColor: DS.primaryBase,
                          ),
                          const Divider(height: DS.spacing24),
                          ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: const Icon(Icons.tune),
                            title: Text(l10n.aiReasoningTitle),
                            subtitle: Text(l10n.aiReasoningSubtitle),
                          ),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: Wrap(
                              spacing: DS.spacing8,
                              runSpacing: DS.spacing8,
                              children: [
                                ChoiceChip(
                                  label: Text(l10n.aiReasoningFastLabel),
                                  selected: aiReasoningMode == 'fast',
                                  onSelected: (_) => unawaited(
                                    _applyAiReasoningMode(
                                      context,
                                      l10n,
                                      'fast',
                                    ),
                                  ),
                                ),
                                ChoiceChip(
                                  label: Text(l10n.aiReasoningBalancedLabel),
                                  selected: aiReasoningMode == 'balanced',
                                  onSelected: (_) => unawaited(
                                    _applyAiReasoningMode(
                                      context,
                                      l10n,
                                      'balanced',
                                    ),
                                  ),
                                ),
                                ChoiceChip(
                                  label: Text(l10n.aiReasoningDeepLabel),
                                  selected: aiReasoningMode == 'deep',
                                  onSelected: (_) => unawaited(
                                    _applyAiReasoningMode(
                                      context,
                                      l10n,
                                      'deep',
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: DS.spacing12),
                          _buildSelectionPreviewCard(
                            icon: Icons.auto_awesome_rounded,
                            title: _aiReasoningModeTitle(l10n, aiReasoningMode),
                            description: _aiReasoningModeDescription(
                              l10n,
                              aiReasoningMode,
                            ),
                          ),
                          const SizedBox(height: DS.spacing16),
                          _buildEmotionAdaptiveModeControl(emotionState),
                          const SizedBox(height: DS.spacing16),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(l10n.showChatContextToggleTitle),
                            subtitle: Text(l10n.showChatContextToggleSubtitle),
                            value: showChatContextToggle,
                            onChanged: (value) => ref
                                .read(showChatContextToggleProvider.notifier)
                                .setEnabled(value),
                            activeThumbColor: DS.primaryBase,
                          ),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(l10n.showChatPredictionDockTitle),
                            subtitle: Text(l10n.showChatPredictionDockSubtitle),
                            value: showChatPredictionDock,
                            onChanged: (value) => ref
                                .read(showChatPredictionDockProvider.notifier)
                                .setEnabled(value),
                            activeThumbColor: DS.primaryBase,
                          ),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(l10n.showChatTransparencyCapsuleTitle),
                            subtitle:
                                Text(l10n.showChatTransparencyCapsuleSubtitle),
                            value: showChatTransparencyCapsule,
                            onChanged: (value) => ref
                                .read(showChatTransparencyCapsuleProvider
                                    .notifier)
                                .setEnabled(value),
                            activeThumbColor: DS.primaryBase,
                          ),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(l10n.chatPureMode),
                            subtitle: Text(
                              l10n.chatPureModeSubtitle,
                            ),
                            value: chatPureMode,
                            onChanged: (value) => ref
                                .read(chatPureModeProvider.notifier)
                                .setEnabled(value),
                            activeThumbColor: DS.primaryBase,
                          ),
                          const SizedBox(height: DS.spacing8),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: Text(
                              l10n.motionIntensity,
                              style: DS.labelSmall.copyWith(
                                color: DS.textSecondary,
                              ),
                            ),
                          ),
                          const SizedBox(height: DS.spacing8),
                          Wrap(
                            spacing: DS.spacing8,
                            runSpacing: DS.spacing8,
                            children: MotionIntensityLevel.values
                                .map(
                                  (level) => ChoiceChip(
                                    label: Text(
                                        _motionIntensityLabel(l10n, level)),
                                    selected: motionIntensityLevel == level,
                                    onSelected: (_) => ref
                                        .read(motionIntensityLevelProvider
                                            .notifier)
                                        .setLevel(level),
                                  ),
                                )
                                .toList(),
                          ),
                          const SizedBox(height: DS.spacing10),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(DS.spacing12),
                            decoration: BoxDecoration(
                              borderRadius: DS.borderRadius12,
                              color: Color.alphaBlend(
                                DS.primaryBase.withValues(alpha: 0.05),
                                DS.surfaceSecondary,
                              ),
                            ),
                            child: Text(
                              _motionIntensityDescription(
                                  l10n, motionIntensityLevel),
                              style: DS.bodySmall.copyWith(
                                color: DS.textSecondary,
                                height: 1.4,
                              ),
                            ),
                          ),
                          const SizedBox(height: DS.spacing12),
                          aiUsageSummary.when(
                            data: (summary) => _buildAiUsageSummary(summary),
                            loading: () =>
                                const LinearProgressIndicator(minHeight: 3),
                            error: (_, __) => Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: DS.surfaceSecondary,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                l10n.aiUsagePanelUnavailable,
                              ),
                            ),
                          ),
                          const SizedBox(height: DS.spacing12),
                          aiOpsDashboard.when(
                            data: (dashboard) => Column(
                              children: [
                                _buildAiUserViewPanel(
                                  dashboard,
                                  predictionAnalytics.valueOrNull,
                                ),
                                const SizedBox(height: DS.spacing12),
                                _buildAiDeveloperViewPanel(
                                  dashboard,
                                  predictionAnalytics.valueOrNull,
                                ),
                              ],
                            ),
                            loading: () =>
                                const LinearProgressIndicator(minHeight: 3),
                            error: (_, __) => Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: DS.surfaceSecondary,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                l10n.aiOpsPanelUnavailable,
                              ),
                            ),
                          ),
                        ],
                      ),
                      crossFadeState: _themeExpanded
                          ? CrossFadeState.showSecond
                          : CrossFadeState.showFirst,
                      duration: const Duration(milliseconds: 250),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              // ── Aurora Communication Preferences ──
              GraphiteCardSurface(
                child: Column(
                  children: [
                    _buildCollapsibleHeader(
                      icon: Icons.auto_awesome_outlined,
                      title: I18nService.instance.isChinese
                          ? 'Aurora 沟通偏好'
                          : 'Aurora Preferences',
                      subtitle: I18nService.instance.isChinese
                          ? '控制 Aurora 如何与你互动'
                          : 'Control how Aurora interacts with you',
                      expanded: _auroraPrefsExpanded,
                      onToggle: () => setState(
                          () => _auroraPrefsExpanded = !_auroraPrefsExpanded),
                    ),
                    AnimatedCrossFade(
                      firstChild: const SizedBox(width: double.infinity),
                      secondChild: Builder(
                        builder: (context) {
                          final prefsAsync =
                              ref.watch(auroraPreferencesProvider);
                          return prefsAsync.when(
                            data: (prefs) => Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                _buildAuroraPrefSegmented(
                                  label: I18nService.instance.isChinese
                                      ? '分析深度'
                                      : 'Analysis Depth',
                                  options: [
                                    (
                                      I18nService.instance.isChinese
                                          ? '少分析我'
                                          : 'Light',
                                      'light',
                                      Icons.insights_outlined,
                                    ),
                                    (
                                      I18nService.instance.isChinese
                                          ? '多分析我'
                                          : 'Deep',
                                      'deep',
                                      Icons.psychology_outlined,
                                    ),
                                  ],
                                  selected: prefs.analysisDepth,
                                  onChanged: (v) => ref
                                      .read(auroraPreferencesProvider.notifier)
                                      .updatePreference(
                                          'aurora_analysis_depth', v),
                                ),
                                const Divider(height: DS.spacing24),
                                _buildAuroraPrefSegmented(
                                  label: I18nService.instance.isChinese
                                      ? '沟通方式'
                                      : 'Directness',
                                  options: [
                                    (
                                      I18nService.instance.isChinese
                                          ? '直接安排我'
                                          : 'Direct',
                                      'direct',
                                      Icons.fast_forward_outlined,
                                    ),
                                    (
                                      I18nService.instance.isChinese
                                          ? '引导我'
                                          : 'Guided',
                                      'guided',
                                      Icons.tour_outlined,
                                    ),
                                  ],
                                  selected: prefs.directness,
                                  onChanged: (v) => ref
                                      .read(auroraPreferencesProvider.notifier)
                                      .updatePreference('aurora_directness', v),
                                ),
                                const Divider(height: DS.spacing24),
                                _buildAuroraPrefSegmented(
                                  label: I18nService.instance.isChinese
                                      ? '解释详细程度'
                                      : 'Explanation Level',
                                  options: [
                                    (
                                      I18nService.instance.isChinese
                                          ? '多解释原因'
                                          : 'Detailed',
                                      'detailed',
                                      Icons.article_outlined,
                                    ),
                                    (
                                      I18nService.instance.isChinese
                                          ? '简洁'
                                          : 'Brief',
                                      'brief',
                                      Icons.short_text_outlined,
                                    ),
                                  ],
                                  selected: prefs.explanationLevel,
                                  onChanged: (v) => ref
                                      .read(auroraPreferencesProvider.notifier)
                                      .updatePreference(
                                          'aurora_explanation_level', v),
                                ),
                                const Divider(height: DS.spacing24),
                                _buildAuroraPrefSegmented(
                                  label: I18nService.instance.isChinese
                                      ? '压力提醒风格'
                                      : 'Pressure Style',
                                  options: [
                                    (
                                      I18nService.instance.isChinese
                                          ? '不用压力提醒'
                                          : 'Gentle',
                                      'gentle',
                                      Icons.spa_outlined,
                                    ),
                                    (
                                      I18nService.instance.isChinese
                                          ? '可用压力'
                                          : 'Motivating',
                                      'motivating',
                                      Icons.fitness_center_outlined,
                                    ),
                                  ],
                                  selected: prefs.pressureStyle,
                                  onChanged: (v) => ref
                                      .read(auroraPreferencesProvider.notifier)
                                      .updatePreference(
                                          'aurora_pressure_style', v),
                                ),
                                const SizedBox(height: DS.spacing12),
                              ],
                            ),
                            loading: () => const Center(
                                child: CircularProgressIndicator()),
                            error: (_, __) => Padding(
                              padding: const EdgeInsets.all(DS.spacing16),
                              child: Text(
                                I18nService.instance.isChinese
                                    ? '加载偏好失败'
                                    : 'Failed to load preferences',
                                style: DS.bodySmall
                                    .copyWith(color: DS.textSecondary),
                              ),
                            ),
                          );
                        },
                      ),
                      crossFadeState: _auroraPrefsExpanded
                          ? CrossFadeState.showSecond
                          : CrossFadeState.showFirst,
                      duration: const Duration(milliseconds: 250),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              // Notification permission status card
              _buildNotificationPermissionCard(context, l10n),
              const SizedBox(height: DS.spacing20),
              GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.notifications_active_outlined),
                      title: Text(l10n.notificationSettings),
                      subtitle: Text(
                        notificationPrefs.isLoaded
                            ? l10n.notificationManageSubtitle
                            : l10n.notificationLoadingPrefs,
                      ),
                    ),
                    if (!notificationPrefs.isLoaded)
                      const LinearProgressIndicator(minHeight: 3)
                    else ...[
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(l10n.notificationSystem),
                        subtitle: Text(l10n.notificationSystemSubtitle),
                        value: notificationPrefs.enableSystem,
                        onChanged: (value) => unawaited(
                          _updateNotificationPreferences(
                            context,
                            enableSystem: value,
                          ),
                        ),
                        activeThumbColor: DS.primaryBase,
                      ),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(l10n.notificationInterventions),
                        subtitle: Text(l10n.notificationInterventionsSubtitle),
                        value: notificationPrefs.enableInterventions,
                        onChanged: (value) => unawaited(
                          _updateNotificationPreferences(
                            context,
                            enableInterventions: value,
                          ),
                        ),
                        activeThumbColor: DS.primaryBase,
                      ),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(l10n.notificationReminders),
                        subtitle: Text(l10n.notificationRemindersSubtitle),
                        onChanged: (value) => unawaited(
                          _updateNotificationTypePreference(
                            context,
                            type: 'reminder',
                            enabled: value,
                          ),
                        ),
                        value: _isNotificationTypeEnabled(
                          notificationPrefs,
                          'reminder',
                        ),
                        activeThumbColor: DS.primaryBase,
                      ),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(l10n.notificationSpacedRepetition),
                        subtitle:
                            Text(l10n.notificationSpacedRepetitionSubtitle),
                        onChanged: (value) => unawaited(
                          _updateNotificationTypePreference(
                            context,
                            type: 'spaced_repetition',
                            enabled: value,
                          ),
                        ),
                        value: _isNotificationTypeEnabled(
                          notificationPrefs,
                          'spaced_repetition',
                        ),
                        activeThumbColor: DS.primaryBase,
                      ),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(l10n.notificationWeeklyReport),
                        subtitle: Text(l10n.notificationWeeklyReportSubtitle),
                        onChanged: (value) => unawaited(
                          _updateNotificationTypePreference(
                            context,
                            type: 'weekly_report',
                            enabled: value,
                          ),
                        ),
                        value: _isNotificationTypeEnabled(
                          notificationPrefs,
                          'weekly_report',
                        ),
                        activeThumbColor: DS.primaryBase,
                      ),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(l10n.notificationMilestone),
                        subtitle: Text(l10n.notificationMilestoneSubtitle),
                        onChanged: (value) => unawaited(
                          _updateNotificationTypePreference(
                            context,
                            type: 'milestone',
                            enabled: value,
                          ),
                        ),
                        value: _isNotificationTypeEnabled(
                          notificationPrefs,
                          'milestone',
                        ),
                        activeThumbColor: DS.primaryBase,
                      ),
                      const Divider(height: DS.spacing24),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.tune_rounded),
                        title: Text(l10n.notificationLevel),
                        subtitle: Text(
                          _notificationLevelDescription(
                            l10n,
                            notificationLevel,
                          ),
                        ),
                      ),
                      _buildSettingsDropdownField<String>(
                        value: notificationLevel,
                        items: [
                          DropdownMenuItem(
                            value: 'minimal',
                            child: Text(
                              _notificationLevelLabel(l10n, 'minimal'),
                            ),
                          ),
                          DropdownMenuItem(
                            value: 'standard',
                            child: Text(
                              _notificationLevelLabel(l10n, 'standard'),
                            ),
                          ),
                          DropdownMenuItem(
                            value: 'verbose',
                            child: Text(
                              _notificationLevelLabel(l10n, 'verbose'),
                            ),
                          ),
                        ],
                        onChanged: (level) {
                          if (level == null) {
                            return;
                          }
                          unawaited(
                            _updateNotificationPreferences(
                              context,
                              notificationLevel: level,
                              successMessage: l10n.notificationLevelSwitched(
                                  _notificationLevelLabel(l10n, level)),
                            ),
                          );
                        },
                      ),
                      const SizedBox(height: DS.spacing12),
                      _buildSelectionPreviewCard(
                        icon: Icons.notifications_active_outlined,
                        title: l10n.notificationLevelPreviewTitle(
                            _notificationLevelLabel(l10n, notificationLevel)),
                        description: _notificationLevelPreview(
                          l10n,
                          notificationLevel,
                        ),
                      ),
                      const Divider(height: DS.spacing24),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(l10n.notificationQuietHours),
                        subtitle: Text(
                          notificationPrefs.quietHoursEnabled
                              ? '${notificationPrefs.quietHoursStart} - ${notificationPrefs.quietHoursEnd}'
                              : l10n.notificationQuietHoursSubtitle,
                        ),
                        value: notificationPrefs.quietHoursEnabled,
                        onChanged: (value) {
                          final nextStart = notificationPrefs.quietHoursStart;
                          final nextEnd = notificationPrefs.quietHoursEnd;
                          unawaited(
                            _updateNotificationPreferences(
                              context,
                              quietHoursEnabled: value,
                              quietHoursStart: nextStart,
                              quietHoursEnd: nextEnd,
                            ),
                          );
                        },
                        activeThumbColor: DS.primaryBase,
                      ),
                      if (notificationPrefs.quietHoursEnabled) ...[
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.nights_stay_outlined),
                          title: Text(l10n.notificationQuietHoursStart),
                          subtitle: Text(notificationPrefs.quietHoursStart),
                          trailing: const Icon(Icons.chevron_right_rounded),
                          onTap: () => unawaited(
                            _pickQuietHoursTime(
                              context,
                              isStart: true,
                              currentValue: notificationPrefs.quietHoursStart,
                            ),
                          ),
                        ),
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.wb_sunny_outlined),
                          title: Text(l10n.notificationQuietHoursEnd),
                          subtitle: Text(notificationPrefs.quietHoursEnd),
                          trailing: const Icon(Icons.chevron_right_rounded),
                          onTap: () => unawaited(
                            _pickQuietHoursTime(
                              context,
                              isStart: false,
                              currentValue: notificationPrefs.quietHoursEnd,
                            ),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.only(top: DS.spacing4),
                          child: _buildInlineStatusMessage(
                            l10n.notificationQuietHoursHint,
                          ),
                        ),
                      ],
                    ],
                    const Divider(height: DS.spacing24),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.alarm_outlined),
                      title: Text(l10n.taskReminderSettingsTitle),
                      subtitle: Text(
                        _taskReminderSummary(l10n, taskReminderConfig),
                      ),
                      trailing: const Icon(Icons.chevron_right_rounded),
                      onTap: () => context.push(UserRoutes.taskReminders),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              GraphiteCardSurface(
                child: Column(
                  children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(l10n.enableNotifications),
                      subtitle: Text(l10n.notificationReceiveSmartPush),
                      value: pushPrefs.enableCuriosity,
                      onChanged: (v) async {
                        if (v) {
                          final granted = await ref
                              .read(
                                notificationPermissionStatusProvider.notifier,
                              )
                              .requestPermission();
                          if (!granted) {
                            if (context.mounted) {
                              _showOpenSettingsDialog(context);
                            }
                            return;
                          }
                        }
                        await ref
                            .read(pushPreferencesProvider.notifier)
                            .updatePreferences(enableCuriosity: v);
                      },
                      activeThumbColor: DS.primaryBase,
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(l10n.smartReminders),
                      subtitle: Text(l10n.pushMicroTasks),
                      value: pushPrefs.dailyCap > 0,
                      onChanged: (v) {
                        ref
                            .read(pushPreferencesProvider.notifier)
                            .updatePreferences(
                              dailyCap: v ? 5 : 0,
                            );
                      },
                      activeThumbColor: DS.primaryBase,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              GraphiteCardSurface(
                child: Column(
                  children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(l10n.enableTransparentMode),
                      subtitle: Text(l10n.showStatusOverview),
                      value: transparentMode,
                      onChanged: (v) => ref
                          .read(transparencyLevelProvider.notifier)
                          .setLevel(v ? 2 : 0),
                      activeThumbColor: DS.primaryBase,
                    ),
                    if (transparentMode) ...[
                      const SizedBox(height: DS.spacing8),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(l10n.transparencyLevel),
                        subtitle: Text(
                          '${l10n.basic}/${l10n.standard}/${l10n.advanced}',
                        ),
                      ),
                      _buildSettingsDropdownField<int>(
                        value: transparencyLevel,
                        items: [
                          DropdownMenuItem(
                            value: 0,
                            child: Text(l10n.cancel),
                          ),
                          DropdownMenuItem(
                            value: 1,
                            child: Text(l10n.basic),
                          ),
                          DropdownMenuItem(
                            value: 2,
                            child: Text(l10n.standard),
                          ),
                          DropdownMenuItem(
                            value: 3,
                            child: Text(l10n.advanced),
                          ),
                        ],
                        onChanged: (level) {
                          if (level != null) {
                            ref
                                .read(transparencyLevelProvider.notifier)
                                .setLevel(level);
                          }
                        },
                      ),
                    ],
                    const Divider(height: DS.spacing24),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(l10n.systemFeedback),
                      subtitle: Text(l10n.controlUpdateDetails),
                    ),
                    _buildSettingsDropdownField<int>(
                      value: systemUpdateLevel,
                      items: [
                        DropdownMenuItem(value: 0, child: Text(l10n.silent)),
                        DropdownMenuItem(
                          value: 1,
                          child: Text(l10n.summary),
                        ),
                        DropdownMenuItem(
                          value: 2,
                          child: Text(l10n.detailed),
                        ),
                      ],
                      onChanged: (level) {
                        if (level != null) {
                          ref
                              .read(systemUpdateLevelProvider.notifier)
                              .setLevel(level);
                        }
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              GraphiteCardSurface(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.sync),
                  title: Text(l10n.syncCenter),
                  subtitle: Text(l10n.viewOfflineQueue),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push(UserRoutes.syncCenter),
                ),
              ),
              const SizedBox(height: DS.spacing12),
              GraphiteCardSurface(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.hub_outlined),
                  title: Text(l10n.aiExecutionEngine),
                  subtitle: Text(l10n.aiExecutionEngineSubtitle),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push(UserRoutes.openClawSettings),
                ),
              ),
              const SizedBox(height: DS.spacing20),
              // UX-010: Data & Privacy management entries
              _buildSectionHeader(Icons.shield_outlined, 'Data & Privacy'),
              const SizedBox(height: DS.spacing12),
              GraphiteCardSurface(
                child: Column(
                  children: [
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.psychology_outlined),
                      title: const Text('Memory Settings'),
                      subtitle: const Text('Manage what Sparkle remembers'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => context.push('/settings/memory'),
                    ),
                    const Divider(height: 1, indent: 48),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.group_outlined),
                      title: const Text('Community Intelligence'),
                      subtitle: const Text('Control shared learning insights'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => context.push('/settings/community'),
                    ),
                    const Divider(height: 1, indent: 48),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.source_outlined),
                      title: const Text('Source Permissions'),
                      subtitle: const Text('Manage material access'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => context.push('/settings/sources'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              _buildSectionHeader(Icons.language_rounded, l10n.language),
              const SizedBox(height: DS.spacing12),
              GraphiteCardSurface(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.language_rounded),
                  title: Text(l10n.language),
                  subtitle: Text(
                    ref.watch(localeProvider).languageCode == 'zh'
                        ? l10n.languageChinese
                        : l10n.languageEnglish,
                  ),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => _showLanguageDialog(context, ref, l10n),
                ),
              ),
              const SizedBox(height: DS.spacing64),
              Center(
                child: GestureDetector(
                  onLongPress: () {
                    showSensoryDialog<void>(
                      context: context,
                      builder: (context) => const ChaosControlDialog(),
                    );
                  },
                  child: Text(
                    l10n.version,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: DS.brandPrimaryConst,
                      fontSize: DS.fontSizeXs,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing32),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _requestCapsuleGeneration(
    BuildContext context,
    AppLocalizations l10n,
  ) async {
    setState(() => _isGenerating = true);

    try {
      final capsule =
          await ref.read(capsuleRepositoryProvider).generateCapsule();
      await ref.read(capsuleProvider.notifier).fetchTodayCapsules();
      await ref.read(capsuleStatsProvider.notifier).fetchStats();
      await ref.read(generationJobsProvider.notifier).fetchJobs();

      if (mounted) {
        AppFeedback.success(context, l10n.capsuleGenerated);
        await showSensoryModalBottomSheet<void>(
          context: context,
          isScrollControlled: true,
          builder: (sheetContext) => SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing16),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    capsule.title,
                    style: Theme.of(sheetContext).textTheme.titleLarge,
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    capsule.content.trim().isEmpty
                        ? l10n.capsuleGeneratedEmpty
                        : capsule.content.trim(),
                    style:
                        Theme.of(sheetContext).textTheme.bodyMedium?.copyWith(
                              color: DS.textSecondary,
                            ),
                    maxLines: 4,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: DS.spacing16),
                  SparkleButton(
                    expand: true,
                    label: l10n.capsuleViewNew,
                    icon: const Icon(Icons.auto_awesome),
                    onPressed: () {
                      Navigator.of(sheetContext).pop();
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) =>
                              CapsuleDetailScreen(capsuleId: capsule.id),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
          context,
          l10n.generationFailedWithDetail(e.toString()),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isGenerating = false);
      }
    }
  }

  void _showLanguageDialog(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations l10n,
  ) {
    final currentLocale = ref.read(localeProvider);

    showSensoryDialog<void>(
      context: context,
      builder: (dialogContext) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: DS.surfaceRoleColor(SparkleSurfaceRole.modal),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                l10n.language,
                style: DS.titleLarge.copyWith(color: DS.textPrimary),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                l10n.languageDialogDescription,
                style: Theme.of(dialogContext).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
              const SizedBox(height: DS.spacing16),
              _buildLanguageOption(
                dialogContext,
                title: l10n.languageChinese,
                subtitle: l10n.languageChineseDescription,
                selected: currentLocale.languageCode == 'zh',
                onTap: () {
                  ref
                      .read(localeProvider.notifier)
                      .setLocale(const Locale('zh'));
                  Navigator.pop(dialogContext);
                },
              ),
              const SizedBox(height: DS.spacing8),
              _buildLanguageOption(
                dialogContext,
                title: l10n.languageEnglish,
                subtitle: l10n.languageEnglishDescription,
                selected: currentLocale.languageCode == 'en',
                onTap: () {
                  ref
                      .read(localeProvider.notifier)
                      .setLocale(const Locale('en'));
                  Navigator.pop(dialogContext);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _updateNotificationPreferences(
    BuildContext context, {
    bool? enableSystem,
    bool? enableInterventions,
    List<String>? disabledTypes,
    String? notificationLevel,
    bool? quietHoursEnabled,
    String? quietHoursStart,
    String? quietHoursEnd,
    String? successMessage,
  }) async {
    try {
      await ref
          .read(notificationPreferenceSettingsProvider.notifier)
          .updatePreferences(
            enableSystem: enableSystem,
            enableInterventions: enableInterventions,
            disabledTypes: disabledTypes,
            notificationLevel: notificationLevel,
            quietHoursEnabled: quietHoursEnabled,
            quietHoursStart: quietHoursStart,
            quietHoursEnd: quietHoursEnd,
          );
      if (!context.mounted ||
          successMessage == null ||
          successMessage.isEmpty) {
        return;
      }
      AppFeedback.success(context, successMessage);
    } catch (e) {
      if (!context.mounted) {
        return;
      }
      AppFeedback.error(
        context,
        AppLocalizations.of(context)!.notificationUpdateFailed(
            e.toString().replaceFirst('Exception: ', '').trim()),
      );
    }
  }

  bool _isNotificationTypeEnabled(
    NotificationPreferenceSettings prefs,
    String type,
  ) {
    final aliases = _notificationTypeAliases[type] ?? {type};
    final disabled = prefs.disabledTypes.map((item) => item.toLowerCase());
    return disabled.every((item) => !aliases.contains(item));
  }

  Future<void> _updateNotificationTypePreference(
    BuildContext context, {
    required String type,
    required bool enabled,
  }) async {
    final prefs = ref.read(notificationPreferenceSettingsProvider);
    final nextDisabled = prefs.disabledTypes.toSet();
    final aliases = _notificationTypeAliases[type] ?? {type};
    if (enabled) {
      nextDisabled.removeWhere((item) => aliases.contains(item.toLowerCase()));
    } else {
      nextDisabled.add(type);
    }
    await _updateNotificationPreferences(
      context,
      disabledTypes: nextDisabled.toList()..sort(),
    );
  }

  Future<void> _pickQuietHoursTime(
    BuildContext context, {
    required bool isStart,
    required String currentValue,
  }) async {
    final currentTime = _parseTimeOfDay(currentValue);
    final picked = await showTimePicker(
      context: context,
      initialTime: currentTime,
    );
    if (picked == null || !context.mounted) {
      return;
    }

    final formatted = _formatTimeOfDay(picked);
    final prefs = ref.read(notificationPreferenceSettingsProvider);
    final nextStart = isStart ? formatted : prefs.quietHoursStart;
    final nextEnd = isStart ? prefs.quietHoursEnd : formatted;
    if (nextStart == nextEnd) {
      AppFeedback.info(context,
          AppLocalizations.of(context)!.notificationQuietHoursSameTimeError);
      return;
    }
    await _updateNotificationPreferences(
      context,
      quietHoursStart: isStart ? formatted : null,
      quietHoursEnd: isStart ? null : formatted,
      successMessage: isStart
          ? AppLocalizations.of(context)!.notificationQuietHoursStartUpdated
          : AppLocalizations.of(context)!.notificationQuietHoursEndUpdated,
    );
  }

  Future<void> _applyAiReasoningMode(
    BuildContext context,
    AppLocalizations l10n,
    String mode,
  ) async {
    await ref.read(aiReasoningModeProvider.notifier).setMode(mode);
    if (!context.mounted) {
      return;
    }
    final currentMode = ref.read(aiReasoningModeProvider);
    if (currentMode == mode) {
      AppFeedback.success(
        context,
        l10n.aiReasoningModeSwitched(_aiReasoningModeTitle(l10n, mode)),
      );
      return;
    }
    AppFeedback.error(context, l10n.aiReasoningModeSwitchFailed);
  }

  TimeOfDay _parseTimeOfDay(String value) {
    final parts = value.split(':');
    if (parts.length != 2) {
      return const TimeOfDay(hour: 22, minute: 0);
    }
    return TimeOfDay(
      hour: int.tryParse(parts[0]) ?? 22,
      minute: int.tryParse(parts[1]) ?? 0,
    );
  }

  String _formatTimeOfDay(TimeOfDay time) {
    final hour = time.hour.toString().padLeft(2, '0');
    final minute = time.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }

  String _taskReminderSummary(
      AppLocalizations l10n, TaskReminderConfig config) {
    if (!config.enabled) {
      return l10n.taskReminderDisabled;
    }
    if (config.reminders.isEmpty) {
      return l10n.taskReminderEnabledNoTime;
    }
    final labels = config.reminders
        .map((m) => _formatReminderMinutes(l10n, m))
        .join(' / ');
    return '${l10n.taskReminderEnabledWithTimes} · $labels';
  }

  String _formatReminderMinutes(AppLocalizations l10n, int minutes) {
    if (minutes >= 1440) {
      final days = minutes ~/ 1440;
      return l10n.taskReminderDaysAgo(days);
    }
    if (minutes >= 60) {
      final hours = minutes ~/ 60;
      return l10n.taskReminderHoursAgo(hours);
    }
    return l10n.taskReminderMinutesAgo(minutes);
  }

  String _notificationLevelLabel(AppLocalizations l10n, String level) {
    switch (level) {
      case 'minimal':
        return l10n.notificationLevelMinimal;
      case 'verbose':
        return l10n.notificationLevelVerbose;
      case 'standard':
      default:
        return l10n.notificationLevelStandard;
    }
  }

  String _notificationLevelDescription(AppLocalizations l10n, String level) {
    switch (level) {
      case 'minimal':
        return l10n.notificationLevelMinimalDesc;
      case 'verbose':
        return l10n.notificationLevelVerboseDesc;
      case 'standard':
      default:
        return l10n.notificationLevelStandardDesc;
    }
  }

  String _notificationLevelPreview(AppLocalizations l10n, String level) {
    switch (level) {
      case 'minimal':
        return l10n.notificationLevelMinimalPreview;
      case 'verbose':
        return l10n.notificationLevelVerbosePreview;
      case 'standard':
      default:
        return l10n.notificationLevelStandardPreview;
    }
  }

  String _aiReasoningModeTitle(AppLocalizations l10n, String mode) {
    switch (mode) {
      case 'fast':
        return l10n.aiReasoningFastLabel;
      case 'deep':
        return l10n.aiReasoningDeepLabel;
      case 'balanced':
      default:
        return l10n.aiReasoningBalancedLabel;
    }
  }

  String _aiReasoningModeDescription(AppLocalizations l10n, String mode) {
    switch (mode) {
      case 'fast':
        return l10n.aiReasoningFastDesc;
      case 'deep':
        return l10n.aiReasoningDeepDesc;
      case 'balanced':
      default:
        return l10n.aiReasoningBalancedDesc;
    }
  }

  Widget _buildSelectionPreviewCard({
    required IconData icon,
    required String title,
    required String description,
  }) =>
      Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: DS.primaryBase, size: 18),
            const SizedBox(width: DS.spacing10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontWeight: DS.fontWeightBold),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    description,
                    style: DS.bodySmall.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _buildInlineStatusMessage(
    String message, {
    bool isError = false,
  }) =>
      Row(
        children: [
          Icon(
            isError ? Icons.error_outline_rounded : Icons.check_circle_outline,
            size: 16,
            color: isError ? DS.error : DS.textSecondary,
          ),
          const SizedBox(width: DS.spacing6),
          Expanded(
            child: Text(
              message,
              style: DS.bodySmall.copyWith(
                color: isError ? DS.error : DS.textSecondary,
              ),
            ),
          ),
        ],
      );

  Widget _buildLanguageOption(
    BuildContext context, {
    required String title,
    required String subtitle,
    required bool selected,
    required VoidCallback onTap,
  }) =>
      InkWell(
        onTap: onTap,
        borderRadius: DS.borderRadius16,
        child: Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: selected
                ? DS.primaryBase.withValues(alpha: 0.08)
                : DS.surfaceSecondary,
            borderRadius: DS.borderRadius16,
            border: Border.all(
              color: selected
                  ? DS.primaryBase.withValues(alpha: 0.2)
                  : DS.borderSubtle,
            ),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                            height: 1.4,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Icon(
                selected ? Icons.check_circle_rounded : Icons.circle_outlined,
                color: selected ? DS.primaryBase : DS.textSecondary,
              ),
            ],
          ),
        ),
      );

  Widget _buildCollapsibleHeader({
    required IconData icon,
    required String title,
    required String subtitle,
    required bool expanded,
    required VoidCallback onToggle,
  }) =>
      InkWell(
        onTap: onToggle,
        borderRadius: BorderRadius.circular(12),
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(icon),
          title: Text(title),
          subtitle: Text(
            subtitle,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          trailing: AnimatedRotation(
            turns: expanded ? 0.5 : 0,
            duration: const Duration(milliseconds: 250),
            child: const Icon(Icons.expand_more),
          ),
        ),
      );

  Widget _buildEmotionAdaptiveModeControl(EmotionState state) {
    final zh = I18nService.instance.isChinese;
    final mode = state.mode;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.self_improvement_rounded),
          title: Text(zh ? '情绪适应模式' : 'Emotion adaptive mode'),
          subtitle: Text(
            zh
                ? '根据疲劳、压力和认知负荷调低刺激，或手动固定。'
                : 'Lower visual stimulus from fatigue, stress, and load signals, or keep a manual override.',
          ),
        ),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: [
            ChoiceChip(
              label: Text(zh ? '自动' : 'Auto'),
              selected: mode == EmotionAdaptiveMode.auto,
              onSelected: (_) => unawaited(
                ref
                    .read(emotionStateProvider.notifier)
                    .setMode(EmotionAdaptiveMode.auto),
              ),
            ),
            ChoiceChip(
              label: Text(zh ? '低刺激' : 'Low stimulus'),
              selected: mode == EmotionAdaptiveMode.alwaysLow,
              onSelected: (_) => unawaited(
                ref
                    .read(emotionStateProvider.notifier)
                    .setMode(EmotionAdaptiveMode.alwaysLow),
              ),
            ),
            ChoiceChip(
              label: Text(zh ? '标准' : 'Normal'),
              selected: mode == EmotionAdaptiveMode.alwaysNormal,
              onSelected: (_) => unawaited(
                ref
                    .read(emotionStateProvider.notifier)
                    .setMode(EmotionAdaptiveMode.alwaysNormal),
              ),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing10),
        _buildSelectionPreviewCard(
          icon: state.responsiveConfig.isLowStimulus
              ? Icons.nightlight_round
              : Icons.wb_sunny_outlined,
          title: state.responsiveConfig.isLowStimulus
              ? (zh ? '当前：低刺激界面' : 'Current: low-stimulus UI')
              : (zh ? '当前：标准界面' : 'Current: normal UI'),
          description: state.responsiveConfig.isLowStimulus
              ? (zh
                  ? '字体略放大、动画减少、卡片层级更轻、挑战徽章会收起。'
                  : 'Text is slightly larger, motion is reduced, surfaces are calmer, and challenge badges are hidden.')
              : (zh
                  ? '界面保持常规动效、色温和信息密度。'
                  : 'The interface keeps normal motion, color temperature, and density.'),
        ),
      ],
    );
  }

  Widget _buildSectionHeader(IconData icon, String title) => Row(
        children: [
          Icon(icon, color: DS.primaryBase, size: DS.iconSizeBase),
          const SizedBox(width: DS.spacing8),
          Text(
            title,
            style: const TextStyle(
              fontSize: DS.fontSizeLg,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ],
      );

  Widget _buildAuroraPrefSegmented({
    required String label,
    required List<(String, String, IconData)> options,
    required String selected,
    required ValueChanged<String> onChanged,
  }) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: options
                .map(
                  (opt) => ChoiceChip(
                    avatar: Icon(opt.$3, size: 16),
                    label: Text(opt.$1),
                    selected: selected == opt.$2,
                    onSelected: (_) => onChanged(opt.$2),
                  ),
                )
                .toList(),
          ),
        ],
      );

  Widget _buildSettingsDropdownField<T>({
    required T value,
    required List<DropdownMenuItem<T>> items,
    required ValueChanged<T?> onChanged,
  }) =>
      Padding(
        padding: const EdgeInsets.only(top: DS.spacing8),
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: DS.borderRadius12,
            border: Border.all(color: DS.borderSubtle),
            color: DS.surfaceSecondary,
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: DS.spacing12),
            child: DropdownButton<T>(
              value: value,
              isExpanded: true,
              underline: const SizedBox.shrink(),
              onChanged: onChanged,
              items: items,
            ),
          ),
        ),
      );

  Widget _buildWeeklyAgendaSection(
    BuildContext context,
    AppLocalizations l10n,
    Map<String, dynamic>? weeklyAgenda,
  ) {
    final summary = _buildWeeklyAgendaSummary(l10n, weeklyAgenda);
    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
      decoration: BoxDecoration(
        color: DS.surfaceTertiary.withValues(alpha: 0.28),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(20),
            onTap: () {
              setState(() {
                _weeklyAgendaExpanded = !_weeklyAgendaExpanded;
              });
            },
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing16),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          l10n.selectTimeSlots,
                          style: DS.labelLarge.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightSemibold,
                          ),
                        ),
                        const SizedBox(height: DS.xs),
                        Text(
                          summary,
                          style: DS.bodySmall.copyWith(
                            color: DS.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  AnimatedRotation(
                    turns: _weeklyAgendaExpanded ? 0.5 : 0,
                    duration: const Duration(milliseconds: 220),
                    child: Icon(
                      Icons.keyboard_arrow_down_rounded,
                      color: DS.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ),
          AnimatedCrossFade(
            duration: const Duration(milliseconds: 220),
            firstChild: const SizedBox.shrink(),
            secondChild: Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing16,
                0,
                DS.spacing16,
                DS.spacing16,
              ),
              child: WeeklyAgendaGrid(
                initialData: weeklyAgenda,
                onChanged: (data) {
                  ref.read(weeklyAgendaProvider.notifier).updateAgenda(data);
                },
              ),
            ),
            crossFadeState: _weeklyAgendaExpanded
                ? CrossFadeState.showSecond
                : CrossFadeState.showFirst,
          ),
        ],
      ),
    );
  }

  String _buildWeeklyAgendaSummary(
    AppLocalizations l10n,
    Map<String, dynamic>? weeklyAgenda,
  ) {
    final rawGrid = weeklyAgenda?['grid'];
    if (rawGrid is! List || rawGrid.isEmpty) {
      return l10n.weeklyAgendaCollapsedHint;
    }

    final busyCount = rawGrid.where((slot) => slot == 'busy').length;
    final fragmentedCount =
        rawGrid.where((slot) => slot == 'fragmented').length;
    final activeCount = busyCount + fragmentedCount;
    if (activeCount == 0) {
      return l10n.weeklyAgendaEmptyHint;
    }
    return l10n.weeklyAgendaSummary(activeCount, busyCount, fragmentedCount);
  }

  String _bgmSectionSubtitle() {
    final snapshot = _bgmLibrarySnapshot;
    if (snapshot == null) {
      return context.l10n.bgmSectionSubtitleDefault;
    }
    return context.l10n.bgmSectionSubtitleWithCount(snapshot.totalCount);
  }

  Widget _buildBgmLibrarySummaryCard() {
    final snapshot = _bgmLibrarySnapshot;
    if (snapshot == null) {
      return const SizedBox.shrink();
    }
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius12,
        color: Color.alphaBlend(
          DS.brandPrimary.withValues(alpha: 0.06),
          DS.surfaceSecondary,
        ),
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.library_music_rounded, size: 18),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  context.l10n.bgmLibraryUpdated(snapshot.totalCount),
                  style: DS.bodyLarge,
                ),
              ),
              TextButton.icon(
                onPressed: () => unawaited(_openBgmLibrary()),
                icon: const Icon(Icons.open_in_new_rounded, size: 16),
                label: Text(context.l10n.bgmOpenLibrary),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _buildInfoChip(context.l10n.bgmCurated,
                  context.l10n.tracksCount(snapshot.curatedCount)),
              _buildInfoChip(context.l10n.bgmImported,
                  context.l10n.tracksCount(snapshot.importedCount)),
              _buildInfoChip(context.l10n.bgmBundled,
                  context.l10n.tracksCount(snapshot.bundledCount)),
              _buildInfoChip(
                context.l10n.bgmModeLabel,
                _bgmMode == BgmMode.continuous
                    ? context.l10n.bgmPlayerMode
                    : context.l10n.bgmPageStrategyMode,
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.bgmLibraryHint,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBgmNowPlayingCard() {
    final snapshot = _bgmPlaybackSnapshot;
    final sceneName = snapshot?.scene?.name ?? context.l10n.bgmNotPlaying;
    final trackName = snapshot?.trackTitle ??
        snapshot?.trackId ??
        context.l10n.bgmBundledTrack;
    final sourceLabel = snapshot?.sourceLabel ?? 'Bundled fallback';
    final reason = snapshot?.selectionReason ?? context.l10n.bgmWaitingPlayback;
    final statusText = !_bgmEnabled
        ? context.l10n.bgmDisabled
        : _bgmMode == BgmMode.silent
            ? context.l10n.bgmGlobalSilent
            : _bgmMode == BgmMode.continuous
                ? context.l10n.bgmContinuousPlaying
                : sceneName;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius12,
        color: Color.alphaBlend(
          DS.warning.withValues(alpha: 0.05),
          DS.surfaceSecondary,
        ),
        border: Border.all(color: DS.warning.withValues(alpha: 0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.equalizer_rounded, size: 18),
              const SizedBox(width: DS.spacing8),
              Text(context.l10n.bgmNowPlaying, style: DS.bodyLarge),
              const Spacer(),
              if (_previewingSceneTrack == null)
                TextButton.icon(
                  onPressed: _bgmEnabled && _bgmPlaybackSnapshot?.track != null
                      ? () => unawaited(_previewCurrentScene())
                      : null,
                  icon: const Icon(Icons.headphones_rounded, size: 16),
                  label: Text(context.l10n.bgmPreviewCurrentScene),
                )
              else
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(statusText, style: DS.bodyLarge),
          const SizedBox(height: DS.spacing6),
          Text(
            context.l10n.bgmTrackLabel(trackName),
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          Text(
            context.l10n.bgmSourceLabel(sourceLabel),
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            reason,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.4,
            ),
          ),
          if (snapshot != null)
            Padding(
              padding: const EdgeInsets.only(top: DS.spacing8),
              child: Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  _buildInfoChip(context.l10n.bgmIntensityLabel,
                      _bgmIntensityLabel(context.l10n, snapshot.intensity)),
                  _buildInfoChip(context.l10n.bgmVarietyLabel,
                      _bgmVarietyLabel(context.l10n, snapshot.variety)),
                  if (snapshot.readingProtectionApplied)
                    _buildInfoChip(context.l10n.bgmReadingProtection,
                        context.l10n.bgmReadingProtectionTitle),
                  if (snapshot.focusPriorityApplied)
                    _buildInfoChip(context.l10n.bgmFocusPriority,
                        context.l10n.bgmFocusPriorityTitle),
                  if (snapshot.styleLocked)
                    _buildInfoChip(context.l10n.bgmStyleLocked,
                        context.l10n.bgmStyleLocked),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildBgmAdvancedControls() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.l10n.bgmAtmosphereIntensity,
          style: DS.labelSmall.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing8),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: BgmIntensity.values
              .map(
                (intensity) => ChoiceChip(
                  label: Text(_bgmIntensityLabel(context.l10n, intensity)),
                  selected: _bgmIntensity == intensity,
                  onSelected: _bgmReady
                      ? (_) => unawaited(_setBgmIntensity(intensity))
                      : null,
                ),
              )
              .toList(),
        ),
        const SizedBox(height: DS.spacing8),
        Text(
          _bgmIntensityDescription(context.l10n, _bgmIntensity),
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing16),
        Text(
          context.l10n.bgmVarietyFrequency,
          style: DS.labelSmall.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing8),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: BgmVariety.values
              .map(
                (variety) => ChoiceChip(
                  label: Text(_bgmVarietyLabel(context.l10n, variety)),
                  selected: _bgmVariety == variety,
                  onSelected: _bgmReady
                      ? (_) => unawaited(_setBgmVariety(variety))
                      : null,
                ),
              )
              .toList(),
        ),
        const SizedBox(height: DS.spacing8),
        Text(
          _bgmVarietyDescription(context.l10n, _bgmVariety),
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing16),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(context.l10n.bgmReadingProtectionTitle),
          subtitle: Text(context.l10n.bgmReadingProtectionSubtitle),
          value: _bgmReadingProtection,
          onChanged: _bgmReady
              ? (value) => unawaited(_setBgmReadingProtection(value))
              : null,
          activeThumbColor: DS.primaryBase,
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(context.l10n.bgmFocusPriorityTitle),
          subtitle: Text(context.l10n.bgmFocusPrioritySubtitle),
          value: _bgmFocusPriority,
          onChanged: _bgmReady
              ? (value) => unawaited(_setBgmFocusPriority(value))
              : null,
          activeThumbColor: DS.primaryBase,
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(context.l10n.bgmLockStyleTitle),
          subtitle: Text(context.l10n.bgmLockStyleSubtitle),
          value: _bgmLockCurrentStyle,
          onChanged: _bgmReady
              ? (value) => unawaited(_setBgmLockCurrentStyle(value))
              : null,
          activeThumbColor: DS.primaryBase,
        ),
      ],
    );
  }

  Widget _buildInfoChip(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius16,
        color: DS.surfaceSecondary,
      ),
      child: Text(
        '$label · $value',
        style: DS.labelSmall.copyWith(color: DS.textSecondary),
      ),
    );
  }

  String _bgmPaletteLabel(AppLocalizations l10n, BgmPalette palette) =>
      switch (palette) {
        BgmPalette.adaptive => l10n.bgmPaletteAdaptive,
        BgmPalette.classical => l10n.bgmPaletteClassical,
        BgmPalette.piano => l10n.bgmPalettePiano,
        BgmPalette.airy => l10n.bgmPaletteAiry,
        BgmPalette.warm => l10n.bgmPaletteWarm,
      };

  String _bgmPaletteDescription(AppLocalizations l10n, BgmPalette palette) =>
      switch (palette) {
        BgmPalette.adaptive => l10n.bgmPaletteAdaptiveDesc,
        BgmPalette.classical => l10n.bgmPaletteClassicalDesc,
        BgmPalette.piano => l10n.bgmPalettePianoDesc,
        BgmPalette.airy => l10n.bgmPaletteAiryDesc,
        BgmPalette.warm => l10n.bgmPaletteWarmDesc,
      };

  String _bgmIntensityLabel(AppLocalizations l10n, BgmIntensity intensity) =>
      switch (intensity) {
        BgmIntensity.gentle => l10n.bgmIntensityGentle,
        BgmIntensity.balanced => l10n.bgmIntensityBalanced,
        BgmIntensity.lush => l10n.bgmIntensityLush,
      };

  String _bgmIntensityDescription(
          AppLocalizations l10n, BgmIntensity intensity) =>
      switch (intensity) {
        BgmIntensity.gentle => l10n.bgmIntensityGentleDesc,
        BgmIntensity.balanced => l10n.bgmIntensityBalancedDesc,
        BgmIntensity.lush => l10n.bgmIntensityLushDesc,
      };

  String _bgmVarietyLabel(AppLocalizations l10n, BgmVariety variety) =>
      switch (variety) {
        BgmVariety.steady => l10n.bgmVarietySteady,
        BgmVariety.balanced => l10n.bgmVarietyBalanced,
        BgmVariety.dynamic => l10n.bgmVarietyDynamic,
      };

  String _bgmVarietyDescription(AppLocalizations l10n, BgmVariety variety) =>
      switch (variety) {
        BgmVariety.steady => l10n.bgmVarietySteadyDesc,
        BgmVariety.balanced => l10n.bgmVarietyBalancedDesc,
        BgmVariety.dynamic => l10n.bgmVarietyDynamicDesc,
      };

  String _motionIntensityLabel(
          AppLocalizations l10n, MotionIntensityLevel level) =>
      switch (level) {
        MotionIntensityLevel.ultra => l10n.motionIntensityUltra,
        MotionIntensityLevel.high => l10n.motionIntensityHigh,
        MotionIntensityLevel.medium => l10n.motionIntensityMedium,
        MotionIntensityLevel.off => l10n.motionIntensityOff,
      };

  String _motionIntensityDescription(
          AppLocalizations l10n, MotionIntensityLevel level) =>
      switch (level) {
        MotionIntensityLevel.ultra => l10n.motionIntensityUltraDesc,
        MotionIntensityLevel.high => l10n.motionIntensityHighDesc,
        MotionIntensityLevel.medium => l10n.motionIntensityMediumDesc,
        MotionIntensityLevel.off => l10n.motionIntensityOffDesc,
      };

  String _bgmModeLabel(AppLocalizations l10n, BgmMode mode) => switch (mode) {
        BgmMode.adaptive => l10n.bgmModeAdaptive,
        BgmMode.continuous => l10n.bgmModeContinuous,
        BgmMode.focusOnly => l10n.bgmModeFocusOnly,
        BgmMode.silent => l10n.bgmModeSilent,
      };

  String _bgmModeDescription(AppLocalizations l10n, BgmMode mode) =>
      switch (mode) {
        BgmMode.adaptive => l10n.bgmModeAdaptiveDesc,
        BgmMode.continuous => l10n.bgmModeContinuousDesc,
        BgmMode.focusOnly => l10n.bgmModeFocusOnlyDesc,
        BgmMode.silent => l10n.bgmModeSilentDesc,
      };

  Widget _buildNotificationPermissionCard(
    BuildContext context,
    AppLocalizations l10n,
  ) {
    final permissionStatus = ref.watch(notificationPermissionStatusProvider);

    return permissionStatus.when(
      loading: () => GraphiteCardSurface(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          title: Text(l10n.notificationPermissionStatus),
          subtitle: Text('...'),
        ),
      ),
      error: (error, stack) => GraphiteCardSurface(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.error_outline, color: DS.error),
          title: Text(l10n.notificationPermissionStatus),
          subtitle:
              Text(l10n.notificationPermissionDeniedTitle(error.toString())),
        ),
      ),
      data: (status) {
        final hasPermission = status.hasPermission;
        final isPartial = status.hasPermission &&
            (status.alertEnabled == false ||
                status.badgeEnabled == false ||
                status.soundEnabled == false);

        Color statusColor;
        IconData statusIcon;
        String? hintText;

        if (!hasPermission) {
          statusColor = DS.error;
          statusIcon = Icons.notifications_off_outlined;
          hintText = l10n.notificationPermissionDeniedHint;
        } else if (isPartial) {
          statusColor = DS.warning;
          statusIcon = Icons.notifications_active_outlined;
          hintText = l10n.notificationPermissionPartialHint;
        } else {
          statusColor = DS.success;
          statusIcon = Icons.notifications_active;
        }

        return GraphiteCardSurface(
          child: Column(
            children: [
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: Color.alphaBlend(
                      statusColor.withValues(alpha: 0.1),
                      DS.surfaceSecondary,
                    ),
                    borderRadius: DS.borderRadius12,
                  ),
                  child: Icon(statusIcon, color: statusColor),
                ),
                title: Text(l10n.notificationPermissionStatus),
                subtitle: hintText != null
                    ? Text(
                        hintText,
                        style: DS.bodySmall.copyWith(color: statusColor),
                      )
                    : null,
                trailing: hasPermission && !isPartial
                    ? Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing8,
                          vertical: DS.spacing6,
                        ),
                        decoration: BoxDecoration(
                          color: statusColor.withValues(alpha: 0.1),
                          borderRadius: DS.borderRadius12,
                        ),
                        child: Icon(Icons.check_circle, color: statusColor),
                      )
                    : SparkleButton.ghost(
                        label: !hasPermission
                            ? l10n.notificationRequestPermission
                            : l10n.notificationOpenSettings,
                        onPressed: () async {
                          if (!hasPermission) {
                            final granted = await ref
                                .read(
                                  notificationPermissionStatusProvider.notifier,
                                )
                                .requestPermission();
                            if (!granted && context.mounted) {
                              _showOpenSettingsDialog(context);
                            }
                          } else {
                            _showOpenSettingsDialog(context);
                          }
                        },
                      ),
              ),
              if (isPartial) ...[
                const Divider(height: DS.spacing8),
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing16,
                    vertical: DS.spacing8,
                  ),
                  child: Wrap(
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing8,
                    children: [
                      _buildPermissionChip(
                        'Alert',
                        status.alertEnabled ?? false,
                      ),
                      _buildPermissionChip(
                        'Badge',
                        status.badgeEnabled ?? false,
                      ),
                      _buildPermissionChip(
                        'Sound',
                        status.soundEnabled ?? false,
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildPermissionChip(String label, bool enabled) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: enabled
              ? DS.success.withValues(alpha: 0.1)
              : DS.surfaceTertiary.withValues(alpha: 0.3),
          borderRadius: BorderRadius.circular(DS.radius8),
          border: Border.all(
            color: enabled ? DS.success : DS.borderSubtle,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              enabled ? Icons.check : Icons.close,
              size: 14,
              color: enabled ? DS.success : DS.textSecondary,
            ),
            const SizedBox(width: DS.spacing4),
            Text(
              label,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: enabled ? DS.success : DS.textSecondary,
              ),
            ),
          ],
        ),
      );

  void _showOpenSettingsDialog(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.l10n.notificationPermissionDialogTitle),
        content: Text(context.l10n.notificationPermissionDialogContent),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(context.l10n.commonCancel),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              // Open app settings
              unawaited(
                ref
                    .read(notificationPermissionStatusProvider.notifier)
                    .requestPermission(),
              );
            },
            child: Text(context.l10n.notificationOpenSettings),
          ),
        ],
      ),
    );
  }

  Widget _buildAiUsageSummary(Map<String, dynamic> summary) {
    final theme = Theme.of(context);
    final items = (summary['items'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .toList();
    if (items.isEmpty) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(context.l10n.aiUsageTodayPreparing),
      );
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          DS.primaryBase.withValues(alpha: 0.05),
          DS.surfaceSecondary,
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.aiUsageTodayTitle,
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          ...items.map((item) {
            final label =
                item['label']?.toString() ?? item['mode']?.toString() ?? '';
            final used = item['requests_used'] ?? 0;
            final limit = item['requests_limit'] ?? 0;
            final tokens = item['total_tokens'] ?? 0;
            final cost = (item['total_cost_usd'] as num?)?.toDouble() ?? 0.0;
            final avgTotalMs =
                (item['avg_total_duration_ms'] as num?)?.toDouble() ?? 0.0;
            final avgFirstTokenMs =
                (item['avg_first_token_ms'] as num?)?.toDouble() ?? 0.0;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 44,
                    child: Text(
                      label,
                      style: theme.textTheme.bodySmall?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${context.l10n.aiUsageRequests(used as int, limit as int)} · $tokens tokens · \$${cost.toStringAsFixed(4)}',
                          style: theme.textTheme.bodySmall,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          context.l10n.aiUsageLatency(
                              avgFirstTokenMs.toStringAsFixed(0),
                              avgTotalMs.toStringAsFixed(0)),
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.textTheme.bodySmall?.color?.withValues(
                              alpha: 0.72,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildAiUserViewPanel(
    Map<String, dynamic> payload,
    Map<String, dynamic>? predictionPayload,
  ) {
    final theme = Theme.of(context);
    final items = (payload['items'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .toList();
    if (items.isEmpty) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(context.l10n.aiOpsModesAccumulating),
      );
    }

    final totalRequests = items.fold<int>(
      0,
      (sum, item) => sum + ((item['requests_total'] as num?)?.toInt() ?? 0),
    );
    final totalSuccess = items.fold<int>(
      0,
      (sum, item) => sum + ((item['requests_success'] as num?)?.toInt() ?? 0),
    );
    final weightedFirstToken = items.fold<double>(
      0,
      (sum, item) =>
          sum +
          (((item['avg_first_token_ms'] as num?)?.toDouble() ?? 0) *
              ((item['requests_total'] as num?)?.toDouble() ?? 0)),
    );
    final weightedTotalDuration = items.fold<double>(
      0,
      (sum, item) =>
          sum +
          (((item['avg_total_duration_ms'] as num?)?.toDouble() ?? 0) *
              ((item['requests_total'] as num?)?.toDouble() ?? 0)),
    );
    final weightedExecutionConv = items.fold<double>(
      0,
      (sum, item) =>
          sum +
          (((item['execution_conversion_rate_percent'] as num?)?.toDouble() ??
                  0) *
              ((item['requests_total'] as num?)?.toDouble() ?? 0)),
    );
    final successRate =
        totalRequests > 0 ? (totalSuccess / totalRequests) * 100 : 0.0;
    final avgFirstToken =
        totalRequests > 0 ? weightedFirstToken / totalRequests : 0.0;
    final avgTotalDuration =
        totalRequests > 0 ? weightedTotalDuration / totalRequests : 0.0;
    final executionRate =
        totalRequests > 0 ? weightedExecutionConv / totalRequests : 0.0;
    final topMode = [...items]..sort(
        (a, b) => ((b['requests_total'] as num?)?.toInt() ?? 0)
            .compareTo((a['requests_total'] as num?)?.toInt() ?? 0),
      );
    final topChatMode = topMode.isNotEmpty
        ? _labelForChatMode(topMode.first['chat_mode'])
        : context.l10n.aiOpsTopChatModeStandard;
    final funnel = (predictionPayload?['funnel'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
    final acceptToExecution =
        (funnel['accept_to_execution_percent'] as num?)?.toDouble() ?? 0.0;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          DS.info.withValues(alpha: 0.05),
          DS.surfaceSecondary,
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.aiOpsUserViewTitle,
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.aiOpsUserViewDesc,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.textTheme.bodySmall?.color?.withValues(alpha: 0.78),
            ),
          ),
          const SizedBox(height: DS.spacing10),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _MetricChip(
                label: context.l10n.aiOpsSuccessRate,
                value: '${successRate.toStringAsFixed(1)}%',
              ),
              _MetricChip(
                label: context.l10n.aiOpsAvgFirstToken,
                value: '${avgFirstToken.toStringAsFixed(0)}ms',
              ),
              _MetricChip(
                label: context.l10n.aiOpsAvgTotalDuration,
                value: '${avgTotalDuration.toStringAsFixed(0)}ms',
              ),
              _MetricChip(
                label: context.l10n.aiOpsExecutionConversion,
                value: '${executionRate.toStringAsFixed(1)}%',
              ),
              _MetricChip(
                label: context.l10n.aiOpsPredictedAcceptExec,
                value: '${acceptToExecution.toStringAsFixed(1)}%',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          Text(
            context.l10n.aiOpsTopModeSummary(topChatMode),
            style: theme.textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _buildAiDeveloperViewPanel(
    Map<String, dynamic> payload,
    Map<String, dynamic>? predictionPayload,
  ) {
    final theme = Theme.of(context);
    final windowDays = payload['window_days'] as int? ?? 7;
    final items = (payload['items'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .toList();
    final totalCost = items.fold<double>(
      0,
      (sum, item) => sum + ((item['total_cost_usd'] as num?)?.toDouble() ?? 0),
    );
    final totalRequests = items.fold<int>(
      0,
      (sum, item) => sum + ((item['requests_total'] as num?)?.toInt() ?? 0),
    );
    final weightedFallback = items.fold<double>(
      0,
      (sum, item) =>
          sum +
          (((item['fallback_rate_percent'] as num?)?.toDouble() ?? 0) *
              ((item['requests_total'] as num?)?.toDouble() ?? 0)),
    );
    final fallbackRate =
        totalRequests > 0 ? weightedFallback / totalRequests : 0.0;
    final promptKnown = items.fold<int>(
      0,
      (sum, item) =>
          sum +
          ((item['prompt_utilization_known_count'] as num?)?.toInt() ?? 0),
    );
    final inferenceKnown = items.fold<int>(
      0,
      (sum, item) =>
          sum +
          ((item['inference_utilization_known_count'] as num?)?.toInt() ?? 0),
    );
    final promptUtilWeighted = items.fold<double>(
      0,
      (sum, item) =>
          sum +
          (((item['avg_prompt_utilization_percent'] as num?)?.toDouble() ?? 0) *
              ((item['prompt_utilization_known_count'] as num?)?.toDouble() ??
                  0)),
    );
    final inferenceUtilWeighted = items.fold<double>(
      0,
      (sum, item) =>
          sum +
          (((item['avg_inference_utilization_percent'] as num?)?.toDouble() ??
                  0) *
              ((item['inference_utilization_known_count'] as num?)
                      ?.toDouble() ??
                  0)),
    );
    final avgPromptUtil =
        promptKnown > 0 ? promptUtilWeighted / promptKnown : 0.0;
    final avgInferenceUtil =
        inferenceKnown > 0 ? inferenceUtilWeighted / inferenceKnown : 0.0;
    final topActions = (predictionPayload?['top_actions'] as List<dynamic>? ??
            const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .toList();
    final topAction = topActions.isNotEmpty
        ? topActions.first['action_type']?.toString() ?? 'unknown'
        : 'unknown';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          DS.warning.withValues(alpha: 0.05),
          DS.surfaceSecondary,
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.aiOpsDevViewTitle,
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.aiOpsDevViewDesc,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.textTheme.bodySmall?.color?.withValues(alpha: 0.78),
            ),
          ),
          const SizedBox(height: DS.spacing10),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _MetricChip(
                label: context.l10n.aiOpsMonitoringModes,
                value: '${items.length}',
              ),
              _MetricChip(
                label: context.l10n.aiOpsTotalRequests,
                value: '$totalRequests',
              ),
              _MetricChip(
                label: context.l10n.aiOpsFallback,
                value: '${fallbackRate.toStringAsFixed(1)}%',
              ),
              _MetricChip(
                label: context.l10n.aiOpsTotalCost,
                value: '\$${totalCost.toStringAsFixed(4)}',
              ),
              _MetricChip(
                label: context.l10n.aiOpsPromptHit,
                value: '${avgPromptUtil.toStringAsFixed(1)}%',
              ),
              _MetricChip(
                label: context.l10n.aiOpsInferenceHit,
                value: '${avgInferenceUtil.toStringAsFixed(1)}%',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          Text(
            context.l10n.aiOpsPredictionSummary(
                windowDays,
                topAction,
                avgPromptUtil.toStringAsFixed(1),
                avgInferenceUtil.toStringAsFixed(1)),
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: DS.spacing12),
          Align(
            alignment: Alignment.centerLeft,
            child: SparkleButton.ghost(
              label: context.l10n.aiOpsOpenAnalysis,
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => const AiOpsAnalysisScreen(),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Align(
            alignment: Alignment.centerLeft,
            child: SparkleButton.ghost(
              label: context.l10n.aiOpsOpenAdminPanel,
              onPressed: () => context.push(UserRoutes.adminOperations),
            ),
          ),
        ],
      ),
    );
  }

  String _labelForChatMode(Object? value) {
    switch (value?.toString()) {
      case 'standard':
        return context.l10n.aiOpsTopChatModeStandard;
      case 'study_plan':
        return context.l10n.aiOpsTopChatModeStudyPlan;
      case 'deep_analysis':
        return context.l10n.aiOpsTopChatModeDeepAnalysis;
      case 'error_diagnosis':
        return context.l10n.aiOpsTopChatModeErrorDiagnosis;
      case 'expert_auto':
        return context.l10n.aiOpsTopChatModeExpertAuto;
      default:
        return value?.toString() ?? 'standard';
    }
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: Color.alphaBlend(
            DS.primaryBase.withValues(alpha: 0.06),
            DS.surfacePrimary,
          ),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: 2),
            Text(
              value,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ],
        ),
      );
}
