import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/agent_run_command_service.dart';
import 'package:sparkle/core/services/agent_run_read_service.dart';
import 'package:sparkle/features/journey/data/models/hybrid_journey_models.dart';
import 'package:sparkle/features/journey/data/repositories/hybrid_journey_repository.dart';
import 'package:sparkle/features/journey/presentation/widgets/hybrid_journey_sheet.dart';
import 'package:sparkle/shared/widgets/action_proposal/awaiting_step_resume_card.dart';

/// V4-U04 · 运行工作台（FIX535：把孤儿 HybridJourneySheet 挂到运行面）.
///
/// 纪律（卡面 + SCREEN_FAMILIES「对话/卡住/Hybrid/运行台」段）：
/// - **运行台沿用 OpenClaw 路径与 Run ID，不创建像素版独立 Agent 中心**——
///   数据唯一来自 X-05/X-07 既有读面（`GET /runs?active=true`，客户端不是
///   runtime owner，本页零本地持久化、零第二真源）；不重建任何交接机制。
/// - **「轮到谁」一目了然**：每步标注 ownership（我来做 / 带我做 /
///   交给 Sparkle，I07 三种可读选择词表）；human 步骤只有用户本人确认才
///   推进——本页没有任何 agent 代推进控件，服务端 owner 纪律兜底。
/// - **中断/跨端恢复保持同 run**：恢复唯一锚点是 runId（`fetchState` /
///   `GET /runs`），幂等键确定性推导——重开 App / 换设备续跑同一段 run，
///   不新建 run、不重复生成工件；`step_replay=true` 呈现「已确认过」而非
///   报错（X-07 命令面挂载要求）。
/// - **不绕审批**：本页只是入口与读面；所有推进动作都落在既有门后端点
///   （旅程判断/交付确认、generic step complete 的 awaiting 校验）。取消是
///   显式确认后的 user_cancelled，终态如实呈现，不伪装成功。
///
/// RF-06 零触碰：本页为新页面文件，不改任何既有冲突面。
class HybridWorkbenchScreen extends ConsumerStatefulWidget {
  const HybridWorkbenchScreen({this.initialRunId, this.initialTaskId, super.key});

  /// 跨端/冷启动恢复深链锚点：缺省存在时进入本页即续跑**同一段**旅程
  /// （幂等读面回放，不 start 新 run）。
  final String? initialRunId;

  /// 从任务面带上下文进入时携带（start 幂等键按任务锚定，跨端同键同 run）。
  final String? initialTaskId;

  @override
  ConsumerState<HybridWorkbenchScreen> createState() =>
      _HybridWorkbenchScreenState();
}

class _HybridWorkbenchScreenState extends ConsumerState<HybridWorkbenchScreen> {
  bool _initialRunOpened = false;
  String? _replayNotice;

  @override
  void initState() {
    super.initState();
    scheduleMicrotask(() async {
      final initialRunId = widget.initialRunId;
      if (initialRunId == null || _initialRunOpened) return;
      _initialRunOpened = true;
      if (!mounted) return;
      await _openJourneySheet(runId: initialRunId);
    });
  }

  Future<void> _openJourneySheet({String? runId}) async {
    await showHybridJourneySheet(
      context,
      repository: ref.read(hybridJourneyRepositoryProvider),
      taskId: widget.initialTaskId,
      runId: runId,
    );
    // sheet 关闭后刷新运行列表（旅程可能已推进/完成）。
    if (mounted) {
      ref.invalidate(activeAgentRunsProvider);
    }
  }

  Future<void> _completeAwaitingStep({
    required String runId,
    required String stepId,
    required String idempotencyKey,
  }) async {
    final result = await ref.read(agentRunCommandServiceProvider).completeStep(
          runId,
          stepId,
          idempotencyKey: idempotencyKey,
        );
    // X-07 命令面挂载要求：step_replay=true 呈现「已确认过」，不报错。
    if (!mounted) return;
    setState(() {
      _replayNotice = result['step_replay'] == true
          ? context.l10n.workbenchReplayNotice
          : null;
    });
    ref.invalidate(activeAgentRunsProvider);
  }

  Future<void> _cancelRun(AgentRunView run, [String? idempotencyKey]) async {
    final l10n = context.l10n;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(l10n.workbenchCancelConfirmTitle),
        content: Text(l10n.workbenchCancelConfirmBody),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: Text(l10n.proposalActionCancel),
          ),
          TextButton(
            key: const Key('workbench_cancel_confirm_yes'),
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: Text(l10n.workbenchCancelConfirmYes),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    // 取消幂等键确定性推导：重试/重进同键，终态 first-wins 不重复取消。
    await ref.read(agentRunCommandServiceProvider).cancelRun(
          run.runId,
          idempotencyKey: idempotencyKey ??
              runStepActionIdempotencyKey(
                  run.runId, run.awaitingStep?.stepId ?? 'run', 'cancel',),
        );
    if (!mounted) return;
    ref.invalidate(activeAgentRunsProvider);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final runsAsync = ref.watch(activeAgentRunsProvider);

    Widget body;
    if (runsAsync.isLoading) {
      body = const Center(child: LoadingIndicator());
    } else if (runsAsync.hasError) {
      body = EmptyState(
        key: const Key('workbench_error'),
        icon: Icons.cloud_off_rounded,
        title: l10n.workbenchLoadFailed,
        description: '${runsAsync.error}',
        actionText: l10n.workbenchRetry,
        onAction: () => ref.invalidate(activeAgentRunsProvider),
      );
    } else {
      final runs = runsAsync.valueOrNull ?? const <AgentRunView>[];
      body = RefreshIndicator(
        onRefresh: () async => ref.refresh(activeAgentRunsProvider.future),
        child: ListView(
          key: const Key('workbench_list'),
          padding: const EdgeInsets.all(DS.md),
          children: [
            Text(
              l10n.workbenchRunCount(runs.length),
              style: Theme.of(context).textTheme.titleSmall,
            ),
            if (_replayNotice != null) ...[
              const SizedBox(height: DS.sm),
              SemanticPill(
                key: const Key('workbench_replay_notice'),
                label: _replayNotice!,
                tone: PillTone.neutral,
                icon: Icons.done_all_rounded,
              ),
            ],
            const SizedBox(height: DS.sm),
            if (runs.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: DS.lg),
                child: Text(
                  l10n.workbenchEmptyHint,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              )
            else
              for (final run in runs) ...[
                _buildRunCard(run),
                const SizedBox(height: DS.sm),
              ],
            const SizedBox(height: DS.md),
            Text(
              l10n.workbenchStartJourneyHint,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: DS.sm),
            OutlinedButton.icon(
              key: const Key('workbench_start_journey'),
              onPressed: _openJourneySheet,
              icon: const Icon(Icons.group_outlined),
              label: Text(l10n.workbenchStartJourney),
            ),
            const SizedBox(height: DS.xl),
          ],
        ),
      );
    }

    return Scaffold(
      key: const Key('hybrid_workbench_screen'),
      appBar: AppBar(title: Text(l10n.workbenchTitle)),
      body: body,
    );
  }

  Widget _buildRunCard(AgentRunView run) => _RunCard(
        run: run,
        onResumeJourney: _resumeJourney,
        onConfirmStep: _completeAwaitingStep,
        onCancelRun: (idempotencyKey) => _cancelRun(run, idempotencyKey),
      );

  void _resumeJourney(AgentRunView run) {
    unawaited(_openJourneySheet(runId: run.runId));
  }
}

/// 单段 run 卡：objective + 诚实状态 + 逐步骤 ownership + 恢复入口.
class _RunCard extends StatelessWidget {
  const _RunCard({
    required this.run,
    required this.onResumeJourney,
    required this.onConfirmStep,
    required this.onCancelRun,
  });

  final AgentRunView run;

  /// 旅程 run 的恢复入口（收到 run 上下文；sheet 内幂等回放同一段 run）。
  final void Function(AgentRunView run) onResumeJourney;
  final Future<void> Function({
    required String runId,
    required String stepId,
    required String idempotencyKey,
  }) onConfirmStep;

  /// 取消整段 run（确认对话框在父层；key 为空时父层按 (run, awaiting step)
  /// 确定性推导，重试/重进同键不重复取消）。
  final Future<void> Function(String? idempotencyKey) onCancelRun;

  bool get _isJourneyRun => run.traceId == kHybridJourneyTraceId;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final awaiting = run.awaitingStep;

    return Container(
      key: Key('workbench_run_card_${run.runId}'),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: DS.borderRadius16,
        boxShadow: DS.shadowSm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  run.objective,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: DS.fontWeightSemiBold,
                      ),
                ),
              ),
              const SizedBox(width: DS.sm),
              SemanticPill(label: _statusLabel(context, run.status), tone: _statusTone(run)),
            ],
          ),
          const SizedBox(height: DS.sm),
          // 逐步骤 ownership（我来做/带我做/交给 Sparkle；完成/等待如实标注）。
          Wrap(
            spacing: DS.xs,
            runSpacing: DS.xs,
            children: [
              for (final step in run.steps)
                SemanticPill(
                  label: '${_ownerLabel(context, step.owner)} · '
                      '${step.completed ? l10n.workbenchStepDone : (awaiting != null && awaiting.stepId == step.stepId ? l10n.workbenchStepAwaiting : l10n.workbenchStepWaiting)}',
                  tone: step.completed
                      ? PillTone.success
                      : (awaiting != null && awaiting.stepId == step.stepId
                          ? PillTone.warning
                          : PillTone.neutral),
                ),
            ],
          ),
          if (awaiting != null && awaiting.isAwaiting) ...[
            const SizedBox(height: DS.sm),
            if (_isJourneyRun)
              // 旅程 run：回同一张 HybridJourneySheet（同 run 幂等回放；
              // 判断/交付只能由用户在 sheet 内亲自推进）。
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  key: Key('workbench_resume_journey_${run.runId}'),
                  onPressed: () => onResumeJourney(run),
                  icon: const Icon(Icons.play_circle_outline_rounded),
                  label: Text(l10n.workbenchResumeJourney),
                ),
              )
            else ...[
              // 通用 run：X-07 统一 awaiting-step 卡（确认=用户本人推进；
              // 服务端 first-wins + 本页消费 step_replay）。
              AwaitingStepResumeCard(
                runId: run.runId,
                step: awaiting,
                onConfirm: (idempotencyKey) => onConfirmStep(
                  runId: run.runId,
                  stepId: awaiting.stepId,
                  idempotencyKey: idempotencyKey,
                ),
                onCancel: onCancelRun,
                onRefresh: () => onCancelRun(null),
              ),
            ],
          ],
          if (!run.isTerminal) ...[
            const SizedBox(height: DS.sm),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                key: Key('workbench_cancel_run_${run.runId}'),
                onPressed: () => onCancelRun(null),
                icon: const Icon(Icons.close_rounded, size: 16),
                label: Text(l10n.workbenchCancelRun),
              ),
            ),
          ],
        ],
      ),
    );
  }

  static String _ownerLabel(BuildContext context, String owner) {
    final l10n = context.l10n;
    switch (owner) {
      case 'human':
        return l10n.workbenchOwnershipHuman;
      case 'agent':
        return l10n.workbenchOwnershipAgent;
      default:
        return l10n.workbenchOwnershipHybrid;
    }
  }

  static String _statusLabel(BuildContext context, String status) {
    final l10n = context.l10n;
    switch (status.toUpperCase()) {
      case 'QUEUED':
        return l10n.workbenchStatusQueued;
      case 'RUNNING':
      case 'EXECUTING':
        return l10n.workbenchStatusRunning;
      case 'AWAITING_USER':
      case 'AWAITING_APPROVAL':
        return l10n.workbenchStatusAwaitingUser;
      case 'SUCCEEDED':
        return l10n.workbenchStatusSucceeded;
      case 'FAILED':
        return l10n.workbenchStatusFailed;
      case 'CANCELLED':
        return l10n.workbenchStatusCancelled;
      default:
        // 未知词表值原样呈现（诚实），不臆造成功/失败语义。
        return status;
    }
  }

  static PillTone _statusTone(AgentRunView run) {
    if (run.isAwaitingUser) return PillTone.warning;
    switch (run.status.toUpperCase()) {
      case 'SUCCEEDED':
        return PillTone.success;
      case 'FAILED':
      case 'CANCELLED':
        return PillTone.danger;
      case 'RUNNING':
      case 'EXECUTING':
        return PillTone.brand;
      default:
        return PillTone.neutral;
    }
  }
}
