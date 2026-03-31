import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/insights/presentation/widgets/learning_path_dialog.dart';
import 'package:sparkle/features/knowledge/data/models/knowledge_detail_model.dart';
import 'package:sparkle/features/knowledge/presentation/providers/knowledge_detail_provider.dart';

class KnowledgeDetailScreen extends ConsumerWidget {
  const KnowledgeDetailScreen({required this.nodeId, super.key});
  final String nodeId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(knowledgeDetailProvider(nodeId));
    final l10n = context.l10n;

    return detailAsync.when(
      loading: () => const GraphiteScaffold(
        role: SparklePageRole.content,
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (error, stack) => GraphiteScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          leading: BackButton(onPressed: () => context.pop()),
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                l10n.knowledgeLoadFailed,
                style: DS.titleLarge.copyWith(color: DS.textPrimary),
              ),
              const SizedBox(height: DS.lg),
              Text(
                '$error',
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.lg),
              SparkleButton.primary(
                label: l10n.knowledgeReload,
                onPressed: () =>
                    ref.invalidate(knowledgeDetailProvider(nodeId)),
              ),
            ],
          ),
        ),
      ),
      data: (detail) => _buildContent(context, ref, detail),
    );
  }

  Widget _buildContent(
    BuildContext context,
    WidgetRef ref,
    KnowledgeDetailResponse detail,
  ) {
    final sectorStyle = SectorConfig.getStyle(detail.node.sector);
    final theme = Theme.of(context);
    final l10n = context.l10n;
    final visibleRelations =
        detail.relations.where(_isRenderableRelation).toList(growable: false);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      floatingActionButton: SparkleButton(
        label: l10n.knowledgeGeneratePath,
        icon: const Icon(Icons.timeline),
        onPressed: () {
          unawaited(
            showSensoryModalBottomSheet<void>(
              context: context,
              useRootNavigator: true,
              isScrollControlled: true,
              backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
              builder: (context) => GraphiteModalSurface(
                title: l10n.knowledgeGeneratePath,
                child: LearningPathDialog(
                  targetNodeId: nodeId,
                  targetNodeName: detail.node.name,
                ),
              ),
            ),
          );
        },
      ),
      child: CustomScrollView(
        slivers: [
          // Hero Header with sector gradient
          SliverAppBar(
            expandedHeight: 200,
            pinned: true,
            backgroundColor: DS.surfaceOverlay,
            surfaceTintColor: Colors.transparent,
            leading: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: Icon(Icons.arrow_back, color: DS.textPrimary),
              onPressed: () => context.pop(),
            ),
            actions: [
              SparkleIconButton(
                variant: ButtonVariant.ghost,
                icon: Icon(
                  detail.userStats.isFavorite ? Icons.star : Icons.star_border,
                  color: detail.userStats.isFavorite
                      ? sectorStyle.primaryColor
                      : DS.textPrimary,
                ),
                onPressed: () {
                  ref.read(toggleFavoriteProvider(nodeId));
                },
              ),
              SparkleIconButton(
                variant: ButtonVariant.ghost,
                icon: const Icon(Icons.share_outlined),
                onPressed: () => unawaited(_showShareSheet(context, detail)),
              ),
            ],
            flexibleSpace: FlexibleSpaceBar(
              background: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Color.lerp(
                        DS.surfaceCanvas,
                        sectorStyle.primaryColor,
                        0.28,
                      )!,
                      Color.lerp(
                        DS.surfaceCanvas,
                        sectorStyle.glowColor,
                        0.16,
                      )!,
                      DS.surfaceCanvas,
                    ],
                  ),
                ),
                child: SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.all(DS.lg),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.end,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Sector tag
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: DS.brandPrimary24,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Text(
                            sectorStyle.name,
                            style: TextStyle(
                              color: DS.textPrimary,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        const SizedBox(height: DS.sm),
                        // Node name
                        Text(
                          detail.node.name,
                          style: DS.headingLarge.copyWith(
                            color: DS.textPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        if (detail.node.nameEn != null) ...[
                          const SizedBox(height: DS.xs),
                          Text(
                            detail.node.nameEn!,
                            style: DS.bodyMedium.copyWith(
                              color: DS.textSecondary,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),

          // Mastery Progress Card
          SliverToBoxAdapter(
            child: ContentConstraint(
              child: SparkleStaggerItem(
                index: 0,
                child: _MasteryCard(
                  stats: detail.userStats,
                  sectorColor: sectorStyle.primaryColor,
                ),
              ),
            ),
          ),

          // Description Section
          if (detail.node.description != null &&
              detail.node.description!.isNotEmpty)
            SliverToBoxAdapter(
              child: ContentConstraint(
                child: SparkleStaggerItem(
                  index: 1,
                  child: _SectionCard(
                    title: context.l10n.knowledgeDescription,
                    child: Text(
                      detail.node.description!,
                      style: theme.textTheme.bodyMedium,
                    ),
                  ),
                ),
              ),
            ),

          // Keywords
          if (detail.node.keywords.isNotEmpty)
            SliverToBoxAdapter(
              child: ContentConstraint(
                child: SparkleStaggerItem(
                  index: 2,
                  child: _SectionCard(
                    title: context.l10n.knowledgeKeywords,
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: detail.node.keywords
                          .map(
                            (keyword) => Chip(
                              label: Text(keyword),
                              backgroundColor:
                                  sectorStyle.glowColor.withAlpha(50),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                ),
              ),
            ),

          SliverToBoxAdapter(
            child: ContentConstraint(
              child: SparkleStaggerItem(
                index: 3,
                child: _SectionCard(
                  title: 'AI 拓展相关节点',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '基于当前节点生成 3 个候选相关节点。你可以不选，也可以任选 1 到 3 个真正写入知识星图。',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                      ),
                      const SizedBox(height: DS.sm),
                      SparkleButton(
                        label: '生成候选节点',
                        icon: const Icon(Icons.auto_awesome),
                        expand: true,
                        onPressed: () => unawaited(
                          _showExpansionSheet(context, ref, detail),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Related Knowledge Nodes
          if (visibleRelations.isNotEmpty)
            SliverToBoxAdapter(
              child: ContentConstraint(
                child: _SectionCard(
                  title: context.l10n.knowledgeRelatedNodes,
                  child: Column(
                    children: visibleRelations.map((relation) {
                      final isSource = relation.sourceNodeId == nodeId;
                      final relatedNodeId = isSource
                          ? relation.targetNodeId
                          : relation.sourceNodeId;
                      final relatedNodeName = isSource
                          ? relation.targetNodeName
                          : relation.sourceNodeName;

                      return ListTile(
                        leading: Icon(
                          _getRelationIcon(relation.relationType),
                          color: sectorStyle.primaryColor,
                        ),
                        title: Text(relatedNodeName ?? '未知节点'),
                        subtitle: Text(relation.relationLabel),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () {
                          if (!_isRenderableNodeName(relatedNodeName) ||
                              relatedNodeId.trim().isEmpty) {
                            AppFeedback.info(
                              context,
                              '这个节点已被清理，星图会在下次刷新后同步。',
                            );
                            return;
                          }
                          unawaited(
                              context.push('/galaxy/node/$relatedNodeId'));
                        },
                      );
                    }).toList(),
                  ),
                ),
              ),
            ),

          if (detail.learningPathSnapshot != null)
            SliverToBoxAdapter(
              child: ContentConstraint(
                child: _SectionCard(
                  title: '最近生成的学习路径',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(DS.sm),
                        decoration: BoxDecoration(
                          color: DS.surfacePanel,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          detail.learningPathSnapshot!.mode == 'task_path'
                              ? '当前为轻量任务路径，不占用计划额度。'
                              : '当前为完整学习计划路径。',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                          ),
                        ),
                      ),
                      const SizedBox(height: DS.md),
                      SparkleMarkdown(
                        content: detail.learningPathSnapshot!.summary,
                        textColor: DS.textPrimary,
                        codeBackgroundColor: DS.surfacePanel,
                        linkColor: DS.brandPrimary,
                        fontSize: theme.textTheme.bodyMedium?.fontSize ?? 14,
                        contentRole: SparkleMarkdownRole.knowledgeSummary,
                      ),
                      if (detail.learningPathSnapshot!.tasks.isNotEmpty) ...[
                        const SizedBox(height: DS.md),
                        Text(
                          '已生成任务',
                          style: theme.textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: DS.xs),
                        ...detail.learningPathSnapshot!.tasks.map(
                          (task) => Container(
                            margin: const EdgeInsets.only(bottom: DS.spacing8),
                            decoration: BoxDecoration(
                              color: DS.surfacePanel,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: ListTile(
                              dense: true,
                              contentPadding: const EdgeInsets.symmetric(
                                horizontal: DS.spacing12,
                                vertical: DS.spacing4,
                              ),
                              leading: const Icon(Icons.task_alt),
                              title: Text(
                                task.title,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                              subtitle: Text('约 ${task.estimatedMinutes} 分钟'),
                              trailing: const Icon(Icons.chevron_right),
                              onTap: () =>
                                  unawaited(context.push('/tasks/${task.id}')),
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),

          // Related Tasks
          if (detail.relatedTasks.isNotEmpty)
            SliverToBoxAdapter(
              child: ContentConstraint(
                child: _SectionCard(
                  title: context.l10n.knowledgeRelatedTasks,
                  child: Column(
                    children: detail.relatedTasks
                        .map(
                          (task) => ListTile(
                            leading: Icon(
                              Icons.task_alt,
                              color: task.status.name == 'completed'
                                  ? DS.success
                                  : DS.brandPrimary,
                            ),
                            title: Text(task.title),
                            subtitle: Text(
                              '${context.l10n.knowledgeEstimated} ${task.estimatedMinutes} ${context.l10n.knowledgeMinutes}',
                            ),
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () {
                              unawaited(context.push('/tasks/${task.id}'));
                            },
                          ),
                        )
                        .toList(),
                  ),
                ),
              ),
            ),

          // Related Plans
          if (detail.relatedPlans.isNotEmpty)
            SliverToBoxAdapter(
              child: ContentConstraint(
                child: _SectionCard(
                  title: context.l10n.knowledgeRelatedPlans,
                  child: Column(
                    children: detail.relatedPlans
                        .map(
                          (plan) => ListTile(
                            leading: Icon(
                              plan.planType == 'sprint'
                                  ? Icons.bolt
                                  : Icons.trending_up,
                              color: sectorStyle.primaryColor,
                            ),
                            title: Text(plan.title),
                            subtitle: Text(
                              plan.planType == 'sprint'
                                  ? context.l10n.planTypeSprint
                                  : context.l10n.planTypeGrowth,
                            ),
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () {
                              if (plan.planType == 'sprint') {
                                unawaited(context.push('/sprint'));
                              } else {
                                unawaited(context.push('/growth'));
                              }
                            },
                          ),
                        )
                        .toList(),
                  ),
                ),
              ),
            ),

          // Bottom padding
          const SliverToBoxAdapter(
            child: SizedBox(height: 100),
          ),
        ],
      ),
    );
  }

  Future<void> _showShareSheet(
    BuildContext context,
    KnowledgeDetailResponse detail,
  ) async {
    await showUniversalShareSheet(
      context,
      payload: UniversalSharePayload(
        contentType: ShareableContentType.knowledgeNode,
        resourceId: detail.node.id,
        title: detail.node.name,
        subtitle:
            detail.node.nameEn ?? detail.node.description?.split('\n').first,
        description: detail.node.description,
        metadata: {
          'mastery': detail.userStats.masteryProgress,
          'category': SectorConfig.getLocalizedName(detail.node.sector),
          'parent_path': detail.node.subjectName,
          'connections': detail.relations.length,
          'learning_time': detail.userStats.totalStudyMinutes,
          'study_count': detail.userStats.studyCount,
        },
      ),
      onGenerateCard: (payload) =>
          SharePosterService().generatePoster(context, payload),
    );
  }

  Future<void> _showExpansionSheet(
    BuildContext context,
    WidgetRef ref,
    KnowledgeDetailResponse detail,
  ) async {
    await showSensoryModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      builder: (context) => GraphiteModalSurface(
        title: 'AI 拓展相关节点',
        child: _NodeExpansionSheet(
          nodeId: nodeId,
          nodeName: detail.node.name,
          onApplied: () {
            ref
              ..invalidate(knowledgeDetailProvider(nodeId))
              ..invalidate(galaxyRepositoryProvider)
              ..invalidate(enhancedGalaxyRepositoryProvider)
              ..invalidate(galaxyProvider);
          },
        ),
      ),
    );
  }

  IconData _getRelationIcon(String relationType) {
    switch (relationType) {
      case 'prerequisite':
        return Icons.arrow_upward;
      case 'related':
        return Icons.link;
      case 'application':
        return Icons.build;
      case 'composition':
        return Icons.account_tree;
      case 'evolution':
        return Icons.trending_up;
      default:
        return Icons.circle;
    }
  }

  bool _isRenderableRelation(NodeRelation relation) {
    final isSource = relation.sourceNodeId == nodeId;
    final relatedNodeName =
        isSource ? relation.targetNodeName : relation.sourceNodeName;
    final relatedNodeId =
        isSource ? relation.targetNodeId : relation.sourceNodeId;
    return relatedNodeId.trim().isNotEmpty &&
        _isRenderableNodeName(relatedNodeName);
  }

  bool _isRenderableNodeName(String? rawName) {
    final name = rawName?.trim() ?? '';
    if (name.isEmpty || name.contains('�')) {
      return false;
    }
    if (RegExp(r'^J\d', caseSensitive: false).hasMatch(name)) {
      return false;
    }
    if (RegExp(r'^[a-zA-Z]\d{2,}$').hasMatch(name)) {
      return false;
    }
    if (name.toLowerCase() == 'null') {
      return false;
    }
    return !RegExp(r'^[?？·•\-_=\s]+$').hasMatch(name);
  }
}

/// Mastery progress card
class _MasteryCard extends StatelessWidget {
  const _MasteryCard({
    required this.stats,
    required this.sectorColor,
  });
  final KnowledgeUserStats stats;
  final Color sectorColor;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        margin: const EdgeInsets.all(DS.lg),
        child: Padding(
          padding: const EdgeInsets.all(DS.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Mastery header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    context.l10n.knowledgeMastery,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: _getMasteryColor().withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text(
                      stats.masteryLabel,
                      style: DS.labelLarge.copyWith(
                        color: _getMasteryColor(),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.lg),

              // Progress bar
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: stats.masteryProgress,
                  minHeight: 12,
                  backgroundColor: DS.surfaceTertiary,
                  valueColor: AlwaysStoppedAnimation<Color>(_getMasteryColor()),
                ),
              ),
              const SizedBox(height: DS.sm),
              Text(
                '${stats.masteryScore.toStringAsFixed(0)}%',
                style: DS.titleLarge.copyWith(
                  color: _getMasteryColor(),
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: DS.lg),

              // Stats row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _StatItem(
                    icon: Icons.timer,
                    value: '${stats.totalStudyMinutes}',
                    label: context.l10n.knowledgeStudyMinutes,
                  ),
                  _StatItem(
                    icon: Icons.repeat,
                    value: '${stats.studyCount}',
                    label: context.l10n.knowledgeStudyCount,
                  ),
                  if (stats.nextReviewAt != null)
                    _StatItem(
                      icon: Icons.event,
                      value: _formatReviewDate(context, stats.nextReviewAt!),
                      label: context.l10n.knowledgeNextReview,
                    ),
                ],
              ),

              // Decay status
              if (stats.decayPaused) ...[
                const SizedBox(height: DS.lg),
                Container(
                  padding: const EdgeInsets.all(DS.sm),
                  decoration: BoxDecoration(
                    color: DS.surfacePanel,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.pause_circle,
                        color: DS.brandPrimaryConst,
                        size: 20,
                      ),
                      const SizedBox(width: DS.smConst),
                      Text(
                        context.l10n.knowledgeDecayPaused,
                        style: DS.bodyMedium.copyWith(color: DS.textPrimary),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      );

  Color _getMasteryColor() {
    if (stats.masteryScore >= 95) return DS.prismPurple;
    if (stats.masteryScore >= 80) return DS.success;
    if (stats.masteryScore >= 30) return DS.brandPrimary;
    if (stats.masteryScore > 0) return DS.brandPrimary;
    return DS.brandPrimary;
  }

  String _formatReviewDate(BuildContext context, DateTime date) {
    final now = DateTime.now();
    final diff = date.difference(now);
    if (diff.inDays == 0) return context.l10n.knowledgeToday;
    if (diff.inDays == 1) return context.l10n.knowledgeTomorrow;
    if (diff.inDays < 7) return context.l10n.knowledgeDaysLater(diff.inDays);
    return context.l10n.knowledgeWeeksLater((diff.inDays / 7).floor());
  }
}

class _StatItem extends StatelessWidget {
  const _StatItem({
    required this.icon,
    required this.value,
    required this.label,
  });
  final IconData icon;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Icon(icon, color: DS.brandPrimary),
          const SizedBox(height: DS.xs),
          Text(
            value,
            style: DS.bodyLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(
            label,
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
          ),
        ],
      );
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.child,
  });
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              GraphiteSectionTitle(
                title: title,
              ),
              const SizedBox(height: DS.spacing12),
              child,
            ],
          ),
        ),
      );
}

class _NodeExpansionSheet extends ConsumerStatefulWidget {
  const _NodeExpansionSheet({
    required this.nodeId,
    required this.nodeName,
    required this.onApplied,
  });

  final String nodeId;
  final String nodeName;
  final VoidCallback onApplied;

  @override
  ConsumerState<_NodeExpansionSheet> createState() =>
      _NodeExpansionSheetState();
}

class _NodeExpansionSheetState extends ConsumerState<_NodeExpansionSheet> {
  bool _isGenerating = false;
  bool _isApplying = false;
  String? _error;
  String? _promptVersion;
  List<NodeExpansionCandidate> _candidates = const <NodeExpansionCandidate>[];
  final Set<String> _selectedIds = <String>{};

  Future<void> _generateCandidates() async {
    setState(() {
      _isGenerating = true;
      _error = null;
    });
    try {
      final response = await ref
          .read(galaxyRepositoryProvider)
          .generateExpansionCandidates(widget.nodeId);
      if (!mounted) {
        return;
      }
      setState(() {
        _promptVersion = response.promptVersion;
        _candidates = response.candidates;
        _selectedIds
          ..clear()
          ..addAll(response.candidates.map((item) => item.candidateId));
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '').trim();
      });
    } finally {
      if (mounted) {
        setState(() => _isGenerating = false);
      }
    }
  }

  Future<void> _applySelected() async {
    final selected = _candidates
        .where((item) => _selectedIds.contains(item.candidateId))
        .toList(growable: false);
    if (selected.isEmpty) {
      Navigator.of(context).pop();
      return;
    }

    setState(() {
      _isApplying = true;
      _error = null;
    });
    try {
      final created =
          await ref.read(galaxyRepositoryProvider).applyExpansionCandidates(
                widget.nodeId,
                promptVersion: _promptVersion ?? 'v1',
                candidates: selected,
              );
      if (!mounted) {
        return;
      }
      widget.onApplied();
      Navigator.of(context).pop();
      AppFeedback.success(
        context,
        created.isEmpty ? '候选节点已处理。' : '已将 ${created.length} 个节点纳入星图。',
      );
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '').trim();
      });
    } finally {
      if (mounted) {
        setState(() => _isApplying = false);
      }
    }
  }

  String _relationLabel(String relation) {
    switch (relation) {
      case 'prerequisite':
        return '前置';
      case 'application':
        return '应用';
      case 'evolution':
        return '进阶';
      default:
        return '相关';
    }
  }

  @override
  Widget build(BuildContext context) {
    final mediaQuery = MediaQuery.of(context);
    final maxSheetHeight = (mediaQuery.size.height -
            mediaQuery.viewPadding.top -
            mediaQuery.viewPadding.bottom) *
        0.72;

    return SizedBox(
      height: maxSheetHeight,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '围绕“${widget.nodeName}”生成 3 个候选节点，再由你决定哪些真正写入知识星图。',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          const SizedBox(height: DS.md),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (_candidates.isEmpty && !_isGenerating)
                    SparkleButton(
                      label: '生成 3 个候选节点',
                      icon: const Icon(Icons.auto_awesome),
                      expand: true,
                      onPressed: _generateCandidates,
                    ),
                  if (_isGenerating)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: DS.spacing24),
                      child: Center(child: CircularProgressIndicator()),
                    ),
                  if (_error != null) ...[
                    Text(
                      _error!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.error,
                          ),
                    ),
                    const SizedBox(height: DS.sm),
                  ],
                  if (_candidates.isNotEmpty) ...[
                    ..._candidates.map(
                      (candidate) => Container(
                        margin: const EdgeInsets.only(bottom: DS.spacing12),
                        decoration: BoxDecoration(
                          color: DS.surfacePanel,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: _selectedIds.contains(candidate.candidateId)
                                ? DS.brandPrimary.withValues(alpha: 0.28)
                                : DS.neutral200,
                          ),
                        ),
                        child: CheckboxListTile(
                          value: _selectedIds.contains(candidate.candidateId),
                          controlAffinity: ListTileControlAffinity.leading,
                          title: Text(candidate.name),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const SizedBox(height: DS.xs),
                              Text(candidate.description),
                              const SizedBox(height: DS.xs),
                              Wrap(
                                spacing: DS.spacing8,
                                runSpacing: DS.spacing8,
                                children: [
                                  _CandidateMetaChip(
                                      _relationLabel(candidate.relationToTrigger)),
                                  _CandidateMetaChip(
                                      '重要度 ${candidate.importanceLevel}'),
                                  ...candidate.keywords
                                      .take(2)
                                      .map(_CandidateMetaChip.new),
                                ],
                              ),
                            ],
                          ),
                          onChanged: _isApplying
                              ? null
                              : (selected) {
                                  setState(() {
                                    if (selected == true) {
                                      _selectedIds.add(candidate.candidateId);
                                    } else {
                                      _selectedIds.remove(candidate.candidateId);
                                    }
                                  });
                                },
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          if (_candidates.isNotEmpty) ...[
            const SizedBox(height: DS.md),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                SparkleButton(
                  label: '重新生成',
                  variant: ButtonVariant.secondary,
                  onPressed: _isApplying ? null : _generateCandidates,
                ),
                SparkleButton(
                  label: _selectedIds.isEmpty ? '本次不纳入' : '纳入星图',
                  icon: _isApplying
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.hub_outlined),
                  loading: _isApplying,
                  onPressed: _isApplying ? null : _applySelected,
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _CandidateMetaChip extends StatelessWidget {
  const _CandidateMetaChip(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: DS.brandPrimary,
                fontWeight: FontWeight.w700,
              ),
        ),
      );
}
