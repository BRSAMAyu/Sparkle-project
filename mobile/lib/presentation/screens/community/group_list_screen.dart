import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';

class GroupListScreen extends ConsumerWidget {
  const GroupListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupsState = ref.watch(myGroupsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Community'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () {
              context.push('/community/groups/search');
            },
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          context.push('/community/groups/create');
        },
        icon: Icon(Icons.add),
        label: Text('Create'),
        backgroundColor: DS.primaryBase,
        elevation: 4,
      ),
      body: groupsState.when(
        data: (groups) {
          if (groups.isEmpty) {
            return Center(
              child: CompactEmptyState(
                message: 'You haven\'t joined any groups yet',
                icon: Icons.group_outlined,
                actionText: 'Discover Groups',
                onAction: () {
                  context.push('/community/groups/search');
                },
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.read(myGroupsProvider.notifier).refresh(),
            child: ListView.separated(
              padding: EdgeInsets.all(DS.spacing16),
              itemCount: groups.length,
              separatorBuilder: (context, index) =>
                  SizedBox(height: DS.spacing12),
              itemBuilder: (context, index) {
                final group = groups[index];
                return _AnimatedGroupTile(
                  group: group,
                  index: index,
                );
              },
            ),
          );
        },
        loading: () => const _GroupListLoading(),
        error: (error, stackTrace) => Center(
          child: CustomErrorWidget.page(
            message: error.toString(),
            onRetry: () {
              ref.read(myGroupsProvider.notifier).refresh();
            },
          ),
        ),
      ),
    );
  }
}

class _AnimatedGroupTile extends StatefulWidget {

  const _AnimatedGroupTile({required this.group, required this.index});
  final GroupListItem group;
  final int index;

  @override
  State<_AnimatedGroupTile> createState() => _AnimatedGroupTileState();
}

class _AnimatedGroupTileState extends State<_AnimatedGroupTile> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    
    // Stagger effect based on index
    final delay = Duration(milliseconds: widget.index * 50);
    Future.delayed(delay, () {
      if (mounted) _controller.forward();
    });

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );

    _slideAnimation = Tween<Offset>(begin: const Offset(0, 0.1), end: Offset.zero).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => FadeTransition(
      opacity: _fadeAnimation,
      child: SlideTransition(
        position: _slideAnimation,
        child: _GroupListTile(group: widget.group),
      ),
    );
}

class _GroupListTile extends StatelessWidget {

  const _GroupListTile({required this.group});
  final GroupListItem group;

  @override
  Widget build(BuildContext context) {
    final isSprint = group.isSprint;
    
    return DecoratedBox(
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        borderRadius: DS.borderRadius16,
        boxShadow: DS.shadowSm,
        border: Border.all(color: DS.neutral100),
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: DS.borderRadius16,
        child: InkWell(
          onTap: () {
            context.push('/community/groups/${group.id}');
          },
          borderRadius: DS.borderRadius16,
          splashColor: DS.primaryBase.withValues(alpha: 0.1),
          highlightColor: DS.primaryBase.withValues(alpha: 0.05),
          child: Padding(
            padding: EdgeInsets.all(DS.spacing16),
            child: Row(
              children: [
                // Avatar with Hero
                Hero(
                  tag: 'group-avatar-${group.id}',
                  child: Container(
                    width: 56,
                    height: 56,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: isSprint 
                          ? LinearGradient(colors: [DS.brandPrimary.shade100, DS.brandPrimary.shade50])
                          : LinearGradient(colors: [DS.brandPrimary.shade100, DS.brandPrimary.shade50]),
                      boxShadow: [
                         BoxShadow(
                           color: (isSprint ? DS.brandPrimary : DS.brandPrimary).withValues(alpha: 0.2),
                           blurRadius: 8,
                           offset: Offset(0, 4),
                         ),
                      ],
                    ),
                    child: Icon(
                       isSprint ? Icons.timer_outlined : Icons.school_outlined,
                       color: isSprint ? Colors.deepOrange : DS.brandPrimary.shade700,
                       size: 28,
                    ),
                  ),
                ),
                SizedBox(width: DS.spacing16),
                
                // Content
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              group.name,
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.bold,
                                    color: DS.neutral900,
                                  ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (isSprint && group.daysRemaining != null)
                             Container(
                               padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                               decoration: BoxDecoration(
                                 color: DS.error.shade50,
                                 borderRadius: BorderRadius.circular(8),
                               ),
                               child: Text(
                                 '${group.daysRemaining}d left',
                                 style: TextStyle(
                                   color: DS.error.shade700,
                                   fontSize: 10,
                                   fontWeight: FontWeight.bold,
                                 ),
                               ),
                             ),
                        ],
                      ),
                      SizedBox(height: 6),
                      Row(
                        children: [
                          _buildInfoBadge(
                            context, 
                            Icons.local_fire_department_rounded, 
                            '${group.totalFlamePower}',
                            DS.brandPrimary,
                          ),
                          SizedBox(width: DS.md),
                          _buildInfoBadge(
                            context,
                            Icons.people_alt_rounded,
                            '${group.memberCount}',
                            DS.brandPrimary,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                SizedBox(width: DS.sm),
                Icon(Icons.chevron_right, color: DS.neutral400),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInfoBadge(BuildContext context, IconData icon, String text, Color color) => Row(
      children: [
        Icon(icon, size: 14, color: color),
        SizedBox(width: DS.xs),
        Text(
          text,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: DS.neutral600,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
}

class _GroupListLoading extends StatelessWidget {
  const _GroupListLoading();

  @override
  Widget build(BuildContext context) => ListView.separated(
      padding: EdgeInsets.all(DS.spacing16),
      itemCount: 6,
      separatorBuilder: (context, index) => SizedBox(height: DS.spacing12),
      itemBuilder: (context, index) => Shimmer.fromColors(
          baseColor: DS.neutral200,
          highlightColor: DS.neutral100,
          child: Container(
            height: 88,
            decoration: BoxDecoration(
              color: DS.brandPrimaryConst,
              borderRadius: DS.borderRadius16,
            ),
          ),
        ),
    );
}
