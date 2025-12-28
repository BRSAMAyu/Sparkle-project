import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';

class GroupSearchScreen extends ConsumerStatefulWidget {
  const GroupSearchScreen({super.key});

  @override
  ConsumerState<GroupSearchScreen> createState() => _GroupSearchScreenState();
}

class _GroupSearchScreenState extends ConsumerState<GroupSearchScreen> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _handleSearch() {
    final query = _searchController.text.trim();
    if (query.isNotEmpty) {
      ref.read(groupSearchProvider.notifier).search(query);
    }
  }

  @override
  Widget build(BuildContext context) {
    final searchState = ref.watch(groupSearchProvider);

    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _searchController,
          autofocus: true,
          decoration: const InputDecoration(
            hintText: 'Search groups...',
            border: InputBorder.none,
            hintStyle: TextStyle(color: DS.brandPrimary70),
          ),
          style: TextStyle(color: DS.brandPrimary),
          onSubmitted: (_) => _handleSearch(),
          textInputAction: TextInputAction.search,
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: _handleSearch,
          ),
        ],
      ),
      body: searchState.when(
        data: (groups) {
          if (groups.isEmpty) {
            return const Center(
              child: CompactEmptyState(
                message: 'Search for squads or sprint groups',
                icon: Icons.search,
              ),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(DS.lg),
            itemCount: groups.length,
            separatorBuilder: (context, index) => const SizedBox(height: DS.md),
            itemBuilder: (context, index) {
              final group = groups[index];
              return Card(
                elevation: 2,
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: DS.brandPrimary.shade200,
                    child: Icon(group.type.name == 'sprint' ? Icons.timer : Icons.group),
                  ),
                  title: Text(group.name),
                  subtitle: Text('${group.memberCount} members • ${group.totalFlamePower} flame'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () {
                    context.push('/community/groups/${group.id}');
                  },
                ),
              );
            },
          );
        },
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, s) => Center(child: Text('Error: $e')),
      ),
    );
  }
}
