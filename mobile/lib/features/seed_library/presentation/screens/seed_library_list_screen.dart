import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/seed_library/presentation/screens/create_library_screen.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_detail_screen.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_template_pack_list_screen.dart';
import 'package:sparkle/features/seed_library/presentation/widgets/seed_library_card.dart';

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

    return Scaffold(
      appBar: AppBar(
        title: const Text('种子库'),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            size: DS.touchTargetMinSize,
            icon: const Icon(Icons.refresh),
            onPressed: _applyFilters,
          ),
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            size: DS.touchTargetMinSize,
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
          ),
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            size: DS.touchTargetMinSize,
            icon: const Icon(Icons.auto_awesome),
            onPressed: () {
              Navigator.push<void>(
                context,
                MaterialPageRoute(
                  builder: (_) => const SeedTemplatePackListScreen(),
                ),
              );
            },
          ),
        ],
      ),
      body: ContentConstraint(
        child: Column(
          children: [
            // Search bar
            Padding(
              padding: const EdgeInsets.all(DS.spacing16),
              child: TextField(
                controller: _searchController,
                decoration: InputDecoration(
                  hintText: '搜索种子库...',
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
                  fillColor:
                      Theme.of(context).colorScheme.surfaceContainerHighest,
                ),
                onSubmitted: (_) => _applyFilters(),
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
      floatingActionButton: SparkleIconButton(
        size: DS.touchTargetMinSize + DS.spacing8,
        variant: ButtonVariant.primary,
        onPressed: () async {
          final result = await Navigator.push<bool>(
            context,
            MaterialPageRoute(
              builder: (context) => const CreateLibraryScreen(),
            ),
          );
          if (result ?? false) {
            _applyFilters();
          }
        },
        icon: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildLibraryList(
    BuildContext context,
    SeedLibraryListState state,
    SeedLibraryListNotifier notifier,
  ) {
    if (state.isLoading && state.libraries.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.libraries.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: DS.spacing64, color: DS.error),
            const SizedBox(height: DS.spacing16),
            Text(
              state.error!,
              style: Theme.of(context).textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.spacing16),
            SparkleButton(
              onPressed: _applyFilters,
              label: '重试',
              icon: const Icon(Icons.refresh),
              variant: ButtonVariant.destructive,
            ),
          ],
        ),
      );
    }

    if (state.libraries.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.library_books_outlined,
              size: DS.spacing64,
              color: DS.textTertiary,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              '暂无种子库',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              '创建一个新的种子库开始使用',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => notifier.refresh(
        category: _selectedCategory,
        visibility: _selectedVisibility,
        search: _searchController.text.isEmpty ? null : _searchController.text,
      ),
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
          return SeedLibraryCard(
            library: library,
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute<void>(
                  builder: (context) => SeedLibraryDetailScreen(
                    libraryId: library.id,
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }

  void _showFilterDialog() {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('筛选'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('分类', style: TextStyle(fontWeight: FontWeight.bold)),
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
            const Text('可见性', style: TextStyle(fontWeight: FontWeight.bold)),
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
            label: '清除',
          ),
          SparkleButton(
            onPressed: () {
              Navigator.pop(context);
              _applyFilters();
            },
            label: '应用',
          ),
        ],
      ),
    );
  }
}
