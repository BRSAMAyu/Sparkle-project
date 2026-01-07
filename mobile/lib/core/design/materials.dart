import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
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
    this.noiseOpacity = 0.0,
    this.noiseBlendMode = BlendMode.overlay,
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
  
  /// Opacity of the noise texture overlay (0.0 - 1.0)
  /// Use 0.0 for text containers to ensure readability.
  final double noiseOpacity;
  final BlendMode noiseBlendMode;
  
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
    double? noiseOpacity,
    BlendMode? noiseBlendMode,
    double? blurSigma,
    Color? rimLightColor,
    Color? glowColor,
    List<BoxShadow>? shadows,
    Gradient? borderGradient,
    Color? borderColor,
    double? borderWidth,
  }) {
    return SparkleMaterial(
      backgroundGradient: backgroundGradient ?? this.backgroundGradient,
      backgroundColor: backgroundColor ?? this.backgroundColor,
      opacity: opacity ?? this.opacity,
      noiseOpacity: noiseOpacity ?? this.noiseOpacity,
      noiseBlendMode: noiseBlendMode ?? this.noiseBlendMode,
      blurSigma: blurSigma ?? this.blurSigma,
      rimLightColor: rimLightColor ?? this.rimLightColor,
      glowColor: glowColor ?? this.glowColor,
      shadows: shadows ?? this.shadows,
      borderGradient: borderGradient ?? this.borderGradient,
      borderColor: borderColor ?? this.borderColor,
      borderWidth: borderWidth ?? this.borderWidth,
    );
  }
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
      blurSigma: enableBlur ? 16.0 : 0.0,
      noiseOpacity: (enableNoise && isDark) ? 0.03 : (enableNoise ? 0.05 : 0.0),
      noiseBlendMode: BlendMode.overlay,
      backgroundGradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: isDark 
            ? [Colors.white.withValues(alpha: 0.05), Colors.white.withValues(alpha: 0.02)]
            : [Colors.white.withValues(alpha: 0.6), Colors.white.withValues(alpha: 0.3)],
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
      blurSigma: 0.0,
      noiseOpacity: 0.0, // Clean, glossy look
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
      blurSigma: 0.0,
      noiseOpacity: 0.0,
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
    super.key,
    required this.material,
    required this.child,
    this.shape = BoxShape.rectangle,
    this.borderRadius,
    this.padding,
  });

  final SparkleMaterial material;
  final Widget child;
  final BoxShape shape;
  final BorderRadiusGeometry? borderRadius;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    // Determine the border radius to use for clipping
    final BorderRadius resolvedRadius = borderRadius is BorderRadius 
        ? borderRadius as BorderRadius 
        : (shape == BoxShape.circle 
            ? BorderRadius.circular(1000) 
            : BorderRadius.zero);

    return Container(
      // Shadow layer: Rendered outside the clip
      decoration: BoxDecoration(
        shape: shape,
        borderRadius: shape == BoxShape.rectangle ? borderRadius : null,
        boxShadow: material.shadows,
      ),
      child: ClipRRect(
        borderRadius: resolvedRadius,
        child: Stack(
          children: [
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

            // Layer 1: Background (Color / Gradient)
            Positioned.fill(
              child: Container(
                decoration: BoxDecoration(
                  color: material.backgroundColor,
                  gradient: material.backgroundGradient,
                  shape: shape,
                ),
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
                      color: material.noiseBlendMode == BlendMode.dst ? null : Colors.white, // Hint for some blend modes
                      colorBlendMode: material.noiseBlendMode,
                    ),
                  ),
                ),
              ),

            // Layer 4: Inner Glow (Emphasis)
            if (material.glowColor != null)
              Positioned.fill(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    shape: shape,
                    gradient: RadialGradient(
                      center: Alignment.center,
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

            // Layer 5: Content
            Padding(
              padding: padding ?? EdgeInsets.zero,
              child: child,
            ),

            // Layer 6: Rim Light & Border
            Positioned.fill(
              child: IgnorePointer(
                child: CustomPaint(
                  painter: _MaterialHighlightPainter(
                    rimColor: material.rimLightColor,
                    borderColor: material.borderColor,
                    borderWidth: material.borderWidth,
                    borderRadius: resolvedRadius,
                    shape: shape,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MaterialHighlightPainter extends CustomPainter {
  _MaterialHighlightPainter({
    this.rimColor,
    this.borderColor,
    this.borderWidth = 0.0,
    this.borderRadius,
    this.shape = BoxShape.rectangle,
  });

  final Color? rimColor;
  final Color? borderColor;
  final double borderWidth;
  final BorderRadius? borderRadius;
  final BoxShape shape;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(0, 0, size.width, size.height);
    final RRect rrect = (borderRadius ?? BorderRadius.zero).toRRect(rect);

    // 1. Draw Border (if any)
    if (borderColor != null && borderWidth > 0) {
      final borderPaint = Paint()
        ..color = borderColor!
        ..style = PaintingStyle.stroke
        ..strokeWidth = borderWidth;
      
      if (shape == BoxShape.circle) {
         canvas.drawCircle(rect.center, size.width / 2, borderPaint);
      } else {
         canvas.drawRRect(rrect, borderPaint);
      }
    }

    // 2. Draw Rim Light (Top Edge)
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

      if (shape == BoxShape.circle) {
        canvas.drawCircle(rect.center, size.width / 2, rimPaint);
      } else {
        // We trim the path to only show top part effectively via gradient, 
        // but drawing the full RRect with top-down gradient works well for Rim Light.
        canvas.drawRRect(rrect.deflate(0.5), rimPaint); 
      }
    }
  }

  @override
  bool shouldRepaint(covariant _MaterialHighlightPainter oldDelegate) {
    return oldDelegate.rimColor != rimColor ||
        oldDelegate.borderColor != borderColor ||
        oldDelegate.borderWidth != borderWidth ||
        oldDelegate.borderRadius != borderRadius;
  }
}