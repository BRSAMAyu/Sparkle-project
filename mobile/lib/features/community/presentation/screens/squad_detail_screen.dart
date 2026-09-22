import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/data/models/shared_error_models.dart';
import 'package:sparkle/features/community/data/models/squad_board_models.dart';
import 'package:sparkle/features/community/data/models/squad_models.dart';
import 'package:sparkle/features/community/data/models/study_room_models.dart';
import 'package:sparkle/features/community/presentation/providers/squad_provider.dart';
import 'package:sparkle/features/leaderboard/leaderboard_routes.dart';

/// D-COMM-4/5：冲刺小队详情屏（榜 + 自习室 + 错题分享段）。
///
/// SPEC v1.0：必达项 2（① 成员完成度榜——completion 百分比 + 并列名次
/// 1,1,3 如实渲染；<3 人降级 `self_view_only` → 切自我锚（既有路由）
/// ② 在室状态——显式进出按钮 + 今日累计 + 全员在场列表）。
/// 错题分享为详情内第三段（列表 + 诚实空态引导；分享动作在错题本，
/// 只传 error_id）。语义槽：在室 = success 在线语义、榜 = info 数据
/// 可视化；唯一交互 accent 不变；时长/完成度数字全部令牌样式。
///
/// 三段各自独立加载/错误面——单面失败不拖垮整屏（诚实且韧性）。
class SquadDetailScreen extends ConsumerWidget {
  const SquadDetailScreen({required this.groupId, super.key});

  final String groupId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(squadDetailProvider(groupId));
    final typo = context.typo;
    final colors = context.colors;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: detailAsync.whenOrNull(
              data: (SquadInfo squad) => Text(squad.name),
            ) ??
            Text(context.l10n.squadTitle),
      ),
      child: ContentConstraint(
        child: SparkleRefreshIndicator(
          onRefresh: () async {
            ref
              ..invalidate(squadDetailProvider(groupId))
              ..invalidate(squadLeaderboardProvider(groupId))
              ..invalidate(squadPresenceProvider(groupId))
              ..invalidate(squadMyRoomStatusProvider(groupId))
              ..invalidate(squadSharedErrorsProvider(groupId));
          },
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: EdgeInsets.all(context.space.md),
            children: [
              detailAsync.when(
                loading: () => const Padding(
                  padding: EdgeInsets.symmetric(vertical: 24),
                  child: SparkleCardSkeleton(),
                ),
                error: (Object error, StackTrace stackTrace) =>
                    _SectionErrorCard(
                  message: context.l10n.squadLoadFailed(error),
                  onRetry: () => ref.invalidate(squadDetailProvider(groupId)),
                ),
                data: (SquadInfo squad) => _SquadMetaHeader(squad: squad),
              ),
              SizedBox(height: context.space.md),
              _LeaderboardCard(groupId: groupId),
              SizedBox(height: context.space.md),
              _StudyRoomCard(groupId: groupId),
              SizedBox(height: context.space.md),
              _SharedErrorsSection(groupId: groupId),
              SizedBox(height: context.space.md),
              Text(
                context.l10n.squadDetailFootnote,
                style: typo.labelSmall.copyWith(color: colors.textTertiary),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 定位性元信息行（成员规模 / 剩余天数 / 目标）——非必达项，不占卡片主面积。
class _SquadMetaHeader extends StatelessWidget {
  const _SquadMetaHeader({required this.squad});

  final SquadInfo squad;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;
    final daysRemaining = squad.daysRemaining;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              context.l10n.squadMembersCount(
                squad.memberCount,
                squad.maxMembers,
              ),
              style: typo.labelLarge.copyWith(color: colors.textSecondary),
            ),
            if (daysRemaining != null) ...[
              SizedBox(width: context.space.md),
              Text(
                context.l10n.squadDaysRemaining(daysRemaining),
                style: typo.labelLarge.copyWith(color: colors.textSecondary),
              ),
            ],
          ],
        ),
        if (sprintGoalText != null) ...[
          SizedBox(height: context.space.xs),
          Text(
            sprintGoalText!,
            style: typo.bodySmall.copyWith(color: colors.textTertiary),
          ),
        ],
      ],
    );
  }

  String? get sprintGoalText {
    final goal = squad.sprintGoal?.trim();
    return (goal == null || goal.isEmpty) ? null : goal;
  }
}

/// 必达项①：成员完成度榜（info 数据可视化语义；并列名次 1,1,3 如实）。
///
/// 降级裁决：`self_view_only`（<3 人）→ 榜不成立——给降级提示 +
/// 「查看自我锚」按钮（既有路由 `/leaderboards/self-anchor`），不渲染残缺榜。
class _LeaderboardCard extends ConsumerWidget {
  const _LeaderboardCard({required this.groupId});

  final String groupId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final boardAsync = ref.watch(squadLeaderboardProvider(groupId));
    final colors = context.colors;
    final typo = context.typo;

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Padding(
        padding: EdgeInsets.all(context.space.md),
        child: boardAsync.when(
          loading: () => const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: SparkleCardSkeleton(),
          ),
          error: (Object error, StackTrace stackTrace) => _SectionErrorBody(
            message: context.l10n.squadBoardLoadFailed(error),
            onRetry: () => ref.invalidate(squadLeaderboardProvider(groupId)),
          ),
          data: (SquadLeaderboard board) {
            if (board.selfViewOnly || !board.boardValid) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _sectionTitle(
                    context,
                    icon: Icons.leaderboard_outlined,
                    color: colors.info,
                    title: context.l10n.squadDetailLeaderboardTitle,
                  ),
                  SizedBox(height: context.space.sm),
                  Text(
                    context.l10n.squadDetailLeaderboardDegraded,
                    style:
                        typo.bodyMedium.copyWith(color: colors.textSecondary),
                  ),
                  SizedBox(height: context.space.md),
                  SparkleButton(
                    key: const ValueKey('squad-degrade-self-anchor-button'),
                    variant: ButtonVariant.outline,
                    label: context.l10n.squadDetailLeaderboardSelfAnchorAction,
                    onPressed: () => unawaited(
                      context.push(LeaderboardRoutes.selfAnchor),
                    ),
                  ),
                ],
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _sectionTitle(
                  context,
                  icon: Icons.leaderboard_outlined,
                  color: colors.info,
                  title: context.l10n.squadDetailLeaderboardTitle,
                ),
                SizedBox(height: context.space.sm),
                for (var i = 0; i < board.entries.length; i++)
                  _LeaderboardRow(
                    entry: board.entries[i],
                    isLast: i == board.entries.length - 1,
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}

/// 单行榜条目：名次直显后端并列名次（1,1,3 不重排）；
/// has_ledger_data=false 如实显示「无账本数据」，不把 0 伪装成 0%。
class _LeaderboardRow extends StatelessWidget {
  const _LeaderboardRow({required this.entry, required this.isLast});

  final SquadLeaderboardEntry entry;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;
    final name = entry.displayName;

    return Column(
      children: [
        Row(
          children: [
            SizedBox(
              width: context.space.xl + context.space.lg,
              child: Text(
                '${entry.rank}',
                key: ValueKey('squad-leaderboard-rank-${entry.userId}'),
                style: typo.titleMedium.copyWith(color: colors.info),
              ),
            ),
            Expanded(
              child: Text(
                (name == null || name.trim().isEmpty)
                    ? context.l10n.squadMemberFallbackName
                    : name,
                style: typo.bodyMedium.copyWith(color: colors.textPrimary),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (entry.hasLedgerData)
              Text(
                context.l10n.squadCompletionPercent(
                  (entry.completionRate * 100).round(),
                ),
                key: ValueKey('squad-leaderboard-rate-${entry.userId}'),
                style: typo.labelLarge.copyWith(color: colors.textSecondary),
              )
            else
              Text(
                context.l10n.squadNoLedgerData,
                style: typo.labelMedium.copyWith(color: colors.textTertiary),
              ),
          ],
        ),
        if (!isLast) ...[
          SizedBox(height: context.space.sm),
          Divider(height: 1, color: colors.neutralOutline),
          SizedBox(height: context.space.sm),
        ],
      ],
    );
  }
}

/// 必达项②：自习室（在室 = success 在线语义；显式进出 + 今日累计）。
class _StudyRoomCard extends ConsumerStatefulWidget {
  const _StudyRoomCard({required this.groupId});

  final String groupId;

  @override
  ConsumerState<_StudyRoomCard> createState() => _StudyRoomCardState();
}

class _StudyRoomCardState extends ConsumerState<_StudyRoomCard> {
  bool _actionInFlight = false;

  Future<void> _toggleRoom(bool enter) async {
    if (_actionInFlight) {
      return;
    }
    setState(() {
      _actionInFlight = true;
    });
    try {
      final repository = ref.read(squadRepositoryProvider);
      if (enter) {
        await repository.enterStudyRoom(widget.groupId);
      } else {
        await repository.exitStudyRoom(widget.groupId);
      }
      ref
        ..invalidate(squadMyRoomStatusProvider(widget.groupId))
        ..invalidate(squadPresenceProvider(widget.groupId));
    } catch (error) {
      if (mounted) {
        AppFeedback.error(
          context,
          context.l10n.squadActionFailed(error),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _actionInFlight = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final myStatusAsync = ref.watch(squadMyRoomStatusProvider(widget.groupId));
    final presenceAsync = ref.watch(squadPresenceProvider(widget.groupId));
    final colors = context.colors;
    final typo = context.typo;

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Padding(
        padding: EdgeInsets.all(context.space.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: _sectionTitle(
                    context,
                    icon: Icons.self_improvement,
                    color: colors.success,
                    title: context.l10n.squadDetailStudyRoomTitle,
                  ),
                ),
                presenceAsync.whenOrNull(
                      data: (StudyRoomPresence presence) => Text(
                        context.l10n
                            .squadDetailPresenceInRoom(presence.inRoomCount),
                        style: typo.labelMedium
                            .copyWith(color: colors.textSecondary),
                      ),
                    ) ??
                    const SizedBox.shrink(),
              ],
            ),
            SizedBox(height: context.space.md),
            // 本人状态（心跳诚实上报：不在场不自动重开，进出以按钮为准）。
            myStatusAsync.when(
              loading: () => const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: SparkleCardSkeleton(),
              ),
              error: (Object error, StackTrace stackTrace) => _SectionErrorBody(
                message: context.l10n.squadRoomStatusLoadFailed(error),
                onRetry: () =>
                    ref.invalidate(squadMyRoomStatusProvider(widget.groupId)),
              ),
              data: (StudyRoomMyStatus status) => Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      _RoomStatusPill(inRoom: status.inRoom),
                      SizedBox(width: context.space.md),
                      Expanded(
                        child: Text(
                          context.l10n.squadDetailStudyRoomTodayMinutes(
                            status.todayMinutes,
                          ),
                          style: typo.bodyMedium
                              .copyWith(color: colors.textSecondary),
                        ),
                      ),
                      SparkleButton(
                        key: ValueKey(
                          status.inRoom
                              ? 'squad-study-room-exit-button'
                              : 'squad-study-room-enter-button',
                        ),
                        variant: status.inRoom
                            ? ButtonVariant.outline
                            : ButtonVariant.primary,
                        label: status.inRoom
                            ? context.l10n.squadDetailStudyRoomExit
                            : context.l10n.squadDetailStudyRoomEnter,
                        onPressed: _actionInFlight
                            ? null
                            : () => unawaited(
                                  _toggleRoom(!status.inRoom),
                                ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            SizedBox(height: context.space.md),
            // 全员在场列表（未入场成员如实列 0，不惩罚缺席）。
            presenceAsync.when(
              loading: () => const SizedBox.shrink(),
              error: (Object error, StackTrace stackTrace) => Text(
                context.l10n.squadPresenceLoadFailed(error),
                style: typo.labelSmall.copyWith(color: colors.textTertiary),
              ),
              data: (StudyRoomPresence presence) => Column(
                children: [
                  for (var i = 0; i < presence.members.length; i++)
                    _PresenceRow(
                      entry: presence.members[i],
                      isLast: i == presence.members.length - 1,
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 在室状态徽标：success 语义（在线），心跳滞后只作弱提示不降级。
class _RoomStatusPill extends StatelessWidget {
  const _RoomStatusPill({required this.inRoom});

  final bool inRoom;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;
    final color = inRoom ? colors.success : colors.textTertiary;

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: context.space.sm,
        vertical: context.space.xs,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(context.radius.full),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: context.space.sm,
            height: context.space.sm,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          SizedBox(width: context.space.xs),
          Text(
            inRoom
                ? context.l10n.squadDetailStudyRoomInRoom
                : context.l10n.squadDetailStudyRoomNotInRoom,
            style: typo.labelMedium.copyWith(color: color),
          ),
        ],
      ),
    );
  }
}

class _PresenceRow extends StatelessWidget {
  const _PresenceRow({required this.entry, required this.isLast});

  final StudyRoomPresenceEntry entry;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;
    final name = entry.displayName;
    final statusColor = entry.inRoom ? colors.success : colors.neutralOutline;

    return Column(
      children: [
        Row(
          children: [
            Container(
              width: context.space.sm,
              height: context.space.sm,
              decoration: BoxDecoration(
                color: statusColor,
                shape: BoxShape.circle,
              ),
            ),
            SizedBox(width: context.space.sm),
            Expanded(
              child: Row(
                children: [
                  Flexible(
                    child: Text(
                      (name == null || name.trim().isEmpty)
                          ? context.l10n.squadMemberFallbackName
                          : name,
                      style:
                          typo.bodyMedium.copyWith(color: colors.textPrimary),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (entry.isStale) ...[
                    SizedBox(width: context.space.xs),
                    Tooltip(
                      message: context.l10n.squadDetailPresenceStaleHint,
                      child: Icon(
                        Icons.schedule,
                        size: typo.labelMedium.fontSize ?? 12,
                        color: colors.textTertiary,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            Text(
              context.l10n.squadDetailStudyRoomTodayMinutes(entry.todayMinutes),
              style: typo.labelMedium.copyWith(color: colors.textSecondary),
            ),
          ],
        ),
        if (!isLast) ...[
          SizedBox(height: context.space.sm),
          Divider(height: 1, color: colors.neutralOutline),
          SizedBox(height: context.space.sm),
        ],
      ],
    );
  }
}

/// 错题分享段（D-COMM-5 列表面）：白名单投影如实渲染——题目/知识点/
/// 掌握度快照；**无答案字段可渲染**（契约即不含答案，绝不造占位）。
/// 分享动作入口在错题本详情（只传 error_id）。
class _SharedErrorsSection extends ConsumerWidget {
  const _SharedErrorsSection({required this.groupId});

  final String groupId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sharedAsync = ref.watch(squadSharedErrorsProvider(groupId));
    final colors = context.colors;
    final typo = context.typo;

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Padding(
        padding: EdgeInsets.all(context.space.md),
        child: sharedAsync.when(
          loading: () => const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: SparkleCardSkeleton(),
          ),
          error: (Object error, StackTrace stackTrace) => _SectionErrorBody(
            message: context.l10n.squadSharedErrorsLoadFailed(error),
            onRetry: () => ref.invalidate(squadSharedErrorsProvider(groupId)),
          ),
          data: (SharedErrorList list) {
            if (list.items.isEmpty) {
              // 空态诚实：没有分享 ≠ 报错——引导去错题本。
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _sectionTitle(
                    context,
                    icon: Icons.share_outlined,
                    color: colors.info,
                    title: context.l10n.squadDetailSharedErrorsTitle,
                  ),
                  SizedBox(height: context.space.sm),
                  Text(
                    context.l10n.squadDetailSharedErrorsEmpty,
                    style: typo.bodyMedium.copyWith(
                      color: colors.textSecondary,
                    ),
                  ),
                  SizedBox(height: context.space.md),
                  SparkleButton(
                    variant: ButtonVariant.outline,
                    label: context.l10n.squadDetailSharedErrorsGoBook,
                    onPressed: () => unawaited(context.push('/errors')),
                  ),
                ],
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _sectionTitle(
                  context,
                  icon: Icons.share_outlined,
                  color: colors.info,
                  title: context.l10n.squadDetailSharedErrorsTitle,
                ),
                SizedBox(height: context.space.sm),
                for (var i = 0; i < list.items.length; i++)
                  _SharedErrorCard(
                    entry: list.items[i],
                    isLast: i == list.items.length - 1,
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _SharedErrorCard extends StatelessWidget {
  const _SharedErrorCard({required this.entry, required this.isLast});

  final SharedErrorEntry entry;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;
    final sharer = entry.sharerName;
    final note = entry.note;
    final rootCause = entry.rootCause;
    final knowledgeNames = entry.knowledgeNodes.map((n) => n.name).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                (sharer == null || sharer.trim().isEmpty)
                    ? context.l10n.squadMemberFallbackName
                    : context.l10n.squadSharedErrorBy(sharer),
                style: typo.labelLarge.copyWith(color: colors.textPrimary),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            Text(
              context.l10n
                  .squadCompletionPercent((entry.masteryLevel * 100).round()),
              style: typo.labelMedium.copyWith(color: colors.textSecondary),
            ),
          ],
        ),
        // 题目文本可空（图片题等）：不渲染该行，不造占位。
        if (entry.questionText != null &&
            entry.questionText!.trim().isNotEmpty) ...[
          SizedBox(height: context.space.xs),
          Text(
            entry.questionText!,
            style: typo.bodyMedium.copyWith(color: colors.textPrimary),
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
          ),
        ],
        if (knowledgeNames.isNotEmpty) ...[
          SizedBox(height: context.space.xs),
          Text(
            knowledgeNames.join(' · '),
            style: typo.labelSmall.copyWith(color: colors.info),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
        if (rootCause != null && rootCause.trim().isNotEmpty) ...[
          SizedBox(height: context.space.xs),
          Text(
            rootCause,
            style: typo.bodySmall.copyWith(color: colors.textSecondary),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
        if (note != null && note.trim().isNotEmpty) ...[
          SizedBox(height: context.space.xs),
          Text(
            note,
            style: typo.bodySmall.copyWith(
              color: colors.textSecondary,
              fontStyle: FontStyle.italic,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
        if (!isLast) ...[
          SizedBox(height: context.space.md),
          Divider(height: 1, color: colors.neutralOutline),
        ],
        SizedBox(height: context.space.md),
      ],
    );
  }
}

Widget _sectionTitle(
  BuildContext context, {
  required IconData icon,
  required Color color,
  required String title,
}) {
  final typo = context.typo;
  return Row(
    children: [
      Icon(icon, size: typo.labelLarge.fontSize ?? 14, color: color),
      SizedBox(width: context.space.xs),
      Text(title, style: typo.labelLarge),
    ],
  );
}

/// 段内错误体（诚实错误文案 + 重试；不拖垮相邻段）。
class _SectionErrorBody extends StatelessWidget {
  const _SectionErrorBody({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CustomErrorWidget(message: message),
          SizedBox(height: context.space.sm),
          SparkleButton(
            variant: ButtonVariant.outline,
            label: context.l10n.squadRetry,
            onPressed: onRetry,
          ),
        ],
      );
}

/// 段级错误卡（整段数据面失败时的兜底，保其余段可达）。
class _SectionErrorCard extends StatelessWidget {
  const _SectionErrorCard({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Padding(
          padding: EdgeInsets.all(context.space.md),
          child: _SectionErrorBody(message: message, onRetry: onRetry),
        ),
      );
}
