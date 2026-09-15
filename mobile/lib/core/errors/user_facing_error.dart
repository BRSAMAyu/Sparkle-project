import 'package:sparkle/core/services/i18n_service.dart';

/// Strips internal error details and returns a user-safe error message.
///
/// Use this instead of `e.toString()` in catch blocks to prevent
/// stack traces, class names, and internal details from reaching the UI.
///
/// All user-facing messages are localized via ARB keys (error*).
class UserFacingError {
  UserFacingError._();

  /// Categories of errors that map to user-friendly messages.
  static String from(Object error) {
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
      return S.errorNetworkDetail;
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
      return S.errorAuthDetail;
    }

    // Timeout patterns
    if (_containsAny(message, ['TimeoutException', 'timed out', 'timeout'])) {
      return S.errorTimeoutDetail;
    }

    // Server errors
    if (_containsAny(message, ['500', '502', '503', '504', 'Internal Server'])) {
      return S.errorServerDetail;
    }

    // Not found
    if (_containsAny(message, ['404', 'Not Found', 'not found'])) {
      return S.errorNotFoundDetail;
    }

    // Rate limiting
    if (_containsAny(message, ['429', 'rate limit', 'Rate limit', 'too many'])) {
      return S.errorRateLimitDetail;
    }

    // Format/validation errors
    if (_containsAny(message, ['FormatException', 'invalid', 'Invalid'])) {
      return S.errorUnknownDetail;
    }

    // Default: return a generic message
    return S.errorDefaultTitle;
  }

  static bool _containsAny(String source, List<String> patterns) {
    for (final pattern in patterns) {
      if (source.contains(pattern)) return true;
    }
    return false;
  }
}
