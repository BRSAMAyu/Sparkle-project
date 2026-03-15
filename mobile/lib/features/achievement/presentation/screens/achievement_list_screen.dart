import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_card.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_stats_panel.dart';
import 'package:sparkle/features/achievement/presentation/widgets/streak_indicator.dart';
import 'package:sparkle/l10n/app_localizations.dart';
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
  }) =>
      AchievementFilterOptions(
        category: category ?? this.category,
        rarity: rarity ?? this.rarity,
        status: status ?? this.status,
      );

  bool get hasFilters =>
      category != null ||
      rarity != null ||
      (status != null && status != AchievementStatus.all);
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

class _AchievementListScreenState extends ConsumerState<AchievementListScreen> {
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
    final l10n = context.l10n;

    return SparklePageScaffold(
      role: SparklePageRole.immersive,
      safeArea: false,
      child: ContentConstraint(
        child: CustomScrollView(
          slivers: [
            // 顶部统计面板
            SliverToBoxAdapter(
              child: _buildHeader(context, state, l10n),
            ),

            // 筛选栏
            SliverToBoxAdapter(
              child: _buildFilterBar(context, l10n),
            ),

            // 分类标签
            SliverToBoxAdapter(
              child: _buildCategoryTabs(context, l10n),
            ),

            // 内容区域
            if (state.isLoading)
              const SliverFillRemaining(
                child: Center(child: CircularProgressIndicator()),
              )
            else if (state.error != null)
              SliverFillRemaining(
                child: _buildErrorView(context, state.error!, l10n),
              )
            else
              _buildAchievementContent(state),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(
    BuildContext context,
    AchievementState state,
    AppLocalizations l10n,
  ) =>
      Container(
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
          child: LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxWidth < 420;
              return Column(
                children: [
                  Row(
                    children: [
                      SparkleIconButton(
                        icon: const Icon(Icons.arrow_back),
                        onPressed: () => context.pop(),
                        variant: ButtonVariant.ghost,
                      ),
                      const SizedBox(width: DS.spacing8),
                      Expanded(
                        child: Text(
                          l10n.achievementTitle,
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
                  DashboardStreakIndicator(
                    onTap: () => _showStreakDetails(context),
                  ),
                  const SizedBox(height: DS.spacing16),
                  AchievementStatsPanel(
                    stats: state.stats,
                    isCompact: compact,
                  ),
                ],
              );
            },
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
  }) =>
      GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(DS.spacing8),
          decoration: BoxDecoration(
            color: isActive
                ? DS.brandPrimary
                : DS.surfacePrimary.withValues(alpha: 0),
            borderRadius: DS.borderRadius8,
          ),
          child: Icon(
            icon,
            size: DS.iconSizeSm,
            color: isActive ? DS.textOnPrimary : DS.textSecondary,
          ),
        ),
      );

  Widget _buildFilterBar(BuildContext context, AppLocalizations l10n) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing12,
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 420;
            final search = Container(
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
                        hintText: l10n.achievementSearch,
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
            );

            if (compact) {
              return Column(
                children: [
                  search,
                  const SizedBox(height: DS.spacing12),
                  SizedBox(
                    width: double.infinity,
                    child: _buildFilterButton(l10n),
                  ),
                ],
              );
            }

            return Row(
              children: [
                Expanded(child: search),
                const SizedBox(width: DS.spacing12),
                _buildFilterButton(l10n),
              ],
            );
          },
        ),
      );

  Widget _buildFilterButton(AppLocalizations l10n) {
    final hasFilters = _filterOptions.hasFilters;

    return GestureDetector(
      onTap: () => _showFilterSheet(context),
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing12,
        ),
        decoration: BoxDecoration(
          color: hasFilters
              ? DS.brandPrimary.withValues(alpha: 0.1)
              : DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: hasFilters ? DS.brandPrimary : DS.border,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.filter_list,
              size: DS.iconSizeSm,
              color: hasFilters ? DS.brandPrimary : DS.textSecondary,
            ),
            const SizedBox(width: DS.spacing8),
            Text(
              hasFilters
                  ? l10n.achievementFilterActive
                  : l10n.achievementFilter,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: hasFilters ? DS.brandPrimary : DS.textSecondary,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCategoryTabs(BuildContext context, AppLocalizations l10n) {
    final categories = [
      l10n.achievementAll,
      l10n.achievementStatusUnlocked,
      l10n.achievementStatusInProgress,
      l10n.achievementCategoryMilestone,
      l10n.achievementCategoryStreak,
      l10n.achievementCategoryMastery,
      l10n.achievementCategoryExploration,
      l10n.achievementCategoryTask,
    ];
    final selectedCategory = _filterOptions.status != null
        ? _getStatusName(_filterOptions.status!, l10n)
        : _filterOptions.category != null
            ? _getCategoryLocalizedName(_filterOptions.category!, l10n)
            : l10n.achievementAll;

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
            padding: EdgeInsets.only(
              right: index == categories.length - 1 ? 0 : DS.spacing12,
            ),
            child: _buildCategoryChip(category, isSelected, l10n),
          );
        },
      ),
    );
  }

  Widget _buildCategoryChip(
    String category,
    bool isSelected,
    AppLocalizations l10n,
  ) =>
      GestureDetector(
        onTap: () => _selectCategory(category, l10n),
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
              fontWeight:
                  isSelected ? DS.fontWeightSemibold : DS.fontWeightRegular,
              color: isSelected ? DS.textOnPrimary : DS.textSecondary,
            ),
          ),
        ),
      );

  Widget _buildAchievementContent(AchievementState state) {
    final filteredAchievements = _filterAchievements(state.achievements);

    if (filteredAchievements.isEmpty) {
    return SliverFillRemaining(
        child: _buildEmptyView(context, context.l10n),
      );
    }

    if (_viewMode == AchievementViewMode.grid) {
      return SliverPadding(
        padding: const EdgeInsets.all(DS.spacing16),
        sliver: SliverLayoutBuilder(
          builder: (context, constraints) {
            final width = constraints.crossAxisExtent;
            final crossAxisCount = width < 380
                ? 1
                : width < 900
                    ? 2
                    : 3;
            final mainAxisExtent = width < 380
                ? 190.0
                : width < 900
                    ? 228.0
                    : 236.0;

            return SliverGrid(
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: crossAxisCount,
                mainAxisSpacing: DS.spacing12,
                crossAxisSpacing: DS.spacing12,
                mainAxisExtent: mainAxisExtent,
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
            );
          },
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
              padding: EdgeInsets.only(
                bottom: index < filteredAchievements.length - 1
                    ? DS.spacing12
                    : 0,
              ),
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

  Widget _buildEmptyView(BuildContext context, AppLocalizations l10n) => Center(
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
              l10n.achievementNoMatch,
              style: TextStyle(
                fontSize: DS.fontSizeBase,
                color: DS.textSecondary,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              l10n.achievementAdjustFilter,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: DS.textTertiary,
              ),
            ),
          ],
        ),
      );

  Widget _buildErrorView(
    BuildContext context,
    String error,
    AppLocalizations l10n,
  ) =>
      Center(
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
              l10n.loadingFailed,
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
            SparkleButton.outline(
              label: l10n.retry,
              onPressed: () {
                ref.read(achievementProvider.notifier).loadInitialData();
              },
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
          .where(
            (a) =>
                a.achievement.name
                    .toLowerCase()
                    .contains(_searchQuery.toLowerCase()) ||
                (a.achievement.description
                        ?.toLowerCase()
                        .contains(_searchQuery.toLowerCase()) ??
                    false),
          )
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

  void _selectCategory(String category, AppLocalizations l10n) {
    AchievementStatus? status;

    if (category == l10n.achievementAll) {
      setState(() {
        _filterOptions = _filterOptions.copyWith(
          status: null,
          category: null,
        );
      });
      return;
    }

    if (category == l10n.achievementStatusUnlocked) {
      status = AchievementStatus.unlocked;
    } else if (category == l10n.achievementStatusInProgress) {
      status = AchievementStatus.inProgress;
    } else {
      // Map category names to achievement categories
      final categoryMap = {
        l10n.achievementCategoryMilestone: 'milestone',
        l10n.achievementCategoryStreak: 'streak',
        l10n.achievementCategoryMastery: 'mastery',
        l10n.achievementCategoryExploration: 'exploration',
        l10n.achievementCategoryTask: 'tasks',
      };
      setState(() {
        _filterOptions = _filterOptions.copyWith(
          category: categoryMap[category],
          status: null,
        );
      });
      return;
    }

    setState(() {
      _filterOptions = _filterOptions.copyWith(
        status: status,
        category: null,
      );
    });
  }

  String _getStatusName(AchievementStatus status, AppLocalizations l10n) {
    switch (status) {
      case AchievementStatus.all:
        return l10n.achievementAll;
      case AchievementStatus.unlocked:
        return l10n.achievementStatusUnlocked;
      case AchievementStatus.locked:
        return l10n.achievementStatusLocked;
      case AchievementStatus.inProgress:
        return l10n.achievementStatusInProgress;
    }
  }

  String _getCategoryLocalizedName(String category, AppLocalizations l10n) {
    switch (category) {
      case 'milestone':
        return l10n.achievementCategoryMilestone;
      case 'streak':
        return l10n.achievementCategoryStreak;
      case 'mastery':
        return l10n.achievementCategoryMastery;
      case 'exploration':
      case 'node_explore':
        return l10n.achievementCategoryExploration;
      case 'tasks':
      case 'task':
      case 'task_complete':
        return l10n.achievementCategoryTask;
      default:
        return category;
    }
  }

  void _showFilterSheet(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
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
    final l10n = context.l10n;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
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
            Text(
              l10n.streakDetails,
              style: const TextStyle(
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
class _AchievementFilterSheet extends StatefulWidget {
  const _AchievementFilterSheet({
    required this.currentOptions,
    required this.onApply,
    required this.onClear,
  });

  final AchievementFilterOptions currentOptions;
  final void Function(AchievementFilterOptions) onApply;
  final VoidCallback onClear;

  @override
  State<_AchievementFilterSheet> createState() =>
      _AchievementFilterSheetState();
}

class _AchievementFilterSheetState extends State<_AchievementFilterSheet> {
  late AchievementFilterOptions _options;

  @override
  void initState() {
    super.initState();
    _options = widget.currentOptions;
  }

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
                Text(
                  context.l10n.achievementFilterSheet,
                  style: const TextStyle(
                    fontSize: DS.fontSizeLg,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                SparkleButton.ghost(
                  label: context.l10n.commonClear,
                  onPressed: widget.onClear,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing16),

            // 稀有度筛选
            _buildRarityFilter(context.l10n),
            const SizedBox(height: DS.spacing16),

            // 状态筛选
            _buildStatusFilter(context.l10n),
            const SizedBox(height: DS.spacing24),

            // 应用按钮
            SizedBox(
              width: double.infinity,
              child: SparkleButton.primary(
                label: context.l10n.achievementApplyFilter,
                onPressed: () => widget.onApply(_options),
                expand: true,
              ),
            ),
          ],
        ),
      );

  Widget _buildRarityFilter(AppLocalizations l10n) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.achievementRarity,
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
              final isSelected = _options.rarity == rarity;
              return _buildFilterChip(
                _getRarityName(rarity, l10n),
                isSelected,
                onTap: () {
                  setState(() {
                    _options = _options.copyWith(
                      rarity: _options.rarity == rarity ? null : rarity,
                    );
                  });
                },
              );
            }).toList(),
          ),
        ],
      );

  Widget _buildStatusFilter(AppLocalizations l10n) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.achievementStatus,
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
              final isSelected = status == AchievementStatus.all
                  ? _options.status == null ||
                      _options.status == AchievementStatus.all
                  : _options.status == status;
              return _buildFilterChip(
                _getStatusDisplayName(status, l10n),
                isSelected,
                onTap: () {
                  setState(() {
                    if (status == AchievementStatus.all) {
                      _options = _options.copyWith(status: null);
                    } else {
                      _options = _options.copyWith(
                        status: _options.status == status ? null : status,
                      );
                    }
                  });
                },
              );
            }).toList(),
          ),
        ],
      );

  Widget _buildFilterChip(
    String label,
    bool isSelected, {
    VoidCallback? onTap,
  }) =>
      GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: isSelected
                ? DS.brandPrimary.withValues(alpha: 0.1)
                : DS.surfaceSecondary,
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

  String _getRarityName(AchievementRarity rarity, AppLocalizations l10n) {
    switch (rarity) {
      case AchievementRarity.common:
        return l10n.achievementRarityCommon;
      case AchievementRarity.rare:
        return l10n.achievementRarityRare;
      case AchievementRarity.epic:
        return l10n.achievementRarityEpic;
      case AchievementRarity.legendary:
        return l10n.achievementRarityLegendary;
    }
  }

  String _getStatusDisplayName(AchievementStatus status, AppLocalizations l10n) {
    switch (status) {
      case AchievementStatus.all:
        return l10n.achievementAll;
      case AchievementStatus.unlocked:
        return l10n.achievementStatusUnlocked;
      case AchievementStatus.locked:
        return l10n.achievementStatusLocked;
      case AchievementStatus.inProgress:
        return l10n.achievementStatusInProgress;
    }
  }
}
