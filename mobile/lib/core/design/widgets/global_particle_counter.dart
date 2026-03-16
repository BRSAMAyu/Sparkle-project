import 'dart:math' as math;

/// Global particle budget guard for animated visual effects.
class GlobalParticleCounter {
  GlobalParticleCounter._();

  static int currentCount = 0;
  static const int maxParticles = 80;

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

  static bool get isOverLimit => currentCount > maxParticles;
}
