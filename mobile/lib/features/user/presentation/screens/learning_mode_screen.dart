import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/widgets/preference_controller_2d.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class LearningModeScreen extends ConsumerStatefulWidget {
  const LearningModeScreen({super.key});

  @override
  ConsumerState<LearningModeScreen> createState() => _LearningModeScreenState();
}

class _LearningModeScreenState extends ConsumerState<LearningModeScreen> {
  double _currentDepthPreference = 0.5;
  double _currentCuriosityPreference = 0.5;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadUserPreferences();
  }

  void _loadUserPreferences() {
    final user = ref.read(authProvider).user;
    if (user != null) {
      setState(() {
        _currentDepthPreference = user.depthPreference;
        _currentCuriosityPreference = user.curiosityPreference;
      });
    }
  }

  Future<void> _savePreferences() async {
    setState(() {
      _isLoading = true;
    });
    try {
      final userRepo = ref.read(userRepositoryProvider);
      final userPreferences = UserPreferences(
        depthPreference: _currentDepthPreference,
        curiosityPreference: _currentCuriosityPreference,
      );

      await userRepo.updateUserPreferences(userPreferences);

      // Refresh auth provider user data to reflect changes
      await ref.read(authProvider.notifier).refreshUser();

      if (mounted) {
        AppFeedback.success(context, '学习偏好保存成功！');
        context.pop(); // Go back to previous screen
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '保存失败: $e');
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => SparklePageScaffold(
        role: SparklePageRole.settings,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            size: DS.touchTargetMinSize,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: const Text('学习模式设置'),
        ),
        child: ContentConstraint(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(DS.spacing16),
            child: GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '拖动火苗调整你的学习偏好',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: DS.fontWeightMedium,
                        ),
                  ),
                  const SizedBox(height: DS.spacing24),
                  Center(
                    child: PreferenceController2D(
                      initialDepth: _currentDepthPreference,
                      initialCuriosity: _currentCuriosityPreference,
                      onPreferenceChanged: (newPreferences) {
                        setState(() {
                          _currentCuriosityPreference =
                              newPreferences.dx; // dx is curiosity
                          _currentDepthPreference =
                              newPreferences.dy; // dy is depth
                        });
                      },
                    ),
                  ),
                  const SizedBox(height: DS.spacing24),
                  Text(
                    '深度偏好 (Y轴): ${(_currentDepthPreference * 100).toStringAsFixed(0)}%',
                    style: Theme.of(context)
                        .textTheme
                        .bodyMedium
                        ?.copyWith(color: DS.neutral600),
                  ),
                  Text(
                    '好奇心偏好 (X轴): ${(_currentCuriosityPreference * 100).toStringAsFixed(0)}%',
                    style: Theme.of(context)
                        .textTheme
                        .bodyMedium
                        ?.copyWith(color: DS.neutral600),
                  ),
                  const SizedBox(height: DS.spacing24),
                  Center(
                    child: SparkleButton(
                      onPressed: _isLoading ? null : _savePreferences,
                      label: '保存偏好',
                      loading: _isLoading,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}
