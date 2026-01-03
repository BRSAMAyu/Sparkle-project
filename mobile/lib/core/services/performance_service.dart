/// Service to manage app performance settings
class PerformanceService {
  // Can be toggled by user in settings
  static bool isLowPowerMode = false;

  // Configuration for Focus Mode
  static int get focusStarCount => isLowPowerMode ? 30 : 120;
  static bool get enableFocusTwinkle => !isLowPowerMode;
  
  // Configuration for Particles (Cognitive Prism)
  static int get prismParticleCount => isLowPowerMode ? 5 : 20;
}
