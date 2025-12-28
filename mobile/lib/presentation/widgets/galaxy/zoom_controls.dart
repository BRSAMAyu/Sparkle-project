import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class ZoomControls extends StatefulWidget {

  const ZoomControls({
    required this.transformationController, super.key,
    this.minScale = 0.1,
    this.maxScale = 3.0,
  });
  final TransformationController transformationController;
  final double minScale;
  final double maxScale;

  @override
  State<ZoomControls> createState() => _ZoomControlsState();
}

class _ZoomControlsState extends State<ZoomControls> {
  double _currentScale = 1.0;

  @override
  void initState() {
    super.initState();
    widget.transformationController.addListener(_onTransformChanged);
    _currentScale = widget.transformationController.value.getMaxScaleOnAxis();
  }

  @override
  void dispose() {
    widget.transformationController.removeListener(_onTransformChanged);
    super.dispose();
  }

  void _onTransformChanged() {
    final scale = widget.transformationController.value.getMaxScaleOnAxis();
    if ((scale - _currentScale).abs() > 0.01) {
      setState(() {
        _currentScale = scale;
      });
    }
  }

  void _updateZoom(double newScale) {
    final scale = newScale.clamp(widget.minScale, widget.maxScale);
    _zoomToCenter(scale);
  }

  void _zoomToCenter(double targetScale) {
    // This requires knowing the screen size to find the center.
    // Since we are in a small widget, we can use MediaQuery.
    final screenSize = MediaQuery.of(context).size;
    final center = Offset(screenSize.width / 2, screenSize.height / 2);
    
    final currentMatrix = widget.transformationController.value;
    final currentScale = currentMatrix.getMaxScaleOnAxis();
    
    final scaleRatio = targetScale / currentScale;
    
    // Translate to center, scale, translate back
    // NewMatrix = Translate(C) * Scale(ratio) * Translate(-C) * OldMatrix
    
    final t1 = Matrix4.translationValues(center.dx, center.dy, 0);
    final s = Matrix4.diagonal3Values(scaleRatio, scaleRatio, 1);
    final t2 = Matrix4.translationValues(-center.dx, -center.dy, 0);
    
    // Matrix multiplication order is important: T1 * S * T2 * current
    final newMatrix = t1 * s * t2 * currentMatrix;
      
    widget.transformationController.value = newMatrix;
  }

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: DS.brandPrimary24),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            icon: const Icon(Icons.add, color: DS.brandPrimary),
            onPressed: () => _updateZoom(_currentScale * 1.2),
            tooltip: 'Zoom In',
          ),
          SizedBox(
            height: 150,
            child: RotatedBox(
              quarterTurns: 3,
              child: SliderTheme(
                data: const SliderThemeData(
                  trackHeight: 2,
                  activeTrackColor: DS.brandPrimary,
                  inactiveTrackColor: DS.brandPrimary24,
                  thumbColor: DS.brandPrimary,
                  thumbShape: RoundSliderThumbShape(enabledThumbRadius: 6),
                  overlayShape: RoundSliderOverlayShape(overlayRadius: 12),
                ),
                child: Slider(
                  value: _currentScale.clamp(widget.minScale, widget.maxScale),
                  min: widget.minScale,
                  max: widget.maxScale,
                  onChanged: _updateZoom,
                ),
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.remove, color: DS.brandPrimary),
            onPressed: () => _updateZoom(_currentScale / 1.2),
            tooltip: 'Zoom Out',
          ),
        ],
      ),
    );
}
