import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/community_accountability_hub_model.dart';
import 'package:sparkle/features/community/presentation/l10n/community_accountability_hub_l10n.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_hub_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/accountability_hub/commitment_card.dart';
import 'package:sparkle/features/community/presentation/widgets/accountability_hub/partner_observation_control.dart';
import 'package:sparkle/features/community/presentation/widgets/community_strategy_card.dart';

class AccountabilityHubScreen extends ConsumerWidget {
  const AccountabilityHubScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(accountabilityHubProvider);
    final colorScheme = Theme.of(context).colorScheme;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(context.l10n.cahTitle),
        centerTitle: false,
        actions: [
          Tooltip(
            message: context.l10n.cahRetry,
            child: IconButton(
              icon: const Icon(Icons.refresh_rounded),
              onPressed: () =>
                  ref.read(accountabilityHubProvider.notifier).refresh(),
            ),
          ),
        ],
      ),
      child: state.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.sync_problem_rounded,
                  size: 48,
                  color: colorScheme.error,
                ),
                const SizedBox(height: 12),
                Text(
                  context.l10n.cahLoadFailed,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: () =>
                      ref.read(accountabilityHubProvider.notifier).refresh(),
                  icon: const Icon(Icons.refresh_rounded),
                  label: Text(context.l10n.cahRetry),
                ),
              ],
            ),
          ),
        ),
        data: (hub) => RefreshIndicator(
          onRefresh: () =>
              ref.read(accountabilityHubProvider.notifier).refresh(),
          child: ContentConstraint(
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 32),
              children: [
                _HubHeader(hub: hub),
                const SizedBox(height: 18),
                if (hub.isEmpty)
                  _EmptyHubCard()
                else ...[
                  _CommitmentsSection(commitments: hub.myCommitments),
                  const SizedBox(height: 22),
                  _PartnerProgressSection(items: hub.partnerProgress),
                  const SizedBox(height: 22),
                  _SharedGoalsSection(items: hub.sharedGoals),
                  const SizedBox(height: 22),
                  _HelpSection(hub: hub),
                ],
                const SizedBox(height: 22),
                _StrategySection(hub: hub),
                const SizedBox(height: 22),
                _SecondaryEntrySection(),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _HubHeader extends StatelessWidget {
  const _HubHeader({required this.hub});

  final CommunityAccountabilityHub hub;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Semantics(
      header: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.cahSubtitle,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _MetricTile(
                  icon: Icons.assignment_turned_in_outlined,
                  value: hub.myCommitments.length.toString(),
                  label: context.l10n.cahMyCommitments,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _MetricTile(
                  icon: Icons.diversity_3_outlined,
                  value: hub.partnerProgress.length.toString(),
                  label: context.l10n.cahPartnerProgress,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _MetricTile(
                  icon: Icons.volunteer_activism_outlined,
                  value: hub.helpable.length.toString(),
                  label: context.l10n.cahHelpable,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _CommitmentsSection extends ConsumerWidget {
  const _CommitmentsSection({required this.commitments});

  final List<CommitmentCardPayload> commitments;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (commitments.isEmpty) return const SizedBox.shrink();
    return _Section(
      title: context.l10n.cahMyCommitments,
      child: SizedBox(
        height: 342,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: commitments.length,
          separatorBuilder: (_, __) => const SizedBox(width: 12),
          itemBuilder: (context, index) {
            final commitment = commitments[index];
            return CommitmentCard(
              commitment: commitment,
              onReminderChanged: (value) {
                ref
                    .read(accountabilityHubProvider.notifier)
                    .setReminderBoundary(commitment.id, value);
                AppFeedback.undoable(
                  context: context,
                  message: context.l10n.cahBoundaryChanged,
                  actionLabel: context.l10n.cahUndo,
                  onAction: () {
                    ref
                        .read(accountabilityHubProvider.notifier)
                        .restoreCommitment(commitment);
                  },
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _PartnerProgressSection extends StatelessWidget {
  const _PartnerProgressSection({required this.items});

  final List<PartnerProgressItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return _Section(
      title: context.l10n.cahPartnerProgress,
      subtitle: context.l10n.cahTogetherNotRanking,
      child: Column(
        children: [
          for (final item in items) ...[
            _PartnerProgressCard(item: item),
            if (item != items.last) const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

class _PartnerProgressCard extends StatelessWidget {
  const _PartnerProgressCard({required this.item});

  final PartnerProgressItem item;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            SizedBox(
              width: 58,
              height: 58,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  CircularProgressIndicator(
                    value: item.weeklyProgress,
                    strokeWidth: 7,
                    strokeCap: StrokeCap.round,
                  ),
                  Text(
                    context.l10n
                        .cahPercent((item.weeklyProgress * 100).round()),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: colorScheme.onSurface,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.partnerName,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    context.l10n.cahPartnerGoal(item.partnerName),
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    item.goalSummary,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Tooltip(
              message: item.todayDone
                  ? context.l10n.cahTodayDone
                  : context.l10n.cahTodayWaiting,
              child: Icon(
                item.todayDone
                    ? Icons.check_circle_rounded
                    : Icons.radio_button_unchecked_rounded,
                color:
                    item.todayDone ? colorScheme.primary : colorScheme.outline,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SharedGoalsSection extends StatelessWidget {
  const _SharedGoalsSection({required this.items});

  final List<SharedGoalItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return _Section(
      title: context.l10n.cahSharedGoals,
      child: Column(
        children: [
          for (final item in items) ...[
            _SharedGoalCard(item: item),
            if (item != items.last) const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

class _SharedGoalCard extends StatelessWidget {
  const _SharedGoalCard({required this.item});

  final SharedGoalItem item;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              item.title,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 10),
            LinearProgressIndicator(
              value: item.progress,
              minHeight: 8,
              borderRadius: BorderRadius.circular(999),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final name in item.memberNames)
                  Chip(
                    avatar: CircleAvatar(
                      backgroundColor: colorScheme.primaryContainer,
                      foregroundColor: colorScheme.onPrimaryContainer,
                      child: Text(name.isEmpty ? '?' : name[0].toUpperCase()),
                    ),
                    label: Text(name),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _HelpSection extends StatelessWidget {
  const _HelpSection({required this.hub});

  final CommunityAccountabilityHub hub;

  @override
  Widget build(BuildContext context) {
    final items = [
      ...hub.squadRisks.map(
        (item) => _HelpRowData(
          title: item.memberName,
          body: item.reason,
          icon: Icons.health_and_safety_outlined,
        ),
      ),
      ...hub.helpable.map(
        (item) => _HelpRowData(
          title: item.memberName,
          body: item.need,
          icon: Icons.volunteer_activism_outlined,
        ),
      ),
    ];
    if (items.isEmpty) return const SizedBox.shrink();

    return _Section(
      title: context.l10n.cahNeedsAttention,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final item in items) ...[
                _HelpRow(item: item),
                if (item != items.last) const Divider(height: 18),
              ],
              const SizedBox(height: 8),
              PartnerObservationControl(
                onAccept: () => _showUndoable(
                  context,
                  context.l10n.cahReminderAccepted,
                ),
                onDecline: () => _showUndoable(
                  context,
                  context.l10n.cahReminderDeclined,
                ),
                onLater: () => _showUndoable(
                  context,
                  context.l10n.cahReminderLater,
                ),
                onTooFrequent: () => _showUndoable(
                  context,
                  context.l10n.cahReminderReduced,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showUndoable(BuildContext context, String message) {
    AppFeedback.undoable(
      context: context,
      message: message,
      actionLabel: context.l10n.cahUndo,
      onAction: () =>
          AppFeedback.info(context, context.l10n.cahBoundaryChanged),
    );
  }
}

class _SecondaryEntrySection extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.cahFeedEntry,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 4),
              Text(
                context.l10n.cahFeedEntryHint,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilledButton.icon(
                    onPressed: () =>
                        unawaited(context.push(CommunityRoutes.feed)),
                    icon: const Icon(Icons.forum_outlined),
                    label: Text(context.l10n.cahFeedEntry),
                  ),
                  OutlinedButton.icon(
                    onPressed: () =>
                        unawaited(context.push(CommunityRoutes.friends)),
                    icon: const Icon(Icons.people_outline_rounded),
                    label: Text(context.l10n.cahFriendsEntry),
                  ),
                  OutlinedButton.icon(
                    onPressed: () =>
                        unawaited(context.push(CommunityRoutes.groups)),
                    icon: const Icon(Icons.groups_outlined),
                    label: Text(context.l10n.cahGroupsEntry),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
}

class _EmptyHubCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Icon(
              Icons.diversity_1_outlined,
              size: 48,
              color: colorScheme.primary,
            ),
            const SizedBox(height: 12),
            Text(
              context.l10n.cahEmptyTitle,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              context.l10n.cahEmptyBody,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.icon,
    required this.value,
    required this.label,
  });

  final IconData icon;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Icon(icon, color: colorScheme.primary),
            const SizedBox(height: 6),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({
    required this.title,
    required this.child,
    this.subtitle,
  });

  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        if (subtitle != null) ...[
          const SizedBox(height: 2),
          Text(
            subtitle!,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
          ),
        ],
        const SizedBox(height: 10),
        child,
      ],
    );
  }
}

class _HelpRowData {
  const _HelpRowData({
    required this.title,
    required this.body,
    required this.icon,
  });

  final String title;
  final String body;
  final IconData icon;
}

class _HelpRow extends StatelessWidget {
  const _HelpRow({required this.item});

  final _HelpRowData item;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(item.icon, color: colorScheme.primary),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                item.title,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 2),
              Text(
                item.body,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _StrategySection extends StatelessWidget {
  const _StrategySection({required this.hub});

  final CommunityAccountabilityHub hub;

  @override
  Widget build(BuildContext context) {
    final strategies = _deriveStrategies(context);
    if (strategies.isEmpty) return const SizedBox.shrink();
    return _Section(
      title: context.l10n.cahStrategies,
      child: Column(
        children: [
          for (final s in strategies) ...[
            CommunityStrategyCard(strategy: s),
            if (s != strategies.last) const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }

  List<CommunityStrategy> _deriveStrategies(BuildContext context) {
    final l10n = context.l10n;
    final strategies = <CommunityStrategy>[];

    if (hub.myCommitments.isEmpty) {
      strategies.add(CommunityStrategy(
        title: l10n.cahStrategyCreateTitle,
        description: l10n.cahStrategyCreateDesc,
        strategyType: 'create_commitment',
        icon: Icons.assignment_outlined,
        actionLabel: l10n.cahStrategyCreateAction,
        onAction: () => unawaited(context.push(CommunityRoutes.feed)),
      ));
    }

    if (hub.partnerProgress.isEmpty) {
      strategies.add(CommunityStrategy(
        title: l10n.cahStrategyPartnerTitle,
        description: l10n.cahStrategyPartnerDesc,
        strategyType: 'find_partner',
        icon: Icons.person_search_outlined,
        actionLabel: l10n.cahStrategyPartnerAction,
        onAction: () => unawaited(context.push(CommunityRoutes.friends)),
      ));
    }

    if (hub.sharedGoals.isEmpty) {
      strategies.add(CommunityStrategy(
        title: l10n.cahStrategySharedGoalTitle,
        description: l10n.cahStrategySharedGoalDesc,
        strategyType: 'shared_goal',
        icon: Icons.groups_outlined,
        actionLabel: l10n.cahStrategySharedGoalAction,
        onAction: () => unawaited(context.push(CommunityRoutes.groups)),
      ));
    }

    if (hub.squadRisks.isNotEmpty) {
      strategies.add(CommunityStrategy(
        title: l10n.cahStrategySquadRiskTitle,
        description: l10n.cahStrategySquadRiskDesc,
        strategyType: 'squad_risk',
        icon: Icons.health_and_safety_outlined,
        actionLabel: l10n.cahStrategySquadRiskAction,
        onAction: () => unawaited(context.push(CommunityRoutes.friends)),
      ));
    }

    return strategies;
  }
}
