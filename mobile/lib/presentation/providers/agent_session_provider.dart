import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/agent_session_store.dart';
import 'package:sparkle/presentation/providers/guest_provider.dart';

final agentSessionStoreProvider = Provider<AgentSessionStore>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return AgentSessionStore(prefs);
});
