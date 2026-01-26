import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_detail_screen.dart';
import 'package:sparkle/features/seed_library/presentation/screens/create_library_screen.dart';
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
      ref.read(seedLibraryListProvider(({
        category: _selectedCategory,
        visibility: _selectedVisibility,
        search: _searchController.text.isEmpty ? null : _searchController.text,
      }).notifier));
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _applyFilters() {
    ref.read(seedLibraryListProvider(({
      category: _selectedCategory,
      visibility: _selectedVisibility,
      search: _searchController.text.isEmpty ? null : _searchController.text,
    }).notifier)).refresh(
      category: _selectedCategory,
      visibility: _selectedVisibility,
      search: _searchController.text.isEmpty ? null : _searchController.text,
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = seedLibraryListProvider(({
      category: _selectedCategory,
      visibility: _selectedVisibility,
      search: _searchController.text.isEmpty ? null : _searchController.text,
    });
    final state = ref.watch(provider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('种子库'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _applyFilters(),
          ),
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: '搜索种子库...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
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
                fillColor: Theme.of(context).colorScheme.surfaceVariant,
              ),
              onSubmitted: (_) => _applyFilters(),
            ),
          ),

          // Filter chips
          if (_selectedCategory != null || _selectedVisibility != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Wrap(
                spacing: 8,
                children: [
                  if (_selectedCategory != null)
                    Chip(
                      label: Text(_selectedCategory!.categoryDisplayName),
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
                      label: Text(_selectedVisibility!.visibilityDisplayName),
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
            child: _buildLibraryList(context, state, provider.notifier),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final result = await Navigator.push<bool>(
            context,
            MaterialPageRoute(
              builder: (context) => const CreateLibraryScreen(),
            ),
          );
          if (result == true) {
            _applyFilters();
          }
        },
        child: const Icon(Icons.add),
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
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              state.error!,
              style: Theme.of(context).textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _applyFilters,
              child: const Text('重试'),
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
            Icon(Icons.library_books_outlined,
                size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              '暂无种子库',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              '创建一个新的种子库开始使用',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[600],
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
        padding: const EdgeInsets.all(16),
        itemCount: state.libraries.length + (state.hasMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index >= state.libraries.length) {
            // Load more indicator
            notifier.loadMore();
            return const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            );
          }

          final library = state.libraries[index];
          return SeedLibraryCard(
            library: library,
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
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
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('筛选'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('分类', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: LibraryCategory.values.map((category) {
                final isSelected = _selectedCategory == category;
                return FilterChip(
                  label: Text(category.categoryDisplayName),
                  selected: isSelected,
                  onSelected: (selected) {
                    setState(() {
                      _selectedCategory = selected ? category : null;
                    });
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 16),
            const Text('可见性', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: LibraryVisibility.values.map((visibility) {
                final isSelected = _selectedVisibility == visibility;
                return FilterChip(
                  label: Text(visibility.visibilityDisplayName),
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
          TextButton(
            onPressed: () {
              setState(() {
                _selectedCategory = null;
                _selectedVisibility = null;
              });
              Navigator.pop(context);
              _applyFilters();
            },
            child: const Text('清除'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _applyFilters();
            },
            child: const Text('应用'),
          ),
        ],
      ),
    );
  }
}
