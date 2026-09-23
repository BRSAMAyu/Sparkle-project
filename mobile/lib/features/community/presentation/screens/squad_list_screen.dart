import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
// X3：时间格式唯一入口——截止日为纯日期展示位，走 formatSparkleDateOnly，
// 禁手工拼接 'y/m/d'（A-SPEC2 CO-G4）。
import 'package:sparkle/core/display/lexicon/date_formatting.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/squad_models.dart';
import 'package:sparkle/features/community/presentation/providers/squad_provider.dart';

/// D-COMM-3：冲刺小队列表屏（`GET /community/squads`）。
///
/// SPEC：必达项 2——① 我的小队列表（空态诚实：无小队 ≠ 报错，给组队引导）
/// ② 创建/加入入口（AppBar 次级动作，不占内容主面积）。
/// 唯一 accent（brandPrimary）；颜色/字号/间距全部走令牌，零字面量。
class SquadListScreen extends ConsumerWidget {
  const SquadListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final squadsAsync = ref.watch(squadListProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(context.l10n.squadTitle),
        actions: [
          // 必达项②：创建/加入入口（次级位置，空态时仍可达）。
          Tooltip(
            message: context.l10n.squadCreateEntry,
            child: SparkleIconButton(
              key: const ValueKey('squad-create-entry-button'),
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.add),
              onPressed: () => unawaited(_showCreateDialog(context, ref)),
            ),
          ),
          Tooltip(
            message: context.l10n.squadJoinEntry,
            child: SparkleIconButton(
              key: const ValueKey('squad-join-entry-button'),
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.group_add_outlined),
              onPressed: () => unawaited(_showJoinDialog(context, ref)),
            ),
          ),
        ],
      ),
      child: ContentConstraint(
        child: SparkleRefreshIndicator(
          onRefresh: () => ref.refresh(squadListProvider.future),
          child: squadsAsync.when(
            loading: () => const _StateFill(child: SparkleCardSkeleton()),
            error: (Object error, StackTrace stackTrace) => _StateFill(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: context.space.md),
                    child: CustomErrorWidget(
                      message: context.l10n.squadLoadFailed(error),
                    ),
                  ),
                  SizedBox(height: context.space.md),
                  SparkleButton(
                    key: const ValueKey('squad-list-retry-button'),
                    variant: ButtonVariant.outline,
                    label: context.l10n.squadRetry,
                    onPressed: () => ref.invalidate(squadListProvider),
                  ),
                ],
              ),
            ),
            data: (List<SquadListItem> squads) {
              if (squads.isEmpty) {
                // 空态诚实：无小队不是错误——给组队引导，不造假列表。
                return _StateFill(
                  child: EmptyState(
                    key: const ValueKey('squad-list-empty-state'),
                    icon: Icons.groups_outlined,
                    title: context.l10n.squadListEmptyTitle,
                    description: context.l10n.squadListEmptyDescription,
                    actionText: context.l10n.squadListEmptyAction,
                    onAction: () => unawaited(_showCreateDialog(context, ref)),
                  ),
                );
              }
              return ListView.builder(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: EdgeInsets.all(context.space.md),
                itemCount: squads.length,
                itemBuilder: (context, index) => Padding(
                  padding: EdgeInsets.only(bottom: context.space.sm),
                  child: _SquadListCard(
                    squad: squads[index],
                    onTap: () => unawaited(
                      context.push(
                        CommunityRoutes.squadDetailPath(squads[index].id),
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Future<void> _showCreateDialog(BuildContext context, WidgetRef ref) async {
    unawaited(
      SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen),
    );
    final created = await showDialog<bool>(
      context: context,
      builder: (_) => const _CreateSquadDialog(),
    );
    if (created ?? false) {
      ref.invalidate(squadListProvider);
    }
  }

  Future<void> _showJoinDialog(BuildContext context, WidgetRef ref) async {
    unawaited(
      SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen),
    );
    final joined = await showDialog<bool>(
      context: context,
      builder: (_) => const _JoinSquadDialog(),
    );
    if (joined ?? false) {
      ref.invalidate(squadListProvider);
    }
  }
}

class _SquadListCard extends StatelessWidget {
  const _SquadListCard({required this.squad, this.onTap});

  final SquadListItem squad;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;
    final daysRemaining = squad.daysRemaining;

    return GraphiteCardSurface(
      key: ValueKey('squad-list-card-${squad.id}'),
      surfaceRole: SparkleSurfaceRole.card,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(context.radius.md),
        child: Padding(
          padding: EdgeInsets.all(context.space.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      squad.name,
                      style:
                          typo.titleMedium.copyWith(color: colors.textPrimary),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (daysRemaining != null) ...[
                    SizedBox(width: context.space.sm),
                    Text(
                      context.l10n.squadDaysRemaining(daysRemaining),
                      style: typo.labelMedium
                          .copyWith(color: colors.textSecondary),
                    ),
                  ],
                ],
              ),
              if (squad.sprintGoal != null &&
                  squad.sprintGoal!.trim().isNotEmpty) ...[
                SizedBox(height: context.space.xs),
                Text(
                  squad.sprintGoal!,
                  style: typo.bodySmall.copyWith(color: colors.textSecondary),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              SizedBox(height: context.space.sm),
              // 人数为真源数字直显（member_count/max_members），不自算。
              Text(
                context.l10n.squadMembersCount(
                  squad.memberCount,
                  squad.maxMembers,
                ),
                style: typo.labelMedium.copyWith(color: colors.textTertiary),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 创建冲刺小队：名称必填、冲刺截止必填（后端契约），目标可选。
class _CreateSquadDialog extends ConsumerStatefulWidget {
  const _CreateSquadDialog();

  @override
  ConsumerState<_CreateSquadDialog> createState() => _CreateSquadDialogState();
}

class _CreateSquadDialogState extends ConsumerState<_CreateSquadDialog> {
  final _nameController = TextEditingController();
  final _goalController = TextEditingController();
  DateTime? _deadline;
  bool _submitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _nameController.dispose();
    _goalController.dispose();
    super.dispose();
  }

  Future<void> _pickDeadline() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: now.add(const Duration(days: 7)),
      firstDate: now,
      lastDate: now.add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() {
        // 截止取当日日末，保证「未来时间」语义（服务端会再校验）。
        _deadline = DateTime(picked.year, picked.month, picked.day, 23, 59);
      });
    }
  }

  Future<void> _submit() async {
    final l10n = context.l10n;
    final name = _nameController.text.trim();
    if (name.length < 2 || _deadline == null) {
      setState(() {
        _errorMessage = l10n.squadCreateInvalid;
      });
      return;
    }
    setState(() {
      _submitting = true;
      _errorMessage = null;
    });
    try {
      await ref.read(squadRepositoryProvider).createSquad(
            SquadCreateInput(
              name: name,
              sprintGoal: _goalController.text.trim(),
              deadline: _deadline!,
            ),
          );
      if (mounted) {
        AppFeedback.success(context, l10n.squadCreateSuccess);
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _submitting = false;
          _errorMessage = l10n.squadCreateFailed(error);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;
    final l10n = context.l10n;

    return AlertDialog(
      title: Text(l10n.squadCreateEntry),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              key: const ValueKey('squad-create-name-field'),
              controller: _nameController,
              decoration: InputDecoration(
                labelText: l10n.squadCreateNameLabel,
                hintText: l10n.squadCreateNameHint,
              ),
            ),
            SizedBox(height: context.space.sm),
            TextField(
              controller: _goalController,
              decoration: InputDecoration(
                labelText: l10n.squadCreateGoalLabel,
                hintText: l10n.squadCreateGoalHint,
              ),
            ),
            SizedBox(height: context.space.sm),
            // deadline 必填（后端契约：冲刺周期既是可见性窗口也是加入窗口）。
            InkWell(
              key: const ValueKey('squad-create-deadline-button'),
              onTap: () => unawaited(_pickDeadline()),
              borderRadius: BorderRadius.circular(context.radius.sm),
              child: InputDecorator(
                decoration: InputDecoration(
                  labelText: l10n.squadCreateDeadlineLabel,
                  suffixIcon: const Icon(Icons.calendar_today_outlined),
                ),
                child: Text(
                  _deadline == null
                      ? l10n.squadCreateDeadlinePick
                      : formatSparkleDateOnly(_deadline!, l10n),
                  style: typo.bodyMedium.copyWith(
                    color: _deadline == null
                        ? colors.textTertiary
                        : colors.textPrimary,
                  ),
                ),
              ),
            ),
            if (_errorMessage != null) ...[
              SizedBox(height: context.space.sm),
              Text(
                _errorMessage!,
                key: const ValueKey('squad-create-error-text'),
                style: typo.bodySmall.copyWith(color: colors.error),
              ),
            ],
          ],
        ),
      ),
      actions: [
        SparkleButton(
          variant: ButtonVariant.ghost,
          onPressed: () => Navigator.of(context).pop(false),
          disabled: _submitting,
          label: l10n.cancel,
        ),
        SparkleButton(
          key: const ValueKey('squad-create-submit-button'),
          onPressed: _submitting ? null : () => unawaited(_submit()),
          label: l10n.squadCreateSubmit,
        ),
      ],
    );
  }
}

/// 凭小队 ID 加入（分享链接/面对面口传场景的最小入口）。
class _JoinSquadDialog extends ConsumerStatefulWidget {
  const _JoinSquadDialog();

  @override
  ConsumerState<_JoinSquadDialog> createState() => _JoinSquadDialogState();
}

class _JoinSquadDialogState extends ConsumerState<_JoinSquadDialog> {
  final _idController = TextEditingController();
  bool _submitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _idController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final l10n = context.l10n;
    final groupId = _idController.text.trim();
    if (groupId.isEmpty) {
      setState(() {
        _errorMessage = l10n.squadJoinInvalid;
      });
      return;
    }
    setState(() {
      _submitting = true;
      _errorMessage = null;
    });
    try {
      await ref.read(squadRepositoryProvider).joinSquad(groupId);
      if (mounted) {
        AppFeedback.success(context, l10n.squadJoinSuccess);
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _submitting = false;
          _errorMessage = l10n.squadJoinFailed(error);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final l10n = context.l10n;

    return AlertDialog(
      title: Text(l10n.squadJoinEntry),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            key: const ValueKey('squad-join-id-field'),
            controller: _idController,
            decoration: InputDecoration(
              labelText: l10n.squadJoinIdLabel,
              hintText: l10n.squadJoinIdHint,
            ),
          ),
          if (_errorMessage != null) ...[
            SizedBox(height: context.space.sm),
            Text(
              _errorMessage!,
              style: context.typo.bodySmall.copyWith(color: colors.error),
            ),
          ],
        ],
      ),
      actions: [
        SparkleButton(
          variant: ButtonVariant.ghost,
          onPressed: () => Navigator.of(context).pop(false),
          disabled: _submitting,
          label: l10n.cancel,
        ),
        SparkleButton(
          onPressed: _submitting ? null : () => unawaited(_submit()),
          label: l10n.squadJoinSubmit,
        ),
      ],
    );
  }
}

/// 加载/错误/空态的满高可滚动填充（照 SelfAnchorScreen 同款结构）。
class _StateFill extends StatelessWidget {
  const _StateFill({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) => ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            SizedBox(
              height: constraints.maxHeight,
              child: child,
            ),
          ],
        ),
      );
}
