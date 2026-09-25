import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/agent_run_command_service.dart';
import 'package:sparkle/features/journey/data/models/hybrid_journey_models.dart';
import 'package:sparkle/features/journey/data/repositories/hybrid_journey_repository.dart';
import 'package:sparkle/shared/widgets/action_proposal/awaiting_step_resume_card.dart';
import 'package:sparkle/shared/widgets/action_proposal/proposal_card_models.dart';

/// J-06 · Hybrid 旗舰旅程统一入口（与 J-05 同一 modal 语义：GraphiteModalSurface）。
Future<void> showHybridJourneySheet(
  BuildContext context, {
  required HybridJourneyRepository repository,
  String? taskId,
  String? runId,
}) =>
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => DraggableScrollableSheet(
        initialChildSize: 0.68,
        minChildSize: 0.45,
        maxChildSize: 0.94,
        builder: (context, scrollController) => GraphiteModalSurface(
          title: sheetContext.l10n.hybridJourneySheetTitle,
          expandChild: true,
          child: SingleChildScrollView(
            controller: scrollController,
            child: HybridJourneySheetBody(
              repository: repository,
              taskId: taskId,
              runId: runId,
            ),
          ),
        ),
      ),
    );

/// J-06 · Hybrid 旗舰旅程承载面——「AI 降摩擦但不偷走目标」.
///
/// **统一交接面（不另起第二套）**：四段链（Agent prep → Human judgment →
/// Agent execute/check → Outcome）的 handoff 全部走 X-07 run 步骤机制的
/// 统一 Runtime/UI——「轮到谁」复用 U-04 ownership 词表（你做/Sparkle做/
/// 一起做）与 [ProposalActionGuard] 防抖；最终交付确认直接挂
/// [AwaitingStepResumeCard]（X-07 统一 awaiting-step 卡），幂等键经
/// [runStepActionIdempotencyKey] 确定性推导。本面只新增「判断选项」这一
/// 内容层（哪些材料进入交付），不重建任何交接机制。
///
/// 卡魂的 UI 面：判断段（你做）必须有至少一项选择才能提交——提交键在
/// 空选择时结构性禁用（AI 不代决的客户端呈现），并在页头显式说明
/// 「为什么这一步需要你决定」。
class HybridJourneySheetBody extends StatefulWidget {
  const HybridJourneySheetBody({
    required this.repository,
    this.taskId,
    this.runId,
    super.key,
  });

  final HybridJourneyRepository repository;
  final String? taskId;

  /// 已有旅程时直接回放（重开 App 持久化面）；缺省则启动新旅程。
  final String? runId;

  @override
  State<HybridJourneySheetBody> createState() => _HybridJourneySheetBodyState();
}

class _HybridJourneySheetBodyState extends State<HybridJourneySheetBody> {
  final ProposalActionGuard _guard = ProposalActionGuard();
  final TextEditingController _focusController = TextEditingController();
  final Set<String> _selectedRefs = <String>{};

  bool _loading = true;
  bool _busy = false;
  String? _error;
  HybridJourneyPayload? _payload;

  @override
  void initState() {
    super.initState();
    scheduleMicrotask(_load);
  }

  @override
  void dispose() {
    _focusController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final payload = widget.runId != null && widget.runId!.isNotEmpty
          ? await widget.repository.fetchState(runId: widget.runId!)
          : await widget.repository.start(
              taskId: widget.taskId,
              idempotencyKey: 'j06:start:${widget.taskId ?? 'auto'}',
            );
      if (!mounted) return;
      setState(() {
        _payload = payload;
        _loading = false;
      });
    } on HybridJourneyException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _loading = false;
      });
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _submitJudgment(List<HybridJourneyCitation> options) async {
    await _guard.run('judgment', () async {
      setState(() => _busy = true);
      try {
        final payload = await widget.repository.submitJudgment(
          runId: _payload!.runId,
          selectedRefs: _selectedRefs.toList(growable: false),
          idempotencyKey: 'j06:judge:${_payload!.runId}',
          focusNote: _focusController.text.trim(),
        );
        if (!mounted) return;
        setState(() {
          _payload = payload;
          _busy = false;
        });
      } on Exception catch (e) {
        if (!mounted) return;
        setState(() {
          _error = e.toString();
          _busy = false;
        });
      }
    });
  }

  Future<void> _confirmOutcome() async {
    await _guard.run('confirm', () async {
      setState(() => _busy = true);
      try {
        final payload = await widget.repository.confirmOutcome(
          runId: _payload!.runId,
          idempotencyKey:
              runStepActionIdempotencyKey(_payload!.runId, 'outcome', 'confirm'),
        );
        if (!mounted) return;
        setState(() {
          _payload = payload;
          _busy = false;
        });
      } on Exception catch (e) {
        if (!mounted) return;
        setState(() {
          _error = e.toString();
          _busy = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    if (_loading) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing32),
        child: Center(child: LoadingIndicator.circular(size: 28)),
      );
    }
    final payload = _payload;
    if (payload == null) {
      return _ErrorPane(message: _error ?? l10n.hybridJourneyLoadFailed, onRetry: _load);
    }
    return Column(
      key: const ValueKey('hybrid-journey-ready'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _StageChips(payload: payload),
        if (_error != null) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            _error!,
            style: context.typo.bodySmall.copyWith(
              color: context.colors.error,
              height: 1.45,
            ),
          ),
        ],
        if (payload.isAwaitingJudgment) _JudgmentPane(payload: payload, body: this),
        if (payload.isAwaitingOutcome) _OutcomePane(payload: payload, body: this),
        if (payload.isSucceeded) _DonePane(payload: payload),
        const SizedBox(height: DS.spacing24),
      ],
    );
  }
}

/// 四段链进度（「轮到谁」= U-04 ownership 词表，不重建文案）。
class _StageChips extends StatelessWidget {
  const _StageChips({required this.payload});

  final HybridJourneyPayload payload;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final completedSteps = payload.steps
        .where((s) => s.completed)
        .map((s) => s.stepId)
        .toSet();
    final awaitingId = payload.awaitingStep?.stepId;
    String stageLabel(String stage, String ownership) => switch (stage) {
          'prep' => '${l10n.hybridJourneyStagePrep} · ${l10n.proposalOwnershipAgent}',
          'judgment' => '${l10n.hybridJourneyStageJudgment} · ${l10n.proposalOwnershipHuman}',
          'execute_check' =>
            '${l10n.hybridJourneyStageExecuteCheck} · ${l10n.proposalOwnershipAgent}',
          _ => '${l10n.hybridJourneyStageOutcome} · ${l10n.proposalOwnershipHybrid}',
        };
    PillTone stageTone(String stage) {
      if (completedSteps.contains(stage) || payload.isSucceeded) {
        return PillTone.success;
      }
      if (awaitingId == stage) return PillTone.warning;
      return PillTone.neutral;
    }

    return Wrap(
      spacing: DS.spacing8,
      runSpacing: DS.spacing8,
      children: [
        for (final stage in const ['prep', 'judgment', 'execute_check', 'outcome'])
          SemanticPill(
            label: stageLabel(stage, ''),
            tone: stageTone(stage),
          ),
      ],
    );
  }
}

/// 判断段：为什么需要你决定 + 真实材料选项（至少选一项，AI 不代决）。
class _JudgmentPane extends StatelessWidget {
  const _JudgmentPane({required this.payload, required this.body});

  final HybridJourneyPayload payload;
  final _HybridJourneySheetBodyState body;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final brief = payload.judgmentBrief;
    final options = brief?.options ?? payload.citations;
    final selected = body._selectedRefs;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: DS.spacing20),
        _SectionHeader(label: l10n.hybridJourneyWhyHumanHeader),
        const SizedBox(height: DS.spacing8),
        Text(
          l10n.hybridJourneyJudgmentWhyHuman,
          style: context.typo.titleMedium.copyWith(
            color: context.colors.textPrimary,
            height: 1.45,
          ),
        ),
        const SizedBox(height: DS.spacing12),
        Text(
          l10n.hybridJourneySelectPrompt,
          style: context.typo.bodySmall.copyWith(
            color: context.colors.textSecondary,
            height: 1.45,
          ),
        ),
        const SizedBox(height: DS.spacing8),
        for (final option in options)
          _CitationOption(
            citation: option,
            selected: selected.contains(option.sourceRef),
            onChanged: body._busy
                ? null
                : (value) => body.setState(() {
                      if (value ?? false) {
                        selected.add(option.sourceRef);
                      } else {
                        selected.remove(option.sourceRef);
                      }
                    }),
          ),
        const SizedBox(height: DS.spacing8),
        TextField(
          controller: body._focusController,
          enabled: !body._busy,
          maxLines: 2,
          decoration: InputDecoration(
            hintText: l10n.hybridJourneyFocusHint,
            border: const OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: DS.spacing12),
        SizedBox(
          width: double.infinity,
          child: SparkleButton(
            key: const Key('hybrid-journey-submit-judgment'),
            label: l10n.hybridJourneySubmitJudgment,
            // 卡魂：空选择不提交——AI 不代决的客户端结构性呈现。
            disabled: selected.isEmpty || body._busy,
            onPressed: () => body._submitJudgment(options),
            expand: true,
          ),
        ),
      ],
    );
  }
}

/// 交付确认段：X-07 统一 awaiting-step 卡（handoff 不另起第二套交接面）。
class _OutcomePane extends StatelessWidget {
  const _OutcomePane({required this.payload, required this.body});

  final HybridJourneyPayload payload;
  final _HybridJourneySheetBodyState body;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final outlineCandidates = payload.artifacts
        .where((a) => a.stage == 'execute_check')
        .toList();
    final outline = outlineCandidates.isEmpty ? null : outlineCandidates.first;
    final awaiting = payload.awaitingStep;
    if (awaiting == null || outline == null) {
      return const SizedBox.shrink();
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: DS.spacing20),
        _SectionHeader(label: l10n.hybridJourneyOutcomeHeader),
        const SizedBox(height: DS.spacing8),
        if (outline.checkPassed)
          Row(
            children: [
              Icon(
                Icons.check_circle_outline,
                size: 18,
                color: DS.success,
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  l10n.hybridJourneyCheckPassed(outline.citations.length),
                  style: context.typo.bodySmall.copyWith(
                    color: context.colors.textSecondary,
                    height: 1.45,
                  ),
                ),
              ),
            ],
          ),
        const SizedBox(height: DS.spacing12),
        // 统一 Runtime/UI：交付确认 = X-07 awaiting step（幂等键确定性推导）。
        AwaitingStepResumeCard(
          runId: payload.runId,
          step: awaiting,
          onConfirm: (_) => body._confirmOutcome(),
        ),
      ],
    );
  }
}

class _DonePane extends StatelessWidget {
  const _DonePane({required this.payload});

  final HybridJourneyPayload payload;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final usedCitations = payload.artifacts
        .where((a) => a.stage == 'execute_check')
        .fold<int>(0, (sum, a) => sum + a.citations.length);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: DS.spacing20),
        Row(
          children: [
            Icon(Icons.verified_outlined, size: 20, color: DS.success),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                l10n.hybridJourneyDone(usedCitations),
                style: context.typo.titleMedium.copyWith(
                  color: context.colors.textPrimary,
                  height: 1.45,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _CitationOption extends StatelessWidget {
  const _CitationOption({
    required this.citation,
    required this.selected,
    required this.onChanged,
  });

  final HybridJourneyCitation citation;
  final bool selected;
  final ValueChanged<bool?>? onChanged;

  @override
  Widget build(BuildContext context) {
    final pages = citation.pageLabel;
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: DS.spacing8),
      color: selected ? DS.surfaceSecondary.withValues(alpha: 0.9) : null,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
        side: BorderSide(
          color: selected ? DS.success : DS.borderSubtle,
        ),
      ),
      child: CheckboxListTile(
        value: selected,
        onChanged: onChanged,
        controlAffinity: ListTileControlAffinity.leading,
        title: Text(
          '[${citation.citationId}] ${citation.fileName}'
          '${pages.isEmpty ? '' : ' · p.$pages'}',
          style: context.typo.bodyMedium.copyWith(
            fontWeight: DS.fontWeightBold,
            color: context.colors.textPrimary,
          ),
        ),
        subtitle: Text(
          citation.snippet,
          maxLines: 3,
          overflow: TextOverflow.ellipsis,
          style: context.typo.bodySmall.copyWith(
            color: context.colors.textSecondary,
            height: 1.4,
          ),
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Text(
        label,
        style: context.typo.labelLarge.copyWith(
          color: context.colors.textSecondary,
          fontWeight: DS.fontWeightBold,
        ),
      );
}

class _ErrorPane extends StatelessWidget {
  const _ErrorPane({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: DS.spacing16),
        Text(
          message,
          style: context.typo.bodyMedium.copyWith(
            color: context.colors.textSecondary,
          ),
        ),
        const SizedBox(height: DS.spacing12),
        SizedBox(
          width: double.infinity,
          child: SparkleButton.secondary(
            label: l10n.hybridJourneyRetry,
            onPressed: onRetry,
          ),
        ),
        const SizedBox(height: DS.spacing16),
      ],
    );
  }
}
