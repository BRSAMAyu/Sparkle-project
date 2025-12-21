import 'package:flutter/material.dart';

class BonfireWidget extends StatelessWidget {
  final int level; // 1-5
  final double size;

  const BonfireWidget({
    super.key, 
    required this.level,
    this.size = 100,
  });

  @override
  Widget build(BuildContext context) {
    // Placeholder visualization: A fire icon that grows/changes color with level
    Color fireColor;
    double iconSize = size;

    if (level >= 5) {
      fireColor = Colors.purple;
      iconSize = size * 1.2;
    } else if (level >= 4) {
      fireColor = Colors.red;
      iconSize = size * 1.1;
    } else if (level >= 3) {
      fireColor = Colors.deepOrange;
    } else if (level >= 2) {
      fireColor = Colors.orange;
      iconSize = size * 0.9;
    } else {
      fireColor = Colors.yellow.shade700;
      iconSize = size * 0.8;
    }

    return Container(
      width: size * 1.5,
      height: size * 1.5,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            fireColor.withOpacity(0.2),
            Colors.transparent,
          ],
        ),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Icon(Icons.local_fire_department, size: iconSize, color: fireColor),
          Positioned(
            bottom: 0,
            child: Text(
              'Lv.$level',
              style: TextStyle(
                color: fireColor,
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
