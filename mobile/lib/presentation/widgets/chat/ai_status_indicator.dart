import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/ai_status_capsule.dart';
import 'package:sparkle/core/design/utils/ai_status_mapper.dart';

/// AI 状态指示器
/// 显示 AI 的当前状态（THINKING, GENERATING, EXECUTING_TOOL 等）
class AiStatusIndicator extends StatelessWidget {

  const AiStatusIndicator({
    super.key,
    this.status,
    this.details,
  });
  final String? status;
  final String? details;

  @override
  Widget build(BuildContext context) {
    if (status == null) {
      return const SizedBox.shrink();
    }

    final tone = AiStatusMapper.tone(status!);
    final color = AiStatusMapper.toneToColor(tone, context);

    return AiStatusCapsule(
      label: AiStatusMapper.label(status!),
      color: color,
    );
  }
}

/// AI 状态气泡（紧凑版，用于聊天气泡中）
class AiStatusBubble extends StatelessWidget {

  const AiStatusBubble({
    required this.status,
    super.key,
  });
  final String status;

  @override
  Widget build(BuildContext context) {
    final tone = AiStatusMapper.tone(status);
    final color = AiStatusMapper.toneToColor(tone, context);

    return AiStatusCapsule(
      label: AiStatusMapper.compactLabel(status),
      color: color,
      dense: true,
    );
  }
}
