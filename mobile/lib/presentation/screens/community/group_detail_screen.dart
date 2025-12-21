import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';
import 'package:sparkle/presentation/widgets/community/bonfire_widget.dart';

class GroupDetailScreen extends ConsumerWidget {
  final String groupId;

  const GroupDetailScreen({super.key, required this.groupId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupState = ref.watch(groupDetailProvider(groupId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Group Details'),
        actions: [
          groupState.maybeWhen(
            data: (group) => group.myRole != null 
              ? IconButton(
                  icon: const Icon(Icons.settings), 
                  onPressed: () {
                    // TODO: Group settings (leave, edit if owner)
                    _showGroupOptions(context, ref, group);
                  },
                )
              : const SizedBox.shrink(),
            orElse: () => const SizedBox.shrink(),
          ),
        ],
      ),
      body: groupState.when(
        data: (group) => _buildBody(context, ref, group),
        loading: () => const Center(child: LoadingIndicator.circular()),
        error: (e, s) => Center(child: CustomErrorWidget.page(message: e.toString(), onRetry: () {
          ref.read(groupDetailProvider(groupId).notifier).refresh();
        })),
      ),
    );
  }

  Widget _buildBody(BuildContext context, WidgetRef ref, GroupInfo group) {
    final isMember = group.myRole != null;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppDesignTokens.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Center(
            child: Column(
              children: [
                CircleAvatar(
                  radius: 40,
                  backgroundColor: group.isSprint ? Colors.orange.shade100 : Colors.blue.shade100,
                  child: Icon(
                    group.isSprint ? Icons.timer : Icons.school,
                    size: 40,
                    color: group.isSprint ? Colors.orange : Colors.blue,
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  group.name,
                  style: Theme.of(context).textTheme.headlineMedium,
                  textAlign: TextAlign.center,
                ),
                if (group.isSprint && group.daysRemaining != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 8.0),
                    child: Chip(
                      label: Text('${group.daysRemaining} days left'),
                      backgroundColor: Colors.red.shade50,
                      labelStyle: TextStyle(color: Colors.red.shade700),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          
          // Bonfire
          Center(
            child: BonfireWidget(
              level: (group.totalFlamePower ~/ 1000 + 1).clamp(1, 5),
            ),
          ),
          
          const SizedBox(height: 24),

          // Stats
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildStat('Members', '${group.memberCount}/${group.maxMembers}'),
              _buildStat('Flame', '${group.totalFlamePower}'),
              _buildStat('Check-ins', '${group.todayCheckinCount}'),
            ],
          ),
          const SizedBox(height: 24),

          // Description
          if (group.description != null) ...[
            Text('About', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(group.description!),
            const SizedBox(height: 24),
          ],

          // Tags
          if (group.focusTags.isNotEmpty) ...[
            Wrap(
              spacing: 8,
              children: group.focusTags.map((tag) => Chip(label: Text(tag))).toList(),
            ),
            const SizedBox(height: 24),
          ],

          // Actions
          if (isMember) ...[
            CustomButton.filled(
              text: 'Enter Chat',
              icon: Icons.chat_bubble,
              onPressed: () {
                context.push('/community/groups/$groupId/chat');
              },
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: CustomButton.outlined(
                    text: 'Tasks',
                    icon: Icons.check_circle_outline,
                    onPressed: () {
                      context.push('/community/groups/$groupId/tasks');
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: CustomButton.outlined(
                    text: 'Members',
                    icon: Icons.people_outline,
                    onPressed: () {
                      // TODO: Navigate to members list
                    },
                  ),
                ),
              ],
            ),
          ] else ...[
            CustomButton.filled(
              text: 'Join Group',
              onPressed: () async {
                try {
                  await ref.read(groupDetailProvider(groupId).notifier).joinGroup();
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Joined group!')));
                  }
                } catch (e) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to join: $e')));
                  }
                }
              },
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStat(String label, String value) {
    return Column(
      children: [
        Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        Text(label, style: const TextStyle(color: Colors.grey)),
      ],
    );
  }

  void _showGroupOptions(BuildContext context, WidgetRef ref, GroupInfo group) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.exit_to_app, color: Colors.red),
              title: const Text('Leave Group', style: TextStyle(color: Colors.red)),
              onTap: () async {
                Navigator.pop(context);
                final confirm = await showDialog<bool>(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: const Text('Leave Group?'),
                    content: const Text('Are you sure you want to leave this group?'),
                    actions: [
                      TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
                      TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Leave')),
                    ],
                  ),
                );
                
                if (confirm == true) {
                   try {
                    await ref.read(groupDetailProvider(groupId).notifier).leaveGroup();
                    if (context.mounted) {
                      context.pop(); // Go back to list
                    }
                   } catch(e) {
                      // Handle error
                   }
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}