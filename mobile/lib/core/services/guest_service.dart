import 'package:shared_preferences/shared_preferences.dart';

/// 访客服务 - 管理访客 ID 的持久化
///
/// 使用固定的访客 ID，这样所有设备的访客模式都共享同一个账户，
/// 确保体验数据一致，方便全功能验收。
class GuestService {
  GuestService(this._prefs) {
    // 初始化时从本地存储加载
    _cachedGuestId = _prefs.getString(_guestIdKey);
    _cachedNickname = _prefs.getString(_guestNicknameKey);
  }
  static const String _guestIdKey = 'guest_id';
  static const String _guestNicknameKey = 'guest_nickname';

  /// 固定的访客 ID，所有设备共享同一个访客账户
  static const String _wellKnownGuestId = 'guest_sparkle_demo_visitor';

  final SharedPreferences _prefs;
  String? _cachedGuestId;
  String? _cachedNickname;

  /// 获取访客 ID — 始终使用固定 ID，确保跨设备一致性
  Future<String> getGuestId() async {
    // 迁移：如果之前存了随机 UUID 的 guest_id，替换为固定 ID
    if (_cachedGuestId != null && _cachedGuestId != _wellKnownGuestId) {
      await _prefs.setString(_guestIdKey, _wellKnownGuestId);
      _cachedGuestId = _wellKnownGuestId;
    }

    if (_cachedGuestId != null) {
      return _cachedGuestId!;
    }

    await _prefs.setString(_guestIdKey, _wellKnownGuestId);
    _cachedGuestId = _wellKnownGuestId;

    return _wellKnownGuestId;
  }

  /// 获取访客昵称
  String getGuestNickname() {
    if (_cachedNickname != null) {
      return _cachedNickname!;
    }

    // 生成随机访客昵称
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final nickname = '访客${timestamp.toString().substring(7)}';
    return nickname;
  }

  /// 设置访客昵称
  Future<void> setGuestNickname(String nickname) async {
    await _prefs.setString(_guestNicknameKey, nickname);
    _cachedNickname = nickname;
  }

  /// 检查是否是访客模式
  bool get isGuestMode => _cachedGuestId != null;

  /// 清除访客数据（用户登录后调用）
  Future<void> clearGuestData() async {
    await _prefs.remove(_guestIdKey);
    await _prefs.remove(_guestNicknameKey);
    _cachedGuestId = null;
    _cachedNickname = null;
  }
}
