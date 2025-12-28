import 'package:flutter/foundation.dart';

/// API Constants
class ApiConstants {
  static const String _baseUrlOverride = String.fromEnvironment('API_BASE_URL');
  static const String _wsBaseUrlOverride = String.fromEnvironment('WS_BASE_URL');

  // Base URL (HTTP)
  static String get baseUrl {
    if (_baseUrlOverride.isNotEmpty) {
      return _baseUrlOverride;
    }
    if (kIsWeb) {
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
    if (_wsBaseUrlOverride.isNotEmpty) {
      return _wsBaseUrlOverride;
    }
    if (_baseUrlOverride.isNotEmpty) {
      return _toWsUrl(_baseUrlOverride);
    }
    if (kIsWeb) {
      return 'ws://localhost:8080';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'ws://10.0.2.2:8080';
    }
    return 'ws://localhost:8080';
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

  static String _toWsUrl(String httpBase) {
    final uri = Uri.parse(httpBase);
    final wsScheme = uri.scheme == 'https' ? 'wss' : 'ws';
    return uri.replace(scheme: wsScheme, path: '').toString();
  }
}
