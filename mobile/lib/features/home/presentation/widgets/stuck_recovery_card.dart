import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_card.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/presentation/providers/stuck_recovery_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// J-05 ·「我卡住了」旗舰恢复旅程的首页承接卡（中断回流最小闭环）。
///
/// 形制：与 GuestConversionCard（N40）/ OnboardingResumeCard（J-02）同款
/// 内联卡——SparkleCard 家族 + core/design 令牌（取色 context.colors、
/// 字阶 context.typo、间距 DS.spacing 档），内联非弹窗，不可见渲染
/// SizedBox.shrink。守门在 [stuckRecoveryCardProvider]（检测停滞 ≥48h、
/// 已认证、无执行中任务），卡内只消费视图，不重复判定。
///
/// 闭环三拍：
/// ① 共情：任务名 + 中断天数（不指责，不断言原因）；
/// ② 最小重启：CTA「先做 5 分钟」——resume（若在 paused/stuck）后直进
///    执行屏，把「接着做」的门槛降到一步；
/// ③ 正反馈：经本卡重启的任务完成时，卡变「重新接上了」正反馈相，
///    ack 后闭环归零（stuckRecoveryControllerProvider 状态机）。
class StuckRecoveryCard extends ConsumerWidget {
  const StuckRecoveryCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final view = ref.watch(stuckRecoveryCardProvider);
    if (view == null) return const SizedBox.shrink();

    final colors = context.colors;
    final typo = context.typo;
    final l10n = context.l10n;

    final isReconnected = view.phase == StuckRecoveryPhase.reconnected;
    final title = isReconnected
        ? l10n.stuckRecoveryReconnectTitle
        : l10n.stuckRecoveryCardTitle;
    final body = isReconnected
        ? l10n.stuckRecoveryReconnectBody(view.reconnectedTaskTitle ?? '')
        : l10n.stuckRecoveryCardBody(view.task!.title, view.absentDays);

    return SparkleCard(
      borderColor: colors.brandPrimary.withAlpha(64),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(DS.spacing8),
                decoration: BoxDecoration(
                  color: colors.brandPrimary.withAlpha(30),
                  borderRadius: BorderRadius.circular(DS.radius12),
                ),
                child: Icon(
                  isReconnected
                      ? Icons.link_rounded
                      : Icons.restart_alt_rounded,
                  size: 20,
                  color: colors.brandPrimary,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  title,
                  style: typo.titleLarge.copyWith(color: colors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            body,
            style: typo.bodyMedium.copyWith(
              color: colors.textSecondary,
              height: 1.5,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          if (isReconnected)
            SizedBox(
              width: double.infinity,
              child: SparkleButton.primary(
                label: l10n.stuckRecoveryReconnectAck,
                onPressed: () => ref
                    .read(stuckRecoveryControllerProvider.notifier)
                    .ackReconnect(),
              ),
            )
          else
            Row(
              children: [
                Expanded(
                  child: SparkleButton.primary(
                    label: l10n.stuckRecoveryCardCta,
                    onPressed: () =>
                        _handleRestartTap(context, ref, view.task!),
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                SparkleButton.ghost(
                  label: l10n.stuckRecoveryCardDismiss,
                  onPressed: () => ref
                      .read(stuckRecoveryControllerProvider.notifier)
                      .dismissForSession(),
                ),
              ],
            ),
        ],
      ),
    );
  }

  /// 最小重启动作：标记 restarted（此后完成即正反馈）→ 需要时 resume →
  /// 设执行态 → 进执行屏。导航形制对齐 next_actions_card._openTaskExecution
  /// （activeTaskProvider 置位 + push 执行路由）。
  Future<void> _handleRestartTap(
    BuildContext context,
    WidgetRef ref,
    TaskModel task,
  ) async {
    ref.read(stuckRecoveryControllerProvider.notifier).markRestartStarted();
    final needsResume = task.status == TaskStatus.paused ||
        task.status == TaskStatus.stuck ||
        task.status == TaskStatus.restore;
    if (needsResume) {
      await ref.read(taskListProvider.notifier).resumeTask(task.id);
    }
    if (!context.mounted) return;
    // resume 后以任务列表里的最新快照进执行屏（状态/ guide 已刷新）。
    var current = task;
    for (final item in ref.read(taskListProvider).tasks) {
      if (item.id == task.id) {
        current = item;
        break;
      }
    }
    ref.read(activeTaskProvider.notifier).state = current;
    unawaited(context.push('/tasks/${task.id}/execute?origin=home_recovery'));
  }
}
