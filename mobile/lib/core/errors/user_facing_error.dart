import 'package:flutter/foundation.dart';
import 'package:sparkle/core/services/i18n_service.dart';

/// Strips internal error details and returns a user-safe error message.
///
/// Use this instead of `e.toString()` in catch blocks to prevent
/// stack traces, class names, and internal details from reaching the UI.
///
/// All user-facing messages are localized via ARB keys (error*).
///
/// A-3 diagnosability (client-side aid): every mapped message carries a
/// stable `[ERR-*]` category code so field reports — even a bare
/// screenshot of a release build — can be traced to a failure category.
/// The original exception is additionally surfaced via [debugPrint] in
/// debug builds only (silent in release), e.g. into logcat during
/// on-device testing.
class UserFacingError {
  UserFacingError._();

  /// Stable short category codes appended to the localized copy.
  ///
  /// Keep these terse and stable: they are the join key between field
  /// reports and the error taxonomy above.
  static const String _codeNetwork = 'ERR-NET';
  static const String _codeAuth = 'ERR-AUTH';
  static const String _codeTimeout = 'ERR-TIMEOUT';
  static const String _codeServer = 'ERR-SERVER';
  static const String _codeNotFound = 'ERR-NOTFOUND';
  static const String _codeRateLimit = 'ERR-RATELIMIT';
  static const String _codeFormat = 'ERR-FORMAT';
  static const String _codeUnknown = 'ERR-UNKNOWN';

  /// Categories of errors that map to user-friendly messages.
  static String from(Object error) {
    // Debug-only root-cause aid: the raw exception never reaches the UI,
    // but a developer/tester running a debug build gets it in the log.
    if (kDebugMode) {
      debugPrint('[UserFacingError] ${error.runtimeType}: $error');
    }
    final message = error.toString();

    // Common network patterns
    if (_containsAny(message, [
      'SocketException',
      'Connection refused',
      'Connection timed out',
      'network',
      'Network',
      'CLIENT_CLOSED',
    ])) {
      return _withCode(S.errorNetworkDetail, _codeNetwork);
    }

    // Auth patterns
    if (_containsAny(message, [
      '401',
      '403',
      'Unauthorized',
      'Forbidden',
      'token',
      'Token expired',
    ])) {
      return _withCode(S.errorAuthDetail, _codeAuth);
    }

    // Timeout patterns
    if (_containsAny(message, ['TimeoutException', 'timed out', 'timeout'])) {
      return _withCode(S.errorTimeoutDetail, _codeTimeout);
    }

    // Server errors
    if (_containsAny(message, ['500', '502', '503', '504', 'Internal Server'])) {
      return _withCode(S.errorServerDetail, _codeServer);
    }

    // Not found
    if (_containsAny(message, ['404', 'Not Found', 'not found'])) {
      return _withCode(S.errorNotFoundDetail, _codeNotFound);
    }

    // Rate limiting
    if (_containsAny(message, ['429', 'rate limit', 'Rate limit', 'too many'])) {
      return _withCode(S.errorRateLimitDetail, _codeRateLimit);
    }

    // Format/validation errors
    if (_containsAny(message, ['FormatException', 'invalid', 'Invalid'])) {
      return _withCode(S.errorUnknownDetail, _codeFormat);
    }

    // Default: return a generic message, still traceable via its code.
    return _withCode(S.errorDefaultTitle, _codeUnknown);
  }

  static String _withCode(String message, String code) => '$message [$code]';

  static bool _containsAny(String source, List<String> patterns) {
    for (final pattern in patterns) {
      if (source.contains(pattern)) return true;
    }
    return false;
  }
}
