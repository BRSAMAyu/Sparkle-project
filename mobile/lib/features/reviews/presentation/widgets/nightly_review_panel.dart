import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_motion.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/reviews/reviews_routes.dart';

class NightlyReviewPanel extends ConsumerWidget {
  const NightlyReviewPanel({super.key, this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reviewAsync = ref.watch(nightlyReviewProvider);

    return reviewAsync.when(
      data: (review) {
        if (review == null || review.widgetPayload == null) {
          return const SizedBox.shrink();
        }
        if (review.status == 'reviewed') {
          return const SizedBox.shrink();
        }

        return ContentConstraint(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
              DS.spacing16,
              DS.spacing4,
              DS.spacing16,
              compact ? DS.spacing12 : DS.spacing16,
            ),
            child: DashboardEntrance(
              index: 6,
              slideOffset: const Offset(0, -0.06),
              duration: DS.durationFast,
              child: DashboardPressable(
                onTap: () => context.push(ReviewRoutes.planHub),
                borderRadius: DS.borderRadius16,
                child: MaterialStyler(
                  material: AppMaterials.ceramic(context),
                  borderRadius: DS.borderRadius16,
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing12,
                    vertical: DS.spacing10,
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 22,
                        height: 22,
                        decoration: BoxDecoration(
                          color: DS.surfaceOverlay,
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          Icons.dark_mode_outlined,
                          color: DS.brandSecondary,
                          size: 14,
                        ),
                      ),
                      const SizedBox(width: DS.spacing10),
                      Expanded(
                        child: Text(
                          context.l10n.nightlyReviewPending,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: context.sparkleTypography.labelLarge.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightSemiBold,
                          ),
                        ),
                      ),
                      InkWell(
                        onTap: () => context.push(ReviewRoutes.planHub),
                        borderRadius: BorderRadius.circular(999),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: DS.spacing4,
                            vertical: 2,
                          ),
                          child: Text(
                            context.l10n.nightlyReviewStart,
                            style:
                                context.sparkleTypography.labelLarge.copyWith(
                              color: DS.brandPrimary,
                              fontWeight: DS.fontWeightBold,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, __) => CompactErrorCard(
        onRetry: () => ref.invalidate(nightlyReviewProvider),
      ),
    );
  }
}
