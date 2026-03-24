/// Stub implementation for Google Sign-In
///
/// This file is used when Google services are disabled (ENABLE_GOOGLE_SERVICES=false)
/// to provide a no-op implementation that allows the app to build and run
/// without Google Sign-In dependency.

import 'package:logger/logger.dart';

/// Result of a social authentication flow
class SocialAuthResult {
  SocialAuthResult({
    required this.provider,
    required this.token,
    this.openid,
    this.email,
    this.nickname,
    this.avatarUrl,
  });

  final String provider;
  final String token;
  final String? openid;
  final String? email;
  final String? nickname;
  final String? avatarUrl;

  @override
  String toString() =>
      'SocialAuthResult(provider: $provider, token: ${token.substring(0, 5)}..., email: $email)';
}

/// Social authentication service stub (Google services disabled)
///
/// Provides WeChat and Apple login, but Google login is unavailable.
class SocialAuthService {
  factory SocialAuthService() => _instance;
  SocialAuthService._internal();
  static final SocialAuthService _instance = SocialAuthService._internal();

  final Logger _logger = Logger();
  bool _weChatInitialized = false;

  /// WeChat App ID
  String _weChatAppId = const String.fromEnvironment('WECHAT_APP_ID');
  String _weChatUniversalLink =
      const String.fromEnvironment('WECHAT_UNIVERSAL_LINK');

  /// Whether WeChat SDK is available
  bool get isWeChatAvailable => _weChatInitialized;

  /// Initialize WeChat SDK
  Future<void> initWeChat({String? appId, String? universalLink}) async {
    final effectiveAppId = appId ?? _weChatAppId;
    if (effectiveAppId.isEmpty) {
      _logger.w('WeChat App ID not configured — skipping SDK init');
      return;
    }
    if (_weChatInitialized) return;

    try {
      _weChatAppId = effectiveAppId;
      _weChatUniversalLink = universalLink ?? _weChatUniversalLink;
      _weChatInitialized = true;
      _logger.i('WeChat SDK initialized (stub mode)');
    } catch (e) {
      _logger.e('WeChat SDK init failed: $e');
    }
  }

  /// Google Sign In (unavailable when Google services disabled)
  Future<SocialAuthResult?> signInWithGoogle() async {
    _logger.w('Google Sign-In is disabled in this build');
    throw UnsupportedError(
      'Google 登录在当前版本不可用。此版本仅支持微信和 Apple 登录。',
    );
  }

  /// Apple Sign In (requires sign_in_with_apple package)
  Future<SocialAuthResult?> signInWithApple() async {
    _logger.i('Apple Sign-In requested');
    // This would need the actual implementation from sign_in_with_apple
    // For the stub, we just log and return null
    throw UnimplementedError(
      'Apple Sign-In requires the sign_in_with_apple package. '
      'Please use the full build for Apple Sign-In support.',
    );
  }

  /// WeChat Sign In
  Future<SocialAuthResult?> signInWithWeChat() async {
    if (!_weChatInitialized || _weChatAppId.isEmpty) {
      throw UnsupportedError(
        '微信登录不可用：SDK 未初始化或 App ID 未配置。',
      );
    }
    // This would need the actual implementation from fluwx
    // For the stub, we just log and return null
    _logger.i('WeChat Sign-In requested');
    return null;
  }
}
