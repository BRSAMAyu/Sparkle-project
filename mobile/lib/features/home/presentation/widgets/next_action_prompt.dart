import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';

class NextActionPrompt extends StatelessWidget {
  const NextActionPrompt({
    super.key,
    this.task,
    this.isLoading = false,
    this.onStart,
    this.onOpenTasks,
  });

  final HomeGrowthTask? task;
  final bool isLoading;
  final ValueChanged<HomeGrowthTask>? onStart;
  final VoidCallback? onOpenTasks;

  @override
  Widget build(BuildContext context) {
    final activeTask = task;
    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: MaterialStyler(
          material: AppMaterials.ceramic(context).copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                DS.surfacePrimaryElevated,
                DS.brandPrimary.withValues(alpha: 0.07),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderColor: DS.brandPrimary.withValues(alpha: 0.16),
            borderWidth: 1,
          ),
          borderRadius: DS.borderRadius16,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing12,
          ),
          child: ConstrainedBox(
            key: const ValueKey('next-action-prompt'),
            constraints: const BoxConstraints(minHeight: 48),
            child: isLoading
                ? const _NextActionSkeleton()
                : Row(
                    children: [
                      Expanded(
                        child: Text(
                          activeTask == null
                              ? (I18nService.instance.isChinese
                                  ? '现在最值得做的：给今天做一个轻量复盘'
                                  : 'Best move right now: do a quick review of today')
                              : (I18nService.instance.isChinese
                                  ? '现在最值得做的：${activeTask.title}'
                                  : 'Best move right now: ${activeTask.title}'),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: context.sparkleTypography.bodyMedium.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightBold,
                            height: 1.3,
                          ),
                        ),
                      ),
                      const SizedBox(width: DS.spacing12),
                      SparkleButton(
                        key: const ValueKey('next-action-start-button'),
                        label: activeTask == null
                            ? (I18nService.instance.isChinese ? '查看' : 'View')
                            : (I18nService.instance.isChinese ? '开始' : 'Start'),
                        size: ButtonSize.small,
                        icon: Icon(
                          activeTask == null
                              ? Icons.list_alt_rounded
                              : Icons.play_arrow_rounded,
                        ),
                        onPressed: activeTask == null
                            ? onOpenTasks
                            : () => onStart?.call(activeTask),
                        disabled: activeTask == null
                            ? onOpenTasks == null
                            : onStart == null,
                      ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}

class _NextActionSkeleton extends StatelessWidget {
  const _NextActionSkeleton();

  @override
  Widget build(BuildContext context) => const Row(
        children: [
          Expanded(
            child: SparkleSkeleton(height: 18, borderRadius: 9),
          ),
          SizedBox(width: DS.spacing12),
          SparkleSkeleton(width: 72, height: 36, borderRadius: 18),
        ],
      );
}
