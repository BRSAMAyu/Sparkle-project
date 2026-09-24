import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';
import 'package:sparkle/features/memory/presentation/providers/understanding_overview_provider.dart';
import 'package:sparkle/features/memory/presentation/widgets/why_this_receipt_sheet.dart';

const List<UnderstandingBucket> _bucketOrder = [
  UnderstandingBucket.told,
  UnderstandingBucket.observed,
  UnderstandingBucket.uncertain,
  UnderstandingBucket.effective,
];

/// 「Sparkle 对我的理解」四组视图（U-03）。
///
/// 数据面：M-08 provenance list API（bucket/bucket_label/source/tier 全部
/// 服务端投影）。嵌入 [embedded] 模式时每组最多显示 [_embeddedPerBucket] 条，
/// 其余通过「查看全部」进完整视图；完整模式支持分页加载更多。
///
/// 文案纪律（COPY_TONE）：不出现条目计数、置信百分比等无来源精确数字，
/// 主呈现只有分组 + 内容 + 来源 + 可执行操作。
class UnderstandingOverviewView extends ConsumerStatefulWidget {
  const UnderstandingOverviewView({
    required this.embedded,
    this.onNeedFullView,
    super.key,
  });

  /// true：嵌入记忆面板（紧凑，每组截断 + 查看全部入口）。
  final bool embedded;
  final VoidCallback? onNeedFullView;

  static const int _embeddedPerBucket = 3;

  @override
  ConsumerState<UnderstandingOverviewView> createState() =>
      _UnderstandingOverviewViewState();
}

class _UnderstandingOverviewViewState
    extends ConsumerState<UnderstandingOverviewView> {
  @override
  Widget build(BuildContext context) {
    final state = ref.watch(understandingOverviewProvider);
    final l10n = context.l10n;

    if (state.isLoading) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.xl),
        child: Center(child: LoadingIndicator.circular(strokeWidth: 2)),
      );
    }

    if (state.error != null && state.items.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.xl),
        child: Column(
          children: [
            Text(
              state.error ?? l10n.whyThisLoadFailed,
              style: TextStyle(color: DS.textSecondary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.md),
            SparkleButton.primary(
              label: l10n.retry,
              onPressed: () =>
                  ref.read(understandingOverviewProvider.notifier).refresh(),
            ),
          ],
        ),
      );
    }

    final grouped = state.grouped;
    if (grouped.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.xl),
        child: EmptyState(
          icon: Icons.psychology_alt_outlined,
          title: l10n.understandingEmptyTitle,
          description: l10n.understandingEmptyBody,
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: DS.sm),
          child: Text(
            l10n.understandingViewIntro,
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          ),
        ),
        if (state.scanCapped) ...[
          Padding(
            padding: const EdgeInsets.only(bottom: DS.sm),
            child: Text(
              l10n.understandingScanCapped,
              style: TextStyle(color: DS.textTertiary, fontSize: DS.fontSizeXs),
            ),
          ),
        ],
        for (final bucket in _bucketOrder)
          if (grouped[bucket]?.isNotEmpty ?? false)
            _BucketSection(
              title: grouped[bucket]!.first.bucketLabel.isNotEmpty
                  ? grouped[bucket]!.first.bucketLabel
                  : kBucketFallbackLabels[bucket]!,
              items: widget.embedded
                  ? grouped[bucket]!
                      .take(UnderstandingOverviewView._embeddedPerBucket)
                      .toList()
                  : grouped[bucket]!,
              hiddenCount: widget.embedded
                  ? grouped[bucket]!.length -
                      UnderstandingOverviewView._embeddedPerBucket
                  : 0,
              onViewAll: widget.onNeedFullView,
            ),
        if (!widget.embedded && state.hasMore)
          Padding(
            padding: const EdgeInsets.only(top: DS.sm),
            child: Center(
              child: SparkleButton(
                label: l10n.understandingLoadMore,
                variant: ButtonVariant.ghost,
                onPressed: state.isLoadingMore
                    ? () {}
                    : () => ref
                        .read(understandingOverviewProvider.notifier)
                        .loadMore(),
                disabled: state.isLoadingMore,
              ),
            ),
          ),
      ],
    );
  }
}

class _BucketSection extends StatelessWidget {
  const _BucketSection({
    required this.title,
    required this.items,
    required this.hiddenCount,
    this.onViewAll,
  });

  final String title;
  final List<ProvenanceMemoryItem> items;
  final int hiddenCount;
  final VoidCallback? onViewAll;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.sm),
            ...items.map(
              (item) => UnderstandingItemCard(item: item),
            ),
            if (hiddenCount > 0)
              if (onViewAll != null)
                Align(
                  alignment: Alignment.centerLeft,
                  child: SparkleButton.ghost(
                    label: context.l10n.understandingViewAll,
                    onPressed: onViewAll!,
                  ),
                ),
          ],
        ),
      );
}

/// 单条理解项卡片：内容 + 来源/置信/范围/时间 + 状态 + 操作条。
class UnderstandingItemCard extends ConsumerWidget {
  const UnderstandingItemCard({required this.item, super.key});

  final ProvenanceMemoryItem item;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final state = ref.watch(understandingOverviewProvider);
    final pending = state.pendingActionIds.contains(item.id);
    final scopeLabel = switch (item.scope['level']) {
      'goal' => l10n.understandingScopeGoal,
      'domain' => l10n.understandingScopeDomain,
      'session' => l10n.understandingScopeSession,
      _ => l10n.understandingScopeGlobal,
    };
    final metaParts = <String>[
      if (item.sourceLabel.isNotEmpty)
        item.sourceKnown ? item.sourceLabel : l10n.whyThisSourceUnknown,
      if (item.confidenceTierLabel.isNotEmpty) item.confidenceTierLabel,
      scopeLabel,
      if (item.updatedAt != null) _formatDate(item.updatedAt!),
    ];

    return Card(
      margin: const EdgeInsets.only(bottom: DS.sm),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap:
            item.can('view_source') ? () => _openWhyThis(context, ref) : null,
        child: Padding(
          padding: const EdgeInsets.all(DS.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      item.displayContent,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: DS.textPrimary,
                          ),
                    ),
                  ),
                  const SizedBox(width: DS.sm),
                  if (item.isPaused)
                    SemanticPill(
                      label: l10n.understandingPausedBadge,
                      tone: PillTone.warning,
                      dense: true,
                    )
                  else if (item.status == 'superseded')
                    SemanticPill(
                      label: l10n.understandingStatusSuperseded,
                      tone: PillTone.neutral,
                      dense: true,
                    )
                  else if (item.confidenceTierLabel.isNotEmpty)
                    SemanticPill(
                      label: item.confidenceTierLabel,
                      tone: item.confidenceTier == 'confirmed'
                          ? PillTone.success
                          : item.confidenceTier == 'likely'
                              ? PillTone.info
                              : PillTone.neutral,
                      dense: true,
                    ),
                ],
              ),
              const SizedBox(height: DS.xs),
              Text(
                metaParts.join(' · '),
                style:
                    TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
              ),
              const SizedBox(height: DS.sm),
              Wrap(
                spacing: DS.sm,
                runSpacing: DS.sm,
                children: [
                  if (item.can('update'))
                    SparkleButton(
                      label: l10n.understandingActionEdit,
                      variant: ButtonVariant.ghost,
                      disabled: pending,
                      onPressed: pending ? () {} : () => _edit(context, ref),
                    ),
                  if (item.can('pause'))
                    SparkleButton(
                      label: l10n.understandingActionPause,
                      variant: ButtonVariant.ghost,
                      disabled: pending,
                      onPressed: pending ? () {} : () => _pause(context, ref),
                    ),
                  if (item.can('resume'))
                    SparkleButton(
                      label: l10n.understandingActionResume,
                      variant: ButtonVariant.ghost,
                      disabled: pending,
                      onPressed: pending ? () {} : () => _resume(context, ref),
                    ),
                  if (item.can('set_scope'))
                    SparkleButton(
                      label: l10n.understandingActionScope,
                      variant: ButtonVariant.ghost,
                      disabled: pending,
                      onPressed: pending ? () {} : () => _scope(context, ref),
                    ),
                  if (item.can('set_scope'))
                    SparkleButton(
                      label: l10n.understandingActionLinkTask,
                      variant: ButtonVariant.ghost,
                      disabled: pending,
                      onPressed:
                          pending ? () {} : () => _linkTask(context, ref),
                    ),
                  if (item.can('revoke'))
                    SparkleButton(
                      label: l10n.understandingActionDelete,
                      variant: ButtonVariant.ghost,
                      disabled: pending,
                      onPressed: pending ? () {} : () => _delete(context, ref),
                    ),
                  if (item.can('view_source'))
                    SparkleButton(
                      label: l10n.understandingActionWhy,
                      variant: ButtonVariant.ghost,
                      disabled: pending,
                      onPressed:
                          pending ? () {} : () => _openWhyThis(context, ref),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _openWhyThis(BuildContext context, WidgetRef ref) =>
      unawaited(unawaitedWhyThis(context, ref, item));

  Future<void> _edit(BuildContext context, WidgetRef ref) async {
    final notifier = ref.read(understandingOverviewProvider.notifier);
    final edited = await showUnderstandingEditDialog(context, item);
    if (edited == null || !context.mounted) {
      return;
    }
    try {
      await notifier.updateItem(
        item,
        content: item.kind == 'goal' ? null : edited,
        title: item.kind == 'goal' ? edited : null,
        reason: 'user_edit',
      );
      if (context.mounted) {
        AppFeedback.success(context, context.l10n.understandingToastUpdated);
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(
          context,
          context.l10n.understandingToastFailedDetail(
            provenanceErrorDetail(e) ?? '$e',
          ),
        );
      }
    }
  }

  Future<void> _pause(BuildContext context, WidgetRef ref) async {
    final confirmed = await showUnderstandingConfirmDialog(
      context,
      title: context.l10n.understandingPauseTitle,
      body: context.l10n.understandingPauseBody,
      confirmLabel: context.l10n.understandingActionPause,
    );
    if (confirmed == null || !context.mounted) {
      return;
    }
    try {
      await ref
          .read(understandingOverviewProvider.notifier)
          .setPaused(item, paused: true);
      if (context.mounted) {
        AppFeedback.success(context, context.l10n.understandingToastPaused);
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(
          context,
          context.l10n.understandingToastFailedDetail(
            provenanceErrorDetail(e) ?? '$e',
          ),
        );
      }
    }
  }

  Future<void> _resume(BuildContext context, WidgetRef ref) async {
    try {
      await ref
          .read(understandingOverviewProvider.notifier)
          .setPaused(item, paused: false);
      if (context.mounted) {
        AppFeedback.success(context, context.l10n.understandingToastResumed);
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(
          context,
          context.l10n.understandingToastFailedDetail(
            provenanceErrorDetail(e) ?? '$e',
          ),
        );
      }
    }
  }

  Future<void> _scope(BuildContext context, WidgetRef ref) async {
    final planId = await showUnderstandingScopeSheet(context);
    if (planId == null || !context.mounted) {
      return;
    }
    try {
      await ref
          .read(understandingOverviewProvider.notifier)
          .linkToPlan(item, planId: planId);
      if (context.mounted) {
        AppFeedback.success(context, context.l10n.understandingToastScoped);
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(
          context,
          context.l10n.understandingToastFailedDetail(
            provenanceErrorDetail(e) ?? '$e',
          ),
        );
      }
    }
  }

  /// 仅此 Goal（任务粒度）：task-picker 选真实任务 → link_task（U-03 补齐）。
  Future<void> _linkTask(BuildContext context, WidgetRef ref) async {
    final taskId = await showUnderstandingTaskSheet(context);
    if (taskId == null || !context.mounted) {
      return;
    }
    try {
      await ref
          .read(understandingOverviewProvider.notifier)
          .linkToTask(item, taskId: taskId);
      if (context.mounted) {
        AppFeedback.success(context, context.l10n.understandingToastScoped);
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(
          context,
          context.l10n.understandingToastFailedDetail(
            provenanceErrorDetail(e) ?? '$e',
          ),
        );
      }
    }
  }

  Future<void> _delete(BuildContext context, WidgetRef ref) async {
    final confirmed = await showUnderstandingConfirmDialog(
      context,
      title: context.l10n.understandingDeleteTitle,
      body: context.l10n.understandingDeleteBody,
      confirmLabel: context.l10n.understandingActionDelete,
      destructive: true,
    );
    if (confirmed == null || !context.mounted) {
      return;
    }
    try {
      await ref.read(understandingOverviewProvider.notifier).revokeItem(item);
      if (context.mounted) {
        AppFeedback.success(context, context.l10n.understandingToastDeleted);
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(
          context,
          context.l10n.understandingToastFailedDetail(
            provenanceErrorDetail(e) ?? '$e',
          ),
        );
      }
    }
  }
}

String _formatDate(DateTime value) =>
    '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
