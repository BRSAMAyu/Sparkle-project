import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/cognitive_provider.dart';

class RealtimeNudgeBubble extends ConsumerStatefulWidget {
  const RealtimeNudgeBubble({super.key});

  @override
  ConsumerState<RealtimeNudgeBubble> createState() => _RealtimeNudgeBubbleState();
}

class _RealtimeNudgeBubbleState extends ConsumerState<RealtimeNudgeBubble> {
  @override
  void initState() {
    super.initState();
    // Load patterns when the widget is initialized
    _loadPatterns();
  }

  Future<void> _loadPatterns() async {
    await ref.read(cognitiveProvider.notifier).loadPatterns();
  }

  @override
  Widget build(BuildContext context) {
    final cognitiveState = ref.watch(cognitiveProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    // Get the latest pattern with a solution text
    final patternsWithSolution = cognitiveState.patterns.where(
      (pattern) => pattern.solutionText != null && pattern.solutionText!.isNotEmpty,
    );
    final latestPatternWithSolution = patternsWithSolution.isNotEmpty ? patternsWithSolution.first : null;

    if (cognitiveState.isLoading || latestPatternWithSolution == null) {
      return const SizedBox.shrink(); // Don't show if loading or no relevant patterns
    }

    return GestureDetector(
      onTap: () {
        // Navigate to the pattern list or a detail view if available
        context.go('/cognitive/patterns');
      },
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: AppDesignTokens.spacing16),
        padding: const EdgeInsets.all(AppDesignTokens.spacing12),
        decoration: BoxDecoration(
          color: isDark ? AppDesignTokens.neutral800 : AppDesignTokens.info.withOpacity(0.1),
          borderRadius: AppDesignTokens.borderRadius16,
          boxShadow: isDark ? null : AppDesignTokens.shadowSm,
          border: Border.all(color: AppDesignTokens.info.withOpacity(0.3)),
        ),
        child: Row(
          children: [
            const Icon(Icons.lightbulb_outline, color: AppDesignTokens.info, size: 24),
            const SizedBox(width: AppDesignTokens.spacing12),
            Expanded(
              child: Text(
                '💡 ${latestPatternWithSolution.patternName}: ${latestPatternWithSolution.solutionText}',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: isDark ? AppDesignTokens.neutral200 : AppDesignTokens.neutral800,
                  fontWeight: FontWeight.w500,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: AppDesignTokens.spacing8),
            const Icon(Icons.arrow_forward_ios_rounded, color: AppDesignTokens.neutral400, size: 16),
          ],
        ),
      ),
    );
  }
}
