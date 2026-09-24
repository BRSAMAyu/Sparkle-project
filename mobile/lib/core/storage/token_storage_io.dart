import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'package:sparkle/core/storage/token_storage.dart';

/// 原生平台（Android / iOS / Linux / macOS / Windows）后端：
/// 直接转发 FlutterSecureStorage（Keystore / Keychain）。
///
/// 行为与修复前的 auth_repository 直连版本完全一致——默认选项沿用
/// 原 flutterSecureStorageProvider 的配置
/// （Android EncryptedSharedPreferences + iOS first_unlock）。
/// 可注入 [storage] 便于测试替换内存实现。
class SecureTokenStorage implements TokenStorage {
  SecureTokenStorage({
    FlutterSecureStorage? storage,
  }) : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
              iOptions: IOSOptions(
                accessibility: KeychainAccessibility.first_unlock,
              ),
              // macOS fix: the Data Protection keychain requires
              // keychain-access-groups entitlements which unsigned local
              // builds lack (SecItem -> -34018 errSecMissingEntitlement).
              // Use the legacy file-based keychain instead.
              mOptions: MacOsOptions(useDataProtectionKeyChain: false),
            );

  final FlutterSecureStorage _storage;

  @override
  Future<String?> read(String key) => _storage.read(key: key);

  @override
  Future<void> write(String key, String value) =>
      _storage.write(key: key, value: value);

  @override
  Future<void> delete(String key) => _storage.delete(key: key);
}

TokenStorage createTokenStorageImpl() => SecureTokenStorage();
