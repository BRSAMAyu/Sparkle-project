import 'dart:math' as math;
import 'dart:ui' as ui;

/// Global particle budget guard for animated visual effects.
class GlobalParticleCounter {
  GlobalParticleCounter._();

  static int currentCount = 0;
  static const int _defaultMaxParticles = 80;

  static int get maxParticles {
    final dispatcher = ui.PlatformDispatcher.instance;
    final view = dispatcher.views.isNotEmpty ? dispatcher.views.first : null;
    final reduceMotion = dispatcher.accessibilityFeatures.disableAnimations ||
        dispatcher.accessibilityFeatures.accessibleNavigation;
    if (reduceMotion) {
      return 0;
    }
    if (view == null) {
      return _defaultMaxParticles;
    }
    final logicalShortestSide =
        view.physicalSize.shortestSide / view.devicePixelRatio;
    if (logicalShortestSide < 380) {
      return 48;
    }
    if (logicalShortestSide < 430) {
      return 64;
    }
    return _defaultMaxParticles;
  }

  static bool canAddParticles(int count) =>
      currentCount + count <= maxParticles;

  static bool tryAddParticles(int count) {
    if (count <= 0) return true;
    if (!canAddParticles(count)) return false;
    currentCount += count;
    return true;
  }

  static void releaseParticles(int count) {
    if (count <= 0) return;
    currentCount = math.max(0, currentCount - count);
  }

  static bool get isOverLimit => currentCount >= maxParticles;
}
