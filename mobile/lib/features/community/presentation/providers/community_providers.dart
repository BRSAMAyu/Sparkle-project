import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/community/data/models/community_models.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';

// Feed State Controller
class FeedNotifier extends StateNotifier<AsyncValue<List<Post>>> {
  FeedNotifier(this._repository, this._currentUserId)
      : super(const AsyncValue.loading()) {
    refresh();
  }
  final CommunityRepository _repository;
  final String? _currentUserId;

  Future<void> refresh() async {
    try {
      state = const AsyncValue.loading();
      final posts = await _repository.getFeed();
      state = AsyncValue.data(posts);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  // Optimistic Update: Add post locally before sync
  Future<void> addPostOptimistically(
      String content, List<String> imageUrls, String topic,) async {
    final currentUserId = _currentUserId;
    if (currentUserId == null) return;

    // 1. Create Temporary Post Object
    final tempPost = Post(
      id: 'temp-${DateTime.now().millisecondsSinceEpoch}',
      userId: currentUserId,
      content: content,
      imageUrls: imageUrls,
      topic: topic,
      createdAt: DateTime.now(),
      user: PostUser(
        id: currentUserId,
        username: 'You', // In a real app, grab from currentUserProvider
      ),
      isOptimistic: true,
    );

    // 2. Insert at top of list
    final currentList = state.value ?? [];
    state = AsyncValue.data([tempPost, ...currentList]);

    try {
      // 3. Perform Actual API Call
      await _repository.createPost(
        CreatePostRequest(
          userId: currentUserId,
          content: content,
          imageUrls: imageUrls,
          topic: topic,
        ),
      );

      // 4. Wait a bit for Worker to sync (Optional hack for MVP)
      // In a real CQRS app, we might just leave the optimistic one until next refresh
      // or listen to a WebSocket event that confirms creation.

      // For this demo, let's trigger a refresh after 500ms
      await Future.delayed(const Duration(milliseconds: 500));
      await refresh();
    } catch (e) {
      // Revert if failed
      state = AsyncValue.data(currentList);
      rethrow;
    }
  }
}

final feedProvider =
    StateNotifierProvider<FeedNotifier, AsyncValue<List<Post>>>((ref) {
  final repository = ref.watch(communityRepositoryProvider);
  final user = ref.watch(currentUserProvider);
  return FeedNotifier(repository, user?.id);
});
