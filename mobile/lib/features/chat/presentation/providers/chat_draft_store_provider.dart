import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/services/chat_draft_store.dart';

/// N46 草稿仓 Provider（shared_preferences 经 main.dart override 注入）。
final chatDraftStoreProvider = Provider<ChatDraftStore>(
  (ref) => ChatDraftStore(ref.watch(sharedPreferencesProvider)),
);

/// 解析草稿键的 userId 段：登录用户用账号 id，游客回退 guestId（对齐
/// agent_session_store 的 userId 口径）；两者皆不可得时落 'anon'。
Future<String> resolveChatDraftUserId(WidgetRef ref) async {
  final user = ref.read(currentUserProvider);
  final userId = user?.id.trim();
  if (userId != null && userId.isNotEmpty) {
    return userId;
  }
  try {
    final guestId = await ref.read(guestServiceProvider).getGuestId();
    final normalized = guestId.trim();
    if (normalized.isNotEmpty) return normalized;
  } catch (_) {
    // 游客 id 不可得时退化为共享草稿段，不阻塞草稿链路。
  }
  return 'anon';
}
