import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/services/performance_service.dart';

/// ---------------------------------------------------------------------------
/// 1. THE RECIPE (Pure Data)
/// ---------------------------------------------------------------------------

/// Defines the physical properties of a material.
/// This decouples the "look" from the rendering logic.
@immutable
class SparkleMaterial {
  const SparkleMaterial({
    this.backgroundGradient,
    this.backgroundColor,
    this.opacity = 1.0,
    this.blendMode,
    this.noiseOpacity = 0.0,
    this.noiseBlendMode = BlendMode.overlay,
    this.noiseColor,
    this.blurSigma = 0.0,
    this.rimLightColor,
    this.glowColor,
    this.shadows,
    this.borderGradient,
    this.borderColor,
    this.borderWidth = 0.0,
  });

  final Gradient? backgroundGradient;
  final Color? backgroundColor;
  final double opacity;
  final BlendMode? blendMode;
  
  /// Opacity of the noise texture overlay (0.0 - 1.0)
  /// Use 0.0 for text containers to ensure readability.
  final double noiseOpacity;
  final BlendMode noiseBlendMode;
  final Color? noiseColor;
  
  /// Backdrop filter blur sigma.
  final double blurSigma;
  
  /// Top-edge highlight color (simulates light from top).
  final Color? rimLightColor;
  
  /// Inner ambient glow color.
  final Color? glowColor;
  
  /// Elevation shadows.
  final List<BoxShadow>? shadows;
  
  /// Optional gradient border.
  final Gradient? borderGradient;
  
  /// Fallback solid border color.
  final Color? borderColor;
  
  final double borderWidth;

  SparkleMaterial copyWith({
    Gradient? backgroundGradient,
    Color? backgroundColor,
    double? opacity,
    BlendMode? blendMode,
    double? noiseOpacity,
    BlendMode? noiseBlendMode,
    Color? noiseColor,
    double? blurSigma,
    Color? rimLightColor,
    Color? glowColor,
    List<BoxShadow>? shadows,
    Gradient? borderGradient,
    Color? borderColor,
    double? borderWidth,
  }) => SparkleMaterial(
      backgroundGradient: backgroundGradient ?? this.backgroundGradient,
      backgroundColor: backgroundColor ?? this.backgroundColor,
      opacity: opacity ?? this.opacity,
      blendMode: blendMode ?? this.blendMode,
      noiseOpacity: noiseOpacity ?? this.noiseOpacity,
      noiseBlendMode: noiseBlendMode ?? this.noiseBlendMode,
      noiseColor: noiseColor ?? this.noiseColor,
      blurSigma: blurSigma ?? this.blurSigma,
      rimLightColor: rimLightColor ?? this.rimLightColor,
      glowColor: glowColor ?? this.glowColor,
      shadows: shadows ?? this.shadows,
      borderGradient: borderGradient ?? this.borderGradient,
      borderColor: borderColor ?? this.borderColor,
      borderWidth: borderWidth ?? this.borderWidth,
    );
}

/// ---------------------------------------------------------------------------
/// 2. THE PRESETS (Catalog)
/// ---------------------------------------------------------------------------

/// Standard material presets for the Luminous Cognition design system.
class AppMaterials {
  AppMaterials._();

  /// **NeoGlass** (The Hero Material)
  /// Used for: CuriosityCapsule, FocusCard, OmniBar.
  /// Features: Frosted glass, subtle noise, rim light.
  static SparkleMaterial get neoGlass {
    final colors = ThemeManager().current.colors;
    final isDark = colors.brightness == Brightness.dark;
    
    // Performance degradation
    final enableBlur = PerformanceService.instance.enableBlur;
    final enableNoise = PerformanceService.instance.currentTier.value == PerformanceTier.ultra;

    return SparkleMaterial(
      blurSigma: enableBlur ? 15.0 : 0.0,
      noiseOpacity: (enableNoise && isDark) ? 0.03 : (enableNoise ? 0.05 : 0.0),
      noiseColor: colors.noiseColor,
      backgroundGradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: isDark
            ? [Colors.white.withValues(alpha: 0.05), Colors.white.withValues(alpha: 0.02)]
            : [Colors.white.withValues(alpha: 0.05), Colors.white.withValues(alpha: 0.15)],
      ),
      rimLightColor: colors.rimLight,
      borderWidth: 1.0,
      borderColor: colors.surfaceTertiary.withValues(alpha: 0.3),
      shadows: ThemeManager().current.shadows.medium,
    );
  }

  /// **Obsidian** (Dark Mode Emphasis)
  /// Used for: Primary Action Buttons, Active States in Dark Mode.
  /// Features: Deep, glossy, volcanic glass look.
  static SparkleMaterial get obsidian {
    final colors = ThemeManager().current.colors;
    final isDark = colors.brightness == Brightness.dark;

    if (!isDark) {
      // Fallback for light mode if obsidian is requested (usually mapped to ceramic or high contrast)
      return neoGlass.copyWith(
        backgroundColor: colors.brandPrimary.withValues(alpha: 0.1),
        rimLightColor: colors.brandPrimary.withValues(alpha: 0.5),
      );
    }

    return SparkleMaterial(
      backgroundColor: Colors.black.withValues(alpha: 0.6),
      rimLightColor: colors.brandPrimary.withValues(alpha: 0.4),
      glowColor: colors.brandPrimary.withValues(alpha: 0.1),
      shadows: ThemeManager().current.shadows.large,
      borderWidth: 1.0,
      borderColor: colors.brandPrimary.withValues(alpha: 0.3),
    );
  }

  /// **Ceramic** (Light Mode Standard)
  /// Used for: Standard Cards, Bento Grid items.
  /// Features: Matte, opaque, tactile, soft shadows.
  static SparkleMaterial get ceramic {
    final colors = ThemeManager().current.colors;
    return SparkleMaterial(
      backgroundColor: colors.surfaceSecondary,
      shadows: ThemeManager().current.shadows.small,
      borderColor: colors.surfaceTertiary.withValues(alpha: 0.5),
      borderWidth: 0.5,
    );
  }
}

/// ---------------------------------------------------------------------------
/// 3. THE RENDERER (Styler Widget)
/// ---------------------------------------------------------------------------

class MaterialStyler extends StatelessWidget {
  const MaterialStyler({
    required this.material, required this.child, super.key,
    this.shape = BoxShape.rectangle,
    this.shapeBorder,
    this.borderRadius,
    this.padding,
  });

  final SparkleMaterial material;
  final Widget child;
  final BoxShape shape;
  final ShapeBorder? shapeBorder;
  final BorderRadiusGeometry? borderRadius;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    // Determine the border radius to use for clipping when no ShapeBorder is provided.
    final resolvedRadius = borderRadius is BorderRadius
        ? borderRadius as BorderRadius
        : (shape == BoxShape.circle
            ? BorderRadius.circular(1000)
            : BorderRadius.zero);

    final clipRadius = shapeBorder == null ? resolvedRadius : BorderRadius.zero;

    return DecoratedBox(
      // Shadow layer: Rendered outside the clip
      decoration: BoxDecoration(
        shape: shape,
        borderRadius: shape == BoxShape.rectangle ? borderRadius : null,
        boxShadow: material.shadows,
      ),
      child: ClipPath(
        clipper: shapeBorder != null ? ShapeBorderClipper(shape: shapeBorder!) : null,
        child: ClipRRect(
          borderRadius: clipRadius,
          child: Stack(
            children: [
              // Layer 1: Background (Color / Gradient)
              Positioned.fill(
                child: _MaterialBackground(
                  material: material,
                  shape: shape,
                ),
              ),

              // Layer 2: Backdrop Blur
              if (material.blurSigma > 0.0)
                Positioned.fill(
                  child: BackdropFilter(
                    filter: ui.ImageFilter.blur(
                      sigmaX: material.blurSigma,
                      sigmaY: material.blurSigma,
                    ),
                    child: Container(color: Colors.transparent),
                  ),
                ),

              // Layer 3: Noise Overlay
              if (material.noiseOpacity > 0.0)
                Positioned.fill(
                  child: IgnorePointer(
                    child: Opacity(
                      opacity: material.noiseOpacity,
                      child: Image.asset(
                        'assets/images/noise_texture.png',
                        fit: BoxFit.cover,
                        repeat: ImageRepeat.repeat,
                        gaplessPlayback: true,
                        color: material.noiseColor,
                        colorBlendMode: material.noiseBlendMode,
                      ),
                    ),
                  ),
                ),

              // Layer 4: Rim Light
              if (material.rimLightColor != null)
                Positioned.fill(
                  child: IgnorePointer(
                    child: CustomPaint(
                      painter: _MaterialRimPainter(
                        rimColor: material.rimLightColor,
                        borderRadius: resolvedRadius,
                        shape: shape,
                        shapeBorder: shapeBorder,
                      ),
                    ),
                  ),
                ),

              // Layer 5: Inner Glow (Emphasis)
              if (material.glowColor != null)
                Positioned.fill(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      shape: shape,
                      gradient: RadialGradient(
                        radius: 1.5,
                        colors: [
                           Colors.transparent,
                           material.glowColor!,
                        ],
                        stops: const [0.6, 1.0],
                      ),
                    ),
                  ),
                ),

              // Layer 6: Content
              Padding(
                padding: padding ?? EdgeInsets.zero,
                child: child,
              ),

              // Layer 7: Border
              if (material.borderWidth > 0 &&
                  (material.borderColor != null || material.borderGradient != null))
                Positioned.fill(
                  child: IgnorePointer(
                    child: CustomPaint(
                      painter: _MaterialBorderPainter(
                        borderColor: material.borderColor,
                        borderGradient: material.borderGradient,
                        borderWidth: material.borderWidth,
                        borderRadius: resolvedRadius,
                        shape: shape,
                        shapeBorder: shapeBorder,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MaterialBackground extends StatelessWidget {
  const _MaterialBackground({
    required this.material,
    required this.shape,
  });

  final SparkleMaterial material;
  final BoxShape shape;

  @override
  Widget build(BuildContext context) {
    Widget content = Container(
      decoration: BoxDecoration(
        color: material.backgroundColor,
        gradient: material.backgroundGradient,
        shape: shape,
      ),
    );

    if (material.opacity < 1.0) {
      content = Opacity(opacity: material.opacity, child: content);
    }

    if (material.blendMode != null) {
      content = ColorFiltered(
        colorFilter: ColorFilter.mode(
          Colors.white,
          material.blendMode!,
        ),
        child: content,
      );
    }

    return content;
  }
}

class _MaterialRimPainter extends CustomPainter {
  _MaterialRimPainter({
    this.rimColor,
    this.borderRadius,
    this.shape = BoxShape.rectangle,
    this.shapeBorder,
  });

  final Color? rimColor;
  final BorderRadius? borderRadius;
  final BoxShape shape;
  final ShapeBorder? shapeBorder;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(0, 0, size.width, size.height);
    final rrect = (borderRadius ?? BorderRadius.zero).toRRect(rect);
    final borderPath =
        shapeBorder?.getOuterPath(rect);

    // Draw Rim Light (Top Edge)
    if (rimColor != null) {
      final rimPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.0 // Fine hairline
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            rimColor!,
            rimColor!.withValues(alpha: 0.0),
          ],
          stops: const [0.0, 0.4], // Fade out quickly
        ).createShader(rect);

      if (borderPath != null) {
        canvas.drawPath(borderPath, rimPaint);
      } else if (shape == BoxShape.circle) {
        canvas.drawCircle(rect.center, size.width / 2, rimPaint);
      } else {
        // We trim the path to only show top part effectively via gradient,
        // but drawing the full RRect with top-down gradient works well for Rim Light.
        canvas.drawRRect(rrect.deflate(0.5), rimPaint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _MaterialRimPainter oldDelegate) => oldDelegate.rimColor != rimColor ||
        oldDelegate.borderRadius != borderRadius ||
        oldDelegate.shapeBorder != shapeBorder;
}

class _MaterialBorderPainter extends CustomPainter {
  _MaterialBorderPainter({
    this.borderColor,
    this.borderGradient,
    this.borderWidth = 0.0,
    this.borderRadius,
    this.shape = BoxShape.rectangle,
    this.shapeBorder,
  });

  final Color? borderColor;
  final Gradient? borderGradient;
  final double borderWidth;
  final BorderRadius? borderRadius;
  final BoxShape shape;
  final ShapeBorder? shapeBorder;

  @override
  void paint(Canvas canvas, Size size) {
    if (borderWidth <= 0) return;
    if (borderColor == null && borderGradient == null) return;

    final rect = Rect.fromLTWH(0, 0, size.width, size.height);
    final rrect = (borderRadius ?? BorderRadius.zero).toRRect(rect);
    final borderPath =
        shapeBorder?.getOuterPath(rect);

    final borderPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = borderWidth;

    if (borderGradient != null) {
      borderPaint.shader = borderGradient!.createShader(rect);
    } else if (borderColor != null) {
      borderPaint.color = borderColor!;
    }

    if (borderPath != null) {
      canvas.drawPath(borderPath, borderPaint);
    } else if (shape == BoxShape.circle) {
      canvas.drawCircle(rect.center, size.width / 2, borderPaint);
    } else {
      canvas.drawRRect(rrect, borderPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _MaterialBorderPainter oldDelegate) => oldDelegate.borderColor != borderColor ||
        oldDelegate.borderGradient != borderGradient ||
        oldDelegate.borderWidth != borderWidth ||
        oldDelegate.borderRadius != borderRadius ||
        oldDelegate.shape != shape ||
        oldDelegate.shapeBorder != shapeBorder;
}
