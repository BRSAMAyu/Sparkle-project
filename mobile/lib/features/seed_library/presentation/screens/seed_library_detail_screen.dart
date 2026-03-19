import 'dart:async';
import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
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
              onPressed: () => showShareResourceSheet(
                context,
                resourceType: 'seed_library',
                resourceId: state.library!.id,
                title: state.library!.name,
                subtitle: state.library!.description,
              ),
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
              onPressed: () {
                // TODO: Implement edit
              },
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
                      .read(seedLibraryDetailProvider(widget.libraryId).notifier)
                      .toggleSubscription(),
                );
              }
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'subscribe',
                child: Text(
                  state.isSubscribed ? context.l10n.seedLibraryUnsubscribe : context.l10n.seedLibrarySubscribe,
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
                      context.l10n.seedLibraryContentItems,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const Spacer(),
                    SparkleButton.ghost(
                      onPressed: () {
                        // TODO: Show filter dialog
                      },
                      icon: const Icon(Icons.filter_list, size: DS.iconSizeXs),
                      label: context.l10n.seedLibraryFilter,
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
                            context.l10n.seedLibraryNoContent,
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
                      unawaited(
                        ref
                            .read(seedLibraryDetailProvider(widget.libraryId)
                                .notifier,)
                            .loadItems(),
                      );
                      return const SizedBox(
                        height: 100,
                        child: Center(child: CircularProgressIndicator()),
                      );
                    }

                    final item = state.items[index];
                    return SeedItemCard(
                      item: item,
                      onShare: () => showShareResourceSheet(
                        context,
                        resourceType: 'seed_item',
                        resourceId: item.id,
                        title: item.title ?? item.itemTypeDisplayName,
                        subtitle: item.content,
                      ),
                    );
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
                      .read(seedLibraryDetailProvider(widget.libraryId).notifier)
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

    await showModalBottomSheet<void>(
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
                        '添加种子内容',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: DS.spacing16),
                      DropdownButtonFormField<ItemType>(
                        initialValue: itemType,
                        decoration: const InputDecoration(
                          labelText: '内容类型',
                          border: OutlineInputBorder(),
                        ),
                        items: ItemType.values
                            .map(
                              (type) => DropdownMenuItem(
                                value: type,
                                child: Text(type.displayName),
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
                        decoration: const InputDecoration(
                          labelText: '标题',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: DS.spacing12),
                      TextFormField(
                        controller: contentController,
                        decoration: const InputDecoration(
                          labelText: '内容',
                          border: OutlineInputBorder(),
                        ),
                        minLines: 3,
                        maxLines: 6,
                      ),
                      const SizedBox(height: DS.spacing12),
                      TextFormField(
                        controller: subjectController,
                        decoration: const InputDecoration(
                          labelText: '主题/学科',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: DS.spacing12),
                      DropdownButtonFormField<DifficultyLevel?>(
                        initialValue: difficultyLevel,
                        decoration: const InputDecoration(
                          labelText: '难度',
                          border: OutlineInputBorder(),
                        ),
                        items: [
                          const DropdownMenuItem<DifficultyLevel?>(
                            child: Text('未设置'),
                          ),
                          ...DifficultyLevel.values.map(
                            (level) => DropdownMenuItem(
                              value: level,
                              child: Text(level.displayName),
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
                        decoration: const InputDecoration(
                          labelText: '标签（逗号分隔）',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: DS.spacing16),
                      SizedBox(
                        width: double.infinity,
                        child: SparkleButton(
                          label: '保存内容',
                          onPressed: () async {
                            try {
                              final tags = tagsController.text
                                  .split(',')
                                  .map((item) => item.trim())
                                  .where((item) => item.isNotEmpty)
                                  .toList();
                              await ref
                                  .read(seedLibraryDetailProvider(widget.libraryId).notifier)
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
                              AppFeedback.success(context, '种子内容已添加');
                            } catch (e) {
                              if (!context.mounted) return;
                              AppFeedback.error(context, '添加失败：$e');
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
        allowedExtensions: const ['json'],
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
        AppFeedback.error(context, '无法读取文件内容');
        return;
      }
      final decoded = jsonDecode(utf8.decode(bytes));
      final dynamic rawItems =
          decoded is Map<String, dynamic> ? decoded['items'] : decoded;
      if (!mounted) {
        return;
      }
      if (rawItems is! List) {
        AppFeedback.error(context, 'JSON 格式无效，需为数组或 {items:[...]}');
        return;
      }

      final items = rawItems
          .whereType<Map<String, dynamic>>()
          .map(Map<String, dynamic>.from)
          .toList();
      if (items.isEmpty) {
        AppFeedback.info(context, '文件中没有可导入的内容项');
        return;
      }

      final resultData = await ref
          .read(seedLibraryDetailProvider(widget.libraryId).notifier)
          .importItems(items);
      if (!mounted) return;
      final importedCount = resultData['imported_count'] ?? 0;
      final failedCount = resultData['failed_count'] ?? 0;
      AppFeedback.success(
        context,
        '导入完成：成功 $importedCount 条，失败 $failedCount 条',
      );
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, '导入失败：$e');
    }
  }
}
