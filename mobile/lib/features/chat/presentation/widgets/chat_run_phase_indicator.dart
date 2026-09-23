import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';

/// S18（§4.5 AI 推理等待「诚实分阶段」）：首流等待期的单行阶段胶囊。
/// （类名 Indicator——"Capsule/Pill" 等语义名由 UX-COMP 收归 core/design
/// owner，features 域禁新增。）
///
/// 三阶段映射（数据链已存在，仅做 UI 呈现——不改引擎协议）：
/// - 检索：`ChatRunPhase.sending` 且状态为检索类（或尚未上报状态）；
/// - 思考：状态为思考/分析/规划类；
/// - 生成：`ChatRunPhase.streaming` / `finalizing`。
///
/// 规范落点：§5.2 阶段胶囊（仅存在于等待期，完成即消失）；§8.2-2
/// （三阶段+预期时长+可取消，`_TypingIndicator` 三点动画退役）。
/// 动效：激活段单点 M1 脉冲（同屏唯一持续源候选），reduce-motion 静态。
enum ChatRunStage { retrieve, think, generate }

/// 纯函数映射，便于静态三态断言（不含 UI 依赖）。
ChatRunStage resolveChatRunStage(ChatRunPhase phase, String? aiStatus) {
  switch (phase) {
    case ChatRunPhase.streaming:
    case ChatRunPhase.finalizing:
      return ChatRunStage.generate;
    case ChatRunPhase.sending:
    case ChatRunPhase.idle:
    case ChatRunPhase.completed:
    case ChatRunPhase.cancelled:
    case ChatRunPhase.interrupted:
    case ChatRunPhase.failed:
      break;
  }
  final status = (aiStatus ?? '').trim().toUpperCase();
  const thinkingStatuses = {
    'THINKING',
    'ANALYZING',
    'PLANNING',
    'REVIEWING',
    'REASONING',
  };
  if (thinkingStatuses.contains(status)) {
    return ChatRunStage.think;
  }
  return ChatRunStage.retrieve;
}

class ChatRunPhaseIndicator extends StatefulWidget {
  const ChatRunPhaseIndicator({
    required this.phase,
    required this.aiStatus,
    required this.onCancel,
    super.key,
    this.modeLabel,
  });

  final ChatRunPhase phase;
  final String? aiStatus;

  /// 可选：本轮双核路由模式（`ux_turn.dual_core_mode`），随阶段一行透明。
  final String? modeLabel;

  final VoidCallback onCancel;

  @override
  State<ChatRunPhaseIndicator> createState() => _ChatRunPhaseIndicatorState();
}

class _ChatRunPhaseIndicatorState extends State<ChatRunPhaseIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 700),
      vsync: this,
    );
    unawaited(_pulseController.repeat());
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final reduceMotion = context.reduceMotion;
    final stage = resolveChatRunStage(widget.phase, widget.aiStatus);
    final stageLabels = {
      ChatRunStage.retrieve: l10n.chatRunPhaseRetrieveLabel,
      ChatRunStage.think: l10n.chatRunPhaseThinkLabel,
      ChatRunStage.generate: l10n.chatRunPhaseGenerateLabel,
    };
    final activeLabel = stageLabels[stage]!;
    final semanticsLabel =
        l10n.chatRunPhaseLiveLabel(activeLabel);

    return Semantics(
      // 仅 liveRegion 播报阶段，不整体声明为 button——取消是独立的
      // IconButton 语义节点（避免嵌套 button 语义）。container+explicit
      // 阻止子文本并入本节点标签，播报内容精确为「正在{stage}，可取消」。
      container: true,
      explicitChildNodes: true,
      liveRegion: true,
      label: semanticsLabel,
      child: Container(
        margin: const EdgeInsets.only(bottom: DS.spacing12),
        padding: const EdgeInsets.fromLTRB(
          DS.spacing12,
          DS.spacing6,
          DS.spacing4,
          DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.info.withValues(alpha: 0.08),
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: DS.info.withValues(alpha: 0.22)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // V13-RETEST Minor（debug overflow 14px）：三段阶段标签是胶囊的
            // 主内容，按固有宽度参与布局（~200px，远小于最小支持屏宽）；
            // 收敛压力全部交给下方 Flexible 的时长提示（可省略号截断）。
            // 此前三段与提示混排（提示 Text 非弹性、不受约束地取固有宽），
            // 412dp 窄屏上整行超出 14px 触发 OVERFLOWED BY 14 PIXELS。
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (var i = 0; i < ChatRunStage.values.length; i++) ...[
                  if (i > 0)
                    Padding(
                      padding:
                          const EdgeInsets.symmetric(horizontal: DS.spacing4),
                      child: Icon(
                        Icons.chevron_right_rounded,
                        size: DS.iconSizeXs,
                        color: DS.info.withValues(alpha: 0.5),
                      ),
                    ),
                  _stageSegment(
                    context,
                    index: i,
                    label: stageLabels[ChatRunStage.values[i]]!,
                    active: ChatRunStage.values[i] == stage,
                    reduceMotion: reduceMotion,
                  ),
                ],
              ],
            ),
            const SizedBox(width: DS.spacing8),
            Flexible(
              child: Text(
                l10n.chatRunPhaseDurationHint,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: DS.textTertiary,
                  fontSize: DS.fontSizeXs,
                ),
              ),
            ),
            const SizedBox(width: DS.spacing4),
            Semantics(
              button: true,
              label: l10n.chatRunPhaseCancelButton,
              child: IconButton(
                tooltip: l10n.chatRunPhaseCancelButton,
                visualDensity: VisualDensity.compact,
                onPressed: widget.onCancel,
                icon: Icon(
                  Icons.close_rounded,
                  size: DS.iconSizeSm,
                  color: DS.textSecondary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _stageSegment(
    BuildContext context, {
    required int index,
    required String label,
    required bool active,
    required bool reduceMotion,
  }) {
    if (!active) {
      return Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: DS.textSecondary,
          fontSize: DS.fontSizeXs,
        ),
      );
    }
    final dot = _StageDot(
      reduceMotion: reduceMotion,
      pulse: reduceMotion ? null : _pulseController,
    );
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        dot,
        const SizedBox(width: DS.spacing6),
        Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            color: DS.info,
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
      ],
    );
  }
}

class _StageDot extends StatelessWidget {
  const _StageDot({
    required this.reduceMotion,
    this.pulse,
  });

  final bool reduceMotion;
  final Animation<double>? pulse;

  @override
  Widget build(BuildContext context) {
    const dimension = 8.0;
    Widget dot = Container(
      width: dimension,
      height: dimension,
      decoration: BoxDecoration(
        color: DS.info,
        shape: BoxShape.circle,
      ),
    );
    if (reduceMotion || pulse == null) {
      return dot;
    }
    return AnimatedBuilder(
      animation: pulse!,
      builder: (context, child) {
        // 单点呼吸只做透明度微调（0.55–1.0），不做位移缩放过冲（§2.2.1）。
        final value = 0.55 + (1.0 - pulse!.value) * 0.45;
        return Opacity(opacity: value, child: child);
      },
      child: dot,
    );
  }
}
