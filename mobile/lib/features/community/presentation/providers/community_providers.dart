import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/models/community_models.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/data/repositories/community_share_repository.dart';

/// N34/N36：feed 页数据 + 溯源——[fromCache] 表示本次（或其中一页）来自
/// 本地快照回读，[asOf] 为数据时点戳，UI 据此挂「截至 X」stale 徽标。
class FeedPageData {
  const FeedPageData({
    required this.posts,
    this.fromCache = false,
    this.asOf,
  });

  final List<Post> posts;
  final bool fromCache;
  final DateTime? asOf;
}

// Feed State Controller
class FeedNotifier extends StateNotifier<AsyncValue<FeedPageData>> {
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
  bool _fromCache = false;
  DateTime? _asOf;
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
      // N34：缓存感知读——离线回读快照并带「截至 X」溯源。
      final result = await _repository.getFeedCached(scope: _scope);
      _hasMore = result.data.length >= _pageSize;
      _fromCache = result.fromCache;
      _asOf = result.asOf;
      state = AsyncValue.data(
        FeedPageData(
          posts: result.data,
          fromCache: result.fromCache,
          asOf: result.asOf,
        ),
      );
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> loadMore() async {
    if (_isLoadingMore || !_hasMore) return;

    final currentPosts = state.value?.posts ?? [];
    if (currentPosts.isEmpty) return;

    _isLoadingMore = true;
    final nextPage = _currentPage + 1;
    try {
      final result = await _repository.getFeedCached(
        page: nextPage,
        scope: _scope,
      );
      if (result.data.isEmpty) {
        _hasMore = false;
      } else {
        _currentPage = nextPage;
        _hasMore = result.data.length >= _pageSize;
        // N36：任一页来自快照即整体标记 stale，时点取更早者。
        if (result.fromCache) {
          _fromCache = true;
          final incoming = result.asOf;
          if (incoming != null && (_asOf == null || incoming.isBefore(_asOf!))) {
            _asOf = incoming;
          }
        }
        state = AsyncValue.data(
          FeedPageData(
            posts: [...currentPosts, ...result.data],
            fromCache: _fromCache,
            asOf: _asOf,
          ),
        );
      }
    } catch (e) {
      // Silently fail on load-more to avoid disrupting the existing list
      debugPrint('FeedNotifier.loadMore failed: $e');
    } finally {
      _isLoadingMore = false;
    }
  }

  Future<void> toggleLike(String postId) async {
    final currentList = state.value?.posts ?? [];
    final idx = currentList.indexWhere((p) => p.id == postId);
    if (idx == -1) return;

    final post = currentList[idx];
    final wasLiked = post.isLiked;
    final newCount = wasLiked ? post.likeCount - 1 : post.likeCount + 1;

    // Optimistic update
    state = AsyncValue.data(
      FeedPageData(
        posts: [
          for (int i = 0; i < currentList.length; i++)
            if (i == idx)
              post.copyWith(likeCount: newCount, isLiked: !wasLiked)
            else
              currentList[i],
        ],
        fromCache: _fromCache,
        asOf: _asOf,
      ),
    );

    try {
      await _repository.likePost(postId, _currentUserId ?? '');
    } catch (_) {
      // Revert on failure
      state = AsyncValue.data(
        FeedPageData(
          posts: currentList,
          fromCache: _fromCache,
          asOf: _asOf,
        ),
      );
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
    final currentList = state.value?.posts ?? [];
    state = AsyncValue.data(
      FeedPageData(
        posts: [tempPost, ...currentList],
        fromCache: _fromCache,
        asOf: _asOf,
      ),
    );

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
      state = AsyncValue.data(
        FeedPageData(
          posts: currentList,
          fromCache: _fromCache,
          asOf: _asOf,
        ),
      );
      rethrow;
    }
  }
}

final feedProvider =
    StateNotifierProvider<FeedNotifier, AsyncValue<FeedPageData>>((ref) {
  final repository = ref.watch(communityRepositoryProvider);
  final user = ref.watch(currentUserProvider);
  return FeedNotifier(repository, user?.id);
});

/// S-03 收敛：社群首页「成果反馈」段数据——伙伴共享 artifact（质量分排序）。
/// 真源是既有 `/community/resources` 读接口与 [CommunityShareRepository]，
/// 此前该表面无任何产品入口（SharedResourceCard 是孤儿组件），此处接回。
final sharedResourcesProvider =
    FutureProvider.autoDispose<List<SharedResourceInfo>>((ref) async {
  final repository = ref.watch(communityShareRepositoryProvider);
  return repository.fetchSharedResources(limit: 10);
});
