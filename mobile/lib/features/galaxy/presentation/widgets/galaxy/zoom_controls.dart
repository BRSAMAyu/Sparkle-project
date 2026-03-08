import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class ZoomControls extends StatefulWidget {
  const ZoomControls({
    required this.transformationController,
    required this.viewportSize,
    super.key,
    this.minScale = 0.1,
    this.maxScale = 5.0,
    this.sliderHeight = 150,
  });
  final TransformationController transformationController;
  final Size viewportSize;
  final double minScale;
  final double maxScale;
  final double sliderHeight;

  @override
  State<ZoomControls> createState() => _ZoomControlsState();
}

class _ZoomControlsState extends State<ZoomControls>
    with TickerProviderStateMixin {
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

  void _onSliderChanged(double value) {
    setState(() {
      _currentScale = _sliderValueToScale(value);
    });
  }

  void _onSliderChangeEnd(double value) {
    final scale = _sliderValueToScale(value);
    _zoomToCenter(scale);
  }

  double _scaleToSliderValue(double scale) {
    final minLog = math.log(widget.minScale);
    final maxLog = math.log(widget.maxScale);
    final currentLog = math.log(scale.clamp(widget.minScale, widget.maxScale));
    return ((currentLog - minLog) / (maxLog - minLog)).clamp(0.0, 1.0);
  }

  double _sliderValueToScale(double sliderValue) {
    final minLog = math.log(widget.minScale);
    final maxLog = math.log(widget.maxScale);
    final nextLog = minLog + (maxLog - minLog) * sliderValue.clamp(0.0, 1.0);
    return math.exp(nextLog);
  }

  void _zoomToCenter(double targetScale) {
    final center = Offset(
      widget.viewportSize.width / 2,
      widget.viewportSize.height / 2,
    );

    final currentMatrix = widget.transformationController.value;
    final currentScale = currentMatrix.getMaxScaleOnAxis();

    final scaleRatio = targetScale / currentScale;

    // Translate to center, scale, translate back
    // NewMatrix = Translate(C) * Scale(ratio) * Translate(-C) * OldMatrix

    // Create new matrix using matrix multiplication
    // Equivalent to: Translate(C) * Scale(ratio) * Translate(-C) * currentMatrix
    final t1 = Matrix4.translationValues(center.dx, center.dy, 0);
    final s = Matrix4.diagonal3Values(scaleRatio, scaleRatio, 1);
    final t2 = Matrix4.translationValues(-center.dx, -center.dy, 0);

    // Use explicit casting to avoid dynamic type issues
    final newMatrix = (t1 * s * t2 * currentMatrix) as Matrix4;

    // Use smooth animation with AnimationController
    final animationController = AnimationController(
      duration: const Duration(milliseconds: 220),
      vsync: this,
    );

    final tween = Tween<Matrix4>(
      begin: currentMatrix,
      end: newMatrix,
    );
    final animation = tween.animate(
      CurvedAnimation(
        parent: animationController,
        curve: Curves.easeInOut,
      ),
    );

    animation.addListener(() {
      widget.transformationController.value = animation.value;
    });

    unawaited(
      animationController.forward().then(
        (_) {
          animationController.dispose();
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
      decoration: BoxDecoration(
        color: isDark
            ? DS.surfaceHigh.withValues(alpha: 0.7)
            : DS.surfacePrimary.withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: isDark ? DS.neutral700 : DS.neutral300,
        ),
        boxShadow: [
          BoxShadow(
            color: DS.overlay30.withValues(alpha: 0.2),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Tooltip(
            message: 'Zoom In',
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              size: 36,
              icon: Icon(Icons.add, color: DS.brandPrimary),
              onPressed: () => _updateZoom(_currentScale * 1.2),
            ),
          ),
          SizedBox(
            height: widget.sliderHeight,
            child: RotatedBox(
              quarterTurns: 3,
              child: SliderTheme(
                data: SliderThemeData(
                  trackHeight: 2,
                  activeTrackColor: DS.brandPrimary,
                  inactiveTrackColor: isDark ? DS.neutral700 : DS.neutral300,
                  thumbColor: DS.brandPrimary,
                  overlayColor: DS.brandPrimary.withValues(alpha: 0.2),
                  thumbShape:
                      const RoundSliderThumbShape(enabledThumbRadius: 6),
                  overlayShape:
                      const RoundSliderOverlayShape(overlayRadius: 12),
                ),
                child: Slider(
                  value: _scaleToSliderValue(_currentScale),
                  min: 0,
                  max: 1,
                  onChanged: _onSliderChanged,
                  onChangeEnd: _onSliderChangeEnd,
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Text(
              '${(_currentScale * 100).round()}%',
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Tooltip(
            message: 'Zoom Out',
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              size: 36,
              icon: Icon(Icons.remove, color: DS.brandPrimary),
              onPressed: () => _updateZoom(_currentScale / 1.2),
            ),
          ),
        ],
      ),
    );
  }
}
