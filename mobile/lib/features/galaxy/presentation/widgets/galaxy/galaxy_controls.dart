import 'dart:ui';

import 'package:flutter/material.dart';

class GalaxyControls extends StatelessWidget {
  const GalaxyControls({
    required this.onZoomIn,
    required this.onFitToOverview,
    required this.onZoomOut,
    required this.onReplay,
    required this.onSearch,
    required this.isDarkMode,
    this.isReplaying = false,
    this.isSearchOpen = false,
    super.key,
  });

  final VoidCallback onZoomIn;
  final VoidCallback onFitToOverview;
  final VoidCallback onZoomOut;
  final VoidCallback onReplay;
  final VoidCallback onSearch;
  final bool isDarkMode;
  final bool isReplaying;
  final bool isSearchOpen;

  @override
  Widget build(BuildContext context) {
    final backgroundColor = isDarkMode
        ? const Color(0xAA0F1726)
        : Colors.white.withValues(alpha: 0.78);
    final borderColor = isDarkMode
        ? Colors.white.withValues(alpha: 0.12)
        : Colors.black.withValues(alpha: 0.08);
    final iconColor = isDarkMode ? Colors.white : Colors.black87;
    final glowColor =
        isDarkMode ? const Color(0xFF78A7FF) : const Color(0xFF2A5BD7);

    return ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: backgroundColor,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: borderColor),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: isDarkMode ? 0.22 : 0.1),
                blurRadius: 28,
                offset: const Offset(0, 14),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _ControlGroup(
                  borderColor: borderColor,
                  isDarkMode: isDarkMode,
                  children: [
                    _ControlButton(
                      icon: Icons.add_rounded,
                      tooltip: '放大',
                      iconColor: iconColor,
                      onPressed: onZoomIn,
                    ),
                    _ControlButton(
                      icon: Icons.my_location_rounded,
                      tooltip: '返回全景',
                      iconColor: iconColor,
                      onPressed: onFitToOverview,
                    ),
                    _ControlButton(
                      icon: Icons.remove_rounded,
                      tooltip: '缩小',
                      iconColor: iconColor,
                      onPressed: onZoomOut,
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                _ControlGroup(
                  borderColor: borderColor,
                  isDarkMode: isDarkMode,
                  children: [
                    _ControlButton(
                      icon: isSearchOpen
                          ? Icons.search_off_rounded
                          : Icons.search_rounded,
                      tooltip: isSearchOpen ? '关闭搜索' : '搜索节点',
                      iconColor: isSearchOpen ? glowColor : iconColor,
                      onPressed: onSearch,
                      isActive: isSearchOpen,
                      activeGlowColor: glowColor,
                    ),
                    _ControlButton(
                      icon: isReplaying
                          ? Icons.stop_circle_outlined
                          : Icons.play_circle_outline_rounded,
                      tooltip: isReplaying ? '停止构建动画' : '回放构建动画',
                      iconColor: isReplaying ? glowColor : iconColor,
                      onPressed: onReplay,
                      isActive: isReplaying,
                      activeGlowColor: glowColor,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class GalaxySectorIndicator extends StatelessWidget {
  const GalaxySectorIndicator({
    required this.label,
    required this.color,
    required this.isDarkMode,
    super.key,
  });

  final String label;
  final Color color;
  final bool isDarkMode;

  @override
  Widget build(BuildContext context) => AnimatedOpacity(
        duration: const Duration(milliseconds: 150),
        opacity: 1,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: (isDarkMode ? const Color(0xCC101722) : Colors.white)
                .withValues(alpha: 0.88),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: color.withValues(alpha: 0.35)),
            boxShadow: [
              BoxShadow(
                color: color.withValues(alpha: 0.12),
                blurRadius: 18,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.auto_awesome, size: 14, color: color),
                const SizedBox(width: 8),
                Text(
                  label,
                  style: TextStyle(
                    color: isDarkMode ? Colors.white : Colors.black87,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.2,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _ControlButton extends StatelessWidget {
  const _ControlButton({
    required this.icon,
    required this.tooltip,
    required this.iconColor,
    required this.onPressed,
    this.isActive = false,
    this.activeGlowColor,
  });

  final IconData icon;
  final String tooltip;
  final Color iconColor;
  final VoidCallback onPressed;
  final bool isActive;
  final Color? activeGlowColor;

  @override
  Widget build(BuildContext context) => Tooltip(
        message: tooltip,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: isActive
                ? (activeGlowColor ?? iconColor).withValues(alpha: 0.14)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(14),
            boxShadow: [
              if (isActive)
                BoxShadow(
                  color: (activeGlowColor ?? iconColor).withValues(alpha: 0.22),
                  blurRadius: 18,
                  spreadRadius: 1,
                ),
            ],
          ),
          child: IconButton(
            onPressed: onPressed,
            icon: Icon(icon, color: iconColor, size: 20),
            visualDensity: VisualDensity.compact,
          ),
        ),
      );
}

class _ControlGroup extends StatelessWidget {
  const _ControlGroup({
    required this.children,
    required this.borderColor,
    required this.isDarkMode,
  });

  final List<Widget> children;
  final Color borderColor;
  final bool isDarkMode;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: (isDarkMode ? Colors.white : Colors.black)
              .withValues(alpha: isDarkMode ? 0.04 : 0.03),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: borderColor.withValues(alpha: 0.75)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: children
                .expand(
                  (child) => [
                    child,
                    if (child != children.last)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2),
                        child: SizedBox(
                          width: 28,
                          child: Divider(
                            height: 1,
                            thickness: 1,
                            color: borderColor.withValues(alpha: 0.55),
                          ),
                        ),
                      ),
                  ],
                )
                .toList(growable: false),
          ),
        ),
      );
}
