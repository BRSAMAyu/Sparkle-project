import 'dart:async';
import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// 聊天输入草稿的会话维度持久仓（N46 单机草稿令，A-SPEC8A 会话连续性改造 #1）。
///
/// 对标 Telegram「用户离开会话必须保留未发送草稿」的客户端义务（单机版，
/// 跨设备同步明确不做）。形制对齐同层 [AgentSessionStore]：shared_preferences
/// 键值仓、构造注入、`SharedPreferences.setMockInitialValues` 可测。
///
/// - 键：`chat_draft:<scope>:<conversationId>:<userId>`；会话尚未拿到
///   conversationId（首条消息未发出）时落 [`newConversationKey`] 兜底键。
/// - 防抖落盘：[scheduleSave] 每键 500ms 合并；[flush]/[save] 即时写。
/// - 清除：发送成功（输入框被清空）或会话删除时 [clear]。
/// - 容量上界：单草稿 ≤[maxDraftBytes] UTF-8 字节（超界截断保头部，切在
///   码点边界）；总量 ≤[maxEntries] 条，LRU 淘汰最久未用。
enum ChatDraftScope { chat, privateChat, groupChat }

class ChatDraftStore {
  ChatDraftStore(this._prefs);

  final SharedPreferences _prefs;

  static const String _keyPrefix = 'chat_draft:';
  static const String _lruIndexKey = 'chat_draft:@lru_index';

  /// conversationId 尚未生成（首条消息未发出）时的兜底会话段。
  static const String newConversationKey = '_new';

  /// 单草稿字节上界（4KB）。
  static const int maxDraftBytes = 4096;

  /// 草稿总条数上界，超出按 LRU 淘汰。
  static const int maxEntries = 100;

  /// 输入防抖窗口（N46：debounce ≤500ms）。
  static const Duration debounceDelay = Duration(milliseconds: 500);

  final Map<String, Timer> _pendingTimers = <String, Timer>{};

  // LRU 索引的读-改-写串行链，防并发交错丢更新。
  Future<void> _lruChain = Future<void>.value();

  /// 组装草稿存储键（各入口与测试共用，保证键口径单一）。
  static String buildKey({
    required ChatDraftScope scope,
    required String conversationId,
    required String userId,
  }) {
    final normalizedConversation = conversationId.trim().isEmpty
        ? newConversationKey
        : conversationId.trim();
    final normalizedUser = userId.trim().isEmpty ? 'anon' : userId.trim();
    return '$_keyPrefix${scope.name}:$normalizedConversation:$normalizedUser';
  }

  /// 防抖保存：文本为空视作用户已清空/已发送，立即删草稿。
  void scheduleSave({
    required ChatDraftScope scope,
    required String conversationId,
    required String userId,
    required String text,
  }) {
    final key = buildKey(
      scope: scope,
      conversationId: conversationId,
      userId: userId,
    );
    if (text.trim().isEmpty) {
      _pendingTimers.remove(key)?.cancel();
      unawaited(
        clear(
          scope: scope,
          conversationId: conversationId,
          userId: userId,
        ),
      );
      return;
    }
    _pendingTimers.remove(key)?.cancel();
    _pendingTimers[key] = Timer(debounceDelay, () {
      _pendingTimers.remove(key);
      unawaited(
        save(
          scope: scope,
          conversationId: conversationId,
          userId: userId,
          text: text,
        ),
      );
    });
  }

  /// 立即落盘（页面 dispose / 关键节点调用），取消未触发的防抖定时器。
  Future<void> flush({
    required ChatDraftScope scope,
    required String conversationId,
    required String userId,
    required String text,
  }) {
    final key = buildKey(
      scope: scope,
      conversationId: conversationId,
      userId: userId,
    );
    _pendingTimers.remove(key)?.cancel();
    if (text.trim().isEmpty) {
      return clear(
        scope: scope,
        conversationId: conversationId,
        userId: userId,
      );
    }
    return save(
      scope: scope,
      conversationId: conversationId,
      userId: userId,
      text: text,
    );
  }

  /// 取消某键尚未触发的防抖写入（归属切换/恢复覆盖前调用，防旧闭包回写）。
  void cancelScheduled({
    required ChatDraftScope scope,
    required String conversationId,
    required String userId,
  }) {
    final key = buildKey(
      scope: scope,
      conversationId: conversationId,
      userId: userId,
    );
    _pendingTimers.remove(key)?.cancel();
  }

  /// 保存草稿（截断到字节上界后写入并刷新 LRU）。
  Future<void> save({
    required ChatDraftScope scope,
    required String conversationId,
    required String userId,
    required String text,
  }) async {
    if (text.trim().isEmpty) {
      await clear(
        scope: scope,
        conversationId: conversationId,
        userId: userId,
      );
      return;
    }
    final prefs = _prefs;
    final key = buildKey(
      scope: scope,
      conversationId: conversationId,
      userId: userId,
    );
    await prefs.setString(key, _capToByteLimit(text));
    await _touchKey(key);
  }

  /// 读取草稿；不存在返回 null。读取同时刷新 LRU（最近使用）。
  Future<String?> load({
    required ChatDraftScope scope,
    required String conversationId,
    required String userId,
  }) async {
    final prefs = _prefs;
    final key = buildKey(
      scope: scope,
      conversationId: conversationId,
      userId: userId,
    );
    final value = prefs.getString(key);
    if (value == null) return null;
    await _touchKey(key);
    return value;
  }

  /// 删除草稿（发送成功、用户清空、会话删除三条路径共用）。
  Future<void> clear({
    required ChatDraftScope scope,
    required String conversationId,
    required String userId,
  }) async {
    final key = buildKey(
      scope: scope,
      conversationId: conversationId,
      userId: userId,
    );
    _pendingTimers.remove(key)?.cancel();
    final prefs = _prefs;
    await prefs.remove(key);
    await _removeFromIndex(key);
  }

  /// 截断到 [maxDraftBytes] 字节，回退扫描码点边界，避免截出非法 UTF-8。
  String _capToByteLimit(String text) {
    final bytes = utf8.encode(text);
    if (bytes.length <= maxDraftBytes) return text;
    var end = maxDraftBytes;
    while (end > 0 && (bytes[end] & 0xC0) == 0x80) {
      end--;
    }
    return utf8.decode(bytes.sublist(0, end));
  }

  /// 刷新键的 LRU 位次；超出 [maxEntries] 淘汰最久未用条目。
  Future<void> _touchKey(String key) {
    _lruChain = _lruChain.then((_) async {
      final prefs = _prefs;
      final keys = prefs.getStringList(_lruIndexKey) ?? <String>[];
      final refreshed = keys.where((candidate) => candidate != key).toList()
        ..add(key);
      var evicted = const <String>[];
      if (refreshed.length > maxEntries) {
        evicted = refreshed.sublist(0, refreshed.length - maxEntries);
      }
      await prefs.setStringList(_lruIndexKey, refreshed);
      for (final stale in evicted) {
        await prefs.remove(stale);
      }
    });
    return _lruChain;
  }

  Future<void> _removeFromIndex(String key) {
    _lruChain = _lruChain.then((_) async {
      final prefs = _prefs;
      final keys = prefs.getStringList(_lruIndexKey) ?? <String>[];
      if (!keys.contains(key)) return;
      keys.remove(key);
      await prefs.setStringList(_lruIndexKey, keys);
    });
    return _lruChain;
  }
}
