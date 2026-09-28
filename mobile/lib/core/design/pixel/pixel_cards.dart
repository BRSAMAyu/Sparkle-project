/// V4-F02 · 像素卡片族——主卡 / 次卡 / AuroraReceipt / ActionDiff /
/// RunCard / EvidenceStamp（DESIGN_SYSTEM.md 核心组件合同逐条落地）。
///
/// 共同纪律：
/// - 面板一律走 [PixelFrame]（装饰不吞手势、Semantics 由内容提供）；
/// - 颜色只取既有语义槽（context.sparkleTheme.colors），无第二色源；
/// - 状态呈现走 [PixelStateBadge]（四态互异、非成功无庆祝动效）；
/// - 撤回/纠正/重算等关键操作恒可达（合同行内逐条）。
library;

import 'package:flutter/material.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel_frame.dart';
import 'package:sparkle/core/design/pixel/pixel_primary_action.dart';
import 'package:sparkle/core/design/pixel/pixel_state.dart';

/// 主卡（NextStepCard/GoalAnchor 承载面）：深墨轮廓 + 单切角 + 单主 CTA。
class PixelPrimaryCard extends StatelessWidget {
  const PixelPrimaryCard({
    required this.title, required this.child, super.key,
    this.actionLabel,
    this.onAction,
    this.state,
  });

  final String title;
  final Widget child;
  final String? actionLabel;
  final VoidCallback? onAction;

  /// 附属状态徽章（cancelled/unknown/conflict/failed/success）。
  final PixelRunState? state;

  @override
  Widget build(BuildContext context) {
    final typo = context.sparkleTheme.typography;
    final colors = context.sparkleTheme.colors;
    return PixelFrame(
      emphasis: PixelFrameEmphasis.primary,
      cutCorner: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: typo.titleMedium.copyWith(color: colors.textPrimary),
                ),
              ),
              if (state != null) PixelStateBadge(state: state!, dense: true),
            ],
          ),
          const SizedBox(height: DS.sm),
          child,
          if (actionLabel != null && onAction != null) ...[
            const SizedBox(height: DS.sm),
            // 单视口最多一个强主 CTA（视觉语法合同）。
            Align(
              alignment: Alignment.centerRight,
              child: PixelPrimaryAction(
                label: actionLabel!,
                onPressed: onAction!,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// 次卡：单线或轻底色，无切角、无主 CTA。
class PixelSecondaryCard extends StatelessWidget {
  const PixelSecondaryCard({
    required this.title, required this.child, super.key,
    this.fill = false,
    this.trailing,
  });

  final String title;
  final Widget child;
  final bool fill;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final typo = context.sparkleTheme.typography;
    final colors = context.sparkleTheme.colors;
    return PixelFrame(
      fill: fill,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: typo.labelLarge.copyWith(color: colors.textPrimary),
                ),
              ),
              if (trailing != null) trailing!,
            ],
          ),
          const SizedBox(height: DS.xs),
          child,
        ],
      ),
    );
  }
}

/// AuroraReceipt（为什么/用了哪条经验）：
/// - 只对实际选用 ref 有说明（refs 为空显示「未引用经验」，不伪造）；
/// - 纠正 / 仅本次 / 删除三个动作**恒可达**（合同原文）。
class PixelReceiptCard extends StatelessWidget {
  const PixelReceiptCard({
    required this.reason, super.key,
    this.usedRefs = const [],
    this.onCorrect,
    this.onThisTimeOnly,
    this.onDelete,
  });

  final String reason;
  final List<String> usedRefs;
  final VoidCallback? onCorrect;
  final VoidCallback? onThisTimeOnly;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final typo = context.sparkleTheme.typography;
    final colors = context.sparkleTheme.colors;
    return PixelSecondaryCard(
      title: '为什么这样做',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            reason,
            style: typo.bodyMedium.copyWith(color: colors.textSecondary),
          ),
          const SizedBox(height: DS.xs),
          if (usedRefs.isEmpty)
            Text(
              '未引用经验',
              style: typo.labelSmall.copyWith(color: colors.textDisabled),
            )
          else
            ...usedRefs.map(
              (ref) => Text(
                '· $ref',
                style: typo.labelSmall.copyWith(color: colors.textSecondary),
              ),
            ),
          const SizedBox(height: DS.sm),
          Row(
            children: [
              TextButton(
                onPressed: onCorrect,
                child: const Text('纠正'),
              ),
              TextButton(
                onPressed: onThisTimeOnly,
                child: const Text('仅本次'),
              ),
              TextButton(
                onPressed: onDelete,
                child: const Text('删除'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// ActionDiff 卡（old→new / 变化理由 / 状态机）。
///
/// 合同：proposed/approved/applying/committed/unknown/conflict 六态；
/// **不能合并**——本组件不提供任何「合并/覆盖写」入口（approve 语义是
/// 逐字段确认，不是把 unknown/conflict 并入 committed）。
class PixelDiffCard extends StatelessWidget {
  const PixelDiffCard({
    required this.field, required this.oldValue, required this.newValue, required this.reason, required this.status, super.key,
    this.onApprove,
  });

  final String field;
  final String oldValue;
  final String newValue;
  final String reason;

  /// Diff 六态（unknown/conflict 走 PixelRunState 同一视觉族）。
  final PixelDiffStatus status;

  /// proposed/approved 前进动作；unknown/conflict/committed 恒 null。
  final VoidCallback? onApprove;

  bool get _approvable =>
      status == PixelDiffStatus.proposed ||
      status == PixelDiffStatus.approved;

  @override
  Widget build(BuildContext context) {
    final typo = context.sparkleTheme.typography;
    final colors = context.sparkleTheme.colors;
    final badge = switch (status) {
      PixelDiffStatus.proposed => const _PlainBadge(label: '待确认'),
      PixelDiffStatus.approved => const _PlainBadge(label: '已确认'),
      PixelDiffStatus.applying => const _PlainBadge(label: '写入中'),
      PixelDiffStatus.committed => const _PlainBadge(label: '已提交'),
      PixelDiffStatus.unknown => const PixelStateBadge(
          state: PixelRunState.unknown,
          dense: true,
        ),
      PixelDiffStatus.conflict => const PixelStateBadge(
          state: PixelRunState.conflict,
          dense: true,
        ),
    };
    return PixelSecondaryCard(
      title: field,
      trailing: badge,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  oldValue,
                  style: typo.bodyMedium.copyWith(
                    color: colors.textSecondary,
                    decoration: TextDecoration.lineThrough,
                  ),
                ),
              ),
              Icon(Icons.arrow_forward,
                  size: 16, color: colors.textSecondary,),
              Expanded(
                child: Text(
                  newValue,
                  style: typo.bodyMedium.copyWith(color: colors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.xs),
          Text(
            reason,
            style: typo.labelSmall.copyWith(color: colors.textSecondary),
          ),
          if (_approvable && onApprove != null)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: onApprove,
                child: const Text('确认修改'),
              ),
            ),
          // unknown/conflict 无前进入口（不能合并合同的 UI 面）。
        ],
      ),
    );
  }
}

/// Diff 六态（DESIGN_SYSTEM.md ActionDiffSheet 行）。
enum PixelDiffStatus {
  proposed,
  approved,
  applying,
  committed,

  /// 结果未知（联动 PixelRunState.unknown 视觉族）。
  unknown,

  /// 并发版本冲突（联动 PixelRunState.conflict 视觉族）。
  conflict,
}

/// RunCard（plan、阶段、handoff）：
/// - 离开后恢复（「继续」入口恒在）；
/// - **长任务不以假进度百分比填空**：progress==null 时显示阶段列表，
///   绝不渲染编造的 % 数字。
class PixelRunCard extends StatelessWidget {
  const PixelRunCard({
    required this.plan, required this.stages, super.key,
    this.currentStage = 0,
    this.progress,
    this.state = PixelRunState.unknown,
    this.onResume,
  });

  final String plan;

  /// 阶段名（真实阶段，不造进度）。
  final List<String> stages;
  final int currentStage;

  /// 真实进度（null = 不可知，显示阶段不显示 %）。
  final double? progress;

  /// 运行态徽章（running 用 unknown 族之外的纯文本；非成功四态可入）。
  final PixelRunState state;
  final VoidCallback? onResume;

  @override
  Widget build(BuildContext context) {
    final typo = context.sparkleTheme.typography;
    final colors = context.sparkleTheme.colors;
    return PixelSecondaryCard(
      title: plan,
      trailing: PixelStateBadge(state: state, dense: true),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          for (var i = 0; i < stages.length; i++) ...[
            Row(
              children: [
                Icon(
                  i < currentStage
                      ? Icons.check
                      : i == currentStage
                          ? Icons.play_arrow
                          : Icons.crop_square,
                  size: 14,
                  color: i <= currentStage
                      ? colors.brandPrimary
                      : colors.textDisabled,
                ),
                const SizedBox(width: DS.xs),
                Text(
                  stages[i],
                  style: typo.labelSmall.copyWith(
                    color: i <= currentStage
                        ? colors.textPrimary
                        : colors.textSecondary,
                  ),
                ),
              ],
            ),
            if (i < stages.length - 1) const SizedBox(height: DS.spacing4),
          ],
          // 假进度红线：progress 不可知时绝不渲染百分比。
          if (progress != null) ...[
            const SizedBox(height: DS.xs),
            Text(
              '${(progress!.clamp(0, 1) * 100).round()}%',
              style: typo.labelSmall.copyWith(color: colors.textSecondary),
            ),
          ],
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: onResume,
              child: const Text('继续'),
            ),
          ),
        ],
      ),
    );
  }
}

/// EvidenceStamp（outcome→来源与方法）：
/// - persisted ≠ validated ≠ mastery 三态徽章（不同语义槽）；
/// - 撤回 / 重算恒可达。
class PixelEvidenceStamp extends StatelessWidget {
  const PixelEvidenceStamp({
    required this.outcome, required this.source, required this.method, required this.certainty, super.key,
    this.onRecall,
    this.onRecalc,
  });

  final String outcome;
  final String source;
  final String method;

  /// 证据确证级：仅持久化 / 已验证 / 已掌握。
  final PixelEvidenceCertainty certainty;
  final VoidCallback? onRecall;
  final VoidCallback? onRecalc;

  @override
  Widget build(BuildContext context) {
    final typo = context.sparkleTheme.typography;
    final colors = context.sparkleTheme.colors;
    final label = switch (certainty) {
      PixelEvidenceCertainty.persisted => '已记录',
      PixelEvidenceCertainty.validated => '已验证',
      PixelEvidenceCertainty.mastery => '已掌握',
    };
    final certaintyColor = switch (certainty) {
      PixelEvidenceCertainty.persisted => colors.textSecondary,
      PixelEvidenceCertainty.validated => colors.semanticInfo,
      PixelEvidenceCertainty.mastery => colors.semanticSuccess,
    };
    return PixelSecondaryCard(
      title: '证据',
      trailing: _PlainBadge(label: label, color: certaintyColor),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            outcome,
            style: typo.bodyMedium.copyWith(color: colors.textPrimary),
          ),
          const SizedBox(height: DS.xs),
          Text(
            '来源：$source · 方法：$method',
            style: typo.labelSmall.copyWith(color: colors.textSecondary),
          ),
          Row(
            children: [
              TextButton(
                onPressed: onRecall,
                child: const Text('撤回'),
              ),
              TextButton(
                onPressed: onRecalc,
                child: const Text('重算'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// 证据确证级（persisted ≠ validated ≠ mastery 合同）。
enum PixelEvidenceCertainty { persisted, validated, mastery }

/// 中性文本徽章（非状态族的普通流程态；无庆祝无警示）。
class _PlainBadge extends StatelessWidget {
  const _PlainBadge({required this.label, this.color});

  final String label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final colors = context.sparkleTheme.colors;
    return Text(
      label,
      style: context.sparkleTheme.typography.labelSmall
          .copyWith(color: color ?? colors.textSecondary),
    );
  }
}
