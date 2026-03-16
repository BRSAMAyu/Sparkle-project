import 'dart:async';
import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

/// Manages device push token registration with the backend.
///
/// Responsibilities:
/// 1. Generate and cache device ID
/// 2. Register FCM/APNs token with backend API
/// 3. Handle token refresh
/// 4. Track registration status
class PushTokenManager extends AsyncNotifier<void> {
  final Logger _logger = Logger();
  static const _deviceIdKey = 'push_device_id';
  static const _lastTokenKey = 'push_last_token';

  String? _deviceId;
  String? _lastRegisteredToken;

  @override
  Future<void> build() async {
    // Initialize device ID on build
    _deviceId = await _getOrCreateDeviceId();
  }

  /// Get or create a unique device identifier
  Future<String> _getOrCreateDeviceId() async {
    final prefs = ref.read(sharedPreferencesProvider);
    var deviceId = prefs.getString(_deviceIdKey);

    if (deviceId == null) {
      // Generate new device ID based on device info
      final deviceInfo = DeviceInfoPlugin();
      String identifier;

      if (Platform.isAndroid) {
        final androidInfo = await deviceInfo.androidInfo;
        identifier = '${androidInfo.brand}_${androidInfo.model}_${androidInfo.id}';
      } else if (Platform.isIOS) {
        final iosInfo = await deviceInfo.iosInfo;
        identifier = '${iosInfo.name}_${iosInfo.model}_${iosInfo.identifierForVendor ?? "unknown"}';
      } else {
        identifier = 'unknown_${DateTime.now().millisecondsSinceEpoch}';
      }

      // Create a hash for consistent device ID
      deviceId = 'sparkle_${identifier.hashCode.toRadixString(16)}';
      await prefs.setString(_deviceIdKey, deviceId!);
      _logger.i('Generated new device ID: $deviceId');
    }

    return deviceId;
  }

  /// Register push token with backend
  ///
  /// This should be called:
  /// - On app startup (after getting FCM token)
  /// - When token is refreshed
  Future<bool> registerToken(String token) async {
    if (token.isEmpty) {
      _logger.w('Attempted to register empty token');
      return false;
    }

    // Skip if already registered with same token
    if (token == _lastRegisteredToken) {
      _logger.d('Token already registered, skipping');
      return true;
    }

    try {
      final deviceId = await _getOrCreateDeviceId();
      final platform = Platform.isIOS ? 'ios' : Platform.isAndroid ? 'android' : 'web';
      final tokenType = Platform.isIOS ? 'apns' : 'fcm';

      // Get app version
      final packageInfo = await PackageInfo.fromPlatform();
      final appVersion = '${packageInfo.version}+${packageInfo.buildNumber}';

      // Get OS version
      String? osVersion;
      final deviceInfo = DeviceInfoPlugin();
      if (Platform.isAndroid) {
        final androidInfo = await deviceInfo.androidInfo;
        osVersion = 'Android ${androidInfo.version.release}';
      } else if (Platform.isIOS) {
        final iosInfo = await deviceInfo.iosInfo;
        osVersion = 'iOS ${iosInfo.systemVersion}';
      }

      // Get device name
      String? deviceName;
      if (Platform.isAndroid) {
        final androidInfo = await deviceInfo.androidInfo;
        deviceName = '${androidInfo.manufacturer} ${androidInfo.model}';
      } else if (Platform.isIOS) {
        final iosInfo = await deviceInfo.iosInfo;
        deviceName = iosInfo.name;
      }

      final apiClient = ref.read(apiClientProvider);

      final response = await apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.registerDevice,
        data: <String, dynamic>{
          'device_id': deviceId,
          'push_token': token,
          'platform': platform,
          'token_type': tokenType,
          'device_name': deviceName,
          'app_version': appVersion,
          'os_version': osVersion,
        },
      );

      if (response.data != null) {
        _lastRegisteredToken = token;

        // Cache last token
        final prefs = ref.read(sharedPreferencesProvider);
        await prefs.setString(_lastTokenKey, token);

        _logger.i('Successfully registered push token for device $deviceId');
        return true;
      }

      return false;
    } catch (e, stack) {
      _logger.e('Failed to register push token: $e');
      _logger.d(stack.toString());
      return false;
    }
  }

  /// Unregister current device from push notifications
  Future<bool> unregisterDevice() async {
    try {
      final deviceId = await _getOrCreateDeviceId();

      final apiClient = ref.read(apiClientProvider);
      await apiClient.delete(
        ApiEndpoints.unregisterDevice,
        queryParameters: {'device_id': deviceId},
      );

      // Clear cached token
      _lastRegisteredToken = null;
      final prefs = ref.read(sharedPreferencesProvider);
      await prefs.remove(_lastTokenKey);

      _logger.i('Successfully unregistered device $deviceId');
      return true;
    } catch (e) {
      _logger.e('Failed to unregister device: $e');
      return false;
    }
  }

  /// Check if token needs to be re-registered
  Future<bool> needsReRegistration(String currentToken) async {
    final prefs = ref.read(sharedPreferencesProvider);
    final lastToken = prefs.getString(_lastTokenKey);

    return lastToken != currentToken;
  }

  /// Get current device ID
  Future<String?> getDeviceId() async {
    _deviceId ??= await _getOrCreateDeviceId();
    return _deviceId;
  }
}

/// Provider for PushTokenManager
final pushTokenManagerProvider =
    AsyncNotifierProvider<PushTokenManager, void>(PushTokenManager.new);

/// Provider for SharedPreferences (should be overridden in main.dart)
final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPreferencesProvider must be overridden');
});
