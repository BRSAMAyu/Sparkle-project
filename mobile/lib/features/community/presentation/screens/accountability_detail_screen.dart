import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/repositories/accountability_repository.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';

/// 责任伙伴关系详情页
class AccountabilityDetailScreen extends ConsumerStatefulWidget {
  const AccountabilityDetailScreen({
    required this.partnershipId,
    super.key,
  });
  final String partnershipId;

  @override
  ConsumerState<AccountabilityDetailScreen> createState() =>
      _AccountabilityDetailScreenState();
}

class _AccountabilityDetailScreenState
    extends ConsumerState<AccountabilityDetailScreen> {
  @override
  Widget build(BuildContext context) {
    final partnershipsAsync = ref.watch(myPartnershipsProvider);
    final statsAsync =
        ref.watch(partnershipStatsProvider(widget.partnershipId));
    final timelineAsync =
        ref.watch(partnershipTimelineProvider(widget.partnershipId));
    final currentUserId = ref.watch(currentUserProvider)?.id ?? '';

    final partnership = partnershipsAsync.valueOrNull?.firstWhere(
      (p) => p.id == widget.partnershipId,
      orElse: () => AccountabilityPartnershipInfo(
        id: widget.partnershipId,
        initiatorId: '',
        partnerId: '',
        initiatorGoal: '',
        checkInDays: 1,
        status: AccountabilityStatus.active,
        createdAt: DateTime.now(),
      ),
    );

    final isInitiator = partnership?.initiatorId == currentUserId;
    final partner =
        isInitiator ? partnership?.partner : partnership?.initiator;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(partner?.displayName ?? '责任伙伴'),
        actions: [
          PopupMenuButton<String>(
            onSelected: (v) {
              if (v == 'end') _confirmEnd();
            },
            itemBuilder: (_) => [
              const PopupMenuItem(
                  value: 'end', child: Text('结束伙伴关系'),),
            ],
          ),
        ],
      ),
      child: Column(
        children: [
          // ── Top: Dual avatar + streaks ──────────────────────────────
          statsAsync.when(
            loading: () => const SizedBox(height: 120, child: Center(child: LoadingIndicator())),
            error: (e, _) => const SizedBox.shrink(),
            data: (stats) => Container(
              padding: const EdgeInsets.all(DS.spacing16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _PersonStat(
                    name: '我',
                    streakDays: stats.myStreakDays,
                    checkedInToday: true, // assume checked if we called this page
                  ),
                  Column(
                    children: [
                      Text(
                        '🔥 ${stats.totalCheckins}',
                        style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: DS.brandPrimary),
                      ),
                      Text('总打卡',
                          style: TextStyle(
                              fontSize: DS.fontSizeXs, color: DS.neutral500),),
                    ],
                  ),
                  _PersonStat(
                    name: partner?.displayName ?? '伙伴',
                    streakDays: stats.partnerStreakDays,
                    checkedInToday: stats.partnerCheckedInToday,
                  ),
                ],
              ),
            ),
          ),

          const Divider(),

          // ── Today's goal section ────────────────────────────────────
          if (partnership != null)
            Padding(
              padding: const EdgeInsets.all(DS.spacing16),
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.panel,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('我的目标',
                        style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: DS.fontSizeSm,
                            color: DS.textSecondary),),
                    const SizedBox(height: DS.xs),
                    Text(
                      isInitiator
                          ? partnership.initiatorGoal
                          : partnership.partnerGoal ?? '(未设置)',
                    ),
                  ],
                ),
              ),
            ),

          // ── Timeline ────────────────────────────────────────────────
          Expanded(
            child: timelineAsync.when(
              loading: () => const Center(child: LoadingIndicator()),
              error: (e, _) => Center(
                  child: Text('$e', style: TextStyle(color: DS.error)),),
              data: (checkins) => ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                itemCount: checkins.length,
                itemBuilder: (ctx, i) => _CheckinTile(
                  checkin: checkins[i],
                  isMe: checkins[i].userId == currentUserId,
                ),
              ),
            ),
          ),

          // ── Bottom: Check-in button ──────────────────────────────────
          Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: SizedBox(
              width: double.infinity,
              child: SparkleButton.primary(
                label: '今日打卡',
                onPressed: () => _showCheckinSheet(),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showCheckinSheet() {
    unawaited(showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      builder: (ctx) => AccountabilityCheckinSheet(
        partnershipId: widget.partnershipId,
        onDone: () {
          ref.invalidate(partnershipStatsProvider(widget.partnershipId));
          ref.invalidate(partnershipTimelineProvider(widget.partnershipId));
        },
      ),
    ));
  }

  Future<void> _confirmEnd() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('结束伙伴关系'),
        content: const Text('确定要结束这段责任伙伴关系吗？'),
        actions: [
          SparkleButton.ghost(
            label: '取消',
            onPressed: () => Navigator.pop(ctx, false),
          ),
          SparkleButton(
            label: '结束',
            onPressed: () => Navigator.pop(ctx, true),
            variant: ButtonVariant.destructive,
          ),
        ],
      ),
    );

    if (confirmed ?? false) {
      try {
        await ref
            .read(myPartnershipsProvider.notifier)
            .endPartnership(widget.partnershipId);
        if (mounted) {
          context.pop();
          AppFeedback.success(context, '伙伴关系已结束');
        }
      } catch (e) {
        if (mounted) AppFeedback.error(context, '操作失败: $e');
      }
    }
  }
}

class _PersonStat extends StatelessWidget {
  const _PersonStat({
    required this.name,
    required this.streakDays,
    required this.checkedInToday,
  });

  final String name;
  final int streakDays;
  final bool checkedInToday;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Stack(
            children: [
              CircleAvatar(
                radius: 32,
                backgroundColor: DS.brandPrimary.withValues(alpha: 0.15),
                child: Text(
                  name.substring(0, 1).toUpperCase(),
                  style: TextStyle(
                      color: DS.brandPrimary,
                      fontWeight: FontWeight.bold,
                      fontSize: 24),
                ),
              ),
              if (checkedInToday)
                Positioned(
                  right: 0,
                  bottom: 0,
                  child: Container(
                    width: 18,
                    height: 18,
                    decoration: BoxDecoration(
                      color: DS.success,
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 2),
                    ),
                    child: const Icon(Icons.check,
                        size: 10, color: Colors.white,),
                  ),
                ),
            ],
          ),
          const SizedBox(height: DS.xs),
          Text(name,
              style: const TextStyle(fontWeight: FontWeight.bold),),
          Text('$streakDays 天',
              style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.brandPrimary),),
        ],
      );
}

class _CheckinTile extends StatelessWidget {
  const _CheckinTile({required this.checkin, required this.isMe});

  final AccountabilityCheckinInfo checkin;
  final bool isMe;

  @override
  Widget build(BuildContext context) {
    final dateStr =
        DateFormat('MM-dd HH:mm').format(checkin.createdAt);
    final moodEmojis = ['😔', '😕', '😐', '😊', '😄'];
    final moodIdx = (checkin.mood - 1).clamp(0, 4);

    return Container(
      margin: const EdgeInsets.only(bottom: DS.sm),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: isMe
            ? DS.brandPrimary.withValues(alpha: 0.08)
            : DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(DS.borderRadiusMD),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                isMe ? '我' : '伙伴',
                style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: isMe ? DS.brandPrimary : DS.textPrimary,
                    fontSize: DS.fontSizeSm),
              ),
              const SizedBox(width: DS.sm),
              Text(moodEmojis[moodIdx], style: const TextStyle(fontSize: 16)),
              const SizedBox(width: DS.sm),
              if (checkin.minutes > 0)
                Text('${checkin.minutes}分钟',
                    style: TextStyle(
                        fontSize: DS.fontSizeXs, color: DS.textSecondary),),
              const Spacer(),
              Text(dateStr,
                  style: TextStyle(
                      fontSize: DS.fontSizeXs, color: DS.neutral400),),
            ],
          ),
          const SizedBox(height: DS.xs),
          Text(checkin.content,
              style: const TextStyle(fontSize: DS.fontSizeSm),),
        ],
      ),
    );
  }
}

/// 打卡 BottomSheet
class AccountabilityCheckinSheet extends ConsumerStatefulWidget {
  const AccountabilityCheckinSheet({
    required this.partnershipId,
    required this.onDone,
    super.key,
  });

  final String partnershipId;
  final VoidCallback onDone;

  @override
  ConsumerState<AccountabilityCheckinSheet> createState() =>
      _AccountabilityCheckinSheetState();
}

class _AccountabilityCheckinSheetState
    extends ConsumerState<AccountabilityCheckinSheet> {
  final _contentController = TextEditingController();
  int _mood = 3;
  int _minutes = 30;
  bool _isLoading = false;

  @override
  void dispose() {
    _contentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final moodEmojis = ['😔', '😕', '😐', '😊', '😄'];

    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: EdgeInsets.only(
            left: DS.spacing16,
            right: DS.spacing16,
            top: DS.spacing16,
            bottom:
                MediaQuery.of(context).viewInsets.bottom + DS.spacing16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('今日打卡',
                  style: TextStyle(
                      fontWeight: FontWeight.bold, fontSize: DS.fontSizeLg),),
              const SizedBox(height: DS.spacing16),

              // Content input
              TextField(
                controller: _contentController,
                decoration: const InputDecoration(
                  hintText: '今日进展...',
                  border: OutlineInputBorder(),
                ),
                maxLines: 3,
                autofocus: true,
              ),
              const SizedBox(height: DS.spacing16),

              // Mood selector
              const Text('今日心情:',
                  style: TextStyle(fontWeight: FontWeight.bold),),
              const SizedBox(height: DS.sm),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: List.generate(5, (i) {
                  final selected = _mood == i + 1;
                  return GestureDetector(
                    onTap: () => setState(() => _mood = i + 1),
                    child: Container(
                      padding: const EdgeInsets.all(DS.sm),
                      decoration: BoxDecoration(
                        color: selected
                            ? DS.brandPrimary.withValues(alpha: 0.15)
                            : Colors.transparent,
                        borderRadius:
                            BorderRadius.circular(DS.borderRadiusMD),
                        border: selected
                            ? Border.all(color: DS.brandPrimary)
                            : null,
                      ),
                      child: Text(moodEmojis[i],
                          style: const TextStyle(fontSize: 28),),
                    ),
                  );
                }),
              ),
              const SizedBox(height: DS.spacing16),

              // Minutes slider
              Row(
                children: [
                  Text('投入时长: $_minutes 分钟',
                      style:
                          const TextStyle(fontWeight: FontWeight.bold),),
                ],
              ),
              Slider(
                value: _minutes.toDouble(),
                min: 0,
                max: 360,
                divisions: 72,
                label: '$_minutes 分钟',
                onChanged: (v) =>
                    setState(() => _minutes = v.toInt()),
              ),
              const SizedBox(height: DS.spacing16),

              SizedBox(
                width: double.infinity,
                child: SparkleButton.primary(
                  label: _isLoading ? '提交中...' : '提交打卡',
                  onPressed: _isLoading ? () {} : () { unawaited(_submit()); },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _submit() async {
    final content = _contentController.text.trim();
    if (content.isEmpty) {
      AppFeedback.info(context, '请输入今日进展');
      return;
    }

    setState(() => _isLoading = true);
    try {
      await ref.read(accountabilityRepositoryProvider).dailyCheckin(
            widget.partnershipId,
            content: content,
            mood: _mood,
            minutes: _minutes,
          );
      if (!mounted) return;
      Navigator.pop(context);
      widget.onDone();
      AppFeedback.success(context, '打卡成功！继续加油 🔥');
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      AppFeedback.error(context, '打卡失败: $e');
    }
  }
}
