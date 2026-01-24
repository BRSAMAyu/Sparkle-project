import 'package:flutter/material.dart';

/// Unified animation configuration for statistics module
///
/// All statistics-related animations should use these constants
/// for consistent UX across the app.
class StatisticsAnimationConfig {
  // Private constructor to prevent instantiation
  StatisticsAnimationConfig._();

  // ============================================
  // DURATION CONSTANTS
  // ============================================

  /// Ultra-fast animation (150ms) - for micro-interactions
  static const Duration ultraFast = Duration(milliseconds: 150);

  /// Fast animation (250ms) - for button presses, simple state changes
  static const Duration fast = Duration(milliseconds: 250);

  /// Medium animation (400ms) - default for most transitions
  static const Duration medium = Duration(milliseconds: 400);

  /// Slow animation (600ms) - for complex layout transitions
  static const Duration slow = Duration(milliseconds: 600);

  /// Extra slow animation (800ms) - for initial page load animations
  static const Duration extraSlow = Duration(milliseconds: 800);

  // ============================================
  // CURVE CONSTANTS
  // ============================================

  /// Ease out curve - fast entry, slow exit (default for most animations)
  static const Curve easeOut = Curves.easeOut;

  /// Ease in-out curve - smooth start and end
  static const Curve easeInOut = Curves.easeInOut;

  /// Ease out quart - snappy but smooth
  static const Curve easeOutQuart = Curves.easeOutQuart;

  /// Ease out cubic - natural deceleration
  static const Curve easeOutCubic = Curves.easeOutCubic;

  /// Ease out back - slight overshoot for emphasis
  static const Curve easeOutBack = Curves.easeOutBack;

  /// Bounce - playful bounce effect
  static const Curve bounce = Curves.bounceOut;

  /// Linear - constant speed (for loading indicators)
  static const Curve linear = Curves.linear;

  // ============================================
  // CHART ANIMATION CONFIG
  // ============================================

  /// Duration for chart entrance animation
  static const Duration chartEntrance = Duration(milliseconds: 800);

  /// Duration for chart data update animation
  static const Duration chartUpdate = Duration(milliseconds: 500);

  /// Curve for chart line animation
  static const Curve chartCurve = Curves.easeOutCubic;

  /// Delay before animating each chart element (stagger effect)
  static const Duration chartStaggerDelay = Duration(milliseconds: 50);

  // ============================================
  // CARD ANIMATION CONFIG
  // ============================================

  /// Duration for card entrance animation
  static const Duration cardEntrance = Duration(milliseconds: 400);

  /// Duration for card hover/press effect
  static const Duration cardPress = Duration(milliseconds: 150);

  /// Curve for card scale animation
  static const Curve cardCurve = Curves.easeOutCubic;

  /// Scale factor for card press effect
  static const double cardPressScale = 0.96;

  /// Scale factor for card hover effect
  static const double cardHoverScale = 1.02;

  // ============================================
  // LIST ANIMATION CONFIG
  // ============================================

  /// Duration for list item entrance
  static const Duration listEntrance = Duration(milliseconds: 300);

  /// Duration for list item removal
  static const Duration listRemoval = Duration(milliseconds: 250);

  /// Curve for list animation
  static const Curve listCurve = Curves.easeOut;

  /// Initial offset for list items sliding in
  static const double listSlideOffset = 50.0;

  /// Delay between each list item animation
  static const Duration listStaggerDelay = Duration(milliseconds: 40);

  // ============================================
  // OVERLAY/BOTTOM SHEET CONFIG
  // ============================================

  /// Duration for bottom sheet entrance
  static const Duration bottomSheetEntrance = Duration(milliseconds: 400);

  /// Curve for bottom sheet animation
  static const Curve bottomSheetCurve = Curves.easeOutCubic;

  /// Duration for modal/overlay fade
  static const Duration modalFade = Duration(milliseconds: 250);

  /// Duration for dialog scale animation
  static const Duration dialogScale = Duration(milliseconds: 300);

  // ============================================
  // REFRESH/LOADING CONFIG
  // ============================================

  /// Duration for refresh spinner animation
  static const Duration refreshSpin = Duration(milliseconds: 1000);

  /// Duration for skeleton loader fade
  static const Duration skeletonFade = Duration(milliseconds: 500);

  /// Minimum duration to show loading state
  /// (prevents flicker for very fast operations)
  static const Duration minLoadingDuration = Duration(milliseconds: 500);

  // ============================================
  // PRESET CURVES FOR SPECIFIC USE CASES
  // ============================================

  /// Animation config for chart entrance
  static const ChartAnimationSpec chartEntranceSpec = ChartAnimationSpec(
    duration: chartEntrance,
    curve: chartCurve,
    delay: Duration.zero,
  );

  /// Animation config for chart data update
  static const ChartAnimationSpec chartUpdateSpec = ChartAnimationSpec(
    duration: chartUpdate,
    curve: chartCurve,
    delay: Duration.zero,
  );

  /// Animation config for card entrance
  static const CardAnimationSpec cardEntranceSpec = CardAnimationSpec(
    duration: cardEntrance,
    curve: cardCurve,
    offsetBegin: Offset(0, 20),
  );

  /// Animation config for staggered list items
  static List<ItemAnimationSpec> staggeredListSpec(int count) => List.generate(
      count,
      (index) => ItemAnimationSpec(
        duration: listEntrance,
        curve: listCurve,
        delay: Duration(milliseconds: listStaggerDelay.inMilliseconds * index),
        offsetBegin: Offset(0, listSlideOffset),
      ),
    );
}

/// Specification for chart animations
class ChartAnimationSpec {

  const ChartAnimationSpec({
    required this.duration,
    required this.curve,
    required this.delay,
  });
  final Duration duration;
  final Curve curve;
  final Duration delay;

  /// Reverse animation spec (for exit)
  ChartAnimationSpec reverse() => ChartAnimationSpec(
      duration: duration,
      curve: curve.flipped,
      delay: Duration.zero,
    );
}

/// Specification for card animations
class CardAnimationSpec {

  const CardAnimationSpec({
    required this.duration,
    required this.curve,
    this.scaleBegin = 0.9,
    this.offsetBegin = Offset.zero,
  });
  final Duration duration;
  final Curve curve;
  final double scaleBegin;
  final Offset offsetBegin;
}

/// Specification for list item animations
class ItemAnimationSpec {

  const ItemAnimationSpec({
    required this.duration,
    required this.curve,
    required this.delay,
    this.offsetBegin = Offset.zero,
  });
  final Duration duration;
  final Curve curve;
  final Duration delay;
  final Offset offsetBegin;
}

/// Extension for creating animation controllers with statistics config
extension StatisticsAnimationExtension on AnimationController {
  /// Create a standard fade-in animation
  CurvedAnimation fadeIn({
    Duration? duration,
    Curve curve = StatisticsAnimationConfig.easeOut,
  }) => CurvedAnimation(
      parent: this,
      curve: curve,
    );

  /// Create a standard slide-in animation
  Animation<Offset> slideIn({
    Duration? duration,
    Curve curve = StatisticsAnimationConfig.easeOut,
    Offset begin = const Offset(0, 1),
  }) => Tween<Offset>(begin: begin, end: Offset.zero).animate(
      CurvedAnimation(parent: this, curve: curve),
    );

  /// Create a standard scale-in animation
  Animation<double> scaleIn({
    Duration? duration,
    Curve curve = StatisticsAnimationConfig.easeOutBack,
    double begin = 0.0,
  }) => Tween<double>(begin: begin, end: 1.0).animate(
      CurvedAnimation(parent: this, curve: curve),
    );
}

/// Extension for Curve to get flipped version
extension CurveExtension on Curve {
  Curve get flipped => FlippedCurve(this);
}

/// Flipped curve for reverse animations
class FlippedCurve extends Curve {

  const FlippedCurve(this.curve);
  final Curve curve;

  @override
  double transform(double t) => 1 - curve.transform(1 - t);

  @override
  String toString() => '${curve}.flipped';
}
