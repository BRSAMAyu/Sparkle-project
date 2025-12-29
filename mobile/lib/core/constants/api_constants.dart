import 'package:flutter/foundation.dart';

/// API Constants
class ApiConstants {
  static const String _baseUrlOverride = String.fromEnvironment('API_BASE_URL');
  static const String _wsBaseUrlOverride = String.fromEnvironment('WS_BASE_URL');

  // Base URL (HTTP)
  static String get baseUrl {
    if (_baseUrlOverride.isNotEmpty) {
      if (kReleaseMode && _baseUrlOverride.startsWith('http:')) {
        debugPrint('⚠️ WARNING: Using insecure HTTP API in RELEASE mode. Consider using HTTPS.');
      }
      return _baseUrlOverride;
    }

    // Default fallback logic
    if (kIsWeb) {
      if (kReleaseMode) {
        debugPrint('⚠️ WARNING: Flutter Web in release mode may require HTTPS for many features.');
      }
      return 'http://localhost:8080';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8080';
    }
    return 'http://localhost:8080';
  }
  
  static const String apiVersion = 'v1';
  static const String apiBasePath = '/api/$apiVersion';

  // WebSocket URL (Go Gateway)
  static String get wsBaseUrl {
    final String rawBaseUrl = _wsBaseUrlOverride.isNotEmpty
        ? _wsBaseUrlOverride
        : _baseUrlOverride.isNotEmpty
            ? _toWsUrl(_baseUrlOverride)
            : _defaultWsBaseUrl();
    final bool isProduction = kReleaseMode;
    return _applyWsSchemeForEnvironment(rawBaseUrl, isProduction: isProduction);
  }
  static const String wsChat = '/ws/chat';

  // Endpoints
  static const String auth = '/auth';
  static const String login = '$auth/login';
  static const String register = '$auth/register';
  static const String logout = '$auth/logout';
  static const String refreshToken = '$auth/refresh';

  static const String users = '/users';
  static const String tasks = '/tasks';
  static const String chat = '/chat';
  static const String plans = '/plans';
  static const String statistics = '/statistics';

  // Timeout
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const Duration sendTimeout = Duration(seconds: 30);

  static String _defaultWsBaseUrl() {
    if (kIsWeb) {
      return 'ws://localhost:8080';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'ws://10.0.2.2:8080';
    }
    return 'ws://localhost:8080';
  }

  static String _applyWsSchemeForEnvironment(
    String rawBaseUrl, {
    required bool isProduction,
  }) {
    final uri = Uri.parse(rawBaseUrl);
    if (isProduction) {
      // 仅警告，不强制修改协议，避免破坏用户显式配置
      if (uri.scheme == 'ws') {
        debugPrint('⚠️ WARNING: Using insecure WebSocket (ws://) in RELEASE mode. '
            'Consider using secure WebSocket (wss://) for production.');
      } else if (uri.scheme == 'http') {
        debugPrint('⚠️ WARNING: Using insecure HTTP (http://) in RELEASE mode. '
            'Consider using HTTPS for production.');
      }
    }
    return rawBaseUrl;
  }

  static String _toWsUrl(String httpBase) {
    final uri = Uri.parse(httpBase);
    final wsScheme = uri.scheme == 'https' ? 'wss' : 'ws';
    return uri.replace(scheme: wsScheme, path: '').toString();
  }
}
