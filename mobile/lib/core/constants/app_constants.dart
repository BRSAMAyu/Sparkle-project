/// App Constants
class AppConstants {
  // App Info
  static const String appName = 'Sparkle';
  static const String appNameChinese = '星火';
  static const String appVersion = '0.1.0';

  // Storage Keys
  static const String keyAccessToken = 'access_token';
  static const String keyRefreshToken = 'refresh_token';
  static const String keyUserId = 'user_id';
  static const String keyUserData = 'user_data';
  static const String keyThemeMode = 'theme_mode';

  // Flame Levels
  static const int maxFlameLevel = 10;
  static const double minFlameBrightness = 0.0;
  static const double maxFlameBrightness = 1.0;

  // Task Settings
  static const int defaultPomodoroMinutes = 25;
  static const int defaultBreakMinutes = 5;
  static const int maxTaskDifficulty = 5;
  static const int maxEnergyCost = 5;

  // Preferences
  static const double defaultDepthPreference = 0.5;
  static const double defaultCuriosityPreference = 0.5;
}
