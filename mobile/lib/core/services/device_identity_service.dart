import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';

const _deviceIdentityKey = 'auth_device_identity_v1';

class DeviceIdentityService {
  DeviceIdentityService(this._prefs);

  final SharedPreferences _prefs;

  Future<Map<String, String>> buildHeaders() async {
    final deviceId = await _getOrCreateDeviceId();
    final platform = kIsWeb ? 'web' : Platform.operatingSystem;
    final deviceName = kIsWeb
        ? 'Web Browser'
        : '${Platform.operatingSystem} ${Platform.operatingSystemVersion}';

    return {
      'X-Device-Id': deviceId,
      'X-Device-Platform': platform,
      'X-Device-Name': deviceName,
    };
  }

  Future<String> _getOrCreateDeviceId() async {
    final cached = _prefs.getString(_deviceIdentityKey);
    if (cached != null && cached.isNotEmpty) {
      return cached;
    }
    final deviceId = const Uuid().v4();
    await _prefs.setString(_deviceIdentityKey, deviceId);
    return deviceId;
  }
}

final deviceIdentityServiceProvider = Provider<DeviceIdentityService>(
  (ref) => DeviceIdentityService(ref.watch(sharedPreferencesProvider)),
);
