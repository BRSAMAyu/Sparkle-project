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
