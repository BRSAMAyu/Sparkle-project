/// Centralized responsive breakpoints.
///
/// These values are the single source of truth for layout decisions.
class Breakpoints {
  const Breakpoints._();

  /// Phone-specific guidance breakpoints.
  static const double narrow = 360.0;
  static const double standard = 390.0;
  static const double wide = 428.0;
}

/// Layout breakpoints for multi-device layouts.
class LayoutBreakpoints {
  const LayoutBreakpoints._();

  /// Tablet starts here.
  static const double tablet = 768.0;

  /// Desktop layouts start here.
  ///
  /// Set to 1200 to avoid classifying 1024px tablets (e.g. iPad Pro 12.9")
  /// as desktop.
  static const double desktop = 1200.0;

  /// Very wide displays start here.
  static const double wideDesktop = 1440.0;
}
