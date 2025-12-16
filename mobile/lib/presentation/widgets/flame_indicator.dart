import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class FlameIndicator extends StatelessWidget {
  final int currentLevel;
  final int maxLevel;
  final double iconSize;
  final Color activeColor;
  final Color inactiveColor;

  const FlameIndicator({
    super.key,
    required this.currentLevel,
    this.maxLevel = 5, // Default max level
    this.iconSize = AppDesignTokens.iconSizeBase,
    this.activeColor = AppDesignTokens.primaryBase,
    this.inactiveColor = AppDesignTokens.neutral300,
  })  : assert(currentLevel >= 0 && currentLevel <= maxLevel);

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Flame Level $currentLevel out of $maxLevel',
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(maxLevel, (index) {
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppDesignTokens.spacing4 / 2),
            child: Icon(
              Icons.local_fire_department, // Flame icon
              size: iconSize,
              color: index < currentLevel ? activeColor : inactiveColor,
            ),
          );
        }),
      ),
    );
  }
}