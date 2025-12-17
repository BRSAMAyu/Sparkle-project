import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

class FlameCore extends StatefulWidget {
  final double intensity;

  const FlameCore({required this.intensity, super.key});

  @override
  State<FlameCore> createState() => _FlameCoreState();
}

class _FlameCoreState extends State<FlameCore> with SingleTickerProviderStateMixin {
  late Ticker _ticker;
  double _time = 0.0;
  ui.FragmentProgram? _program;

  @override
  void initState() {
    super.initState();
    _loadShader();
    _ticker = createTicker((elapsed) {
      setState(() {
        _time = elapsed.inMilliseconds / 1000.0;
      });
    });
    _ticker.start();
  }

  Future<void> _loadShader() async {
    try {
      final program = await ui.FragmentProgram.fromAsset('shaders/core_flame.frag');
      setState(() {
        _program = program;
      });
    } catch (e) {
      debugPrint('Failed to load shader: $e');
    }
  }

  @override
  void dispose() {
    _ticker.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_program == null) {
      return const SizedBox(width: 200, height: 200);
    }

    return CustomPaint(
      size: const Size(200, 200),
      painter: _ShaderPainter(
        shader: _program!.fragmentShader(),
        time: _time,
        intensity: widget.intensity,
      ),
    );
  }
}

class _ShaderPainter extends CustomPainter {
  final ui.FragmentShader shader;
  final double time;
  final double intensity;

  _ShaderPainter({
    required this.shader,
    required this.time,
    required this.intensity,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Uniforms: u_time, u_intensity, u_resolution
    // Note: The order must match the uniform order in the GLSL file
    // uniform float u_time;
    // uniform float u_intensity;
    // uniform vec2 u_resolution;
    
    shader.setFloat(0, time);
    shader.setFloat(1, intensity);
    shader.setFloat(2, size.width);
    shader.setFloat(3, size.height);

    final paint = Paint()..shader = shader;
    canvas.drawRect(Offset.zero & size, paint);
  }

  @override
  bool shouldRepaint(covariant _ShaderPainter oldDelegate) {
    return oldDelegate.time != time || oldDelegate.intensity != intensity;
  }
}
