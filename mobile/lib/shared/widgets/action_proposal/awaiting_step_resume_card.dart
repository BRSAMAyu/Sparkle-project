import 'dart:async';

import 'package:flutter/material.dart';

import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/agent_run_read_service.dart';
import 'package:sparkle/shared/widgets/action_proposal/proposal_card_models.dart';

/// X-07 · Hybrid Handoff「恢复到 awaiting step」卡片（U-04 交互族挂载面）.
///
/// **不重建组件**：ownership 词表（[ProposalTurnOwnership]，"你做 / Sparkle做 /
/// 一起做"）、防抖（[ProposalActionGuard]）与文案全部复用 U-04
/// （proposal_card_models.dart / ActionProposalCard 的设计语言）；数据面是
/// X-07 run 步骤投影（[AgentRunAwaitingStep]，服务端从 ``agent_runs.steps``
/// 推导——通知点击/冷启动重开直接渲染，不靠内存）。
///
/// 状态诚实（acceptance ②）：
/// - awaiting：显示"轮到谁 + 提示 + Agent 产物引用"和 **确认，继续**（确认
///   /编辑触发 resume）；幂等键由调用方经 [runStepActionIdempotencyKey]
///   确定性推导，服务端 first-wins——双击/重试绝不二次 resume；
/// - expired / cancelled：明确呈现"已过期 / 已取消"（复用 U-04 文案），
///   不再提供确认入口。
///
/// 组件为纯展示：所有网络行为经回调注入，不持有 provider/仓库依赖。
class AwaitingStepResumeCard extends StatefulWidget {
  const AwaitingStepResumeCard({
    required this.runId,
    required this.step,
    required this.onConfirm,
    super.key,
    this.onCancel,
    this.onRefresh,
    this.guard,
  });

  final String runId;
  final AgentRunAwaitingStep step;

  /// 确认/编辑该步（触发服务端幂等 resume）。回调收到稳定幂等键，调用方应
  /// 将其透传给 `POST /runs/{id}/steps/{stepId}/complete` 的 idempotency_key。
  final Future<void> Function(String idempotencyKey) onConfirm;

  /// 取消整个 run（awaiting 态可选次操作；user_cancelled 语义）。
  final Future<void> Function(String idempotencyKey)? onCancel;

  final VoidCallback? onRefresh;

  /// 测试注入用防抖器；缺省内部新建。
  final ProposalActionGuard? guard;

  @override
  State<AwaitingStepResumeCard> createState() => _AwaitingStepResumeCardState();
}

class _AwaitingStepResumeCardState extends State<AwaitingStepResumeCard> {
  late final ProposalActionGuard _guard = widget.guard ?? ProposalActionGuard();
  String? _error;

  ProposalTurnOwnership get _ownership =>
      proposalOwnershipFromWire(widget.step.owner);

  Future<void> _run(String action, Future<void> Function() op) async {
    await _guard.run(action, () async {
      try {
        await op();
        if (mounted) {
          setState(() => _error = null);
        }
      } on Exception catch (e) {
        // 失败不伪装成功：留在当前态，由卡片内联错误提示（服务端幂等保证
        // 重试安全——同键重发只会重放）。
        if (mounted) {
          setState(() => _error = e.toString());
        }
      }
    });
  }

  void _confirm() {
    final key = runStepIdempotencyKey(widget.runId, widget.step.stepId, 'confirm');
    unawaited(_run('confirm', () => widget.onConfirm(key)));
  }

  void _cancel() {
    final key = runStepIdempotencyKey(widget.runId, widget.step.stepId, 'cancel');
    final onCancel = widget.onCancel;
    if (onCancel != null) {
      unawaited(_run('cancel', () => onCancel(key)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final step = widget.step;

    final ownershipLabel = switch (_ownership) {
      ProposalTurnOwnership.human => l10n.proposalOwnershipHuman,
      ProposalTurnOwnership.agent => l10n.proposalOwnershipAgent,
      ProposalTurnOwnership.hybrid => l10n.proposalOwnershipHybrid,
    };

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
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
              SemanticPill(
                label: ownershipLabel,
                tone: PillTone.brand,
                icon: switch (_ownership) {
                  ProposalTurnOwnership.human => Icons.person_outline,
                  ProposalTurnOwnership.agent => Icons.smart_toy_outlined,
                  ProposalTurnOwnership.hybrid => Icons.group_outlined,
                },
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  step.isExpired
                      ? l10n.proposalStatusExpired
                      : step.isCancelled
                          ? l10n.proposalStatusCancelled
                          : l10n.proposalTurnYours,
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          if (step.isAwaiting) ...[
            if ((step.label ?? step.prompt) != null)
              Text(
                step.label != null && step.prompt != null
                    ? '${step.label}\n${step.prompt}'
                    : (step.label ?? step.prompt!),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            if (step.artifactRefs.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                l10n.runStepArtifactsTitle,
                style: Theme.of(context).textTheme.labelMedium,
              ),
              const SizedBox(height: DS.spacing4),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing4,
                children: [
                  for (final artifact in step.artifactRefs)
                    SemanticPill(label: artifact.label, tone: PillTone.neutral),
                ],
              ),
            ],
            const SizedBox(height: DS.spacing12),
              Text(
                l10n.runStepAwaitingHint,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            const SizedBox(height: DS.spacing12),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    // 在途防抖（ProposalActionGuard）：双击复用同一 Future，
                    // 服务端再以同键 first-wins——两层防线，绝无二次 resume。
                    onPressed: _guard.isInFlight('confirm') ? null : _confirm,
                    icon: _guard.isInFlight('confirm')
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.check),
                    label: Text(
                      _guard.isInFlight('confirm')
                          ? l10n.proposalConfirming
                          : l10n.runStepContinueCta,
                    ),
                  ),
                ),
                if (widget.onCancel != null) ...[
                  const SizedBox(width: DS.spacing8),
                  TextButton(
                    onPressed: _guard.isInFlight('cancel') ? null : _cancel,
                    child: Text(l10n.proposalActionCancel),
                  ),
                ],
              ],
            ),
          ] else ...[
            // expired / cancelled：明确终态，不给确认入口（acceptance ②）。
            Text(
              step.isExpired
                  ? l10n.proposalExpiredHint
                  : l10n.proposalCancelledHint,
              style: Theme.of(context).textTheme.bodyMedium,
            ),            if (widget.onRefresh != null) ...[
              const SizedBox(height: DS.spacing8),
              TextButton(
                onPressed: widget.onRefresh,
                child: Text(l10n.proposalActionRefresh),
              ),
            ],
          ],
          if (_error != null) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              _error!,
              style: TextStyle(
                color: Theme.of(context).colorScheme.error,
                fontSize: 12,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// X-07 稳定幂等键（与 core/services/agent_run_command_service.dart 的
/// `runStepActionIdempotencyKey` 同构；组件侧本地推导避免 core←shared 反向
/// 依赖——键式 `x07:<runId>:<stepId>:<action>` 两处恒等，服务端语义不受影响）。
String runStepIdempotencyKey(String runId, String stepId, String action) =>
    'x07:$runId:$stepId:$action';
