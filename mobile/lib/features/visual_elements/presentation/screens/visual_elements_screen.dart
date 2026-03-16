import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/visual_elements/data/repositories/visual_element_repository.dart';
import 'package:sparkle/features/visual_elements/domain/services/visual_recommendation_service.dart';
import 'package:sparkle/features/visual_elements/presentation/providers/visual_elements_provider.dart';
import 'package:sparkle/features/visual_elements/presentation/providers/visual_recommendation_provider.dart';
import 'package:sparkle/features/visual_elements/presentation/widgets/visual_element_preview_dialog.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';
import 'package:sparkle/shared/providers/visual_element_provider.dart';

/// 布局动画时长
const _kLayoutAnimationDuration = Duration(milliseconds: 400);
const _kLayoutAnimationCurve = Curves.easeOutCubic;

/// 视觉元素管理页面
class VisualElementsScreen extends ConsumerStatefulWidget {
  const VisualElementsScreen({super.key});

  @override
  ConsumerState<VisualElementsScreen> createState() =>
      _VisualElementsScreenState();
}

class _VisualElementsScreenState extends ConsumerState<VisualElementsScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  VisualElementFilterOptions _filterOptions = const VisualElementFilterOptions();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 6, vsync: this);
    _tabController.addListener(_onTabChanged);

    // 初始加载数据
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(visualElementsNotifierProvider.notifier).loadAll();
    });
  }

  @override
  void dispose() {
    _tabController.removeListener(_onTabChanged);
    _tabController.dispose();
    super.dispose();
  }

  void _onTabChanged() {
    if (!_tabController.indexIsChanging) {
      _updateFilterFromTab();
    }
  }

  void _updateFilterFromTab() {
    if (_tabController.index == 0) {
      setState(() {
        _filterOptions = _filterOptions.copyWith(
          type: null,
          showUnlockedOnly: false,
        );
      });
      ref.read(visualElementsNotifierProvider.notifier).setFilterOptions(
            _filterOptions,
          );
      return;
    }

    final adjustedIndex = _tabController.index - 1;
    final type = switch (adjustedIndex) {
      0 => null, // 全部
      1 => VisualElementType.background,
      2 => VisualElementType.particle,
      3 => VisualElementType.effect,
      4 => null, // 已解锁
      _ => null,
    };

    final showUnlockedOnly = adjustedIndex == 4;

    setState(() {
      _filterOptions = _filterOptions.copyWith(
        type: type,
        showUnlockedOnly: showUnlockedOnly,
      );
    });

    ref.read(visualElementsNotifierProvider.notifier).setFilterOptions(
          _filterOptions,
        );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final state = ref.watch(visualElementsNotifierProvider);

    return SparklePageScaffold(
      role: SparklePageRole.immersive,
      safeArea: false,
      child: ContentConstraint(
        child: NestedScrollView(
          headerSliverBuilder: (context, innerBoxIsScrolled) => [
            _buildHeader(context, l10n, state),
            _buildTabBar(context, l10n),
          ],
          body: _buildBody(context, l10n, state),
        ),
      ),
    );
  }

  Widget _buildHeader(
    BuildContext context,
    AppLocalizations l10n,
    VisualElementsState state,
  ) {
    final eventElements = state.allElements
        .where((element) => element.unlockSource == VisualElementUnlockSource.event)
        .toList();

    return SliverToBoxAdapter(
      child: Container(
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
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 导航栏
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
                      l10n.visualElementsTitle,
                      style: const TextStyle(
                        fontSize: DS.fontSizeXl,
                        fontWeight: DS.fontWeightBold,
                        color: DS.textPrimary,
                      ),
                    ),
                  ),
                  SparkleIconButton(
                    icon: const Icon(Icons.filter_list),
                    onPressed: () => _showFilterSheet(context, l10n),
                    variant: ButtonVariant.ghost,
                  ),
                ],
              ),

              const SizedBox(height: DS.spacing16),

              // 统计面板
              _buildStatsPanel(state.stats, l10n),

              if (eventElements.isNotEmpty) ...[
                const SizedBox(height: DS.spacing16),
                _buildEventSection(eventElements, state, l10n),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatsPanel(VisualElementStats stats, AppLocalizations l10n) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border.withValues(alpha: 0.5)),
      ),
      child: Row(
        children: [
          // 解锁进度
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.visualElementsUnlockProgress,
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    color: DS.textSecondary,
                  ),
                ),
                const SizedBox(height: DS.spacing8),
                ClipRRect(
                  borderRadius: DS.borderRadius8,
                  child: LinearProgressIndicator(
                    value: stats.unlockProgress,
                    backgroundColor: DS.surfaceTertiary,
                    valueColor: AlwaysStoppedAnimation(DS.brandPrimary),
                    minHeight: 8,
                  ),
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  '${stats.unlockedCount}/${stats.totalCount}',
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    fontWeight: DS.fontWeightMedium,
                    color: DS.textPrimary,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(width: DS.spacing16),

          // 装备中的元素
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing16,
              vertical: DS.spacing12,
            ),
            decoration: BoxDecoration(
              color: DS.brandPrimary10,
              borderRadius: DS.borderRadius12,
            ),
            child: Column(
              children: [
                Icon(
                  Icons.check_circle,
                  color: DS.brandPrimary,
                  size: DS.iconSizeMd,
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  '${stats.equippedCount}',
                  style: const TextStyle(
                    fontSize: DS.fontSizeLg,
                    fontWeight: DS.fontWeightBold,
                    color: DS.brandPrimary,
                  ),
                ),
                Text(
                  l10n.visualElementsEquipped,
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.brandPrimary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabBar(BuildContext context, AppLocalizations l10n) {
    return SliverPersistentHeader(
      pinned: true,
      delegate: _StickyTabBarDelegate(
        TabBar(
          controller: _tabController,
          isScrollable: false,
          indicatorSize: TabBarIndicatorSize.label,
          indicator: BoxDecoration(
            color: DS.brandPrimary,
            borderRadius: DS.borderRadius8,
          ),
          indicatorPadding: const EdgeInsets.symmetric(vertical: DS.spacing8),
          labelColor: DS.textOnPrimary,
          unselectedLabelColor: DS.textSecondary,
          labelStyle: const TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightMedium,
          ),
          tabs: [
            Tab(
              icon: const Icon(Icons.auto_awesome),
              text: l10n.visualElementsRecommended,
            ),
            Tab(text: l10n.visualElementTabAll),
            Tab(text: l10n.visualElementTabBackground),
            Tab(text: l10n.visualElementTabParticle),
            Tab(text: l10n.visualElementTabEffect),
            Tab(text: l10n.visualElementTabUnlocked),
          ],
        ),
      ),
    );
  }

  Widget _buildBody(
    BuildContext context,
    AppLocalizations l10n,
    VisualElementsState state,
  ) {
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null) {
      return _buildErrorView(state.error!, l10n);
    }

    if (_tabController.index == 0) {
      final recommendations = ref.watch(visualRecommendationProvider);
      return _buildRecommendationBody(context, l10n, state, recommendations);
    }

    final filteredElements = state.filteredElements;

    if (filteredElements.isEmpty) {
      return _buildEmptyView(l10n);
    }

    return RefreshIndicator(
      onRefresh: () =>
          ref.read(visualElementsNotifierProvider.notifier).refresh(),
      child: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.all(DS.spacing16),
            sliver: SliverLayoutBuilder(
              builder: (context, constraints) {
                return AnimatedSwitcher(
                  duration: _kLayoutAnimationDuration,
                  switchInCurve: _kLayoutAnimationCurve,
                  switchOutCurve: _kLayoutAnimationCurve,
                  layoutBuilder: (currentChild, previousChildren) {
                    // 使用 Stack 实现交叉淡入淡出
                    return Stack(
                      alignment: Alignment.center,
                      children: <Widget>[
                        ...previousChildren,
                        if (currentChild != null) currentChild,
                      ],
                    );
                  },
                  transitionBuilder: (child, animation) {
                    return FadeTransition(
                      opacity: animation,
                      child: SlideTransition(
                        position: Tween<Offset>(
                          begin: const Offset(0, 0.05),
                          end: Offset.zero,
                        ).animate(animation),
                        child: child,
                      ),
                    );
                  },
                  child: SliverGrid(
                    key: ValueKey(_filterOptions.hashCode),
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: _calculateCrossAxisCount(
                        constraints.crossAxisExtent,
                      ),
                      mainAxisSpacing: DS.spacing12,
                      crossAxisSpacing: DS.spacing12,
                      mainAxisExtent: 180,
                    ),
                    delegate: SliverChildBuilderDelegate(
                      (context, index) {
                        final element = filteredElements[index];
                        return _buildElementCard(element, state, l10n);
                      },
                      childCount: filteredElements.length,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildElementCard(
    VisualElementModel element,
    VisualElementsState state,
    AppLocalizations l10n,
  ) {
    final isUnlocked = state.unlockedIds.contains(element.id);
    final isEquipped = state.equippedIds.contains(element.id);
    final resolvedElement = element.copyWith(
      isUnlocked: isUnlocked,
      isEquipped: isEquipped,
    );

    return _VisualElementCard(
      element: resolvedElement,
      onTap: () => _showElementPreview(element, isUnlocked, isEquipped),
      onLongPress: isUnlocked && !isEquipped
          ? () => _equipElement(element.id)
          : null,
    );
  }

  void _showElementPreview(
    VisualElementModel element,
    bool isUnlocked,
    bool isEquipped,
  ) {
    VisualElementPreviewDialog.show(
      context,
      element: element,
      baseConfig: ref.read(visualElementsNotifierProvider).config,
      isUnlocked: isUnlocked,
      isEquipped: isEquipped,
      onEquip: isUnlocked ? () => _equipElement(element.id) : null,
      onUnequip: isEquipped
          ? () => _unequipElement(element.elementType)
          : null,
    );
  }

  Future<void> _equipElement(String elementId) async {
    final notifier = ref.read(visualElementsNotifierProvider.notifier);
    final success = await notifier.equipElement(elementId);

    if (mounted) {
      if (success) {
        ref.read(visualElementProvider.notifier).loadConfig();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.l10n.visualElementEquipSuccess),
            backgroundColor: DS.success,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.l10n.visualElementEquipFailed),
            backgroundColor: DS.error,
          ),
        );
      }
    }
  }

  Future<void> _unequipElement(VisualElementType type) async {
    final notifier = ref.read(visualElementsNotifierProvider.notifier);
    final success = await notifier.unequipElement(type);

    if (mounted) {
      if (success) {
        ref.read(visualElementProvider.notifier).loadConfig();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.l10n.visualElementUnequipSuccess),
            backgroundColor: DS.info,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.l10n.visualElementUnequipFailed),
            backgroundColor: DS.error,
          ),
        );
      }
    }
  }

  Widget _buildErrorView(String error, AppLocalizations l10n) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing24),
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
              style: const TextStyle(
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
            SparkleButton.primary(
              label: l10n.retry,
              onPressed: () {
                ref.read(visualElementsNotifierProvider.notifier).loadAll();
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyView(AppLocalizations l10n) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.palette_outlined,
              size: 64,
              color: DS.textTertiary,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              l10n.visualElementEmpty,
              style: TextStyle(
                fontSize: DS.fontSizeBase,
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendationBody(
    BuildContext context,
    AppLocalizations l10n,
    VisualElementsState state,
    AsyncValue<List<VisualRecommendation>> recommendationsValue,
  ) {
    return recommendationsValue.when(
      data: (recommendations) {
        if (recommendations.isEmpty) {
          return _buildEmptyView(l10n);
        }

        return RefreshIndicator(
          onRefresh: () =>
              ref.read(visualElementsNotifierProvider.notifier).refresh(),
          child: CustomScrollView(
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.all(DS.spacing16),
                sliver: SliverGrid(
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: _calculateCrossAxisCount(
                      MediaQuery.of(context).size.width,
                    ),
                    mainAxisSpacing: DS.spacing12,
                    crossAxisSpacing: DS.spacing12,
                    mainAxisExtent: 200,
                  ),
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final recommendation = recommendations[index];
                      final element = recommendation.element;
                      final isUnlocked = state.unlockedIds.contains(element.id);
                      final isEquipped = state.equippedIds.contains(element.id);
                      final resolvedElement = element.copyWith(
                        isUnlocked: isUnlocked,
                        isEquipped: isEquipped,
                      );

                      return _RecommendationCard(
                        element: resolvedElement,
                        reason: recommendation.reason,
                        reasonText: _recommendationReasonText(
                          l10n,
                          recommendation.reason,
                        ),
                        onTap: () => _showElementPreview(
                          element,
                          isUnlocked,
                          isEquipped,
                        ),
                        onEquip: isUnlocked && !isEquipped
                            ? () => _equipElement(element.id)
                            : null,
                      );
                    },
                    childCount: recommendations.length,
                  ),
                ),
              ),
            ],
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => _buildErrorView(err.toString(), l10n),
    );
  }

  String _recommendationReasonText(
    AppLocalizations l10n,
    VisualRecommendationReason reason,
  ) {
    switch (reason) {
      case VisualRecommendationReason.focus:
        return l10n.visualRecommendationFocus;
      case VisualRecommendationReason.relax:
        return l10n.visualRecommendationRelax;
      case VisualRecommendationReason.sprint:
        return l10n.visualRecommendationSprint;
      case VisualRecommendationReason.night:
        return l10n.visualRecommendationNight;
      case VisualRecommendationReason.streak:
        return l10n.visualRecommendationStreak;
    }
  }

  void _showFilterSheet(BuildContext context, AppLocalizations l10n) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _FilterSheet(
        currentOptions: _filterOptions,
        onApply: (options) {
          setState(() => _filterOptions = options);
          ref.read(visualElementsNotifierProvider.notifier).setFilterOptions(
                options,
              );
        },
        onClear: () {
          setState(() => _filterOptions = const VisualElementFilterOptions());
          ref.read(visualElementsNotifierProvider.notifier).clearFilters();
        },
      ),
    );
  }

  int _calculateCrossAxisCount(double width) {
    if (width < 360) return 1;
    if (width < 600) return 2;
    if (width < 900) return 3;
    return 4;
  }

  Widget _buildEventSection(
    List<VisualElementModel> eventElements,
    VisualElementsState state,
    AppLocalizations l10n,
  ) {
    final endAt = _getEventEndAt(eventElements);
    final countdownText = endAt == null
        ? null
        : _formatEventCountdown(endAt, l10n);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.brandPrimary.withValues(alpha: 0.12),
            DS.brandSecondary.withValues(alpha: 0.08),
          ],
        ),
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.timer_outlined,
                color: DS.brandPrimary,
                size: DS.iconSizeSm,
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  l10n.visualElementEventTitle,
                  style: const TextStyle(
                    fontSize: DS.fontSizeBase,
                    fontWeight: DS.fontWeightBold,
                    color: DS.textPrimary,
                  ),
                ),
              ),
              if (countdownText != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing8,
                    vertical: DS.spacing4,
                  ),
                  decoration: BoxDecoration(
                    color: DS.surfacePrimary.withValues(alpha: 0.7),
                    borderRadius: DS.borderRadius8,
                  ),
                  child: Text(
                    countdownText,
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: DS.textSecondary,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          SizedBox(
            height: 150,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: eventElements.length,
              separatorBuilder: (_, __) => const SizedBox(width: DS.spacing12),
              itemBuilder: (context, index) {
                final element = eventElements[index];
                final resolvedElement = element.copyWith(
                  isUnlocked: state.unlockedIds.contains(element.id),
                  isEquipped: state.equippedIds.contains(element.id),
                );
                return SizedBox(
                  width: 160,
                  child: _VisualElementCard(
                    element: resolvedElement,
                    onTap: () => _showElementPreview(
                      element,
                      state.unlockedIds.contains(element.id),
                      state.equippedIds.contains(element.id),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  DateTime? _getEventEndAt(List<VisualElementModel> elements) {
    final dates = <DateTime>[];
    for (final element in elements) {
      final raw = element.unlockRequirement?['event_end_at'] ??
          element.unlockRequirement?['end_at'] ??
          element.unlockRequirement?['endAt'];
      final parsed = _parseEventDate(raw);
      if (parsed != null) {
        dates.add(parsed);
      }
    }

    if (dates.isEmpty) return null;
    dates.sort();
    return dates.first;
  }

  DateTime? _parseEventDate(dynamic raw) {
    if (raw == null) return null;
    if (raw is String) {
      return DateTime.tryParse(raw);
    }
    if (raw is int) {
      return DateTime.fromMillisecondsSinceEpoch(raw);
    }
    if (raw is num) {
      return DateTime.fromMillisecondsSinceEpoch(raw.toInt());
    }
    return null;
  }

  String _formatEventCountdown(DateTime endAt, AppLocalizations l10n) {
    final now = DateTime.now();
    if (endAt.isBefore(now)) {
      return l10n.visualElementEventEnded;
    }

    final remaining = endAt.difference(now);
    final days = remaining.inDays;
    final hours = remaining.inHours % 24;
    final minutes = remaining.inMinutes % 60;

    if (days > 0) {
      return l10n.visualElementEventEndsIn(
        l10n.visualElementEventCountdownDays(days, hours),
      );
    }
    if (hours > 0) {
      return l10n.visualElementEventEndsIn(
        l10n.visualElementEventCountdownHours(hours, minutes),
      );
    }
    return l10n.visualElementEventEndsIn(
      l10n.visualElementEventCountdownMinutes(minutes),
    );
  }
}

/// 粘性 TabBar 代理
class _StickyTabBarDelegate extends SliverPersistentHeaderDelegate {
  _StickyTabBarDelegate(this.tabBar);

  final TabBar tabBar;

  @override
  double get minExtent => tabBar.preferredSize.height;

  @override
  double get maxExtent => tabBar.preferredSize.height;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) {
    return Container(
      color: DS.surfacePrimary,
      child: tabBar,
    );
  }

  @override
  bool shouldRebuild(_StickyTabBarDelegate oldDelegate) {
    return tabBar != oldDelegate.tabBar;
  }
}

/// 筛选面板
class _FilterSheet extends StatefulWidget {
  const _FilterSheet({
    required this.currentOptions,
    required this.onApply,
    required this.onClear,
  });

  final VisualElementFilterOptions currentOptions;
  final void Function(VisualElementFilterOptions) onApply;
  final VoidCallback onClear;

  @override
  State<_FilterSheet> createState() => _FilterSheetState();
}

class _FilterSheetState extends State<_FilterSheet> {
  late VisualElementFilterOptions _options;

  @override
  void initState() {
    super.initState();
    _options = widget.currentOptions;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;

    return Container(
      padding: const EdgeInsets.all(DS.spacing24),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: SingleChildScrollView(
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
                  l10n.visualElementFilter,
                  style: const TextStyle(
                    fontSize: DS.fontSizeLg,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                SparkleButton.ghost(
                  label: l10n.commonClear,
                  onPressed: widget.onClear,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing16),

            // 稀有度筛选
            _buildRarityFilter(l10n),
            const SizedBox(height: DS.spacing16),

            // 状态筛选
            _buildStatusFilter(l10n),
            const SizedBox(height: DS.spacing16),

            // 排序选项
            _buildSortFilter(l10n),
            const SizedBox(height: DS.spacing24),

            // 应用按钮
            SizedBox(
              width: double.infinity,
              child: SparkleButton.primary(
                label: l10n.visualElementApplyFilter,
                onPressed: () => widget.onApply(_options),
                expand: true,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusFilter(AppLocalizations l10n) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.visualElementStatus,
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
          children: [
            _buildFilterChip(
              l10n.visualElementUnlocked,
              _options.showUnlockedOnly,
              onTap: () {
                setState(() {
                  _options = _options.copyWith(
                    showUnlockedOnly: !_options.showUnlockedOnly,
                  );
                });
              },
            ),
            _buildFilterChip(
              l10n.visualElementEquipped,
              _options.showEquippedOnly,
              onTap: () {
                setState(() {
                  _options = _options.copyWith(
                    showEquippedOnly: !_options.showEquippedOnly,
                  );
                });
              },
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSortFilter(AppLocalizations l10n) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.visualElementSort,
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
          children: [
            _buildFilterChip(
              l10n.visualElementSortDefault,
              _options.sortBy == VisualElementSortBy.sortOrder,
              onTap: () {
                setState(() {
                  _options = _options.copyWith(
                    sortBy: VisualElementSortBy.sortOrder,
                  );
                });
              },
            ),
            _buildFilterChip(
              l10n.visualElementSortName,
              _options.sortBy == VisualElementSortBy.name,
              onTap: () {
                setState(() {
                  _options = _options.copyWith(
                    sortBy: VisualElementSortBy.name,
                  );
                });
              },
            ),
            _buildFilterChip(
              l10n.visualElementSortRarity,
              _options.sortBy == VisualElementSortBy.rarity,
              onTap: () {
                setState(() {
                  _options = _options.copyWith(
                    sortBy: VisualElementSortBy.rarity,
                  );
                });
              },
            ),
            _buildFilterChip(
              l10n.visualElementSortUnlockDate,
              _options.sortBy == VisualElementSortBy.unlockDate,
              onTap: () {
                setState(() {
                  _options = _options.copyWith(
                    sortBy: VisualElementSortBy.unlockDate,
                  );
                });
              },
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildRarityFilter(AppLocalizations l10n) {
    return Column(
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
          children: VisualElementRarity.values.map((rarity) {
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
  }

  Widget _buildFilterChip(
    String label,
    bool isSelected, {
    VoidCallback? onTap,
  }) {
    return GestureDetector(
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
  }

  String _getRarityName(VisualElementRarity rarity, AppLocalizations l10n) {
    switch (rarity) {
      case VisualElementRarity.common:
        return l10n.achievementRarityCommon;
      case VisualElementRarity.rare:
        return l10n.achievementRarityRare;
      case VisualElementRarity.epic:
        return l10n.achievementRarityEpic;
      case VisualElementRarity.legendary:
        return l10n.achievementRarityLegendary;
    }
  }
}

/// 视觉元素卡片（简化版）
class _VisualElementCard extends StatelessWidget {
  const _VisualElementCard({
    required this.element,
    this.onTap,
    this.onLongPress,
  });

  final VisualElementModel element;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) {
    final colors = _getRarityColors(element.rarity);

    return GestureDetector(
      onTap: onTap,
      onLongPress: onLongPress,
      child: Container(
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          border: Border.all(
            color: element.isEquipped
                ? colors.border
                : DS.border.withValues(alpha: 0.5),
            width: element.isEquipped ? 2 : 1,
          ),
        ),
        child: Stack(
          children: [
            // 内容
            Padding(
              padding: const EdgeInsets.all(DS.spacing12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 类型图标
                  Container(
                    padding: const EdgeInsets.all(DS.spacing6),
                    decoration: BoxDecoration(
                      color: DS.surfacePrimary.withValues(alpha: 0.8),
                      borderRadius: DS.borderRadius8,
                    ),
                    child: Icon(
                      _getTypeIcon(element.elementType),
                      size: DS.iconSizeSm,
                      color: DS.textSecondary,
                    ),
                  ),

                  const Spacer(),

                  // 名称
                  Text(
                    element.name,
                    style: const TextStyle(
                      fontSize: DS.fontSizeSm,
                      fontWeight: DS.fontWeightSemibold,
                      color: DS.textPrimary,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),

                  const SizedBox(height: DS.spacing4),

                  // 稀有度
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing6,
                      vertical: DS.spacing2,
                    ),
                    decoration: BoxDecoration(
                      color: colors.background,
                      borderRadius: DS.borderRadius6,
                    ),
                    child: Icon(
                      _getRarityIcon(element.rarity),
                      size: 10,
                      color: colors.text,
                    ),
                  ),
                ],
              ),
            ),

            // 装备状态
            if (element.isEquipped)
              Positioned(
                top: DS.spacing8,
                right: DS.spacing8,
                child: Container(
                  padding: const EdgeInsets.all(DS.spacing4),
                  decoration: BoxDecoration(
                    color: DS.success,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.check,
                    size: 12,
                    color: Colors.white,
                  ),
                ),
              ),

            // 锁定遮罩
            if (!element.isUnlocked)
              Positioned.fill(
                child: Container(
                  decoration: BoxDecoration(
                    color: DS.surfacePrimary.withValues(alpha: 0.7),
                    borderRadius: DS.borderRadius16,
                  ),
                  child: Center(
                    child: Icon(
                      Icons.lock,
                      size: DS.iconSizeMd,
                      color: DS.textTertiary,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  _RarityColors _getRarityColors(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return _RarityColors(
          background: DS.rarityCommonBg,
          border: DS.rarityCommon,
          text: DS.rarityCommonText,
        );
      case VisualElementRarity.rare:
        return _RarityColors(
          background: DS.rarityRareBg,
          border: DS.rarityRare,
          text: DS.rarityRareText,
        );
      case VisualElementRarity.epic:
        return _RarityColors(
          background: DS.rarityEpicBg,
          border: DS.rarityEpic,
          text: DS.rarityEpicText,
        );
      case VisualElementRarity.legendary:
        return _RarityColors(
          background: DS.rarityLegendaryBg,
          border: DS.rarityLegendary,
          text: DS.rarityLegendaryText,
        );
    }
  }

  IconData _getTypeIcon(VisualElementType type) {
    switch (type) {
      case VisualElementType.background:
        return Icons.gradient;
      case VisualElementType.particle:
        return Icons.auto_awesome;
      case VisualElementType.effect:
        return Icons.blur_on;
      case VisualElementType.bundle:
        return Icons.inventory_2;
    }
  }

  IconData _getRarityIcon(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return Icons.circle_outlined;
      case VisualElementRarity.rare:
        return Icons.star_border;
      case VisualElementRarity.epic:
        return Icons.auto_awesome;
      case VisualElementRarity.legendary:
        return Icons.diamond_outlined;
    }
  }
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({
    required this.element,
    required this.reason,
    required this.reasonText,
    this.onTap,
    this.onEquip,
  });

  final VisualElementModel element;
  final VisualRecommendationReason reason;
  final String reasonText;
  final VoidCallback? onTap;
  final VoidCallback? onEquip;

  @override
  Widget build(BuildContext context) {
    final colors = _getRarityColors(element.rarity);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          border: Border.all(
            color: DS.brandPrimary.withValues(alpha: 0.3),
          ),
        ),
        child: Stack(
          children: [
            Padding(
              padding: const EdgeInsets.all(DS.spacing12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing8,
                      vertical: DS.spacing4,
                    ),
                    decoration: BoxDecoration(
                      color: DS.brandPrimary.withValues(alpha: 0.12),
                      borderRadius: DS.borderRadius8,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          _reasonIcon(reason),
                          size: DS.iconSizeXs,
                          color: DS.brandPrimary,
                        ),
                        const SizedBox(width: DS.spacing4),
                        Text(
                          reasonText,
                          style: TextStyle(
                            fontSize: DS.fontSizeXs,
                            color: DS.brandPrimary,
                            fontWeight: DS.fontWeightMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  Expanded(
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        element.name,
                        style: const TextStyle(
                          fontSize: DS.fontSizeSm,
                          fontWeight: DS.fontWeightSemibold,
                          color: DS.textPrimary,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing6,
                          vertical: DS.spacing2,
                        ),
                        decoration: BoxDecoration(
                          color: colors.background,
                          borderRadius: DS.borderRadius6,
                        ),
                        child: Icon(
                          _getRarityIcon(element.rarity),
                          size: 10,
                          color: colors.text,
                        ),
                      ),
                      const Spacer(),
                      if (onEquip != null)
                        GestureDetector(
                          onTap: onEquip,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: DS.spacing8,
                              vertical: DS.spacing4,
                            ),
                            decoration: BoxDecoration(
                              color: DS.brandPrimary,
                              borderRadius: DS.borderRadius8,
                            ),
                            child: Text(
                              context.l10n.visualElementEquip,
                              style: TextStyle(
                                fontSize: DS.fontSizeXs,
                                color: DS.textOnPrimary,
                                fontWeight: DS.fontWeightMedium,
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            if (!element.isUnlocked)
              Positioned.fill(
                child: Container(
                  decoration: BoxDecoration(
                    color: DS.surfacePrimary.withValues(alpha: 0.75),
                    borderRadius: DS.borderRadius16,
                  ),
                  child: Center(
                    child: Icon(
                      Icons.lock,
                      size: DS.iconSizeMd,
                      color: DS.textTertiary,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  _RarityColors _getRarityColors(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return _RarityColors(
          background: DS.rarityCommonBg,
          border: DS.rarityCommon,
          text: DS.rarityCommonText,
        );
      case VisualElementRarity.rare:
        return _RarityColors(
          background: DS.rarityRareBg,
          border: DS.rarityRare,
          text: DS.rarityRareText,
        );
      case VisualElementRarity.epic:
        return _RarityColors(
          background: DS.rarityEpicBg,
          border: DS.rarityEpic,
          text: DS.rarityEpicText,
        );
      case VisualElementRarity.legendary:
        return _RarityColors(
          background: DS.rarityLegendaryBg,
          border: DS.rarityLegendary,
          text: DS.rarityLegendaryText,
        );
    }
  }

  IconData _getRarityIcon(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return Icons.circle_outlined;
      case VisualElementRarity.rare:
        return Icons.star_border;
      case VisualElementRarity.epic:
        return Icons.auto_awesome;
      case VisualElementRarity.legendary:
        return Icons.diamond_outlined;
    }
  }

  IconData _reasonIcon(VisualRecommendationReason reason) {
    switch (reason) {
      case VisualRecommendationReason.focus:
        return Icons.center_focus_strong;
      case VisualRecommendationReason.relax:
        return Icons.spa;
      case VisualRecommendationReason.sprint:
        return Icons.bolt;
      case VisualRecommendationReason.night:
        return Icons.nights_stay;
      case VisualRecommendationReason.streak:
        return Icons.local_fire_department;
    }
  }
}

class _RarityColors {
  _RarityColors({
    required this.background,
    required this.border,
    required this.text,
  });

  final Color background;
  final Color border;
  final Color text;
}
