import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/visual_elements/domain/services/visual_recommendation_service.dart';
import 'package:sparkle/features/visual_elements/presentation/providers/visual_elements_provider.dart';
import 'package:sparkle/features/visual_elements/presentation/providers/visual_recommendation_provider.dart';
import 'package:sparkle/features/visual_elements/presentation/shared/visual_element_palette.dart';
import 'package:sparkle/features/visual_elements/presentation/widgets/visual_element_card.dart';
import 'package:sparkle/features/visual_elements/presentation/widgets/visual_element_preview_dialog.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

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
  VisualElementFilterOptions _filterOptions =
      const VisualElementFilterOptions();

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

  void _applyDisplaySlotFilter(String displaySlot) {
    final nextOptions = _filterOptions.copyWith(
      displaySlot: displaySlot,
      showUnlockedOnly: false,
      sortBy: VisualElementSortBy.prestige,
    );
    setState(() => _filterOptions = nextOptions);
    ref.read(visualElementsNotifierProvider.notifier).setFilterOptions(
          nextOptions,
        );
    if (_tabController.index == 0) {
      _tabController.animateTo(1);
    }
  }

  void _clearDisplaySlotFilter() {
    final nextOptions = _filterOptions.copyWith(clearDisplaySlot: true);
    setState(() => _filterOptions = nextOptions);
    ref.read(visualElementsNotifierProvider.notifier).setFilterOptions(
          nextOptions,
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
    final palette = VisualElementPalette.of(context);
    final eventElements = state.allElements
        .where(
          (element) => element.unlockSource == VisualElementUnlockSource.event,
        )
        .toList();

    return SliverToBoxAdapter(
      child: Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          gradient: palette.pageHeaderGradient,
          boxShadow: [
            BoxShadow(
              color: palette.cyan.withValues(alpha: 0.08),
              blurRadius: 28,
              offset: const Offset(0, 14),
            ),
          ],
        ),
        child: SafeArea(
          bottom: false,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 导航栏
              Row(
                children: [
                  SparkleIconButton(
                    icon: const Icon(Icons.arrow_back),
                    onPressed: () => context.canPop()
                        ? context.pop()
                        : context.go('/profile/settings'),
                    variant: ButtonVariant.ghost,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      l10n.visualElementsTitle,
                      style: TextStyle(
                        fontSize: DS.fontSizeXl,
                        fontWeight: DS.fontWeightBold,
                        color: palette.textPrimary,
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

              const SizedBox(height: DS.spacing12),

              // 统计面板
              _buildStatsPanel(context, state.stats, l10n),

              if (eventElements.isNotEmpty) ...[
                const SizedBox(height: DS.spacing12),
                _buildEventSection(eventElements, state, l10n),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatsPanel(
    BuildContext context,
    VisualElementStats stats,
    AppLocalizations l10n,
  ) {
    final palette = VisualElementPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        gradient: palette.panelGradient,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: palette.hairline),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.28),
            blurRadius: 28,
            offset: const Offset(0, 16),
          ),
        ],
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 360;
          final progressWidth = compact
              ? constraints.maxWidth
              : math.max(0.0, constraints.maxWidth - 108);
          final equippedWidth = compact ? constraints.maxWidth : 96.0;

          return Wrap(
            spacing: DS.spacing12,
            runSpacing: DS.spacing12,
            children: [
              SizedBox(
                width: progressWidth,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.visualElementsUnlockProgress,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: DS.fontSizeSm,
                        color: palette.textSecondary,
                      ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    ClipRRect(
                      borderRadius: DS.borderRadius8,
                      child: LinearProgressIndicator(
                        value: stats.unlockProgress,
                        backgroundColor:
                            palette.textPrimary.withValues(alpha: 0.08),
                        valueColor: AlwaysStoppedAnimation(palette.gold),
                        minHeight: 8,
                      ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    Text(
                      '${stats.unlockedCount}/${stats.totalCount}',
                      style: TextStyle(
                        fontSize: DS.fontSizeSm,
                        fontWeight: DS.fontWeightMedium,
                        color: palette.textPrimary,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                width: equippedWidth,
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing12,
                  vertical: DS.spacing12,
                ),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      palette.gold.withValues(alpha: 0.18),
                      palette.cyan.withValues(alpha: 0.08),
                    ],
                  ),
                  borderRadius: DS.borderRadius12,
                  border: Border.all(
                    color: palette.gold.withValues(alpha: 0.32),
                  ),
                ),
                child: Column(
                  children: [
                    Icon(
                      Icons.check_circle,
                      color: palette.gold,
                      size: DS.iconSizeMd,
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      '${stats.equippedCount}',
                      style: TextStyle(
                        fontSize: DS.fontSizeLg,
                        fontWeight: DS.fontWeightBold,
                        color: palette.textPrimary,
                      ),
                    ),
                    Text(
                      l10n.visualElementsEquipped,
                      textAlign: TextAlign.center,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: palette.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildCurrentShowcase(VisualElementsState state) {
    final palette = VisualElementPalette.of(context);
    final equipped = [
      state.config?.equippedBackground,
      state.config?.equippedParticle,
      state.config?.equippedEffect,
    ].whereType<VisualElementModel>().toList();

    if (equipped.isEmpty) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: palette.panel,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: palette.hairline),
        ),
        child: Text(
          context.l10n.visualPrestigeEmpty,
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            color: palette.textSecondary,
          ),
        ),
      );
    }

    final primary = equipped.first;
    final title = equipped
        .map((element) => element.prestigeLabel ?? element.name)
        .join(' · ');
    final setName = equipped
        .map((element) => element.setId)
        .whereType<String>()
        .fold<Map<String, int>>({}, (acc, setId) {
          acc[setId] = (acc[setId] ?? 0) + 1;
          return acc;
        })
        .entries
        .toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            _elementAccent(primary).withValues(alpha: 0.28),
            palette.panel,
            palette.surface,
          ],
        ),
        borderRadius: DS.borderRadius16,
        border:
            Border.all(color: _elementAccent(primary).withValues(alpha: 0.34)),
        boxShadow: [
          BoxShadow(
            color: _elementAccent(primary).withValues(alpha: 0.14),
            blurRadius: 26,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.visualCurrentPrestigeSet,
            style: TextStyle(
              fontSize: DS.fontSizeBase,
              fontWeight: DS.fontWeightBold,
              color: palette.textPrimary,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            setName.isNotEmpty
                ? setName.first.key
                : context.l10n.visualMixMatch,
            style: TextStyle(
              fontSize: DS.fontSizeLg,
              fontWeight: DS.fontWeightBold,
              color: _elementAccent(primary),
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            title,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: palette.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPrestigeSetShowcase(VisualElementsState state) {
    final bundles = state.allElements
        .where((element) => element.isBundle)
        .toList()
      ..sort((a, b) => b.visibilityWeight.compareTo(a.visibilityWeight));

    if (bundles.isEmpty) {
      return const SizedBox.shrink();
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 340) {
          return const SizedBox.shrink();
        }
        final cardWidth = _horizontalShowcaseCardWidth(constraints.maxWidth);
        final compact = constraints.maxWidth < 360;
        final cardHeight = compact ? 268.0 : 128.0;
        final palette = VisualElementPalette.of(context);

        return SizedBox(
          height: cardHeight,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: bundles.length > 6 ? 6 : bundles.length,
            separatorBuilder: (_, __) => const SizedBox(width: DS.spacing12),
            itemBuilder: (context, index) {
              final element = bundles[index];
              final isUnlocked = state.unlockedIds.contains(element.id);
              final isEquipped = _isElementEquipped(element, state);
              final ownedCount = _bundleOwnedCount(element, state);
              final totalCount = _bundleTotalCount(element);
              return GestureDetector(
                onTap: () => _showElementPreview(
                  element,
                  isUnlocked,
                  isEquipped,
                ),
                child: Container(
                  width: cardWidth,
                  padding:
                      EdgeInsets.all(compact ? DS.spacing12 : DS.spacing16),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        _elementAccent(element).withValues(alpha: 0.22),
                        palette.panel,
                        palette.surface,
                      ],
                    ),
                    borderRadius: DS.borderRadius16,
                    border: Border.all(
                      color: _elementAccent(element).withValues(alpha: 0.34),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: _elementAccent(element).withValues(alpha: 0.10),
                        blurRadius: 22,
                        offset: const Offset(0, 12),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: DS.spacing6,
                        runSpacing: DS.spacing6,
                        children: [
                          _miniChip(
                            element.prestigeLabel ?? element.name,
                            _elementAccent(element),
                          ),
                          _miniChip(
                            isUnlocked
                                ? context.l10n.visualUnlocked
                                : context.l10n.visualLocked,
                            isUnlocked ? DS.success : DS.warning,
                          ),
                          if (totalCount > 0)
                            _miniChip(
                              context.l10n
                                  .visualCollectedCount(ownedCount, totalCount),
                              ownedCount == totalCount ? DS.success : DS.info,
                            ),
                        ],
                      ),
                      if (!compact) const Spacer(),
                      Text(
                        element.name,
                        style: TextStyle(
                          fontSize: DS.fontSizeBase,
                          fontWeight: DS.fontWeightBold,
                          color: palette.textPrimary,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        element.description ?? context.l10n.visualHighExposure,
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: palette.textSecondary,
                        ),
                        maxLines: compact ? 3 : 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        );
      },
    );
  }

  Widget _miniChip(String label, Color color) => Container(
        constraints: const BoxConstraints(maxWidth: 156),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: DS.borderRadius12,
          border: Border.all(color: color.withValues(alpha: 0.24)),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: Color.lerp(
              color,
              VisualElementPalette.of(context).textPrimary,
              0.18,
            ),
            fontWeight: DS.fontWeightMedium,
          ),
        ),
      );

  Color _elementAccent(VisualElementModel element) {
    final gradientConfig = element.config['gradient'];
    final gradient = gradientConfig is List<dynamic>
        ? gradientConfig
        : gradientConfig is Map<String, dynamic>
            ? gradientConfig['colors'] as List<dynamic>?
            : null;
    final colors = element.config['colors'] as List<dynamic>?;
    final aurora = element.config['aurora_colors'] as List<dynamic>?;
    final nebula = element.config['nebula_colors'] as List<dynamic>?;
    final neon = element.config['neon_colors'] as List<dynamic>?;
    final raw = (aurora != null && aurora.isNotEmpty)
        ? aurora.first
        : (nebula != null && nebula.isNotEmpty)
            ? nebula.first
            : (neon != null && neon.isNotEmpty)
                ? neon.first
                : (colors != null && colors.isNotEmpty)
                    ? colors.first
                    : (gradient != null && gradient.isNotEmpty
                        ? gradient.last
                        : '#8FB8C8');
    final hex = raw.toString().replaceFirst('#', '');
    final normalized = hex.length == 6 ? 'FF$hex' : hex;
    final value = int.tryParse(normalized, radix: 16);
    return value == null ? VisualElementPalette.of(context).cyan : Color(value);
  }

  Widget _buildTabBar(BuildContext context, AppLocalizations l10n) {
    final palette = VisualElementPalette.of(context);
    final compact = MediaQuery.sizeOf(context).width < 360;
    return SliverPersistentHeader(
      pinned: true,
      delegate: _StickyTabBarDelegate(
        TabBar(
          controller: _tabController,
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          indicatorSize: TabBarIndicatorSize.label,
          indicator: BoxDecoration(
            color: palette.gold.withValues(alpha: 0.92),
            borderRadius: DS.borderRadius8,
            boxShadow: [
              BoxShadow(
                color: palette.gold.withValues(alpha: 0.18),
                blurRadius: 16,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          indicatorPadding: const EdgeInsets.symmetric(vertical: DS.spacing8),
          labelColor: palette.moonless,
          unselectedLabelColor: palette.textSecondary,
          labelStyle: const TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightMedium,
          ),
          labelPadding: const EdgeInsets.symmetric(horizontal: DS.spacing10),
          tabs: [
            compact
                ? Tab(text: l10n.visualElementsRecommended)
                : Tab(
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
      return const SparkleListSkeleton();
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
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing16,
                DS.spacing16,
                DS.spacing16,
                0,
              ),
              child: Column(
                children: [
                  _buildCurrentShowcase(state),
                  const SizedBox(height: DS.spacing12),
                  _buildPrestigeSetShowcase(state),
                  const SizedBox(height: DS.spacing12),
                  _buildStyleRunway(state),
                  if (state.filterOptions.displaySlot != null) ...[
                    const SizedBox(height: DS.spacing12),
                    _buildActiveDisplaySlotFilter(state),
                  ],
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.all(DS.spacing16),
            sliver: SliverLayoutBuilder(
              builder: (context, constraints) {
                if (constraints.crossAxisExtent < 360) {
                  return SliverList.separated(
                    itemCount: filteredElements.length,
                    itemBuilder: (context, index) {
                      final element = filteredElements[index];
                      return _buildElementCard(element, state);
                    },
                    separatorBuilder: (_, __) =>
                        const SizedBox(height: DS.spacing12),
                  );
                }
                return SliverGrid(
                  key: ValueKey(_filterOptions.hashCode),
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: _calculateCrossAxisCount(
                      constraints.crossAxisExtent,
                    ),
                    mainAxisSpacing: DS.spacing12,
                    crossAxisSpacing: DS.spacing12,
                    mainAxisExtent: _gridMainAxisExtent(
                      constraints.crossAxisExtent,
                    ),
                  ),
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final element = filteredElements[index];
                      return _buildElementCard(element, state);
                    },
                    childCount: filteredElements.length,
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
  ) {
    final isUnlocked = state.unlockedIds.contains(element.id);
    final isEquipped = _isElementEquipped(element, state);
    final bundleOwnedCount = _bundleOwnedCount(element, state);
    final bundleTotalCount = _bundleTotalCount(element);
    final resolvedElement = element.copyWith(
      isUnlocked: isUnlocked,
      isEquipped: isEquipped,
    );

    return _VisualElementCard(
      element: resolvedElement,
      bundleOwnedCount: bundleOwnedCount,
      bundleTotalCount: bundleTotalCount,
      onTap: () => _showElementPreview(element, isUnlocked, isEquipped),
      onLongPress:
          isUnlocked && !isEquipped ? () => _equipElement(element.id) : null,
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
      availableElements: ref.read(visualElementsNotifierProvider).allElements,
      baseConfig: ref.read(visualElementsNotifierProvider).config,
      unlockedElementIds: ref.read(visualElementsNotifierProvider).unlockedIds,
      isUnlocked: isUnlocked,
      isEquipped: isEquipped,
      onEquip: isUnlocked
          ? () => element.isBundle
              ? _equipBundle(element)
              : _equipElement(element.id)
          : null,
      onUnequip: isEquipped
          ? () => element.isBundle
              ? _unequipBundle(element)
              : _unequipElement(element.elementType)
          : null,
    );
  }

  bool _isElementEquipped(
          VisualElementModel element, VisualElementsState state) =>
      element.matchesConfig(state.config);

  int _bundleOwnedCount(
    VisualElementModel element,
    VisualElementsState state,
  ) {
    if (!element.isBundle) return 0;
    return element.bundlePieceIds
        .where((pieceId) => state.unlockedIds.contains(pieceId))
        .length;
  }

  int _bundleTotalCount(VisualElementModel element) =>
      element.isBundle ? element.bundlePieceIds.length : 0;

  Future<void> _equipElement(String elementId) async {
    final notifier = ref.read(visualElementsNotifierProvider.notifier);
    final success = await notifier.equipElement(elementId);

    if (mounted) {
      if (success) {
        AppFeedback.success(context, context.l10n.visualElementEquipSuccess);
      } else {
        AppFeedback.error(context, context.l10n.visualElementEquipFailed);
      }
    }
  }

  Future<void> _unequipElement(VisualElementType type) async {
    final notifier = ref.read(visualElementsNotifierProvider.notifier);
    final success = await notifier.unequipElement(type);

    if (mounted) {
      if (success) {
        AppFeedback.info(context, context.l10n.visualElementUnequipSuccess);
      } else {
        AppFeedback.error(context, context.l10n.visualElementUnequipFailed);
      }
    }
  }

  Future<void> _equipBundle(VisualElementModel bundle) async {
    final notifier = ref.read(visualElementsNotifierProvider.notifier);
    final state = ref.read(visualElementsNotifierProvider);
    final unlockedIds = state.unlockedIds;
    final pieces = bundle.bundlePieceIds
        .where((pieceId) => unlockedIds.contains(pieceId))
        .toList();

    if (pieces.isEmpty) {
      if (mounted) {
        AppFeedback.warning(context, context.l10n.visualBundleIncomplete);
      }
      return;
    }

    final results = <bool>[];
    for (final pieceId in pieces) {
      results.add(await notifier.equipElement(pieceId));
    }
    final success = results.isNotEmpty && results.every((result) => result);

    if (mounted) {
      if (success) {
        AppFeedback.success(context, context.l10n.visualBundleEquipped);
      } else {
        AppFeedback.error(context, context.l10n.visualEquipFailed);
      }
    }
  }

  Future<void> _unequipBundle(VisualElementModel bundle) async {
    final notifier = ref.read(visualElementsNotifierProvider.notifier);
    final tasks = <Future<bool>>[];

    if (bundle.bundleBackgroundId != null) {
      tasks.add(notifier.unequipElement(VisualElementType.background));
    }
    if (bundle.bundleParticleId != null) {
      tasks.add(notifier.unequipElement(VisualElementType.particle));
    }
    if (bundle.bundleEffectId != null) {
      tasks.add(notifier.unequipElement(VisualElementType.effect));
    }

    final results = await Future.wait(tasks);
    final success = results.every((result) => result);

    if (mounted) {
      if (success) {
        AppFeedback.info(context, context.l10n.visualBundleUnequipped);
      } else {
        AppFeedback.error(context, context.l10n.visualUnequipFailed);
      }
    }
  }

  Widget _buildErrorView(String error, AppLocalizations l10n) => Center(
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

  Widget _buildEmptyView(AppLocalizations l10n) => Center(
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

  Widget _buildRecommendationBody(
    BuildContext context,
    AppLocalizations l10n,
    VisualElementsState state,
    AsyncValue<List<VisualRecommendation>> recommendationsValue,
  ) =>
      recommendationsValue.when(
        data: (recommendations) {
          if (recommendations.isEmpty) {
            return _buildEmptyView(l10n);
          }

          return RefreshIndicator(
            onRefresh: () =>
                ref.read(visualElementsNotifierProvider.notifier).refresh(),
            child: CustomScrollView(
              slivers: [
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(
                      DS.spacing16,
                      DS.spacing16,
                      DS.spacing16,
                      0,
                    ),
                    child: Column(
                      children: [
                        _buildCurrentShowcase(state),
                        const SizedBox(height: DS.spacing12),
                        _buildStyleRunway(state),
                        if (state.filterOptions.displaySlot != null) ...[
                          const SizedBox(height: DS.spacing12),
                          _buildActiveDisplaySlotFilter(state),
                        ],
                      ],
                    ),
                  ),
                ),
                SliverPadding(
                  padding: const EdgeInsets.all(DS.spacing16),
                  sliver: SliverGrid(
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: _calculateCrossAxisCount(
                        MediaQuery.of(context).size.width,
                      ),
                      mainAxisSpacing: DS.spacing12,
                      crossAxisSpacing: DS.spacing12,
                      mainAxisExtent: _recommendationMainAxisExtent(
                        MediaQuery.of(context).size.width,
                      ),
                    ),
                    delegate: SliverChildBuilderDelegate(
                      (context, index) {
                        final recommendation = recommendations[index];
                        final element = recommendation.element;
                        final isUnlocked =
                            state.unlockedIds.contains(element.id);
                        final isEquipped = _isElementEquipped(element, state);
                        final bundleOwnedCount = _bundleOwnedCount(
                          element,
                          state,
                        );
                        final bundleTotalCount = _bundleTotalCount(element);
                        final resolvedElement = element.copyWith(
                          isUnlocked: isUnlocked,
                          isEquipped: isEquipped,
                        );

                        return _RecommendationCard(
                          element: resolvedElement,
                          bundleOwnedCount: bundleOwnedCount,
                          bundleTotalCount: bundleTotalCount,
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
        loading: () => const SparkleListSkeleton(),
        error: (err, _) => _buildErrorView(err.toString(), l10n),
      );

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
    showSensoryModalBottomSheet<void>(
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
    final palette = VisualElementPalette.of(context);
    final endAt = _getEventEndAt(eventElements);
    final countdownText =
        endAt == null ? null : _formatEventCountdown(endAt, l10n);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            palette.gold.withValues(alpha: 0.18),
            palette.cyan.withValues(alpha: 0.10),
            palette.panel,
          ],
        ),
        borderRadius: DS.borderRadius16,
        border: Border.all(color: palette.gold.withValues(alpha: 0.34)),
        boxShadow: [
          BoxShadow(
            color: palette.gold.withValues(alpha: 0.10),
            blurRadius: 24,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.timer_outlined,
                color: palette.gold,
                size: DS.iconSizeSm,
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  l10n.visualElementEventTitle,
                  style: TextStyle(
                    fontSize: DS.fontSizeBase,
                    fontWeight: DS.fontWeightBold,
                    color: palette.textPrimary,
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
                    color: palette.moonless.withValues(alpha: 0.58),
                    borderRadius: DS.borderRadius8,
                    border: Border.all(
                      color: palette.gold.withValues(alpha: 0.20),
                    ),
                  ),
                  child: Text(
                    countdownText,
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: palette.textSecondary,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          LayoutBuilder(
            builder: (context, constraints) {
              final cardWidth = math.min(
                math.max(160.0, constraints.maxWidth * 0.52),
                192.0,
              );
              final compact = constraints.maxWidth < 360;

              return SizedBox(
                height: compact ? 196 : 184,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: eventElements.length,
                  separatorBuilder: (_, __) =>
                      const SizedBox(width: DS.spacing12),
                  itemBuilder: (context, index) {
                    final element = eventElements[index];
                    final resolvedElement = element.copyWith(
                      isUnlocked: state.unlockedIds.contains(element.id),
                      isEquipped: _isElementEquipped(element, state),
                    );
                    return SizedBox(
                      width: cardWidth,
                      child: _VisualElementCard(
                        element: resolvedElement,
                        onTap: () => _showElementPreview(
                          element,
                          state.unlockedIds.contains(element.id),
                          _isElementEquipped(element, state),
                        ),
                      ),
                    );
                  },
                ),
              );
            },
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

  Widget _buildStyleRunway(VisualElementsState state) {
    final bySlot = <String, List<VisualElementModel>>{};
    for (final element in state.allElements) {
      bySlot.putIfAbsent(element.displaySlot, () => []).add(element);
    }

    final entries = bySlot.entries.toList()
      ..sort((a, b) => b.value.length.compareTo(a.value.length));

    if (entries.isEmpty) {
      return const SizedBox.shrink();
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final cardWidth = _horizontalShowcaseCardWidth(constraints.maxWidth);
        final compact = constraints.maxWidth < 360;

        if (compact) {
          final visibleEntries = entries.take(3).toList(growable: false);
          return Column(
            children: [
              for (var index = 0; index < visibleEntries.length; index++) ...[
                _buildCompactRunwayCard(visibleEntries[index], state),
                if (index != visibleEntries.length - 1)
                  const SizedBox(height: DS.spacing12),
              ],
            ],
          );
        }

        return SizedBox(
          height: compact ? 190 : 140,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: entries.length,
            separatorBuilder: (_, __) => const SizedBox(width: DS.spacing12),
            itemBuilder: (context, index) {
              final entry = entries[index];
              final elements = [...entry.value]..sort(
                  (a, b) => b.visibilityWeight.compareTo(a.visibilityWeight),
                );
              final lead = elements.first;
              final unlockedCount = elements
                  .where((element) => state.unlockedIds.contains(element.id))
                  .length;
              final accent = _elementAccent(lead);
              final palette = VisualElementPalette.of(context);

              return GestureDetector(
                onTap: () => _applyDisplaySlotFilter(lead.displaySlot),
                child: Container(
                  width: cardWidth,
                  padding:
                      EdgeInsets.all(compact ? DS.spacing12 : DS.spacing16),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        accent.withValues(alpha: 0.22),
                        palette.panel,
                        palette.surface,
                      ],
                    ),
                    borderRadius: DS.borderRadius16,
                    border: Border.all(color: accent.withValues(alpha: 0.30)),
                    boxShadow: [
                      BoxShadow(
                        color: accent.withValues(alpha: 0.08),
                        blurRadius: 20,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _miniChip(lead.displaySlotLabel, accent),
                      if (!compact)
                        const Spacer()
                      else
                        const SizedBox(height: DS.spacing8),
                      Text(
                        context.l10n.visualStyleCount(elements.length),
                        style: TextStyle(
                          fontSize: DS.fontSizeLg,
                          fontWeight: DS.fontWeightBold,
                          color: palette.textPrimary,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        context.l10n
                            .visualOwnedCount(unlockedCount, elements.length),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: DS.fontSizeSm,
                          color: palette.textSecondary,
                        ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      Text(
                        elements
                            .take(2)
                            .map((element) => element.name)
                            .join(' · '),
                        maxLines: compact ? 2 : 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: accent,
                          fontWeight: DS.fontWeightMedium,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        );
      },
    );
  }

  Widget _buildCompactRunwayCard(
    MapEntry<String, List<VisualElementModel>> entry,
    VisualElementsState state,
  ) {
    final elements = [...entry.value]
      ..sort((a, b) => b.visibilityWeight.compareTo(a.visibilityWeight));
    final lead = elements.first;
    final unlockedCount = elements
        .where((element) => state.unlockedIds.contains(element.id))
        .length;
    final accent = _elementAccent(lead);
    final palette = VisualElementPalette.of(context);

    return GestureDetector(
      onTap: () => _applyDisplaySlotFilter(lead.displaySlot),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              accent.withValues(alpha: 0.16),
              palette.panel,
              palette.surface,
            ],
          ),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: accent.withValues(alpha: 0.30)),
          boxShadow: [
            BoxShadow(
              color: accent.withValues(alpha: 0.08),
              blurRadius: 18,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _miniChip(lead.displaySlotLabel, accent),
            const SizedBox(height: DS.spacing10),
            Text(
              context.l10n.visualStyleCount(elements.length),
              style: TextStyle(
                fontSize: DS.fontSizeBase,
                fontWeight: DS.fontWeightBold,
                color: palette.textPrimary,
              ),
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              context.l10n.visualOwnedCount(unlockedCount, elements.length),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: palette.textSecondary,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              elements.take(2).map((element) => element.name).join(' · '),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: accent,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActiveDisplaySlotFilter(VisualElementsState state) {
    final slot = state.filterOptions.displaySlot;
    if (slot == null) {
      return const SizedBox.shrink();
    }

    final label = _displaySlotLabel(slot);
    final matchedCount = state.filteredElements.length;

    return Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: VisualElementPalette.of(context).cyan.withValues(alpha: 0.08),
        borderRadius: DS.borderRadius16,
        border: Border.all(
          color: VisualElementPalette.of(context).cyan.withValues(alpha: 0.22),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final stack = constraints.maxWidth < 360;
          final info = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.visualCurrentView(label),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  fontWeight: DS.fontWeightBold,
                  color: VisualElementPalette.of(context).textPrimary,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                context.l10n.visualSlotSwitched(matchedCount),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: VisualElementPalette.of(context).textSecondary,
                ),
              ),
            ],
          );
          final clearButton = TextButton(
            onPressed: _clearDisplaySlotFilter,
            child: Text(context.l10n.visualClearFilter),
          );

          if (stack) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                info,
                const SizedBox(height: DS.spacing8),
                clearButton,
              ],
            );
          }

          return Row(
            children: [
              Expanded(child: info),
              const SizedBox(width: DS.spacing12),
              clearButton,
            ],
          );
        },
      ),
    );
  }

  double _gridMainAxisExtent(double width) {
    final crossAxisCount = _calculateCrossAxisCount(width);
    if (crossAxisCount == 1) return 360;
    if (crossAxisCount == 2) return 236;
    if (crossAxisCount == 3) return 224;
    return 216;
  }

  double _recommendationMainAxisExtent(double width) {
    final crossAxisCount = _calculateCrossAxisCount(width);
    if (crossAxisCount == 1) return 380;
    if (crossAxisCount == 2) return 252;
    if (crossAxisCount == 3) return 236;
    return 228;
  }

  double _horizontalShowcaseCardWidth(double width) =>
      math.min(math.max(196.0, width * 0.68), 232.0);

  String _displaySlotLabel(String slot) {
    final l = context.l10n;
    switch (slot) {
      case 'avatar_border':
        return l.visualSlotAvatarBorder;
      case 'title_bar':
        return l.visualSlotTitleBar;
      case 'profile_banner':
        return l.visualSlotProfileBanner;
      case 'achievement_frame':
        return l.visualSlotAchievementFrame;
      case 'home_ambience':
        return l.visualSlotHomeAmbience;
      case 'star_map_effect':
        return l.visualSlotStarMapEffect;
      case 'streak_flame':
        return l.visualSlotStreakFlame;
      case 'display_pedestal':
        return l.visualSlotDisplayPedestal;
      case 'background':
        return l.visualSlotBackground;
      case 'particle':
        return l.visualSlotParticle;
      case 'effect':
        return l.visualSlotEffect;
      case 'bundle':
        return l.visualSlotBundle;
      default:
        return slot;
    }
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
  ) =>
      Container(
        color: VisualElementPalette.of(context).surface,
        child: tabBar,
      );

  @override
  bool shouldRebuild(_StickyTabBarDelegate oldDelegate) =>
      tabBar != oldDelegate.tabBar;
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

  Widget _buildStatusFilter(AppLocalizations l10n) => Column(
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

  Widget _buildSortFilter(AppLocalizations l10n) => Column(
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
                AppLocalizations.of(context)!.visualSortPrestige,
                _options.sortBy == VisualElementSortBy.prestige,
                onTap: () {
                  setState(() {
                    _options = _options.copyWith(
                      sortBy: VisualElementSortBy.prestige,
                    );
                  });
                },
              ),
              _buildFilterChip(
                AppLocalizations.of(context)!.visualSortBySet,
                _options.sortBy == VisualElementSortBy.set,
                onTap: () {
                  setState(() {
                    _options = _options.copyWith(
                      sortBy: VisualElementSortBy.set,
                    );
                  });
                },
              ),
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
    this.bundleOwnedCount = 0,
    this.bundleTotalCount = 0,
  });

  final VisualElementModel element;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final int bundleOwnedCount;
  final int bundleTotalCount;

  @override
  Widget build(BuildContext context) => VisualElementCard(
        element: element,
        onTap: onTap,
        onLongPress: onLongPress,
        isCompact: true,
        bundleOwnedCount: bundleOwnedCount,
        bundleTotalCount: bundleTotalCount,
      );
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({
    required this.element,
    required this.reason,
    required this.reasonText,
    this.onTap,
    this.onEquip,
    this.bundleOwnedCount = 0,
    this.bundleTotalCount = 0,
  });

  final VisualElementModel element;
  final VisualRecommendationReason reason;
  final String reasonText;
  final VoidCallback? onTap;
  final VoidCallback? onEquip;
  final int bundleOwnedCount;
  final int bundleTotalCount;

  @override
  Widget build(BuildContext context) {
    final palette = VisualElementPalette.of(context);
    final colors = _getRarityColors(context, element.rarity);
    final actionLabel = element.isBundle
        ? AppLocalizations.of(context)!.visualOneClickEquip
        : context.l10n.visualElementEquip;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              colors.border.withValues(alpha: 0.18),
              palette.panel,
              palette.surface,
            ],
          ),
          borderRadius: DS.borderRadius16,
          border: Border.all(
            color: colors.border.withValues(alpha: 0.28),
          ),
          boxShadow: [
            BoxShadow(
              color: colors.border.withValues(alpha: 0.08),
              blurRadius: 18,
              offset: const Offset(0, 10),
            ),
          ],
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
                      color: colors.border.withValues(alpha: 0.13),
                      borderRadius: DS.borderRadius8,
                      border: Border.all(
                        color: colors.border.withValues(alpha: 0.22),
                      ),
                    ),
                    child: Wrap(
                      spacing: DS.spacing4,
                      runSpacing: DS.spacing4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Icon(
                          _reasonIcon(reason),
                          size: DS.iconSizeXs,
                          color: colors.text,
                        ),
                        Text(
                          reasonText,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: DS.fontSizeXs,
                            color: colors.text,
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
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            element.name,
                            style: TextStyle(
                              fontSize: DS.fontSizeSm,
                              fontWeight: DS.fontWeightSemibold,
                              color: palette.textPrimary,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: DS.spacing6),
                          Wrap(
                            spacing: DS.spacing6,
                            runSpacing: DS.spacing6,
                            children: [
                              if (element.prestigeLabel != null)
                                _miniInfoChip(
                                  context,
                                  element.prestigeLabel!,
                                  colors.border,
                                ),
                              _miniInfoChip(
                                context,
                                element.displaySlotLabel,
                                colors.text,
                              ),
                              if (element.isBundle && bundleTotalCount > 0)
                                _miniInfoChip(
                                  context,
                                  AppLocalizations.of(context)!
                                      .visualCollectedCount(
                                          bundleOwnedCount, bundleTotalCount),
                                  bundleOwnedCount == bundleTotalCount
                                      ? DS.success
                                      : DS.info,
                                ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Wrap(
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing8,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    alignment: WrapAlignment.spaceBetween,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing6,
                          vertical: DS.spacing2,
                        ),
                        decoration: BoxDecoration(
                          color: colors.background,
                          borderRadius: DS.borderRadius6,
                          border: Border.all(
                            color: colors.border.withValues(alpha: 0.28),
                          ),
                        ),
                        child: Icon(
                          _getRarityIcon(element.rarity),
                          size: 10,
                          color: colors.text,
                        ),
                      ),
                      if (onEquip != null)
                        GestureDetector(
                          onTap: onEquip,
                          child: Container(
                            constraints: const BoxConstraints(maxWidth: 108),
                            padding: const EdgeInsets.symmetric(
                              horizontal: DS.spacing8,
                              vertical: DS.spacing4,
                            ),
                            decoration: BoxDecoration(
                              color: palette.gold,
                              borderRadius: DS.borderRadius8,
                            ),
                            child: Text(
                              actionLabel,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: DS.fontSizeXs,
                                color: palette.moonless,
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
                child: IgnorePointer(
                  child: Container(
                    decoration: BoxDecoration(
                      color: palette.moonless.withValues(alpha: 0.76),
                      borderRadius: DS.borderRadius16,
                    ),
                    child: Center(
                      child: Icon(
                        Icons.lock,
                        size: DS.iconSizeMd,
                        color: palette.textSecondary,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  VisualElementRarityColors _getRarityColors(
    BuildContext context,
    VisualElementRarity rarity,
  ) =>
      VisualElementPalette.of(context).rarityColors(rarity);

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

  Widget _miniInfoChip(BuildContext context, String label, Color color) =>
      Container(
        constraints: const BoxConstraints(maxWidth: 112),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing6,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.13),
          borderRadius: DS.borderRadius8,
          border: Border.all(color: color.withValues(alpha: 0.22)),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: Color.lerp(
              color,
              VisualElementPalette.of(context).textPrimary,
              0.12,
            ),
            fontWeight: DS.fontWeightMedium,
          ),
        ),
      );
}
