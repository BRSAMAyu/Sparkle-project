import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
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
        title: Text(context.l10n.blockedUsersTitle),
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
                    context.l10n.blockedNoBlockedUsers,
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
              Text(context.l10n.favoritesLoadFailed(e), style: TextStyle(color: DS.error)),
              SizedBox(height: 16),
              ElevatedButton(
                onPressed: () =>
                    ref.read(blockedUsersProvider.notifier).refresh(),
                child: Text(context.l10n.favoritesRetry),
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
                context.l10n.blockedReason(blockInfo.reason ?? ''),
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
          child: Text(context.l10n.blockedUnblock),
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
        title: Text(context.l10n.blockedUnblockConfirmTitle),
        content: Text(context.l10n.blockedUnblockConfirmBody(displayName)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(context.l10n.blockedCancel),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: DS.primaryBase),
            child: Text(context.l10n.blockedConfirm),
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
            SparkleSnackBar.success(context.l10n.blockedUnblockedSuccess(displayName)),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SparkleSnackBar.error(context.l10n.blockedOperationFailed(e.toString())),
          );
        }
      }
    }
  }
}
