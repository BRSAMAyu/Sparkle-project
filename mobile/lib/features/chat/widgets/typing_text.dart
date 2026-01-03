import 'dart:async';
import 'package:flutter/material.dart';

/// 打字机效果文本组件
///
/// 设计原则：
/// 1. 性能优化：使用 Timer 而非 Animation，减少重建
/// 2. 可控速度：支持三档速度（快/中/慢）
/// 3. 可中断：支持跳过动画直接显示全文
/// 4. 完成回调：动画结束时通知父组件
class TypingText extends StatefulWidget {

  const TypingText({
    super.key,
    required this.text,
    this.style,
    this.maxLines,
    this.overflow,
    this.textAlign,
    this.charDelay = const Duration(milliseconds: 20),
    this.animate = true,
    this.onComplete,
    this.showCursor = true,
  });

  /// 工厂方法：快速模式
  factory TypingText.fast({
    required String text,
    TextStyle? style,
    VoidCallback? onComplete,
  }) {
    return TypingText(
      text: text,
      style: style,
      charDelay: const Duration(milliseconds: 15),
      onComplete: onComplete,
    );
  }

  /// 工厂方法：慢速模式（适合重点强调）
  factory TypingText.slow({
    required String text,
    TextStyle? style,
    VoidCallback? onComplete,
  }) {
    return TypingText(
      text: text,
      style: style,
      charDelay: const Duration(milliseconds: 50),
      onComplete: onComplete,
    );
  }
  final String text;
  final TextStyle? style;
  final int? maxLines;
  final TextOverflow? overflow;
  final TextAlign? textAlign;

  /// 打字速度：每个字符的延迟（毫秒）
  /// 快速: 15ms, 中速: 30ms, 慢速: 50ms
  final Duration charDelay;

  /// 是否启用打字动画（false 则直接显示全文）
  final bool animate;

  /// 动画完成回调
  final VoidCallback? onComplete;

  /// 是否显示闪烁光标
  final bool showCursor;

  @override
  State<TypingText> createState() => _TypingTextState();
}

class _TypingTextState extends State<TypingText> {
  String _displayedText = '';
  Timer? _typingTimer;
  int _currentIndex = 0;
  bool _isCompleted = false;

  @override
  void initState() {
    super.initState();
    if (widget.animate) {
      _startTyping();
    } else {
      _displayedText = widget.text;
      _isCompleted = true;
    }
  }

  @override
  void didUpdateWidget(TypingText oldWidget) {
    super.didUpdateWidget(oldWidget);

    // 文本变化时重新开始打字
    if (widget.text != oldWidget.text) {
      _stopTyping();
      _currentIndex = 0;
      _displayedText = '';
      _isCompleted = false;

      if (widget.animate) {
        _startTyping();
      } else {
        setState(() {
          _displayedText = widget.text;
          _isCompleted = true;
        });
      }
    }

    // 动画模式变化
    if (widget.animate != oldWidget.animate) {
      if (!widget.animate && !_isCompleted) {
        // 从动画切换到非动画：立即显示全文
        _skipAnimation();
      }
    }
  }

  void _startTyping() {
    _typingTimer = Timer.periodic(widget.charDelay, (timer) {
      if (_currentIndex < widget.text.length) {
        setState(() {
          _currentIndex++;
          _displayedText = widget.text.substring(0, _currentIndex);
        });
      } else {
        _completeTyping();
      }
    });
  }

  void _completeTyping() {
    _stopTyping();
    setState(() {
      _displayedText = widget.text;
      _isCompleted = true;
    });
    widget.onComplete?.call();
  }

  void _stopTyping() {
    _typingTimer?.cancel();
    _typingTimer = null;
  }

  /// 跳过动画，立即显示全文
  void _skipAnimation() {
    if (_isCompleted) return;
    _completeTyping();
  }

  @override
  void dispose() {
    _stopTyping();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => GestureDetector(
      // 点击文本区域可跳过动画（可选功能）
      onTap: widget.animate && !_isCompleted ? _skipAnimation : null,
      child: Text.rich(
        TextSpan(
          text: _displayedText,
          style: widget.style,
          children: [
            // 显示闪烁光标（仅在打字时）
            if (widget.showCursor && !_isCompleted)
              WidgetSpan(
                alignment: PlaceholderAlignment.middle,
                child: _BlinkingCursor(
                  color: widget.style?.color ??
                      Theme.of(context).colorScheme.onSurface,
                ),
              ),
          ],
        ),
        maxLines: widget.maxLines,
        overflow: widget.overflow,
        textAlign: widget.textAlign,
      ),
    );
}

/// 闪烁光标
///
/// 使用 AnimatedOpacity 实现平滑的淡入淡出效果
class _BlinkingCursor extends StatefulWidget {

  const _BlinkingCursor({
    required this.color,
  });
  final Color color;

  @override
  State<_BlinkingCursor> createState() => _BlinkingCursorState();
}

class _BlinkingCursorState extends State<_BlinkingCursor>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 530), // 标准光标闪烁速度
      vsync: this,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => FadeTransition(
      opacity: _controller,
      child: Container(
        width: 2,
        height: 16,
        margin: const EdgeInsets.only(left: 2),
        decoration: BoxDecoration(
          color: widget.color,
          borderRadius: BorderRadius.circular(1),
        ),
      ),
    );
}

/// 打字机效果文本字段（支持富文本）
///
/// 可以分段显示不同样式的文本
class TypingRichText extends StatefulWidget {

  const TypingRichText({
    super.key,
    required this.spans,
    this.charDelay = const Duration(milliseconds: 20),
    this.animate = true,
    this.onComplete,
  });
  final List<TextSpan> spans;
  final Duration charDelay;
  final bool animate;
  final VoidCallback? onComplete;

  @override
  State<TypingRichText> createState() => _TypingRichTextState();
}

class _TypingRichTextState extends State<TypingRichText> {
  late String _fullText;
  String _displayedText = '';
  Timer? _typingTimer;
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    _fullText = _extractText(widget.spans);

    if (widget.animate) {
      _startTyping();
    } else {
      _displayedText = _fullText;
    }
  }

  String _extractText(List<TextSpan> spans) {
    final buffer = StringBuffer();
    for (final span in spans) {
      buffer.write(span.text ?? '');
    }
    return buffer.toString();
  }

  void _startTyping() {
    _typingTimer = Timer.periodic(widget.charDelay, (timer) {
      if (_currentIndex < _fullText.length) {
        setState(() {
          _currentIndex++;
          _displayedText = _fullText.substring(0, _currentIndex);
        });
      } else {
        _stopTyping();
        widget.onComplete?.call();
      }
    });
  }

  void _stopTyping() {
    _typingTimer?.cancel();
    _typingTimer = null;
  }

  @override
  void dispose() {
    _stopTyping();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Text(_displayedText);
}
