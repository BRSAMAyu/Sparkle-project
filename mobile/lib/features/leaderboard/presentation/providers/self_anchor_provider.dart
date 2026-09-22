import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/leaderboard/data/models/self_anchor_model.dart';
import 'package:sparkle/features/leaderboard/data/repositories/self_anchor_repository.dart';

/// D-COMM-1：自我 7 日锚视图 provider（只读快照，autoDispose，重进即重取）。
final selfAnchorRepositoryProvider = Provider<SelfAnchorRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return SelfAnchorRepository(apiClient);
});

class SelfAnchorNotifier extends AutoDisposeAsyncNotifier<SelfAnchorView> {
  @override
  Future<SelfAnchorView> build() => ref.watch(selfAnchorRepositoryProvider).getSelfAnchor();
}

final selfAnchorProvider = AsyncNotifierProvider.autoDispose<
    SelfAnchorNotifier, SelfAnchorView>(
  SelfAnchorNotifier.new,
);
