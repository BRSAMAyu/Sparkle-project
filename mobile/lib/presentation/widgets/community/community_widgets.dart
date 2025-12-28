import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/sparkle_theme.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/widgets/common/sparkle_avatar.dart';

/// 带有在线状态指示器的头像
class StatusAvatar extends StatelessWidget {

  const StatusAvatar({
    required this.status, super.key,
    this.url,
    this.size = 48,
    this.fallbackText,
  });
  final String? url;
  final UserStatus status;
  final double size;
  final String? fallbackText;

  @override
  Widget build(BuildContext context) {
    final statusColor = status == UserStatus.online 
        ? SparkleTheme.online 
        : (status == UserStatus.invisible ? SparkleTheme.invisible : SparkleTheme.offline);

    return Stack(
      children: [
        DecoratedBox(
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: SparkleTheme.primary.withValues(alpha: 0.1), width: 2),
          ),
          child: SparkleAvatar(
            radius: size / 2,
            url: url,
            fallbackText: fallbackText,
          ),
        ),
        Positioned(
          right: 2,
          bottom: 2,
          child: Container(
            width: size * 0.25,
            height: size * 0.25,
            decoration: BoxDecoration(
              color: statusColor,
              shape: BoxShape.circle,
              border: Border.all(color: DS.brandPrimaryConst, width: 2),
              boxShadow: [
                BoxShadow(
                  color: statusColor.withValues(alpha: 0.4),
                  blurRadius: 4,
                  spreadRadius: 1,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

/// 优雅的消息气泡
class ChatBubble extends StatelessWidget { // 是否已确认 (ACK)

  const ChatBubble({
    required this.content, required this.isMe, required this.time, super.key,
    this.isSent = true,
  });
  final String content;
  final bool isMe;
  final DateTime time;
  final bool isSent;

  @override
  Widget build(BuildContext context) => Align(
      alignment: isMe ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
        padding: EdgeInsets.all(DS.md),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
        decoration: BoxDecoration(
          color: isMe ? SparkleTheme.primary : DS.brandPrimary,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isMe ? 16 : 4),
            bottomRight: Radius.circular(isMe ? 4 : 16),
          ),
          boxShadow: [
            BoxShadow(
              color: DS.brandPrimary.withValues(alpha: 0.05),
              blurRadius: 5,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              content,
              style: TextStyle(
                color: isMe ? DS.brandPrimary : DS.brandPrimary87,
                fontSize: 15,
              ),
            ),
            SizedBox(height: DS.xs),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  "${time.hour}:${time.minute.toString().padLeft(2, '0')}",
                  style: TextStyle(
                    color: isMe ? DS.brandPrimary70 : DS.brandPrimary45,
                    fontSize: 10,
                  ),
                ),
                if (isMe) ...[
                  SizedBox(width: DS.xs),
                  Icon(
                    isSent ? Icons.done_all : Icons.access_time,
                    size: 12,
                    color: isSent ? DS.brandPrimary70 : DS.brandPrimary38,
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
}

/// 正在输入指示器 (动效)
class TypingIndicator extends StatefulWidget {
  const TypingIndicator({super.key});

  @override
  State<TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<TypingIndicator> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 1000))..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Row(
      children: List.generate(3, (index) => AnimatedBuilder(
          animation: _controller,
          builder: (context, child) {
            final delay = index * 0.2;
            final value = Curves.easeInOut.transform((_controller.value - delay).clamp(0.0, 1.0));
            return Container(
              width: 6,
              height: 6,
              margin: const EdgeInsets.symmetric(horizontal: 2),
              decoration: BoxDecoration(
                color: SparkleTheme.primary.withValues(alpha: 0.3 + (value * 0.7)),
                shape: BoxShape.circle,
              ),
            );
          },
        ),),
    );
}
