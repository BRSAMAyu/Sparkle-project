import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/group_recommendation_card.dart';

class GroupDiscoverScreen extends ConsumerWidget {
  const GroupDiscoverScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recommendationsState = ref.watch(groupDiscoverProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('Discover Groups'),
        centerTitle: true,
      ),
      child: recommendationsState.when(
        data: (items) {
          if (items.isEmpty) {
            return Center(
              child: CompactEmptyState(
                message: 'No recommendations yet',
                icon: Icons.group_outlined,
                actionText: 'Refresh',
                onAction: () {
                  ref.read(groupDiscoverProvider.notifier).refresh();
                },
              ),
            );
          }
          return ContentConstraint(
            child: RefreshIndicator(
              onRefresh: () async =>
                  ref.read(groupDiscoverProvider.notifier).refresh(),
              child: ListView.separated(
                padding: const EdgeInsets.all(DS.spacing16),
                itemCount: items.length,
                separatorBuilder: (context, index) =>
                    const SizedBox(height: DS.spacing12),
                itemBuilder: (context, index) {
                  final item = items[index];
                  return GroupRecommendationCard(
                    recommendation: item,
                    onTap: () {
                      context.push('/community/groups/${item.group.id}');
                    },
                    onJoin: () async {
                      await ref
                          .read(groupDiscoverProvider.notifier)
                          .join(item.group.id);
                    },
                    onDismiss: () async {
                      await ref
                          .read(groupDiscoverProvider.notifier)
                          .dismiss(item.group.id);
                    },
                  );
                },
              ),
            ),
          );
        },
        loading: () => const Center(child: LoadingIndicator()),
        error: (error, stackTrace) => Center(
          child: CustomErrorWidget.page(
            context: context,
            message: error.toString(),
            onRetry: () {
              ref.read(groupDiscoverProvider.notifier).refresh();
            },
          ),
        ),
      ),
    );
  }
}
