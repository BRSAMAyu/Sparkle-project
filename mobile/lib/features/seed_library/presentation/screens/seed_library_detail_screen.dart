import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/seed_library/presentation/widgets/seed_item_card.dart';

/// Seed Library Detail Screen
/// Displays details of a single seed library and its items
class SeedLibraryDetailScreen extends ConsumerStatefulWidget {
  const SeedLibraryDetailScreen({
    required this.libraryId,
    super.key,
  });

  final String libraryId;

  @override
  ConsumerState<SeedLibraryDetailScreen> createState() =>
      _SeedLibraryDetailScreenState();
}

class _SeedLibraryDetailScreenState
    extends ConsumerState<SeedLibraryDetailScreen> {
  @override
  Widget build(BuildContext context) {
    final state = ref.watch(seedLibraryDetailProvider(widget.libraryId));

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(state.library?.name ?? '种子库详情'),
        actions: [
          if (state.library != null &&
              state.library!.ownerId == null) // Editable check
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.edit),
              onPressed: () {
                // TODO: Implement edit
              },
            ),
          if (state.library != null && state.library!.ownerId == null)
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.delete),
              onPressed: () => _showDeleteDialog(context),
            ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'subscribe') {
                ref
                    .read(seedLibraryDetailProvider(widget.libraryId).notifier)
                    .toggleSubscription();
              }
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'subscribe',
                child: Text(
                  state.isSubscribed ? '取消订阅' : '订阅',
                ),
              ),
            ],
          ),
        ],
      ),
      child: _buildBody(context, state),
    );
  }

  Widget _buildBody(
    BuildContext context,
    SeedLibraryDetailState state,
  ) {
    if (state.isLoadingLibrary) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.library == null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: DS.spacing64, color: DS.error),
            const SizedBox(height: DS.spacing16),
            Text(state.error!),
            const SizedBox(height: DS.spacing16),
            SparkleButton(
              onPressed: () => ref
                  .read(seedLibraryDetailProvider(widget.libraryId).notifier)
                  .loadLibrary(),
              variant: ButtonVariant.destructive,
              icon: const Icon(Icons.refresh),
              label: '重试',
            ),
          ],
        ),
      );
    }

    if (state.library == null) {
      return const Center(child: Text('种子库不存在'));
    }

    final library = state.library!;

    return RefreshIndicator(
      onRefresh: () async {
        await ref
            .read(seedLibraryDetailProvider(widget.libraryId).notifier)
            .loadLibrary();
        await ref
            .read(seedLibraryDetailProvider(widget.libraryId).notifier)
            .loadItems(refresh: true);
      },
      child: CustomScrollView(
        slivers: [
          // Header section
          SliverToBoxAdapter(
            child: ContentConstraint(
              child: Padding(
                padding: const EdgeInsets.all(DS.spacing16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Category and visibility badges
                    Wrap(
                      spacing: DS.spacing8,
                      children: [
                        Chip(
                          label: Text(library.category.displayName),
                          backgroundColor:
                              Theme.of(context).colorScheme.primaryContainer,
                        ),
                        Chip(
                          label: Text(library.visibility.displayName),
                          backgroundColor:
                              library.visibility == LibraryVisibility.official
                                  ? DS.warningAccent
                                  : null,
                        ),
                        if (library.isOfficial || library.isFeatured)
                          Icon(
                            library.isOfficial ? Icons.verified : Icons.star,
                            color: library.isOfficial
                                ? DS.warning
                                : DS.warningLight,
                            size: DS.iconSizeSm,
                          ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing12),

                    // Description
                    if (library.description != null) ...[
                      Text(
                        library.description!,
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: DS.spacing12),
                    ],

                    // Stats
                    Wrap(
                      spacing: DS.spacing16,
                      runSpacing: DS.spacing8,
                      children: [
                        _buildStatItem(
                          context,
                          Icons.article_outlined,
                          '${library.itemCount}',
                          '内容',
                        ),
                        _buildStatItem(
                          context,
                          Icons.people_outline,
                          '${library.subscriberCount}',
                          '订阅者',
                        ),
                        _buildStatItem(
                          context,
                          Icons.visibility_outlined,
                          '${library.usageCount}',
                          '使用',
                        ),
                        if (library.qualityScore != null)
                          _buildStatItem(
                            context,
                            Icons.star,
                            library.qualityScore!.toStringAsFixed(1),
                            '质量分',
                          ),
                      ],
                    ),

                    // Tags
                    if (library.tags != null && library.tags!.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing12),
                      Wrap(
                        spacing: DS.spacing8,
                        children: library.tags!
                            .map((tag) => Chip(
                                label: Text(tag),
                                labelPadding: EdgeInsets.zero,),)
                            .toList(),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),

          // Items section
          SliverToBoxAdapter(
            child: ContentConstraint(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(
                  DS.spacing16,
                  DS.spacing8,
                  DS.spacing16,
                  DS.spacing8,
                ),
                child: Row(
                  children: [
                    Text(
                      '内容项',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const Spacer(),
                    SparkleButton.ghost(
                      onPressed: () {
                        // TODO: Show filter dialog
                      },
                      icon: const Icon(Icons.filter_list, size: DS.iconSizeXs),
                      label: '筛选',
                    ),
                  ],
                ),
              ),
            ),
          ),

          // Items list
          if (state.items.isEmpty)
            SliverFillRemaining(
              child: state.isLoadingItems
                  ? const Center(child: CircularProgressIndicator())
                  : Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.inbox_outlined,
                              size: DS.spacing64, color: DS.textTertiary,),
                          const SizedBox(height: DS.spacing16),
                          Text(
                            '暂无内容',
                            style:
                                Theme.of(context).textTheme.bodyLarge?.copyWith(
                                      color: DS.textSecondary,
                                    ),
                          ),
                        ],
                      ),
                    ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.all(DS.spacing16),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    if (index >= state.items.length) {
                      // Load more indicator
                      ref
                          .read(seedLibraryDetailProvider(widget.libraryId)
                              .notifier,)
                          .loadItems();
                      return const SizedBox(
                        height: 100,
                        child: Center(child: CircularProgressIndicator()),
                      );
                    }

                    final item = state.items[index];
                    return SeedItemCard(item: item);
                  },
                  childCount: state.items.length + (state.hasMoreItems ? 1 : 0),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildStatItem(
    BuildContext context,
    IconData icon,
    String value,
    String label,
  ) =>
      Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: DS.textSecondary),
          const SizedBox(width: DS.spacing4),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(width: 2),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
        ],
      );

  void _showDeleteDialog(
    BuildContext context,
  ) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除种子库'),
        content: const Text('确定要删除这个种子库吗？此操作不可撤销。'),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.pop(context),
            label: '取消',
          ),
          SparkleButton.destructive(
            onPressed: () async {
              try {
                await ref
                    .read(seedLibraryDetailProvider(widget.libraryId).notifier)
                    .deleteLibrary();
                if (context.mounted) {
                  Navigator.pop(context); // Close dialog
                  Navigator.pop(context); // Close screen
                }
              } catch (e) {
                if (context.mounted) {
                  AppFeedback.error(context, '删除失败：$e');
                }
              }
            },
            label: '删除',
          ),
        ],
      ),
    );
  }
}
