import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// FocusFloatingDock - 专注模式悬浮窗
/// 支持边缘吸附、自动隐藏、点击展开菜单
class FocusFloatingDock extends StatefulWidget {
  // Left, Right, Top, Bottom

  const FocusFloatingDock({
    super.key,
    this.onMindfulnessTap,
    this.onToolsTap,
    this.initialEdge = Axis.horizontal,
  });
  final VoidCallback? onMindfulnessTap;
  final VoidCallback? onToolsTap;
  final Axis initialEdge;

  @override
  State<FocusFloatingDock> createState() => _FocusFloatingDockState();
}

class _FocusFloatingDockState extends State<FocusFloatingDock>
    with SingleTickerProviderStateMixin {
  Offset _position = const Offset(0, 300);
  bool _isExpanded = false;
  bool _isHiding = false;

  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );

    // Auto-hide after 3 seconds of inactivity
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted && !_isExpanded) {
        setState(() => _isHiding = true);
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
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

  void _toggleExpand() {
    unawaited(
      SensoryFeedbackService.emit(
        _isExpanded
            ? SensoryFeedbackEvent.selection
            : SensoryFeedbackEvent.sheetOpen,
      ),
    );
    setState(() {
      _isExpanded = !_isExpanded;
      _isHiding = false;
      if (_isExpanded) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.of(context).size;
    final isRightSide = _position.dx > screenSize.width / 2;

    return Positioned(
      left: _position.dx,
      top: _position.dy,
      child: GestureDetector(
        onPanUpdate: (details) {
          if (_isExpanded) return; // Disable drag when expanded
          setState(() {
            _position += details.delta;
            _isHiding = false;
          });
        },
        onPanEnd: (details) {
          if (_isExpanded) return;
          _snapToEdge(screenSize);
        },
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: 0.92, end: 1),
          duration: DS.durationSlow,
          curve: Curves.easeOutBack,
          builder: (context, value, child) => Transform.scale(
            scale: value,
            child: child,
          ),
          child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          width: _isHiding ? 20 : (_isExpanded ? 180 : 60),
          height: _isExpanded ? 160 : 60,
          decoration: BoxDecoration(
            color: DS.primaryBase.withValues(alpha: 0.95),
            borderRadius: _isHiding
                ? BorderRadius.horizontal(
                    left: isRightSide ? const Radius.circular(30) : Radius.zero,
                    right:
                        !isRightSide ? const Radius.circular(30) : Radius.zero,
                  )
                : BorderRadius.circular(30),
            boxShadow: [
              BoxShadow(
                color: DS.brandPrimary.withValues(alpha: 0.3),
                blurRadius: 10,
                spreadRadius: 2,
              ),
            ],
          ),
          child: _isHiding
              ? InkWell(
                  onTap: () {
                    unawaited(
                      SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                    );
                    setState(() => _isHiding = false);
                  },
                  child: const SizedBox.expand(),
                )
              : _isExpanded
                  ? _buildExpandedMenu()
                  : _buildCollapsedIcon(),
        ),
        ),
      ),
    );
  }

  Widget _buildCollapsedIcon() => InkWell(
        onTap: _toggleExpand,
        borderRadius: BorderRadius.circular(30),
        child: Center(
          child:
              Icon(Icons.timer_rounded, color: DS.brandPrimaryConst, size: 30),
        ),
      );

  Widget _buildExpandedMenu() => Column(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          // Collapse Button
          InkWell(
            onTap: _toggleExpand,
            child: Icon(Icons.close, color: DS.brandPrimaryConst, size: 24),
          ),

          // Menu Items
          _buildMenuItem(
            context: context,
            icon: Icons.self_improvement,
            onTap: () {
              _toggleExpand();
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
              );
              widget.onMindfulnessTap?.call();
            },
          ),
          _buildMenuItem(
            context: context,
            icon: Icons.grid_view,
            onTap: () {
              _toggleExpand();
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
              );
              widget.onToolsTap?.call();
            },
          ),
        ],
      );

  Widget _buildMenuItem({
    required BuildContext context,
    required IconData icon,
    required VoidCallback onTap,
  }) =>
      InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              Icon(icon, color: DS.brandPrimaryConst, size: 20),
              const SizedBox(width: DS.md),
              Text(
                icon == Icons.self_improvement
                    ? context.l10n.focusDockMindfulness
                    : context.l10n.focusDockToolbox,
                style: TextStyle(
                  color: DS.brandPrimaryConst,
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
            ],
          ),
        ),
      );
}
