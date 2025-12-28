import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/user_model.dart';
import 'package:sparkle/data/repositories/user_repository.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/widgets/profile/preference_controller_2d.dart';

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
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('学习偏好保存成功！')),
        );
        context.pop(); // Go back to previous screen
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('保存失败: $e')),
        );
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
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(
        title: const Text('学习模式设置'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(AppDesignTokens.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '拖动火苗调整你的学习偏好',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: AppDesignTokens.fontWeightMedium,
                  ),
            ),
            const SizedBox(height: AppDesignTokens.spacing24),
            Center(
              child: PreferenceController2D(
                initialDepth: _currentDepthPreference,
                initialCuriosity: _currentCuriosityPreference,
                onPreferenceChanged: (newPreferences) {
                  setState(() {
                    _currentCuriosityPreference = newPreferences.dx; // dx is curiosity
                    _currentDepthPreference = newPreferences.dy;   // dy is depth
                  });
                },
              ),
            ),
            const SizedBox(height: AppDesignTokens.spacing24),
            Text(
              '深度偏好 (Y轴): ${(_currentDepthPreference * 100).toStringAsFixed(0)}%',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppDesignTokens.neutral600),
            ),
            Text(
              '好奇心偏好 (X轴): ${(_currentCuriosityPreference * 100).toStringAsFixed(0)}%',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppDesignTokens.neutral600),
            ),
            const Spacer(),
            Center(
              child: ElevatedButton(
                onPressed: _isLoading ? null : _savePreferences,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 15),
                  shape: RoundedRectangleBorder(
                    borderRadius: AppDesignTokens.borderRadius12,
                  ),
                ),
                child: _isLoading ? const CircularProgressIndicator() : const Text('保存偏好'),
              ),
            ),
          ],
        ),
      ),
    );
}
