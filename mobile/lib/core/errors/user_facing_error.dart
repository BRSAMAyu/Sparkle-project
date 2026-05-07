/// Strips internal error details and returns a user-safe error message.
///
/// Use this instead of `e.toString()` in catch blocks to prevent
/// stack traces, class names, and internal details from reaching the UI.
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
      return 'Network error, please check your connection';
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
      return 'Session expired, please sign in again';
    }

    // Timeout patterns
    if (_containsAny(message, ['TimeoutException', 'timed out', 'timeout'])) {
      return 'Request timed out, please try again';
    }

    // Server errors
    if (_containsAny(message, ['500', '502', '503', '504', 'Internal Server'])) {
      return 'Server error, please try again later';
    }

    // Not found
    if (_containsAny(message, ['404', 'Not Found', 'not found'])) {
      return 'Resource not found';
    }

    // Rate limiting
    if (_containsAny(message, ['429', 'rate limit', 'Rate limit', 'too many'])) {
      return 'Too many requests, please wait a moment';
    }

    // Format/validation errors
    if (_containsAny(message, ['FormatException', 'invalid', 'Invalid'])) {
      return 'Invalid data format';
    }

    // Default: return a generic message
    return 'Something went wrong, please try again';
  }

  static bool _containsAny(String source, List<String> patterns) {
    for (final pattern in patterns) {
      if (source.contains(pattern)) return true;
    }
    return false;
  }
}
