import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';
import 'package:sparkle/features/memory/presentation/providers/understanding_overview_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// U-03 Why-this receipt：从任何理解项可追问「为什么有这条 / 为什么用它」。
///
/// 数据全部来自 POST /memory/provenance/why-this（M-08 Work 3 契约）：
/// why_included / internal_only 原因码由服务端翻译成用户语言，known=false
/// 时如实显示「原因说明暂缺」，绝不猜标签（honest unknown）。回执底部直接
/// 提供「这不对」纠正入口（correction loop）。
Future<void> unawaitedWhyThis(
  BuildContext context,
  WidgetRef ref,
  ProvenanceMemoryItem item,
) =>
    showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _WhyThisSheet(item: item),
    );

class _WhyThisSheet extends ConsumerStatefulWidget {
  const _WhyThisSheet({required this.item});

  final ProvenanceMemoryItem item;

  @override
  ConsumerState<_WhyThisSheet> createState() => _WhyThisSheetState();
}

class _WhyThisSheetState extends ConsumerState<_WhyThisSheet> {
  WhyThisResult? _result;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await ref
          .read(understandingOverviewProvider.notifier)
          .whyThis(widget.item);
      if (!mounted) {
        return;
      }
      setState(() {
        _result = result;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      padding: const EdgeInsets.fromLTRB(DS.xl, DS.md, DS.xl, DS.xl),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: DS.borderSubtle,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: DS.lg),
            Text(
              l10n.whyThisSheetTitle,
              style: DS.titleMedium.copyWith(fontWeight: DS.fontWeightBold),
            ),
            const SizedBox(height: DS.md),
            Flexible(
              child: SingleChildScrollView(
                child: _buildBody(l10n),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBody(AppLocalizations l10n) {
    if (_loading) {
      return Padding(
        padding: const EdgeInsets.all(DS.xl),
        child: Center(child: LoadingIndicator.circular(size: 20)),
      );
    }
    if (_error != null || _result == null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.whyThisLoadFailed,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.md),
          SparkleButton.ghost(
            label: l10n.retry,
            onPressed: _load,
          ),
        ],
      );
    }
    final result = _result!;
    final statusLine = result.statusNow == 'active'
        ? l10n.whyThisInUse
        : result.paused
            ? l10n.whyThisPausedNow
            : result.statusNow == 'superseded'
                ? l10n.whyThisReplacedNow
                : l10n.whyThisGoneNow;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          result.content,
          style: DS.bodyMedium.copyWith(color: DS.textPrimary),
        ),
        const SizedBox(height: DS.xs),
        SemanticPill(
          label: statusLine,
          tone: result.stillInUse ? PillTone.success : PillTone.neutral,
          dense: true,
        ),
        if (!result.receiptVersionKnown) ...[
          const SizedBox(height: DS.xs),
          Text(
            l10n.whyThisReceiptStale,
            style: DS.labelSmall.copyWith(color: DS.textTertiary),
          ),
        ],
        const SizedBox(height: DS.md),
        _sourceSection(result),
        _reasonsSection(
          title: l10n.whyThisWhyTitle,
          reasons: result.whyIncluded,
          emptyText: l10n.whyThisWhyEmpty,
        ),
        if (result.internalOnly.isNotEmpty)
          _reasonsSection(
            title: l10n.whyThisInternalTitle,
            reasons: result.internalOnly,
            emptyText: l10n.whyThisWhyEmpty,
          ),
        _usageSection(result),
        const SizedBox(height: DS.md),
        Align(
          alignment: Alignment.centerLeft,
          child: SparkleButton.secondary(
            label: l10n.whyThisCorrectAction,
            onPressed: () => _correct(context),
          ),
        ),
      ],
    );
  }

  Widget _sourceSection(WhyThisResult result) {
    final l10n = context.l10n;
    final source = result.source;
    final parts = <String>[
      if (source.sourceKnown) source.sourceLabel else l10n.whyThisSourceUnknown,
      if (source.writtenAt != null)
        l10n.whyThisWrittenAt(_formatDateTime(source.writtenAt!)),
      if (result.usedAt != null)
        l10n.whyThisLastUsedAt(_formatDateTime(result.usedAt!)),
    ];
    final govLine = source.governanceHistory
        .take(3)
        .map(
          (event) => _formatDateTime(
            event.at ?? DateTime.fromMillisecondsSinceEpoch(0),
          ),
        )
        .join(' · ');
    return _SectionCard(
      title: l10n.whyThisSourceTitle,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            parts.join(' · '),
            style: DS.bodySmall.copyWith(color: DS.textPrimary),
          ),
          if (govLine.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: DS.xs),
              child: Text(
                govLine,
                style: DS.labelSmall.copyWith(color: DS.textTertiary),
              ),
            ),
        ],
      ),
    );
  }

  Widget _reasonsSection({
    required String title,
    required List<WhyReason> reasons,
    required String emptyText,
  }) {
    final visible = reasons
        .map(
          (reason) => reason.known
              ? (reason.label ?? emptyText)
              : context.l10n.whyThisUnknownReason,
        )
        .toList();
    return _SectionCard(
      title: title,
      child: visible.isEmpty
          ? Text(
              emptyText,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final label in visible)
                  Padding(
                    padding: const EdgeInsets.only(bottom: DS.xs),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('· '),
                        Expanded(
                          child: Text(
                            label,
                            style: DS.bodySmall.copyWith(color: DS.textPrimary),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
    );
  }

  Widget _usageSection(WhyThisResult result) {
    final l10n = context.l10n;
    final runParts = <String>[
      if (result.runCreatedAt != null)
        l10n.whyThisWrittenAt(_formatDateTime(result.runCreatedAt!)),
    ];
    final useParts = <String>[
      for (final use in result.recentUses.take(3))
        if (use.at != null) _formatDateTime(use.at!),
    ];
    if (runParts.isEmpty && useParts.isEmpty) {
      return _SectionCard(
        title: l10n.whyThisUsageTitle,
        child: Text(
          l10n.whyThisUsageEmpty,
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
      );
    }
    return _SectionCard(
      title: l10n.whyThisUsageTitle,
      child: Text(
        [...runParts, ...useParts].join(' · '),
        style: DS.bodySmall.copyWith(color: DS.textPrimary),
      ),
    );
  }

  Future<void> _correct(BuildContext context) async {
    final edited = await showUnderstandingEditDialog(context, widget.item);
    if (edited == null || !context.mounted) {
      return;
    }
    final notifier = ref.read(understandingOverviewProvider.notifier);
    try {
      await notifier.updateItem(
        widget.item,
        content: widget.item.kind == 'goal' ? null : edited,
        title: widget.item.kind == 'goal' ? edited : null,
        reason: 'why_this_correction',
      );
      if (!context.mounted) {
        return;
      }
      Navigator.of(context).pop();
      AppFeedback.success(context, context.l10n.understandingToastUpdated);
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

  String _formatDateTime(DateTime value) {
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    return '${value.year}/$month/$day $hour:$minute';
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.md),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: DS.surfaceHigh.withValues(alpha: 0.6),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Padding(
            padding: const EdgeInsets.all(DS.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: DS.labelLarge.copyWith(
                    color: DS.textSecondary,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const SizedBox(height: DS.xs),
                child,
              ],
            ),
          ),
        ),
      );
}

/// 修改对话框：返回新内容文本；取消返回 null。
///
/// controller 由 [_EditDialogState] 持有并在 dispose 释放——不能用
/// whenComplete 提前 dispose（退出动画期间 TextField 仍在树上）。
Future<String?> showUnderstandingEditDialog(
  BuildContext context,
  ProvenanceMemoryItem item,
) =>
    showDialog<String?>(
      context: context,
      builder: (dialogContext) => _EditDialog(item: item),
    );

class _EditDialog extends StatefulWidget {
  const _EditDialog({required this.item});

  final ProvenanceMemoryItem item;

  @override
  State<_EditDialog> createState() => _EditDialogState();
}

class _EditDialogState extends State<_EditDialog> {
  late final TextEditingController _controller =
      TextEditingController(text: widget.item.displayContent);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.understandingEditTitle),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(l10n.understandingEditLabel),
          const SizedBox(height: DS.xs),
          TextField(
            controller: _controller,
            autofocus: true,
            maxLines: 3,
            minLines: 1,
            maxLength: 2000,
          ),
        ],
      ),
      actions: [
        SparkleButton(
          label: l10n.cancel,
          variant: ButtonVariant.ghost,
          onPressed: () => Navigator.of(context).pop(),
        ),
        SparkleButton(
          label: l10n.confirm,
          onPressed: () {
            final text = _controller.text.trim();
            Navigator.of(context).pop(text.isEmpty ? null : text);
          },
        ),
      ],
    );
  }
}

/// 通用确认对话框（删除/暂停）。确认返回 true，取消返回 null。
Future<bool?> showUnderstandingConfirmDialog(
  BuildContext context, {
  required String title,
  required String body,
  required String confirmLabel,
  bool destructive = false,
}) =>
    showDialog<bool?>(
      context: context,
      builder: (dialogContext) {
        final l10n = dialogContext.l10n;
        return AlertDialog(
          title: Text(title),
          content: Text(body),
          actions: [
            SparkleButton(
              label: l10n.cancel,
              variant: ButtonVariant.ghost,
              onPressed: () => Navigator.of(dialogContext).pop(),
            ),
            SparkleButton(
              label: confirmLabel,
              variant: destructive
                  ? ButtonVariant.destructive
                  : ButtonVariant.primary,
              onPressed: () => Navigator.of(dialogContext).pop(true),
            ),
          ],
        );
      },
    );

/// 仅此 Goal：选择真实学习计划（planRepositoryProvider 走真实后端）。
/// 返回 plan id；取消返回 null；无计划返回空字符串。
Future<String?> showUnderstandingScopeSheet(BuildContext context) =>
    showSensoryModalBottomSheet<String?>(
      context: context,
      builder: (sheetContext) => Consumer(
        builder: (context, ref, _) {
          final l10n = sheetContext.l10n;
          final plansAsync = ref.watch(_plansFutureProvider);
          return Container(
            decoration: BoxDecoration(
              color: DS.surfacePanel,
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(20)),
            ),
            padding: const EdgeInsets.fromLTRB(DS.xl, DS.md, DS.xl, DS.xl),
            child: SafeArea(
              top: false,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.understandingScopeSheetTitle,
                    style:
                        DS.titleMedium.copyWith(fontWeight: DS.fontWeightBold),
                  ),
                  const SizedBox(height: DS.md),
                  Flexible(
                    child: plansAsync.when(
                      loading: () => Padding(
                        padding: const EdgeInsets.all(DS.lg),
                        child: Center(
                          child: LoadingIndicator.circular(size: 20),
                        ),
                      ),
                      error: (_, __) => Text(
                        l10n.understandingScopeNoPlans,
                        style: DS.bodySmall.copyWith(color: DS.textSecondary),
                      ),
                      data: (plans) {
                        if (plans.isEmpty) {
                          return Padding(
                            padding: const EdgeInsets.only(bottom: DS.md),
                            child: Text(
                              l10n.understandingScopeNoPlans,
                              style: DS.bodySmall
                                  .copyWith(color: DS.textSecondary),
                            ),
                          );
                        }
                        return ListView.builder(
                          shrinkWrap: true,
                          itemCount: plans.length,
                          itemBuilder: (context, index) {
                            final plan = plans[index];
                            return ListTile(
                              dense: true,
                              leading: const Icon(Icons.flag_outlined),
                              title: Text(
                                plan.name,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              onTap: () =>
                                  Navigator.of(sheetContext).pop(plan.id),
                            );
                          },
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );

final _plansFutureProvider = FutureProvider.autoDispose<List<PlanModel>>(
  (ref) => ref.watch(planRepositoryProvider).getActivePlans(),
);
