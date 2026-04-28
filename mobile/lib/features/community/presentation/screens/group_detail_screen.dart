import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/bonfire_widget.dart';
import 'package:sparkle/features/community/presentation/widgets/group_knowledge_base_view.dart';

enum _GroupDetailTab { overview, knowledgeBase }

class GroupDetailScreen extends ConsumerStatefulWidget {
  const GroupDetailScreen({required this.groupId, super.key});
  final String groupId;

  @override
  ConsumerState<GroupDetailScreen> createState() => _GroupDetailScreenState();
}

class _GroupDetailScreenState extends ConsumerState<GroupDetailScreen> {
  _GroupDetailTab _selectedTab = _GroupDetailTab.overview;

  @override
  Widget build(BuildContext context) {
    final groupState = ref.watch(groupDetailProvider(widget.groupId));

    return SparklePageScaffold(
      role: SparklePageRole.content,
      safeArea: false,
      child: groupState.when(
        data: (group) => _buildContent(context, ref, group),
        loading: () => const _DetailLoading(),
        error: (e, s) => SafeArea(
          child: Column(
            children: [
              AppBar(
                leading: SparkleIconButton(
                  icon: const Icon(Icons.arrow_back),
                  onPressed: () => context.pop(),
                ),
                title: Text('Group Details'),
              ),
              Expanded(
                child: Center(
                  child: CustomErrorWidget.page(
                    context: context,
                    message: e.toString(),
                    onRetry: () => unawaited(
                      ref
                          .read(groupDetailProvider(widget.groupId).notifier)
                          .refresh(),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, WidgetRef ref, GroupInfo group) =>
      ContentConstraint(
      child: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          _buildAppBar(context, ref, group),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing16,
                DS.spacing16,
                DS.spacing16,
                DS.spacing12,
              ),
              child: _GroupDetailTabs(
                selectedTab: _selectedTab,
                onChanged: (tab) => setState(() => _selectedTab = tab),
              ),
            ),
          ),
          if (_selectedTab == _GroupDetailTab.overview)
            SliverToBoxAdapter(
              child: _buildOverviewTab(context, ref, group),
            )
          else
            SliverFillRemaining(
              child: GroupKnowledgeBaseView(
                groupId: widget.groupId,
                currentUserRole: group.myRole,
              ),
            ),
        ],
      ),
      );

  SliverAppBar _buildAppBar(BuildContext context, WidgetRef ref, GroupInfo group) {
    final isMember = group.myRole != null;
    final isSprint = group.isSprint;

    return SliverAppBar(
      leading: SparkleIconButton(
        icon: const Icon(Icons.arrow_back),
        onPressed: () => context.pop(),
      ),
      expandedHeight: 200,
      pinned: true,
      stretch: true,
      backgroundColor: DS.surfaceOverlay.withValues(alpha: 0.94),
      flexibleSpace: FlexibleSpaceBar(
        title: Text(
          group.name,
          style: TextStyle(
            color: DS.textPrimary,
            shadows: [
              Shadow(
                color: Colors.black.withValues(alpha: 0.08),
                blurRadius: 8,
              ),
            ],
          ),
        ),
        background: DecoratedBox(
          decoration: BoxDecoration(
            gradient: isSprint
                ? LinearGradient(
                    colors: [
                      DS.surfaceRoleColor(SparkleSurfaceRole.accent),
                      DS.surfaceRoleColor(SparkleSurfaceRole.panel),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  )
                : LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      DS.surfacePrimary,
                      Color.lerp(DS.surfaceSecondary, DS.info, 0.04) ??
                          DS.surfaceSecondary,
                    ],
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
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      DS.brandPrimary.withValues(alpha: 0.16),
                      DS.info.withValues(alpha: 0.08),
                    ],
                  ),
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: DS.brandPrimary.withValues(alpha: 0.24),
                    width: 2,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: DS.brandPrimary.withValues(alpha: 0.1),
                      blurRadius: 18,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: Icon(
                  isSprint ? Icons.timer_outlined : Icons.school_outlined,
                  size: 40,
                  color: DS.textPrimary,
                ),
              ),
            ),
          ),
        ),
      ),
      actions: [
        if (isMember)
          SparkleIconButton(
            icon: Icon(Icons.more_vert, color: DS.textPrimary),
            onPressed: () => _showGroupOptions(context, ref, group),
          ),
      ],
    );
  }

  Widget _buildOverviewTab(BuildContext context, WidgetRef ref, GroupInfo group) {
    final isMember = group.myRole != null;
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (group.isSprint && group.daysRemaining != null)
            Center(
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      DS.error.withValues(alpha: 0.1),
                      DS.surfacePrimary,
                    ],
                  ),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: DS.error.withValues(alpha: 0.16),
                  ),
                ),
                child: Text(
                  '冲刺倒计时 ${group.daysRemaining} 天',
                  style: TextStyle(
                    color: DS.error,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          const SizedBox(height: DS.xl),
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
                showCrackleToggle: true,
              ),
            ),
          ),
          const SizedBox(height: DS.xxl),
          SparkleStaggerItem(
            index: 0,
            child: Row(
              children: [
                Expanded(
                  child: _buildStatCard(
                    context,
                    '成员',
                    '${group.memberCount}/${group.maxMembers}',
                    Icons.people,
                  ),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: _buildStatCard(
                    context,
                    '火力值',
                    '${group.totalFlamePower}',
                    Icons.local_fire_department,
                  ),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: _buildStatCard(
                    context,
                    '今日打卡',
                    '${group.todayCheckinCount}',
                    Icons.check_circle,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.xxl),
          Text(
            '关于',
            style: theme.textTheme.titleLarge
                ?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: DS.sm),
          Text(
            group.description ?? '暂无描述',
            style: theme.textTheme.bodyMedium
                ?.copyWith(color: DS.textSecondary, height: 1.6),
          ),
          const SizedBox(height: DS.xl),
          if (group.focusTags.isNotEmpty) ...[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: group.focusTags
                  .map(
                    (tag) => Chip(
                      label: Text(tag),
                      backgroundColor: Color.alphaBlend(
                        DS.info.withValues(alpha: 0.05),
                        DS.surfacePrimary,
                      ),
                      side: BorderSide(
                        color: DS.border.withValues(alpha: 0.45),
                      ),
                      labelStyle: TextStyle(color: DS.textPrimary),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: DS.xxl),
          ],
          Row(
            children: [
              Expanded(
                child: Text(
                  '公告',
                  style: theme.textTheme.titleLarge
                      ?.copyWith(fontWeight: FontWeight.bold),
                ),
              ),
              if (group.isAdmin)
                SparkleIconButton(
                  icon: const Icon(Icons.edit_outlined, size: 18),
                  onPressed: () => _showEditAnnouncementDialog(
                    context,
                    ref,
                    group,
                  ),
                ),
            ],
          ),
          const SizedBox(height: DS.sm),
          Text(
            group.announcement?.isNotEmpty ?? false ? group.announcement! : '暂无公告',
            style: theme.textTheme.bodyMedium
                ?.copyWith(color: DS.textSecondary, height: 1.6),
          ),
          const SizedBox(height: DS.xxl),
          if (isMember) ...[
            CustomButton.primary(
              text: '进入聊天',
              icon: Icons.chat_bubble_outline,
              size: CustomButtonSize.large,
              onPressed: () =>
                  unawaited(context.push('/chat/group/${widget.groupId}')),
            ),
            const SizedBox(height: DS.lg),
            Row(
              children: [
                Expanded(
                  child: CustomButton.secondary(
                    text: '任务',
                    icon: Icons.task_alt,
                    onPressed: () =>
                        unawaited(context.push('/community/groups/${widget.groupId}/tasks')),
                  ),
                ),
                const SizedBox(width: DS.lg),
                Expanded(
                  child: CustomButton.secondary(
                    text: '成员',
                    icon: Icons.people_outline,
                    onPressed: () => unawaited(
                      context.push(
                        '/community/groups/${widget.groupId}/members?name=${Uri.encodeComponent(group.name)}',
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.lg),
            CustomButton.secondary(
              text: '打开知识库',
              icon: Icons.auto_stories_outlined,
              onPressed: () =>
                  setState(() => _selectedTab = _GroupDetailTab.knowledgeBase),
            ),
          ] else ...[
            CustomButton.primary(
              text: '加入群组',
              onPressed: () async {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
                );
                try {
                  await ref
                      .read(groupDetailProvider(widget.groupId).notifier)
                      .joinGroup();
                  if (context.mounted) {
                    AppFeedback.success(context, 'Welcome to the group!');
                  }
                } catch (e) {
                  if (context.mounted) {
                    AppFeedback.error(context, '加入失败: $e');
                  }
                }
              },
            ),
          ],
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _buildStatCard(
    BuildContext context,
    String label,
    String value,
    IconData icon,
  ) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.spacing8),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(icon, color: DS.textSecondary, size: 20),
            ),
            const SizedBox(height: DS.sm),
            Text(
              value,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: DS.textPrimary,
              ),
            ),
            const SizedBox(height: DS.xs),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: DS.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );

  void _showGroupOptions(BuildContext context, WidgetRef ref, GroupInfo group) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (context) => GraphiteModalSurface(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: Container(
                  padding: const EdgeInsets.all(DS.sm),
                  decoration: BoxDecoration(
                    color: DS.surfaceSecondary,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: DS.error.withValues(alpha: 0.3),
                    ),
                  ),
                  child: Icon(
                    Icons.exit_to_app,
                    color: DS.error,
                    size: 20,
                  ),
                ),
                title: Text(
                  '离开群组',
                  style: TextStyle(
                    color: DS.error,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                onTap: () async {
                  Navigator.pop(context);
                  final confirm = await showSensoryDialog<bool>(
                    context: context,
                    builder: (context) => AlertDialog(
                      title: const Text('确认离开?'),
                      content: const Text('确定要离开这个群组吗？'),
                      actions: [
                        SparkleButton.ghost(
                          label: '取消',
                          onPressed: () => Navigator.pop(context, false),
                        ),
                        SparkleButton.destructive(
                          label: '离开',
                          onPressed: () => Navigator.pop(context, true),
                        ),
                      ],
                    ),
                  );

                  if (confirm ?? false) {
                    try {
                      await ref
                          .read(groupDetailProvider(widget.groupId).notifier)
                          .leaveGroup();
                      if (context.mounted) context.pop();
                    } catch (_) {}
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

  Future<void> _showEditAnnouncementDialog(
    BuildContext context,
    WidgetRef ref,
    GroupInfo group,
  ) async {
    final controller = TextEditingController(text: group.announcement ?? '');
    final result = await showSensoryDialog<String?>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: DS.surfacePrimary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: DS.border.withValues(alpha: 0.5)),
        ),
        title: const Text('编辑公告'),
        content: TextField(
          controller: controller,
          maxLines: 4,
          maxLength: 2000,
          decoration: const InputDecoration(
            hintText: '输入群组公告...',
          ),
        ),
        actions: [
          SparkleButton.ghost(
            label: '取消',
            onPressed: () => Navigator.pop(context),
          ),
          SparkleButton.primary(
            label: '保存',
            onPressed: () => Navigator.pop(context, controller.text.trim()),
          ),
        ],
      ),
    );
    controller.dispose();
    if (result == null) return;
    try {
      await ref
          .read(groupDetailProvider(widget.groupId).notifier)
          .updateAnnouncement(result.isEmpty ? null : result);
      if (context.mounted) AppFeedback.success(context, '公告已更新');
    } catch (e) {
      if (context.mounted) AppFeedback.error(context, '更新失败: $e');
    }
  }
}

class _GroupDetailTabs extends StatelessWidget {
  const _GroupDetailTabs({
    required this.selectedTab,
    required this.onChanged,
  });

  final _GroupDetailTab selectedTab;
  final ValueChanged<_GroupDetailTab> onChanged;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing4),
        decoration: BoxDecoration(
          color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          children: [
            Expanded(
              child: _TabButton(
                label: '概览',
                selected: selectedTab == _GroupDetailTab.overview,
                onTap: () => onChanged(_GroupDetailTab.overview),
              ),
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: _TabButton(
                label: '知识库',
                selected: selectedTab == _GroupDetailTab.knowledgeBase,
                onTap: () => onChanged(_GroupDetailTab.knowledgeBase),
              ),
            ),
          ],
        ),
      );
}

class _TabButton extends StatelessWidget {
  const _TabButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(14),
          child: Ink(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing12,
            ),
            decoration: BoxDecoration(
              color: selected ? DS.brandPrimary : Colors.transparent,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Center(
              child: Text(
                label,
                style: TextStyle(
                  fontWeight: DS.fontWeightSemiBold,
                  color: selected ? Colors.white : DS.textSecondary,
                ),
              ),
            ),
          ),
        ),
      );
}

class _DetailLoading extends StatelessWidget {
  const _DetailLoading();

  @override
  Widget build(BuildContext context) => Shimmer.fromColors(
        baseColor: DS.surfaceOverlay,
        highlightColor: DS.surfacePrimary,
        child: Column(
          children: [
            Container(height: 200, color: DS.surfaceOverlay),
            Padding(
              padding: const EdgeInsets.all(DS.lg),
              child: Column(
                children: [
                  Container(
                    height: 20,
                    width: 200,
                    decoration: BoxDecoration(
                      color: DS.surfaceOverlay,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      Expanded(
                        child: Container(
                          height: 80,
                          decoration: BoxDecoration(
                            color: DS.surfaceOverlay,
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Container(
                          height: 80,
                          decoration: BoxDecoration(
                            color: DS.surfaceOverlay,
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Container(
                          height: 80,
                          decoration: BoxDecoration(
                            color: DS.surfaceOverlay,
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}
