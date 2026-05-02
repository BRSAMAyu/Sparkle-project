import 'dart:async';
import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/text_rendering.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/share_resource_sheet.dart';
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
  ItemType? _selectedItemType;
  DifficultyLevel? _selectedDifficulty;
  bool _showInactiveItems = false;

  String _friendlyActionError(Object error) {
    final raw = error.toString().replaceFirst('Exception: ', '').trim();
    if (raw.isEmpty || raw.toLowerCase() == 'null') {
      return context.l10n.seedLibraryDetailFriendlyError;
    }
    return raw;
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(seedLibraryDetailProvider(widget.libraryId));
    final currentUser = ref.watch(currentUserProvider);
    final canManageLibrary =
        state.library != null && currentUser?.id == state.library!.ownerId;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(state.library?.name ?? context.l10n.seedLibraryDetail),
        actions: [
          if (state.library != null)
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.share_outlined),
              onPressed: () {
                unawaited(
                  SensoryFeedbackService.emit(
                    SensoryFeedbackEvent.sheetOpen,
                  ),
                );
                unawaited(
                  showShareResourceSheet(
                    context,
                    resourceType: 'seed_library',
                    resourceId: state.library!.id,
                    title: state.library!.name,
                    subtitle: state.library!.description,
                  ),
                );
              },
            ),
          if (canManageLibrary)
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.playlist_add),
              onPressed: () => _showAddItemSheet(context),
            ),
          if (canManageLibrary)
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.upload_file_outlined),
              onPressed: _importJsonItems,
            ),
          if (canManageLibrary)
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.edit),
              onPressed: () => _showEditDialog(context, state.library!),
            ),
          if (canManageLibrary)
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.delete),
              onPressed: () => _showDeleteDialog(context),
            ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'subscribe') {
                unawaited(
                  ref
                      .read(
                          seedLibraryDetailProvider(widget.libraryId).notifier)
                      .toggleSubscription(),
                );
              }
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'subscribe',
                child: Text(
                  state.isSubscribed
                      ? context.l10n.seedLibraryUnsubscribe
                      : context.l10n.seedLibrarySubscribe,
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
              label: context.l10n.commonRetry,
            ),
          ],
        ),
      );
    }

    if (state.library == null) {
      return Center(child: Text(context.l10n.seedLibraryNotFound));
    }

    final library = state.library!;
    final filteredItems = state.items.where((item) {
      if (!_showInactiveItems && !item.isActive) {
        return false;
      }
      if (_selectedItemType != null && item.itemType != _selectedItemType) {
        return false;
      }
      if (_selectedDifficulty != null &&
          item.difficultyLevel != _selectedDifficulty) {
        return false;
      }
      return true;
    }).toList();

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
                child: SparkleStaggerItem(
                  index: 0,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Category and visibility badges
                      Wrap(
                        spacing: DS.spacing8,
                        children: [
                          Chip(
                            label: Text(library.categoryLabel(context.l10n)),
                            backgroundColor:
                                Theme.of(context).colorScheme.primaryContainer,
                          ),
                          Chip(
                            label: Text(library.visibility.label(context.l10n)),
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
                            context.l10n.seedLibraryContent,
                          ),
                          _buildStatItem(
                            context,
                            Icons.people_outline,
                            '${library.subscriberCount}',
                            context.l10n.seedLibrarySubscribers,
                          ),
                          _buildStatItem(
                            context,
                            Icons.visibility_outlined,
                            '${library.usageCount}',
                            context.l10n.seedLibraryUsage,
                          ),
                          if (library.qualityScore != null)
                            _buildStatItem(
                              context,
                              Icons.star,
                              library.qualityScore!.toStringAsFixed(1),
                              context.l10n.seedLibraryQualityScore,
                            ),
                          if ((library.userRatingCount ?? 0) > 0)
                            _buildStatItem(
                              context,
                              Icons.reviews_outlined,
                              '${library.userRatingCount}',
                              context.l10n.seedLibraryDetailUserRatings,
                            ),
                        ],
                      ),

                      if (library.systemQualityScore != null ||
                          library.userRatingAvg != null) ...[
                        const SizedBox(height: DS.spacing16),
                        GraphiteCardSurface(
                          surfaceRole: SparkleSurfaceRole.panel,
                          padding: const EdgeInsets.all(DS.spacing16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                context.l10n.seedLibraryDetailQualityBreakdown,
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              const SizedBox(height: DS.spacing8),
                              Text(
                                context
                                    .l10n.seedLibraryDetailQualityBreakdownDesc,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(
                                      color: DS.textSecondary,
                                      height: 1.45,
                                    ),
                              ),
                              const SizedBox(height: DS.spacing12),
                              Wrap(
                                spacing: DS.spacing12,
                                runSpacing: DS.spacing12,
                                children: [
                                  if (library.qualityScore != null)
                                    _buildQualityBadge(
                                      context,
                                      label: context.l10n
                                          .seedLibraryDetailQualityComprehensive,
                                      value: library.qualityScore!,
                                      icon: Icons.auto_awesome_outlined,
                                    ),
                                  if (library.systemQualityScore != null)
                                    _buildQualityBadge(
                                      context,
                                      label: context
                                          .l10n.seedLibraryDetailQualitySystem,
                                      value: library.systemQualityScore!,
                                      icon: Icons.settings_suggest_outlined,
                                    ),
                                  if (library.userRatingAvg != null)
                                    _buildQualityBadge(
                                      context,
                                      label: context
                                          .l10n.seedLibraryDetailQualityUser,
                                      value: library.userRatingAvg!,
                                      icon: Icons.people_outline,
                                    ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ],

                      const SizedBox(height: DS.spacing16),
                      GraphiteCardSurface(
                        surfaceRole: SparkleSurfaceRole.panel,
                        padding: const EdgeInsets.all(DS.spacing16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              context.l10n.seedLibraryDetailApplyToSystem,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: DS.spacing8),
                            Text(
                              _buildUsageExplanation(library, state),
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                  ),
                            ),
                            const SizedBox(height: DS.spacing12),
                            Wrap(
                              spacing: DS.spacing8,
                              runSpacing: DS.spacing8,
                              children: [
                                SparkleButton(
                                  onPressed: () async {
                                    try {
                                      final wasEnabled =
                                          state.subscription?.isEnabled ??
                                              false;
                                      await ref
                                          .read(seedLibraryDetailProvider(
                                                  widget.libraryId)
                                              .notifier)
                                          .toggleApplied();
                                      if (!context.mounted) return;
                                      final refreshedState = ref.read(
                                        seedLibraryDetailProvider(
                                            widget.libraryId),
                                      );
                                      final isNowEnabled = refreshedState
                                              .subscription?.isEnabled ??
                                          false;
                                      AppFeedback.success(
                                        context,
                                        isNowEnabled && !wasEnabled
                                            ? context.l10n
                                                .seedLibraryDetailAppliedSuccess
                                            : !isNowEnabled && wasEnabled
                                                ? context.l10n
                                                    .seedLibraryDetailPausedSuccess
                                                : context.l10n
                                                    .seedLibraryDetailStatusUpdated,
                                      );
                                    } catch (e) {
                                      if (!context.mounted) return;
                                      AppFeedback.error(
                                        context,
                                        context.l10n
                                            .seedLibraryDetailApplyFailed(
                                                _friendlyActionError(e)),
                                      );
                                    }
                                  },
                                  label: (state.subscription?.isEnabled ??
                                          false)
                                      ? context.l10n.seedLibraryDetailPauseUse
                                      : context
                                          .l10n.seedLibraryDetailApplyLibrary,
                                  icon: Icon(
                                    (state.subscription?.isEnabled ?? false)
                                        ? Icons.pause_circle_outline
                                        : Icons.play_circle_outline,
                                  ),
                                ),
                                SparkleButton.secondary(
                                  onPressed: () async {
                                    try {
                                      await ref
                                          .read(seedLibraryDetailProvider(
                                                  widget.libraryId)
                                              .notifier)
                                          .setAsPrimaryLibrary();
                                      if (!context.mounted) return;
                                      AppFeedback.success(
                                          context,
                                          context.l10n
                                              .seedLibraryDetailSetPrimarySuccess);
                                    } catch (e) {
                                      if (!context.mounted) return;
                                      AppFeedback.error(
                                          context,
                                          context.l10n
                                              .seedLibraryDetailSetPrimaryFailed(
                                                  e.toString()));
                                    }
                                  },
                                  label:
                                      context.l10n.seedLibraryDetailSetPrimary,
                                  icon: const Icon(Icons.vertical_align_top),
                                ),
                                SparkleButton.ghost(
                                  onPressed: () async {
                                    try {
                                      await ref
                                          .read(seedLibraryDetailProvider(
                                                  widget.libraryId)
                                              .notifier)
                                          .markNotSuitable();
                                      if (!context.mounted) return;
                                      AppFeedback.success(
                                        context,
                                        context.l10n
                                            .seedLibraryDetailMarkedNotSuitableSuccess,
                                      );
                                    } catch (e) {
                                      if (!context.mounted) return;
                                      AppFeedback.error(
                                        context,
                                        context.l10n
                                            .seedLibraryDetailMarkNotSuitableFailed(
                                                _friendlyActionError(e)),
                                      );
                                    }
                                  },
                                  label: context
                                      .l10n.seedLibraryDetailMarkNotSuitable,
                                  icon:
                                      const Icon(Icons.thumb_down_alt_outlined),
                                ),
                                SparkleButton.ghost(
                                  onPressed: () =>
                                      _showRatingSheet(context, state),
                                  label: library.currentUserRating != null
                                      ? context.l10n.seedLibraryDetailEditRating
                                      : context
                                          .l10n.seedLibraryDetailGiveRating,
                                  icon: const Icon(Icons.star_outline),
                                ),
                              ],
                            ),
                            if (state.subscription != null) ...[
                              const SizedBox(height: DS.spacing10),
                              Text(
                                context.l10n.seedLibraryDetailCurrentStatus(
                                  state.subscription!.isEnabled
                                      ? context.l10n
                                          .seedLibraryDetailSubscriptionStatusEnabled
                                      : context.l10n
                                          .seedLibraryDetailSubscriptionStatusDisabled,
                                  state.subscription!.priority,
                                ),
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(
                                      color: DS.textSecondary,
                                    ),
                              ),
                            ],
                          ],
                        ),
                      ),

                      if (state.activeSubscriptions.isNotEmpty) ...[
                        const SizedBox(height: DS.spacing12),
                        GraphiteCardSurface(
                          surfaceRole: SparkleSurfaceRole.panel,
                          padding: const EdgeInsets.all(DS.spacing16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                context
                                    .l10n.seedLibraryDetailActiveSubscriptions,
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              const SizedBox(height: DS.spacing8),
                              Text(
                                context.l10n
                                    .seedLibraryDetailActiveSubscriptionsDesc,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(
                                      color: DS.textSecondary,
                                    ),
                              ),
                              const SizedBox(height: DS.spacing10),
                              Wrap(
                                spacing: DS.spacing8,
                                runSpacing: DS.spacing8,
                                children: state.activeSubscriptions
                                    .take(6)
                                    .map((sub) {
                                  final isCurrent =
                                      sub.libraryId == widget.libraryId;
                                  return Chip(
                                    label: Text(
                                      '${sub.library?.name ?? context.l10n.seedLibraryDetailFallbackName} · P${sub.priority}',
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    avatar: Icon(
                                      isCurrent
                                          ? Icons.auto_awesome
                                          : Icons.layers_outlined,
                                      size: DS.iconSizeXs,
                                    ),
                                    backgroundColor: isCurrent
                                        ? DS.primaryBase.withValues(alpha: 0.12)
                                        : null,
                                  );
                                }).toList(),
                              ),
                            ],
                          ),
                        ),
                      ],

                      // Tags
                      if (library.tags != null && library.tags!.isNotEmpty) ...[
                        const SizedBox(height: DS.spacing12),
                        Wrap(
                          spacing: DS.spacing8,
                          children: library.tags!
                              .map(
                                (tag) => Chip(
                                  label: Text(tag),
                                  labelPadding: EdgeInsets.zero,
                                ),
                              )
                              .toList(),
                        ),
                      ],
                    ],
                  ),
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
                child: SparkleStaggerItem(
                  index: 1,
                  child: Row(
                    children: [
                      Text(
                        context.l10n.seedLibraryContentItems,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const Spacer(),
                      SparkleButton.ghost(
                        onPressed: () {
                          unawaited(
                            SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.selection,
                            ),
                          );
                          unawaited(_showItemFilterSheet(context));
                        },
                        icon:
                            const Icon(Icons.filter_list, size: DS.iconSizeXs),
                        label: context.l10n.seedLibraryFilter,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Items list
          if (filteredItems.isEmpty)
            SliverFillRemaining(
              child: state.isLoadingItems
                  ? const Center(child: CircularProgressIndicator())
                  : Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.inbox_outlined,
                            size: DS.spacing64,
                            color: DS.textTertiary,
                          ),
                          const SizedBox(height: DS.spacing16),
                          Text(
                            state.items.isEmpty
                                ? context.l10n.seedLibraryNoContent
                                : context
                                    .l10n.seedLibraryDetailNoResultsUnderFilter,
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
                    if (index >= filteredItems.length) {
                      // Load more indicator
                      unawaited(
                        ref
                            .read(
                              seedLibraryDetailProvider(widget.libraryId)
                                  .notifier,
                            )
                            .loadItems(),
                      );
                      return const SizedBox(
                        height: 100,
                        child: Center(child: CircularProgressIndicator()),
                      );
                    }

                    final item = filteredItems[index];
                    return SparkleStaggerItem(
                      index: index,
                      child: SeedItemCard(
                        item: item,
                        onTap: () => _showItemDetailSheet(context, item),
                        onShare: () {
                          unawaited(
                            SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.sheetOpen,
                            ),
                          );
                          showShareResourceSheet(
                            context,
                            resourceType: 'seed_item',
                            resourceId: item.id,
                            title: item.title ?? item.itemTypeLabel(context.l10n),
                            subtitle: item.content,
                          );
                        },
                      ),
                    );
                  },
                  childCount:
                      filteredItems.length + (state.hasMoreItems ? 1 : 0),
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
                  fontWeight: DS.fontWeightBold,
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

  Widget _buildQualityBadge(
    BuildContext context, {
    required String label,
    required double value,
    required IconData icon,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing10,
        ),
        decoration: BoxDecoration(
          color: DS.warningAccent.withValues(alpha: 0.22),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: DS.warning.withValues(alpha: 0.28)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 18, color: DS.warning),
            const SizedBox(width: DS.spacing8),
            Text(
              '$label ${value.toStringAsFixed(1)}',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: DS.fontWeightSemibold,
                  ),
            ),
          ],
        ),
      );

  String _buildUsageExplanation(
    SeedLibrary library,
    SeedLibraryDetailState state,
  ) {
    final categoryHint = switch (library.category) {
      LibraryCategory.fewShot => context.l10n.seedLibraryDetailUsageFewShot,
      LibraryCategory.teachingContent =>
        context.l10n.seedLibraryDetailUsageTeachingContent,
      LibraryCategory.replyTemplate =>
        context.l10n.seedLibraryDetailUsageReplyTemplate,
      LibraryCategory.custom => context.l10n.seedLibraryDetailUsageCustom,
    };
    if (state.subscription?.isEnabled ?? false) {
      return context.l10n.seedLibraryDetailUsageAppliedEnabled(categoryHint);
    }
    if (state.isSubscribed) {
      return context.l10n
          .seedLibraryDetailUsageSubscribedNotEnabled(categoryHint);
    }
    return context.l10n.seedLibraryDetailUsageNotApplied(categoryHint);
  }

  Future<void> _showItemFilterSheet(BuildContext context) async {
    await showSensoryModalBottomSheet<void>(
      context: context,
      builder: (sheetContext) => StatefulBuilder(
        builder: (sheetContext, setSheetState) => Padding(
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.seedLibraryDetailFilterTitle,
                style: Theme.of(sheetContext).textTheme.titleLarge,
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                context.l10n.seedLibraryDetailFilterDesc,
                style: Theme.of(sheetContext).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
              const SizedBox(height: DS.spacing16),
              Text(context.l10n.seedLibraryDetailFilterContentType,
                  style: Theme.of(sheetContext).textTheme.titleSmall),
              const SizedBox(height: DS.spacing8),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  FilterChip(
                    label: Text(context.l10n.seedLibraryDetailFilterAll),
                    selected: _selectedItemType == null,
                    onSelected: (_) {
                      setSheetState(() {
                        _selectedItemType = null;
                      });
                    },
                  ),
                  ...ItemType.values.map(
                    (itemType) => FilterChip(
                      label: Text(itemType.label(context.l10n)),
                      selected: _selectedItemType == itemType,
                      onSelected: (_) {
                        setSheetState(() {
                          _selectedItemType =
                              _selectedItemType == itemType ? null : itemType;
                        });
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing16),
              Text(context.l10n.seedLibraryDetailFilterDifficulty,
                  style: Theme.of(sheetContext).textTheme.titleSmall),
              const SizedBox(height: DS.spacing8),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  FilterChip(
                    label: Text(context.l10n.seedLibraryDetailFilterAll),
                    selected: _selectedDifficulty == null,
                    onSelected: (_) {
                      setSheetState(() {
                        _selectedDifficulty = null;
                      });
                    },
                  ),
                  ...DifficultyLevel.values.map(
                    (difficulty) => FilterChip(
                      label: Text(difficulty.label(context.l10n)),
                      selected: _selectedDifficulty == difficulty,
                      onSelected: (_) {
                        setSheetState(() {
                          _selectedDifficulty =
                              _selectedDifficulty == difficulty
                                  ? null
                                  : difficulty;
                        });
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing16),
              SwitchListTile.adaptive(
                value: _showInactiveItems,
                contentPadding: EdgeInsets.zero,
                title: Text(context.l10n.seedLibraryDetailFilterShowInactive),
                subtitle:
                    Text(context.l10n.seedLibraryDetailFilterShowInactiveDesc),
                onChanged: (value) {
                  setSheetState(() {
                    _showInactiveItems = value;
                  });
                },
              ),
              const SizedBox(height: DS.spacing16),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton.ghost(
                      onPressed: () {
                        setState(() {
                          _selectedItemType = null;
                          _selectedDifficulty = null;
                          _showInactiveItems = false;
                        });
                        Navigator.of(sheetContext).pop();
                      },
                      label: context.l10n.seedLibraryDetailFilterReset,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: SparkleButton(
                      onPressed: () {
                        setState(() {});
                        Navigator.of(sheetContext).pop();
                      },
                      label: context.l10n.seedLibraryDetailFilterDone,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _showRatingSheet(
    BuildContext context,
    SeedLibraryDetailState state,
  ) async {
    final commentController = TextEditingController();
    var score =
        state.library?.currentUserRating ?? state.library?.userRatingAvg ?? 8;
    await showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          left: DS.spacing16,
          right: DS.spacing16,
          top: DS.spacing16,
          bottom: MediaQuery.of(context).viewInsets.bottom + DS.spacing16,
        ),
        child: StatefulBuilder(
          builder: (context, setModalState) => Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(context.l10n.seedLibraryDetailRatingTitle,
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: DS.spacing8),
              Text(
                context.l10n.seedLibraryDetailRatingDescription,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
              const SizedBox(height: DS.spacing12),
              Text(context.l10n
                  .seedLibraryDetailCurrentRating(score.toStringAsFixed(1))),
              Slider(
                value: score,
                max: 10,
                divisions: 20,
                label: score.toStringAsFixed(1),
                onChanged: (value) => setModalState(() => score = value),
              ),
              TextField(
                controller: commentController,
                minLines: 2,
                maxLines: 4,
                decoration: InputDecoration(
                  labelText: context.l10n.seedLibraryDetailRatingCommentLabel,
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton.ghost(
                      onPressed: () => Navigator.pop(context),
                      label: context.l10n.commonCancel,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: SparkleButton(
                      onPressed: () async {
                        try {
                          await ref
                              .read(seedLibraryDetailProvider(widget.libraryId)
                                  .notifier)
                              .submitRating(
                                score: score,
                                comment: commentController.text.trim().isEmpty
                                    ? null
                                    : commentController.text.trim(),
                              );
                          if (!context.mounted) return;
                          Navigator.pop(context);
                          AppFeedback.success(context,
                              context.l10n.seedLibraryDetailRatingSubmitted);
                        } catch (e) {
                          if (!context.mounted) return;
                          AppFeedback.error(
                              context,
                              context.l10n
                                  .seedLibraryDetailRatingFailed(e.toString()));
                        }
                      },
                      label: context.l10n.seedLibraryDetailSubmitRating,
                      expand: true,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _showItemDetailSheet(BuildContext context, SeedItem item) async {
    await showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing16),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title ?? item.itemTypeLabel(context.l10n),
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: DS.spacing8),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    Chip(label: Text(item.itemTypeLabel(context.l10n))),
                    if (item.subject != null) Chip(label: Text(item.subject!)),
                    if (item.difficultyLevel != null)
                      Chip(label: Text(item.difficultyLevelLabel(context.l10n)!)),
                    ...?item.tags?.map((tag) => Chip(label: Text(tag))),
                  ],
                ),
                if (item.content != null &&
                    item.content!.trim().isNotEmpty) ...[
                  const SizedBox(height: DS.spacing16),
                  Text(context.l10n.seedLibraryDetailContentBody,
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: DS.spacing8),
                  GraphiteCardSurface(
                    surfaceRole: SparkleSurfaceRole.panel,
                    padding: const EdgeInsets.all(DS.spacing12),
                    child: SparkleMarkdown(
                      content: item.content!,
                      textColor: DS.textPrimary,
                      codeBackgroundColor: DS.surfaceSecondary,
                      linkColor: DS.info,
                      selectable: true,
                      contentRole: SparkleMarkdownRole.seedBody,
                    ),
                  ),
                ],
                if (item.contentData != null &&
                    item.contentData!.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing16),
                  Text(context.l10n.seedLibraryDetailStructuredContent,
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: DS.spacing8),
                  GraphiteCardSurface(
                    surfaceRole: SparkleSurfaceRole.panel,
                    padding: const EdgeInsets.all(DS.spacing12),
                    child: SelectableText(
                      const JsonEncoder.withIndent('  ')
                          .convert(item.contentData),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            fontFamily: 'monospace',
                            fontFamilyFallback: sparkleFontFallback,
                          ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _showEditDialog(BuildContext context, SeedLibrary library) {
    final nameController = TextEditingController(text: library.name);
    final descController =
        TextEditingController(text: library.description ?? '');
    final formKey = GlobalKey<FormState>();

    unawaited(
      showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(context.l10n.seedLibraryDetailEditLibrary),
          content: Form(
            key: formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: nameController,
                  decoration: InputDecoration(
                      labelText: context.l10n.seedLibraryDetailEditName),
                  validator: (v) => (v == null || v.trim().isEmpty)
                      ? context.l10n.seedLibraryDetailEditNameEmpty
                      : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: descController,
                  decoration: InputDecoration(
                      labelText: context
                          .l10n.seedLibraryDetailEditDescriptionOptional),
                  maxLines: 3,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text(context.l10n.seedLibraryDetailEditCancel),
            ),
            TextButton(
              onPressed: () async {
                if (!formKey.currentState!.validate()) return;
                Navigator.pop(ctx);
                try {
                  await ref
                      .read(
                          seedLibraryDetailProvider(widget.libraryId).notifier)
                      .updateLibrary(
                        name: nameController.text.trim(),
                        description: descController.text.trim().isEmpty
                            ? null
                            : descController.text.trim(),
                      );
                  if (!context.mounted) return;
                  AppFeedback.success(
                      context, context.l10n.seedLibraryDetailLibraryUpdated);
                } catch (e) {
                  if (!context.mounted) return;
                  AppFeedback.error(
                    context,
                    _friendlyActionError(e),
                  );
                }
              },
              child: Text(context.l10n.seedLibraryDetailEditSave),
            ),
          ],
        ),
      ),
    );
  }

  void _showDeleteDialog(
    BuildContext context,
  ) {
    unawaited(
      showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(context.l10n.seedLibraryDeleteTitle),
          content: Text(context.l10n.seedLibraryDeleteConfirm),
          actions: [
            SparkleButton.ghost(
              onPressed: () => Navigator.pop(context),
              label: context.l10n.commonCancel,
            ),
            SparkleButton.destructive(
              onPressed: () async {
                try {
                  await ref
                      .read(
                          seedLibraryDetailProvider(widget.libraryId).notifier)
                      .deleteLibrary();
                  if (context.mounted) {
                    Navigator.pop(context);
                    Navigator.pop(context);
                  }
                } catch (e) {
                  if (context.mounted) {
                    AppFeedback.error(
                      context,
                      context.l10n.seedLibraryDeleteFailed(e.toString()),
                    );
                  }
                }
              },
              label: context.l10n.commonDelete,
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showAddItemSheet(BuildContext context) async {
    final formKey = GlobalKey<FormState>();
    final titleController = TextEditingController();
    final contentController = TextEditingController();
    final subjectController = TextEditingController();
    final tagsController = TextEditingController();
    var itemType = ItemType.example;
    DifficultyLevel? difficultyLevel = DifficultyLevel.beginner;

    await showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          left: DS.spacing16,
          right: DS.spacing16,
          top: DS.spacing16,
          bottom: MediaQuery.of(context).viewInsets.bottom + DS.spacing16,
        ),
        child: StatefulBuilder(
          builder: (context, setModalState) => Form(
            key: formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.l10n.seedLibraryDetailAddItem,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: DS.spacing16),
                  DropdownButtonFormField<ItemType>(
                    initialValue: itemType,
                    decoration: InputDecoration(
                      labelText: context.l10n.seedLibraryDetailAddItemType,
                      border: OutlineInputBorder(),
                    ),
                    items: ItemType.values
                        .map(
                          (type) => DropdownMenuItem(
                            value: type,
                            child: Text(type.label(context.l10n)),
                          ),
                        )
                        .toList(),
                    onChanged: (value) {
                      if (value != null) {
                        setModalState(() => itemType = value);
                      }
                    },
                  ),
                  const SizedBox(height: DS.spacing12),
                  TextFormField(
                    controller: titleController,
                    decoration: InputDecoration(
                      labelText: context.l10n.seedLibraryDetailAddItemTitle,
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  TextFormField(
                    controller: contentController,
                    decoration: InputDecoration(
                      labelText: context.l10n.seedLibraryDetailAddItemContent,
                      border: OutlineInputBorder(),
                    ),
                    minLines: 3,
                    maxLines: 6,
                  ),
                  const SizedBox(height: DS.spacing12),
                  TextFormField(
                    controller: subjectController,
                    decoration: InputDecoration(
                      labelText: context.l10n.seedLibraryDetailAddItemSubject,
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  DropdownButtonFormField<DifficultyLevel?>(
                    initialValue: difficultyLevel,
                    decoration: InputDecoration(
                      labelText:
                          context.l10n.seedLibraryDetailAddItemDifficulty,
                      border: OutlineInputBorder(),
                    ),
                    items: [
                      DropdownMenuItem<DifficultyLevel?>(
                        child: Text(context.l10n.seedLibraryDetailAddItemUnset),
                      ),
                      ...DifficultyLevel.values.map(
                        (level) => DropdownMenuItem(
                          value: level,
                          child: Text(level.label(context.l10n)),
                        ),
                      ),
                    ],
                    onChanged: (value) {
                      setModalState(() => difficultyLevel = value);
                    },
                  ),
                  const SizedBox(height: DS.spacing12),
                  TextFormField(
                    controller: tagsController,
                    decoration: InputDecoration(
                      labelText: context.l10n.seedLibraryDetailAddItemTags,
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  SizedBox(
                    width: double.infinity,
                    child: SparkleButton(
                      label: context.l10n.seedLibraryDetailAddItemSave,
                      onPressed: () async {
                        try {
                          final tags = tagsController.text
                              .split(',')
                              .map((item) => item.trim())
                              .where((item) => item.isNotEmpty)
                              .toList();
                          await ref
                              .read(seedLibraryDetailProvider(widget.libraryId)
                                  .notifier)
                              .addItem(
                                itemType: itemType,
                                title: titleController.text.trim().isEmpty
                                    ? null
                                    : titleController.text.trim(),
                                content: contentController.text.trim().isEmpty
                                    ? null
                                    : contentController.text.trim(),
                                subject: subjectController.text.trim().isEmpty
                                    ? null
                                    : subjectController.text.trim(),
                                difficultyLevel: difficultyLevel,
                                tags: tags.isEmpty ? null : tags,
                              );
                          if (!context.mounted) return;
                          Navigator.pop(context);
                          AppFeedback.success(context,
                              context.l10n.seedLibraryDetailAddItemSuccess);
                        } catch (e) {
                          if (!context.mounted) return;
                          AppFeedback.error(
                              context,
                              context.l10n.seedLibraryDetailAddItemFailed(
                                  e.toString()));
                        }
                      },
                      expand: true,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _importJsonItems() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['json'],
        withData: true,
      );
      if (result == null || result.files.isEmpty) {
        return;
      }
      if (!mounted) {
        return;
      }
      final file = result.files.single;
      final bytes = file.bytes;
      if (bytes == null) {
        AppFeedback.error(
            context, context.l10n.seedLibraryDetailImportCannotRead);
        return;
      }
      final decoded = jsonDecode(utf8.decode(bytes));
      final dynamic rawItems =
          decoded is Map<String, dynamic> ? decoded['items'] : decoded;
      if (!mounted) {
        return;
      }
      if (rawItems is! List) {
        AppFeedback.error(
            context, context.l10n.seedLibraryDetailImportInvalidJson);
        return;
      }

      final items = rawItems
          .whereType<Map<String, dynamic>>()
          .map(Map<String, dynamic>.from)
          .toList();
      if (items.isEmpty) {
        AppFeedback.info(context, context.l10n.seedLibraryDetailImportNoItems);
        return;
      }

      final resultData = await ref
          .read(seedLibraryDetailProvider(widget.libraryId).notifier)
          .importItems(items);
      if (!mounted) return;
      final importedCount = (resultData['imported_count'] as int?) ?? 0;
      final failedCount = (resultData['failed_count'] as int?) ?? 0;
      AppFeedback.success(
        context,
        context.l10n.seedLibraryDetailImportResult(importedCount, failedCount),
      );
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(
          context, context.l10n.seedLibraryDetailImportFailed(e.toString()));
    }
  }
}
