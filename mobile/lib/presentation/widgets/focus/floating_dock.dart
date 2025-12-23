import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// FocusFloatingDock - 专注模式悬浮窗
/// 支持边缘吸附、自动隐藏、点击展开
class FocusFloatingDock extends StatefulWidget {
  final VoidCallback onTap;
  final Axis initialEdge; // Left, Right, Top, Bottom

  const FocusFloatingDock({
    super.key,
    required this.onTap,
    this.initialEdge = Axis.horizontal,
  });

  @override
  State<FocusFloatingDock> createState() => _FocusFloatingDockState();
}

class _FocusFloatingDockState extends State<FocusFloatingDock> with SingleTickerProviderStateMixin {
  Offset _position = const Offset(0, 300);
  bool _isExpanded = false;
  bool _isHiding = false;
  
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _animation = CurvedAnimation(parent: _controller, curve: Curves.easeInOut);
  }

  void _snapToEdge(Size screenSize) {
    setState(() {
      if (_position.dx < screenSize.width / 2) {
        _position = Offset(0, _position.dy);
      } else {
        _position = Offset(screenSize.width - 60, _position.dy);
      }
      _isHiding = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final Size screenSize = MediaQuery.of(context).size;

    return Positioned(
      left: _position.dx,
      top: _position.dy,
      child: GestureDetector(
        onPanUpdate: (details) {
          setState(() {
            _position += details.delta;
            _isHiding = false;
          });
        },
        onPanEnd: (details) {
          _snapToEdge(screenSize);
        },
        onTap: () {
          setState(() {
            _isHiding = !_isHiding;
          });
          widget.onTap();
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          width: _isHiding ? 20 : 60,
          height: 60,
          decoration: BoxDecoration(
            color: AppDesignTokens.primaryBase.withOpacity(0.9),
            borderRadius: BorderRadius.horizontal(
              left: _position.dx > 100 ? const Radius.circular(30) : Radius.zero,
              right: _position.dx < 100 ? const Radius.circular(30) : Radius.zero,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.3),
                blurRadius: 10,
                spreadRadius: 2,
              ),
            ],
          ),
          child: _isHiding 
            ? const SizedBox.shrink() 
            : const Icon(Icons.timer_rounded, color: Colors.white, size: 30),
        ),
      ),
    );
  }
}
