import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
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

    return detailAsync.when(
      loading: () => const GraphiteScaffold(
        role: SparklePageRole.content,
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (error, stack) => GraphiteScaffold(
        role: SparklePageRole.content,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '知识节点加载失败',
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
                label: '重新加载',
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

    return SparklePageScaffold(
      role: SparklePageRole.content,
      floatingActionButton: SparkleButton(
        label: '生成学习路径',
        icon: const Icon(Icons.timeline),
        onPressed: () {
          showModalBottomSheet<void>(
            context: context,
            isScrollControlled: true,
            backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
            builder: (context) => GraphiteModalSurface(
              title: '生成学习路径',
              child: LearningPathDialog(
                targetNodeId: nodeId,
                targetNodeName: detail.node.name,
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
              size: DS.touchTargetMinSize,
              icon: Icon(Icons.arrow_back, color: DS.textPrimary),
              onPressed: () => context.pop(),
            ),
            actions: [
              SparkleIconButton(
                variant: ButtonVariant.ghost,
                size: DS.touchTargetMinSize,
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
            ],
            flexibleSpace: FlexibleSpaceBar(
              background: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Color.lerp(
                          DS.surfaceCanvas, sectorStyle.primaryColor, 0.28)!,
                      Color.lerp(
                          DS.surfaceCanvas, sectorStyle.glowColor, 0.16)!,
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
              child: _MasteryCard(
                stats: detail.userStats,
                sectorColor: sectorStyle.primaryColor,
              ),
            ),
          ),

          // Description Section
          if (detail.node.description != null &&
              detail.node.description!.isNotEmpty)
            SliverToBoxAdapter(
              child: ContentConstraint(
                child: _SectionCard(
                  title: '描述',
                  child: Text(
                    detail.node.description!,
                    style: theme.textTheme.bodyMedium,
                  ),
                ),
              ),
            ),

          // Keywords
          if (detail.node.keywords.isNotEmpty)
            SliverToBoxAdapter(
              child: ContentConstraint(
                child: _SectionCard(
                  title: '关键词',
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

          // Related Knowledge Nodes
          if (detail.relations.isNotEmpty)
            SliverToBoxAdapter(
              child: ContentConstraint(
                child: _SectionCard(
                  title: '相关知识',
                  child: Column(
                    children: detail.relations.map((relation) {
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
                          context.push('/galaxy/node/$relatedNodeId');
                        },
                      );
                    }).toList(),
                  ),
                ),
              ),
            ),

          // Related Tasks
          if (detail.relatedTasks.isNotEmpty)
            SliverToBoxAdapter(
              child: ContentConstraint(
                child: _SectionCard(
                  title: '相关任务',
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
                            subtitle: Text('预计 ${task.estimatedMinutes} 分钟'),
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () {
                              context.push('/tasks/${task.id}');
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
                  title: '相关计划',
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
                              plan.planType == 'sprint' ? '冲刺计划' : '成长计划',
                            ),
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () {
                              if (plan.planType == 'sprint') {
                                context.push('/sprint');
                              } else {
                                context.push('/growth');
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
                    '掌握度',
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
                    label: '学习分钟',
                  ),
                  _StatItem(
                    icon: Icons.repeat,
                    value: '${stats.studyCount}',
                    label: '学习次数',
                  ),
                  if (stats.nextReviewAt != null)
                    _StatItem(
                      icon: Icons.event,
                      value: _formatReviewDate(stats.nextReviewAt!),
                      label: '下次复习',
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
                        '遗忘衰减已暂停',
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

  String _formatReviewDate(DateTime date) {
    final now = DateTime.now();
    final diff = date.difference(now);
    if (diff.inDays == 0) return '今天';
    if (diff.inDays == 1) return '明天';
    if (diff.inDays < 7) return '${diff.inDays}天后';
    return '${(diff.inDays / 7).floor()}周后';
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
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Padding(
          padding: const EdgeInsets.all(DS.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              GraphiteSectionTitle(
                title: title,
              ),
              const SizedBox(height: DS.md),
              child,
            ],
          ),
        ),
      );
}
