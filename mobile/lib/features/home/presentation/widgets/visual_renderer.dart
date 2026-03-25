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
import 'package:sparkle/shared/entities/visual_element_model.dart';
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
    final equippedElements = [
      config?.equippedBackground,
      config?.equippedParticle,
      config?.equippedEffect,
    ].whereType<VisualElementModel>().toList();
    final gloryAccent = _resolveAccent(equippedElements);
    final gloryIntensity = _resolveIntensity(equippedElements);
    final identityLabel = _resolveIdentityLabel(equippedElements);

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

          if (equippedElements.isNotEmpty)
            _GloryOverlayLayer(
              accent: gloryAccent,
              intensity: gloryIntensity,
              animation: _mainAnimationController,
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
          if (identityLabel != null)
            Positioned(
              top: MediaQuery.of(context).padding.top + 8,
              left: 16,
              child: _buildIdentityBadge(identityLabel, gloryAccent),
            ),
        ],
      ),
    );
  }

  Widget _buildIdentityBadge(String label, Color accent) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing10,
        ),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              accent.withValues(alpha: 0.2),
              DS.surfacePrimary.withValues(alpha: 0.82),
            ],
          ),
          borderRadius: DS.borderRadius12,
          border: Border.all(color: accent.withValues(alpha: 0.32)),
          boxShadow: [
            BoxShadow(
              color: accent.withValues(alpha: 0.16),
              blurRadius: 18,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightBold,
            color: accent,
          ),
        ),
      );

  double _resolveIntensity(List<VisualElementModel> elements) {
    if (elements.isEmpty) return 0.0;
    final maxWeight = elements
        .map((element) => element.visibilityWeight)
        .reduce((a, b) => a > b ? a : b);
    return (maxWeight / 100).clamp(0.2, 1.0);
  }

  String? _resolveIdentityLabel(List<VisualElementModel> elements) {
    if (elements.isEmpty) return null;
    final sorted = [...elements]
      ..sort((a, b) => b.visibilityWeight.compareTo(a.visibilityWeight));
    final lead = sorted.first;
    return lead.prestigeLabel ?? lead.name;
  }

  Color _resolveAccent(List<VisualElementModel> elements) {
    for (final element in elements) {
      final candidates = [
        (element.config['color'] as String?),
        if (element.config['colors'] is List<dynamic> &&
            (element.config['colors'] as List<dynamic>).isNotEmpty)
          (element.config['colors'] as List<dynamic>).first.toString(),
        if (element.config['gradient'] is List<dynamic> &&
            (element.config['gradient'] as List<dynamic>).isNotEmpty)
          (element.config['gradient'] as List<dynamic>).last.toString(),
      ].whereType<String>();
      for (final candidate in candidates) {
        final parsed = _parseHexColor(candidate);
        if (parsed != null) return parsed;
      }
    }
    return const Color(0xFF8BE9FD);
  }

  Color? _parseHexColor(String raw) {
    final value = raw.replaceFirst('#', '');
    final normalized = value.length == 6 ? 'FF$value' : value;
    final parsed = int.tryParse(normalized, radix: 16);
    return parsed == null ? null : Color(parsed);
  }

  Widget _buildWeatherStatus(String type, String condition) => Container(
        constraints: const BoxConstraints(maxWidth: 188),
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              _weatherAccent(type).withValues(alpha: 0.18),
              DS.surfacePrimary.withValues(alpha: 0.86),
              DS.surfaceSecondary.withValues(alpha: 0.76),
            ],
            stops: const [0.0, 0.4, 1.0],
          ),
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: _weatherAccent(type).withValues(alpha: 0.26),
          ),
          boxShadow: [
            BoxShadow(
              color: _weatherAccent(type).withValues(alpha: 0.12),
              blurRadius: 20,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _getWeatherTitle(type),
                        style: TextStyle(
                          fontSize: DS.fontSizeSm,
                          fontWeight: DS.fontWeightBold,
                          color: DS.textPrimary,
                        ),
                      ),
                      const SizedBox(height: DS.spacing2),
                      Text(
                        _getWeatherSubtitle(type),
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: DS.textSecondary,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: DS.spacing10),
                _buildWeatherIcon(type),
              ],
            )
                .animate(
                    onPlay: (controller) => controller.repeat(reverse: true))
                .fadeIn(duration: 2000.ms)
                .scale(
                  begin: const Offset(0.95, 0.95),
                  end: const Offset(1.0, 1.0),
                  duration: 2000.ms,
                ),
            const SizedBox(height: DS.spacing10),
            Wrap(
              alignment: WrapAlignment.end,
              spacing: DS.spacing6,
              runSpacing: DS.spacing6,
              children: [
                _buildWeatherChip(
                  _getWeatherRhythm(type),
                  _weatherAccent(type),
                ),
                _buildWeatherChip(
                  condition.isNotEmpty ? condition : _getWeatherCue(type),
                  Color.lerp(_weatherAccent(type), DS.info, 0.35) ?? DS.info,
                ),
              ],
            ).animate().fadeIn(delay: 180.ms),
          ],
        ),
      );

  Widget _buildWeatherChip(String label, Color color) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: color.withValues(alpha: 0.18)),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: color,
            fontWeight: DS.fontWeightMedium,
          ),
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

    final accent = _weatherAccent(type);

    return Container(
      width: 34,
      height: 34,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            accent.withValues(alpha: 0.24),
            accent.withValues(alpha: 0.08),
            Colors.transparent,
          ],
        ),
      ),
      child: Icon(
        iconData,
        size: 18,
        color: accent,
      ),
    );
  }

  Color _weatherAccent(String type) => switch (type) {
        'sunny' => const Color(0xFFFFC857),
        'cloudy' => const Color(0xFF8BA3C7),
        'rainy' => const Color(0xFF66C7F4),
        'meteor' => const Color(0xFFB78CFF),
        _ => DS.brandPrimary,
      };

  String _getWeatherTitle(String type) => switch (type) {
        'sunny' => '晴空万里',
        'cloudy' => '薄雾弥漫',
        'rainy' => '风雨欲来',
        'meteor' => '繁星入梦',
        _ => '晴空万里',
      };

  String _getWeatherSubtitle(String type) => switch (type) {
        'sunny' => '光感上扬，今天适合把推进感拉满。',
        'cloudy' => '边界柔和，适合整理思路与缓冲节奏。',
        'rainy' => '环境压低，适合沉浸专注与减少噪声。',
        'meteor' => '灵感高亮，适合冲刺、突破与留下痕迹。',
        _ => '今天的氛围已经准备就绪。',
      };

  String _getWeatherRhythm(String type) => switch (type) {
        'sunny' => '节奏: 明亮推进',
        'cloudy' => '节奏: 柔和过渡',
        'rainy' => '节奏: 深潜聚焦',
        'meteor' => '节奏: 高光冲刺',
        _ => '节奏: 平稳展开',
      };

  String _getWeatherCue(String type) => switch (type) {
        'sunny' => '感官提示: 提升出发感',
        'cloudy' => '感官提示: 保持留白',
        'rainy' => '感官提示: 收拢注意力',
        'meteor' => '感官提示: 捕捉灵感窗口',
        _ => '感官提示: 保持状态流动',
      };
}

class _GloryOverlayLayer extends StatelessWidget {
  const _GloryOverlayLayer({
    required this.accent,
    required this.intensity,
    required this.animation,
  });

  final Color accent;
  final double intensity;
  final Animation<double> animation;

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: AnimatedBuilder(
          animation: animation,
          builder: (context, child) => CustomPaint(
            size: Size.infinite,
            painter: _GloryOverlayPainter(
              accent: accent,
              intensity: intensity,
              animationValue: animation.value,
            ),
          ),
        ),
      );
}

class _GloryOverlayPainter extends CustomPainter {
  _GloryOverlayPainter({
    required this.accent,
    required this.intensity,
    required this.animationValue,
  });

  final Color accent;
  final double intensity;
  final double animationValue;

  @override
  void paint(Canvas canvas, Size size) {
    final pulse = 0.88 + animationValue * 0.24;
    final topGlow = Paint()
      ..shader = RadialGradient(
        center: const Alignment(0.82, -0.28),
        radius: 0.95,
        colors: [
          accent.withValues(alpha: 0.24 * intensity * pulse),
          accent.withValues(alpha: 0.08 * intensity),
          Colors.transparent,
        ],
        stops: const [0.0, 0.42, 1.0],
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, topGlow);

    final framePaint = Paint()
      ..color = accent.withValues(alpha: 0.14 * intensity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;
    final inset = 12 + (1 - intensity) * 8;
    final rect = RRect.fromRectAndRadius(
      Rect.fromLTWH(
        inset,
        inset + 20,
        size.width - inset * 2,
        size.height - inset * 2 - 28,
      ),
      const Radius.circular(24),
    );
    canvas.drawRRect(rect, framePaint);

    final ribbonPaint = Paint()
      ..color = accent.withValues(alpha: 0.12 * intensity)
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;
    for (var i = 0; i < 3; i++) {
      final y = size.height * (0.22 + i * 0.11);
      canvas.drawLine(
        Offset(size.width * 0.08, y),
        Offset(size.width * (0.34 + animationValue * 0.05), y - 18),
        ribbonPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _GloryOverlayPainter oldDelegate) =>
      animationValue != oldDelegate.animationValue ||
      intensity != oldDelegate.intensity ||
      accent != oldDelegate.accent;
}
