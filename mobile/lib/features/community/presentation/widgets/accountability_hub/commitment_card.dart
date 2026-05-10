import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/data/models/community_accountability_hub_model.dart';

class CommitmentCard extends StatefulWidget {
  const CommitmentCard({
    required this.commitment,
    required this.onReminderChanged,
    super.key,
  });

  final CommitmentCardPayload commitment;
  final ValueChanged<bool> onReminderChanged;

  @override
  State<CommitmentCard> createState() => _CommitmentCardState();
}

class _CommitmentCardState extends State<CommitmentCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final progressPercent = (widget.commitment.progress * 100).round();

    return Semantics(
      button: true,
      label: widget.commitment.summary,
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () => setState(() => _expanded = !_expanded),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 400, minWidth: 260),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      _StatusPill(status: widget.commitment.status),
                      const Spacer(),
                      Icon(
                        _expanded
                            ? Icons.keyboard_arrow_up_rounded
                            : Icons.keyboard_arrow_down_rounded,
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    widget.commitment.summary,
                    maxLines: _expanded ? 4 : 2,
                    overflow: TextOverflow.ellipsis,
                    style: textTheme.titleMedium?.copyWith(
                      color: colorScheme.onSurface,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: LinearProgressIndicator(
                          minHeight: 8,
                          value: widget.commitment.progress,
                          borderRadius: BorderRadius.circular(999),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        context.l10n.cahPercent(progressPercent),
                        style: textTheme.labelMedium?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      if (widget.commitment.dueAt != null)
                        _MetaChip(
                          icon: Icons.schedule_rounded,
                          label: context.l10n.cahDueDate(
                            _formatDueAt(widget.commitment.dueAt!),
                          ),
                        ),
                      if (widget.commitment.witnessNames.isNotEmpty)
                        _MetaChip(
                          icon: Icons.visibility_outlined,
                          label:
                              '${context.l10n.cahWitnesses}: ${widget.commitment.witnessNames.join(', ')}',
                        ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Semantics(
                    toggled: widget.commitment.allowPartnerReminders,
                    label: widget.commitment.allowPartnerReminders
                        ? context.l10n.cahAllowReminder
                        : context.l10n.cahDoNotDisturb,
                    child: SwitchListTile.adaptive(
                      contentPadding: EdgeInsets.zero,
                      dense: true,
                      title: Text(
                        widget.commitment.allowPartnerReminders
                            ? context.l10n.cahAllowReminder
                            : context.l10n.cahDoNotDisturb,
                      ),
                      value: widget.commitment.allowPartnerReminders,
                      onChanged: widget.onReminderChanged,
                    ),
                  ),
                  AnimatedCrossFade(
                    firstChild: const SizedBox.shrink(),
                    secondChild: _CommitmentDetails(
                      commitment: widget.commitment,
                    ),
                    crossFadeState: _expanded
                        ? CrossFadeState.showSecond
                        : CrossFadeState.showFirst,
                    duration: const Duration(milliseconds: 180),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  String _formatDueAt(DateTime value) {
    final local = value.toLocal();
    final minute = local.minute.toString().padLeft(2, '0');
    return '${local.month}/${local.day} ${local.hour}:$minute';
  }
}

class _CommitmentDetails extends StatelessWidget {
  const _CommitmentDetails({required this.commitment});

  final CommitmentCardPayload commitment;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _DetailList(
              title: context.l10n.cahSuccessCriteria,
              items: commitment.successCriteria,
              icon: Icons.check_circle_outline_rounded,
            ),
            const SizedBox(height: 10),
            _DetailList(
              title: context.l10n.cahMilestones,
              items: commitment.milestones,
              icon: Icons.flag_outlined,
            ),
            const SizedBox(height: 10),
            _DetailList(
              title: context.l10n.cahEvidence,
              items: commitment.evidenceRefs.isEmpty
                  ? [context.l10n.cahNoEvidence]
                  : commitment.evidenceRefs,
              icon: Icons.link_rounded,
            ),
          ],
        ),
      );
}

class _DetailList extends StatelessWidget {
  const _DetailList({
    required this.title,
    required this.items,
    required this.icon,
  });

  final String title;
  final List<String> items;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 16, color: colorScheme.primary),
            const SizedBox(width: 6),
            Text(
              title,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: colorScheme.onSurface,
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        for (final item in items)
          Padding(
            padding: const EdgeInsets.only(bottom: 4, left: 22),
            child: Text(
              item,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
            ),
          ),
      ],
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final label = switch (status) {
      'due_soon' => context.l10n.cahDueSoon,
      'completed' || 'fulfilled' => context.l10n.cahCompleted,
      'violated' => context.l10n.cahViolated,
      _ => context.l10n.cahActive,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: colorScheme.onPrimaryContainer,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: colorScheme.onSurfaceVariant),
          const SizedBox(width: 6),
          Flexible(
            child: Text(
              label,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}
