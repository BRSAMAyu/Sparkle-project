import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class PersonaOnboardingScreen extends ConsumerStatefulWidget {
  const PersonaOnboardingScreen({super.key});

  @override
  ConsumerState<PersonaOnboardingScreen> createState() =>
      _PersonaOnboardingScreenState();
}

class _PersonaOnboardingScreenState
    extends ConsumerState<PersonaOnboardingScreen> {
  final _goalController = TextEditingController();
  Timer? _previewDebounce;
  int _currentStep = 0;
  String _goalType = 'exam';
  String _learningStyle = 'balanced';
  String _knowledgeLevel = 'beginner';
  double _studyMinutes = 60;
  double _depthPreference = 0.5;
  double _curiosityPreference = 0.5;
  bool _submitting = false;
  bool _previewLoading = false;
  String? _previewMessage;
  int _previewRequestId = 0;

  @override
  void initState() {
    super.initState();
    _goalController.addListener(_schedulePreview);
  }

  @override
  void dispose() {
    _previewDebounce?.cancel();
    _goalController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final steps = _buildSteps(l10n);
    return SceneAudioScope(
      policy: ExperienceProfiles.dashboardProductive.audioPolicy(
        trackOverride: _personaTrack(),
      ),
      child: SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: Text(l10n.personaGuide),
      ),
      child: ContentConstraint(
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          margin: const EdgeInsets.all(DS.spacing16),
          child: Stepper(
            currentStep: _currentStep,
            onStepContinue: _submitting
                ? null
                : () {
                    unawaited(_handleContinue(steps.length));
                  },
            onStepCancel: _submitting ? null : _handleBack,
            controlsBuilder: (context, details) {
              final isLast = _currentStep == steps.length - 1;
              return Row(
                children: [
                  SparkleButton(
                    label: isLast ? l10n.personaComplete : l10n.personaNextStep,
                    onPressed: details.onStepContinue,
                    loading: _submitting,
                  ),
                  const SizedBox(width: DS.spacing12),
                  if (_currentStep > 0)
                    SparkleButton(
                      label: l10n.personaPreviousStep,
                      variant: ButtonVariant.ghost,
                      onPressed: details.onStepCancel,
                    ),
                ],
              );
            },
            steps: steps,
          ),
        ),
      ),
      ),
    );
  }

  BgmTrack _personaTrack() {
    switch (_learningStyle) {
      case 'practice':
        return BgmTrack.focusStart;
      case 'logic':
        return BgmTrack.thinking;
      case 'visual':
        return BgmTrack.dashboard;
      default:
        return BgmTrack.profile;
    }
  }

  List<Step> _buildSteps(AppLocalizations l10n) => [
        Step(
          title: Text(l10n.personaLearningGoal),
          content: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: DS.spacing8,
                children: [
                  _goalTypeChip('exam', l10n.personaGoalTypeExam),
                  _goalTypeChip('skill', l10n.personaGoalTypeSkill),
                  _goalTypeChip('interest', l10n.personaGoalTypeInterest),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              TextField(
                controller: _goalController,
                decoration: InputDecoration(
                  hintText: l10n.personaGoalHint,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _buildPreviewCard(context),
            ],
          ),
          isActive: _currentStep >= 0,
        ),
        Step(
          title: Text(l10n.personaLearningStyle),
          content: Wrap(
            spacing: DS.spacing8,
            children: [
              _styleChip('balanced', l10n.personaStyleBalanced),
              _styleChip('visual', l10n.personaStyleVisual),
              _styleChip('practice', l10n.personaStylePractice),
              _styleChip('logic', l10n.personaStyleLogic),
            ],
          ),
          isActive: _currentStep >= 1,
        ),
        Step(
          title: Text(l10n.personaDailyStudyTime),
          content: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(l10n.personaMinutes(_studyMinutes.round())),
              Slider(
                value: _studyMinutes,
                min: 10,
                max: 180,
                divisions: 17,
                onChanged: (v) {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                  );
                  setState(() => _studyMinutes = v);
                  _schedulePreview();
                },
              ),
            ],
          ),
          isActive: _currentStep >= 2,
        ),
        Step(
          title: Text(l10n.personaKnowledgeLevel),
          content: Wrap(
            spacing: DS.spacing8,
            children: [
              _levelChip('beginner', l10n.personaLevelBeginner),
              _levelChip('intermediate', l10n.personaLevelIntermediate),
              _levelChip('advanced', l10n.personaLevelAdvanced),
            ],
          ),
          isActive: _currentStep >= 3,
        ),
        Step(
          title: Text(l10n.personaResponsePreference),
          content: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(l10n.personaResponseDepth),
              Slider(
                value: _depthPreference,
                divisions: 10,
                onChanged: (v) {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                  );
                  setState(() => _depthPreference = v);
                  _schedulePreview();
                },
              ),
              const SizedBox(height: DS.spacing12),
              Text(l10n.personaCuriosityExtension),
              Slider(
                value: _curiosityPreference,
                divisions: 10,
                onChanged: (v) {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                  );
                  setState(() => _curiosityPreference = v);
                  _schedulePreview();
                },
              ),
            ],
          ),
          isActive: _currentStep >= 4,
        ),
      ];

  ChoiceChip _styleChip(String value, String label) => ChoiceChip(
        label: Text(label),
        selected: _learningStyle == value,
        onSelected: (_) {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
          setState(() => _learningStyle = value);
          _schedulePreview();
        },
      );

  ChoiceChip _goalTypeChip(String value, String label) => ChoiceChip(
        label: Text(label),
        selected: _goalType == value,
        onSelected: (_) {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
          setState(() => _goalType = value);
          _schedulePreview();
        },
      );

  ChoiceChip _levelChip(String value, String label) => ChoiceChip(
        label: Text(label),
        selected: _knowledgeLevel == value,
        onSelected: (_) {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
          setState(() => _knowledgeLevel = value);
          _schedulePreview();
        },
      );

  void _handleBack() {
    if (_currentStep == 0) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    setState(() => _currentStep -= 1);
  }

  void _schedulePreview() {
    _previewDebounce?.cancel();
    final goal = _goalController.text.trim();
    if (goal.isEmpty) {
      if (_previewMessage != null || _previewLoading) {
        setState(() {
          _previewMessage = null;
          _previewLoading = false;
        });
      }
      return;
    }

    _previewDebounce = Timer(const Duration(milliseconds: 450), () {
      unawaited(_loadPreview());
    });
  }

  Future<void> _loadPreview() async {
    final goal = _goalController.text.trim();
    if (goal.isEmpty) return;

    final requestId = ++_previewRequestId;
    setState(() => _previewLoading = true);

    final repo = ref.read(userRepositoryProvider);
    try {
      final preview = await repo.fetchOnboardingPreview({
        'learning_goal_type': _goalType,
        'learning_goal': goal,
        'learning_style': _learningStyle,
        'study_time_minutes': _studyMinutes.round(),
        'knowledge_level': _knowledgeLevel,
        'response_depth': _depthPreference,
        'curiosity_preference': _curiosityPreference,
      });
      if (!mounted || requestId != _previewRequestId) return;
      setState(() {
        _previewMessage = preview['message']?.toString().trim();
        _previewLoading = false;
      });
      if ((_previewMessage ?? '').isNotEmpty) {
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.achievementCommon),
        );
      }
    } catch (_) {
      if (!mounted || requestId != _previewRequestId) return;
      setState(() {
        _previewMessage =
            '我已经理解你想先推进「$goal」，接下来会根据你的目标和时间给出第一版学习建议。';
        _previewLoading = false;
      });
    }
  }

  Widget _buildPreviewCard(BuildContext context) {
    final goal = _goalController.text.trim();
    if (goal.isEmpty && !_previewLoading) {
      return const SizedBox.shrink();
    }

    final textTheme = Theme.of(context).textTheme;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(DS.radius16),
        border: Border.all(
          color: DS.brandPrimary.withValues(alpha: 0.14),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(DS.radius12),
            ),
            child: const Icon(Icons.auto_awesome_rounded, size: 16),
          ),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'AI 已开始理解你的目标',
                  style: textTheme.labelLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: DS.spacing4),
                if (_previewLoading)
                  Text(
                    '正在生成第一版理解与建议...',
                    style: textTheme.bodySmall,
                  )
                else
                  Text(
                    _previewMessage ?? '',
                    style: textTheme.bodyMedium,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _handleContinue(int totalSteps) async {
    if (_currentStep < totalSteps - 1) {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
      setState(() => _currentStep += 1);
      return;
    }

    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    setState(() => _submitting = true);
    final repo = ref.read(userRepositoryProvider);
    try {
      final firstMessage = await repo.submitOnboarding({
        'learning_goal_type': _goalType,
        'learning_goal': _goalController.text.trim().isEmpty
            ? null
            : _goalController.text.trim(),
        'learning_style': _learningStyle,
        'study_time_minutes': _studyMinutes.round(),
        'knowledge_level': _knowledgeLevel,
        'response_depth': _depthPreference,
        'curiosity_preference': _curiosityPreference,
      });
      await ref.read(onboardingCompletedProvider.notifier).setCompleted(true);
      ref.invalidate(transparentProfileProvider);
      ref.invalidate(profileContextProvider);
      ref.invalidate(inferredPreferencesProvider);
      ref.invalidate(activePoliciesProvider);
      if (mounted) {
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.achievementRare),
        );
        if (firstMessage != null && firstMessage.isNotEmpty) {
          context.go('/chat', extra: {'initial_ai_message': firstMessage});
        } else {
          context.go('/home');
        }
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}
