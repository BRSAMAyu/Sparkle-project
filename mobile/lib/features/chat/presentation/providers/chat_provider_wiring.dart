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

  void run(void Function() action) {
    _timer?.cancel();
    _timer = Timer(delay, action);
  }

  void flush(void Function() action) {
    _timer?.cancel();
    action();
  }

  void cancel() {
    _timer?.cancel();
    _timer = null;
  }
}
