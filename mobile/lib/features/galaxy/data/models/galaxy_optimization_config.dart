import 'package:flutter/foundation.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';

enum ShaderQuality {
  ultra,    // Gravity + Fluid + Particles
  high,     // Gravity + Particles
  medium,   // Particles
  low,      // Simple Animation
  off,      // Static
}

class GalaxyOptimizationConfig {
  const GalaxyOptimizationConfig({
    required this.shaderQuality,
    required this.maxNodes,
    required this.enablePhysics,
    required this.targetFps,
  });

  factory GalaxyOptimizationConfig.fromTier(PerformanceTier tier) {
    switch (tier) {
      case PerformanceTier.ultra:
        return const GalaxyOptimizationConfig(
          shaderQuality: ShaderQuality.ultra,
          maxNodes: 2000,
          enablePhysics: true,
          targetFps: 60,
        );
      case PerformanceTier.high:
        return const GalaxyOptimizationConfig(
          shaderQuality: ShaderQuality.high,
          maxNodes: 1000,
          enablePhysics: true,
          targetFps: 60,
        );
      case PerformanceTier.medium:
        return const GalaxyOptimizationConfig(
          shaderQuality: ShaderQuality.medium,
          maxNodes: 500,
          enablePhysics: false,
          targetFps: 30,
        );
      case PerformanceTier.low:
        return const GalaxyOptimizationConfig(
          shaderQuality: ShaderQuality.low,
          maxNodes: 200,
          enablePhysics: false,
          targetFps: 30,
        );
    }
  }

  // Fallback if tier is unknown
  static const GalaxyOptimizationConfig standard = GalaxyOptimizationConfig(
    shaderQuality: ShaderQuality.medium,
    maxNodes: 500,
    enablePhysics: false,
    targetFps: 30,
  );

  final ShaderQuality shaderQuality;
  final int maxNodes;
  final bool enablePhysics;
  final int targetFps;
  
  GalaxyOptimizationConfig copyWith({
    ShaderQuality? shaderQuality,
    int? maxNodes,
    bool? enablePhysics,
    int? targetFps,
  }) => GalaxyOptimizationConfig(
      shaderQuality: shaderQuality ?? this.shaderQuality,
      maxNodes: maxNodes ?? this.maxNodes,
      enablePhysics: enablePhysics ?? this.enablePhysics,
      targetFps: targetFps ?? this.targetFps,
    );
}