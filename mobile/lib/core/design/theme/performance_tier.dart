import 'dart:math' as math;
import 'dart:ui';

/// Global performance tier for visual effects and motion.
///
/// UI must read this from theme/context; do not infer per-widget.
enum PerformanceTier {
  ultra,
  high,
  medium,
  low,
}

enum MotionIntensityLevel {
  ultra,
  high,
  medium,
  off,
}

extension MotionIntensityLevelX on MotionIntensityLevel {
  String get storageValue => name;
}

/// Single decision point for performance tier defaults.
PerformanceTier defaultPerformanceTier() {
  try {
    final view = PlatformDispatcher.instance.views.first;
    final refreshRate = view.display.refreshRate;
    final dpr = view.devicePixelRatio;
    final shortestSide =
        math.min(view.physicalSize.width, view.physicalSize.height) / dpr;

    if (refreshRate >= 110 && dpr <= 3.2) {
      return PerformanceTier.ultra;
    }

    // Very constrained devices: low refresh + high DPR + small screen (e.g. iPhone SE 1st gen)
    if (refreshRate <= 60 && dpr >= 3.5 && shortestSide < 375) {
      return PerformanceTier.low;
    }

    if (refreshRate <= 60 && (dpr >= 3.0 || shortestSide < 390)) {
      return PerformanceTier.medium;
    }

    return PerformanceTier.high;
  } catch (_) {
    return PerformanceTier.high;
  }
}
