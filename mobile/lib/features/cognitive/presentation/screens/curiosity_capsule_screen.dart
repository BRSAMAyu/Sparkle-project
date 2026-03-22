import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_archive_provider.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/curiosity_capsule_card.dart';

class CuriosityCapsuleScreen extends ConsumerWidget {
  const CuriosityCapsuleScreen({this.highlightId, super.key});
  final String? highlightId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final capsuleState = ref.watch(capsuleProvider);
    final archiveState = ref.watch(capsuleArchiveProvider);
    final l10n = context.l10n;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        title: Text(l10n.capsuleScreenTitle),
      ),
      child: capsuleState.when(
        data: (capsules) {
          final archivedIds = archiveState.archivedIds.toSet();
          final activeCapsules = capsules
              .where((capsule) => !archivedIds.contains(capsule.id))
              .toList(growable: false);
          final archivedCapsules = capsules
              .where((capsule) => archivedIds.contains(capsule.id))
              .toList(growable: false);

          if (activeCapsules.isEmpty && archivedCapsules.isEmpty) {
            return _buildEmptyState();
          }

          return DefaultTabController(
            length: 2,
            child: Column(
              children: [
                SparkleStaggerItem(
                  index: 0,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(
                      DS.spacing16,
                      DS.spacing12,
                      DS.spacing16,
                      DS.spacing8,
                    ),
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: DS.surfaceSecondary,
                        borderRadius: DS.borderRadius16,
                        border: Border.all(color: DS.borderSubtle),
                      ),
                      child: TabBar(
                        indicatorSize: TabBarIndicatorSize.tab,
                        dividerColor: Colors.transparent,
                        indicator: BoxDecoration(
                          color: DS.capsuleAccent.withValues(alpha: 0.14),
                          borderRadius: DS.borderRadius16,
                        ),
                        tabs: [
                          Tab(text: l10n.capsuleCurrentTab(activeCapsules.length)),
                          Tab(text: l10n.capsuleArchiveTab(archivedCapsules.length)),
                        ],
                      ),
                    ),
                  ),
                ),
                Expanded(
                  child: RefreshIndicator(
                    onRefresh: () =>
                        ref.read(capsuleProvider.notifier).fetchTodayCapsules(),
                    child: TabBarView(
                      children: [
                        _CapsuleList(
                          capsules: activeCapsules,
                          highlightId: highlightId,
                        ),
                        _CapsuleList(
                          capsules: archivedCapsules,
                          highlightId: highlightId,
                          archived: true,
                          emptyMessage: l10n.capsuleArchiveEmpty,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text(l10n.capsuleLoadFailed('$err'))),
      ),
    );
  }

  Widget _buildEmptyState() => Builder(
        builder: (context) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.lightbulb_outline,
              size: 64,
              color: DS.brandPrimary.withValues(alpha: 0.3),
            ),
            const SizedBox(height: DS.lg),
            Text(
              context.l10n.capsuleEmptyTitle,
              style: TextStyle(color: DS.textPrimary, fontSize: 16),
            ),
            const SizedBox(height: DS.sm),
            Text(
              context.l10n.capsuleEmptySubtitle,
              style: TextStyle(color: DS.textSecondary, fontSize: 14),
            ),
          ],
        ),
      ),
      );
}

class _CapsuleList extends StatelessWidget {
  const _CapsuleList({
    required this.capsules,
    this.highlightId,
    this.archived = false,
    this.emptyMessage,
  });

  final List<CuriosityCapsuleModel> capsules;
  final String? highlightId;
  final bool archived;
  final String? emptyMessage;

  @override
  Widget build(BuildContext context) {
    if (capsules.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          SizedBox(
            height: 360,
            child: Center(
              child: Text(
                emptyMessage ?? context.l10n.capsuleEmptyTitle,
                style: TextStyle(color: DS.textSecondary, fontSize: 14),
              ),
            ),
          ),
        ],
      );
    }

    return ContentConstraint(
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
        itemCount: capsules.length,
        itemBuilder: (context, index) {
          final capsule = capsules[index];
          final isHighlight = highlightId != null && capsule.id == highlightId;
          return CuriosityCapsuleCard(
            capsule: capsule,
            highlighted: isHighlight,
            initiallyExpanded: isHighlight,
            archived: archived,
          );
        },
      ),
    );
  }
}
