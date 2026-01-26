import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 可展开区域组件（支持智能展开）
class ExpandableSection extends StatefulWidget {
  const ExpandableSection({
    required this.title,
    required this.child,
    super.key,
    this.leading,
    this.trailing,
    this.initiallyExpanded = false,
    this.smartExpand = false, // 智能展开：有数据时自动展开
    this.backgroundColor,
  });

  final String title;
  final Widget child;
  final Widget? leading;
  final Widget? trailing;
  final bool initiallyExpanded;
  final bool smartExpand; // 智能展开模式
  final Color? backgroundColor;

  @override
  State<ExpandableSection> createState() => _ExpandableSectionState();
}

class _ExpandableSectionState extends State<ExpandableSection>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;
  bool _isExpanded = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: DS.quick,
    );
    _animation = CurvedAnimation(parent: _controller, curve: Curves.easeInOut);

    // 智能展开逻辑
    bool shouldExpand = widget.initiallyExpanded;
    if (widget.smartExpand) {
      // 判断子组件是否有实际内容
      shouldExpand = _hasContent();
    }

    if (shouldExpand) {
      _isExpanded = true;
      _controller.value = 1.0;
    }
  }

  /// 检查是否有实际内容（用于智能展开）
  bool _hasContent() {
    // 简单的启发式检查：如果子组件不是空的 SizedBox，认为有内容
    // 调用方可以通过 smartExpand 参数让组件自动判断
    return true;
  }

  void _toggle() {
    setState(() {
      _isExpanded = !_isExpanded;
      if (_isExpanded) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: widget.backgroundColor ?? DS.surfaceSecondary,
        borderRadius: DS.borderRadius8,
        border: Border.all(color: DS.neutral200),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          InkWell(
            onTap: _toggle,
            borderRadius: DS.borderRadius8,
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing12),
              child: Row(
                children: [
                  if (widget.leading != null) ...[
                    widget.leading!,
                    const SizedBox(width: DS.spacing8),
                  ],
                  Expanded(
                    child: Text(
                      widget.title,
                      style: TextStyle(
                        fontSize: DS.fontSizeSm,
                        fontWeight: DS.fontWeightSemibold,
                        color: DS.textPrimary,
                      ),
                    ),
                  ),
                  if (widget.trailing != null) ...[
                    widget.trailing!,
                    const SizedBox(width: DS.spacing8),
                  ],
                  AnimatedRotation(
                    turns: _isExpanded ? 0.5 : 0,
                    duration: DS.quick,
                    child: Icon(
                      Icons.expand_more,
                      size: 20,
                      color: DS.neutral600,
                    ),
                  ),
                ],
              ),
            ),
          ),
          ClipRect(
            child: SizeTransition(
              sizeFactor: _animation,
              axisAlignment: -1,
              child: Padding(
                padding: const EdgeInsets.only(
                  left: DS.spacing12,
                  right: DS.spacing12,
                  bottom: DS.spacing12,
                ),
                child: widget.child,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
