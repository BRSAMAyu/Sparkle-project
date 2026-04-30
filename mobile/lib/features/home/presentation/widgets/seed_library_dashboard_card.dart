import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';

/// Seed Library Dashboard Card
/// Displays featured libraries and subscription stats
class SeedLibraryDashboardCard extends ConsumerWidget {
  const SeedLibraryDashboardCard({
    super.key,
    this.compact = false,
    this.dense = false,
  });

  final bool compact;
  final bool dense;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final padding = compact ? (dense ? DS.spacing10 : DS.spacing12) : DS.lg;
    final iconSize = dense ? 16.0 : (compact ? 18.0 : 20.0);

    return SparklePressable(
      onTap: () => context.push('/seed-libraries'),
      padding: EdgeInsets.zero,
      borderRadius: DS.borderRadius20,
      child: MaterialStyler(
        material: AppMaterials.ceramic(context).copyWith(
          backgroundGradient: LinearGradient(
            colors: [
              DS.success.withValues(alpha: 0.12),
              DS.surfaceSecondary,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderColor: DS.success.withValues(alpha: 0.22),
          borderWidth: 1,
        ),
        borderRadius: DS.borderRadius20,
        padding: EdgeInsets.all(padding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row with icon and badge
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Icon(
                  Icons.auto_stories_rounded,
                  color: DS.success,
                  size: iconSize,
                ),
                // Official badge
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: DS.success.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    I18nService.instance.isChinese ? '官方' : 'Official',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      fontWeight: FontWeight.bold,
                      fontSize: 9,
                      color: DS.success,
                    ),
                  ),
                ),
              ],
            ),
            const Spacer(),
            // Title
            Text(
              I18nService.instance.isChinese ? '种子库' : 'Seed Library',
              style: context.sparkleTypography.labelLarge.copyWith(
                fontSize: dense ? 13 : null,
                fontWeight: FontWeight.bold,
                color: DS.textPrimary,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: DS.xs),
            // Subtitle
            Text(
              I18nService.instance.isChinese ? '知识内容仓库' : 'Knowledge repository',
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
            SizedBox(height: dense ? DS.spacing4 : DS.spacing6),
            // Stats
            Text(
              I18nService.instance.isChinese ? '3 个官方库 · 社区精选' : '3 official libs · Community picks',
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
                height: 1.4,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
