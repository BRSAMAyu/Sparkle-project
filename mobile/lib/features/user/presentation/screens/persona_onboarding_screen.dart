import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
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
  int _currentStep = 0;
  String _goalType = 'exam';
  String _learningStyle = 'balanced';
  String _knowledgeLevel = 'beginner';
  double _studyMinutes = 60;
  double _depthPreference = 0.5;
  double _curiosityPreference = 0.5;
  bool _submitting = false;

  @override
  void dispose() {
    _goalController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final steps = _buildSteps(l10n);
    return SparklePageScaffold(
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
    );
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
                onChanged: (v) => setState(() => _studyMinutes = v),
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
                onChanged: (v) => setState(() => _depthPreference = v),
              ),
              const SizedBox(height: DS.spacing12),
              Text(l10n.personaCuriosityExtension),
              Slider(
                value: _curiosityPreference,
                divisions: 10,
                onChanged: (v) => setState(() => _curiosityPreference = v),
              ),
            ],
          ),
          isActive: _currentStep >= 4,
        ),
      ];

  ChoiceChip _styleChip(String value, String label) => ChoiceChip(
        label: Text(label),
        selected: _learningStyle == value,
        onSelected: (_) => setState(() => _learningStyle = value),
      );

  ChoiceChip _goalTypeChip(String value, String label) => ChoiceChip(
        label: Text(label),
        selected: _goalType == value,
        onSelected: (_) => setState(() => _goalType = value),
      );

  ChoiceChip _levelChip(String value, String label) => ChoiceChip(
        label: Text(label),
        selected: _knowledgeLevel == value,
        onSelected: (_) => setState(() => _knowledgeLevel = value),
      );

  void _handleBack() {
    if (_currentStep == 0) return;
    setState(() => _currentStep -= 1);
  }

  Future<void> _handleContinue(int totalSteps) async {
    if (_currentStep < totalSteps - 1) {
      setState(() => _currentStep += 1);
      return;
    }

    setState(() => _submitting = true);
    final repo = ref.read(userRepositoryProvider);
    try {
      await repo.submitOnboarding({
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
      if (mounted) {
        context.go('/home');
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}
