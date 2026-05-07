import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
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
    unawaited(
      SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
    );
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
            onPressed: () => unawaited(
              context.push(SeedLibraryRoutes.marketplace),
            ),
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
      floatingActionButton: SparkleIconButton(
        size: DS.touchTargetMinSize + DS.spacing8,
        onPressed: () async {
          unawaited(
            SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen),
          );
          final result =
              await context.push<bool>(SeedLibraryRoutes.createLibrary);
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
                  onSubmitted: (_) => _applyFilters(),
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
            Expanded(
              child: _buildLibraryList(context, state, notifier),
            ),
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
      return LoadingIndicator.circular(
        showText: true,
        loadingText: 'Loading seed libraries...',
      );
    }

    if (state.error != null && state.libraries.isEmpty) {
      return CustomErrorWidget.page(
        context: context,
        message: state.error!,
        onRetry: _applyFilters,
      );
    }

    if (state.libraries.isEmpty) {
      final hasFilters = _searchController.text.isNotEmpty ||
          _selectedCategory != null ||
          _selectedVisibility != null ||
          _showOfficialOnly ||
          _showFeaturedOnly;
      return EmptyState(
        title: hasFilters
            ? 'No seed libraries match this filter'
            : context.l10n.seedLibraryEmpty,
        description: hasFilters
            ? 'Try clearing a filter or broadening the keyword to discover more reusable growth patterns.'
            : 'Create the first seed library and turn a great prompt, workflow, or strategy into something reusable.',
        icon: Icons.library_books_outlined,
        actionText: hasFilters ? 'Clear filters' : 'Create seed library',
        onAction: () {
          if (hasFilters) {
            setState(() {
              _selectedCategory = null;
              _selectedVisibility = null;
              _showOfficialOnly = false;
              _showFeaturedOnly = false;
              _searchController.clear();
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
                child: Center(child: CircularProgressIndicator()),
              );
            }

            final library = state.libraries[index];
            return SparkleStaggerItem(
              index: index,
              child: SeedLibraryCard(
                library: library,
                onTap: () {
                  unawaited(
                    SensoryFeedbackService.emit(
                      SensoryFeedbackEvent.selection,
                    ),
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
