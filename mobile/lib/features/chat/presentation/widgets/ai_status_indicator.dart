import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/ai_status_capsule.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/utils/ai_status_mapper.dart';

/// AI 状态指示器
/// 显示 AI 的当前状态（THINKING, GENERATING, EXECUTING_TOOL 等）
class AiStatusIndicator extends StatefulWidget {
  const AiStatusIndicator({
    super.key,
    this.status,
    this.details,
    this.startedAtEpochMs,
  });
  final String? status;
  final String? details;
  final int? startedAtEpochMs;

  @override
  State<AiStatusIndicator> createState() => _AiStatusIndicatorState();
}

class _AiStatusIndicatorState extends State<AiStatusIndicator> {
  Timer? _ticker;

  @override
  void initState() {
    super.initState();
    _configureTicker();
  }

  @override
  void didUpdateWidget(covariant AiStatusIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.startedAtEpochMs != widget.startedAtEpochMs ||
        oldWidget.status != widget.status) {
      _configureTicker();
    }
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  void _configureTicker() {
    _ticker?.cancel();
    if (widget.startedAtEpochMs == null || widget.status == null) {
      return;
    }
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) {
        setState(() {});
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final status = widget.status;
    if (status == null) {
      return const SizedBox.shrink();
    }

    final tone = AiStatusMapper.tone(status);
    final color = AiStatusMapper.toneToColor(tone, context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final elapsedLabel = _elapsedLabel(widget.startedAtEpochMs);

    final trimmedDetails = widget.details?.trim();
    final hasDetails = trimmedDetails != null && trimmedDetails.isNotEmpty;
    final detailsColor = isDark
        ? DS.chatBubbleOtherText.withValues(alpha: 0.88)
        : color.withValues(alpha: 0.9);
    final displayLabel = elapsedLabel == null
        ? AiStatusMapper.label(status)
        : '${AiStatusMapper.label(status)} · $elapsedLabel';

    if (!hasDetails) {
      return AiStatusCapsule(
        label: displayLabel,
        color: color,
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AiStatusCapsule(
          label: displayLabel,
          color: color,
        ),
        const SizedBox(height: 4),
        Text(
          trimmedDetails,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: detailsColor,
              ),
        ),
      ],
    );
  }

  String? _elapsedLabel(int? startedAtEpochMs) {
    if (startedAtEpochMs == null) return null;
    final elapsedMs =
        DateTime.now().millisecondsSinceEpoch - startedAtEpochMs;
    if (elapsedMs < 0) return null;
    final seconds = elapsedMs ~/ 1000;
    if (seconds < 60) {
      return '${seconds}s';
    }
    final minutes = seconds ~/ 60;
    final remainder = seconds % 60;
    return '${minutes}m ${remainder}s';
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
