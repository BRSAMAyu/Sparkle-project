import 'dart:math';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 翻页时钟组件 - 星空渐变风格
class FlipClock extends StatelessWidget {

  const FlipClock({
    required this.seconds, super.key,
    this.showHours = false,
  });
  final int seconds;
  final bool showHours;

  @override
  Widget build(BuildContext context) {
    final duration = Duration(seconds: seconds);
    final hours = duration.inHours;
    final minutes = duration.inMinutes % 60;
    final secs = duration.inSeconds % 60;

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (showHours || hours > 0) ...[
          _FlipDigit(digit: hours ~/ 10),
          _FlipDigit(digit: hours % 10),
          const _Colon(),
        ],
        _FlipDigit(digit: minutes ~/ 10),
        _FlipDigit(digit: minutes % 10),
        const _Colon(),
        _FlipDigit(digit: secs ~/ 10),
        _FlipDigit(digit: secs % 10),
      ],
    );
  }
}

/// 单个翻转数字
class _FlipDigit extends StatefulWidget {

  const _FlipDigit({required this.digit});
  final int digit;

  @override
  State<_FlipDigit> createState() => _FlipDigitState();
}

class _FlipDigitState extends State<_FlipDigit>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _topFlipAnimation;
  late Animation<double> _bottomFlipAnimation;

  int _currentDigit = 0;
  int _nextDigit = 0;

  @override
  void initState() {
    super.initState();
    _currentDigit = widget.digit;
    _nextDigit = widget.digit;

    _controller = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );

    _topFlipAnimation = Tween<double>(
      begin: 0,
      end: pi / 2,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: const Interval(0, 0.5, curve: Curves.easeIn),
    ),);

    _bottomFlipAnimation = Tween<double>(
      begin: -pi / 2,
      end: 0,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.5, 1.0, curve: Curves.easeOut),
    ),);
  }

  @override
  void didUpdateWidget(covariant _FlipDigit oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.digit != widget.digit) {
      _nextDigit = widget.digit;
      _controller.forward(from: 0).then((_) {
        setState(() {
          _currentDigit = _nextDigit;
        });
      });
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Container(
      margin: const EdgeInsets.symmetric(horizontal: 3),
      child: Stack(
        children: [
          // 静态下半部分（当前数字）
          _buildHalf(
            digit: _currentDigit,
            isTop: false,
            rotationX: 0,
          ),

          // 静态上半部分（下一个数字）
          _buildHalf(
            digit: _nextDigit,
            isTop: true,
            rotationX: 0,
          ),

          // 动画上半部分翻转（当前数字向下翻）
          AnimatedBuilder(
            animation: _topFlipAnimation,
            builder: (context, _) => Transform(
                alignment: Alignment.bottomCenter,
                transform: Matrix4.identity()
                  ..setEntry(3, 2, 0.001)
                  ..rotateX(_topFlipAnimation.value),
                child: _buildHalf(
                  digit: _currentDigit,
                  isTop: true,
                  rotationX: _topFlipAnimation.value,
                ),
              ),
          ),

          // 动画下半部分翻转（下一个数字从上翻下来）
          AnimatedBuilder(
            animation: _bottomFlipAnimation,
            builder: (context, _) => Transform(
                alignment: Alignment.topCenter,
                transform: Matrix4.identity()
                  ..setEntry(3, 2, 0.001)
                  ..rotateX(_bottomFlipAnimation.value),
                child: _buildHalf(
                  digit: _nextDigit,
                  isTop: false,
                  rotationX: _bottomFlipAnimation.value,
                ),
              ),
          ),
        ],
      ),
    );

  Widget _buildHalf({
    required int digit,
    required bool isTop,
    required double rotationX,
  }) => ClipRect(
      child: Align(
        alignment: isTop ? Alignment.topCenter : Alignment.bottomCenter,
        heightFactor: 0.5,
        child: Container(
          width: 50,
          height: 80,
          decoration: BoxDecoration(
            color: DS.deepSpaceSurface,
            borderRadius: BorderRadius.vertical(
              top: isTop ? Radius.circular(8) : Radius.zero,
              bottom: isTop ? Radius.zero : Radius.circular(8),
            ),
            border: Border.all(
              color: DS.brandPrimary.withValues(alpha: 0.1),
              width: 0.5,
            ),
          ),
          child: Center(
            child: ShaderMask(
              shaderCallback: (bounds) => LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    DS.primaryBase,
                    DS.secondaryLight,
                  ],
                ).createShader(bounds),
              child: Text(
                '$digit',
                style: TextStyle(
                  fontSize: 56,
                  fontWeight: FontWeight.bold,
                  color: DS.brandPrimaryConst,
                  fontFamily: 'monospace',
                  height: 1.0,
                ),
              ),
            ),
          ),
        ),
      ),
    );
}

/// 冒号分隔符
class _Colon extends StatefulWidget {
  const _Colon();

  @override
  State<_Colon> createState() => _ColonState();
}

class _ColonState extends State<_Colon> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _opacityAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _opacityAnimation = Tween<double>(begin: 1.0, end: 0.3).animate(_controller);
    _controller.repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
      animation: _opacityAnimation,
      builder: (context, _) => Padding(
          padding: EdgeInsets.symmetric(horizontal: 8),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _buildDot(_opacityAnimation.value),
              SizedBox(height: DS.lg),
              _buildDot(_opacityAnimation.value),
            ],
          ),
        ),
    );

  Widget _buildDot(double opacity) => Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          colors: [
            DS.primaryBase.withValues(alpha: opacity),
            DS.secondaryLight.withValues(alpha: opacity),
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: DS.primaryBase.withValues(alpha: opacity * 0.5),
            blurRadius: 8,
            spreadRadius: 2,
          ),
        ],
      ),
    );
}

/// 简化版时钟（无翻转动画）
class SimpleFlipClock extends StatelessWidget {

  const SimpleFlipClock({
    required this.seconds, super.key,
    this.showHours = false,
    this.fontSize = 64,
  });
  final int seconds;
  final bool showHours;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    final duration = Duration(seconds: seconds);
    final hours = duration.inHours.toString().padLeft(2, '0');
    final minutes = (duration.inMinutes % 60).toString().padLeft(2, '0');
    final secs = (duration.inSeconds % 60).toString().padLeft(2, '0');

    String timeString;
    if (showHours || duration.inHours > 0) {
      timeString = '$hours:$minutes:$secs';
    } else {
      timeString = '$minutes:$secs';
    }

    return ShaderMask(
      shaderCallback: (bounds) => LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.primaryBase,
            DS.secondaryLight,
          ],
        ).createShader(bounds),
      child: Text(
        timeString,
        style: TextStyle(
          fontSize: fontSize,
          fontWeight: FontWeight.bold,
          color: DS.brandPrimaryConst,
          fontFamily: 'monospace',
          letterSpacing: 4,
        ),
      ),
    );
  }
}
