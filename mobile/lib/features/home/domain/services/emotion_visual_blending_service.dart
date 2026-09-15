import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

enum CognitiveState {
  focus,
  joyful,
  tired,
  excited,
  calm,
}

enum WeatherCondition {
  sunny,
  cloudy,
  rainy,
  meteor,
}

class VisualBlendParams {
  VisualBlendParams({
    required this.primaryTint,
    required this.particleDensity,
    required this.animationSpeed,
    required this.backgroundOpacity,
  });

  final Color primaryTint;
  final double particleDensity;
  final double animationSpeed;
  final double backgroundOpacity;

  VisualBlendParams copyWith({
    Color? primaryTint,
    double? particleDensity,
    double? animationSpeed,
    double? backgroundOpacity,
  }) =>
      VisualBlendParams(
        primaryTint: primaryTint ?? this.primaryTint,
        particleDensity: particleDensity ?? this.particleDensity,
        animationSpeed: animationSpeed ?? this.animationSpeed,
        backgroundOpacity: backgroundOpacity ?? this.backgroundOpacity,
      );
}

class EmotionVisualBlendingService {
  /// 根据认知状态计算视觉参数
  VisualBlendParams calculateBlendParams(CognitiveState state) {
    switch (state) {
      case CognitiveState.focus:
        return VisualBlendParams(
          primaryTint: DS.info,
          particleDensity: 0.3,
          animationSpeed: 0.5,
          backgroundOpacity: 0.28,
        );
      case CognitiveState.joyful:
        return VisualBlendParams(
          primaryTint: DS.warning,
          particleDensity: 0.5,
          animationSpeed: 1.0,
          backgroundOpacity: 0.32,
        );
      case CognitiveState.tired:
        return VisualBlendParams(
          primaryTint: DS.neutral400,
          particleDensity: 0.2,
          animationSpeed: 0.3,
          backgroundOpacity: 0.2,
        );
      case CognitiveState.excited:
        return VisualBlendParams(
          primaryTint: DS.error,
          particleDensity: 0.8,
          animationSpeed: 1.5,
          backgroundOpacity: 0.38,
        );
      case CognitiveState.calm:
        return VisualBlendParams(
          primaryTint: DS.success,
          particleDensity: 0.4,
          animationSpeed: 0.7,
          backgroundOpacity: 0.26,
        );
    }
  }

  /// 混合装备元素与天气效果
  VisualBlendParams blendWithWeather(
    VisualBlendParams base,
    WeatherCondition weather,
  ) {
    switch (weather) {
      case WeatherCondition.rainy:
        return base.copyWith(
          particleDensity: (base.particleDensity * 0.8).clamp(0.15, 1.0),
          animationSpeed: (base.animationSpeed * 0.85).clamp(0.25, 1.6),
          backgroundOpacity: (base.backgroundOpacity * 0.92).clamp(0.15, 0.5),
        );
      case WeatherCondition.cloudy:
        return base.copyWith(
          particleDensity: (base.particleDensity * 0.9).clamp(0.15, 1.0),
          animationSpeed: (base.animationSpeed * 0.95).clamp(0.25, 1.6),
        );
      case WeatherCondition.meteor:
        return base.copyWith(
          particleDensity: (base.particleDensity * 1.05).clamp(0.2, 1.0),
          animationSpeed: (base.animationSpeed * 1.1).clamp(0.3, 1.8),
          backgroundOpacity: (base.backgroundOpacity + 0.04).clamp(0.15, 0.5),
        );
      case WeatherCondition.sunny:
        return base.copyWith(
          particleDensity: (base.particleDensity * 1.05).clamp(0.2, 1.0),
          backgroundOpacity: (base.backgroundOpacity + 0.03).clamp(0.15, 0.5),
        );
    }
  }
}
