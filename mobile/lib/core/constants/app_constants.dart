/// App Constants
class AppConstants {
  // App Info
  static const String appName = 'Sparkle';
  static const String appNameChinese = '星火';
  static const String appVersion = '1.0.0';

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

class AppFeatureFlags {
  static bool enableMemoryPanelV2 = true;
  static bool enableEvidenceViewer = true;
  static bool enableMemoryExplain = true;
  static bool enableMemoryRetraction = true;
  static bool enableMemoryCorrection = true;
  static bool enableUserMemoryControls = true;
  static bool enableWorkingMemoryDrawer = true;
  static bool enableTaskGuidanceV2 = false;

  /// V4-F05：像素候选主题 preview 通道入口（「我的」页开发者入口）。
  /// 设计未批准（TOKENS.proposal.json status=PROPOSED_NOT_APPROVED），
  /// 默认关闭——preview 不隐性全量上线；批准转正时随决策改开。
  static bool enableStylePreview = false;
  static bool enableStage35ProfileCards = const bool.fromEnvironment(
    'mobile.stage35_cards_enabled',
    defaultValue: true,
  );
}
