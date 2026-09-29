import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/semantic_motion_widgets.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/recovery/data/models/stuck_journey_models.dart';
import 'package:sparkle/features/recovery/presentation/providers/recovery_calibration_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// V4-U02 · recovery sheet 的「纠正 → 差异确认」校准区（三宿主同语义）。
///
/// 结构铁律：
/// - **恒可达**：本区不读旅程判定结果——abstain（无提案/无 intervention）
///   时纠正输入原样在场（正面钉 + 反例钉在测试层）；
/// - **约束/偏好分离呈现**：scopeChoice 相两张卡互斥呈现两写路径，文案
///   明示「保存为偏好不改动当前任务」；两个都不选也成立（先都不用）；
/// - **回执门**：成功面孔（PixelSuccessBadge）只在 committed 相渲染；
///   confirming 相零成功文案（时序反例钉）；conflict/unknown 用 F02
///   状态徽章族（conflict/unknown 语义与全产品同源，无庆祝视觉）；
/// - 偏好保存 ack 是中性行，**不**出现成功徽章类型（memory 类成功 ≠
///   任务成功面孔，F03 呈现纪律）。
///
/// UI 全部消费 core/design 令牌（context.colors/typo + DS 间距档），无
/// 颜色字面量；无任务锚点时「仅本次」入口如实缺席并说明（不出假入口）。
class RecoveryCalibrationSection extends ConsumerStatefulWidget {
  const RecoveryCalibrationSection({
    required this.request,
    this.journey,
    this.baselineMinutes,
    super.key,
  });

  /// sheet 宿主上下文（surface + goal/task id；三宿主同构）。
  final StuckJourneyRequest request;

  /// 旅程载荷（可空——abstain 时为 null，本区照常渲染）。
  /// 只用于偏好 claim 语境（锚点 + 方向），不决定本区是否渲染。
  final StuckJourneyPayload? journey;

  /// 锚点任务当前预计时长（宿主从任务列表投影解析；null = 无任务锚点，
  /// 「仅本次」入口结构性缺席并如实说明）。
  final int? baselineMinutes;

  @override
  ConsumerState<RecoveryCalibrationSection> createState() =>
      _RecoveryCalibrationSectionState();
}

class _RecoveryCalibrationSectionState
    extends ConsumerState<RecoveryCalibrationSection> {
  final TextEditingController _input = TextEditingController();

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  String get _taskId => widget.request.taskId ?? '';

  RecoveryCalibrationArgs _args(int? baselineMinutes) =>
      RecoveryCalibrationArgs(taskId: _taskId, baselineMinutes: baselineMinutes);

  String _preferenceClaim(BuildContext context) {
    final data = widget.journey;
    final anchor = data?.context.taskTitle ?? data?.context.goalTitle;
    return anchor == null || anchor.isEmpty
        ? context.l10n.recoveryCalibrationDefaultClaim
        : context.l10n.recoveryCalibrationClaim(anchor);
  }

  /// 回执替换锚（FIX-569）：一次回执一个 key（receipt_id 直调面等价于
  /// 适配器 event_id 契约）。无回执 = 哨兵空串；有回执但缺 id（契约漂移）
  /// = 稳定常量，不造 id、不冒充语义——同回执重投（重放/重建）恒同 key。
  Object _receiptSwapKey(RecoveryCalibrationState state) {
    final receipt = state.proposal?.receipt;
    if (receipt == null || receipt.isEmpty) return '';
    final id = (receipt['receipt_id'] ?? '').toString();
    return id.isEmpty ? 'receipt' : id;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final colors = context.colors;
    final typo = context.typo;
    final baseline = widget.baselineMinutes;
    final args = _args(baseline);
    final state = ref.watch(recoveryCalibrationProvider(args));
    final controller = ref.read(recoveryCalibrationProvider(args).notifier);

    return Container(
      key: const Key('recovery-calibration-section'),
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: colors.surfaceSecondary.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
        border: Border.all(color: colors.neutral300.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.recoveryCalibrationSectionTitle,
            style: typo.labelLarge.copyWith(
              color: colors.textSecondary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          // V4-FIX-569 ·「写入提交成功：回执替换」乐谱行的产品消费点：
          // 本区唯一的成功面孔面（committed 相 PixelStateBadge(success)）。
          // 相体包在恒挂载的替换壳内——confirming→committed 回执落场 =
          // replacementKey 变化 → 一次 160ms 淡入替换；同回执重建/恢复重放
          // （直接挂载进 committed 相）同 key/首挂载 → 不重播；conflict/
          // unknown/输入相树中无成功徽章载体（各相自带，门不放松）。
          SparkleReceiptSwap(
            replacementKey: _receiptSwapKey(state),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: _phaseBody(context, state, controller),
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _phaseBody(
    BuildContext context,
    RecoveryCalibrationState state,
    RecoveryCalibrationController controller,
  ) {
    switch (state.phase) {
      case RecoveryCalibrationPhase.input:
        return _inputBody(context, state, controller);
      case RecoveryCalibrationPhase.scopeChoice:
        return _scopeChoiceBody(context, state, controller);
      case RecoveryCalibrationPhase.adjusting:
        return _adjustingBody(context, state, controller);
      case RecoveryCalibrationPhase.diffReview:
      case RecoveryCalibrationPhase.confirming:
        return _diffReviewBody(context, state, controller);
      case RecoveryCalibrationPhase.committed:
        return _committedBody(context, state, controller);
      case RecoveryCalibrationPhase.conflict:
        return _conflictBody(context, state, controller);
      case RecoveryCalibrationPhase.unknown:
        return _unknownBody(context, state, controller);
      case RecoveryCalibrationPhase.preferenceSaved:
      case RecoveryCalibrationPhase.preferenceFailed:
        return _preferenceBody(context, state, controller);
    }
  }

  // ------------------------------------------------------------------
  // input：纠正输入（恒可达；abstain 同款）
  // ------------------------------------------------------------------

  List<Widget> _inputBody(
    BuildContext context,
    RecoveryCalibrationState state,
    RecoveryCalibrationController controller,
  ) {
    final l10n = context.l10n;
    final colors = context.colors;
    final typo = context.typo;
    return [
      Text(
        l10n.recoveryCalibrationHint,
        style: typo.bodySmall.copyWith(color: colors.textSecondary, height: 1.45),
      ),
      const SizedBox(height: DS.spacing8),
      TextField(
        key: const Key('recovery-calibration-input-field'),
        controller: _input,
        minLines: 1,
        maxLines: 3,
        style: typo.bodyMedium.copyWith(color: colors.textPrimary),
        decoration: InputDecoration(
          isDense: true,
          filled: true,
          fillColor: colors.surfacePrimary,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(DS.radius12),
            borderSide: BorderSide(color: colors.neutral300),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(DS.radius12),
            borderSide: BorderSide(color: colors.neutral300),
          ),
        ),
      ),
      const SizedBox(height: DS.spacing8),
      Align(
        alignment: Alignment.centerRight,
        child: SparkleButton(
          key: const Key('recovery-calibration-submit'),
          variant: ButtonVariant.secondary,
          label: l10n.recoveryCalibrationSubmit,
          onPressed: () => controller.submitConstraint(_input.text),
        ),
      ),
    ];
  }

  // ------------------------------------------------------------------
  // scopeChoice：约束 / 偏好 分离呈现（两写路径互斥；可不选）
  // ------------------------------------------------------------------

  List<Widget> _scopeChoiceBody(
    BuildContext context,
    RecoveryCalibrationState state,
    RecoveryCalibrationController controller,
  ) {
    final l10n = context.l10n;
    final colors = context.colors;
    final typo = context.typo;
    final hasAnchor = state.baselineMinutes != null;
    return [
      _ConstraintChip(text: state.constraintText),
      const SizedBox(height: DS.spacing8),
      Text(
        l10n.recoveryCalibrationScopeHeader,
        style: typo.bodySmall.copyWith(color: colors.textSecondary, height: 1.45),
      ),
      const SizedBox(height: DS.spacing8),
      if (hasAnchor)
        _ScopeOptionCard(
          optionKey: 'recovery-calibration-this-time',
          title: l10n.recoveryCalibrationThisTimeTitle,
          description: l10n.recoveryCalibrationThisTimeDesc,
          buttonLabel: l10n.recoveryCalibrationThisTimeCta,
          onSelected: controller.chooseThisTime,
        )
      else
        Text(
          l10n.recoveryCalibrationAdjustNeedsTask,
          style: typo.bodySmall.copyWith(
            color: colors.textTertiary,
            height: 1.45,
          ),
        ),
      const SizedBox(height: DS.spacing8),
      _ScopeOptionCard(
        optionKey: 'recovery-calibration-save-preference',
        title: l10n.recoveryCalibrationPreferenceTitle,
        description: l10n.recoveryCalibrationPreferenceDesc,
        buttonLabel: l10n.recoveryCalibrationPreferenceCta,
        busy: state.busy,
        onSelected: () => controller.savePreference(
          claim: _preferenceClaim(context),
          correction: state.constraintText,
        ),
      ),
      const SizedBox(height: DS.spacing8),
      Align(
        alignment: Alignment.centerRight,
        child: SparkleButton(
          variant: ButtonVariant.ghost,
          label: l10n.recoveryCalibrationSkip,
          onPressed: controller.resetToInput,
        ),
      ),
    ];
  }

  // ------------------------------------------------------------------
  // adjusting：结构化调整（零写）
  // ------------------------------------------------------------------

  List<Widget> _adjustingBody(
    BuildContext context,
    RecoveryCalibrationState state,
    RecoveryCalibrationController controller,
  ) {
    final l10n = context.l10n;
    final colors = context.colors;
    final typo = context.typo;
    final baseline = state.baselineMinutes!;
    final adjusted = state.adjustedMinutes ?? baseline;
    return [
      _ConstraintChip(text: state.constraintText),
      const SizedBox(height: DS.spacing12),
      Row(
        children: [
          Expanded(
            child: Text(
              l10n.recoveryCalibrationMinutesLabel,
              style: typo.bodyMedium.copyWith(
                color: colors.textPrimary,
                height: 1.45,
              ),
            ),
          ),
          IconButton(
            key: const Key('recovery-calibration-minutes-down'),
            tooltip: l10n.recoveryCalibrationMinutesDecrease,
            onPressed: state.busy
                ? null
                : () => controller.setAdjustedMinutes(adjusted - 5),
            icon: const Icon(Icons.remove_circle_outline_rounded, size: 22),
            color: colors.textSecondary,
          ),
          Text(
            l10n.recoveryCalibrationMinutesValue(adjusted),
            style: typo.titleMedium.copyWith(color: colors.textPrimary),
          ),
          IconButton(
            key: const Key('recovery-calibration-minutes-up'),
            tooltip: l10n.recoveryCalibrationMinutesIncrease,
            onPressed: state.busy
                ? null
                : () => controller.setAdjustedMinutes(adjusted + 5),
            icon: const Icon(Icons.add_circle_outline_rounded, size: 22),
            color: colors.textSecondary,
          ),
        ],
      ),
      const SizedBox(height: DS.spacing4),
      Text(
        l10n.recoveryCalibrationAdjustNote,
        style: typo.bodySmall.copyWith(color: colors.textTertiary, height: 1.4),
      ),
      const SizedBox(height: DS.spacing12),
      if (state.transientError) ...[
        _HonestErrorLine(label: l10n.recoveryCalibrationNetworkFailed),
        const SizedBox(height: DS.spacing8),
      ],
      Row(
        children: [
          Expanded(
            child: SparkleButton(
              key: const Key('recovery-calibration-create-proposal'),
              label: l10n.recoveryCalibrationCreateProposal,
              loading: state.busy,
              onPressed:
                  state.busy ? null : () => controller.buildAdjustment(),
            ),
          ),
          const SizedBox(width: DS.spacing8),
          SparkleButton(
            variant: ButtonVariant.ghost,
            label: l10n.recoveryCalibrationBack,
            onPressed: state.busy ? null : () => controller.resetToInput(),
          ),
        ],
      ),
    ];
  }

  // ------------------------------------------------------------------
  // diffReview / confirming：服务端 diff 在场；confirming 零成功反馈
  // ------------------------------------------------------------------

  List<Widget> _diffReviewBody(
    BuildContext context,
    RecoveryCalibrationState state,
    RecoveryCalibrationController controller,
  ) {
    final l10n = context.l10n;
    final typo = context.typo;
    final colors = context.colors;
    final proposal = state.proposal;
    final confirming = state.phase == RecoveryCalibrationPhase.confirming;
    return [
      _ConstraintChip(text: state.constraintText),
      const SizedBox(height: DS.spacing12),
      _DiffTable(rows: proposal?.diffRows ?? const <RecoveryDiffRow>[]),
      const SizedBox(height: DS.spacing12),
      if (state.transientError) ...[
        _HonestErrorLine(label: l10n.recoveryCalibrationNetworkFailed),
        const SizedBox(height: DS.spacing8),
      ],
      Row(
        children: [
          Expanded(
            child: SparkleButton(
              key: const Key('recovery-calibration-confirm'),
              label: confirming
                  ? l10n.recoveryCalibrationConfirming
                  : l10n.recoveryCalibrationConfirm,
              loading: confirming,
              onPressed:
                  confirming ? null : () => controller.confirmAdjustment(),
            ),
          ),
          const SizedBox(width: DS.spacing8),
          SparkleButton(
            key: const Key('recovery-calibration-cancel-proposal'),
            variant: ButtonVariant.ghost,
            label: l10n.recoveryCalibrationCancelProposal,
            onPressed:
                confirming ? null : () => controller.cancelAdjustment(),
          ),
        ],
      ),
      const SizedBox(height: DS.spacing4),
      Text(
        l10n.recoveryCalibrationConfirmNote,
        style: typo.bodySmall.copyWith(color: colors.textTertiary, height: 1.4),
      ),
    ];
  }

  // ------------------------------------------------------------------
  // committed：回执在场（唯一成功面孔）
  // ------------------------------------------------------------------

  List<Widget> _committedBody(
    BuildContext context,
    RecoveryCalibrationState state,
    RecoveryCalibrationController controller,
  ) {
    final l10n = context.l10n;
    final typo = context.typo;
    final colors = context.colors;
    final receipt = state.proposal?.receipt;
    final receiptId = (receipt?['receipt_id'] ?? '').toString();
    return [
      Row(
        children: [
          const PixelStateBadge(state: PixelRunState.success),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Text(
              l10n.recoveryCalibrationCommitted,
              style: typo.bodyMedium.copyWith(
                color: colors.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ),
        ],
      ),
      if (receiptId.isNotEmpty) ...[
        const SizedBox(height: DS.spacing4),
        Text(
          l10n.recoveryCalibrationReceipt(receiptId),
          style: typo.bodySmall.copyWith(color: colors.textTertiary),
        ),
      ],
      const SizedBox(height: DS.spacing12),
      _DiffTable(rows: state.proposal?.diffRows ?? const <RecoveryDiffRow>[]),
      const SizedBox(height: DS.spacing12),
      Align(
        alignment: Alignment.centerRight,
        child: SparkleButton(
          key: const Key('recovery-calibration-done'),
          variant: ButtonVariant.ghost,
          label: l10n.recoveryCalibrationDone,
          onPressed: controller.resetToInput,
        ),
      ),
    ];
  }

  // ------------------------------------------------------------------
  // conflict / unknown：可恢复，绝不呈现为成功
  // ------------------------------------------------------------------

  List<Widget> _conflictBody(
    BuildContext context,
    RecoveryCalibrationState state,
    RecoveryCalibrationController controller,
  ) {
    final l10n = context.l10n;
    final typo = context.typo;
    final colors = context.colors;
    return [
      Row(
        children: [
          const PixelStateBadge(state: PixelRunState.conflict),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Text(
              l10n.recoveryCalibrationConflictTitle,
              style: typo.bodyMedium.copyWith(color: colors.textPrimary),
            ),
          ),
        ],
      ),
      const SizedBox(height: DS.spacing12),
      if (state.transientError) ...[
        _HonestErrorLine(label: l10n.recoveryCalibrationNetworkFailed),
        const SizedBox(height: DS.spacing8),
      ],
      SparkleButton(
        key: const Key('recovery-calibration-readjust'),
        variant: ButtonVariant.secondary,
        label: l10n.recoveryCalibrationConflictRecover,
        expand: true,
        onPressed:
            state.busy ? null : () => controller.reAdjustAfterConflict(),
      ),
      const SizedBox(height: DS.spacing8),
      SparkleButton(
        key: const Key('recovery-calibration-cancel-proposal'),
        variant: ButtonVariant.ghost,
        label: l10n.recoveryCalibrationConflictCancel,
        expand: true,
        onPressed: state.busy ? null : () => controller.cancelAdjustment(),
      ),
    ];
  }

  List<Widget> _unknownBody(
    BuildContext context,
    RecoveryCalibrationState state,
    RecoveryCalibrationController controller,
  ) {
    final l10n = context.l10n;
    final colors = context.colors;
    final typo = context.typo;
    return [
      Row(
        children: [
          const PixelStateBadge(state: PixelRunState.unknown),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Text(
              l10n.recoveryCalibrationUnknownTitle,
              style: typo.bodyMedium.copyWith(color: colors.textPrimary),
            ),
          ),
        ],
      ),
      const SizedBox(height: DS.spacing12),
      if (state.transientError) ...[
        _HonestErrorLine(label: l10n.recoveryCalibrationNetworkFailed),
        const SizedBox(height: DS.spacing8),
      ],
      SparkleButton(
        key: const Key('recovery-calibration-recheck'),
        variant: ButtonVariant.secondary,
        label: l10n.recoveryCalibrationUnknownRefresh,
        expand: true,
        onPressed: state.busy ? null : () => controller.refreshFromAuthority(),
      ),
      const SizedBox(height: DS.spacing8),
      SparkleButton(
        key: const Key('recovery-calibration-cancel-proposal'),
        variant: ButtonVariant.ghost,
        label: l10n.recoveryCalibrationConflictCancel,
        expand: true,
        onPressed: state.busy ? null : () => controller.cancelAdjustment(),
      ),
    ];
  }

  // ------------------------------------------------------------------
  // preference ack：中性呈现（无成功徽章；任务未改动）
  // ------------------------------------------------------------------

  List<Widget> _preferenceBody(
    BuildContext context,
    RecoveryCalibrationState state,
    RecoveryCalibrationController controller,
  ) {
    final l10n = context.l10n;
    final typo = context.typo;
    final colors = context.colors;
    final saved = state.phase == RecoveryCalibrationPhase.preferenceSaved;
    return [
      _ConstraintChip(text: state.constraintText),
      const SizedBox(height: DS.spacing12),
      Text(
        saved
            ? l10n.recoveryCalibrationPreferenceSaved
            : l10n.recoveryCalibrationPreferenceFailed,
        style: typo.bodyMedium.copyWith(
          color: saved ? colors.textPrimary : colors.semanticError,
          height: 1.5,
        ),
      ),
      const SizedBox(height: DS.spacing12),
      Row(
        children: [
          if (saved)
            Expanded(
              child: SparkleButton(
                key: const Key('recovery-calibration-done'),
                variant: ButtonVariant.ghost,
                label: l10n.recoveryCalibrationDone,
                onPressed: controller.resetToInput,
              ),
            )
          else ...[
            Expanded(
              child: SparkleButton(
                key: const Key('recovery-calibration-preference-retry'),
                variant: ButtonVariant.secondary,
                label: l10n.stuckJourneyRetry,
                loading: state.busy,
                onPressed: state.busy
                    ? null
                    : () => controller.savePreference(
                          claim: _preferenceClaim(context),
                          correction: state.constraintText,
                        ),
              ),
            ),
            const SizedBox(width: DS.spacing8),
            SparkleButton(
              variant: ButtonVariant.ghost,
              label: l10n.recoveryCalibrationSkip,
              onPressed: state.busy ? null : () => controller.resetToInput(),
            ),
          ],
        ],
      ),
    ];
  }
}

/// 本次约束 chip（分离呈现的「这次」侧锚点）。
class _ConstraintChip extends StatelessWidget {
  const _ConstraintChip({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final colors = context.colors;
    final typo = context.typo;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing8),
      decoration: BoxDecoration(
        color: colors.brandPrimary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(DS.radius12),
      ),
      child: Text(
        l10n.recoveryCalibrationConstraintChip(text),
        style: typo.bodySmall.copyWith(color: colors.textPrimary, height: 1.45),
      ),
    );
  }
}

/// 分离选择卡（仅本次 / 保存为偏好 同构；标题 + 后果说明 + 选择按钮）。
class _ScopeOptionCard extends StatelessWidget {
  const _ScopeOptionCard({
    required this.optionKey,
    required this.title,
    required this.description,
    required this.buttonLabel,
    required this.onSelected,
    this.busy = false,
  });

  final String optionKey;
  final String title;
  final String description;
  final String buttonLabel;
  final VoidCallback onSelected;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;
    return Container(
      key: Key(optionKey),
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: colors.surfacePrimary,
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
        border: Border.all(color: colors.neutral300.withValues(alpha: 0.6)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: typo.titleSmall.copyWith(
              color: colors.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            description,
            style: typo.bodySmall.copyWith(
              color: colors.textSecondary,
              height: 1.45,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Align(
            alignment: Alignment.centerRight,
            child: SparkleButton(
              variant: ButtonVariant.secondary,
              label: buttonLabel,
              loading: busy,
              onPressed: busy ? null : onSelected,
            ),
          ),
        ],
      ),
    );
  }
}

/// 可读 diff 表（服务端 diff 权威投影；changed 字段 before → after 原文）。
class _DiffTable extends StatelessWidget {
  const _DiffTable({required this.rows});

  final List<RecoveryDiffRow> rows;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final colors = context.colors;
    final typo = context.typo;
    if (rows.isEmpty) {
      return Text(
        l10n.recoveryCalibrationDiffEmpty,
        style: typo.bodySmall.copyWith(color: colors.textTertiary),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.recoveryCalibrationDiffHeader,
          style: typo.labelLarge.copyWith(
            color: colors.textSecondary,
            fontWeight: DS.fontWeightBold,
          ),
        ),
        const SizedBox(height: DS.spacing8),
        for (final row in rows)
          Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing4),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  // 白名单字段 → 用户语言；词表外原文回落（不脑补翻译）。
                  l10n.recoveryCalibrationDiffFieldLabel(
                    _diffFieldLabel(l10n, row.field),
                  ),
                  style: typo.bodySmall.copyWith(color: colors.textSecondary),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    l10n.recoveryCalibrationDiffValues(
                      row.before ?? '—',
                      row.after ?? '—',
                    ),
                    style: typo.bodySmall.copyWith(
                      color: colors.textPrimary,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

/// 服务端 diff 字段名 → 用户语言（X-03 task 白名单封闭集；词表外原文回落）。
String _diffFieldLabel(AppLocalizations l10n, String field) {
  switch (field) {
    case 'estimated_minutes':
      return l10n.recoveryCalibrationFieldEstimatedMinutes;
    default:
      return field;
  }
}

/// 如实错误行（瞬时失败；不谎报、不吞）。
class _HonestErrorLine extends StatelessWidget {
  const _HonestErrorLine({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Text(
        label,
        style: context.typo.bodySmall.copyWith(
          color: context.colors.semanticError,
          height: 1.4,
        ),
      );
}
