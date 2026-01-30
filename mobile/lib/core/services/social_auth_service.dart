import 'dart:async';
import 'dart:io';

import 'package:fluwx/fluwx.dart';
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

  // Initialize WeChat (Call this on app start if possible, or lazily)
  bool _isWeChatInitialized = false;

  // Placeholder App ID - Replace with real one in production config
  static const String _weChatAppId = 'wx_replace_with_your_app_id';

  Future<void> initWeChat() async {
    if (_isWeChatInitialized) return;
    try {
      await Fluwx().registerApi(appId: _weChatAppId);
      _isWeChatInitialized = true;
    } catch (e) {
      _logger.e('Failed to register WeChat API: $e');
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
  Future<SocialAuthResult?> signInWithWeChat() async {
    if (!(Platform.isAndroid || Platform.isIOS)) {
      throw Exception('WeChat login is only supported on mobile platforms');
    }
    await initWeChat();

    if (!await Fluwx().isWeChatInstalled) {
      throw Exception('WeChat is not installed');
    }

    final completer = Completer<WeChatAuthResponse>();
    FluwxCancelable? subscription;
    subscription = Fluwx().addSubscriber((response) {
      if (response is WeChatAuthResponse && !completer.isCompleted) {
        completer.complete(response);
        subscription?.cancel();
      }
    });

    final sent = await Fluwx().authBy(
      which: NormalAuth(
        scope: 'snsapi_userinfo',
        state: 'sparkle_auth_state',
      ),
    );

    if (!sent) {
      subscription.cancel();
      throw Exception('Failed to send WeChat auth request');
    }

    final response = await completer.future;

    if (response.errCode == 0 && response.code != null) {
      // Success
      // Note: For WeChat, the 'token' here is the temporary 'code'.
      // The backend will use this code + AppID + AppSecret to get access_token and openid.
      // However, the current backend implementation seems to expect 'token' (access_token) and 'openid' directly
      // OR it might need updating to handle the 'code' exchange flow (preferred for security).
      
      // Let's assume for now we send the code as 'token' and backend handles exchange,
      // OR we adjust backend. 
      // The provided backend code shows: 
      // "https://api.weixin.qq.com/sns/auth?access_token=...&openid=..."
      // This implies the FRONTEND is expected to do the code exchange.
      // Doing code exchange on frontend is INSECURE (requires AppSecret on client).
      
      // RECOMMENDATION: We should send the 'code' to the backend.
      // BUT, to respect the current backend logic which verifies access_token directly (likely for legacy reasons or misdesign),
      // we might be stuck.
      
      // Wait, checking backend code again:
      // backend/app/api/v1/auth.py:221
      // response = await client.get("https://api.weixin.qq.com/sns/auth", ...)
      // This endpoint validates an access_token. It is NOT the code exchange endpoint (sns/oauth2/access_token).
      
      // So the current backend expects the Frontend to have already exchanged code for access_token.
      // This is bad practice (exposes App Secret).
      // However, to make it "work" without rewriting backend logic entirely, I might need to implement the exchange here
      // OR update the backend to support code exchange.
      
      // Given I can change backend, I will implement the SECURE way:
      // Frontend sends CODE. Backend exchanges CODE for Token.
      
      // But for this specific task "make it usable", I will try to support what the backend expects if possible,
      // or fix the backend.
      
      // Let's stick to sending the CODE, and I will update the backend to handle 'code' if it detects it,
      // or strictly follow the current "validate token" path if I must.
      
      // Actually, standard WeChat flow:
      // 1. App gets Code.
      // 2. App -> Server: Code.
      // 3. Server -> WeChat: Code -> AccessToken + OpenID.
      // 4. Server uses AccessToken + OpenID to get UserInfo.
      
      // The current backend code does:
      // Client sends token + openid.
      // Backend validates them via sns/auth.
      
      // I will implement the Frontend to return the CODE.
      // I will update the Backend to handle the code exchange.
      
      return SocialAuthResult(
        provider: 'wechat',
        token: response.code!, 
        // We don't have openid yet, backend will get it.
      );
    } else {
      if (response.errCode == -2) return null; // User Cancelled
      throw Exception('WeChat Login Failed: ${response.errStr}');
    }
  }
}
