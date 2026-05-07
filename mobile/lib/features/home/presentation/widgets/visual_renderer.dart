import 'package:flutter/material.dart';
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
  const VisualRenderer({super.key});

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

    return SizedBox.expand(
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
        child: RepaintBoundary(
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
