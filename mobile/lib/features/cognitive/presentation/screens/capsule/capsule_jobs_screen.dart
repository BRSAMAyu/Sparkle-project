import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/cognitive/data/models/capsule_generation_job_model.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';

/// 胶囊生成任务状态页
///
/// 显示所有胶囊生成任务的状态，支持查看详情和重试
class CapsuleJobsScreen extends ConsumerStatefulWidget {
  const CapsuleJobsScreen({super.key});

  @override
  ConsumerState<CapsuleJobsScreen> createState() => _CapsuleJobsScreenState();
}

class _CapsuleJobsScreenState extends ConsumerState<CapsuleJobsScreen> {
  @override
  void initState() {
    super.initState();
    // Load jobs on init
    Future.microtask(() {
      ref.read(generationJobsProvider.notifier).fetchJobs();
    });
  }

  @override
  Widget build(BuildContext context) {
    final jobsState = ref.watch(generationJobsProvider);

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('生成任务'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.read(generationJobsProvider.notifier).fetchJobs();
            },
          ),
        ],
      ),
      body: jobsState.when(
        data: (jobs) => jobs.isEmpty
            ? _buildEmptyState()
            : RefreshIndicator(
                onRefresh: () =>
                    ref.read(generationJobsProvider.notifier).fetchJobs(),
                child: ListView.builder(
                  padding: const EdgeInsets.all(DS.spacing16),
                  itemCount: jobs.length,
                  itemBuilder: (context, index) {
                    final job = jobs[index];
                    return _JobCard(job: job);
                  },
                ),
              ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('加载失败: $err')),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.task_alt_outlined,
              size: 64, color: DS.brandPrimary.withValues(alpha: 0.3)),
          const SizedBox(height: DS.lg),
          Text(
            '还没有生成任务',
            style: TextStyle(color: DS.textPrimary, fontSize: 16),
          ),
          const SizedBox(height: DS.sm),
          Text(
            '在设置页面调整偏好并生成胶囊',
            style: TextStyle(color: DS.textSecondary, fontSize: 14),
          ),
        ],
      ),
    );
  }
}

class _JobCard extends StatelessWidget {
  const _JobCard({required this.job});

  final CapsuleGenerationJobModel job;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      margin: const EdgeInsets.only(bottom: DS.spacing16),
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: isDark ? DS.surfaceTertiary : DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(
          color: _getStatusColor().withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 头部：状态和类型
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: _getStatusColor().withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius8,
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(job.statusEmoji),
                    const SizedBox(width: 4),
                    Text(
                      job.statusEnum.label,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: _getStatusColor(),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: isDark
                      ? DS.neutral700
                      : DS.neutral200,
                  borderRadius: DS.borderRadius8,
                ),
                child: Text(
                  job.typeEnum.label,
                  style: TextStyle(
                    fontSize: 12,
                    color: DS.textSecondary,
                  ),
                ),
              ),
              const Spacer(),
              Text(
                _formatTime(job.createdAt),
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),

          // 进度条 (仅在生成中时显示)
          if (job.isGenerating) ...[
            LinearProgressIndicator(
              value: job.progress,
              backgroundColor: isDark ? DS.neutral700 : DS.neutral200,
              valueColor: AlwaysStoppedAnimation<Color>(DS.primaryBase),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              '生成中... ${job.progressPercent}%',
              style: TextStyle(fontSize: 12, color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing12),
          ],

          // 偏好信息
          Row(
            children: [
              Icon(Icons.timeline_outlined, size: 14, color: DS.info),
              const SizedBox(width: 4),
              Text(
                '深度: ${(job.depthPreference * 100).toInt()}%',
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
              const SizedBox(width: DS.spacing16),
              Icon(Icons.lightbulb_outline, size: 14, color: DS.warning),
              const SizedBox(width: 4),
              Text(
                '好奇: ${(job.curiosityPreference * 100).toInt()}%',
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),

          // 数量信息
          Row(
            children: [
              Text(
                '请求数量: ${job.requestedCount}',
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
              const SizedBox(width: DS.spacing16),
              if (job.actualCount != null)
                Text(
                  '实际数量: ${job.actualCount}',
                  style: TextStyle(
                    fontSize: 12,
                    color: job.isCompleted ? DS.success : DS.textSecondary,
                  ),
                ),
            ],
          ),

          // 错误信息 (仅失败时显示)
          if (job.isFailed && job.errorMessage != null) ...[
            const SizedBox(height: DS.spacing12),
            Container(
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: DS.error.withValues(alpha: 0.1),
                borderRadius: DS.borderRadius8,
                border: Border.all(color: DS.error.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  Icon(Icons.error_outline, size: 16, color: DS.error),
                  const SizedBox(width: DS.sm),
                  Expanded(
                    child: Text(
                      job.errorMessage!,
                      style: TextStyle(fontSize: 12, color: DS.error),
                    ),
                  ),
                ],
              ),
            ),
          ],

          // 完成后的胶囊链接
          if (job.isCompleted && job.capsuleIds != null && job.capsuleIds!.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: job.capsuleIds!.map((id) {
                return Chip(
                  label: Text('胶囊 $id'),
                  avatar: Icon(Icons.check_circle_outline, size: 16),
                  backgroundColor: isDark ? DS.neutral700 : DS.neutral200,
                  onPressed: () {
                    // TODO: 导航到胶囊详情
                  },
                );
              }).toList(),
            ),
          ],

          // 操作按钮
          const SizedBox(height: DS.spacing12),
          Row(
            children: [
              if (job.isFailed)
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {
                      // TODO: 重试
                    },
                    icon: const Icon(Icons.refresh),
                    label: const Text('重试'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: DS.primaryBase,
                    ),
                  ),
                ),
              if (job.isFailed) const SizedBox(width: DS.spacing8),
              if (job.isCompleted && job.capsuleIds != null && job.capsuleIds!.isNotEmpty)
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () {
                      // TODO: 查看生成的胶囊
                    },
                    icon: const Icon(Icons.visibility),
                    label: const Text('查看胶囊'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: DS.primaryBase,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Color _getStatusColor() {
    switch (job.statusEnum) {
      case JobStatus.pending:
        return DS.textSecondary;
      case JobStatus.generating:
        return DS.info;
      case JobStatus.completed:
        return DS.success;
      case JobStatus.failed:
        return DS.error;
    }
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final diff = now.difference(time);

    if (diff.inMinutes < 1) {
      return '刚刚';
    } else if (diff.inHours < 1) {
      return '${diff.inMinutes} 分钟前';
    } else if (diff.inDays < 1) {
      return '${diff.inHours} 小时前';
    } else if (diff.inDays < 7) {
      return '${diff.inDays} 天前';
    } else {
      return '${time.month}-${time.day}';
    }
  }
}
