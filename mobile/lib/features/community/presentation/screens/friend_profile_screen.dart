import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/shared/entities/user_brief.dart';

class FriendProfileScreen extends ConsumerStatefulWidget {
  const FriendProfileScreen({
    required this.userId,
    this.displayName,
    super.key,
  });
  final String userId;
  final String? displayName;

  @override
  ConsumerState<FriendProfileScreen> createState() =>
      _FriendProfileScreenState();
}

class _FriendProfileScreenState extends ConsumerState<FriendProfileScreen> {
  late Future<UserBrief> _profileFuture;

  @override
  void initState() {
    super.initState();
    _profileFuture =
        ref.read(communityRepositoryProvider).getUserProfile(widget.userId);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(widget.displayName ?? ''),
      ),
      child: FutureBuilder<UserBrief>(
        future: _profileFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.error_outline, color: DS.error, size: 48),
                  const SizedBox(height: DS.md),
                  Text(
                    'Failed to load profile',
                    style: theme.textTheme.bodyMedium
                        ?.copyWith(color: DS.textSecondary),
                  ),
                  const SizedBox(height: DS.md),
                  CustomButton.secondary(
                    text: 'Retry',
                    onPressed: () => setState(() {
                      _profileFuture = ref
                          .read(communityRepositoryProvider)
                          .getUserProfile(widget.userId);
                    }),
                  ),
                ],
              ),
            );
          }
          final user = snapshot.data!;
          return _buildContent(context, user);
        },
      ),
    );
  }

  Widget _buildContent(BuildContext context, UserBrief user) {
    final theme = Theme.of(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.all(DS.spacing24),
      child: Column(
        children: [
          const SizedBox(height: DS.spacing16),
          // Avatar
          DecoratedBox(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: DS.brandPrimaryConst, width: 3),
              boxShadow: DS.shadowMd,
            ),
            child: SparkleAvatar(
              radius: 48,
              url: user.avatarUrl,
              fallbackText: user.displayName,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          // Display name
          Text(
            user.displayName,
            style: theme.textTheme.headlineSmall
                ?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: DS.xs),
          // Username
          Text(
            '@${user.username}',
            style: theme.textTheme.bodyMedium
                ?.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing16),
          // Flame level badge
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.xs,
            ),
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: DS.brandPrimary.withValues(alpha: 0.3),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.local_fire_department,
                  size: 16,
                  color: DS.brandPrimaryConst,
                ),
                const SizedBox(width: DS.xs),
                Text(
                  'Flame Lv.${user.flameLevel}',
                  style: TextStyle(
                    color: DS.brandPrimaryConst,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing32),
          // Action buttons
          Row(
            children: [
              Expanded(
                child: CustomButton.primary(
                  text: 'Message',
                  icon: Icons.chat_bubble_outline,
                  onPressed: () {
                    context.push(
                      '/chat/private/${user.id}?name=${Uri.encodeComponent(user.displayName)}',
                    );
                  },
                ),
              ),
              const SizedBox(width: DS.md),
              Expanded(
                child: CustomButton.secondary(
                  text: 'Add Friend',
                  icon: Icons.person_add_outlined,
                  onPressed: () => _sendFriendRequest(context, user),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _sendFriendRequest(BuildContext context, UserBrief user) async {
    try {
      await ref
          .read(communityRepositoryProvider)
          .sendFriendRequest(user.id);
      if (context.mounted) {
        AppFeedback.success(context, 'Friend request sent!');
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, 'Failed to send request: $e');
      }
    }
  }
}
