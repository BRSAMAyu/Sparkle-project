import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';

/// WeatherHeader - Inner Weather System for v2.3 dashboard
///
/// Displays the user's "inner weather" based on:
/// - Sprint plan progress
/// - Recent study activity
/// - Anxiety levels from cognitive fragments
class WeatherHeader extends ConsumerWidget {
  const WeatherHeader({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);

    return Container(
      width: double.infinity,
      height: 200,
      decoration: BoxDecoration(
        gradient: _getWeatherGradient(dashboardState.weather.type),
        borderRadius: const BorderRadius.only(
          bottomLeft: Radius.circular(32),
          bottomRight: Radius.circular(32),
        ),
      ),
      child: Stack(
        children: [
          // Weather particles/effects
          _buildWeatherEffects(dashboardState.weather.type),

          // Content
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      _buildWeatherIcon(dashboardState.weather.type),
                      const SizedBox(width: 12),
                      Text(
                        _getWeatherTitle(dashboardState.weather.type),
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    dashboardState.weather.condition,
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.white.withOpacity(0.8),
                    ),
                  ),
                  const Spacer(),
                  // Today's focus summary
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.local_fire_department_rounded,
                          color: Colors.white,
                          size: 20,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '${_formatFocusTime(dashboardState.flame.todayFocusMinutes)} 专注',
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  LinearGradient _getWeatherGradient(String type) {
    switch (type) {
      case 'sunny':
        return const LinearGradient(
          colors: [Color(0xFF4FC3F7), Color(0xFF29B6F6), Color(0xFF03A9F4)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case 'cloudy':
        return const LinearGradient(
          colors: [Color(0xFF78909C), Color(0xFF607D8B), Color(0xFF546E7A)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case 'rainy':
        return const LinearGradient(
          colors: [Color(0xFF5C6BC0), Color(0xFF3F51B5), Color(0xFF303F9F)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case 'meteor':
        return const LinearGradient(
          colors: [Color(0xFFFF8A65), Color(0xFFFF7043), Color(0xFFFF5722)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      default:
        return const LinearGradient(
          colors: [Color(0xFF4FC3F7), Color(0xFF29B6F6)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
    }
  }

  Widget _buildWeatherIcon(String type) {
    IconData icon;
    switch (type) {
      case 'sunny':
        icon = Icons.wb_sunny_rounded;
        break;
      case 'cloudy':
        icon = Icons.cloud_rounded;
        break;
      case 'rainy':
        icon = Icons.thunderstorm_rounded;
        break;
      case 'meteor':
        icon = Icons.auto_awesome_rounded;
        break;
      default:
        icon = Icons.wb_sunny_rounded;
    }
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Icon(icon, color: Colors.white, size: 28),
    );
  }

  String _getWeatherTitle(String type) {
    switch (type) {
      case 'sunny':
        return '晴空万里';
      case 'cloudy':
        return '阴云密布';
      case 'rainy':
        return '风雨欲来';
      case 'meteor':
        return '流星划过';
      default:
        return '晴空万里';
    }
  }

  Widget _buildWeatherEffects(String type) {
    // Simple particle effects based on weather
    return Positioned.fill(
      child: IgnorePointer(
        child: CustomPaint(
          painter: _WeatherParticlePainter(type),
        ),
      ),
    );
  }

  String _formatFocusTime(int minutes) {
    if (minutes < 60) {
      return '${minutes}m';
    }
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    return mins > 0 ? '${hours}h ${mins}m' : '${hours}h';
  }
}

class _WeatherParticlePainter extends CustomPainter {
  final String type;

  _WeatherParticlePainter(this.type);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.white.withOpacity(0.1);

    // Draw subtle circles for decorative effect
    switch (type) {
      case 'sunny':
        // Sun rays
        paint.style = PaintingStyle.stroke;
        paint.strokeWidth = 1;
        for (int i = 0; i < 8; i++) {
          canvas.drawCircle(
            Offset(size.width * 0.8, size.height * 0.3),
            30 + i * 20.0,
            paint,
          );
        }
        break;
      case 'cloudy':
        // Cloud shapes
        paint.style = PaintingStyle.fill;
        canvas.drawCircle(
          Offset(size.width * 0.7, size.height * 0.4),
          40,
          paint,
        );
        canvas.drawCircle(
          Offset(size.width * 0.8, size.height * 0.5),
          30,
          paint,
        );
        break;
      case 'rainy':
        // Rain drops
        paint.style = PaintingStyle.fill;
        for (int i = 0; i < 20; i++) {
          final x = (size.width * 0.5) + (i % 5) * 30;
          final y = (size.height * 0.2) + (i ~/ 5) * 25;
          canvas.drawRRect(
            RRect.fromRectAndRadius(
              Rect.fromLTWH(x, y, 3, 12),
              const Radius.circular(2),
            ),
            paint,
          );
        }
        break;
      case 'meteor':
        // Shooting stars
        paint.style = PaintingStyle.stroke;
        paint.strokeWidth = 2;
        for (int i = 0; i < 5; i++) {
          final startX = size.width * (0.5 + i * 0.1);
          final startY = size.height * (0.1 + i * 0.1);
          canvas.drawLine(
            Offset(startX, startY),
            Offset(startX + 30, startY + 20),
            paint,
          );
        }
        break;
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
