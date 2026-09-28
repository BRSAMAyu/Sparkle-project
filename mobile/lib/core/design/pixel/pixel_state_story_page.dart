/// V4-F02 · 状态故事页（preview 面，不接正式导航）。
///
/// DESIGN_SYSTEM.md「迁移办法」：先适配组件故事页。本页是 V4-F02 的
/// 组件/状态全覆盖故事页——DPR 面与 focus 面在这里可视化可测：
/// - 全部 PixelRunState 的状态徽章与承载卡（四非成功态互异、无成功动效）；
/// - 主卡/次卡/CTA/receipt/diff/run/evidence 组件族；
/// - 装饰覆盖按钮的命中透传演示区（切角叠按钮）。
///
/// **不写入正式路由**：五 Tab 路由合同零触碰；本页仅供开发预览与
/// widget 测试直接构造（routeName 常量只是命名种子）。
library;

import 'package:flutter/material.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel.dart';

/// preview 路由名（命名种子；未在 router 注册）。
const String kPixelStateStoryRouteName = '/dev-preview/pixel-state-story';

/// 状态故事页。
class PixelStateStoryPage extends StatelessWidget {
  const PixelStateStoryPage({super.key});

  /// 全部演示状态（四非成功态 + 成功对照）。
  static const List<PixelRunState> demoStates = <PixelRunState>[
    PixelRunState.cancelled,
    PixelRunState.unknown,
    PixelRunState.conflict,
    PixelRunState.failed,
    PixelRunState.success,
  ];

  @override
  Widget build(BuildContext context) {
    final colors = context.sparkleTheme.colors;
    final typo = context.sparkleTheme.typography;
    return Scaffold(
      backgroundColor: colors.surfacePrimary,
      appBar: AppBar(title: const Text('像素组件 · 状态故事')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(DS.cardPaddingContent),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Section(
              title: '状态族（非成功四态互异 · 无成功动效）',
              child: Wrap(
                spacing: DS.sm,
                runSpacing: DS.sm,
                children: [
                  for (final s in demoStates)
                    PixelStateBadge(state: s),
                ],
              ),
            ),
            _Section(
              title: '非成功态承载卡（取消/未知/冲突/失败）',
              child: Column(
                children: [
                  for (final s in const [
                    PixelRunState.cancelled,
                    PixelRunState.unknown,
                    PixelRunState.conflict,
                    PixelRunState.failed,
                  ])
                    Padding(
                      padding: const EdgeInsets.only(bottom: DS.sm),
                      child: PixelPrimaryCard(
                        title: '下一步',
                        state: s,
                        child: Text(
                          '状态演示：${PixelStateSpec.forState(s).label}',
                          style: typo.bodyMedium
                              .copyWith(color: colors.textSecondary),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            _Section(
              title: '成功对照（唯一庆祝态）',
              child: PixelPrimaryCard(
                title: '下一步',
                state: PixelRunState.success,
                actionLabel: '再来一次',
                onAction: () {},
                child: Text(
                  '成功态才允许上升动效与对勾。',
                  style:
                      typo.bodyMedium.copyWith(color: colors.textSecondary),
                ),
              ),
            ),
            _Section(
              title: '主卡 / 次卡 / 分隔',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  PixelPrimaryCard(
                    title: '主卡：深墨轮廓 + 阶梯角',
                    child: Text(
                      '单视口最多一个强主 CTA。',
                      style: typo.bodyMedium
                          .copyWith(color: colors.textSecondary),
                    ),
                  ),
                  const SizedBox(height: DS.sm),
                  const PixelSecondaryCard(
                    title: '次卡：单线',
                    child: Text('列表用留白与分割，不每行镶框。'),
                  ),
                  const SizedBox(height: DS.sm),
                  const PixelSecondaryCard(
                    title: '次卡：轻底色',
                    fill: true,
                    child: Text('单线或轻底色，无切角。'),
                  ),
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: DS.sm),
                    child: PixelDivider(),
                  ),
                ],
              ),
            ),
            _Section(
              title: 'AuroraReceipt（纠正/仅本次/删除恒可达）',
              child: PixelReceiptCard(
                reason: '因为你近 7 天在晚间完成任务的比例更高。',
                usedRefs: const ['经验 #12：晚间专注', '经验 #31：拆分 25 分钟'],
                onCorrect: () {},
                onThisTimeOnly: () {},
                onDelete: () {},
              ),
            ),
            _Section(
              title: 'ActionDiff（unknown/conflict 不能合并）',
              child: Column(
                children: [
                  PixelDiffCard(
                    field: '每日目标',
                    oldValue: '30 分钟',
                    newValue: '45 分钟',
                    reason: '你连续 3 天超额完成。',
                    status: PixelDiffStatus.proposed,
                    onApprove: () {},
                  ),
                  const SizedBox(height: DS.sm),
                  const PixelDiffCard(
                    field: '学习时段',
                    oldValue: '20:00',
                    newValue: '21:00',
                    reason: '本机与云端同时被修改。',
                    status: PixelDiffStatus.conflict,
                  ),
                  const SizedBox(height: DS.sm),
                  const PixelDiffCard(
                    field: '提醒方式',
                    oldValue: '推送',
                    newValue: '（未知）',
                    reason: '上次同步中断，结果未知。',
                    status: PixelDiffStatus.unknown,
                  ),
                ],
              ),
            ),
            _Section(
              title: 'RunCard（恢复 · 不造假进度）',
              child: PixelRunCard(
                plan: 'Python 入门冲刺',
                stages: const ['理解', '练习', '回顾', '迁移'],
                currentStage: 1,
                onResume: () {},
              ),
            ),
            _Section(
              title: 'EvidenceStamp（persisted≠validated≠mastery）',
              child: Column(
                children: [
                  PixelEvidenceStamp(
                    outcome: '能独立写出递归函数',
                    source: '练习 #48',
                    method: '三次独立作答',
                    certainty: PixelEvidenceCertainty.validated,
                    onRecall: () {},
                    onRecalc: () {},
                  ),
                  const SizedBox(height: DS.sm),
                  PixelEvidenceStamp(
                    outcome: '偏好图像记忆',
                    source: '会话观察',
                    method: '推断',
                    certainty: PixelEvidenceCertainty.persisted,
                    onRecall: () {},
                    onRecalc: () {},
                  ),
                ],
              ),
            ),
            _Section(
              title: '装饰不吞点击（切角叠按钮 · 命中透传）',
              child: Stack(
                alignment: Alignment.topRight,
                children: [
                  PixelFrame(
                    emphasis: PixelFrameEmphasis.primary,
                    cutCorner: true,
                    padding: const EdgeInsets.fromLTRB(
                        DS.cardPaddingContent, DS.cardPaddingContent, 56, DS.xxl,),
                    child: Text(
                      '轮廓装饰层 IgnorePointer：点击右上角切角区域，事件必须到达其下的按钮。',
                      style: typo.bodyMedium
                          .copyWith(color: colors.textSecondary),
                    ),
                  ),
                  // 故意把按钮放在切角装饰覆盖的位置（右上角）。
                  Positioned(
                    top: DS.spacing4,
                    right: DS.spacing4,
                    child: PixelPrimaryAction(
                      label: '透传演示',
                      semanticLabel: '装饰透传演示按钮',
                      onPressed: () {},
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.xl),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final typo = context.sparkleTheme.typography;
    final colors = context.sparkleTheme.colors;
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: typo.titleSmall.copyWith(color: colors.textPrimary),
          ),
          const SizedBox(height: DS.sm),
          child,
        ],
      ),
    );
  }
}
