import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/universal_share_service.dart';

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
    _selectedCategory = widget.initialCategory ?? QuickShareCategory.achievements;
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
    _tabController.removeListener(_onTabChanged);
    _tabController.dispose();
    super.dispose();
  }

  void _onTabChanged() {
    if (_tabController.indexIsChanging) return;
    setState(() {
      _selectedCategory = QuickShareCategory.values[_tabController.index];
      _isLoading = true;
    });
    unawaited(_loadItems());
  }

  Future<void> _loadItems() async {
    List<QuickShareItem> items = [];

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
    // TODO: Integrate with achievement provider
    // Return mock data for now
    return [
      QuickShareItem(
        id: 'ach_1',
        title: '星空探索者',
        subtitle: '解锁了第一个成就',
        contentType: ShareableContentType.achievement,
        icon: Icons.emoji_events,
        iconColor: DS.warning,
        metadata: {
          'rarity': 'legendary',
          'type': 'milestone',
        },
      ),
      QuickShareItem(
        id: 'ach_2',
        title: '连续学习7天',
        subtitle: '学习连胜',
        contentType: ShareableContentType.achievement,
        icon: Icons.local_fire_department,
        iconColor: DS.error,
        metadata: {
          'rarity': 'rare',
          'type': 'streak',
        },
      ),
    ];
  }

  Future<List<QuickShareItem>> _loadPlans() async {
    // TODO: Integrate with plan provider
    return [
      QuickShareItem(
        id: 'plan_1',
        title: 'Python学习计划',
        subtitle: '进度: 75%',
        contentType: ShareableContentType.planProgress,
        icon: Icons.flag,
        iconColor: DS.info,
        metadata: {
          'progress': 0.75,
          'completed_tasks': 12,
          'total_tasks': 16,
        },
      ),
      QuickShareItem(
        id: 'plan_2',
        title: '算法练习',
        subtitle: '进度: 50%',
        contentType: ShareableContentType.planProgress,
        icon: Icons.flag,
        iconColor: DS.info,
        metadata: {
          'progress': 0.5,
          'completed_tasks': 5,
          'total_tasks': 10,
        },
      ),
    ];
  }

  Future<List<QuickShareItem>> _loadRecentTasks() async {
    // TODO: Integrate with task provider
    return [
      QuickShareItem(
        id: 'task_1',
        title: '完成Flutter基础教程',
        subtitle: '已完成 · 45分钟',
        contentType: ShareableContentType.taskCompletion,
        icon: Icons.task_alt,
        iconColor: DS.success,
        metadata: {
          'duration': 45,
        },
      ),
      QuickShareItem(
        id: 'task_2',
        title: '复习数据结构',
        subtitle: '已完成 · 30分钟',
        contentType: ShareableContentType.taskCompletion,
        icon: Icons.task_alt,
        iconColor: DS.success,
        metadata: {
          'duration': 30,
        },
      ),
    ];
  }

  Future<List<QuickShareItem>> _loadKnowledgeNodes() async {
    // TODO: Integrate with Galaxy/Knowledge service
    return [
      QuickShareItem(
        id: 'node_1',
        title: '微积分基础',
        subtitle: '掌握度: 75%',
        contentType: ShareableContentType.knowledgeNode,
        icon: Icons.school,
        iconColor: DS.brandSecondary,
        metadata: {
          'mastery': 0.75,
          'category': '数学',
        },
      ),
      QuickShareItem(
        id: 'node_2',
        title: 'Python 编程',
        subtitle: '掌握度: 60%',
        contentType: ShareableContentType.knowledgeNode,
        icon: Icons.school,
        iconColor: DS.brandSecondary,
        metadata: {
          'mastery': 0.6,
          'category': '编程',
        },
      ),
    ];
  }

  void _onItemTap(QuickShareItem item) {
    final payload = item.toPayload();
    Navigator.pop(context);
    widget.onShare(payload);
  }

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
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
                '快捷分享',
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),

            // Category tabs
            TabBar(
              controller: _tabController,
              labelColor: DS.brandPrimary,
              indicatorColor: DS.brandPrimary,
              tabs: const [
                Tab(icon: Icon(Icons.emoji_events), text: '成就'),
                Tab(icon: Icon(Icons.flag), text: '计划'),
                Tab(icon: Icon(Icons.task_alt), text: '任务'),
                Tab(icon: Icon(Icons.school), text: '知识'),
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
  }

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
        return _buildItemTile(item);
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
        QuickShareCategory.achievements => '还没有解锁成就',
        QuickShareCategory.plans => '还没有学习计划',
        QuickShareCategory.recentTasks => '还没有完成的任务',
        QuickShareCategory.knowledgeNodes => '还没有学习知识节点',
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
        shape: RoundedRectangleBorder(
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
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
    builder: (context) => QuickSharePickerSheet(
      onShare: onShare,
      initialCategory: initialCategory,
    ),
  );
}
