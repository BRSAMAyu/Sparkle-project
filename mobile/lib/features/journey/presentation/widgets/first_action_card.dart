import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_card.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/journey/data/repositories/first_action_repository.dart';

/// J-04 · First Meaningful Action 卡（链路六环的移动端确认面）.
///
/// 职责（不重建真源）：
/// - **持久化回放**：状态唯一来自 `firstActionStateProvider`（GET
///   `/journey/first-action`）——重开 App 后 PENDING proposal / 已建任务原样
///   可见，不由本卡自造状态；
/// - **诚实失败**：生成失败显示错误 + 重试 + 跳过（[firstActionErrorRetryHint]），
///   永不把失败渲染成成功态；
/// - **feedback 不静默**：拒绝带理由、编辑带 delta，都经 repository 下发到
///   X-03/journey 端点落 append-only 审计；
/// - **Action 三字段可见**：产出（outcome）/ 完成证据（evidence）/ 轮到谁
///   （mode：你做 / Sparkle 做 / 一起做）逐项渲染，不用通用文案顶替。
///
/// 视觉纪律（J-03 唯一 primary CTA 归属 cockpit）：本卡所有按钮使用
/// outline/ghost 档，不与 cockpit 竞争主行动。
class FirstActionCard extends ConsumerStatefulWidget {
  const FirstActionCard({super.key});

  @override
  ConsumerState<FirstActionCard> createState() => _FirstActionCardState();
}

class _FirstActionCardState extends ConsumerState<FirstActionCard> {
  bool _generating = false;
  bool _mutating = false;
  String? _generationError;

  FirstActionRepository get _repository =>
      ref.read(firstActionRepositoryProvider);

  String _modeLabel(String executionMode) {
    final l10n = context.l10n;
    switch (executionMode) {
      case 'human':
        return l10n.firstActionModeHuman;
      case 'agent':
        return l10n.firstActionModeAgent;
      case 'hybrid':
        return l10n.firstActionModeHybrid;
      default:
        return l10n.firstActionModeHybrid;
    }
  }

  String _evidenceLabel(String evidenceKind) {
    final l10n = context.l10n;
    switch (evidenceKind) {
      case 'artifact':
      case 'file':
      case 'code':
        return l10n.firstActionEvidenceArtifact;
      case 'self_report':
      case 'user_confirmation':
        return l10n.firstActionEvidenceSelfReport;
      default:
        return l10n.firstActionEvidenceOther;
    }
  }

  Future<void> _generate() async {
    if (_generating) return;
    setState(() {
      _generating = true;
      _generationError = null;
    });
    try {
      // 幂等键：每次显式生成动作一个新键（重试 = 用户显式再点 → 新提案尝试；
      // 同一次点击的重复触达由 _generating 防抖挡住）。
      await _repository.generate(
        idempotencyKey:
            'first_action:gen:${DateTime.now().microsecondsSinceEpoch}',
      );
      ref.invalidate(firstActionStateProvider);
    } on FirstActionGenerationException catch (e) {
      if (!mounted) return;
      setState(() {
        _generationError = e.noGoal
            ? context.l10n.firstActionGenerateHint
            : context.l10n.firstActionErrorRetryHint;
      });
    } catch (_) {
      if (!mounted) return;
      // 诚实：网络层失败同样可见可重试，不静默、不假装成功。
      setState(() {
        _generationError = context.l10n.firstActionErrorRetryHint;
      });
    } finally {
      if (mounted) {
        setState(() => _generating = false);
      }
    }
  }

  Future<void> _approve(String proposalId) async {
    if (_mutating) return;
    setState(() => _mutating = true);
    try {
      await _repository.approve(proposalId, 'u04:$proposalId:approve');
      ref.invalidate(firstActionStateProvider);
    } finally {
      if (mounted) {
        setState(() => _mutating = false);
      }
    }
  }

  Future<void> _reject(String proposalId) async {
    final reasonController = TextEditingController();
    final reason = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(dialogContext.l10n.firstActionRejectCta),
        content: TextField(
          controller: reasonController,
          maxLines: 2,
          decoration: InputDecoration(
            hintText: dialogContext.l10n.firstActionRejectReasonLabel,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: Text(dialogContext.l10n.cancel),
          ),
          TextButton(
            onPressed: () =>
                Navigator.of(dialogContext).pop(reasonController.text),
            child: Text(dialogContext.l10n.firstActionRejectConfirm),
          ),
        ],
      ),
    );
    if (reason == null || _mutating) return;
    setState(() => _mutating = true);
    try {
      // J-04 feedback 面：理由随 reject 下发——服务端落 append-only 审计，
      // 用户的"这个不合适"不静默丢弃（理由可空：仍走既有拒绝语义）。
      await _repository.reject(
        proposalId,
        'u04:$proposalId:reject',
        reason: reason,
      );
      ref.invalidate(firstActionStateProvider);
    } finally {
      if (mounted) {
        setState(() => _mutating = false);
      }
    }
  }

  Future<void> _edit(String proposalId, FirstActionStep step) async {
    final titleController = TextEditingController(text: step.title);
    final minutesController = TextEditingController(
      text: step.estimatedMinutes?.toString() ?? '',
    );
    final result = await showDialog<({String title, int? minutes, String reason})>(
      context: context,
      builder: (dialogContext) {
        final reasonController = TextEditingController();
        return AlertDialog(
          title: Text(dialogContext.l10n.firstActionEditTitle),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleController,
                decoration: InputDecoration(
                  labelText: dialogContext.l10n.firstActionEditStepLabel,
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: minutesController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: dialogContext.l10n.firstActionEditMinutesLabel,
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: reasonController,
                decoration: InputDecoration(
                  hintText: dialogContext.l10n.firstActionEditReasonHint,
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: Text(dialogContext.l10n.cancel),
            ),
            TextButton(
              onPressed: () {
                final minutes = int.tryParse(minutesController.text.trim());
                Navigator.of(dialogContext).pop((
                  title: titleController.text.trim(),
                  minutes: minutes,
                  reason: reasonController.text.trim(),
                ),);
              },
              child: Text(dialogContext.l10n.firstActionEditSave),
            ),
          ],
        );
      },
    );
    if (result == null || _mutating) return;
    if (result.title.isEmpty) return;
    final edited = <String, dynamic>{'title': result.title};
    if (result.minutes != null) {
      edited['estimated_minutes'] = result.minutes;
    }
    setState(() => _mutating = true);
    try {
      // 编辑 = 拒绝旧提案（delta 进 feedback 审计）+ 同链路重提案（服务端保证）。
      await _repository.edit(
        proposalId,
        editedFields: edited,
        reason: result.reason.isEmpty ? null : result.reason,
        idempotencyKey: 'first_action:edit:$proposalId',
      );
      ref.invalidate(firstActionStateProvider);
    } finally {
      if (mounted) {
        setState(() => _mutating = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final stateAsync = ref.watch(firstActionStateProvider);
    final state = stateAsync.valueOrNull;
    // 守门：未加载 / 无目标 / 不该见的场景一律零布局影响（dashboard 挂载面）。
    if (state?.goal == null) {
      return const SizedBox.shrink();
    }
    final colors = context.colors;
    final typo = context.typo;
    final l10n = context.l10n;

    return SparkleCard(
      borderColor: colors.brandPrimary.withAlpha(48),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.flag_outlined, size: 18, color: colors.brandPrimary),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  l10n.firstActionCardTitle,
                  style: typo.titleMedium.copyWith(color: colors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            state!.goal!.title,
            style: typo.bodySmall.copyWith(color: colors.textSecondary),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 12),
          _buildBody(context, state),
        ],
      ),
    );
  }

  Widget _buildBody(BuildContext context, FirstActionState state) {
    final l10n = context.l10n;
    final colors = context.colors;
    final typo = context.typo;

    // 生成失败 → 诚实错误面：可见 + 可重试 + 可跳过（不假装成功）。
    if (_generationError != null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.error_outline, size: 18, color: colors.warning),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  l10n.firstActionErrorTitle,
                  style: typo.titleSmall.copyWith(color: colors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            _generationError!,
            style: typo.bodySmall.copyWith(color: colors.textSecondary),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              SparkleButton(
                label: l10n.firstActionRetryCta,
                variant: ButtonVariant.outline,
                onPressed: _generating ? () {} : _generate,
                loading: _generating,
              ),
              const SizedBox(width: 8),
              SparkleButton.ghost(
                label: l10n.firstActionSkipCta,
                onPressed:
                    _generating || _mutating ? () {} : () => setState(() {
                          _generationError = null;
                        }),
              ),
            ],
          ),
        ],
      );
    }

    // PENDING proposal → 确认面：三字段 + 开始 / 不合适 / 编辑。
    if (state.hasPendingProposal) {
      final proposalId = state.proposalId!;
      final step = FirstActionStep.fromProposal(state.proposal);
      if (step == null) {
        return const SizedBox.shrink();
      }
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            step.title,
            style: typo.titleSmall.copyWith(color: colors.textPrimary),
          ),
          if (step.stepDescription.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              step.stepDescription,
              style: typo.bodySmall.copyWith(color: colors.textSecondary),
            ),
          ],
          const SizedBox(height: 10),
          _factRow(l10n.firstActionOutcomeLabel, step.outcome),
          _factRow(
            l10n.firstActionEvidenceLabel,
            _evidenceLabel(step.evidenceKind),
          ),
          _factRow(
            l10n.firstActionModeLabel,
            step.estimatedMinutes != null
                ? '${_modeLabel(step.executionMode)} · '
                    '${l10n.firstActionMinutes(step.estimatedMinutes!)}'
                : _modeLabel(step.executionMode),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              SparkleButton(
                label: l10n.firstActionStartCta,
                variant: ButtonVariant.outline,
                onPressed: _mutating ? () {} : () => _approve(proposalId),
                loading: _mutating,
              ),
              const SizedBox(width: 8),
              SparkleButton.ghost(
                label: l10n.firstActionRejectCta,
                onPressed: _mutating ? () {} : () => _reject(proposalId),
              ),
              const SizedBox(width: 8),
              SparkleButton.ghost(
                label: l10n.firstActionEditCta,
                onPressed: _mutating ? () {} : () => _edit(proposalId, step),
              ),
            ],
          ),
        ],
      );
    }

    // 已 commit → 任务已在账本（重开可见的持久化证据面）。
    if (state.hasCommittedProposal && state.tasks.isNotEmpty) {
      final task = state.tasks.first;
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.check_circle_outline,
                  size: 18, color: colors.success,),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  l10n.firstActionCommittedTitle,
                  style: typo.titleSmall.copyWith(color: colors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            l10n.firstActionTaskCreated(task.title),
            style: typo.bodySmall.copyWith(color: colors.textSecondary),
          ),
        ],
      );
    }

    // 还没有提案 → 生成入口（outline 档，不与 cockpit 抢 primary）。
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.firstActionGenerateHint,
          style: typo.bodySmall.copyWith(color: colors.textSecondary),
        ),
        const SizedBox(height: 10),
        SparkleButton(
          label: l10n.firstActionGenerateCta,
          variant: ButtonVariant.outline,
          onPressed: _generating ? () {} : _generate,
          loading: _generating,
        ),
      ],
    );
  }

  Widget _factRow(String label, String value) {
    final colors = context.colors;
    final typo = context.typo;
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 72,
            child: Text(
              label,
              style: typo.labelSmall.copyWith(color: colors.textTertiary),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: typo.bodySmall.copyWith(color: colors.textPrimary),
            ),
          ),
        ],
      ),
    );
  }
}
