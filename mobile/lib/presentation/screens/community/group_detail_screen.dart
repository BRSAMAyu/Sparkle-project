import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/community/bonfire_widget.dart';

class GroupDetailScreen extends ConsumerWidget {

  const GroupDetailScreen({required this.groupId, super.key});
  final String groupId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupState = ref.watch(groupDetailProvider(groupId));

    return Scaffold(
      body: groupState.when(
        data: (group) => _buildContent(context, ref, group),
        loading: () => const _DetailLoading(),
        error: (e, s) => Scaffold(
          appBar: AppBar(),
          body: Center(
            child: CustomErrorWidget.page(
              message: e.toString(), 
              onRetry: () {
                ref.read(groupDetailProvider(groupId).notifier).refresh();
              },
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, WidgetRef ref, GroupInfo group) {
    final isMember = group.myRole != null;
    final isSprint = group.isSprint;
    final theme = Theme.of(context);

    return CustomScrollView(
      physics: const BouncingScrollPhysics(),
      slivers: [
        SliverAppBar(
          expandedHeight: 200.0,
          pinned: true,
          stretch: true,
          flexibleSpace: FlexibleSpaceBar(
            title: Text(
              group.name,
              style: TextStyle(
                color: DS.brandPrimaryConst,
                shadows: [Shadow(color: DS.brandPrimary45, blurRadius: 4)],
              ),
            ),
            background: DecoratedBox(
              decoration: BoxDecoration(
                gradient: isSprint 
                    ? LinearGradient(
                        colors: [Colors.deepOrange, DS.warningAccent],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : LinearGradient(
                        colors: [DS.primaryBase, DS.secondaryBase],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
              ),
              child: Center(
                child: Hero(
                  tag: 'group-avatar-${group.id}',
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 40),
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      color: DS.brandPrimary.withValues(alpha: 0.2),
                      shape: BoxShape.circle,
                      border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.5), width: 2),
                    ),
                    child: Icon(
                      isSprint ? Icons.timer_outlined : Icons.school_outlined,
                      size: 40,
                      color: DS.brandPrimaryConst,
                    ),
                  ),
                ),
              ),
            ),
          ),
          actions: [
            if (isMember)
              IconButton(
                icon: Icon(Icons.more_vert, color: DS.brandPrimary),
                onPressed: () => _showGroupOptions(context, ref, group),
              ),
          ],
        ),
        
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (group.isSprint && group.daysRemaining != null)
                  Center(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: DS.error.shade50,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: DS.error.shade100),
                      ),
                      child: Text(
                        'Sprint ends in ${group.daysRemaining} days',
                        style: TextStyle(
                          color: DS.error.shade700,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                
                const SizedBox(height: DS.xl),
                
                // Bonfire with fade-in animation
                TweenAnimationBuilder<double>(
                  tween: Tween(begin: 0.0, end: 1.0),
                  duration: const Duration(milliseconds: 800),
                  curve: Curves.easeOutBack,
                  builder: (context, value, child) => Transform.scale(
                      scale: value,
                      child: Opacity(opacity: value, child: child),
                    ),
                  child: Center(
                    child: BonfireWidget(
                      level: (group.totalFlamePower ~/ 1000 + 1).clamp(1, 5),
                      size: 140,
                    ),
                  ),
                ),

                const SizedBox(height: DS.xxl),

                // Stats Cards
                Row(
                  children: [
                    Expanded(child: _buildStatCard(context, 'Members', '${group.memberCount}/${group.maxMembers}', Icons.people)),
                    const SizedBox(width: DS.md),
                    Expanded(child: _buildStatCard(context, 'Total Flame', '${group.totalFlamePower}', Icons.local_fire_department)),
                    const SizedBox(width: DS.md),
                    Expanded(child: _buildStatCard(context, 'Check-ins', '${group.todayCheckinCount}', Icons.check_circle)),
                  ],
                ),

                const SizedBox(height: DS.xxl),

                // Description
                Text('About', style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: DS.sm),
                Text(
                  group.description ?? 'No description provided.',
                  style: theme.textTheme.bodyMedium?.copyWith(color: DS.neutral700, height: 1.5),
                ),

                const SizedBox(height: DS.xl),

                // Tags
                if (group.focusTags.isNotEmpty) ...[
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: group.focusTags.map((tag) => Chip(
                      label: Text(tag),
                      backgroundColor: DS.neutral100,
                      labelStyle: TextStyle(color: DS.neutral800),
                    ),).toList(),
                  ),
                  const SizedBox(height: DS.xxl),
                ],

                // Actions
                if (isMember) ...[
                  CustomButton.primary(
                    text: 'Enter Chat',
                    icon: Icons.chat_bubble_outline,
                    size: CustomButtonSize.large,
                    onPressed: () {
                      context.push('/community/groups/$groupId/chat');
                    },
                  ),
                  const SizedBox(height: DS.lg),
                  Row(
                    children: [
                      Expanded(
                        child: CustomButton.secondary(
                          text: 'Tasks',
                          icon: Icons.task_alt,
                          onPressed: () {
                            context.push('/community/groups/$groupId/tasks');
                          },
                        ),
                      ),
                      const SizedBox(width: DS.lg),
                      Expanded(
                        child: CustomButton.secondary(
                          text: 'Members',
                          icon: Icons.people_outline,
                          onPressed: () {
                            // TODO: Members list
                          },
                        ),
                      ),
                    ],
                  ),
                ] else ...[
                  CustomButton.primary(
                    text: 'Join Group',
                    onPressed: () async {
                      HapticFeedback.lightImpact();
                      try {
                        await ref.read(groupDetailProvider(groupId).notifier).joinGroup();
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Welcome to the group!'),
                              behavior: SnackBarBehavior.floating,
                            ),
                          );
                        }
                      } catch (e) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to join: $e')));
                        }
                      }
                    },
                  ),
                ],
                const SizedBox(height: 40),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard(BuildContext context, String label, String value, IconData icon) => Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        borderRadius: BorderRadius.circular(16),
        boxShadow: DS.shadowSm,
        border: Border.all(color: DS.neutral100),
      ),
      child: Column(
        children: [
          Icon(icon, color: DS.primaryBase, size: 24),
          const SizedBox(height: DS.sm),
          Text(
            value,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: DS.neutral900,
            ),
          ),
          const SizedBox(height: DS.xs),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: DS.neutral500,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );

  void _showGroupOptions(BuildContext context, WidgetRef ref, GroupInfo group) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => DecoratedBox(
        decoration: BoxDecoration(
          color: DS.brandPrimaryConst,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(top: 8, bottom: 20),
                decoration: BoxDecoration(
                  color: DS.neutral300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              ListTile(
                leading: Container(
                  padding: const EdgeInsets.all(DS.sm),
                  decoration: BoxDecoration(color: DS.error.shade50, shape: BoxShape.circle),
                  child: Icon(Icons.exit_to_app, color: DS.error.shade700, size: 20),
                ),
                title: Text('Leave Group', style: TextStyle(color: DS.error.shade700, fontWeight: FontWeight.bold)),
                onTap: () async {
                  Navigator.pop(context);
                  final confirm = await showDialog<bool>(
                    context: context,
                    builder: (context) => AlertDialog(
                      title: const Text('Leave Group?'),
                      content: const Text('Are you sure you want to leave this group?'),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
                        TextButton(
                          onPressed: () => Navigator.pop(context, true), 
                          style: TextButton.styleFrom(foregroundColor: DS.error),
                          child: const Text('Leave'),
                        ),
                      ],
                    ),
                  );
                  
                  if (confirm ?? false) {
                     try {
                      await ref.read(groupDetailProvider(groupId).notifier).leaveGroup();
                      if (context.mounted) context.pop();
                     } catch(e) {
                        // Handle error
                     }
                  }
                },
              ),
              const SizedBox(height: DS.lg),
            ],
          ),
        ),
      ),
    );
  }
}

class _DetailLoading extends StatelessWidget {
  const _DetailLoading();

  @override
  Widget build(BuildContext context) => Shimmer.fromColors(
      baseColor: DS.neutral200,
      highlightColor: DS.neutral100,
      child: Column(
        children: [
          Container(height: 200, color: DS.brandPrimary),
          Padding(
            padding: const EdgeInsets.all(DS.lg),
            child: Column(
              children: [
                Container(height: 20, width: 200, color: DS.brandPrimary),
                const SizedBox(height: 20),
                Row(
                  children: [
                    Expanded(child: Container(height: 80, color: DS.brandPrimary)),
                    const SizedBox(width: 10),
                    Expanded(child: Container(height: 80, color: DS.brandPrimary)),
                    const SizedBox(width: 10),
                    Expanded(child: Container(height: 80, color: DS.brandPrimary)),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
}
