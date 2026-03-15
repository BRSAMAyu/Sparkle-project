import 'dart:async';
import 'dart:io';

import 'package:fluwx/fluwx.dart' as fluwx;
import 'package:google_sign_in/google_sign_in.dart';
import 'package:logger/logger.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

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

class SocialAuthService {
  factory SocialAuthService() => _instance;
  SocialAuthService._internal();
  static final SocialAuthService _instance = SocialAuthService._internal();

  final Logger _logger = Logger();

  bool _weChatInitialized = false;

  /// WeChat App ID — set via [initWeChat] or environment config.
  /// When empty the SDK is considered unavailable and [signInWithWeChat]
  /// will throw [UnsupportedError].
  String _weChatAppId = const String.fromEnvironment('WECHAT_APP_ID');

  /// Whether the WeChat SDK has been successfully registered on this device.
  bool get isWeChatAvailable => _weChatInitialized;

  /// Initialize WeChat SDK.
  ///
  /// Call once at app startup (e.g. in main.dart).  If [appId] is empty the
  /// SDK will not be registered and [signInWithWeChat] will be unavailable.
  ///
  /// On platforms where WeChat is not supported (web, desktop) this is a no-op.
  Future<void> initWeChat({String? appId}) async {
    final effectiveAppId = appId ?? _weChatAppId;
    if (effectiveAppId.isEmpty) {
      _logger.w('WeChat App ID not configured — skipping SDK init');
      return;
    }
    if (_weChatInitialized) return;

    try {
      _weChatAppId = effectiveAppId;

      // Universal Link is required on iOS; Android uses the app signature.
      // Replace with your own universal-link domain once configured.
      final universalLink = Platform.isIOS
          ? 'https://your-domain.com/app/'
          : '';

      await fluwx.registerWxApi(
        appId: effectiveAppId,
        universalLink: universalLink,
      );
      _weChatInitialized = true;
      _logger.i('WeChat SDK initialized (appId=${effectiveAppId.substring(0, 4)}…)');
    } catch (e) {
      _logger.e('WeChat SDK init failed: $e');
    }
  }

  // --- Google Sign In ---
  final GoogleSignIn _googleSignIn = GoogleSignIn(
    // scopes: ['email', 'profile'], // Default scopes are usually enough
  );

  Future<SocialAuthResult?> signInWithGoogle() async {
    try {
      final googleUser = await _googleSignIn.signIn();
      if (googleUser == null) {
        return null; // User canceled
      }

      final googleAuth =
          await googleUser.authentication;

      return SocialAuthResult(
        provider: 'google',
        token: googleAuth.idToken ?? '', // Backend verifies idToken
        email: googleUser.email,
        nickname: googleUser.displayName,
        avatarUrl: googleUser.photoUrl,
      );
    } catch (e) {
      _logger.e('Google Sign In Error: $e');
      rethrow;
    }
  }

  // --- Apple Sign In ---
  Future<SocialAuthResult?> signInWithApple() async {
    try {
      final credential = await SignInWithApple.getAppleIDCredential(
        scopes: [
          AppleIDAuthorizationScopes.email,
          AppleIDAuthorizationScopes.fullName,
        ],
      );

      return SocialAuthResult(
        provider: 'apple',
        token: credential.identityToken ?? '',
        email: credential.email,
        nickname: [credential.givenName, credential.familyName]
            .where((s) => s != null)
            .join(' '),
      );
    } catch (e) {
      if (e is SignInWithAppleAuthorizationException &&
          e.code == AuthorizationErrorCode.canceled) {
        return null;
      }
      _logger.e('Apple Sign In Error: $e');
      rethrow;
    }
  }

  // --- WeChat Sign In ---
  /// Launches the WeChat OAuth flow (code exchange).
  ///
  /// Returns a [SocialAuthResult] with `provider: "wechat"` and
  /// `token` set to the authorization code.  The backend exchanges
  /// this code for an access_token + openid via the WeChat API.
  ///
  /// Throws [UnsupportedError] if the SDK was not initialized or WeChat
  /// is not installed on the device.
  Future<SocialAuthResult?> signInWithWeChat() async {
    if (!_weChatInitialized || _weChatAppId.isEmpty) {
      throw UnsupportedError(
        '微信登录不可用：SDK 未初始化或 App ID 未配置。',
      );
    }

    final installed = await fluwx.isWeChatInstalled;
    if (!installed) {
      throw UnsupportedError('请先安装微信客户端');
    }

    // Send OAuth request — WeChat will callback via onWeChatResponse.
    final sent = await fluwx.sendWeChatAuth(
      scope: 'snsapi_userinfo',
      state: 'sparkle_login',
    );
    if (!sent) {
      _logger.e('WeChat sendAuth returned false');
      return null;
    }

    // Listen for the single auth response.
    final completer = Completer<SocialAuthResult?>();
    late final StreamSubscription<fluwx.BaseWeChatResponse> subscription;

    subscription = fluwx.weChatResponseEventHandler.listen((response) {
      if (response is fluwx.WeChatAuthResponse) {
        subscription.cancel();
        if (response.errCode != 0 || response.code == null) {
          _logger.w('WeChat auth denied or failed: errCode=${response.errCode}');
          completer.complete(null);
        } else {
          completer.complete(
            SocialAuthResult(
              provider: 'wechat',
              // Send the auth code to the backend; it will do the code→token exchange.
              token: response.code!,
            ),
          );
        }
      }
    });

    // Timeout after 2 minutes.
    return completer.future.timeout(
      const Duration(minutes: 2),
      onTimeout: () {
        subscription.cancel();
        _logger.w('WeChat auth timed out');
        return null;
      },
    );
  }
}
