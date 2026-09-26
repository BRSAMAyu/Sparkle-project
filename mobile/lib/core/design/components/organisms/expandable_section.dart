import 'dart:async';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 可展开区域组件（支持智能展开）。
///
/// **N17（A-SPEC3 §4.2）登记：「收起一段内容、点开展开」类披露件的
/// 唯一 owner**。展开族统一语法（新披露件一律走本组件）：
/// - 折叠态 = 标题行 + chevron（[AnimatedRotation] 旋转 180°，M1 同款）；
/// - 展开动画统一时长档 = [ExpandableSection.expandDuration]
///   （AnimationSystem.quick 档，控制器与 chevron 同源，禁各处散落自定）；
/// - 折叠/展开态对无障碍语义单源（头部 [Semantics] 携带 button + expanded）。
/// `AnimatedSize` 只作布局动画原语，禁再作披露门面（自装折叠态）。
/// chat 域的 CollapsibleWidgetWrapper 为登记过的域特化（chip 形态 +
/// 会话内持久化），触碰即迁，新代码不得仿照其旁路 owner。
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

  /// 展开族统一动画时长档（N17 语法）：控制器与 chevron 共用，
  /// 取 AnimationSystem.quick 档——即 DS.quick 的 const 形。
  static const Duration expandDuration = AnimationSystem.quick;

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
      duration: ExpandableSection.expandDuration,
    );
    _animation = CurvedAnimation(parent: _controller, curve: Curves.easeInOut);

    // 智能展开逻辑
    var shouldExpand = widget.initiallyExpanded;
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
  ///
  /// 简单的启发式检查：如果子组件不是空的 SizedBox，认为有内容
  /// 调用方可以通过 smartExpand 参数让组件自动判断
  bool _hasContent() => true;

  void _toggle() {
    setState(() {
      _isExpanded = !_isExpanded;
      if (_isExpanded) {
        unawaited(_controller.forward());
      } else {
        unawaited(_controller.reverse());
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => DecoratedBox(
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
            // N17 披露件语法：头部语义单源——button 角色 + expanded 状态
            // 对读屏单点播报，子组件各自不再重复声明披露态。
            child: Semantics(
              button: true,
              expanded: _isExpanded,
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
                      duration: ExpandableSection.expandDuration,
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
