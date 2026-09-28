import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/agent_run_read_service.dart';
import 'package:sparkle/features/journey/data/models/hybrid_journey_models.dart';
import 'package:sparkle/features/journey/data/repositories/hybrid_journey_repository.dart';
import 'package:sparkle/features/journey/presentation/widgets/hybrid_journey_sheet.dart';

/// 本任务名下进行中的 hybrid journey run（FIX535 恢复锚点）.
///
/// 只读投影：数据来自 X-05 既有读面 `GET /runs?active=true&task_id=`，客户端
/// 按 trace 标记过滤出旅程 run；不为零命中造状态。
final activeHybridJourneyRunForTaskProvider =
    FutureProvider.autoDispose.family<AgentRunView?, String>((ref, taskId) async {
  final runs = await ref.watch(agentRunReadServiceProvider).fetchActiveRuns(taskId: taskId);
  for (final run in runs) {
    if (run.traceId == kHybridJourneyTraceId) {
      return run;
    }
  }
  return null;
});

/// V4-U04 · 任务面 Hybrid 入口区块（FIX535：接到合法提案/运行面）.
///
/// 挂载于任务执行面的提案卡旁（与 [PendingProposalSection] 同一运行/提案面），
/// 只做**导航入口**，不携带任何审批语义：
/// - 有本任务进行中的旅程 run → 「继续一起推进」：以 runId 打开
///   HybridJourneySheet **续跑同一段 run**（幂等读面回放，不新建 run、不重复
///   生成工件）；
/// - 没有 → 「和 Sparkle 一起推进」：打开 sheet 启动旅程（start 幂等键按任务
///   锚定 `j06:start:<taskId>`，跨端同键同 run）；判断/交付审批门全部留在
///   sheet 内的服务端门后，本区块不预填、不代答、不绕审批。
/// - 读取失败 → 诚实错误文案，不渲染为可用状态。
class HybridJourneyEntrySection extends ConsumerWidget {
  const HybridJourneyEntrySection({required this.taskId, super.key});

  final String taskId;

  Future<void> _openSheet(
    WidgetRef ref,
    BuildContext context, {
    String? runId,
  }) async {
    await showHybridJourneySheet(
      context,
      repository: ref.read(hybridJourneyRepositoryProvider),
      taskId: taskId,
      runId: runId,
    );
    // sheet 关闭后刷新（旅程可能已推进/完成/取消）。
    ref
      ..invalidate(activeHybridJourneyRunForTaskProvider(taskId))
      ..invalidate(activeAgentRunsProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final runAsync = ref.watch(activeHybridJourneyRunForTaskProvider(taskId));

    // 读取中不闪占位（区块可整体缺席，不伪造入口可用性）。
    if (runAsync.isLoading) return const SizedBox.shrink();

    final run = runAsync.valueOrNull;
    final hasError = runAsync.hasError;

    return Container(
      key: const Key('hybrid_journey_entry_section'),
      width: double.infinity,
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary.withValues(alpha: 0.6),
        borderRadius: DS.borderRadius16,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.group_outlined, size: 18, color: DS.textSecondary),
              const SizedBox(width: DS.sm),
              Expanded(
                child: Text(
                  l10n.journeyEntryHint,
                  style: context.typo.bodySmall.copyWith(
                    color: context.colors.textSecondary,
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ),
          if (hasError) ...[
            const SizedBox(height: DS.sm),
            Text(
              l10n.journeyEntryFailed,
              style: context.typo.bodySmall.copyWith(
                color: context.colors.error,
              ),
            ),
          ],
          const SizedBox(height: DS.sm),
          if (run != null) ...[
            SemanticPill(
              label: _statusLabel(context, run),
              tone: run.isAwaitingUser ? PillTone.warning : PillTone.brand,
            ),
            const SizedBox(height: DS.sm),
          ],
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              key: Key(run != null
                  ? 'journey_entry_resume'
                  : 'journey_entry_start',),
              onPressed: () => _openSheet(ref, context, runId: run?.runId),
              icon: Icon(run != null
                  ? Icons.play_circle_outline_rounded
                  : Icons.group_outlined,),
              label: Text(run != null
                  ? l10n.journeyEntryResumeLabel
                  : l10n.journeyEntryStartLabel,),
            ),
          ),
        ],
      ),
    );
  }

  /// 入口区的诚实状态行（未知词表原样呈现，不臆造成功）。
  static String _statusLabel(BuildContext context, AgentRunView run) {
    final l10n = context.l10n;
    switch (run.status.toUpperCase()) {
      case 'AWAITING_USER':
      case 'AWAITING_APPROVAL':
        return l10n.workbenchStatusAwaitingUser;
      case 'RUNNING':
      case 'EXECUTING':
        return l10n.workbenchStatusRunning;
      case 'QUEUED':
        return l10n.workbenchStatusQueued;
      default:
        return run.status;
    }
  }
}
