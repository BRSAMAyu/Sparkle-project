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

  @override
  void initState() {
    super.initState();
    // Load initial libraries
    Future.microtask(() {
      ref.read(
        seedLibraryListProvider(
          (
            category: _selectedCategory,
            isFeatured: null,
            isOfficial: null,
            visibility: _selectedVisibility,
            search:
                _searchController.text.isEmpty ? null : _searchController.text,
          ),
        ).notifier,
      );
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _applyFilters() {
    unawaited(
      SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
    );
    ref
        .read(
          seedLibraryListProvider(
            (
              category: _selectedCategory,
              isFeatured: null,
              isOfficial: null,
              visibility: _selectedVisibility,
              search: _searchController.text.isEmpty
                  ? null
                  : _searchController.text,
            ),
          ).notifier,
        )
        .refresh(
          category: _selectedCategory,
          visibility: _selectedVisibility,
          search:
              _searchController.text.isEmpty ? null : _searchController.text,
        );
  }

  @override
  Widget build(BuildContext context) {
    final params = (
      category: _selectedCategory,
      isFeatured: null,
      isOfficial: null,
      visibility: _selectedVisibility,
      search: _searchController.text.isEmpty ? null : _searchController.text,
    );
    final state = ref.watch(seedLibraryListProvider(params));
    final notifier = ref.read(seedLibraryListProvider(params).notifier);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(context.l10n.seedLibraryTitle),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.refresh),
            onPressed: _applyFilters,
          ),
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.filter_list),
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
            if (_selectedCategory != null || _selectedVisibility != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                child: Wrap(
                  spacing: DS.spacing8,
                  children: [
                    if (_selectedCategory != null)
                      Chip(
                        label: Text(_selectedCategory!.displayName),
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
                        label: Text(_selectedVisibility!.displayName),
                        deleteIcon: const Icon(Icons.close, size: 18),
                        onDeleted: () {
                          setState(() {
                            _selectedVisibility = null;
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
      final hasFilters =
          _searchController.text.isNotEmpty ||
          _selectedCategory != null ||
          _selectedVisibility != null;
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
              _searchController.clear();
            });
            _applyFilters();
            return;
          }
          context.push(SeedLibraryRoutes.createLibrary);
        },
      );
    }

    return RefreshIndicator(
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
              notifier.loadMore();
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
                  context.push(SeedLibraryRoutes.detail(library.id));
                },
              ),
            );
          },
        ),
      ),
    );
  }

  void _showFilterDialog() {
    showSensoryDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.l10n.seedLibraryFilter),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(context.l10n.seedLibraryCategory, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing8,
              children: LibraryCategory.values.map((category) {
                final isSelected = _selectedCategory == category;
                return FilterChip(
                  label: Text(category.displayName),
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
            Text(context.l10n.seedLibraryVisibility, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing8,
              children: LibraryVisibility.values.map((visibility) {
                final isSelected = _selectedVisibility == visibility;
                return FilterChip(
                  label: Text(visibility.displayName),
                  selected: isSelected,
                  onSelected: (selected) {
                    setState(() {
                      _selectedVisibility = selected ? visibility : null;
                    });
                  },
                );
              }).toList(),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            onPressed: () {
              setState(() {
                _selectedCategory = null;
                _selectedVisibility = null;
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
    );
  }
}
