import 'dart:async';

// import 'package:fluwx/fluwx.dart'; // 🔧 Disabled for Demo build
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
  // 🔧 WeChat support disabled for Demo build
  Future<void> initWeChat() async {
    // WeChat SDK not available in demo build
    _logger.w('WeChat SDK not available in this build');
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
  // 🔧 WeChat login not available in Demo build (fluwx dependency disabled)
  Future<SocialAuthResult?> signInWithWeChat() async {
    _logger.w('WeChat login not available in this build');
    throw UnsupportedError(
      'WeChat login is not available in this Demo version. '
      'Please use Google or Apple sign-in instead.',
    );
  }
}
