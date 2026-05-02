import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_card.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_draft_review_models.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_draft_review_provider.dart';

class GalaxyDraftReviewRouteArgs {
  const GalaxyDraftReviewRouteArgs({this.batchId});

  final String? batchId;
}

class GalaxyDraftReviewScreen extends ConsumerStatefulWidget {
  const GalaxyDraftReviewScreen({
    super.key,
    this.initialBatchId,
  });

  final String? initialBatchId;

  @override
  ConsumerState<GalaxyDraftReviewScreen> createState() =>
      _GalaxyDraftReviewScreenState();
}

class _GalaxyDraftReviewScreenState
    extends ConsumerState<GalaxyDraftReviewScreen> {
  final List<_EditableDraftNode> _workingDrafts = <_EditableDraftNode>[];
  final List<ReviewedGalaxyDraftNode> _reviewedNodes =
      <ReviewedGalaxyDraftNode>[];
  String? _loadedBatchId;
  int _currentIndex = 0;

  bool get _isComplete =>
      _loadedBatchId != null && _currentIndex >= _workingDrafts.length;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final state = ref.watch(galaxyDraftReviewProvider);
    final batch = state.batchById(widget.initialBatchId) ?? state.promptBatch;
    _syncBatch(batch);

    return Theme(
      data: Theme.of(context).copyWith(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF050914),
      ),
      child: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Color(0xFF07111F),
              Color(0xFF0C1830),
              Color(0xFF050914),
            ],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            surfaceTintColor: Colors.transparent,
            elevation: 0,
            leading: SparkleIconButton(
              icon: const Icon(Icons.arrow_back_rounded),
              onPressed: () => context.pop(),
            ),
            titleSpacing: 0,
            title: Text(
              l10n.galaxyDraftReviewScreenTitle,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: DS.neutral0,
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ),
          body: SafeArea(
            top: false,
            child: state.batches.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => _ReviewStatePanel(
                title: l10n.galaxyDraftReviewEmptyTitle,
                body: error.toString(),
                actionLabel: l10n.retry,
                onAction: () =>
                    ref.read(galaxyDraftReviewProvider.notifier).refresh(),
              ),
              data: (_) {
                if (batch == null || _workingDrafts.isEmpty) {
                  return _ReviewStatePanel(
                    title: l10n.galaxyDraftReviewEmptyTitle,
                    body: l10n.galaxyDraftReviewEmptyBody,
                    actionLabel: l10n.galaxyDraftBackToGalaxy,
                    onAction: () => context.pop(),
                  );
                }

                return Padding(
                  padding: const EdgeInsets.fromLTRB(
                    DS.spacing20,
                    DS.spacing8,
                    DS.spacing20,
                    DS.spacing20,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.galaxyDraftReviewPromptTitle(
                          batch.drafts.length,
                          batch.documentName,
                        ),
                        style:
                            Theme.of(context).textTheme.headlineSmall?.copyWith(
                                  color: DS.neutral0,
                                  fontWeight: FontWeight.w800,
                                  height: 1.15,
                                ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      Text(
                        l10n.galaxyDraftReviewPromptBody,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: DS.neutral0.withValues(alpha: 0.72),
                              height: 1.5,
                            ),
                      ),
                      const SizedBox(height: DS.spacing18),
                      _ReviewProgressHeader(
                        current: _currentIndex + 1,
                        total: _workingDrafts.length,
                        currentLabel: _isComplete
                            ? l10n.galaxyDraftCompletionReady
                            : l10n.galaxyDraftReviewProgress(
                                _currentIndex + 1,
                                _workingDrafts.length,
                              ),
                      ),
                      const SizedBox(height: DS.spacing16),
                      Expanded(
                        child: AnimatedSwitcher(
                          duration: const Duration(milliseconds: 280),
                          switchInCurve: Curves.easeOutCubic,
                          switchOutCurve: Curves.easeInCubic,
                          child: _isComplete
                              ? _buildCompletion(batch)
                              : _buildReviewDeck(batch),
                        ),
                      ),
                      if (!_isComplete) ...[
                        const SizedBox(height: DS.spacing16),
                        _ReviewActionBar(
                          canMerge:
                              _workingDrafts[_currentIndex].draft.similarity !=
                                  null,
                          onSkip: () =>
                              _resolveCurrent(GalaxyDraftDecision.reject),
                          onMerge: () =>
                              _resolveCurrent(GalaxyDraftDecision.merge),
                          onApprove: () =>
                              _resolveCurrent(GalaxyDraftDecision.approve),
                        ),
                        const SizedBox(height: DS.spacing12),
                        Center(
                          child: Text(
                            l10n.galaxyDraftLongPressHint,
                            textAlign: TextAlign.center,
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(
                                  color: DS.neutral0.withValues(alpha: 0.58),
                                ),
                          ),
                        ),
                      ],
                    ],
                  ),
                );
              },
            ),
          ),
        ),
      ),
    );
  }

  void _syncBatch(GalaxyDraftBatch? batch) {
    if (batch == null || batch.id == _loadedBatchId) {
      return;
    }
    _loadedBatchId = batch.id;
    _currentIndex = 0;
    _reviewedNodes..clear();
    _workingDrafts
      ..clear()
      ..addAll(
        batch.drafts.map(
          (draft) => _EditableDraftNode(
            draft: draft,
            currentName: draft.proposedName,
            currentDescription: draft.proposedDescription,
          ),
        ),
      );
  }

  Widget _buildReviewDeck(GalaxyDraftBatch batch) {
    final current = _workingDrafts[_currentIndex];
    final next = _currentIndex + 1 < _workingDrafts.length
        ? _workingDrafts[_currentIndex + 1]
        : null;

    return Stack(
      alignment: Alignment.center,
      children: [
        if (next != null)
          Transform.translate(
            offset: const Offset(0, 18),
            child: Transform.scale(
              scale: 0.96,
              child: Opacity(
                opacity: 0.36,
                child: _DraftReviewCard(
                  draft: next,
                  documentName: batch.documentName,
                ),
              ),
            ),
          ),
        Dismissible(
          key: ValueKey(current.draft.id),
          direction: DismissDirection.horizontal,
          background: _SwipeDecisionBackground(
            alignment: Alignment.centerLeft,
            color: DS.success.withValues(alpha: 0.18),
            icon: Icons.auto_awesome_rounded,
            label: context.l10n.galaxyDraftApprove,
          ),
          secondaryBackground: _SwipeDecisionBackground(
            alignment: Alignment.centerRight,
            color: DS.error.withValues(alpha: 0.18),
            icon: Icons.close_rounded,
            label: context.l10n.galaxyDraftSkip,
          ),
          onDismissed: (direction) {
            final decision = direction == DismissDirection.startToEnd
                ? GalaxyDraftDecision.approve
                : GalaxyDraftDecision.reject;
            _resolveCurrent(decision);
          },
          child: _DraftReviewCard(
            draft: current,
            documentName: batch.documentName,
            onLongPress: () => _editCurrentNode(current),
          ),
        ),
      ],
    );
  }

  Widget _buildCompletion(GalaxyDraftBatch batch) {
    final result = GalaxyDraftReviewResult(
      batchId: batch.id,
      documentName: batch.documentName,
      totalDraftCount: batch.drafts.length,
      reviewedNodes: List<ReviewedGalaxyDraftNode>.unmodifiable(_reviewedNodes),
    );
    final accepted = result.reviewedNodes
        .where((node) => node.decision != GalaxyDraftDecision.reject)
        .toList(growable: false);

    return SparkleCard(
      key: const ValueKey<String>('draft-review-complete'),
      backgroundColor: DS.neutral0.withValues(alpha: 0.08),
      borderColor: DS.neutral0.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(28),
      padding: const EdgeInsets.all(DS.spacing24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 62,
            height: 62,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                colors: [
                  DS.brandPrimary.withValues(alpha: 0.92),
                  DS.info.withValues(alpha: 0.92),
                ],
              ),
              boxShadow: [
                BoxShadow(
                  color: DS.brandPrimary.withValues(alpha: 0.36),
                  blurRadius: 28,
                  spreadRadius: 4,
                ),
              ],
            ),
            child: Icon(
              Icons.auto_awesome_rounded,
              color: DS.neutral0,
              size: 28,
            ),
          ),
          const SizedBox(height: DS.spacing20),
          Text(
            context.l10n.galaxyDraftCompletionTitle(
              result.acceptedCount,
              result.totalDraftCount,
            ),
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: DS.neutral0,
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.galaxyDraftCompletionBody(batch.documentName),
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral0.withValues(alpha: 0.72),
                  height: 1.5,
                ),
          ),
          const SizedBox(height: DS.spacing18),
          if (accepted.isNotEmpty)
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: accepted
                  .map(
                    (node) => Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing12,
                        vertical: DS.spacing8,
                      ),
                      decoration: BoxDecoration(
                        color: DS.neutral0.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(
                          color: DS.neutral0.withValues(alpha: 0.08),
                        ),
                      ),
                      child: Text(
                        node.finalName,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: DS.neutral0,
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                    ),
                  )
                  .toList(growable: false),
            )
          else
            Text(
              context.l10n.galaxyDraftCompletionNothingAdded,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.neutral0.withValues(alpha: 0.68),
                  ),
            ),
          const Spacer(),
          SparkleButton.primary(
            label: context.l10n.galaxyDraftBackToGalaxy,
            expand: true,
            onPressed: () {
              ref
                  .read(galaxyDraftReviewProvider.notifier)
                  .completeBatch(batch.id);
              context.pop(result);
            },
          ),
        ],
      ),
    );
  }

  Future<void> _editCurrentNode(_EditableDraftNode current) async {
    final nameController = TextEditingController(text: current.currentName);
    final descriptionController =
        TextEditingController(text: current.currentDescription);

    final saved = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(dialogContext.l10n.galaxyDraftEditTitle),
        content: SizedBox(
          width: 420,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: InputDecoration(
                  labelText: dialogContext.l10n.galaxyDraftNameLabel,
                ),
                maxLength: 60,
              ),
              const SizedBox(height: DS.spacing12),
              TextField(
                controller: descriptionController,
                decoration: InputDecoration(
                  labelText: dialogContext.l10n.galaxyDraftDescriptionLabel,
                ),
                maxLines: 4,
                minLines: 3,
                maxLength: 240,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: Text(dialogContext.l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: Text(dialogContext.l10n.galaxyDraftEditSave),
          ),
        ],
      ),
    );

    final nextName = nameController.text.trim();
    final nextDescription = descriptionController.text.trim();
    nameController.dispose();
    descriptionController.dispose();

    if (saved != true || !mounted) {
      return;
    }

    setState(() {
      current.currentName =
          nextName.isEmpty ? current.draft.proposedName : nextName;
      current.currentDescription = nextDescription.isEmpty
          ? current.draft.proposedDescription
          : nextDescription;
    });
  }

  void _resolveCurrent(GalaxyDraftDecision decision) {
    final current = _workingDrafts[_currentIndex];
    setState(() {
      _reviewedNodes.add(
        ReviewedGalaxyDraftNode(
          draft: current.draft,
          decision: decision,
          finalName: current.currentName,
          finalDescription: current.currentDescription,
        ),
      );
      _currentIndex += 1;
    });
  }
}

class _EditableDraftNode {
  _EditableDraftNode({
    required this.draft,
    required this.currentName,
    required this.currentDescription,
  });

  final GalaxyDraftNode draft;
  String currentName;
  String currentDescription;
}

class _ReviewStatePanel extends StatelessWidget {
  const _ReviewStatePanel({
    required this.title,
    required this.body,
    required this.actionLabel,
    required this.onAction,
  });

  final String title;
  final String body;
  final String actionLabel;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) => Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: SparkleCard(
            backgroundColor: DS.neutral0.withValues(alpha: 0.08),
            borderColor: DS.neutral0.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(28),
            padding: const EdgeInsets.all(DS.spacing24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        color: DS.neutral0,
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: DS.spacing12),
                Text(
                  body,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: DS.neutral0.withValues(alpha: 0.68),
                      ),
                ),
                const SizedBox(height: DS.spacing20),
                SparkleButton.primary(
                  label: actionLabel,
                  expand: true,
                  onPressed: onAction,
                ),
              ],
            ),
          ),
        ),
      );
}

class _ReviewProgressHeader extends StatelessWidget {
  const _ReviewProgressHeader({
    required this.current,
    required this.total,
    required this.currentLabel,
  });

  final int current;
  final int total;
  final String currentLabel;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                currentLabel,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: DS.neutral0,
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const Spacer(),
              Text(
                '$current/$total',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: DS.neutral0.withValues(alpha: 0.56),
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: total == 0 ? 0 : current / total,
              minHeight: 8,
              backgroundColor: DS.neutral0.withValues(alpha: 0.08),
              valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary),
            ),
          ),
        ],
      );
}

class _ReviewActionBar extends StatelessWidget {
  const _ReviewActionBar({
    required this.canMerge,
    required this.onSkip,
    required this.onMerge,
    required this.onApprove,
  });

  final bool canMerge;
  final VoidCallback onSkip;
  final VoidCallback onMerge;
  final VoidCallback onApprove;

  @override
  Widget build(BuildContext context) {
    final buttons = <Widget>[
      Expanded(
        child: SparkleButton.outline(
          label: context.l10n.galaxyDraftSkip,
          icon: const Icon(Icons.close_rounded),
          onPressed: onSkip,
          expand: true,
        ),
      ),
      if (canMerge)
        Expanded(
          child: SparkleButton.secondary(
            label: context.l10n.galaxyDraftMerge,
            icon: const Icon(Icons.merge_type_rounded),
            onPressed: onMerge,
            expand: true,
          ),
        ),
      Expanded(
        child: SparkleAttentionPulse(
          glowColor: DS.brandPrimary,
          child: SparkleButton.primary(
            label: context.l10n.galaxyDraftApprove,
            icon: const Icon(Icons.auto_awesome_rounded),
            onPressed: onApprove,
            expand: true,
          ),
        ),
      ),
    ];

    return Row(
      children: buttons
          .expand(
            (button) => [
              button,
              const SizedBox(width: DS.spacing10),
            ],
          )
          .toList(growable: false)
        ..removeLast(),
    );
  }
}

class _DraftReviewCard extends StatelessWidget {
  const _DraftReviewCard({
    required this.draft,
    required this.documentName,
    this.onLongPress,
  });

  final _EditableDraftNode draft;
  final String documentName;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onLongPress: onLongPress,
        borderRadius: BorderRadius.circular(32),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(32),
            gradient: LinearGradient(
              colors: [
                DS.neutral0.withValues(alpha: 0.12),
                DS.neutral0.withValues(alpha: 0.07),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            border: Border.all(
              color: DS.neutral0.withValues(alpha: 0.12),
            ),
            boxShadow: [
              BoxShadow(
                color: DS.galaxyShadow.withValues(alpha: 0.26),
                blurRadius: 30,
                offset: const Offset(0, 22),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    _MetaPill(
                      icon: Icons.picture_as_pdf_outlined,
                      label: documentName,
                    ),
                    _MetaPill(
                      icon: Icons.touch_app_outlined,
                      label: context.l10n.galaxyDraftLongPressShort,
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing18),
                Text(
                  draft.currentName,
                  style: theme.textTheme.headlineSmall?.copyWith(
                    color: DS.neutral0,
                    fontWeight: FontWeight.w800,
                    height: 1.15,
                  ),
                ),
                const SizedBox(height: DS.spacing10),
                Text(
                  draft.currentDescription,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: DS.neutral0.withValues(alpha: 0.72),
                    height: 1.5,
                  ),
                ),
                if (draft.draft.similarity != null) ...[
                  const SizedBox(height: DS.spacing18),
                  _SimilarityBanner(similarity: draft.draft.similarity!),
                ],
                const SizedBox(height: DS.spacing20),
                Text(
                  context.l10n.galaxyDraftExcerpts,
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: DS.neutral0,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: DS.spacing12),
                Expanded(
                  child: ListView.separated(
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: draft.draft.excerpts.length,
                    separatorBuilder: (_, __) =>
                        const SizedBox(height: DS.spacing10),
                    itemBuilder: (context, index) => _ExcerptCard(
                      excerpt: draft.draft.excerpts[index],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SimilarityBanner extends StatelessWidget {
  const _SimilarityBanner({required this.similarity});

  final GalaxyDraftSimilarity similarity;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing14),
        decoration: BoxDecoration(
          color: DS.warning.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: DS.warning.withValues(alpha: 0.18),
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.hub_outlined,
              color: DS.warningLight,
              size: 20,
            ),
            const SizedBox(width: DS.spacing10),
            Expanded(
              child: Text(
                context.l10n.galaxyDraftSimilarityLabel(
                  similarity.existingNodeName,
                  similarity.similarityPercent,
                ),
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.neutral0,
                      height: 1.45,
                    ),
              ),
            ),
          ],
        ),
      );
}

class _ExcerptCard extends StatelessWidget {
  const _ExcerptCard({required this.excerpt});

  final String excerpt;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing14),
        decoration: BoxDecoration(
          color: DS.neutral0.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: DS.neutral0.withValues(alpha: 0.08),
          ),
        ),
        child: Text(
          excerpt,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: DS.neutral0.withValues(alpha: 0.74),
                height: 1.5,
              ),
        ),
      );
}

class _SwipeDecisionBackground extends StatelessWidget {
  const _SwipeDecisionBackground({
    required this.alignment,
    required this.color,
    required this.icon,
    required this.label,
  });

  final Alignment alignment;
  final Color color;
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(32),
        ),
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing24),
        alignment: alignment,
        child: Row(
          mainAxisAlignment: alignment == Alignment.centerLeft
              ? MainAxisAlignment.start
              : MainAxisAlignment.end,
          children: [
            if (alignment == Alignment.centerRight)
              Text(
                label,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: DS.neutral0,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            if (alignment == Alignment.centerRight)
              const SizedBox(width: DS.spacing10),
            Icon(icon, color: DS.neutral0),
            if (alignment == Alignment.centerLeft)
              const SizedBox(width: DS.spacing10),
            if (alignment == Alignment.centerLeft)
              Text(
                label,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: DS.neutral0,
                      fontWeight: FontWeight.w700,
                    ),
              ),
          ],
        ),
      );
}

class _MetaPill extends StatelessWidget {
  const _MetaPill({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.neutral0.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: DS.neutral0.withValues(alpha: 0.08),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: DS.neutral0.withValues(alpha: 0.74), size: 16),
            const SizedBox(width: DS.spacing8),
            Text(
              label,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: DS.neutral0.withValues(alpha: 0.78),
                  ),
            ),
          ],
        ),
      );
}
