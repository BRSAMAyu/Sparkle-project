import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';

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

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: TextField(
          controller: _searchController,
          autofocus: true,
          decoration: InputDecoration(
            hintText: 'Search groups...',
            border: InputBorder.none,
            hintStyle: TextStyle(color: DS.textSecondary),
          ),
          style: TextStyle(color: DS.textPrimary),
          onSubmitted: (_) => _handleSearch(),
          textInputAction: TextInputAction.search,
        ),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.search),
            onPressed: _handleSearch,
          ),
        ],
      ),
      child: searchState.when(
        data: (groups) {
          if (groups.isEmpty) {
            return const Center(
              child: CompactEmptyState(
                message: 'Search for squads or sprint groups',
                icon: Icons.search,
              ),
            );
          }
          return ContentConstraint(
            child: ListView.separated(
              padding: const EdgeInsets.all(DS.lg),
              itemCount: groups.length,
              separatorBuilder: (context, index) =>
                  const SizedBox(height: DS.md),
              itemBuilder: (context, index) {
                final group = groups[index];
                return GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  padding: EdgeInsets.zero,
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor:
                          DS.surfaceRoleColor(SparkleSurfaceRole.panel),
                      child: Icon(
                        group.type.name == 'sprint' ? Icons.timer : Icons.group,
                      ),
                    ),
                    title: Text(group.name),
                    subtitle: Text(
                      '${group.memberCount} members • ${group.totalFlamePower} flame',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      context.push('/community/groups/${group.id}');
                    },
                  ),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, s) => Center(child: Text('Error: $e')),
      ),
    );
  }
}
