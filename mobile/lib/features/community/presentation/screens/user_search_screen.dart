import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/shared/entities/user_brief.dart';

class UserSearchScreen extends ConsumerStatefulWidget {
  const UserSearchScreen({super.key});

  @override
  ConsumerState<UserSearchScreen> createState() => _UserSearchScreenState();
}

class _UserSearchScreenState extends ConsumerState<UserSearchScreen> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _handleSearch() {
    final query = _searchController.text.trim();
    if (query.isNotEmpty) {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
      ref.read(userSearchProvider.notifier).search(query);
    }
  }

  void _showUserOptions(UserBrief user) {
    unawaited(showSensoryModalBottomSheet<void>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: CircleAvatar(
                backgroundImage: user.avatarUrl != null
                    ? NetworkImage(user.avatarUrl!)
                    : null,
                child: user.avatarUrl == null
                    ? Text(user.displayName.substring(0, 1).toUpperCase())
                    : null,
              ),
              title: Text(user.displayName),
              subtitle: Text('@${user.username}'),
            ),
            const Divider(),
            ListTile(
              leading: Icon(Icons.person_add, color: DS.primaryBase),
              title: const Text('Send Friend Request'),
              onTap: () async {
                Navigator.pop(context);
                try {
                  await ref
                      .read(communityRepositoryProvider)
                      .sendFriendRequest(user.id);
                  if (mounted) {
                    AppFeedback.success(
                      context,
                      'Friend request sent to ${user.displayName}',
                    );
                  }
                } catch (e) {
                  if (mounted) {
                    AppFeedback.error(context, 'Failed to send request: $e');
                  }
                }
              },
            ),
            ListTile(
              leading: Icon(Icons.chat, color: DS.primaryBase),
              title: const Text('Send Message'),
              onTap: () {
                Navigator.pop(context);
                context.push(
                  '/chat/private/${user.id}?name=${Uri.encodeComponent(user.displayName)}',
                );
              },
            ),
            const SizedBox(height: DS.spacing8),
          ],
        ),
      ),
    ),);
  }

  @override
  Widget build(BuildContext context) {
    final searchState = ref.watch(userSearchProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: TextField(
          controller: _searchController,
          autofocus: true,
          decoration: InputDecoration(
            hintText: I18nService.instance.isChinese
                ? '按姓名或用户名搜索...'
                : 'Search users by name or username...',
            border: InputBorder.none,
            hintStyle: TextStyle(color: DS.textSecondary),
          ),
          style: TextStyle(color: DS.textPrimary),
          onSubmitted: (_) => _handleSearch(),
          textInputAction: TextInputAction.search,
        ),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.search),
            onPressed: _handleSearch,
          ),
        ],
      ),
      child: searchState.when(
        data: (users) {
          if (users.isEmpty) {
            return Center(
              child: CompactEmptyState(
                message: _searchController.text.isEmpty
                    ? I18nService.instance.isChinese
                        ? '按姓名或用户名搜索'
                        : 'Search for users by name or username'
                    : I18nService.instance.isChinese
                        ? '未找到用户'
                        : 'No users found',
                icon: Icons.search,
              ),
            );
          }
          return ContentConstraint(
            child: RefreshIndicator(
              onRefresh: () async {
                if (_searchController.text.isNotEmpty) {
                  _handleSearch();
                }
              },
              child: ListView.separated(
                padding: const EdgeInsets.all(DS.lg),
                itemCount: users.length,
                separatorBuilder: (context, index) =>
                    const SizedBox(height: DS.md),
                itemBuilder: (context, index) {
                  final user = users[index];
                  return SparkleStaggerItem(
                    index: index,
                    child: GraphiteCardSurface(
                      surfaceRole: SparkleSurfaceRole.card,
                      padding: EdgeInsets.zero,
                      child: ListTile(
                      leading: Stack(
                        children: [
                          CircleAvatar(
                            backgroundImage: user.avatarUrl != null
                                ? NetworkImage(user.avatarUrl!)
                                : null,
                            child: user.avatarUrl == null
                                ? Text(
                                    user.displayName
                                        .substring(0, 1)
                                        .toUpperCase(),
                                  )
                                : null,
                          ),
                          if (user.status == UserStatus.online)
                            Positioned(
                              right: 0,
                              bottom: 0,
                              child: Container(
                                width: 12,
                                height: 12,
                                decoration: BoxDecoration(
                                  color: DS.success,
                                  shape: BoxShape.circle,
                                  border: Border.all(
                                    color: DS.brandPrimaryConst,
                                    width: 2,
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                      title: Text(
                        user.displayName,
                        style: const TextStyle(fontWeight: DS.fontWeightMedium),
                      ),
                      subtitle: Text('@${user.username}'),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: DS.warning.shade100,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              'Lv.${user.flameLevel}',
                              style: TextStyle(
                                color: DS.warning.shade700,
                                fontSize: 12,
                                fontWeight: DS.fontWeightBold,
                              ),
                            ),
                          ),
                          const SizedBox(width: DS.sm),
                          Icon(Icons.chevron_right, color: DS.brandPrimary),
                        ],
                      ),
                      onTap: () {
                        unawaited(
                          SensoryFeedbackService.emit(
                            SensoryFeedbackEvent.selection,
                          ),
                        );
                        _showUserOptions(user);
                      },
                    ),
                    ),
                  );
                },
              ),
            ),
          );
        },
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, s) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 48, color: DS.error),
              const SizedBox(height: DS.lg),
              Text(I18nService.instance.isChinese ? '搜索失败，请检查网络后重试' : 'Search failed, check your network and retry', style: TextStyle(color: DS.textSecondary)),
              const SizedBox(height: DS.md),
              SparkleButton.primary(
                label: '重试',
                onPressed: _handleSearch,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
