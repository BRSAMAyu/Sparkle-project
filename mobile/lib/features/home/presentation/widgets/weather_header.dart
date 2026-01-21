import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

/// WeatherHeader - Full-screen background weather system
class WeatherHeader extends ConsumerWidget {
  const WeatherHeader({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;

    return Container(
      width: double.infinity,
      height: double.infinity,
      decoration: BoxDecoration(
        gradient: isDarkMode 
            ? const LinearGradient(
                colors: [Color(0xFF000000), Color(0xFF000000), Color(0xFF000000)],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              )
            : _getWeatherGradient(dashboardState.weather.type),
      ),
      child: Stack(
        children: [
          // Background stars
          const _StarField(),

          // Weather effects (Particles)
          _buildWeatherEffects(dashboardState.weather.type),

          // Corner overlay for weather status
          Positioned(
            top: MediaQuery.of(context).padding.top + 8,
            right: 16,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      _getWeatherTitle(dashboardState.weather.type),
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        color: DS.textSecondary,
                      ),
                    ),
                    const SizedBox(width: 6),
                    _buildWeatherIcon(dashboardState.weather.type, context),
                  ],
                ),
                Text(
                  dashboardState.weather.condition,
                  style: TextStyle(
                    fontSize: 10,
                    color: DS.textSecondary.withValues(alpha: 0.6),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  LinearGradient _getWeatherGradient(String type) {
    switch (type) {
      case 'sunny':
        return LinearGradient(
          colors: [DS.deepSpaceStart, DS.deepSpaceEnd, DS.neutral700],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'cloudy':
        return LinearGradient(
          colors: [DS.neutral900, DS.neutral800, DS.neutral700],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'rainy':
        return LinearGradient(
          colors: [DS.deepSpaceStart, DS.deepSpaceSurface, DS.neutral700],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'meteor':
        return LinearGradient(
          colors: [DS.neutral900, DS.neutral800, DS.secondaryBaseDark],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      default:
        return LinearGradient(
          colors: [DS.deepSpaceStart, DS.deepSpaceEnd],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
    }
  }

  Widget _buildWeatherIcon(String type, BuildContext context) {
    IconData icon;
    switch (type) {
      case 'sunny':
        icon = Icons.wb_sunny_rounded;
      case 'cloudy':
        icon = Icons.cloud_rounded;
      case 'rainy':
        icon = Icons.thunderstorm_rounded;
      case 'meteor':
        icon = Icons.auto_awesome_rounded;
      default:
        icon = Icons.wb_sunny_rounded;
    }
    return Icon(icon, color: DS.brandPrimary, size: 18);
  }

  String _getWeatherTitle(String type) {
    switch (type) {
      case 'sunny':
        return '晴空万里';
      case 'cloudy':
        return '薄雾弥漫';
      case 'rainy':
        return '风雨欲来';
      case 'meteor':
        return '繁星入梦';
      default:
        return '晴空万里';
    }
  }

  Widget _buildWeatherEffects(String type) => Positioned.fill(
        child: IgnorePointer(
          child: CustomPaint(
            painter: _WeatherParticlePainter(type),
          ),
        ),
      );
}

class _StarField extends StatelessWidget {
  const _StarField();

  @override
  Widget build(BuildContext context) => CustomPaint(
        size: MediaQuery.of(context).size,
        painter: _StarPainter(),
      );
}

class _StarPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = DS.brandPrimary;
    final stars = [
      Offset(size.width * 0.1, size.height * 0.15),
      Offset(size.width * 0.3, size.height * 0.08),
      Offset(size.width * 0.5, size.height * 0.12),
      Offset(size.width * 0.7, size.height * 0.05),
      Offset(size.width * 0.85, size.height * 0.18),
      Offset(size.width * 0.15, size.height * 0.25),
      Offset(size.width * 0.6, size.height * 0.22),
      Offset(size.width * 0.9, size.height * 0.28),
      Offset(size.width * 0.25, size.height * 0.35),
      Offset(size.width * 0.75, size.height * 0.32),
      Offset(size.width * 0.4, size.height * 0.45),
      Offset(size.width * 0.1, size.height * 0.65),
      Offset(size.width * 0.8, size.height * 0.75),
      Offset(size.width * 0.5, size.height * 0.85),
    ];

    for (var i = 0; i < stars.length; i++) {
      final opacity = 0.2 + (i % 3) * 0.1;
      final radius = 0.5 + (i % 2) * 0.5;
      paint.color = DS.brandPrimary.withAlpha((opacity * 255).toInt());
      canvas.drawCircle(stars[i], radius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _WeatherParticlePainter extends CustomPainter {
  _WeatherParticlePainter(this.type);
  final String type;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = DS.brandPrimary.withValues(alpha: 0.05);

    switch (type) {
      case 'sunny':
        paint.style = PaintingStyle.stroke;
        paint.strokeWidth = 1;
        for (var i = 0; i < 5; i++) {
          canvas.drawCircle(
            Offset(size.width * 0.8, size.height * 0.2),
            20 + i * 30.0,
            paint,
          );
        }
      case 'cloudy':
        paint.style = PaintingStyle.fill;
        canvas.drawCircle(
            Offset(size.width * 0.2, size.height * 0.1), 60, paint,);
        canvas.drawCircle(
            Offset(size.width * 0.8, size.height * 0.3), 80, paint,);
      case 'rainy':
        paint.style = PaintingStyle.fill;
        paint.color = DS.brandPrimary.withValues(alpha: 0.1);
        for (var i = 0; i < 30; i++) {
          final x = (size.width * 0.1) + (i % 6) * 60;
          final y = (size.height * 0.1) + (i ~/ 6) * 80;
          canvas.drawRect(Rect.fromLTWH(x, y, 1, 15), paint);
        }
      case 'meteor':
        paint.style = PaintingStyle.stroke;
        paint.strokeWidth = 1.5;
        paint.color = DS.brandPrimary.withValues(alpha: 0.2);
        for (var i = 0; i < 3; i++) {
          final start = Offset(
              size.width * (0.3 + i * 0.2), size.height * (0.1 + i * 0.1),);
          canvas.drawLine(start, Offset(start.dx + 40, start.dy + 30), paint);
        }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
