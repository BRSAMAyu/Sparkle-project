import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/persona_onboarding_draft.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/user_routes.dart';
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
  // J-02（A-SPEC8B 改造 #3 / N50 前半）：5 步引导 + 已填内容的断点续存，
  // 防抖 400ms 落 per-user prefs；跳过/提交成功即清除。
  Timer? _draftSaveDebounce;
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
    _goalController.addListener(_onFieldMutated);
    unawaited(_restoreDraft());
  }

  @override
  void dispose() {
    _previewDebounce?.cancel();
    _draftSaveDebounce?.cancel();
    _goalController.dispose();
    super.dispose();
  }

  String? get _currentUserId => ref.read(authProvider).user?.id;

  /// 恢复上次中断的引导草稿（步数 + 已填内容），恢复值经 clamp 钳位——
  /// 旧版本/损坏数据不致把用户带进非法状态。
  Future<void> _restoreDraft() async {
    final userId = _currentUserId;
    if (userId == null) return;
    final draft =
        await ref.read(personaOnboardingDraftStoreProvider).load(userId);
    if (!mounted || draft == null) return;
    final restored = draft.clamp();
    setState(() {
      _currentStep = restored.step;
      _goalType = restored.goalType;
      _learningStyle = restored.learningStyle;
      _knowledgeLevel = restored.knowledgeLevel;
      _studyMinutes = restored.studyMinutes;
      _depthPreference = restored.depthPreference;
      _curiosityPreference = restored.curiosityPreference;
      if (restored.goalText.isNotEmpty) {
        // 经 listener 顺带重排预览（_onFieldMutated），内容与草稿一致时
        // 再存一次为幂等写，无害。
        _goalController.text = restored.goalText;
      }
    });
  }

  PersonaOnboardingDraft _draftSnapshot() => PersonaOnboardingDraft(
        step: _currentStep,
        goalType: _goalType,
        goalText: _goalController.text.trim(),
        learningStyle: _learningStyle,
        knowledgeLevel: _knowledgeLevel,
        studyMinutes: _studyMinutes,
        depthPreference: _depthPreference,
        curiosityPreference: _curiosityPreference,
      );

  void _scheduleDraftSave() {
    _draftSaveDebounce?.cancel();
    _draftSaveDebounce = Timer(const Duration(milliseconds: 400), () {
      unawaited(_saveDraftNow());
    });
  }

  Future<void> _saveDraftNow() async {
    final userId = _currentUserId;
    if (userId == null) return;
    await ref
        .read(personaOnboardingDraftStoreProvider)
        .save(userId, _draftSnapshot());
  }

  Future<void> _clearDraft() async {
    _draftSaveDebounce?.cancel();
    final userId = _currentUserId;
    if (userId == null) return;
    await ref.read(personaOnboardingDraftStoreProvider).clear(userId);
  }

  /// 任一字段变更的统一入口：重排 AI 预览 + 防抖续存草稿。
  void _onFieldMutated() {
    _schedulePreview();
    _scheduleDraftSave();
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
          actions: [
            SparkleButton.ghost(
              label: l10n.onboardingSkip,
              onPressed: _handleSkip,
            ),
          ],
        ),
        child: ContentConstraint(
          child: GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            margin: const EdgeInsets.symmetric(vertical: DS.spacing16),
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
                      label:
                          isLast ? l10n.personaComplete : l10n.personaNextStep,
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
                  _onFieldMutated();
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
                  _onFieldMutated();
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
                  _onFieldMutated();
                },
              ),
            ],
          ),
          isActive: _currentStep >= 4,
        ),
      ];

  Widget _styleChip(String value, String label) => SemanticPill(
        label: label,
        tone: PillTone.neutral,
        selected: _learningStyle == value,
        // 触感由 SparklePressable 默认 tap 反馈提供（Step 1 申报：selection→tap）。
        onTap: () {
          setState(() => _learningStyle = value);
          _onFieldMutated();
        },
      );

  Widget _goalTypeChip(String value, String label) => SemanticPill(
        label: label,
        tone: PillTone.neutral,
        selected: _goalType == value,
        // 触感由 SparklePressable 默认 tap 反馈提供（Step 1 申报：selection→tap）。
        onTap: () {
          setState(() => _goalType = value);
          _onFieldMutated();
        },
      );

  Widget _levelChip(String value, String label) => SemanticPill(
        label: label,
        tone: PillTone.neutral,
        selected: _knowledgeLevel == value,
        // 触感由 SparklePressable 默认 tap 反馈提供（Step 1 申报：selection→tap）。
        onTap: () {
          setState(() => _knowledgeLevel = value);
          _onFieldMutated();
        },
      );

  void _handleBack() {
    if (_currentStep == 0) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    setState(() => _currentStep -= 1);
    unawaited(_saveDraftNow());
  }

  void _handleSkip() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    // 用户显式放弃 persona 逐页引导 → 清除草稿（建模访谈完成即整体完成）。
    unawaited(_clearDraft());
    ref.invalidate(transparentProfileProvider);
    ref.invalidate(profileContextProvider);
    ref.invalidate(inferredPreferencesProvider);
    ref.invalidate(activePoliciesProvider);
    if (mounted) {
      context.go(UserRoutes.modelingChat);
    }
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
        _previewMessage = context.l10n.userOnboardingPreviewMessage(goal);
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
                  context.l10n.userOnboardingAIUnderstanding,
                  style: textTheme.labelLarge?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const SizedBox(height: DS.spacing4),
                if (_previewLoading)
                  Text(
                    context.l10n.userOnboardingGenerating,
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
      unawaited(_saveDraftNow());
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
      ref.invalidate(transparentProfileProvider);
      ref.invalidate(profileContextProvider);
      ref.invalidate(inferredPreferencesProvider);
      ref.invalidate(activePoliciesProvider);
      // 提交成功 → 引导闭环，草稿使命结束。
      unawaited(_clearDraft());
      if (mounted) {
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.achievementRare),
        );
        context.go(
          UserRoutes.modelingChat,
          extra: {'post_onboarding_message': firstMessage},
        );
      }
    } catch (error) {
      // V13-MAJORS M-01 连带面：提交超时/失败原先只有 try/finally——按钮转圈
      // 结束后原地复活，用户对成败零反馈（V13 实测 30s 超时静默）。现在给出
      // 可见反馈 + 重试动作；重试即重新提交（服务端写路径为 upsert，幂等）。
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SparkleSnackBar.error(
          context.l10n.userOnboardingSubmitFailed,
          onRetry: () {
            if (mounted) {
              unawaited(_handleContinue(totalSteps));
            }
          },
          retryLabel: context.l10n.retry,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}
