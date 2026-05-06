import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';

class BlockedUsersScreen extends ConsumerWidget {
  const BlockedUsersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final blockedState = ref.watch(blockedUsersProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(I18nService.instance.isChinese ? '黑名单用户' : 'Blocked Users'),
        backgroundColor: DS.surfacePrimary,
      ),
      child: blockedState.when(
        data: (users) {
          if (users.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.block_outlined, size: 64, color: DS.neutral300),
                  SizedBox(height: 16),
                  Text(
                    I18nService.instance.isChinese ? '暂无拉黑用户' : 'No blocked users',
                    style: TextStyle(
                        color: DS.neutral500, fontSize: DS.fontSizeBase,),
                  ),
                ],
              ),
            );
          }
          return ListView.builder(
            padding: const EdgeInsets.all(DS.spacing16),
            itemCount: users.length,
            itemBuilder: (ctx, i) {
              final block = users[i];
              return SparkleStaggerItem(
                index: i,
                child: _BlockedUserTile(blockInfo: block),
              );
            },
          );
        },
        loading: () => const SparkleListSkeleton(),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(I18nService.instance.isChinese ? '加载失败: $e' : 'Load failed: $e', style: TextStyle(color: DS.error)),
              SizedBox(height: 16),
              ElevatedButton(
                onPressed: () =>
                    ref.read(blockedUsersProvider.notifier).refresh(),
                child: Text(I18nService.instance.isChinese ? '重试' : 'Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BlockedUserTile extends ConsumerWidget {
  const _BlockedUserTile({required this.blockInfo});

  final BlockUserInfo blockInfo;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = blockInfo.blockedUser;

    return Card(
      margin: const EdgeInsets.only(bottom: DS.spacing12),
      child: ListTile(
        leading: SparkleAvatar(
          url: user.avatarUrl,
          fallbackText: user.nickname ?? user.username,
        ),
        title: Text(
          user.nickname ?? user.username,
          style: TextStyle(
            fontWeight: DS.fontWeightSemibold,
            color: DS.textPrimary,
          ),
        ),
        subtitle: blockInfo.reason != null
            ? Text(
                I18nService.instance.isChinese ? '原因: ${blockInfo.reason}' : 'Reason: ${blockInfo.reason}',
                style: TextStyle(
                  color: DS.textSecondary,
                  fontSize: DS.fontSizeSm,
                ),
              )
            : null,
        trailing: TextButton(
          onPressed: () => _handleUnblock(context, ref),
          style: TextButton.styleFrom(
            foregroundColor: DS.primaryBase,
          ),
          child: Text(I18nService.instance.isChinese ? '解除拉黑' : 'Unblock'),
        ),
      ),
    );
  }

  Future<void> _handleUnblock(BuildContext context, WidgetRef ref) async {
    final displayName =
        blockInfo.blockedUser.nickname ?? blockInfo.blockedUser.username;
    final confirmed = await showSensoryDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(I18nService.instance.isChinese ? '解除拉黑' : 'Unblock'),
        content: Text(I18nService.instance.isChinese
            ? '确定要解除对 $displayName 的拉黑吗？\n\n解除后对方可以重新发送好友请求和消息给您。'
            : 'Unblock $displayName?\n\nThey will be able to send friend requests and messages again.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(I18nService.instance.isChinese ? '取消' : 'Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: DS.primaryBase),
            child: Text(I18nService.instance.isChinese ? '确定' : 'Confirm'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      try {
        await ref
            .read(blockedUsersProvider.notifier)
            .unblockUser(blockInfo.blockedUser.id);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SparkleSnackBar.success(I18nService.instance.isChinese
                ? '已解除对 $displayName 的拉黑'
                : '$displayName unblocked'),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SparkleSnackBar.error(I18nService.instance.isChinese ? '操作失败: $e' : 'Operation failed: $e'),
          );
        }
      }
    }
  }
}
