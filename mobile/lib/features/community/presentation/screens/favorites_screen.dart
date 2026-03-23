import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';

// ─── Provider ────────────────────────────────────────────────────────────────

final favoritesProvider = StateNotifierProvider.autoDispose<FavoritesNotifier,
    AsyncValue<List<MessageFavoriteInfo>>>((ref) {
  return FavoritesNotifier(ref.watch(communityRepositoryProvider));
});

class FavoritesNotifier
    extends StateNotifier<AsyncValue<List<MessageFavoriteInfo>>> {
  FavoritesNotifier(this._repo) : super(const AsyncValue.loading()) {
    load();
  }

  final CommunityRepository _repo;

  Future<void> load({String? tag}) async {
    state = const AsyncValue.loading();
    try {
      final list = await _repo.getFavorites(tag: tag, limit: 50);
      state = AsyncValue.data(list);
    } catch (e, s) {
      state = AsyncValue.error(e, s);
    }
  }

  Future<void> remove(String favoriteId) async {
    await _repo.removeFavorite(favoriteId);
    state.whenData((list) {
      state = AsyncValue.data(list.where((f) => f.id != favoriteId).toList());
    });
  }
}

// ─── Screen ──────────────────────────────────────────────────────────────────

class FavoritesScreen extends ConsumerWidget {
  const FavoritesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(favoritesProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () =>
              context.canPop() ? context.pop() : context.go('/community'),
        ),
        title: const Text('我的收藏'),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(favoritesProvider.notifier).load(),
          ),
        ],
      ),
      child: state.when(
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('加载失败: $e', style: TextStyle(color: DS.error)),
              const SizedBox(height: DS.md),
              SparkleButton.primary(
                label: '重试',
                onPressed: () => ref.read(favoritesProvider.notifier).load(),
              ),
            ],
          ),
        ),
        data: (favorites) {
          if (favorites.isEmpty) {
            return const Center(
              child: CompactEmptyState(
                message: '暂无收藏消息',
                icon: Icons.bookmark_border,
              ),
            );
          }
          return ContentConstraint(
            child: ListView.separated(
              padding: const EdgeInsets.all(DS.spacing16),
              itemCount: favorites.length,
              separatorBuilder: (_, __) => const SizedBox(height: DS.spacing8),
              itemBuilder: (ctx, i) => SparkleStaggerItem(
                index: i,
                child: _FavoriteTile(favorite: favorites[i]),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _FavoriteTile extends ConsumerWidget {
  const _FavoriteTile({required this.favorite});
  final MessageFavoriteInfo favorite;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final content = favorite.groupMessage?.content ??
        favorite.privateMessage?.content ??
        '（富媒体消息）';
    final sender = favorite.groupMessage?.sender?.displayName ?? '未知用户';
    final dateStr = DateFormat('yyyy-MM-dd HH:mm').format(favorite.createdAt);

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: EdgeInsets.zero,
      child: ListTile(
        leading: Icon(Icons.bookmark, color: DS.brandPrimary),
        title: Text(
          content,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        subtitle: Text(
          '$sender · $dateStr',
          style: TextStyle(fontSize: DS.fontSizeXs, color: DS.neutral500),
        ),
        trailing: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: Icon(Icons.delete_outline, color: DS.error),
          onPressed: () async {
            final confirmed = await showSensoryDialog<bool>(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Text('取消收藏'),
                content: const Text('确定要取消收藏这条消息吗？'),
                actions: [
                  SparkleButton.ghost(
                    label: '取消',
                    onPressed: () => Navigator.pop(ctx, false),
                  ),
                  SparkleButton.primary(
                    label: '确定',
                    onPressed: () => Navigator.pop(ctx, true),
                  ),
                ],
              ),
            );
            if (confirmed ?? false) {
              unawaited(
                ref
                    .read(favoritesProvider.notifier)
                    .remove(favorite.id)
                    .then((_) {
                  if (!context.mounted) return;
                  AppFeedback.success(context, '已取消收藏');
                }).catchError((Object e) {
                  if (!context.mounted) return;
                  AppFeedback.error(context, '操作失败: $e');
                }),
              );
            }
          },
        ),
        onTap: () {
          if (favorite.note != null && favorite.note!.isNotEmpty) {
            showSensoryDialog<void>(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Text('收藏备注'),
                content: Text(favorite.note!),
                actions: [
                  SparkleButton.ghost(
                    label: '关闭',
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
            );
          }
        },
      ),
    );
  }
}
