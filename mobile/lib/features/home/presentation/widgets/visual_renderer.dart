import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/cognitive_state_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/emotion_visual_blend_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/background_layer.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/effect_layer.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/particle_layer.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/weather_layer.dart';
import 'package:sparkle/shared/providers/visual_element_provider.dart';

/// VisualRenderer - 分层叠加视觉渲染系统
///
/// 渲染层次（从底到顶）：
/// 1. 背景层 (用户选择)
/// 2. 粒子层 (用户选择)
/// 3. 特效层 (用户选择)
/// 4. 天气层 (系统自动，根据用户状态)
class VisualRenderer extends ConsumerStatefulWidget {
  const VisualRenderer({super.key, this.showWeatherStatus = true});

  /// 是否显示天气状态标签
  final bool showWeatherStatus;

  @override
  ConsumerState<VisualRenderer> createState() => _VisualRendererState();
}

class _VisualRendererState extends ConsumerState<VisualRenderer>
    with TickerProviderStateMixin {
  // 动画控制器
  late AnimationController _mainAnimationController;
  late AnimationController _particleController;

  @override
  void initState() {
    super.initState();
    _initAnimations();
  }

  void _initAnimations() {
    // 主动画（用于脉动效果）
    _mainAnimationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);

    // 粒子动画
    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    )..repeat();
  }

  @override
  void dispose() {
    _mainAnimationController.dispose();
    _particleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // 获取视觉配置
    final visualState = ref.watch(visualElementProvider);
    final config = visualState.config;

    final cognitiveState = ref.watch(cognitiveStateProvider);
    final blendParams = ref.watch(emotionVisualBlendProvider(cognitiveState));

    // 获取天气类型
    final dashboardState = ref.watch(dashboardProvider);
    final weatherType = dashboardState.weather.type;
    final weatherCondition = dashboardState.weather.condition;

    return Container(
      width: double.infinity,
      height: double.infinity,
      child: Stack(
        children: [
          // Layer 1: 背景层 (用户选择)
          BackgroundLayer(
            element: config?.equippedBackground,
            mainAnimation: _mainAnimationController,
            tint: blendParams.primaryTint,
            tintOpacity: blendParams.backgroundOpacity,
          ),

          // Layer 2: 粒子层 (用户选择)
          ParticleLayer(
            element: config?.equippedParticle,
            particleAnimation: _particleController,
            mainAnimation: _mainAnimationController,
            density: blendParams.particleDensity,
            speedMultiplier: blendParams.animationSpeed,
          ),

          // Layer 3: 特效层 (用户选择)
          EffectLayer(
            element: config?.equippedEffect,
            mainAnimation: _mainAnimationController,
          ),

          // Layer 4: 天气层 (系统自动，叠加在场景之上)
          WeatherLayer(
            weatherType: weatherType,
            weatherCondition: weatherCondition,
            blendParams: blendParams,
            mainAnimation: _mainAnimationController,
            particleAnimation: _particleController,
          ),

          // 天气状态标签
          if (widget.showWeatherStatus)
            Positioned(
              top: MediaQuery.of(context).padding.top + 8,
              right: 16,
              child: _buildWeatherStatus(weatherType, weatherCondition),
            ),
        ],
      ),
    );
  }

  Widget _buildWeatherStatus(String type, String condition) => Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.surfacePrimary.withValues(alpha: 0.82),
            DS.surfaceSecondary.withValues(alpha: 0.72),
          ],
        ),
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: DS.border.withValues(alpha: 0.5),
        ),
        boxShadow: [
          BoxShadow(
            color: DS.textPrimary.withValues(alpha: 0.08),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _getWeatherTitle(type),
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  color: DS.textSecondary,
                ),
              ),
              const SizedBox(width: 6),
              _buildWeatherIcon(type),
            ],
          )
              .animate(onPlay: (controller) => controller.repeat(reverse: true))
              .fadeIn(duration: 2000.ms)
              .scale(
                begin: const Offset(0.95, 0.95),
                end: const Offset(1.0, 1.0),
                duration: 2000.ms,
              ),
          if (condition.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text(
                condition,
                style: TextStyle(
                  fontSize: 11,
                  color: DS.textTertiary,
                ),
              ).animate().fadeIn(delay: 200.ms),
            ),
        ],
      ),
    );

  Widget _buildWeatherIcon(String type) {
    final iconData = switch (type) {
      'sunny' => Icons.wb_sunny_rounded,
      'cloudy' => Icons.cloud_rounded,
      'rainy' => Icons.water_drop_rounded,
      'meteor' => Icons.auto_awesome_rounded,
      _ => Icons.wb_sunny_rounded,
    };

    return Icon(
      iconData,
      size: 16,
      color: Color.lerp(DS.info, DS.brandPrimary, 0.45),
    );
  }

  String _getWeatherTitle(String type) => switch (type) {
      'sunny' => '晴空万里',
      'cloudy' => '薄雾弥漫',
      'rainy' => '风雨欲来',
      'meteor' => '繁星入梦',
      _ => '晴空万里',
    };
}
