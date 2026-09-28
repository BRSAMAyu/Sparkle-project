import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// V4-U07 快慢反馈：零模型快路（I09 deterministic lane）应答的诚实标记。
///
/// 语义（SCREEN_FAMILIES §对话 + 卡验收「首个有用内容与ack区分」）：快路
/// 回复是版本化模板应答（问候/确认/告别），不是真模型生成内容。气泡尾部
/// 轻量标注「即时回复」（已知形态附形态词），用户可分辨该轮未被真模型
/// 处理——不把模板直出伪装成深度生成，也不给模板内容造「思考过程」。
///
/// 形态词只在 I09 冻结词表内翻译（greeting/acknowledgment/farewell）；
/// 未知 kind 原样不译不猜（只显示「即时回复」本体，不臆造标签）。
String? instantLaneKindLabel(String? kind, BuildContext context) {
  if (kind == null || kind.isEmpty) {
    return null;
  }
  final l10n = context.l10n;
  return switch (kind) {
    'greeting' => l10n.chatLaneKindGreeting,
    'acknowledgment' => l10n.chatLaneKindAcknowledgment,
    'farewell' => l10n.chatLaneKindFarewell,
    _ => null, // 未知形态：不臆造标签
  };
}

class AssistantLaneMarker extends StatelessWidget {
  const AssistantLaneMarker({super.key, this.kind});

  /// I09 `deterministic_lane_kind`（greeting/acknowledgment/farewell；
  /// 未知/缺省 → 只显示「即时回复」本体）。
  final String? kind;

  @override
  Widget build(BuildContext context) {
    final kindLabel = instantLaneKindLabel(kind, context);
    final label = kindLabel == null
        ? context.l10n.chatInstantReply
        : '${context.l10n.chatInstantReply} · $kindLabel';
    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing4),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.bolt_rounded,
            size: DS.iconSizeXs,
            color: DS.textTertiary,
          ),
          const SizedBox(width: DS.spacing4),
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: DS.captionStyle,
            ),
          ),
        ],
      ),
    );
  }
}
