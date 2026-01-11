import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';

class NightlyReviewPanel extends ConsumerWidget {
  const NightlyReviewPanel({super.key, this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reviewAsync = ref.watch(nightlyReviewProvider);
    final actions = ref.watch(nightlyReviewActionsProvider);

    return reviewAsync.when(
      data: (review) {
        final payload = review?.widgetPayload;
        if (review == null || payload == null) {
          return const SizedBox.shrink();
        }
        if (review.status == 'reviewed') {
          return const SizedBox.shrink();
        }

        final content = ActionCard(
          action: payload,
          onConfirm: () async {
            await actions.markReviewed(review.id);
          },
        );

        if (!compact) {
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: content,
          );
        }

        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: context.colors.surfaceCard,
              borderRadius: DS.borderRadius16,
              boxShadow: DS.shadowSm,
            ),
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing8),
              child: content,
            ),
          ),
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }
}
