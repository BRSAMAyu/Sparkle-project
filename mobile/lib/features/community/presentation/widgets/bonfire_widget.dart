import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/core/utils/theme_utils.dart';

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
  // V4-G06 reduce-motion/性能降档等价：与 home DecorationMode 同口径
  // （low=off / medium 或 reduce-motion=staticFrame / 其余全量）。火堆是
  // 装饰（D-COMM：先行动与共享成果，再火堆装饰），staticFrame/off 停表为
  // 静态火苗帧，等级徽标静态可读即语义完整。
  bool _animate = true;
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final tier = PerformanceService.instance.currentTier.value;
    final animate = switch (tier) {
      PerformanceTier.low => false,
      PerformanceTier.medium => false,
      PerformanceTier.high || PerformanceTier.ultra => !context.reduceMotion,
    };
    if (_initialized && animate == _animate) return;
    _initialized = true;
    _animate = animate;
    if (animate) {
      if (!_controller.isAnimating) {
        unawaited(_controller.repeat(reverse: true));
      }
    } else {
      _controller
        ..stop()
        ..value = tier == PerformanceTier.low ? 0.0 : 0.5;
    }
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
    // V4-G06 风格面：等级徽标底=brandPrimary 实心，火色文字/图标压上
    // 实算 1.0–1.7:1 全档失败（四档 brandPrimary 明暗跨度大）——徽标
    // 前景改按徽标底色实算，等级数字四档 ≥4.5:1 可读。
    final badgeBackground = Color.alphaBlend(
      DS.brandPrimary.withValues(alpha: 0.9),
      DS.surfacePrimary,
    );
    final onBadge = ThemeUtils.getContrastSafeText(badgeBackground);

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
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: badgeBackground,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: DS.shadowSm,
                  border: Border.all(color: baseColor.withValues(alpha: 0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.bolt, size: 14, color: onBadge),
                    const SizedBox(width: DS.xs),
                    Text(
                      context.l10n.bonfireLevelBadge(widget.level),
                      key: const ValueKey('bonfire-level-badge'),
                      style: TextStyle(
                        color: onBadge,
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
