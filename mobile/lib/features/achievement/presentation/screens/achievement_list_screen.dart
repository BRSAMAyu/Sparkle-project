import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/achievement/achievement_routes.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_card.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_stats_panel.dart';
import 'package:sparkle/features/achievement/presentation/widgets/rarity_badge.dart';
import 'package:sparkle/features/achievement/presentation/widgets/streak_indicator.dart';
import 'package:sparkle/features/task/task_routes.dart';
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

  static const Object _unset = Object();

  final String? category;
  final AchievementRarity? rarity;
  final AchievementStatus? status;

  AchievementFilterOptions copyWith({
    Object? category = _unset,
    Object? rarity = _unset,
    Object? status = _unset,
  }) =>
      AchievementFilterOptions(
        category:
            identical(category, _unset) ? this.category : category as String?,
        rarity: identical(rarity, _unset)
            ? this.rarity
            : rarity as AchievementRarity?,
        status: identical(status, _unset)
            ? this.status
            : status as AchievementStatus?,
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

class _AchievementListScreenState extends ConsumerState<AchievementListScreen>
    with SingleTickerProviderStateMixin {
  AchievementViewMode _viewMode = AchievementViewMode.grid;
  AchievementFilterOptions _filterOptions = const AchievementFilterOptions();
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  GoRouter? _router;
  String? _lastObservedRoutePath;

  late final AnimationController _headerController;
  late final Animation<double> _headerFade;
  late final Animation<Offset> _headerSlide;

  @override
  void initState() {
    super.initState();
    _headerController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );
    _headerFade = CurvedAnimation(
      parent: _headerController,
      curve: Curves.easeOut,
    );
    _headerSlide = Tween<Offset>(
      begin: const Offset(0, -0.05),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _headerController,
        curve: Curves.easeOutCubic,
      ),
    );
    unawaited(_headerController.forward());
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _attachRouteRefreshListener();
  }

  @override
  void dispose() {
    _router?.routeInformationProvider.removeListener(
      _handleRouteVisibilityChanged,
    );
    _searchController.dispose();
    _headerController.dispose();
    super.dispose();
  }

  void _attachRouteRefreshListener() {
    final router = GoRouter.of(context);
    if (identical(_router, router)) {
      return;
    }
    _router?.routeInformationProvider.removeListener(
      _handleRouteVisibilityChanged,
    );
    _router = router;
    _lastObservedRoutePath = router.routeInformationProvider.value.uri.path;
    router.routeInformationProvider.addListener(_handleRouteVisibilityChanged);
  }

  void _handleRouteVisibilityChanged() {
    final path = _router?.routeInformationProvider.value.uri.path;
    final previousPath = _lastObservedRoutePath;
    _lastObservedRoutePath = path;
    if (!mounted ||
        path != AchievementRoutes.basePath ||
        previousPath == AchievementRoutes.basePath) {
      return;
    }

    unawaited(_refreshAchievements());
  }

  Future<void> _refreshAchievements() =>
      ref.read(achievementProvider.notifier).loadInitialData();

  @override
  Widget build(BuildContext context) {
    ref.watch(achievementEventConsumerProvider);
    final state = ref.watch(achievementProvider);
    final l10n = context.l10n;

    return SparklePageScaffold(
      role: SparklePageRole.immersive,
      safeArea: false,
      child: ContentConstraint(
        child: RefreshIndicator(
          onRefresh: _refreshAchievements,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              // 顶部统计面板
              SliverToBoxAdapter(
                child: SlideTransition(
                  position: _headerSlide,
                  child: FadeTransition(
                    opacity: _headerFade,
                    child: _buildHeader(context, state, l10n),
                  ),
                ),
              ),

              // 筛选栏
              SliverToBoxAdapter(
                child: _AnimatedSection(
                  index: 1,
                  child: _buildFilterBar(context, l10n),
                ),
              ),

              // 分类标签
              SliverToBoxAdapter(
                child: _AnimatedSection(
                  index: 2,
                  child: _buildCategoryTabs(context, l10n),
                ),
              ),

              // 限时活动区块
              if (!state.isLoading && state.error == null)
                _buildLimitedTimeSection(state.achievements, l10n),

              // 内容区域
              if (state.isLoading)
                const SliverToBoxAdapter(
                  child: SizedBox(
                    height: 520,
                    child: SparkleListSkeleton(count: 4),
                  ),
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
              Color.lerp(DS.surfaceSecondary, DS.brandPrimary, 0.04) ??
                  DS.surfaceSecondary,
            ],
          ),
          boxShadow: [
            BoxShadow(
              color: DS.textPrimary.withValues(alpha: 0.04),
              blurRadius: 18,
              offset: const Offset(0, 10),
            ),
          ],
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
                  const SizedBox(height: DS.spacing16),
                  _buildQuickActions(context, l10n),
                ],
              );
            },
          ),
        ),
      );

  Widget _buildViewToggle() => DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              DS.surfaceSecondary,
              Color.lerp(DS.surfacePrimary, DS.brandPrimary, 0.03) ??
                  DS.surfacePrimary,
            ],
          ),
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.border.withValues(alpha: 0.6)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildViewModeButton(
              icon: Icons.grid_view,
              isActive: _viewMode == AchievementViewMode.grid,
              onTap: () {
                unawaited(SensoryFeedbackService.emit(
                    SensoryFeedbackEvent.selection));
                setState(() => _viewMode = AchievementViewMode.grid);
              },
            ),
            _buildViewModeButton(
              icon: Icons.view_list,
              isActive: _viewMode == AchievementViewMode.list,
              onTap: () {
                unawaited(SensoryFeedbackService.emit(
                    SensoryFeedbackEvent.selection));
                setState(() => _viewMode = AchievementViewMode.list);
              },
            ),
          ],
        ),
      );

  Widget _buildQuickActions(BuildContext context, AppLocalizations l10n) =>
      LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 420;
          final singleColumn = constraints.maxWidth < 350;
          final cardWidth = singleColumn
              ? constraints.maxWidth
              : compact
                  ? (constraints.maxWidth - DS.spacing12) / 2
                  : (constraints.maxWidth - DS.spacing16) / 2;

          return Wrap(
            spacing: DS.spacing12,
            runSpacing: DS.spacing12,
            children: [
              SizedBox(
                width: cardWidth,
                child: _QuickActionCard(
                  icon: Icons.hub_outlined,
                  title: l10n.achievementMapTitle,
                  subtitle: l10n.achievementMapSubtitle,
                  onTap: () => context.push(AchievementRoutes.map),
                  index: 0,
                ),
              ),
              SizedBox(
                width: cardWidth,
                child: _QuickActionCard(
                  icon: Icons.handshake_outlined,
                  title: l10n.contractEntryTitle,
                  subtitle: l10n.contractEntrySubtitle,
                  onTap: () => context.push(AchievementRoutes.contract),
                  index: 1,
                ),
              ),
            ],
          );
        },
      );

  Widget _buildViewModeButton({
    required IconData icon,
    required bool isActive,
    required VoidCallback onTap,
  }) =>
      GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
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
          vertical: DS.spacing10,
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
                  const SizedBox(height: DS.spacing10),
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
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing10,
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
      height: 44,
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
            child: _AnimatedCategoryChip(
              category: category,
              isSelected: isSelected,
              onTap: () => _selectCategory(category, l10n),
            ),
          );
        },
      ),
    );
  }

  Widget _buildLimitedTimeSection(
    List<AchievementWithProgress> achievements,
    AppLocalizations l10n,
  ) {
    final limited = _getLimitedAchievements(achievements);
    if (limited.isEmpty) {
      return const SliverToBoxAdapter(child: SizedBox.shrink());
    }

    return SliverToBoxAdapter(
      child: _AnimatedSection(
        index: 3,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing16,
            DS.spacing16,
            0,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.timer_outlined,
                        size: DS.iconSizeSm,
                        color: DS.semanticWarning,
                      ),
                      const SizedBox(width: DS.spacing8),
                      Text(
                        l10n.achievementLimitedTitle,
                        style: TextStyle(
                          fontSize: DS.fontSizeBase,
                          fontWeight: DS.fontWeightSemibold,
                          color: DS.textPrimary,
                        ),
                      ),
                    ],
                  ),
                  Text(
                    l10n.achievementLimitedSubtitle,
                    style: TextStyle(
                      fontSize: DS.fontSizeSm,
                      color: DS.textSecondary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              SizedBox(
                height: 170,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: limited.length,
                  separatorBuilder: (_, __) =>
                      const SizedBox(width: DS.spacing12),
                  itemBuilder: (context, index) => _AnimatedLimitedCard(
                    index: index,
                    child: _LimitedAchievementCard(
                      achievement: limited[index],
                      l10n: l10n,
                      onTap: () => _openAchievementDetail(limited[index]),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<AchievementWithProgress> _getLimitedAchievements(
    List<AchievementWithProgress> achievements,
  ) {
    final now = DateTime.now();
    return achievements.where((achievement) {
      final data = achievement.achievement;
      if (!data.isLimited) return false;
      final activeFrom = data.activeFrom;
      final activeTo = data.activeTo;
      if (activeFrom != null && now.isBefore(activeFrom)) return false;
      if (activeTo != null && now.isAfter(activeTo)) return false;
      return true;
    }).toList();
  }

  Widget _buildAchievementContent(AchievementState state) {
    final filteredAchievements = _filterAchievements(state.achievements);

    if (filteredAchievements.isEmpty) {
      return SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing16,
            DS.spacing16,
            DS.spacing32,
          ),
          child: _buildEmptyView(context, context.l10n),
        ),
      );
    }

    if (_viewMode == AchievementViewMode.grid) {
      return SliverPadding(
        padding: const EdgeInsets.all(DS.spacing16),
        sliver: SliverLayoutBuilder(
          builder: (context, constraints) {
            final width = constraints.crossAxisExtent;
            final crossAxisSpacing = width < 360 ? DS.spacing8 : DS.spacing12;
            final mainAxisSpacing = width < 360 ? DS.spacing8 : DS.spacing12;
            const crossAxisCount = 2;
            final mainAxisExtent = width < 360
                ? 188.0
                : width < 430
                    ? 204.0
                    : 220.0;

            return SliverGrid(
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: crossAxisCount,
                mainAxisSpacing: mainAxisSpacing,
                crossAxisSpacing: crossAxisSpacing,
                mainAxisExtent: mainAxisExtent,
              ),
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final achievement = filteredAchievements[index];
                  return AnimatedAchievementCard(
                    index: index,
                    rarity: achievement.achievement.rarity,
                    child: AchievementGridCard(
                      achievement: achievement,
                      onTap: () => _openAchievementDetail(achievement),
                    ),
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
                bottom:
                    index < filteredAchievements.length - 1 ? DS.spacing12 : 0,
              ),
              child: AnimatedAchievementCard(
                index: index,
                rarity: achievement.achievement.rarity,
                child: AchievementListCard(
                  achievement: achievement,
                  onTap: () => _openAchievementDetail(achievement),
                ),
              ),
            );
          },
          childCount: filteredAchievements.length,
        ),
      ),
    );
  }

  Widget _buildEmptyView(BuildContext context, AppLocalizations l10n) {
    final hasFilters =
        _searchQuery.trim().isNotEmpty || _filterOptions.hasFilters;

    return EmptyState(
      icon: Icons.emoji_events_outlined,
      title: hasFilters ? l10n.achievementNoMatch : '还没有解锁任何成就',
      description: hasFilters
          ? l10n.achievementAdjustFilter
          : '先完成一个任务、坚持一次学习或点亮一个知识节点，这里就会开始记录你的里程碑。',
      actionText: hasFilters ? '清空筛选' : '去创建今日任务',
      onAction: () {
        if (hasFilters) {
          _searchController.clear();
          setState(() {
            _searchQuery = '';
            _filterOptions = const AchievementFilterOptions();
          });
          return;
        }
        context.push(TaskRoutes.taskCreate);
      },
    );
  }

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
              l10n.loadingFailed(error),
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
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
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
    unawaited(
      showSensoryModalBottomSheet<void>(
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
      ),
    );
  }

  void _openAchievementDetail(AchievementWithProgress achievement) {
    context.push('/achievements/${achievement.achievement.id}');
  }

  void _showStreakDetails(BuildContext context) {
    context.push(AchievementRoutes.streakDetails);
  }
}

// ─── Animated section entrance ──────────────────────────────────────────────

class _AnimatedSection extends StatelessWidget {
  const _AnimatedSection({
    required this.index,
    required this.child,
  });

  final int index;
  final Widget child;

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.0, end: 1.0),
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeOutCubic,
        builder: (context, value, child) {
          // Apply the delay by clamping based on elapsed time
          return Opacity(
            opacity: value,
            child: Transform.translate(
              offset: Offset(0, 12 * (1 - value)),
              child: child,
            ),
          );
        },
        child: child,
      );
}

// ─── Animated category chip with selection feedback ─────────────────────────

class _AnimatedCategoryChip extends StatelessWidget {
  const _AnimatedCategoryChip({
    required this.category,
    required this.isSelected,
    required this.onTap,
  });

  final String category;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
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
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: DS.brandPrimary.withValues(alpha: 0.2),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
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
}

// ─── Animated limited card entrance ─────────────────────────────────────────

class _AnimatedLimitedCard extends StatefulWidget {
  const _AnimatedLimitedCard({
    required this.index,
    required this.child,
  });

  final int index;
  final Widget child;

  @override
  State<_AnimatedLimitedCard> createState() => _AnimatedLimitedCardState();
}

class _AnimatedLimitedCardState extends State<_AnimatedLimitedCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    Future.delayed(Duration(milliseconds: widget.index * 80), () {
      if (mounted) _controller.forward();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          final curve = Curves.easeOutCubic.transform(_controller.value);
          return Opacity(
            opacity: curve,
            child: Transform.translate(
              offset: Offset(20 * (1 - curve), 0),
              child: Transform.scale(
                scale: 0.92 + 0.08 * curve,
                child: child,
              ),
            ),
          );
        },
        child: widget.child,
      );
}

// ─── Quick action card with tap scale ───────────────────────────────────────

class _QuickActionCard extends StatefulWidget {
  const _QuickActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
    required this.index,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  final int index;

  @override
  State<_QuickActionCard> createState() => _QuickActionCardState();
}

class _QuickActionCardState extends State<_QuickActionCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _tapController;
  late final Animation<double> _tapScale;

  @override
  void initState() {
    super.initState();
    _tapController = AnimationController(
      duration: const Duration(milliseconds: 120),
      vsync: this,
    );
    _tapScale = Tween<double>(begin: 1.0, end: 0.96).animate(
      CurvedAnimation(parent: _tapController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _tapController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTapDown: (_) => _tapController.forward(),
        onTapUp: (_) {
          _tapController.reverse();
          widget.onTap();
        },
        onTapCancel: () => _tapController.reverse(),
        child: ScaleTransition(
          scale: _tapScale,
          child: Container(
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.surfacePrimary,
              borderRadius: DS.borderRadius12,
              border: Border.all(color: DS.border),
            ),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.12),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    widget.icon,
                    color: DS.brandPrimary,
                    size: DS.iconSizeSm,
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.title,
                        style: TextStyle(
                          fontSize: DS.fontSizeSm,
                          fontWeight: DS.fontWeightSemibold,
                          color: DS.textPrimary,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        widget.subtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                Icon(Icons.chevron_right, color: DS.textTertiary),
              ],
            ),
          ),
        ),
      );
}

// ─── Limited achievement card with countdown and glow ───────────────────────

class _LimitedAchievementCard extends StatelessWidget {
  const _LimitedAchievementCard({
    required this.achievement,
    required this.l10n,
    required this.onTap,
  });

  final AchievementWithProgress achievement;
  final AppLocalizations l10n;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final data = achievement.achievement;
    final rarityColor = RarityColorProvider.getColor(data.rarity);
    final countdown = _buildCountdownLabel(data, l10n);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 240,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              DS.surfaceSecondary,
              rarityColor.withValues(alpha: 0.06),
            ],
          ),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: rarityColor.withValues(alpha: 0.4)),
          boxShadow: [
            BoxShadow(
              color: rarityColor.withValues(alpha: 0.12),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _PulsingBadge(
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing8,
                      vertical: DS.spacing4,
                    ),
                    decoration: BoxDecoration(
                      color: DS.semanticWarning.withValues(alpha: 0.2),
                      borderRadius: DS.borderRadiusFull,
                    ),
                    child: Text(
                      l10n.achievementLimitedTime,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: DS.semanticWarning,
                        fontWeight: DS.fontWeightSemibold,
                      ),
                    ),
                  ),
                ),
                const Spacer(),
                if (data.eventTag != null)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing8,
                      vertical: DS.spacing4,
                    ),
                    decoration: BoxDecoration(
                      color: DS.brandPrimary.withValues(alpha: 0.12),
                      borderRadius: DS.borderRadiusFull,
                    ),
                    child: Text(
                      data.eventTag!,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: DS.brandPrimary,
                        fontWeight: DS.fontWeightSemibold,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            Text(
              data.name,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                fontWeight: DS.fontWeightBold,
                color: DS.textPrimary,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              countdown,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: DS.textSecondary,
              ),
            ),
            const Spacer(),
            if (achievement.isUnlocked)
              Row(
                children: [
                  Icon(
                    Icons.check_circle,
                    size: 14,
                    color: DS.semanticSuccess,
                  ),
                  const SizedBox(width: DS.spacing4),
                  Text(
                    l10n.achievementStatusUnlocked,
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      fontWeight: DS.fontWeightSemibold,
                      color: DS.semanticSuccess,
                    ),
                  ),
                ],
              )
            else ...[
              TweenAnimationBuilder<double>(
                tween:
                    Tween(begin: 0, end: achievement.progressPercentage / 100),
                duration: const Duration(milliseconds: 800),
                curve: Curves.easeOutCubic,
                builder: (context, value, _) => Column(
                  children: [
                    ClipRRect(
                      borderRadius: const BorderRadius.all(Radius.circular(3)),
                      child: LinearProgressIndicator(
                        value: value,
                        minHeight: 6,
                        backgroundColor: DS.neutral200,
                        color: rarityColor,
                      ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      '${(value * 100).toInt()}%',
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: DS.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _buildCountdownLabel(AchievementModel data, AppLocalizations l10n) {
    final now = DateTime.now();
    final end = data.activeTo;
    if (end == null) {
      return l10n.achievementLimitedSubtitle;
    }
    if (end.isBefore(now)) {
      return l10n.achievementEventStatusEnded;
    }
    final relative = Formatters.formatRelativeTime(end);
    return l10n.achievementEventEndsIn(relative);
  }
}

// ─── Subtle pulsing badge for limited-time indicators ───────────────────────

class _PulsingBadge extends StatefulWidget {
  const _PulsingBadge({required this.child});
  final Widget child;

  @override
  State<_PulsingBadge> createState() => _PulsingBadgeState();
}

class _PulsingBadgeState extends State<_PulsingBadge>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1800),
      vsync: this,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          final opacity = 0.7 + 0.3 * _controller.value;
          return Opacity(
            opacity: opacity,
            child: child,
          );
        },
        child: widget.child,
      );
}

// ─── Filter sheet ───────────────────────────────────────────────────────────

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
                accentColor: RarityColorProvider.getColor(rarity),
                onTap: () {
                  unawaited(SensoryFeedbackService.emit(
                      SensoryFeedbackEvent.selection));
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
                  unawaited(SensoryFeedbackService.emit(
                      SensoryFeedbackEvent.selection));
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
    Color? accentColor,
    VoidCallback? onTap,
  }) {
    final color = isSelected ? (accentColor ?? DS.brandPrimary) : DS.border;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color:
              isSelected ? color.withValues(alpha: 0.12) : DS.surfaceSecondary,
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: isSelected ? color : DS.border),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            color: isSelected ? color : DS.textSecondary,
            fontWeight:
                isSelected ? DS.fontWeightSemibold : DS.fontWeightRegular,
          ),
        ),
      ),
    );
  }

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

  String _getStatusDisplayName(
    AchievementStatus status,
    AppLocalizations l10n,
  ) {
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
