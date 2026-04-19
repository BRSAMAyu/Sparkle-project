import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/chat/presentation/providers/guidance_mode_provider.dart';

/// A compact segmented toggle for switching between AI-guided and self-guided
/// interaction styles in the chat context controls area.
///
/// This is NOT a mode switch — it adjusts how proactive the AI is.
/// It sits alongside the mode selector pill, not replacing it.
class GuidanceModeToggle extends ConsumerWidget {
  const GuidanceModeToggle({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(guidanceModeProvider);
    final l10n = I18nService.instance.l10n;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: MaterialStyler(
        material: AppMaterials.ceramic(context).copyWith(
          backgroundColor: isDark ? DS.surfaceSecondary : DS.surfaceTertiary,
        ),
        borderRadius: DS.borderRadius20,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing4,
          vertical: DS.spacing4,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _Segment(
              icon: Icons.auto_awesome,
              label: l10n.guidanceModeAi,
              isSelected: mode == GuidanceMode.aiGuide,
              color: DS.brandPrimaryConst,
              onTap: () => ref
                  .read(guidanceModeProvider.notifier)
                  .mode = GuidanceMode.aiGuide,
            ),
            _Segment(
              icon: Icons.self_improvement_rounded,
              label: l10n.guidanceModeSelf,
              isSelected: mode == GuidanceMode.selfGuide,
              color: const Color(0xFF00897B),
              onTap: () => ref
                  .read(guidanceModeProvider.notifier)
                  .mode = GuidanceMode.selfGuide,
            ),
          ],
        ),
      ),
    );
  }
}

class _Segment extends StatelessWidget {
  const _Segment({
    required this.icon,
    required this.label,
    required this.isSelected,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool isSelected;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing10,
            vertical: DS.spacing6,
          ),
          decoration: BoxDecoration(
            color: isSelected ? color.withValues(alpha: 0.15) : null,
            borderRadius: DS.borderRadius16,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: DS.iconSizeXs,
                color: isSelected ? color : DS.textTertiary,
              ),
              const SizedBox(width: DS.spacing4),
              Text(
                label,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  fontWeight:
                      isSelected ? DS.fontWeightSemibold : DS.fontWeightRegular,
                  color: isSelected ? color : DS.textTertiary,
                ),
              ),
            ],
          ),
        ),
      );
}
