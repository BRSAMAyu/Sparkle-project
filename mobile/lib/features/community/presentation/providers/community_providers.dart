import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/community/data/models/community_models.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';

// Feed State Controller
class FeedNotifier extends StateNotifier<AsyncValue<List<Post>>> {
  FeedNotifier(this._repository, this._currentUserId)
      : super(const AsyncValue.loading()) {
    unawaited(refresh());
  }
  final CommunityRepository _repository;
  final String? _currentUserId;

  String? _scope;
  int _currentPage = 1;
  bool _hasMore = true;
  bool _isLoadingMore = false;
  static const int _pageSize = 20;

  bool get hasMore => _hasMore;
  bool get isLoadingMore => _isLoadingMore;

  Future<void> refresh({String? scope, bool clearScope = false}) async {
    if (clearScope) {
      _scope = null;
    } else if (scope != null) {
      _scope = scope;
    }
    try {
      state = const AsyncValue.loading();
      _currentPage = 1;
      _hasMore = true;
      final posts = await _repository.getFeed(page: 1, scope: _scope);
      _hasMore = posts.length >= _pageSize;
      state = AsyncValue.data(posts);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> loadMore() async {
    if (_isLoadingMore || !_hasMore) return;

    final currentPosts = state.value ?? [];
    if (currentPosts.isEmpty) return;

    _isLoadingMore = true;
    final nextPage = _currentPage + 1;
    try {
      final morePosts = await _repository.getFeed(
        page: nextPage,
        scope: _scope,
      );
      if (morePosts.isEmpty) {
        _hasMore = false;
      } else {
        _currentPage = nextPage;
        _hasMore = morePosts.length >= _pageSize;
        state = AsyncValue.data([...currentPosts, ...morePosts]);
      }
    } catch (e) {
      // Silently fail on load-more to avoid disrupting the existing list
      debugPrint('FeedNotifier.loadMore failed: $e');
    } finally {
      _isLoadingMore = false;
    }
  }

  Future<void> toggleLike(String postId) async {
    final currentList = state.value ?? [];
    final idx = currentList.indexWhere((p) => p.id == postId);
    if (idx == -1) return;

    final post = currentList[idx];
    final bool wasLiked = post.isLiked;
    final int newCount = wasLiked ? post.likeCount - 1 : post.likeCount + 1;

    // Optimistic update
    state = AsyncValue.data([
      for (int i = 0; i < currentList.length; i++)
        if (i == idx)
          post.copyWith(likeCount: newCount, isLiked: !wasLiked)
        else
          currentList[i],
    ]);

    try {
      await _repository.likePost(postId, _currentUserId ?? '');
    } catch (_) {
      // Revert on failure
      state = AsyncValue.data(currentList);
    }
  }

  // Optimistic Update: Add post locally before sync
  Future<void> addPostOptimistically(
    String content,
    List<String> imageUrls,
    String topic,
  ) async {
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
      await Future<void>.delayed(const Duration(milliseconds: 500));
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
