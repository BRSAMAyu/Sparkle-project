import 'package:flutter/foundation.dart';

/// API Constants
class ApiConstants {
  static const String _baseUrlOverride = String.fromEnvironment('API_BASE_URL');
  static const String _wsBaseUrlOverride =
      String.fromEnvironment('WS_BASE_URL');
  static const String _androidEmulatorUrlOverride =
      String.fromEnvironment('ANDROID_EMULATOR_URL');
  static const String _androidDeviceUrlOverride =
      String.fromEnvironment('ANDROID_DEVICE_URL');
  static const bool _androidUseEmulator =
      bool.fromEnvironment('ANDROID_USE_EMULATOR');
  static const String apiCertSha256 =
      String.fromEnvironment('API_CERT_SHA256');

  // Base URL (HTTP)
  static String get baseUrl {
    if (_baseUrlOverride.isNotEmpty) {
      if (kReleaseMode && _baseUrlOverride.startsWith('http:')) {
        debugPrint(
            '⚠️ WARNING: Using insecure HTTP API in RELEASE mode. Consider using HTTPS.',);
      }
      return _baseUrlOverride;
    }

    // Default fallback logic
    if (kIsWeb) {
      if (kReleaseMode) {
        debugPrint(
            '⚠️ WARNING: Flutter Web in release mode may require HTTPS for many features.',);
      }
      return 'http://localhost:8080';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return _androidBaseUrl();
    }
    return 'http://localhost:8080';
  }

  static const String apiVersion = 'v1';
  static const String apiBasePath = '/api/$apiVersion';

  // WebSocket URL (Go Gateway)
  static String get wsBaseUrl {
    final rawBaseUrl = _wsBaseUrlOverride.isNotEmpty
        ? _wsBaseUrlOverride
        : _baseUrlOverride.isNotEmpty
            ? _toWsUrl(_baseUrlOverride)
            : _defaultWsBaseUrl();
    const isProduction = kReleaseMode;
    return _applyWsSchemeForEnvironment(rawBaseUrl, isProduction: isProduction);
  }

  static const String wsChat = '/ws/chat';
  static const String wsStt = '/ws/stt';

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

  // gRPC Configuration
  /// gRPC server host (Python backend)
  static String get grpcHost {
    if (_baseUrlOverride.isNotEmpty) {
      final uri = Uri.parse(_baseUrlOverride);
      return uri.host;
    }
    if (kIsWeb) {
      return 'localhost';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      final uri = Uri.parse(_androidBaseUrl());
      return uri.host;
    }
    return 'localhost';
  }

  /// gRPC server port (Python backend default)
  static const int grpcPort = 50051;

  static String _defaultWsBaseUrl() {
    if (kIsWeb) {
      return 'ws://localhost:8080';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return _toWsUrl(_androidBaseUrl());
    }
    return 'ws://localhost:8080';
  }

  static String _androidBaseUrl() {
    if (_androidEmulatorUrlOverride.isNotEmpty) {
      return _androidEmulatorUrlOverride;
    }
    if (_androidUseEmulator) {
      return 'http://10.0.2.2:8080';
    }
    if (_androidDeviceUrlOverride.isNotEmpty) {
      return _androidDeviceUrlOverride;
    }
    // Default to emulator host to preserve existing behavior.
    return 'http://10.0.2.2:8080';
  }

  static String _applyWsSchemeForEnvironment(
    String rawBaseUrl, {
    required bool isProduction,
  }) {
    final uri = Uri.parse(rawBaseUrl);
    if (isProduction) {
      // 仅警告，不强制修改协议，避免破坏用户显式配置
      if (uri.scheme == 'ws') {
        debugPrint(
            '⚠️ WARNING: Using insecure WebSocket (ws://) in RELEASE mode. '
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
