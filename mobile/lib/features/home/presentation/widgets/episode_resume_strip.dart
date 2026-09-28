import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/data/episode_resume_models.dart';
import 'package:sparkle/features/home/presentation/providers/episode_resume_provider.dart';

/// V4-U01 · 首页接续条 ——「上次到哪 + 下一步」（I01 `episode_resume_view.v1`
/// 的如实渲染面，TodayCockpitCard 内的组合件）。
///
/// 呈现纪律：
/// 1. **零假历史**：门未过（无回执 / 角色不符 / 无任务 / 视图降级）→
///    [SizedBox.shrink]，绝不渲染占位「历史」；
/// 2. **如实过期**：渲染时刻现判 [episodeResumeStaleReason]——过期视图
///    只渲染不确定性说明（stale 线），不渲染「上次/下一步」内容，更不
///    驱动接续动作（B05 §9 反例「过期 EpisodeResumeView 自动接续」）；
/// 3. **不抢主行动**：本条零可点目标（纯文本证据面），首屏唯一 primary
///    CTA 仍是 cockpit 主按钮——接续语义只经主按钮标签收敛表达；
/// 4. **无自动播放/重播**：纯静态渲染（reduceMotion 时零动画），退出重进
///    不触发任何导航、成就或播放面。
class EpisodeResumeStrip extends ConsumerWidget {
  const EpisodeResumeStrip({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final resumeAsync = ref.watch(episodeResumeProvider);
    final state = resumeAsync.valueOrNull;
    final view = state?.view;
    if (view == null) {
      return const SizedBox.shrink(key: ValueKey('episode-resume-absent'));
    }
    final l10n = context.l10n;
    final staleReason = episodeResumeStaleReason(view, now: DateTime.now());
    if (staleReason != null) {
      // 过期视图：只允许说明不确定性，不出「上次/下一步」，不接续。
      return Padding(
        padding: const EdgeInsets.only(top: DS.spacing12),
        child: Container(
          key: const ValueKey('episode-resume-stale-line'),
          width: double.infinity,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: DS.warning.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: DS.warning.withValues(alpha: 0.18)),
          ),
          child: Row(
            children: [
              Icon(
                Icons.info_outline_rounded,
                size: 16,
                color: DS.warning,
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  l10n.homeResumeStaleLine,
                  style: context.typo.bodySmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }

    final lastStep = view.lastConfirmedStep?.description;
    final nextStep = view.pendingHumanStep?.description;
    if (lastStep == null && nextStep == null) {
      // 新鲜视图但无可呈现步骤事实（字段级降级后为空）→ 如实缺席。
      return const SizedBox.shrink(key: ValueKey('episode-resume-absent'));
    }
    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing12),
      child: Container(
        key: const ValueKey('episode-resume-strip'),
        width: double.infinity,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing12,
        ),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.14)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.history_rounded,
                  size: 14,
                  color: DS.textSecondary,
                ),
                const SizedBox(width: DS.spacing8),
                // Expanded：长标签（本地化文案）在窄屏截断而非溢出。
                Expanded(
                  child: Text(
                    l10n.homeResumeEyebrow,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.typo.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
              ],
            ),
            if (lastStep != null) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                l10n.homeResumeLastStep(lastStep),
                key: const ValueKey('episode-resume-last-step'),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: context.typo.bodySmall.copyWith(
                  color: DS.textPrimary,
                  height: 1.4,
                ),
              ),
            ],
            if (nextStep != null) ...[
              const SizedBox(height: DS.spacing4),
              Text(
                l10n.homeResumeNextStep(nextStep),
                key: const ValueKey('episode-resume-next-step'),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: context.typo.bodySmall.copyWith(
                  color: DS.textSecondary,
                  fontWeight: DS.fontWeightMedium,
                  height: 1.4,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
