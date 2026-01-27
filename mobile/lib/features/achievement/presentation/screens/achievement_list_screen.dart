import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_card.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_stats_panel.dart';
import 'package:sparkle/features/achievement/presentation/widgets/streak_indicator.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// 成就列表视图模式
enum AchievementViewMode {
  grid,
  list,
}

/// 成就筛选选项
class AchievementFilterOptions {
  const AchievementFilterOptions({
    this.category,
    this.rarity,
    this.status,
  });

  final String? category;
  final AchievementRarity? rarity;
  final AchievementStatus? status;

  AchievementFilterOptions copyWith({
    String? category,
    AchievementRarity? rarity,
    AchievementStatus? status,
  }) => AchievementFilterOptions(
      category: category ?? this.category,
      rarity: rarity ?? this.rarity,
      status: status ?? this.status,
    );

  bool get hasFilters => category != null || rarity != null || status != null;
}

/// 成就状态筛选
enum AchievementStatus {
  all,
  unlocked,
  locked,
  inProgress,
}

/// 成就列表页面
class AchievementListScreen extends ConsumerStatefulWidget {
  const AchievementListScreen({super.key});

  @override
  ConsumerState<AchievementListScreen> createState() =>
      _AchievementListScreenState();
}

class _AchievementListScreenState
    extends ConsumerState<AchievementListScreen> {
  AchievementViewMode _viewMode = AchievementViewMode.grid;
  AchievementFilterOptions _filterOptions = const AchievementFilterOptions();
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(achievementProvider);

    return Scaffold(
      body: ContentConstraint(
        child: CustomScrollView(
          slivers: [
            // 顶部统计面板
            SliverToBoxAdapter(
              child: _buildHeader(context, state),
            ),

            // 筛选栏
            SliverToBoxAdapter(
              child: _buildFilterBar(context),
            ),

            // 分类标签
            SliverToBoxAdapter(
              child: _buildCategoryTabs(context, state),
            ),

            // 内容区域
            if (state.isLoading)
              const SliverFillRemaining(
                child: Center(child: CircularProgressIndicator()),
              )
            else if (state.error != null)
              SliverFillRemaining(
                child: _buildErrorView(context, state.error!),
              )
            else
              _buildAchievementContent(state),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, AchievementState state) => Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            DS.surfacePrimary,
            DS.surfaceSecondary,
          ],
        ),
      ),
      child: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // 标题和操作栏
            Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.arrow_back),
                  onPressed: () => Navigator.of(context).pop(),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    '成就',
                    style: TextStyle(
                      fontSize: DS.fontSizeXl,
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ),
                  ),
                ),
                _buildViewToggle(),
              ],
            ),
            const SizedBox(height: DS.spacing16),

            // 连胜指示器
            DashboardStreakIndicator(
              onTap: () => _showStreakDetails(context),
            ),
            const SizedBox(height: DS.spacing16),

            // 统计面板
            AchievementStatsPanel(stats: state.stats),
          ],
        ),
      ),
    );

  Widget _buildViewToggle() => DecoratedBox(
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildViewModeButton(
            icon: Icons.grid_view,
            isActive: _viewMode == AchievementViewMode.grid,
            onTap: () => setState(() => _viewMode = AchievementViewMode.grid),
          ),
          _buildViewModeButton(
            icon: Icons.view_list,
            isActive: _viewMode == AchievementViewMode.list,
            onTap: () => setState(() => _viewMode = AchievementViewMode.list),
          ),
        ],
      ),
    );

  Widget _buildViewModeButton({
    required IconData icon,
    required bool isActive,
    required VoidCallback onTap,
  }) => GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing8),
        decoration: BoxDecoration(
          color: isActive ? DS.brandPrimary : Colors.transparent,
          borderRadius: DS.borderRadius8,
        ),
        child: Icon(
          icon,
          size: DS.iconSizeSm,
          color: isActive ? Colors.white : DS.textSecondary,
        ),
      ),
    );

  Widget _buildFilterBar(BuildContext context) => Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing12,
      ),
      child: Row(
        children: [
          Expanded(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: DS.spacing12),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: DS.borderRadius12,
                border: Border.all(color: DS.border),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.search,
                    size: DS.iconSizeSm,
                    color: DS.textSecondary,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: TextField(
                      controller: _searchController,
                      decoration: InputDecoration(
                        hintText: '搜索成就',
                        hintStyle: TextStyle(
                          fontSize: DS.fontSizeSm,
                          color: DS.textSecondary,
                        ),
                        border: InputBorder.none,
                        isDense: true,
                      ),
                      style: TextStyle(
                        fontSize: DS.fontSizeSm,
                        color: DS.textPrimary,
                      ),
                      onChanged: (value) {
                        setState(() => _searchQuery = value);
                      },
                    ),
                  ),
                  if (_searchQuery.isNotEmpty)
                    GestureDetector(
                      onTap: () {
                        _searchController.clear();
                        setState(() => _searchQuery = '');
                      },
                      child: Icon(
                        Icons.clear,
                        size: DS.iconSizeSm,
                        color: DS.textSecondary,
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(width: DS.spacing12),
          _buildFilterButton(),
        ],
      ),
    );

  Widget _buildFilterButton() {
    final hasFilters = _filterOptions.hasFilters;

    return GestureDetector(
      onTap: () => _showFilterSheet(context),
      child: Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: hasFilters ? DS.brandPrimary.withValues(alpha: 0.1) : DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: hasFilters ? DS.brandPrimary : DS.border,
          ),
        ),
        child: Icon(
          Icons.filter_list,
          size: DS.iconSizeSm,
          color: hasFilters ? DS.brandPrimary : DS.textSecondary,
        ),
      ),
    );
  }

  Widget _buildCategoryTabs(BuildContext context, AchievementState state) {
    final categories = ['全部', '已解锁', '进行中', '里程碑', '连胜', '精通', '探索'];
    final selectedCategory = _filterOptions.status != null
        ? _getStatusName(_filterOptions.status!)
        : '全部';

    return Container(
      height: 48,
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: categories.length,
        itemBuilder: (context, index) {
          final category = categories[index];
          final isSelected = category == selectedCategory;

          return Padding(
            padding: EdgeInsets.only(right: index == categories.length - 1 ? 0 : DS.spacing12),
            child: _buildCategoryChip(category, isSelected),
          );
        },
      ),
    );
  }

  Widget _buildCategoryChip(String category, bool isSelected) => GestureDetector(
      onTap: () => _selectCategory(category),
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: isSelected ? DS.brandPrimary : DS.surfaceSecondary,
          borderRadius: DS.borderRadiusFull,
          border: Border.all(
            color: isSelected ? DS.brandPrimary : DS.border,
          ),
        ),
        child: Text(
          category,
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: isSelected ? DS.fontWeightSemibold : DS.fontWeightRegular,
            color: isSelected ? Colors.white : DS.textSecondary,
          ),
        ),
      ),
    );

  Widget _buildAchievementContent(AchievementState state) {
    final filteredAchievements = _filterAchievements(state.achievements);

    if (filteredAchievements.isEmpty) {
      return SliverFillRemaining(
        child: _buildEmptyView(context),
      );
    }

    if (_viewMode == AchievementViewMode.grid) {
      return SliverPadding(
        padding: const EdgeInsets.all(DS.spacing16),
        sliver: SliverGrid(
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            mainAxisSpacing: DS.spacing12,
            crossAxisSpacing: DS.spacing12,
          ),
          delegate: SliverChildBuilderDelegate(
            (context, index) {
              final achievement = filteredAchievements[index];
              return AchievementGridCard(
                achievement: achievement,
                onTap: () => _openAchievementDetail(achievement),
              );
            },
            childCount: filteredAchievements.length,
          ),
        ),
      );
    }

    return SliverPadding(
      padding: const EdgeInsets.all(DS.spacing16),
      sliver: SliverList(
        delegate: SliverChildBuilderDelegate(
          (context, index) {
            final achievement = filteredAchievements[index];
            return Padding(
              padding: EdgeInsets.only(bottom: index < filteredAchievements.length - 1 ? DS.spacing12 : 0),
              child: AchievementListCard(
                achievement: achievement,
                onTap: () => _openAchievementDetail(achievement),
              ),
            );
          },
          childCount: filteredAchievements.length,
        ),
      ),
    );
  }

  Widget _buildEmptyView(BuildContext context) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.emoji_events_outlined,
            size: 64,
            color: DS.textTertiary,
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            '没有找到匹配的成就',
            style: TextStyle(
              fontSize: DS.fontSizeBase,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '试试调整筛选条件',
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textTertiary,
            ),
          ),
        ],
      ),
    );

  Widget _buildErrorView(BuildContext context, String error) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
            color: DS.semanticError,
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            '加载失败',
            style: TextStyle(
              fontSize: DS.fontSizeBase,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            error,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textTertiary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: DS.spacing16),
          ElevatedButton(
            onPressed: () {
              ref.read(achievementProvider.notifier).loadInitialData();
            },
            child: const Text('重试'),
          ),
        ],
      ),
    );

  List<AchievementWithProgress> _filterAchievements(
    List<AchievementWithProgress> achievements,
  ) {
    var filtered = achievements;

    // 搜索过滤
    if (_searchQuery.isNotEmpty) {
      filtered = filtered
          .where((a) =>
              a.achievement.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
              (a.achievement.description?.toLowerCase().contains(_searchQuery.toLowerCase()) ?? false),)
          .toList();
    }

    // 稀有度过滤
    if (_filterOptions.rarity != null) {
      filtered = filtered
          .where((a) => a.achievement.rarity == _filterOptions.rarity)
          .toList();
    }

    // 状态过滤
    if (_filterOptions.status != null) {
      switch (_filterOptions.status!) {
        case AchievementStatus.unlocked:
          filtered = filtered.where((a) => a.isUnlocked).toList();
        case AchievementStatus.locked:
          filtered = filtered.where((a) => !a.isUnlocked).toList();
        case AchievementStatus.inProgress:
          filtered = filtered
              .where((a) => !a.isUnlocked && a.progressPercentage > 0)
              .toList();
        case AchievementStatus.all:
          break;
      }
    }

    // 分类过滤
    if (_filterOptions.category != null) {
      filtered = filtered
          .where((a) => a.achievement.category == _filterOptions.category)
          .toList();
    }

    return filtered;
  }

  void _selectCategory(String category) {
    AchievementStatus? status;

    switch (category) {
      case '已解锁':
        status = AchievementStatus.unlocked;
      case '进行中':
        status = AchievementStatus.inProgress;
      case '全部':
        status = AchievementStatus.all;
      default:
        // Map category names to achievement categories
        final categoryMap = {
          '里程碑': 'milestone',
          '连胜': 'streak',
          '精通': 'mastery',
          '探索': 'exploration',
        };
        setState(() {
          _filterOptions = _filterOptions.copyWith(
            category: categoryMap[category],
          );
        });
        return;
    }

    setState(() {
      _filterOptions = _filterOptions.copyWith(
        status: status,
      );
    });
  }

  String _getStatusName(AchievementStatus status) {
    switch (status) {
      case AchievementStatus.all:
        return '全部';
      case AchievementStatus.unlocked:
        return '已解锁';
      case AchievementStatus.locked:
        return '未解锁';
      case AchievementStatus.inProgress:
        return '进行中';
    }
  }

  void _showFilterSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _AchievementFilterSheet(
        currentOptions: _filterOptions,
        onApply: (options) {
          setState(() => _filterOptions = options);
          Navigator.pop(context);
        },
        onClear: () {
          setState(() => _filterOptions = const AchievementFilterOptions());
          Navigator.pop(context);
        },
      ),
    );
  }

  void _openAchievementDetail(AchievementWithProgress achievement) {
    context.push('/achievements/${achievement.achievement.id}');
  }

  void _showStreakDetails(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        padding: const EdgeInsets.all(DS.spacing24),
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: DS.spacing20),
              decoration: BoxDecoration(
                color: DS.neutral300,
                borderRadius: DS.borderRadiusFull,
              ),
            ),
            const Text(
              '连胜详情',
              style: TextStyle(
                fontSize: DS.fontSizeXl,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing16),
            const StreakIndicator(style: StreakIndicatorStyle.full),
          ],
        ),
      ),
    );
  }
}

/// 筛选面板
class _AchievementFilterSheet extends StatelessWidget {
  const _AchievementFilterSheet({
    required this.currentOptions,
    required this.onApply,
    required this.onClear,
  });

  final AchievementFilterOptions currentOptions;
  final void Function(AchievementFilterOptions) onApply;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(DS.spacing24),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: DS.spacing20),
              decoration: BoxDecoration(
                color: DS.neutral300,
                borderRadius: DS.borderRadiusFull,
              ),
            ),
          ),

          // 标题
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                '筛选成就',
                style: TextStyle(
                  fontSize: DS.fontSizeLg,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              TextButton(
                onPressed: onClear,
                child: const Text('清除'),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),

          // 稀有度筛选
          _buildRarityFilter(),
          const SizedBox(height: DS.spacing16),

          // 状态筛选
          _buildStatusFilter(),
          const SizedBox(height: DS.spacing24),

          // 应用按钮
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => onApply(currentOptions),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
                shape: const RoundedRectangleBorder(
                  borderRadius: DS.borderRadius12,
                ),
              ),
              child: const Text('应用筛选'),
            ),
          ),
        ],
      ),
    );

  Widget _buildRarityFilter() => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '稀有度',
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightSemibold,
            color: DS.textSecondary,
          ),
        ),
        const SizedBox(height: DS.spacing12),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: AchievementRarity.values.map((rarity) {
            final isSelected = currentOptions.rarity == rarity;
            return _buildFilterChip(
              _getRarityName(rarity),
              isSelected,
              onTap: () {
                // Update rarity filter
              },
            );
          }).toList(),
        ),
      ],
    );

  Widget _buildStatusFilter() => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '状态',
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightSemibold,
            color: DS.textSecondary,
          ),
        ),
        const SizedBox(height: DS.spacing12),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: AchievementStatus.values.map((status) {
            final isSelected = currentOptions.status == status;
            return _buildFilterChip(
              _getStatusDisplayName(status),
              isSelected,
              onTap: () {
                // Update status filter
              },
            );
          }).toList(),
        ),
      ],
    );

  Widget _buildFilterChip(String label, bool isSelected, {VoidCallback? onTap}) => GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: isSelected ? DS.brandPrimary.withValues(alpha: 0.1) : DS.surfaceSecondary,
          borderRadius: DS.borderRadiusFull,
          border: Border.all(
            color: isSelected ? DS.brandPrimary : DS.border,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            color: isSelected ? DS.brandPrimary : DS.textSecondary,
          ),
        ),
      ),
    );

  String _getRarityName(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return '普通';
      case AchievementRarity.rare:
        return '稀有';
      case AchievementRarity.epic:
        return '史诗';
      case AchievementRarity.legendary:
        return '传说';
    }
  }

  String _getStatusDisplayName(AchievementStatus status) {
    switch (status) {
      case AchievementStatus.all:
        return '全部';
      case AchievementStatus.unlocked:
        return '已解锁';
      case AchievementStatus.locked:
        return '未解锁';
      case AchievementStatus.inProgress:
        return '进行中';
    }
  }
}
