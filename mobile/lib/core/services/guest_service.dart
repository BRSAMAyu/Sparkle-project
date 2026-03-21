import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

/// 访客服务 - 管理访客 ID 的持久化
///
/// 每台设备持久化一个唯一的访客 ID，确保 demo 数据与正式账号、
/// 以及不同设备上的访客数据彼此隔离。
class GuestService {
  GuestService(this._prefs) {
    // 初始化时从本地存储加载
    _cachedGuestId = _prefs.getString(_guestIdKey);
    _cachedNickname = _prefs.getString(_guestNicknameKey);
  }
  static const String _guestIdKey = 'guest_id';
  static const String _guestNicknameKey = 'guest_nickname';

  /// 旧版本曾使用固定访客 ID，需要迁移到设备唯一 ID
  static const String _wellKnownGuestId = 'guest_sparkle_demo_visitor';
  static const Uuid _uuid = Uuid();

  final SharedPreferences _prefs;
  String? _cachedGuestId;
  String? _cachedNickname;

  String _generateGuestId() => 'guest_${_uuid.v4().replaceAll('-', '').substring(0, 12)}';

  /// 获取访客 ID — 始终使用设备唯一 ID，确保数据隔离
  Future<String> getGuestId() async {
    // 迁移：旧版固定 demo 访客 ID 升级为当前设备唯一 ID
    if (_cachedGuestId != null && _cachedGuestId != _wellKnownGuestId) {
      return _cachedGuestId!;
    }

    final nextGuestId = _generateGuestId();
    await _prefs.setString(_guestIdKey, nextGuestId);
    _cachedGuestId = nextGuestId;

    return nextGuestId;
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
