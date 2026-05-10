import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
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
      SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
      ref.read(groupSearchProvider.notifier).search(query);
    }
  }

  @override
  Widget build(BuildContext context) {
    final searchState = ref.watch(groupSearchProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        backgroundColor: DS.surfaceOverlay.withValues(alpha: 0.94),
        surfaceTintColor: Colors.transparent,
        scrolledUnderElevation: 0,
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: TextField(
          controller: _searchController,
          autofocus: true,
          decoration: InputDecoration(
            hintText: context.l10n.groupSearchHint,
            filled: true,
            fillColor: Color.alphaBlend(
              DS.info.withValues(alpha: 0.03),
              DS.surfacePrimary,
            ),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16),
              borderSide: BorderSide.none,
            ),
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
            return Center(
              child: CompactEmptyState(
                message: context.l10n.groupSearchEmpty,
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
                return SparkleStaggerItem(
                  index: index,
                  child: GraphiteCardSurface(
                    surfaceRole: SparkleSurfaceRole.card,
                    padding: EdgeInsets.zero,
                    borderColor: DS.border.withValues(alpha: 0.42),
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
                        '${context.l10n.membersCount(group.memberCount)} • ${context.l10n.flamePower(group.totalFlamePower)}',
                      ),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () {
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.selection,
                        );
                        context.push('/community/groups/${group.id}');
                      },
                    ),
                  ),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, s) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.search_off, size: 48, color: DS.textSecondary),
              const SizedBox(height: DS.spacing12),
              Text(context.l10n.searchFailedRetry, style: TextStyle(color: DS.textSecondary)),
            ],
          ),
        ),
      ),
    );
  }
}