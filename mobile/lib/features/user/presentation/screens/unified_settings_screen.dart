import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/providers/locale_provider.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/chaos/chaos_control_dialog.dart';
import 'package:sparkle/features/cognitive/data/repositories/capsule_repository.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/cognitive/presentation/screens/capsule/capsule_detail_screen.dart';
import 'package:sparkle/features/cognitive/presentation/widgets/capsule/capsule_generation_preview.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/screens/ai_ops_analysis_screen.dart';
import 'package:sparkle/features/user/presentation/widgets/learning_mode_control.dart';
import 'package:sparkle/features/user/presentation/widgets/weekly_agenda_grid.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/features/visual_elements/visual_elements_routes.dart';
import 'package:sparkle/l10n/app_localizations.dart';

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
  bool _sensoryReady = false;
  AmbientScene _ambientScene = AmbientScene.none;
  double _ambientVolume = 0.5;
  Timer? _learningPrefsDebounce;

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
    final ambientScene = await SensoryFeedbackService.getSavedAmbientScene();
    final ambientVolume = await SensoryFeedbackService.getAmbientVolume();
    if (!mounted) {
      return;
    }
    setState(() {
      _soundEnabled = soundEnabled;
      _hapticEnabled = hapticEnabled;
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
        AppFeedback.error(context, '试听失败，请检查音频文件');
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
        AppFeedback.error(context, '当前场景试听失败，请检查音频文件');
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
    _learningPrefsDebounce?.cancel();
    _learningPrefsDebounce = Timer(const Duration(milliseconds: 220), () {
      notifier.updatePreferences(depth: depth, curiosity: curiosity);
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final isCompact = MediaQuery.sizeOf(context).width < 380;
    final enterToSend = ref.watch(enterToSendProvider);
    final transparentMode = ref.watch(transparentModeProvider);
    final transparencyLevel = ref.watch(transparencyLevelProvider);
    final systemUpdateLevel = ref.watch(systemUpdateLevelProvider);
    final aiReasoningMode = ref.watch(aiReasoningModeProvider);
    final showChatContextToggle = ref.watch(showChatContextToggleProvider);
    final showChatPredictionDock = ref.watch(showChatPredictionDockProvider);
    final showChatTransparencyCapsule =
        ref.watch(showChatTransparencyCapsuleProvider);
    final chatPureMode = ref.watch(chatPureModeProvider);
    final motionIntensityLevel = ref.watch(motionIntensityLevelProvider);
    final aiUsageSummary = ref.watch(aiUsageSummaryProvider);
    final aiOpsDashboard = ref.watch(aiOpsDashboardProvider);
    final predictionAnalytics = ref.watch(predictionAnalyticsDashboardProvider);
    final learningPrefs = ref.watch(learningPreferencesProvider);
    final pushPrefs = ref.watch(pushPreferencesProvider);
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
            horizontal: isCompact ? 14 : DS.spacing16,
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
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildCollapsibleHeader(
                      icon: Icons.psychology,
                      title: l10n.learningMode,
                      subtitle: '调整深度与好奇心偏好',
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
                                    label: Text(_bgmModeLabel(mode)),
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
                              _bgmModeDescription(_bgmMode),
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
                            '音乐音量',
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
                            '场景偏好',
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
                                          label:
                                              Text(_bgmPaletteLabel(palette)),
                                          selected: _bgmPalette == palette,
                                          onSelected: _bgmReady
                                              ? (_) => unawaited(
                                                    _setBgmPalette(palette),
                                                  )
                                              : null,
                                        ),
                                        IconButton(
                                          tooltip:
                                              '试听 ${_bgmPaletteLabel(palette)}',
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
                              _bgmPaletteDescription(_bgmPalette),
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
                                          '高级控制',
                                          style: DS.bodyLarge,
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          '控制音乐浓度、轮换频率、阅读保护、专注优先与锁定当前风格',
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
                                  onSelected: (_) => ref
                                      .read(aiReasoningModeProvider.notifier)
                                      .setMode('fast'),
                                ),
                                ChoiceChip(
                                  label: Text(l10n.aiReasoningBalancedLabel),
                                  selected: aiReasoningMode == 'balanced',
                                  onSelected: (_) => ref
                                      .read(aiReasoningModeProvider.notifier)
                                      .setMode('balanced'),
                                ),
                                ChoiceChip(
                                  label: Text(l10n.aiReasoningDeepLabel),
                                  selected: aiReasoningMode == 'deep',
                                  onSelected: (_) => ref
                                      .read(aiReasoningModeProvider.notifier)
                                      .setMode('deep'),
                                ),
                              ],
                            ),
                          ),
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
                            title: const Text('纯净模式'),
                            subtitle: const Text(
                              '聊天中只保留文字消息，隐藏附加信息卡片与消息下方组件。',
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
                              '动效强度',
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
                                    label: Text(_motionIntensityLabel(level)),
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
                              _motionIntensityDescription(motionIntensityLevel),
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
                              child: const Text(
                                '额度面板暂时不可用，但档位切换仍可正常生效。',
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
                              child: const Text(
                                '运营面板暂时不可用，但 AI 档位和使用统计仍可继续使用。',
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
              // Notification permission status card
              _buildNotificationPermissionCard(context, l10n),
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
                  title: const Text('AI执行引擎'),
                  subtitle: const Text('连接你的 OpenClaw 实例并监控健康状态'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push(UserRoutes.openClawSettings),
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
        AppFeedback.success(context, '新的好奇心胶囊已生成');
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
                        ? '已生成新的胶囊，点击下方即可查看完整内容。'
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
                    label: '查看新胶囊',
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
        child: GraphiteModalSurface(
          title: l10n.language,
          showHandle: false,
          borderRadius: BorderRadius.circular(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '选择你更习惯的阅读与交互语言，界面与系统文案会一起切换。',
                style: Theme.of(dialogContext).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
              const SizedBox(height: DS.spacing16),
              _buildLanguageOption(
                dialogContext,
                title: l10n.languageChinese,
                subtitle: '更适合中文阅读与本地化表达。',
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
                subtitle: '适合英文界面与更国际化的内容环境。',
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
                            fontWeight: FontWeight.w700,
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
                            fontWeight: FontWeight.w600,
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
      return '按页面与播放器模式管理背景音乐';
    }
    return '当前共 ${snapshot.totalCount} 首，可在页面策略和播放器模式之间自由切换';
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
                  '曲库已更新为 ${snapshot.totalCount} 首',
                  style: DS.bodyLarge,
                ),
              ),
              TextButton.icon(
                onPressed: () => unawaited(_openBgmLibrary()),
                icon: const Icon(Icons.open_in_new_rounded, size: 16),
                label: const Text('打开曲库'),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _buildInfoChip('精选', '${snapshot.curatedCount} 首'),
              _buildInfoChip('本地导入', '${snapshot.importedCount} 首'),
              _buildInfoChip('系统兜底', '${snapshot.bundledCount} 首'),
              _buildInfoChip(
                '模式',
                _bgmMode == BgmMode.continuous ? '播放器模式' : '页面策略模式',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '新页面里可以点播曲库、导入自己的音乐，并启用“播放器模式”让 BGM 跨页面持续不中断。',
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
    final sceneName = snapshot?.scene?.name ?? '当前未播放';
    final trackName = snapshot?.trackTitle ?? snapshot?.trackId ?? '内置场景曲目';
    final sourceLabel = snapshot?.sourceLabel ?? 'Bundled fallback';
    final reason = snapshot?.selectionReason ?? '等待播放信息';
    final statusText = !_bgmEnabled
        ? '背景音乐已关闭'
        : _bgmMode == BgmMode.silent
            ? '当前处于全局静音'
            : _bgmMode == BgmMode.continuous
                ? '播放器模式持续播放中'
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
              Text('当前播放', style: DS.bodyLarge),
              const Spacer(),
              if (_previewingSceneTrack == null)
                TextButton.icon(
                  onPressed: _bgmEnabled && _bgmPlaybackSnapshot?.track != null
                      ? () => unawaited(_previewCurrentScene())
                      : null,
                  icon: const Icon(Icons.headphones_rounded, size: 16),
                  label: const Text('试听当前场景'),
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
            '曲目: $trackName',
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          Text(
            '来源: $sourceLabel',
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
                  _buildInfoChip('强度', _bgmIntensityLabel(snapshot.intensity)),
                  _buildInfoChip('轮换', _bgmVarietyLabel(snapshot.variety)),
                  if (snapshot.readingProtectionApplied)
                    _buildInfoChip('保护', '阅读保护'),
                  if (snapshot.focusPriorityApplied)
                    _buildInfoChip('优先', '专注优先'),
                  if (snapshot.styleLocked) _buildInfoChip('状态', '锁定风格'),
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
          '氛围强度',
          style: DS.labelSmall.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing8),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: BgmIntensity.values
              .map(
                (intensity) => ChoiceChip(
                  label: Text(_bgmIntensityLabel(intensity)),
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
          _bgmIntensityDescription(_bgmIntensity),
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing16),
        Text(
          '曲目变化频率',
          style: DS.labelSmall.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing8),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: BgmVariety.values
              .map(
                (variety) => ChoiceChip(
                  label: Text(_bgmVarietyLabel(variety)),
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
          _bgmVarietyDescription(_bgmVariety),
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing16),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('阅读保护'),
          subtitle: const Text('聊天、洞察、个人页优先保留低刺激与轻混音'),
          value: _bgmReadingProtection,
          onChanged: _bgmReady
              ? (value) => unawaited(_setBgmReadingProtection(value))
              : null,
          activeThumbColor: DS.primaryBase,
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('专注优先'),
          subtitle: const Text('专注与执行阶段优先选择更纯净、更稳定的曲目'),
          value: _bgmFocusPriority,
          onChanged: _bgmReady
              ? (value) => unawaited(_setBgmFocusPriority(value))
              : null,
          activeThumbColor: DS.primaryBase,
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('锁定当前风格'),
          subtitle: const Text('跨普通页面时尽量延续当前气质，不覆盖专注和庆祝场景'),
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

  String _bgmPaletteLabel(BgmPalette palette) => switch (palette) {
        BgmPalette.adaptive => '自适应',
        BgmPalette.classical => '精选古典',
        BgmPalette.piano => '钢琴优先',
        BgmPalette.airy => '空灵氛围',
        BgmPalette.warm => '温暖轻快',
      };

  String _bgmPaletteDescription(BgmPalette palette) => switch (palette) {
        BgmPalette.adaptive => '系统会按页面功能自动挑选最合适的背景音乐。',
        BgmPalette.classical => '精选古典钢琴与弦乐，会优先使用你本机准备的古典乐库做场景切换。',
        BgmPalette.piano => '整体更偏轻钢琴与安静旋律，适合长时间陪伴。',
        BgmPalette.airy => '整体更偏空灵、梦幻和空间感更强的氛围。',
        BgmPalette.warm => '整体更偏温暖、柔和、有人味的轻快底色。',
      };

  String _bgmIntensityLabel(BgmIntensity intensity) => switch (intensity) {
        BgmIntensity.gentle => '柔和',
        BgmIntensity.balanced => '平衡',
        BgmIntensity.lush => '丰盈',
      };

  String _bgmIntensityDescription(BgmIntensity intensity) =>
      switch (intensity) {
        BgmIntensity.gentle => '更适合长时间陪伴，优先轻密度、低干扰和慢切换。',
        BgmIntensity.balanced => '保留舒适度的同时增加一点层次和存在感。',
        BgmIntensity.lush => '让同一场景更有氛围和包裹感，但仍避免明显突兀。',
      };

  String _bgmVarietyLabel(BgmVariety variety) => switch (variety) {
        BgmVariety.steady => '稳定',
        BgmVariety.balanced => '均衡',
        BgmVariety.dynamic => '灵动',
      };

  String _bgmVarietyDescription(BgmVariety variety) => switch (variety) {
        BgmVariety.steady => '尽量减少跳曲和重复变化，让氛围更连贯。',
        BgmVariety.balanced => '在连贯和新鲜之间保持中间值。',
        BgmVariety.dynamic => '降低重复率，让同类页面也能更常听到新变化。',
      };

  String _motionIntensityLabel(MotionIntensityLevel level) => switch (level) {
        MotionIntensityLevel.ultra => '超强',
        MotionIntensityLevel.high => '高',
        MotionIntensityLevel.medium => '中',
        MotionIntensityLevel.off => '关闭',
      };

  String _motionIntensityDescription(MotionIntensityLevel level) =>
      switch (level) {
        MotionIntensityLevel.ultra => '保留完整粒子、辉光与复杂动效，适合高性能设备。',
        MotionIntensityLevel.high => '维持大部分视觉层，同时允许系统按帧率自动降级。',
        MotionIntensityLevel.medium => '收敛粒子与辉光，优先稳定和省电，仍保留基础层次感。',
        MotionIntensityLevel.off => '尽量关闭强动效与粒子层，适合偏静态、低刺激或低性能场景。',
      };

  String _bgmModeLabel(BgmMode mode) => switch (mode) {
        BgmMode.adaptive => '跟随页面',
        BgmMode.continuous => '播放器模式',
        BgmMode.focusOnly => '仅专注开启',
        BgmMode.silent => '全局静音',
      };

  String _bgmModeDescription(BgmMode mode) => switch (mode) {
        BgmMode.adaptive => '首页、聊天、任务、成就等页面会自动切换到对应氛围音乐。',
        BgmMode.continuous => '当前曲目会持续播放，不会因为你跳转到别的页面而被打断，适合把 App 当成舒缓音乐播放器。',
        BgmMode.focusOnly => '只有专注开始、沉浸和执行任务时才会播放背景音乐，日常页面保持安静。',
        BgmMode.silent => '保留音效和触感反馈，但所有背景音乐都不会自动播放。',
      };

  Widget _buildNotificationPermissionCard(
    BuildContext context,
    AppLocalizations l10n,
  ) {
    final permissionStatus = ref.watch(notificationPermissionStatusProvider);

    return permissionStatus.when(
      loading: () => const GraphiteCardSurface(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          title: Text('通知权限状态'),
          subtitle: Text('...'),
        ),
      ),
      error: (error, stack) => GraphiteCardSurface(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.error_outline, color: DS.error),
          title: const Text('通知权限状态'),
          subtitle: Text('未授权: $error'),
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
          hintText = '通知权限被拒绝，请在系统设置中开启';
        } else if (isPartial) {
          statusColor = DS.warning;
          statusIcon = Icons.notifications_active_outlined;
          hintText = '部分通知功能受限，建议开启完整权限';
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
                title: const Text('通知权限状态'),
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
                        label: !hasPermission ? '请求权限' : '打开设置',
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
        title: const Text('通知权限状态'),
        content: const Text('通知权限被拒绝，请在系统设置中开启'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
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
            child: const Text('打开设置'),
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
        child: const Text('今日额度统计准备中。'),
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
            '今日 AI 额度与消耗',
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w700,
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
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '$used/$limit 次 · $tokens tokens · \$${cost.toStringAsFixed(4)}',
                          style: theme.textTheme.bodySmall,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '平均首 token ${avgFirstTokenMs.toStringAsFixed(0)}ms · 平均总耗时 ${avgTotalMs.toStringAsFixed(0)}ms',
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
        child: const Text('模式级运营指标还在累积中。'),
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
        : '标准对话';
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
            '用户视角',
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '重点看 AI 是否回得快、够稳、能把建议真正推成执行，而不是只看模型层参数。',
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
                label: '成功率',
                value: '${successRate.toStringAsFixed(1)}%',
              ),
              _MetricChip(
                label: '平均首包',
                value: '${avgFirstToken.toStringAsFixed(0)}ms',
              ),
              _MetricChip(
                label: '平均总耗时',
                value: '${avgTotalDuration.toStringAsFixed(0)}ms',
              ),
              _MetricChip(
                label: '执行转化',
                value: '${executionRate.toStringAsFixed(1)}%',
              ),
              _MetricChip(
                label: '预测接受后执行',
                value: '${acceptToExecution.toStringAsFixed(1)}%',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          Text(
            '最近最常用的是「$topChatMode」这条链，说明它已经是用户日常体验里的主力工作流。',
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
            '开发运营视角',
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '这里专门看速度、成本、fallback 和预测转化，用来决定下一轮要优化哪条模式链。',
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
                label: '监控模式',
                value: '${items.length}',
              ),
              _MetricChip(
                label: '请求总量',
                value: '$totalRequests',
              ),
              _MetricChip(
                label: 'fallback',
                value: '${fallbackRate.toStringAsFixed(1)}%',
              ),
              _MetricChip(
                label: '总成本',
                value: '\$${totalCost.toStringAsFixed(4)}',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          Text(
            '近 $windowDays 天里，当前最值得继续盯的预测动作是「$topAction」。',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: DS.spacing12),
          Align(
            alignment: Alignment.centerLeft,
            child: SparkleButton.ghost(
              label: '打开 AI 运营分析页',
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
              label: '打开管理员运营面板',
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
        return '标准对话';
      case 'study_plan':
        return '学习规划';
      case 'deep_analysis':
        return '深度分析';
      case 'error_diagnosis':
        return '诊断纠错';
      case 'expert_auto':
        return '专家协作';
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
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ],
        ),
      );
}
