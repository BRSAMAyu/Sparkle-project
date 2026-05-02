import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
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
        loading: () => LoadingIndicator.circular(
          showText: true,
          loadingText: I18nService.instance.isChinese ? '正在整理今日胶囊...' : 'Preparing today\'s capsule...',
        ),
        error: (err, stack) => CustomErrorWidget.page(
          context: context,
          title: context.l10n.cogCapsuleListFailed,
          message: l10n.capsuleLoadFailed('$err'),
          onRetry: () => ref.read(capsuleProvider.notifier).fetchTodayCapsules(),
        ),
      ),
    );
  }

  Widget _buildEmptyState() => Builder(
        builder: (context) => EmptyState(
          title: context.l10n.capsuleEmptyTitle,
          description: context.l10n.capsuleEmptySubtitle,
          icon: Icons.lightbulb_outline,
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
            child: EmptyState(
              title: emptyMessage ?? context.l10n.capsuleEmptyTitle,
              description: archived
                  ? (I18nService.instance.isChinese ? '已归档的胶囊会在这里显示。' : 'Archived capsules will appear here.')
                  : context.l10n.capsuleEmptySubtitle,
              icon: archived
                  ? Icons.inventory_2_outlined
                  : Icons.auto_awesome_outlined,
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
