import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/galaxy/data/repositories/galaxy_repository.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Quick share category
enum QuickShareCategory {
  achievements,
  plans,
  recentTasks,
  knowledgeNodes,
}

/// Item for quick share picker
class QuickShareItem {
  QuickShareItem({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.contentType,
    required this.icon,
    required this.iconColor,
    this.metadata,
  });

  final String id;
  final String title;
  final String subtitle;
  final ShareableContentType contentType;
  final IconData icon;
  final Color iconColor;
  final Map<String, dynamic>? metadata;

  UniversalSharePayload toPayload() => UniversalSharePayload(
        contentType: contentType,
        resourceId: id,
        title: title,
        subtitle: subtitle,
        metadata: metadata,
      );
}

/// Quick share picker bottom sheet for sharing within chat
class QuickSharePickerSheet extends ConsumerStatefulWidget {
  const QuickSharePickerSheet({
    required this.onShare,
    this.initialCategory,
    super.key,
  });

  /// Callback when an item is selected for sharing
  final void Function(UniversalSharePayload payload) onShare;

  /// Initial category to display
  final QuickShareCategory? initialCategory;

  @override
  ConsumerState<QuickSharePickerSheet> createState() =>
      _QuickSharePickerSheetState();
}

class _QuickSharePickerSheetState extends ConsumerState<QuickSharePickerSheet>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  late QuickShareCategory _selectedCategory;

  List<QuickShareItem> _items = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _selectedCategory =
        widget.initialCategory ?? QuickShareCategory.achievements;
    _tabController = TabController(
      length: 4,
      vsync: this,
      initialIndex: _selectedCategory.index,
    );
    _tabController.addListener(_onTabChanged);
    unawaited(_loadItems());
  }

  @override
  void dispose() {
    super.dispose();
    _tabController
      ..removeListener(_onTabChanged)
      ..dispose();
  }

  void _onTabChanged() {
    if (_tabController.indexIsChanging) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    setState(() {
      _selectedCategory = QuickShareCategory.values[_tabController.index];
      _isLoading = true;
    });
    unawaited(_loadItems());
  }

  Future<void> _loadItems() async {
    var items = <QuickShareItem>[];

    try {
      switch (_selectedCategory) {
        case QuickShareCategory.achievements:
          items = await _loadAchievements();
        case QuickShareCategory.plans:
          items = await _loadPlans();
        case QuickShareCategory.recentTasks:
          items = await _loadRecentTasks();
        case QuickShareCategory.knowledgeNodes:
          items = await _loadKnowledgeNodes();
      }
    } catch (e) {
      debugPrint('Error loading $_selectedCategory: $e');
    }

    if (mounted) {
      setState(() {
        _items = items;
        _isLoading = false;
      });
    }
  }

  Future<List<QuickShareItem>> _loadAchievements() async {
    final state = ref.read(achievementProvider);
    final response = state.achievements.isNotEmpty
        ? null
        : await ref.read(achievementRepositoryProvider).getAchievements();

    final achievements = response?.achievements ?? state.achievements;
    final unlockedAchievements =
        achievements.where((a) => a.isUnlocked).toList()
          ..sort(
            (a, b) => (b.userProgress?.unlockedAt ?? DateTime(1970))
                .compareTo(a.userProgress?.unlockedAt ?? DateTime(1970)),
          );

    return unlockedAchievements.take(10).map((achievement) {
      final rarity = achievement.achievement.rarity;
      final rarityColor = _getRarityColor(rarity);
      return QuickShareItem(
        id: achievement.achievement.id,
        title: achievement.achievement.name,
        subtitle: achievement.achievement.description ?? '',
        contentType: ShareableContentType.achievement,
        icon: _getRarityIcon(rarity),
        iconColor: rarityColor,
        metadata: {
          'rarity': rarity.name,
          'type': achievement.achievement.type.name,
        },
      );
    }).toList();
  }

  Color _getRarityColor(AchievementRarity rarity) => switch (rarity) {
        AchievementRarity.legendary => DS.warning,
        AchievementRarity.epic => DS.prismPurple,
        AchievementRarity.rare => DS.info,
        AchievementRarity.common => DS.neutral500,
      };

  IconData _getRarityIcon(AchievementRarity rarity) => switch (rarity) {
        AchievementRarity.legendary => Icons.emoji_events,
        AchievementRarity.epic => Icons.military_tech,
        AchievementRarity.rare => Icons.star,
        AchievementRarity.common => Icons.check_circle,
      };

  Future<List<QuickShareItem>> _loadPlans() async {
    final state = ref.read(planListProvider);
    final loadedPlans = state.plans.isNotEmpty
        ? state.plans
        : await ref.read(planRepositoryProvider).getPlans();
    final activePlans = loadedPlans.where((plan) => plan.isActive).toList()
      ..sort((a, b) => b.progress.compareTo(a.progress));

    return activePlans
        .take(10)
        .map(
          (plan) => QuickShareItem(
            id: plan.id,
            title: plan.name,
            subtitle: context.l10n.communityProgressPercent((plan.progress * 100).toStringAsFixed(0)),
            contentType: ShareableContentType.planProgress,
            icon: Icons.flag,
            iconColor: DS.info,
            metadata: {
              'progress': plan.progress,
              'subject': plan.subject,
            },
          ),
        )
        .toList();
  }

  Future<List<QuickShareItem>> _loadRecentTasks() async {
    final state = ref.read(taskListProvider);
    final loadedTasks = state.tasks.isNotEmpty
        ? state.tasks
        : (await ref.read(taskRepositoryProvider).getTasks(pageSize: 30)).items;
    final tasks = loadedTasks
        .where((t) =>
            t.status == TaskStatus.completed ||
            t.status == TaskStatus.inProgress ||
            t.status == TaskStatus.stuck ||
            t.status == TaskStatus.pending)
        .toList()
      ..sort(
        (a, b) => (b.completedAt ?? b.updatedAt)
            .compareTo(a.completedAt ?? a.updatedAt),
      );

    return tasks
        .take(10)
        .map(
          (task) => QuickShareItem(
            id: task.id,
            title: task.title,
            subtitle:
                context.l10n.communityTaskStatusMinutes(_taskStatusLabel(task.status), task.actualMinutes ?? task.estimatedMinutes),
            contentType: ShareableContentType.taskCompletion,
            icon: Icons.task_alt,
            iconColor: DS.success,
            metadata: {
              'duration': task.actualMinutes ?? task.estimatedMinutes,
              'type': task.type.name,
            },
          ),
        )
        .toList();
  }

  Future<List<QuickShareItem>> _loadKnowledgeNodes() async {
    final state = ref.read(galaxyProvider);
    final loadedNodes = state.nodes.isNotEmpty
        ? state.nodes
        : (await ref.read(galaxyRepositoryProvider).getGraph()).nodes;
    final nodesWithMastery = loadedNodes
        .where((n) => n.masteryScore > 0)
        .toList()
      ..sort((a, b) => b.masteryScore.compareTo(a.masteryScore));

    return nodesWithMastery.take(10).map((node) {
      final sectorStyle = SectorConfig.getStyle(node.sector);
      return QuickShareItem(
        id: node.id,
        title: node.name,
        subtitle: context.l10n.communityMasteryScore(node.masteryScore),
        contentType: ShareableContentType.knowledgeNode,
        icon: Icons.school,
        iconColor: sectorStyle.primaryColor,
        metadata: {
          'mastery': node.masteryScore / 100,
          'sector': node.sector,
        },
      );
    }).toList();
  }

  String _taskStatusLabel(TaskStatus status) => switch (status) {
        TaskStatus.completed => context.l10n.communityTaskCompleted,
        TaskStatus.inProgress => context.l10n.communityTaskInProgress,
        TaskStatus.stuck => context.l10n.communityTaskStuck,
        TaskStatus.pending => context.l10n.communityTaskPending,
        TaskStatus.paused => context.l10n.communityTaskPaused,
        TaskStatus.restore => context.l10n.taskStatusRestore,
        TaskStatus.abandoned => context.l10n.communityTaskAbandoned,
      };

  void _onItemTap(QuickShareItem item) {
    final payload = item.toPayload();
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    Navigator.pop(context);
    widget.onShare(payload);
  }

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(context).scaffoldBackgroundColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: SafeArea(
          top: false,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Handle bar
              Container(
                width: 36,
                height: 4,
                margin: const EdgeInsets.only(top: DS.md),
                decoration: BoxDecoration(
                  color: DS.neutral300,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),

              // Title
              Padding(
                padding: const EdgeInsets.all(DS.lg),
                child: Text(
                  context.l10n.communityQuickShare,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),

              // Category tabs
              TabBar(
                controller: _tabController,
                labelColor: DS.brandPrimary,
                indicatorColor: DS.brandPrimary,
                tabs: [
                  Tab(icon: Icon(Icons.emoji_events), text: context.l10n.communityTabAchievements),
                  Tab(icon: Icon(Icons.flag), text: context.l10n.communityTabPlans),
                  Tab(icon: Icon(Icons.task_alt), text: context.l10n.communityTabTasks),
                  Tab(icon: Icon(Icons.school), text: context.l10n.communityTabKnowledge),
                ],
              ),

              // Content
              SizedBox(
                height: 300,
                child: TabBarView(
                  controller: _tabController,
                  children: List.generate(
                    4,
                    (_) => _buildItemList(),
                  ),
                ),
              ),

              const SizedBox(height: DS.md),
            ],
          ),
        ),
      );

  Widget _buildItemList() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_items.isEmpty) {
      return _buildEmptyState();
    }

    return ListView.separated(
      padding: const EdgeInsets.all(DS.md),
      itemCount: _items.length,
      separatorBuilder: (_, __) => const SizedBox(height: DS.sm),
      itemBuilder: (context, index) {
        final item = _items[index];
        return SparkleStaggerItem(
          index: index,
          child: _buildItemTile(item),
        );
      },
    );
  }

  Widget _buildEmptyState() => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _getEmptyIcon(),
              size: 48,
              color: DS.neutral300,
            ),
            const SizedBox(height: DS.md),
            Text(
              _getEmptyMessage(),
              style: TextStyle(
                color: DS.textTertiary,
                fontSize: DS.fontSizeSm,
              ),
            ),
          ],
        ),
      );

  IconData _getEmptyIcon() => switch (_selectedCategory) {
        QuickShareCategory.achievements => Icons.emoji_events_outlined,
        QuickShareCategory.plans => Icons.flag_outlined,
        QuickShareCategory.recentTasks => Icons.task_alt_outlined,
        QuickShareCategory.knowledgeNodes => Icons.school_outlined,
      };

  String _getEmptyMessage() => switch (_selectedCategory) {
        QuickShareCategory.achievements => context.l10n.communityNoAchievementsYet,
        QuickShareCategory.plans => context.l10n.communityNoPlansYet,
        QuickShareCategory.recentTasks => context.l10n.communityNoTasksYet,
        QuickShareCategory.knowledgeNodes => context.l10n.communityNoKnowledgeYet,
      };

  Widget _buildItemTile(QuickShareItem item) => ListTile(
        onTap: () => _onItemTap(item),
        leading: Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: item.iconColor.withValues(alpha: 0.15),
            borderRadius: DS.borderRadius8,
          ),
          child: Icon(
            item.icon,
            color: item.iconColor,
          ),
        ),
        title: Text(
          item.title,
          style: TextStyle(
            fontWeight: DS.fontWeightMedium,
            color: DS.textPrimary,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        subtitle: Text(
          item.subtitle,
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            color: DS.textSecondary,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: Icon(
          Icons.share,
          size: 20,
          color: DS.neutral400,
        ),
        shape: const RoundedRectangleBorder(
          borderRadius: DS.borderRadius12,
        ),
        tileColor: DS.surfaceSecondary,
      );
}

/// Convenience function to show the quick share picker
Future<void> showQuickSharePicker(
  BuildContext context, {
  required void Function(UniversalSharePayload payload) onShare,
  QuickShareCategory? initialCategory,
}) async {
  await showSensoryModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
    builder: (context) => QuickSharePickerSheet(
      onShare: onShare,
      initialCategory: initialCategory,
    ),
  );
}
