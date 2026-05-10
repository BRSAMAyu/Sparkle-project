import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';

class ActiveBottleneckAlert extends StatelessWidget {
  const ActiveBottleneckAlert({
    super.key,
    this.bottleneck,
    this.onOpenChat,
  });

  final HomeBottleneck? bottleneck;
  final ValueChanged<HomeBottleneck>? onOpenChat;

  @override
  Widget build(BuildContext context) {
    final activeBottleneck = bottleneck;
    if (activeBottleneck == null) {
      return const SizedBox.shrink();
    }

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing8,
        ),
        child: MaterialStyler(
          material: AppMaterials.ceramic(context).copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                DS.warning.withValues(alpha: 0.14),
                DS.surfacePrimaryElevated,
              ],
            ),
            borderColor: DS.warning.withValues(alpha: 0.22),
            borderWidth: 1,
          ),
          borderRadius: DS.borderRadius16,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing12,
          ),
          child: ConstrainedBox(
            key: const ValueKey('active-bottleneck-alert'),
            constraints: const BoxConstraints(minHeight: 64),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: DS.warning.withValues(alpha: 0.14),
                    borderRadius: DS.borderRadius12,
                    border: Border.all(
                      color: DS.warning.withValues(alpha: 0.22),
                    ),
                  ),
                  child: Text(
                    '⚡',
                    style: context.sparkleTypography.titleLarge.copyWith(
                      color: DS.warning,
                    ),
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Text(
                    context.l10n.bottleneckAlertMessage(activeBottleneck.topic),
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: context.sparkleTypography.bodyMedium.copyWith(
                      color: DS.textPrimary,
                      height: 1.35,
                    ),
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                TextButton(
                  key: const ValueKey('active-bottleneck-open-chat'),
                  onPressed: onOpenChat == null
                      ? null
                      : () => onOpenChat!(activeBottleneck),
                  child: Text(
                    context.l10n.bottleneckAlertAction,
                    style: context.sparkleTypography.labelLarge.copyWith(
                      color: DS.warning,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
