import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:sparkle/core/storage/token_storage_io.dart' if (dart.library.html) 'token_storage_web.dart';

/// Token 持久化门面（key-value，全异步）。
///
/// 背景（web-round1 W-1/W-2 根因，见 docs/competition/2026-tmall-hackathon/
/// 多端实测/web-round1.md）：`flutter_secure_storage` 的 web 实现存在并发写
/// 静默丢失缺陷——IndexedDB `user.box` 实证为空，`saveTokens` 的 4+ 个
/// write 全部丢失，token 从未持久化，导致 web 端登录 200 后会话断裂。
///
/// 平台后端（conditional import，先例：core/offline/local_database_store.dart）：
/// - `io`（Android / iOS / 桌面）：[SecureTokenStorage] 转发
///   FlutterSecureStorage（Keystore / Keychain），行为与旧实现一致；
/// - `web`：SharedPreferences（localStorage）。竞赛 / dev 场景可接受，
///   生产 web 应升级为加密方案（如 WebCrypto 派生密钥 + IndexedDB），
///   详见 token_storage_web.dart 头注释。
abstract class TokenStorage {
  /// 读取 [key] 对应的值；不存在时返回 null。
  Future<String?> read(String key);

  /// 写入 [key] = [value]（覆盖语义）。
  Future<void> write(String key, String value);

  /// 删除 [key]（不存在时为 no-op）。
  Future<void> delete(String key);
}

/// 平台后端工厂（由 io/web 变体提供 createTokenStorageImpl）。
TokenStorage createTokenStorage() => createTokenStorageImpl();

/// 全局 TokenStorage Provider。
///
/// 认证 token 的唯一持久化入口。`flutterSecureStorageProvider` 保留供
/// 未来非 token 的敏感小数据使用（当前无其他消费方）。
final tokenStorageProvider = Provider<TokenStorage>((ref) => createTokenStorage());
