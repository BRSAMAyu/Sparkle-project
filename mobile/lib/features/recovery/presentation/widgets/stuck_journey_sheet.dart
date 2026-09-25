import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/recovery/data/models/stuck_journey_models.dart';
import 'package:sparkle/features/recovery/presentation/providers/stuck_journey_provider.dart';

/// J-05 ·「我卡住了」旗舰恢复旅程——全产品统一恢复入口的承载面。
///
/// 三面（home/goal/action）以各自真实 context（surface + goal/task id）
/// 触发；后端读真源派生 ≤1 个高价值问题与主 intervention（A-03 引擎），
/// 本面只渲染载荷与收集回答/纠正，零本地判定。
///
/// 闭环三拍：
/// ① 单问（可选）：context 驱动选择，分支选项点选即答；
/// ② 主 intervention：中性方向文案（l10n），uncertain 时如实标注
///    best-guess；「照这个方向试试」携真实 context 深链 chat；
/// ③ 纠正：「不是这个原因」→ correct 落库反馈环，纠正后输出立即可见。
Future<void> showStuckJourneySheet(
  BuildContext context, {
  required String surface,
  String? goalId,
  String? taskId,
}) {
  final request = StuckJourneyRequest(
    surface: surface,
    goalId: goalId,
    taskId: taskId,
  );
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (sheetContext) => DraggableScrollableSheet(
      initialChildSize: 0.62,
      minChildSize: 0.42,
      maxChildSize: 0.92,
      builder: (context, scrollController) => GraphiteModalSurface(
        title: sheetContext.l10n.stuckJourneySheetTitle,
        expandChild: true,
        child: SingleChildScrollView(
          controller: scrollController,
          child: StuckJourneySheetBody(request: request),
        ),
      ),
    ),
  );
}

class StuckJourneySheetBody extends ConsumerWidget {
  const StuckJourneySheetBody({required this.request, super.key});

  final StuckJourneyRequest request;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(stuckJourneyProvider(request));
    final l10n = context.l10n;

    return AnimatedSwitcher(
      duration: context.reduceMotion ? Duration.zero : DS.quick,
      child: switch (state.status) {
        StuckJourneyStatus.loading => Padding(
            padding: const EdgeInsets.symmetric(vertical: DS.spacing32),
            child: Center(
              child: ExcludeSemantics(
                child: LoadingIndicator.circular(size: 28),
              ),
            ),
          ),
        StuckJourneyStatus.error => _ErrorPane(
            message: l10n.stuckJourneyLoadFailed,
            retryLabel: l10n.stuckJourneyRetry,
            onRetry: () =>
                ref.read(stuckJourneyProvider(request).notifier).retry(),
          ),
        StuckJourneyStatus.ready => _ReadyPane(
            request: request,
            payload: state.payload,
            busy: state.busy,
          ),
      },
    );
  }
}

class _ReadyPane extends ConsumerWidget {
  const _ReadyPane({
    required this.request,
    required this.payload,
    required this.busy,
  });

  final StuckJourneyRequest request;
  final StuckJourneyPayload? payload;
  final bool busy;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final data = payload;
    if (data == null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing24),
        child: Text(
          l10n.stuckJourneyLoadFailed,
          style: context.typo.bodyMedium.copyWith(
            color: context.colors.textSecondary,
          ),
        ),
      );
    }

    return Column(
      key: const ValueKey('stuck-journey-ready'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ContextLine(data: data.context),
        if (data.correctedThisTurn) ...[
          const SizedBox(height: DS.spacing12),
          _AckLine(label: l10n.stuckJourneyCorrectedAck),
        ],
        if (data.question != null) ...[
          const SizedBox(height: DS.spacing20),
          _SectionHeader(label: l10n.stuckJourneyQuestionHeader),
          const SizedBox(height: DS.spacing8),
          Text(
            data.question!.text,
            style: context.typo.titleMedium.copyWith(
              color: context.colors.textPrimary,
              height: 1.45,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          for (final option in data.question!.options) ...[
            AbsorbPointer(
              absorbing: busy,
              child: SizedBox(
                width: double.infinity,
                child: SparkleButton(
                  label: option.label,
                  variant: ButtonVariant.secondary,
                  onPressed: () => ref
                      .read(stuckJourneyProvider(request).notifier)
                      .answer(data.question!.id, option.key),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing8),
          ],
        ],
        if (data.mainIntervention != null) ...[
          const SizedBox(height: DS.spacing20),
          _SectionHeader(label: l10n.stuckJourneyInterventionHeader),
          const SizedBox(height: DS.spacing8),
          _InterventionCard(
            intervention: data.mainIntervention!,
            anchor: data.context.taskTitle ?? data.context.goalTitle,
          ),
          const SizedBox(height: DS.spacing12),
          SizedBox(
            width: double.infinity,
            child: SparkleButton.primary(
              label: l10n.stuckJourneyTryIt,
              onPressed: () => _openChat(context, data),
            ),
          ),
          const SizedBox(height: DS.spacing8),
          AbsorbPointer(
            absorbing: busy,
            child: SizedBox(
              width: double.infinity,
              child: SparkleButton.ghost(
                key: const Key('stuck-journey-correct-button'),
                label: l10n.stuckJourneyNotThisReason,
                onPressed: () => ref
                    .read(stuckJourneyProvider(request).notifier)
                    .correct(
                      data.mainIntervention!.frictionType,
                      interventionKey: data.mainIntervention!.type,
                    ),
              ),
            ),
          ),
        ],
        const SizedBox(height: DS.spacing24),
      ],
    );
  }

  void _openChat(BuildContext context, StuckJourneyPayload data) {
    final intervention = data.mainIntervention;
    if (intervention == null) return;
    final l10n = context.l10n;
    final anchor = data.context.taskTitle ?? data.context.goalTitle ?? '';
    final direction = _interventionLabel(context, intervention);
    unawaited(
      context.push(
        Uri(
          path: '/chat',
          queryParameters: {
            'prompt': l10n.stuckJourneyChatPrompt(anchor, direction),
            // 与 today_cockpit_card 同口径：后端既有 mode，语义最近 deep_analysis。
            'chat_mode': 'deep_analysis',
          },
        ).toString(),
      ),
    );
  }
}

String _interventionLabel(BuildContext context, StuckJourneyIntervention it) {
  final l10n = context.l10n;
  return switch (it.type) {
    'rescope' => l10n.stuckJourneyInterventionRescope,
    'split' => l10n.stuckJourneyInterventionSplit,
    'clarify' => l10n.stuckJourneyInterventionClarify,
    'explain' => l10n.stuckJourneyInterventionExplain,
    'retrieve' => l10n.stuckJourneyInterventionRetrieve,
    'practice' => l10n.stuckJourneyInterventionPractice,
    'schedule' => l10n.stuckJourneyInterventionSchedule,
    'pause' => l10n.stuckJourneyInterventionPause,
    'remind' => l10n.stuckJourneyInterventionRemind,
    'reflect' => l10n.stuckJourneyInterventionReflect,
    'review' => l10n.stuckJourneyInterventionReview,
    'connect_peer' => l10n.stuckJourneyInterventionConnectPeer,
    'delegate' => l10n.stuckJourneyInterventionDelegate,
    'co_execute' => l10n.stuckJourneyInterventionCoExecute,
    _ => l10n.stuckJourneyInterventionReflect,
  };
}

class _ContextLine extends StatelessWidget {
  const _ContextLine({required this.data});

  final StuckJourneyContextData data;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final parts = <String>[
      if (data.taskTitle != null && data.taskTitle!.isNotEmpty)
        l10n.stuckJourneyContextTask(data.taskTitle!),
      if (data.goalTitle != null && data.goalTitle!.isNotEmpty)
        l10n.stuckJourneyContextGoal(data.goalTitle!),
      if (data.recentFailureCount > 0)
        l10n.stuckJourneyContextFailures(data.recentFailureCount),
      if (data.daysSinceProgress != null && data.daysSinceProgress! >= 2)
        l10n.stuckJourneyContextStalled(data.daysSinceProgress!),
    ];
    if (parts.isEmpty) return const SizedBox.shrink();
    return Text(
      parts.join(' · '),
      style: context.typo.bodySmall.copyWith(
        color: context.colors.textSecondary,
        height: 1.5,
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

class _AckLine extends StatelessWidget {
  const _AckLine({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing8),
        decoration: BoxDecoration(
          color: DS.success.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(DS.radius12),
        ),
        child: Text(
          label,
          style: context.typo.bodySmall.copyWith(color: context.colors.textPrimary),
        ),
      );
}

class _InterventionCard extends StatelessWidget {
  const _InterventionCard({required this.intervention, required this.anchor});

  final StuckJourneyIntervention intervention;
  final String? anchor;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _interventionLabel(context, intervention),
            style: context.typo.bodyMedium.copyWith(
              color: context.colors.textPrimary,
              fontWeight: DS.fontWeightBold,
              height: 1.45,
            ),
          ),
          if (intervention.uncertain) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              l10n.stuckJourneyUncertainHint,
              style: context.typo.bodySmall.copyWith(
                color: context.colors.textSecondary,
                height: 1.45,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ErrorPane extends StatelessWidget {
  const _ErrorPane({
    required this.message,
    required this.retryLabel,
    required this.onRetry,
  });

  final String message;
  final String retryLabel;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Column(
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
            child: SparkleButton.secondary(label: retryLabel, onPressed: onRetry),
          ),
          const SizedBox(height: DS.spacing16),
        ],
      );
}
