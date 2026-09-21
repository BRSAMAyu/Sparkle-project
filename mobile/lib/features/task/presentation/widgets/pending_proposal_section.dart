import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/task/data/repositories/action_proposal_repository.dart';
import 'package:sparkle/shared/widgets/action_proposal/action_proposal_card.dart';

/// U-04 · task 侧 Action Proposal 挂载区块.
///
/// 从 X-03 proposal 收件箱（`GET /action-proposals?subject_id=<taskId>`，
/// PENDING 过滤）拉取本任务名下的待确认 proposal，渲染与 chat 页**同一个**
/// [ActionProposalCard]（单一组件双挂载）。命令经统一 command path 转发；
/// 幂等键由卡片稳定推导并透传（防抖在卡片内，重复点击不双发）。
class PendingProposalSection extends ConsumerWidget {
  const PendingProposalSection({required this.taskId, super.key});

  final String taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final proposalsAsync = ref.watch(pendingTaskProposalsProvider(taskId));
    final cards =
        proposalsAsync.valueOrNull ?? const <ActionProposalCardData>[];
    if (cards.isEmpty) {
      return const SizedBox.shrink();
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final proposal in cards) ...[
          ActionProposalCard(
            data: proposal,
            onApprove: (idempotencyKey) async {
              await ref
                  .read(actionProposalRepositoryProvider)
                  .approve(proposal.proposalId, idempotencyKey);
              ref.invalidate(pendingTaskProposalsProvider(taskId));
            },
            onReject: (idempotencyKey) async {
              await ref
                  .read(actionProposalRepositoryProvider)
                  .reject(proposal.proposalId, idempotencyKey);
              ref.invalidate(pendingTaskProposalsProvider(taskId));
            },
            onCancel: (idempotencyKey) async {
              await ref
                  .read(actionProposalRepositoryProvider)
                  .cancel(proposal.proposalId, idempotencyKey);
              ref.invalidate(pendingTaskProposalsProvider(taskId));
            },
            onReview: () =>
                ref.invalidate(pendingTaskProposalsProvider(taskId)),
            onRefresh: () =>
                ref.invalidate(pendingTaskProposalsProvider(taskId)),
          ),
          const SizedBox(height: DS.spacing12),
        ],
      ],
    );
  }
}
