import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';

final lastContextDecisionProvider = Provider<String?>((ref) {
  final chatState = ref.watch(chatProvider);
  final messages = chatState.messages;
  for (var i = messages.length - 1; i >= 0; i--) {
    final msg = messages[i];
    if (msg.role != MessageRole.assistant) continue;
    final raw = msg.rawMetadata;
    if (raw == null) continue;
    var receipt = raw['context_receipt'];
    if (receipt is String) {
      try {
        receipt = json.decode(receipt) as Map<String, dynamic>;
      } catch (_) {
        continue;
      }
    }
    if (receipt is Map<String, dynamic>) {
      return receipt['decision_reason'] as String? ??
          'Aurora · ${receipt['used_count'] ?? 0} source(s) used';
    }
  }
  return null;
});
