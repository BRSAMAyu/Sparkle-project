import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/data/models/knowledge_detail_model.dart';
import 'package:sparkle/presentation/providers/knowledge_detail_provider.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/presentation/widgets/learning_path/learning_path_dialog.dart';

class KnowledgeDetailScreen extends ConsumerWidget {
  final String nodeId;

  const KnowledgeDetailScreen({required this.nodeId, super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(knowledgeDetailProvider(nodeId));

    return detailAsync.when(
      loading: () => const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (error, stack) => Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('Error: $error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.invalidate(knowledgeDetailProvider(nodeId)),
                child: const Text('Retry'),
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

    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        heroTag: 'learning_path_fab',
        onPressed: () {
          showModalBottomSheet(
            context: context,
            isScrollControlled: true,
            backgroundColor: Colors.transparent,
            builder: (context) => LearningPathDialog(
              targetNodeId: nodeId,
              targetNodeName: detail.node.name,
            ),
          );
        },
        label: const Text('生成学习路径'),
        icon: const Icon(Icons.timeline),
        backgroundColor: sectorStyle.primaryColor,
      ),
      body: CustomScrollView(
        slivers: [
          // Hero Header with sector gradient
        SliverAppBar(
          expandedHeight: 200,
          pinned: true,
          backgroundColor: sectorStyle.primaryColor,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back, color: Colors.white),
            onPressed: () => context.pop(),
          ),
          actions: [
            IconButton(
              icon: Icon(
                detail.userStats.isFavorite ? Icons.star : Icons.star_border,
                color: Colors.white,
              ),
              onPressed: () {
                ref.read(toggleFavoriteProvider(nodeId));
              },
            ),
          ],
          flexibleSpace: FlexibleSpaceBar(
            background: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    sectorStyle.primaryColor,
                    sectorStyle.glowColor.withAlpha(200),
                  ],
                ),
              ),
              child: SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(16),
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
                          color: Colors.white24,
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Text(
                          sectorStyle.name,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      // Node name
                      Text(
                        detail.node.name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (detail.node.nameEn != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          detail.node.nameEn!,
                          style: TextStyle(
                            color: Colors.white.withAlpha(200),
                            fontSize: 14,
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
          child: _MasteryCard(
            stats: detail.userStats,
            sectorColor: sectorStyle.primaryColor,
          ),
        ),

        // Description Section
        if (detail.node.description != null && detail.node.description!.isNotEmpty)
          SliverToBoxAdapter(
            child: _SectionCard(
              title: '描述',
              child: Text(
                detail.node.description!,
                style: theme.textTheme.bodyMedium,
              ),
            ),
          ),

        // Keywords
        if (detail.node.keywords.isNotEmpty)
          SliverToBoxAdapter(
            child: _SectionCard(
              title: '关键词',
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: detail.node.keywords.map((keyword) {
                  return Chip(
                    label: Text(keyword),
                    backgroundColor: sectorStyle.glowColor.withAlpha(50),
                  );
                }).toList(),
              ),
            ),
          ),

        // Related Knowledge Nodes
        if (detail.relations.isNotEmpty)
          SliverToBoxAdapter(
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

        // Related Tasks
        if (detail.relatedTasks.isNotEmpty)
          SliverToBoxAdapter(
            child: _SectionCard(
              title: '相关任务',
              child: Column(
                children: detail.relatedTasks.map((task) {
                  return ListTile(
                    leading: Icon(
                      Icons.task_alt,
                      color: task.status.name == 'completed'
                          ? Colors.green
                          : Colors.orange,
                    ),
                    title: Text(task.title),
                    subtitle: Text('预计 ${task.estimatedMinutes} 分钟'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      context.push('/tasks/${task.id}');
                    },
                  );
                }).toList(),
              ),
            ),
          ),

        // Related Plans
        if (detail.relatedPlans.isNotEmpty)
          SliverToBoxAdapter(
            child: _SectionCard(
              title: '相关计划',
              child: Column(
                children: detail.relatedPlans.map((plan) {
                  return ListTile(
                    leading: Icon(
                      plan.planType == 'sprint'
                          ? Icons.bolt
                          : Icons.trending_up,
                      color: sectorStyle.primaryColor,
                    ),
                    title: Text(plan.title),
                    subtitle: Text(plan.planType == 'sprint' ? '冲刺计划' : '成长计划'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      if (plan.planType == 'sprint') {
                        context.push('/sprint');
                      } else {
                        context.push('/growth');
                      }
                    },
                  );
                }).toList(),
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
  final KnowledgeUserStats stats;
  final Color sectorColor;

  const _MasteryCard({
    required this.stats,
    required this.sectorColor,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
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
                    color: _getMasteryColor().withAlpha(30),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Text(
                    stats.masteryLabel,
                    style: TextStyle(
                      color: _getMasteryColor(),
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Progress bar
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: stats.masteryProgress,
                minHeight: 12,
                backgroundColor: Colors.grey.shade200,
                valueColor: AlwaysStoppedAnimation<Color>(_getMasteryColor()),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '${stats.masteryScore.toStringAsFixed(0)}%',
              style: TextStyle(
                color: _getMasteryColor(),
                fontWeight: FontWeight.bold,
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 16),

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
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.orange.withAlpha(30),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.pause_circle, color: Colors.orange, size: 20),
                    SizedBox(width: 8),
                    Text(
                      '遗忘衰减已暂停',
                      style: TextStyle(color: Colors.orange),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Color _getMasteryColor() {
    if (stats.masteryScore >= 95) return Colors.purple;
    if (stats.masteryScore >= 80) return Colors.green;
    if (stats.masteryScore >= 30) return Colors.blue;
    if (stats.masteryScore > 0) return Colors.orange;
    return Colors.grey;
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
  final IconData icon;
  final String value;
  final String label;

  const _StatItem({
    required this.icon,
    required this.value,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: Colors.grey),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            color: Colors.grey.shade600,
            fontSize: 12,
          ),
        ),
      ],
    );
  }
}

class _SectionCard extends StatelessWidget {
  final String title;
  final Widget child;

  const _SectionCard({
    required this.title,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            child,
          ],
        ),
      ),
    );
  }
}
