import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';

final agentSessionStoreProvider = Provider<AgentSessionStore>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return AgentSessionStore(prefs);
});
