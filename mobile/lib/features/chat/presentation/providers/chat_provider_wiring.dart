part of 'chat_provider.dart';

// 3. Provider
//
// Core keepAlive providers: chat repository and chat state intentionally use
// non-autoDispose providers so tab switches do not tear down the active
// conversation, WebSocket context, or loaded history.
final chatRepositoryProvider = Provider<ChatRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ChatRepository(
    apiClient.dio,
    container: ref.container,
  );
});

/// 聊天缓存依赖缝隙（V3-FIX-549）。
///
/// 缺陷：GroupChatNotifier/PrivateChatNotifier 原先在字段初始化处直握
/// `ChatCacheService()` 单例工厂，社区群聊加载/合并链的缓存写是
/// fire-and-forget——testWidgets 的 FakeAsync 域拆除后，在途 Hive 写的
/// 续延闭包仍登记在已废弃 fake zone 的微任务队列里，永不再执行，
/// `StorageBackendVm.close()` 的 `_writeTask` 永不落定 → tearDownAll 的
/// `Hive.close()` 确定性悬挂（测试只能靠 3s 超时护栏掩蔽）。
///
/// 修法：缓存依赖改经此 provider 读取。默认返回同一 `ChatCacheService()`
/// 单例，生产路径零语义变化（缓存写保留）；测试可 override 为内存实现，
/// 使 FakeAsync 域内不再产生在途真实 Hive 写，收尾可等待。
final chatCacheServiceProvider =
    Provider<ChatCacheService>((ref) => ChatCacheService());

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>(
  (ref) => ChatNotifier(ref.watch(chatRepositoryProvider), ref),
);

class _Debouncer {
  _Debouncer(this.delay);
  final Duration delay;
  Timer? _timer;
  void Function()? _pendingAction;

  void run(void Function() action) {
    _timer?.cancel();
    _pendingAction = action;
    _timer = Timer(delay, () {
      _pendingAction = null;
      action();
    });
  }

  void flush(void Function() action) {
    _timer?.cancel();
    _pendingAction = null;
    action();
  }

  /// M6-09「流式取消=中断保留」：立即执行已调度但未触发的防抖动作，
  /// 使取消路径能拿到完整的已生成内容（而非 50ms 防抖窗口前的旧值）。
  void flushPending() {
    final action = _pendingAction;
    _pendingAction = null;
    _timer?.cancel();
    action?.call();
  }

  void cancel() {
    _timer?.cancel();
    _timer = null;
    _pendingAction = null;
  }
}
