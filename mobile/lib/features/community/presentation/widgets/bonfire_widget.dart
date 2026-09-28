import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// 群火堆（S-03/D-COMM 语义：Flame 只表达群活跃度，由打卡/协作喂养，
/// 不作权益/付费信号；读屏语义由使用方 [Semantics] 承载）。
///
/// V4-U11（统一火堆呈现）：
/// - 等级徽标走 l10n（`bonfireLevelBadge`），不再硬编码「Lv.」；
/// - 移除原「Crackle/Silent」假开关——它只翻图标、从不播放任何声音
///   （假 affordance 即假成功家族，诚实红线不保留；真实背景声/提示音
///   偏好归设置域统一开关，不在装饰组件内私设入口）。
class BonfireWidget extends StatefulWidget {
  const BonfireWidget({
    required this.level,
    super.key,
    this.size = 120,
  });
  final int level; // 1-5
  final double size;

  @override
  State<BonfireWidget> createState() => _BonfireWidgetState();
}

class _BonfireWidgetState extends State<BonfireWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
    unawaited(_controller.repeat(reverse: true));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Color _getFireColor() {
    if (widget.level >= 5) return DS.prismPurple;
    if (widget.level >= 4) return DS.errorAccent;
    if (widget.level >= 3) return DS.error;
    if (widget.level >= 2) return DS.warningAccent;
    return DS.warning;
  }

  @override
  Widget build(BuildContext context) {
    final baseColor = _getFireColor();
    final scaleFactor = 1.0 + (widget.level * 0.1);

    return RepaintBoundary(
      child: SizedBox(
        width: widget.size * 1.5,
        height: widget.size * 1.5,
        child: Stack(
          alignment: Alignment.center,
        children: [
          // Outer Glow
          AnimatedBuilder(
            animation: _controller,
            builder: (context, child) => Container(
              width: widget.size * scaleFactor,
              height: widget.size * scaleFactor,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    baseColor.withValues(
                      alpha: 0.1 + (_controller.value * 0.1),
                    ),
                    DS.surfacePrimary.withValues(alpha: 0),
                  ],
                  stops: const [0.4, 1.0],
                ),
              ),
            ),
          ),

          // Inner Pulse
          AnimatedBuilder(
            animation: _controller,
            builder: (context, child) => Transform.scale(
              scale: 1.0 + (_controller.value * 0.05),
              child: Container(
                width: widget.size * 0.8 * scaleFactor,
                height: widget.size * 0.8 * scaleFactor,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      baseColor.withValues(alpha: 0.2),
                      DS.surfacePrimary.withValues(alpha: 0),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Background flame (darker)
          Positioned(
            bottom: widget.size * 0.1,
            child: Icon(
              Icons.local_fire_department,
              size: widget.size * scaleFactor,
              color: baseColor.withValues(alpha: 0.5),
            ),
          ),

          // Foreground flame (brighter)
          AnimatedBuilder(
            animation: _controller,
            builder: (context, child) => Positioned(
              bottom: widget.size * 0.1 + (_controller.value * 2),
              child: Icon(
                Icons.local_fire_department,
                size: widget.size * 0.95 * scaleFactor,
                color: baseColor,
              ),
            ),
          ),

          // Level Badge（l10n：徽标文案随语言，不硬编码）
          Positioned(
            bottom: 0,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.9),
                borderRadius: BorderRadius.circular(20),
                boxShadow: DS.shadowSm,
                border: Border.all(color: baseColor.withValues(alpha: 0.3)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.bolt, size: 14, color: baseColor),
                  const SizedBox(width: DS.xs),
                  Text(
                    context.l10n.bonfireLevelBadge(widget.level),
                    key: const ValueKey('bonfire-level-badge'),
                    style: TextStyle(
                      color: baseColor,
                      fontWeight: DS.fontWeightBold,
                      fontSize: DS.fontSizeXs,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
        ),
      ),
    );
  }
}
