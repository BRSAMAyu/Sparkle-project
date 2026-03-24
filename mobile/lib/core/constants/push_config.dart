/// Push notification configuration constants
///
/// Contains configuration for FCM, JPush, and local notifications.
class PushConfig {
  PushConfig._();

  // ===========================================================================
  // Build Configuration
  // ===========================================================================

  /// Whether to enable Google services (Firebase, Google Sign-In)
  ///
  /// Set to false for China-only builds to avoid Google dependency issues.
  /// Usage: flutter build --dart-define=ENABLE_GOOGLE_SERVICES=false
  static const bool enableGoogleServices = bool.fromEnvironment(
    'ENABLE_GOOGLE_SERVICES',
    defaultValue: true,
  );

  // ===========================================================================
  // JPush Configuration
  // ===========================================================================

  /// JPush App Key (should be replaced with actual value in production)
  static const String jpushAppKey = String.fromEnvironment(
    'JPUSH_APP_KEY',
    defaultValue: 'YOUR_JPUSH_APPKEY',
  );

  /// JPush Channel for statistics
  static const String jpushChannel = 'developer-default';

  /// Whether JPush is enabled
  static const bool jpushEnabled = bool.fromEnvironment(
    'JPUSH_ENABLED',
    defaultValue: true,
  );

  // ===========================================================================
  // FCM Configuration
  // ===========================================================================

  /// Whether FCM is enabled
  ///
  /// Note: This is additionally gated by [enableGoogleServices].
  /// If enableGoogleServices is false, FCM will be disabled regardless.
  static const bool fcmEnabled = bool.fromEnvironment(
    'FCM_ENABLED',
    defaultValue: true,
  );

  /// Effective FCM enabled status (considers both flags)
  static bool get fcmEffectiveEnabled => enableGoogleServices && fcmEnabled;

  // ===========================================================================
  // Local Notification Configuration
  // ===========================================================================

  /// Default notification channel ID for Android
  static const String defaultChannelId = 'sparkle_smart_push';

  /// Default notification channel name for Android
  static const String defaultChannelName = 'Sparkle Notifications';

  /// Default notification channel description for Android
  static const String defaultChannelDescription =
      'Receive important updates and reminders from Sparkle';

  /// High priority notification channel ID
  static const String highPriorityChannelId = 'sparkle_urgent';

  /// High priority notification channel name
  static const String highPriorityChannelName = 'Urgent Notifications';

  // ===========================================================================
  // Region Detection
  // ===========================================================================

  /// Regions where JPush should be preferred
  static const List<String> jpushPreferredRegions = [
    'cn', // Mainland China
    'CN',
  ];

  /// Regions where FCM should be preferred
  static const List<String> fcmPreferredRegions = [
    'us',
    'uk',
    'jp',
    'kr',
    'sg',
    'eu',
    'international',
  ];

  // ===========================================================================
  // Token Types
  // ===========================================================================

  /// Token type for FCM
  static const String tokenTypeFcm = 'fcm';

  /// Token type for APNs
  static const String tokenTypeApns = 'apns';

  /// Token type for JPush
  static const String tokenTypeJpush = 'jpush';

  /// Token type for Huawei HMS
  static const String tokenTypeHuawei = 'huawei';

  // ===========================================================================
  // Notification Types
  // ===========================================================================

  /// System notification type
  static const String notificationTypeSystem = 'system';

  /// Task reminder notification type
  static const String notificationTypeTaskReminder = 'task_reminder';

  /// Achievement notification type
  static const String notificationTypeAchievement = 'achievement';

  /// Chat notification type
  static const String notificationTypeChat = 'chat';

  /// Goal notification type
  static const String notificationTypeGoal = 'goal';

  /// Streak notification type
  static const String notificationTypeStreak = 'streak';

  // ===========================================================================
  // Deep Link Schemes
  // ===========================================================================

  /// Deep link scheme for the app
  static const String deepLinkScheme = 'sparkle';

  /// Deep link host
  static const String deepLinkHost = 'app';

  /// Build a deep link URL
  static String buildDeepLink(String path, [Map<String, String>? params]) {
    var url = '$deepLinkScheme://$deepLinkHost/$path';
    if (params != null && params.isNotEmpty) {
      final queryString = params.entries
          .map((e) => '${e.key}=${Uri.encodeComponent(e.value)}')
          .join('&');
      url = '$url?$queryString';
    }
    return url;
  }

  // ===========================================================================
  // Helper Methods
  // ===========================================================================

  /// Check if JPush should be used based on region
  static bool shouldUseJPush(String? region) {
    if (!jpushEnabled) return false;
    if (region == null) return false;
    return jpushPreferredRegions.contains(region.toLowerCase());
  }

  /// Check if FCM should be used based on region
  static bool shouldUseFcm(String? region) {
    if (!fcmEffectiveEnabled) return false;
    if (region == null) return true; // Default to FCM
    return !jpushPreferredRegions.contains(region.toLowerCase());
  }
}
