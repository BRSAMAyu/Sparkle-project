import 'package:shared_preferences/shared_preferences.dart';

import 'token_storage.dart';

/// Web 平台后端：SharedPreferences（落 localStorage）。
///
/// ⚠️ 安全边界：localStorage 无加密、可被同源脚本与用户工具直接读取。
/// 此实现用于修复 flutter_secure_storage web 并发写静默丢失导致的会话
/// 断链（web-round1 W-1/W-2，IndexedDB `user.box` 空盒实证），**竞赛 /
/// dev 场景可接受**；生产 web 应升级为加密方案（如 WebCrypto 派生密钥
/// + IndexedDB，或服务端 HttpOnly Cookie 会话），并迁移既有 key。
///
/// 语义与 TokenStorage 契约一致：read 未命中返回 null；write 覆盖；
/// delete 不存在时 no-op。
class TokenStorageWeb implements TokenStorage {
  Future<SharedPreferences> get _prefs => SharedPreferences.getInstance();

  @override
  Future<String?> read(String key) async {
    final prefs = await _prefs;
    return prefs.getString(key);
  }

  @override
  Future<void> write(String key, String value) async {
    final prefs = await _prefs;
    await prefs.setString(key, value);
  }

  @override
  Future<void> delete(String key) async {
    final prefs = await _prefs;
    await prefs.remove(key);
  }
}

TokenStorage createTokenStorageImpl() => TokenStorageWeb();
