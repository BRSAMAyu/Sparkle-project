import 'package:flutter/material.dart';
import 'dart:math' as math;

class GalaxyScreen extends StatefulWidget {
  const GalaxyScreen({super.key});

  @override
  State<GalaxyScreen> createState() => _GalaxyScreenState();
}

class _GalaxyScreenState extends State<GalaxyScreen> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 20),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A), // Void (Base)
      body: Stack(
        children: [
          // 1. The Dynamic Galaxy Painter
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _controller,
              builder: (context, child) {
                return CustomPaint(
                  painter: _SectorModelPainter(animationValue: _controller.value),
                );
              },
            ),
          ),
          
          // 2. Center Overlay (Wisdom Core Interaction)
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white.withOpacity(0.9), // Wisdom (White)
                    boxShadow: [
                      BoxShadow(
                        color: Colors.white.withOpacity(0.6),
                        blurRadius: 40,
                        spreadRadius: 10,
                      ),
                      BoxShadow(
                        color: Colors.blue.withOpacity(0.3),
                        blurRadius: 80,
                        spreadRadius: 20,
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Icon(Icons.psychology, size: 40, color: Colors.black87),
                  ),
                ),
                const SizedBox(height: 24),
                // Text is now drawn by painter to avoid rotation issues, 
                // but main title can stay here
              ],
            ),
          ),
          
          // 3. Floating Legend (Optional)
          Positioned(
            bottom: 40,
            left: 20,
            right: 20,
            child: Center(
              child: Text(
                "Sparkle 6+1 知识星域",
                style: TextStyle(
                  color: Colors.white.withOpacity(0.5),
                  fontSize: 14,
                  letterSpacing: 2,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectorModelPainter extends CustomPainter {
  final double animationValue;

  _SectorModelPainter({required this.animationValue});

  // 6+1 Sector Definitions
  static final List<_SectorDef> sectors = [
    _SectorDef(
      id: "COSMOS",
      name: "理性星域",
      color: Color(0xFF00BFFF), // Deep Sky Blue
      icon: Icons.science,
      description: "真理与法则",
    ),
    _SectorDef(
      id: "TECH",
      name: "造物星域",
      color: Color(0xFFC0C0C0), // Silver (Using light grey for visibility)
      icon: Icons.computer,
      description: "创造与工具",
    ),
    _SectorDef(
      id: "ART",
      name: "灵感星域",
      color: Color(0xFFFF00FF), // Magenta
      icon: Icons.palette,
      description: "美与情感",
    ),
    _SectorDef(
      id: "CIVILIZATION",
      name: "文明星域",
      color: Color(0xFFFFD700), // Gold
      icon: Icons.public,
      description: "社会与历史",
    ),
    _SectorDef(
      id: "LIFE",
      name: "生活星域",
      color: Color(0xFF32CD32), // Lime Green
      icon: Icons.favorite,
      description: "生存与肉体",
    ),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) * 0.45;
    
    // 1. Draw Void Background (Stars)
    _drawVoid(canvas, size);

    // 2. Draw Radial Sectors
    final double angleStep = (2 * math.pi) / sectors.length;
    // Rotate slightly slowly
    final double rotationOffset = animationValue * 2 * math.pi * 0.05; 

    for (int i = 0; i < sectors.length; i++) {
      final sector = sectors[i];
      final double startAngle = (i * angleStep) - (math.pi / 2) + rotationOffset;
      
      _drawSector(
        canvas, 
        center, 
        radius, 
        startAngle, 
        angleStep, 
        sector,
      );
    }

    // 3. Draw Wisdom Halo (Static Center)
    _drawWisdomHalo(canvas, center, radius * 0.25);
  }

  void _drawVoid(Canvas canvas, Size size) {
    final paint = Paint();
    final random = math.Random(42); // Deterministic seed

    for (int i = 0; i < 150; i++) {
      final x = random.nextDouble() * size.width;
      final y = random.nextDouble() * size.height;
      final starSize = random.nextDouble() * 2;
      final opacity = random.nextDouble() * 0.5 + 0.1;

      paint.color = Colors.white.withOpacity(opacity);
      canvas.drawCircle(Offset(x, y), starSize, paint);
    }
  }

  void _drawSector(
    Canvas canvas, 
    Offset center, 
    double radius, 
    double startAngle, 
    double sweepAngle, 
    _SectorDef sector
  ) {
    // 1. Sector Background Gradient (Subtle)
    final paint = Paint()
      ..style = PaintingStyle.fill
      ..shader = RadialGradient(
        colors: [
          sector.color.withOpacity(0.05),
          sector.color.withOpacity(0.2),
          Colors.transparent,
        ],
        stops: const [0.0, 0.7, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: radius));

    // Draw a pie slice shape? No, let's draw a "Cloud" or "Nebula" segment
    // For MVP, we use a custom path representing the sector area
    final path = Path();
    path.moveTo(center.dx, center.dy);
    path.lineTo(
      center.dx + radius * math.cos(startAngle),
      center.dy + radius * math.sin(startAngle),
    );
    path.arcTo(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
    );
    path.close();
    canvas.drawPath(path, paint);

    // 3. Draw Sector Label & Icon at the edge
    final midAngle = startAngle + sweepAngle / 2;
    final iconDist = radius * 0.75;
    final iconPos = Offset(
      center.dx + iconDist * math.cos(midAngle),
      center.dy + iconDist * math.sin(midAngle),
    );

    // Glow behind icon
    canvas.drawCircle(
      iconPos, 
      25, 
      Paint()..color = sector.color.withOpacity(0.2)..maskFilter = const MaskFilter.blur(BlurStyle.normal, 10)
    );

    // Draw Icon (Placeholder circle for now, or text)
    final textPainter = TextPainter(
      text: TextSpan(
        children: [
          TextSpan(
            text: "${sector.name}\n",
            style: TextStyle(
              color: sector.color,
              fontWeight: FontWeight.bold,
              fontSize: 14,
              shadows: [Shadow(color: sector.color, blurRadius: 10)],
            ),
          ),
          TextSpan(
            text: sector.id,
            style: TextStyle(
              color: sector.color.withOpacity(0.7),
              fontSize: 10,
              letterSpacing: 1.5,
            ),
          ),
        ],
      ),
      textAlign: TextAlign.center,
      textDirection: TextDirection.ltr,
    );
    
    textPainter.layout();
    
    // Rotate text to be upright? Or radial? 
    // Keeping it upright is more readable.
    textPainter.paint(
      canvas, 
      Offset(iconPos.dx - textPainter.width / 2, iconPos.dy - textPainter.height / 2)
    );
    
    // 4. Draw some "Stars" within this sector
    final random = math.Random(sector.id.hashCode);
    final starPaint = Paint()..color = sector.color;
    
    for(int i=0; i<8; i++) {
        // Random polar coordinates within the sector wedge
        final r = (random.nextDouble() * 0.6 + 0.3) * radius; // 30% to 90% radius
        final a = startAngle + (random.nextDouble() * 0.8 + 0.1) * sweepAngle; // Keep away from edges
        
        final sx = center.dx + r * math.cos(a);
        final sy = center.dy + r * math.sin(a);
        
        canvas.drawCircle(Offset(sx, sy), random.nextDouble() * 3 + 1, starPaint);
        
        // Connect some stars
        if (i > 0 && i % 3 == 0) {
            canvas.drawLine(
                Offset(sx, sy), 
                center, // Just connect to center for simple visual
                Paint()..color = sector.color.withOpacity(0.1)..strokeWidth = 0.5
            );
        }
    }
  }

  void _drawWisdomHalo(Canvas canvas, Offset center, double radius) {
    // Halo Paint
    final paint = Paint()
      ..color = Colors.white.withOpacity(0.1)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 20);
    
    canvas.drawCircle(center, radius, paint);
    
    // Inner Ring
    final ringPaint = Paint()
      ..style = PaintingStyle.stroke
      ..color = Colors.white.withOpacity(0.2)
      ..strokeWidth = 1;
      
    canvas.drawCircle(center, radius * 0.8, ringPaint);
  }

  @override
  bool shouldRepaint(covariant _SectorModelPainter oldDelegate) => true;
}

class _SectorDef {
  final String id;
  final String name;
  final String description;
  final Color color;
  final IconData icon;

  _SectorDef({
    required this.id,
    required this.name,
    required this.description,
    required this.color,
    required this.icon,
  });
}