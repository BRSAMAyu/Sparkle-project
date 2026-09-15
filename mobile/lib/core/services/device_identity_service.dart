import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:uuid/uuid.dart';

const _deviceIdentityKey = 'auth_device_identity_v1';

class DeviceIdentityService {
  DeviceIdentityService(this._prefs);

  final SharedPreferences _prefs;
  Map<String, String>? _cachedHeaders;
  String? _cachedDeviceId;

  Future<Map<String, String>> buildHeaders() async {
    final cachedHeaders = _cachedHeaders;
    if (cachedHeaders != null && cachedHeaders.isNotEmpty) {
      return cachedHeaders;
    }
    final deviceId = await _getOrCreateDeviceId();
    final platform = kIsWeb ? 'web' : Platform.operatingSystem;
    final deviceName = kIsWeb
        ? 'Web Browser'
        : '${Platform.operatingSystem} ${Platform.operatingSystemVersion}';

    final headers = {
      'X-Device-Id': deviceId,
      'X-Device-Platform': platform,
      'X-Device-Name': deviceName,
    };
    _cachedHeaders = headers;
    return headers;
  }

  Future<String> _getOrCreateDeviceId() async {
    final cachedDeviceId = _cachedDeviceId;
    if (cachedDeviceId != null && cachedDeviceId.isNotEmpty) {
      return cachedDeviceId;
    }
    final cached = _prefs.getString(_deviceIdentityKey);
    if (cached != null && cached.isNotEmpty) {
      _cachedDeviceId = cached;
      return cached;
    }
    final deviceId = const Uuid().v4();
    await _prefs.setString(_deviceIdentityKey, deviceId);
    _cachedDeviceId = deviceId;
    return deviceId;
  }
}

final deviceIdentityServiceProvider = Provider<DeviceIdentityService>(
  (ref) => DeviceIdentityService(ref.watch(sharedPreferencesProvider)),
);
