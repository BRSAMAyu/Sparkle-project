import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/learning/data/learning_journey_models.dart';
import 'package:sparkle/features/learning/presentation/providers/learning_journey_provider.dart';
import 'package:sparkle/features/learning/presentation/widgets/learning_context_header.dart';
import 'package:sparkle/features/learning/presentation/widgets/learning_source_badge.dart';

/// 资料→错题→练习→检验旅程页（V4-U10 旗舰垂直旅程）。
///
/// 纪律（SCREEN_FAMILIES「星图/学习/错题/资料」段）：
/// - 材料、错题沿目标打开，主操作是「继续当前动作」，不回到空白搜索页丢上下文；
/// - 来源badge带版本；OCR失败/不支持 → 手输替代，不假装已识别；
/// - 检验入口走证据门（I07 脚手架：只在用户选择且证据支持时推进）。
class LearningJourneyScreen extends ConsumerWidget {
  const LearningJourneyScreen({required this.journeyContext, super.key});

  final LearningJourneyContext journeyContext;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(learningJourneyProvider(journeyContext));
    final l10n = context.l10n;

    Widget body;
    if (state.loading && state.view == null) {
      body = const Center(child: LoadingIndicator());
    } else if (state.error != null && state.view == null) {
      body = EmptyState(
        key: const Key('learning_journey_error'),
        icon: Icons.cloud_off_rounded,
        title: l10n.learningJourneyLoadFailed,
        description: state.error,
        actionText: l10n.learningJourneyRetry,
        onAction: () =>
            ref.read(learningJourneyProvider(journeyContext).notifier).reload(),
      );
    } else {
      body = _JourneyBody(journeyContext: journeyContext, state: state);
    }

    return Scaffold(
      key: const Key('learning_journey_screen'),
      appBar: AppBar(title: Text(l10n.learningJourneyTitle)),
      body: body,
    );
  }
}

class _JourneyBody extends ConsumerWidget {
  const _JourneyBody({required this.journeyContext, required this.state});

  final LearningJourneyContext journeyContext;
  final LearningJourneyState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final view = state.view!;
    final l10n = context.l10n;
    final notifier = ref.read(learningJourneyProvider(journeyContext).notifier);

    return RefreshIndicator(
      onRefresh: notifier.reload,
      child: ListView(
        key: const Key('learning_journey_list'),
        padding: const EdgeInsets.all(DS.md),
        children: [
          LearningContextHeader(
            goalTitle: journeyContext.goalTitle,
            segmentBadgeLabel: _segmentLabel(context, view.scaffold.segment),
            continueLabel: _continueLabel(context, view.scaffold.segment),
            // 主操作 = 继续当前动作：请求检验入口（证据门由服务端裁决；
            // 未到检验由 HOLD 原地暂缓并提示，不进检验空页）。
            onContinue: () => ref.read(learningJourneyProvider(journeyContext).notifier).requestCheck(),
          ),
          const SizedBox(height: DS.md),
          _SectionHeader(index: 0, label: l10n.learningSegmentMaterials),
          if (view.materials.isEmpty)
            _EmptyHint(label: l10n.learningMaterialsEmpty)
          else
            ...view.materials.map(
              (material) => _MaterialCard(
                material: material,
                manualInput: state.manualInputs[material.source.sourceId],
                onManualInput: (text) =>
                    ref.read(learningJourneyProvider(journeyContext).notifier).saveManualInput(
                          material.source.sourceId,
                          text,
                        ),
              ),
            ),
          const SizedBox(height: DS.md),
          _SectionHeader(index: 1, label: l10n.learningSegmentErrors),
          if (view.errors.isEmpty)
            _EmptyHint(label: l10n.learningErrorsEmpty)
          else
            ...view.errors.map((error) => _ErrorCard(brief: error)),
          const SizedBox(height: DS.md),
          _SectionHeader(index: 2, label: l10n.learningSegmentCheck),
          _CheckCard(
            enabled: !state.submitting,
            evidenceSupported: view.evidenceSupported,
            holdReason: state.checkHoldReason,
            checkQuestion: state.checkQuestion,
            verdict: state.verdict,
            onSubmit: (answer) =>
                ref.read(learningJourneyProvider(journeyContext).notifier).submitCheckAnswer(answer),
          ),
        ],
      ),
    );
  }

  String _segmentLabel(BuildContext context, LearningSegment segment) {
    final l10n = context.l10n;
    switch (segment) {
      case LearningSegment.materials:
        return l10n.learningSegmentMaterials;
      case LearningSegment.errors:
        return l10n.learningSegmentErrors;
      case LearningSegment.practice:
        return l10n.learningSegmentPractice;
      case LearningSegment.independentCheck:
        return l10n.learningSegmentCheck;
    }
  }

  String _continueLabel(BuildContext context, LearningSegment segment) {
    final l10n = context.l10n;
    switch (segment) {
      case LearningSegment.independentCheck:
        return l10n.learningContinueCheck;
      case LearningSegment.materials:
      case LearningSegment.errors:
      case LearningSegment.practice:
        return l10n.learningContinuePractice;
    }
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.index, required this.label});

  final int index;
  final String label;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.sm),
        child: Text(
          label,
          key: Key('learning_section_$index'),
          style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
        ),
      );
}

class _EmptyHint extends StatelessWidget {
  const _EmptyHint({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.sm),
        child: Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(color: DS.textSecondary),
        ),
      );
}

class _MaterialCard extends StatefulWidget {
  const _MaterialCard({
    required this.material,
    required this.manualInput,
    required this.onManualInput,
  });

  final JourneyMaterial material;
  final String? manualInput;
  final ValueChanged<String> onManualInput;

  @override
  State<_MaterialCard> createState() => _MaterialCardState();
}

class _MaterialCardState extends State<_MaterialCard> {
  final TextEditingController _manualController = TextEditingController();

  @override
  void dispose() {
    _manualController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final parse = widget.material.parse;
    return Card(
      key: Key('learning_material_${widget.material.source.sourceId}'),
      margin: const EdgeInsets.only(bottom: DS.sm),
      child: Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    widget.material.fileName,
                    style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                _ParseStatusChip(parse: parse),
              ],
            ),
            const SizedBox(height: DS.sm),
            LearningSourceBadge(source: widget.material.source),
            if (parse.needsManualInput && widget.manualInput == null) ...[
              const SizedBox(height: DS.sm),
              // OCR 失败/不支持 → 手输替代（不假装已识别）。
              Text(
                l10n.learningManualInputHint,
                style: theme.textTheme.bodySmall?.copyWith(color: DS.warning),
              ),
              const SizedBox(height: DS.xs),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      key: Key('learning_manual_input_${widget.material.source.sourceId}'),
                      controller: _manualController,
                      decoration: InputDecoration(
                        hintText: l10n.learningManualInputHint,
                        isDense: true,
                        border: const OutlineInputBorder(),
                      ),
                      minLines: 1,
                      maxLines: 3,
                    ),
                  ),
                  const SizedBox(width: DS.sm),
                  TextButton(
                    key: Key('learning_manual_save_${widget.material.source.sourceId}'),
                    onPressed: () {
                      if (_manualController.text.trim().isNotEmpty) {
                        widget.onManualInput(_manualController.text);
                      }
                    },
                    child: Text(l10n.learningManualInputSave),
                  ),
                ],
              ),
            ] else if (widget.manualInput != null) ...[
              const SizedBox(height: DS.sm),
              Text(
                l10n.learningManualInputSaved,
                style: theme.textTheme.bodySmall?.copyWith(color: DS.semanticSuccess),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ParseStatusChip extends StatelessWidget {
  const _ParseStatusChip({required this.parse});

  final JourneyMaterialParse parse;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final (String label, Color color) = switch (parse.status) {
      JourneyParseStatus.parsed => (l10n.learningParseParsed, DS.semanticSuccess),
      JourneyParseStatus.pending => (l10n.learningParsePending, DS.textSecondary),
      JourneyParseStatus.failed => (l10n.learningParseFailed, DS.semanticError),
      JourneyParseStatus.unsupported => (l10n.learningParseUnsupported, DS.semanticWarning),
      JourneyParseStatus.manual => (l10n.learningParseManual, DS.info),
    };
    return Container(
      key: Key('learning_parse_status_${parse.status.name}'),
      padding: const EdgeInsets.symmetric(horizontal: DS.sm, vertical: DS.xs),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(color: color),
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  const _ErrorCard({required this.brief});

  final JourneyErrorBrief brief;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      key: Key('learning_error_${brief.id}'),
      margin: const EdgeInsets.only(bottom: DS.sm),
      child: Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    brief.questionText,
                    style: theme.textTheme.bodyMedium,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: DS.sm),
                Text(
                  context.l10n.learningReviewCount(brief.reviewCount),
                  style: theme.textTheme.labelSmall?.copyWith(color: DS.textSecondary),
                ),
              ],
            ),
            const SizedBox(height: DS.sm),
            LearningSourceBadge(source: brief.source, compact: true),
          ],
        ),
      ),
    );
  }
}

class _CheckCard extends StatefulWidget {
  const _CheckCard({
    required this.enabled,
    required this.evidenceSupported,
    required this.holdReason,
    required this.checkQuestion,
    required this.verdict,
    required this.onSubmit,
  });

  final bool enabled;
  final bool evidenceSupported;
  final String? holdReason;
  final LearningCheckQuestion? checkQuestion;
  final LearningCheckVerdict? verdict;
  final ValueChanged<String> onSubmit;

  @override
  State<_CheckCard> createState() => _CheckCardState();
}

class _CheckCardState extends State<_CheckCard> {
  final TextEditingController _answerController = TextEditingController();

  @override
  void dispose() {
    _answerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final question = widget.checkQuestion;
    return Card(
      key: const Key('learning_check_card'),
      margin: const EdgeInsets.only(bottom: DS.sm),
      child: Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.fact_check_rounded, size: 18),
                const SizedBox(width: DS.xs),
                Expanded(child: Text(l10n.learningSegmentCheck, style: theme.textTheme.titleSmall)),
              ],
            ),
            const SizedBox(height: DS.sm),
            if (widget.holdReason != null)
              Text(
                // 证据门暂缓：先完成练习再检验（不硬推检验空页）。
                key: const Key('learning_check_hold'),
                l10n.learningCheckHoldHint,
                style: theme.textTheme.bodySmall?.copyWith(color: DS.textSecondary),
              )
            else if (question != null && question.degraded)
              Text(
                key: const Key('learning_check_degraded'),
                l10n.learningCheckDegraded,
                style: theme.textTheme.bodySmall?.copyWith(color: DS.semanticError),
              )
            else if (question != null) ...[
              Text(
                key: const Key('learning_check_question'),
                question.question,
                style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: DS.sm),
              TextField(
                key: const Key('learning_check_answer_field'),
                controller: _answerController,
                decoration: InputDecoration(
                  hintText: l10n.learningCheckAnswerHint,
                  border: const OutlineInputBorder(),
                ),
                minLines: 2,
                maxLines: 4,
              ),
              const SizedBox(height: DS.sm),
              FilledButton(
                key: const Key('learning_check_submit'),
                onPressed: widget.enabled
                    ? () {
                        widget.onSubmit(_answerController.text);
                        _answerController.clear();
                      }
                    : null,
                child: Text(l10n.learningCheckSubmit),
              ),
            ] else
              Text(
                widget.evidenceSupported ? l10n.learningCheckEnterHint : l10n.learningCheckHoldHint,
                style: theme.textTheme.bodySmall?.copyWith(color: DS.textSecondary),
              ),
            if (widget.verdict != null) ...[
              const SizedBox(height: DS.sm),
              _VerdictView(verdict: widget.verdict!),
            ],
          ],
        ),
      ),
    );
  }
}

class _VerdictView extends StatelessWidget {
  const _VerdictView({required this.verdict});

  final LearningCheckVerdict verdict;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = context.l10n;
    // 判分面只呈现对/错与泛化反馈——答案材料永不进入用户可读状态。
    final correct = verdict.correct;
    return Container(
      key: const Key('learning_check_verdict'),
      padding: const EdgeInsets.all(DS.sm),
      decoration: BoxDecoration(
        color: (correct ?? false)
            ? DS.semanticSuccess.withValues(alpha: 0.10)
            : DS.semanticWarning.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(
            (correct ?? false) ? Icons.check_circle_outline_rounded : Icons.refresh_rounded,
            size: 18,
            color: (correct ?? false) ? DS.semanticSuccess : DS.semanticWarning,
          ),
          const SizedBox(width: DS.sm),
          Expanded(
            child: Text(
              verdict.feedback ??
                  ((correct ?? false) ? l10n.learningCheckPassed : l10n.learningCheckFailedHint),
              style: theme.textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}
