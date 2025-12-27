import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

/// 访客服务 - 管理访客 ID 的持久化
class GuestService {
  static const String _guestIdKey = 'guest_id';
  static const String _guestNicknameKey = 'guest_nickname';

  final SharedPreferences _prefs;
  String? _cachedGuestId;
  String? _cachedNickname;

  GuestService(this._prefs) {
    // 初始化时从本地存储加载
    _cachedGuestId = _prefs.getString(_guestIdKey);
    _cachedNickname = _prefs.getString(_guestNicknameKey);
  }

  /// 获取或生成访客 ID
  Future<String> getGuestId() async {
    if (_cachedGuestId != null) {
      return _cachedGuestId!;
    }

    // 生成新的访客 ID
    final uuid = const Uuid();
    final guestId = 'guest_${uuid.v4()}';

    await _prefs.setString(_guestIdKey, guestId);
    _cachedGuestId = guestId;

    return guestId;
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
