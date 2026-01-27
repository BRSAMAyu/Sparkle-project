import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

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
    final steps = _buildSteps();
    return Scaffold(
      appBar: AppBar(
        title: const Text('画像引导'),
      ),
      body: ContentConstraint(
        child: Stepper(
          currentStep: _currentStep,
          onStepContinue: _submitting ? null : () => _handleContinue(steps.length),
        onStepCancel: _submitting ? null : _handleBack,
        controlsBuilder: (context, details) {
          final isLast = _currentStep == steps.length - 1;
          return Row(
            children: [
              ElevatedButton(
                onPressed: details.onStepContinue,
                child: _submitting
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(isLast ? '完成' : '下一步'),
              ),
              const SizedBox(width: DS.spacing12),
              if (_currentStep > 0)
                TextButton(
                  onPressed: details.onStepCancel,
                  child: const Text('上一步'),
                ),
            ],
          );
        },
        steps: steps,
      ),
      ),
    );
  }

  List<Step> _buildSteps() => [
        Step(
          title: const Text('学习目标'),
          content: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: DS.spacing8,
                children: [
                  _goalTypeChip('exam', '考试'),
                  _goalTypeChip('skill', '技能'),
                  _goalTypeChip('interest', '兴趣'),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              TextField(
                controller: _goalController,
                decoration: const InputDecoration(
                  hintText: '例如：备考期末 / 学会Flutter',
                ),
              ),
            ],
          ),
          isActive: _currentStep >= 0,
        ),
        Step(
          title: const Text('学习风格'),
          content: Wrap(
            spacing: DS.spacing8,
            children: [
              _styleChip('balanced', '平衡'),
              _styleChip('visual', '视觉'),
              _styleChip('practice', '实践'),
              _styleChip('logic', '逻辑'),
            ],
          ),
          isActive: _currentStep >= 1,
        ),
        Step(
          title: const Text('每日学习时长'),
          content: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('$_studyMinutes 分钟'),
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
          title: const Text('知识水平'),
          content: Wrap(
            spacing: DS.spacing8,
            children: [
              _levelChip('beginner', '入门'),
              _levelChip('intermediate', '进阶'),
              _levelChip('advanced', '高级'),
            ],
          ),
          isActive: _currentStep >= 3,
        ),
        Step(
          title: const Text('回答偏好'),
          content: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('回答详细程度'),
              Slider(
                value: _depthPreference,
                divisions: 10,
                onChanged: (v) => setState(() => _depthPreference = v),
              ),
              const SizedBox(height: DS.spacing12),
              const Text('好奇心扩展程度'),
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
