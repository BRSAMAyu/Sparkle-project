import 'package:flutter/material.dart';

// 1. 像素进度条 (像血条一样)
class PixelProgressBar extends StatelessWidget {
  final double progress; // 0.0 到 1.0
  final Color color;
  final double height;

  const PixelProgressBar({
    super.key,
    required this.progress,
    this.color = const Color(0xFF6C63FF), // 默认紫色
    this.height = 24,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: Colors.black, width: 3),
        boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(4, 4))],
      ),
      child: FractionallySizedBox(
        alignment: Alignment.centerLeft,
        widthFactor: progress.clamp(0.0, 1.0),
        child: Container(
          margin: const EdgeInsets.all(2), // 内边距，露出一点白边
          decoration: BoxDecoration(
            color: color,
            // 简单的像素纹理效果（可选）
          ),
        ),
      ),
    );
  }
}

// 2. 像素按钮 (按下有位移反馈)
class PixelButton extends StatefulWidget {
  final String label;
  final IconData? icon;
  final Color color;
  final VoidCallback onPressed;
  final bool isLarge;

  const PixelButton({
    super.key,
    required this.label,
    this.icon,
    this.color = const Color(0xFFEDA446), // 默认橙色
    required this.onPressed,
    this.isLarge = false,
  });

  @override
  State<PixelButton> createState() => _PixelButtonState();
}

class _PixelButtonState extends State<PixelButton> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) => setState(() => _isPressed = false),
      onTapCancel: () => setState(() => _isPressed = false),
      onTap: widget.onPressed,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 50),
        // 按下时移动位置，取消阴影，模拟物理按键
        transform: _isPressed ? Matrix4.translationValues(4, 4, 0) : Matrix4.identity(),
        padding: EdgeInsets.symmetric(
          horizontal: widget.isLarge ? 32 : 16, 
          vertical: widget.isLarge ? 16 : 12
        ),
        decoration: BoxDecoration(
          color: widget.color,
          border: Border.all(color: Colors.black, width: 3),
          boxShadow: _isPressed
              ? [] // 按下没阴影
              : const [BoxShadow(color: Colors.black, offset: Offset(4, 4))],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (widget.icon != null) ...[
              Icon(widget.icon, color: Colors.black, size: widget.isLarge ? 28 : 20),
              const SizedBox(width: 8),
            ],
            Text(
              widget.label,
              style: TextStyle(
                color: Colors.black,
                fontWeight: FontWeight.w900,
                fontSize: widget.isLarge ? 20 : 16,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// 3. 复古倒计时数字
class PixelTimerDisplay extends StatelessWidget {
  final int secondsRemaining;

  const PixelTimerDisplay({super.key, required this.secondsRemaining});

  @override
  Widget build(BuildContext context) {
    final minutes = (secondsRemaining / 60).floor().toString().padLeft(2, '0');
    final seconds = (secondsRemaining % 60).toString().padLeft(2, '0');

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.black, // 黑底
        border: Border.all(color: Colors.grey, width: 4),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        "$minutes:$seconds",
        style: const TextStyle(
          color: Color(0xFF00FF00), // 电子表绿
          fontSize: 64,
          fontWeight: FontWeight.w900,
          letterSpacing: 4,
          fontFamily: 'Courier', // 等宽字体模拟电子表
        ),
      ),
    );
  }
}