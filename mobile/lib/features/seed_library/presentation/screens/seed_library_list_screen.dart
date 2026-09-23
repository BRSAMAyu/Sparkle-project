import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/design/widgets/scroll_edge_haptics.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/seed_library/presentation/widgets/seed_library_card.dart';
import 'package:sparkle/features/seed_library/seed_library_routes.dart';

/// Seed Library List Screen
/// Displays a list of seed libraries with filtering and search
class SeedLibraryListScreen extends ConsumerStatefulWidget {
  const SeedLibraryListScreen({super.key});

  @override
  ConsumerState<SeedLibraryListScreen> createState() =>
      _SeedLibraryListScreenState();
}

class _SeedLibraryListScreenState extends ConsumerState<SeedLibraryListScreen> {
  final TextEditingController _searchController = TextEditingController();
  LibraryCategory? _selectedCategory;
  LibraryVisibility? _selectedVisibility;
  bool _showOfficialOnly = false;
  bool _showFeaturedOnly = false;

  ({
    LibraryCategory? category,
    LibraryVisibility? visibility,
    bool? isOfficial,
    bool? isFeatured,
    String? search,
  }) get _currentParams => (
        category: _selectedCategory,
        isFeatured: _showFeaturedOnly ? true : null,
        isOfficial: _showOfficialOnly ? true : null,
        visibility: _selectedVisibility,
        search: _searchController.text.isEmpty ? null : _searchController.text,
      );

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _applyFilters() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    unawaited(
      ref.read(seedLibraryListProvider(_currentParams).notifier).refresh(
            category: _selectedCategory,
            visibility: _selectedVisibility,
            isOfficial: _showOfficialOnly ? true : null,
            isFeatured: _showFeaturedOnly ? true : null,
            search:
                _searchController.text.isEmpty ? null : _searchController.text,
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final params = _currentParams;
    final state = ref.watch(seedLibraryListProvider(params));
    final notifier = ref.read(seedLibraryListProvider(params).notifier);
    final hasActiveFilters = _selectedCategory != null ||
        _selectedVisibility != null ||
        _showOfficialOnly ||
        _showFeaturedOnly;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(context.l10n.seedLibraryTitle),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.storefront_outlined),
            onPressed: () =>
                unawaited(context.push(SeedLibraryRoutes.marketplace)),
          ),
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.refresh),
            onPressed: _applyFilters,
          ),
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: Icon(
              Icons.filter_list,
              color: hasActiveFilters
                  ? Theme.of(context).colorScheme.primary
                  : null,
            ),
            onPressed: _showFilterDialog,
          ),
        ],
      ),
      // FAB-UNIFY：组件已自带最大尺寸语义（fabGeometry 钉死方形几何，
      // 默认 56 方档=touchTargetMinSize+spacing8），急救 SizedBox 去重。
      floatingActionButton: SparkleIconButton.fabGeometry(
        onPressed: () async {
          unawaited(
            SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen),
          );
          final result = await context.push<bool>(
            SeedLibraryRoutes.createLibrary,
          );
          if (result ?? false) {
            _applyFilters();
          }
        },
        icon: const Icon(Icons.add),
      ),
      child: ContentConstraint(
        child: Column(
          children: [
            // Search bar
            Padding(
              padding: const EdgeInsets.all(DS.spacing16),
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.panel,
                padding: EdgeInsets.zero,
                child: TextField(
                  controller: _searchController,
                  decoration: InputDecoration(
                    hintText: context.l10n.seedLibrarySearchHint,
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _searchController.text.isNotEmpty
                        ? SparkleIconButton(
                            variant: ButtonVariant.ghost,
                            size: DS.spacing32,
                            icon: const Icon(Icons.clear),
                            onPressed: () {
                              _searchController.clear();
                              _applyFilters();
                            },
                          )
                        : null,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    filled: true,
                    fillColor: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
                  ),
                  onSubmitted: (_) {
                    // SEARCH-EMPTY：提交后先重建——_currentParams 携带新词
                    // 重算 family 键，否则 watch 仍停在旧参数实例上，
                    // 搜索结果与无结果专用态都不会渲染。
                    setState(() {});
                    _applyFilters();
                  },
                ),
              ),
            ),

            // Filter chips
            if (_selectedCategory != null ||
                _selectedVisibility != null ||
                _showOfficialOnly ||
                _showFeaturedOnly)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                child: Wrap(
                  spacing: DS.spacing8,
                  children: [
                    if (_selectedCategory != null)
                      Chip(
                        label: Text(_selectedCategory!.label(context.l10n)),
                        deleteIcon: const Icon(Icons.close, size: 18),
                        onDeleted: () {
                          setState(() {
                            _selectedCategory = null;
                          });
                          _applyFilters();
                        },
                      ),
                    if (_selectedVisibility != null)
                      Chip(
                        label: Text(_selectedVisibility!.label(context.l10n)),
                        deleteIcon: const Icon(Icons.close, size: 18),
                        onDeleted: () {
                          setState(() {
                            _selectedVisibility = null;
                          });
                          _applyFilters();
                        },
                      ),
                    if (_showOfficialOnly)
                      Chip(
                        label: Text(context.l10n.seedOfficialOnly),
                        deleteIcon: const Icon(Icons.close, size: 18),
                        onDeleted: () {
                          setState(() {
                            _showOfficialOnly = false;
                          });
                          _applyFilters();
                        },
                      ),
                    if (_showFeaturedOnly)
                      Chip(
                        label: Text(context.l10n.seedFeaturedOnly),
                        deleteIcon: const Icon(Icons.close, size: 18),
                        onDeleted: () {
                          setState(() {
                            _showFeaturedOnly = false;
                          });
                          _applyFilters();
                        },
                      ),
                  ],
                ),
              ),

            // Library list
            Expanded(child: _buildLibraryList(context, state, notifier)),
          ],
        ),
      ),
    );
  }

  Widget _buildLibraryList(
    BuildContext context,
    SeedLibraryListState state,
    SeedLibraryListNotifier notifier,
  ) {
    if (state.isLoading && state.libraries.isEmpty) {
      return const SparkleListSkeleton();
    }

    if (state.error != null && state.libraries.isEmpty) {
      return CustomErrorWidget.page(
        context: context,
        // N15：error 位已是类别，直接走 owner 文案表（不再喂 Object 判定）。
        message: uiErrorMessage(context.l10n, state.error!),
        onRetry: _applyFilters,
      );
    }

    if (state.libraries.isEmpty) {
      final hasSearch = _searchController.text.isNotEmpty;
      final hasOtherFilters = _selectedCategory != null ||
          _selectedVisibility != null ||
          _showOfficialOnly ||
          _showFeaturedOnly;
      // N28-③：区分「搜了没有」与「没搜过」两态——搜过零命中一律走
      // EmptyState.noResults（回显关键词+清空搜索），禁与筛选/空库态混用；
      // 原硬编码英文四句迁 l10n（seedLibraryNoMatch*/EmptyDescription/
      // ClearFilters），并拆分 clear 语义：搜过清词、筛过清筛选。
      if (hasSearch) {
        return EmptyState.noResults(
          searchQuery: _searchController.text,
          customAction: SparkleButton.ghost(
            label: context.l10n.commonClearSearch,
            onPressed: () {
              // 同步重建让 family 键回落到无参实例（否则专用态残留）。
              setState(() => _searchController.clear());
              _applyFilters();
            },
          ),
        );
      }
      return EmptyState(
        title: hasOtherFilters
            ? context.l10n.seedLibraryNoMatchTitle
            : context.l10n.seedLibraryEmpty,
        description: hasOtherFilters
            ? context.l10n.seedLibraryNoMatchDescription
            : context.l10n.seedLibraryEmptyDescription,
        icon: Icons.library_books_outlined,
        actionText: hasOtherFilters
            ? context.l10n.seedLibraryClearFilters
            : context.l10n.seedLibraryCreate,
        onAction: () {
          if (hasOtherFilters) {
            setState(() {
              _selectedCategory = null;
              _selectedVisibility = null;
              _showOfficialOnly = false;
              _showFeaturedOnly = false;
            });
            _applyFilters();
            return;
          }
          unawaited(context.push(SeedLibraryRoutes.createLibrary));
        },
      );
    }

    return SparkleRefreshIndicator(
      onRefresh: () => notifier.refresh(
        category: _selectedCategory,
        visibility: _selectedVisibility,
        search: _searchController.text.isEmpty ? null : _searchController.text,
      ),
      child: ScrollEdgeHaptics(
        child: ListView.builder(
          padding: const EdgeInsets.all(DS.spacing16),
          itemCount: state.libraries.length + (state.hasMore ? 1 : 0),
          itemBuilder: (context, index) {
            if (index >= state.libraries.length) {
              // Load more indicator
              unawaited(notifier.loadMore());
              return const Padding(
                padding: EdgeInsets.all(DS.spacing16),
                child: Center(child: LoadingIndicator()),
              );
            }

            final library = state.libraries[index];
            return SparkleStaggerItem(
              index: index,
              child: SeedLibraryCard(
                library: library,
                onTap: () {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                  );
                  unawaited(context.push(SeedLibraryRoutes.detail(library.id)));
                },
              ),
            );
          },
        ),
      ),
    );
  }

  void _showFilterDialog() {
    unawaited(
      showSensoryDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(context.l10n.seedLibraryFilter),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.seedLibraryCategory,
                style: const TextStyle(fontWeight: DS.fontWeightBold),
              ),
              const SizedBox(height: DS.spacing8),
              Wrap(
                spacing: DS.spacing8,
                children: LibraryCategory.values.map((category) {
                  final isSelected = _selectedCategory == category;
                  return FilterChip(
                    label: Text(category.label(context.l10n)),
                    selected: isSelected,
                    onSelected: (selected) {
                      setState(() {
                        _selectedCategory = selected ? category : null;
                      });
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: DS.spacing16),
              Text(
                context.l10n.seedLibraryVisibility,
                style: const TextStyle(fontWeight: DS.fontWeightBold),
              ),
              const SizedBox(height: DS.spacing8),
              Wrap(
                spacing: DS.spacing8,
                children: LibraryVisibility.values.map((visibility) {
                  final isSelected = _selectedVisibility == visibility;
                  return FilterChip(
                    label: Text(visibility.label(context.l10n)),
                    selected: isSelected,
                    onSelected: (selected) {
                      setState(() {
                        _selectedVisibility = selected ? visibility : null;
                      });
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: DS.spacing16),
              CheckboxListTile(
                value: _showOfficialOnly,
                contentPadding: EdgeInsets.zero,
                title: Text(context.l10n.seedOfficialFilter),
                subtitle: Text(context.l10n.seedOfficialFilterDesc),
                onChanged: (value) {
                  setState(() {
                    _showOfficialOnly = value ?? false;
                  });
                },
              ),
              CheckboxListTile(
                value: _showFeaturedOnly,
                contentPadding: EdgeInsets.zero,
                title: Text(context.l10n.seedFeaturedFilter),
                subtitle: Text(context.l10n.seedFeaturedFilterDesc),
                onChanged: (value) {
                  setState(() {
                    _showFeaturedOnly = value ?? false;
                  });
                },
              ),
            ],
          ),
          actions: [
            SparkleButton.ghost(
              onPressed: () {
                setState(() {
                  _selectedCategory = null;
                  _selectedVisibility = null;
                  _showOfficialOnly = false;
                  _showFeaturedOnly = false;
                });
                Navigator.pop(context);
                _applyFilters();
              },
              label: context.l10n.seedLibraryClear,
            ),
            SparkleButton(
              onPressed: () {
                Navigator.pop(context);
                _applyFilters();
              },
              label: context.l10n.seedLibraryApply,
            ),
          ],
        ),
      ),
    );
  }
}
