import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/features/insights/data/models/directive_audit_entry.dart';
import 'package:sparkle/features/insights/presentation/providers/directive_audit_provider.dart';

class DirectiveAuditScreen extends ConsumerStatefulWidget {
  const DirectiveAuditScreen({super.key});

  @override
  ConsumerState<DirectiveAuditScreen> createState() =>
      _DirectiveAuditScreenState();
}

class _DirectiveAuditScreenState extends ConsumerState<DirectiveAuditScreen> {
  String _directiveType = 'all';
  int _hours = 24 * 7;

  @override
  Widget build(BuildContext context) {
    final filter = DirectiveAuditFilter(
      directiveType: _directiveType == 'all' ? null : _directiveType,
      hours: _hours,
    );
    final entriesAsync = ref.watch(directiveAuditProvider(filter));

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(context.l10n.insDecisionLog),
      ),
      child: ContentConstraint(
        child: SparkleRefreshIndicator(
          onRefresh: () async {
            ref.invalidate(directiveAuditProvider(filter));
          },
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(
              DS.spacing16,
              DS.spacing8,
              DS.spacing16,
              DS.spacing24,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _DirectiveAuditFilters(
                  directiveType: _directiveType,
                  hours: _hours,
                  onDirectiveTypeChanged: (value) =>
                      setState(() => _directiveType = value),
                  onHoursChanged: (value) => setState(() => _hours = value),
                ),
                const SizedBox(height: DS.spacing16),
                entriesAsync.when(
                  data: (entries) => DirectiveAuditTimeline(entries: entries),
                  loading: () => const Padding(
                    padding: EdgeInsets.all(DS.spacing32),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                  error: (error, _) => _DirectiveAuditError(
                    message: UserFacingError.from(error),
                    onRetry: () =>
                        ref.invalidate(directiveAuditProvider(filter)),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DirectiveAuditFilters extends StatelessWidget {
  const _DirectiveAuditFilters({
    required this.directiveType,
    required this.hours,
    required this.onDirectiveTypeChanged,
    required this.onHoursChanged,
  });

  final String directiveType;
  final int hours;
  final ValueChanged<String> onDirectiveTypeChanged;
  final ValueChanged<int> onHoursChanged;

  @override
  Widget build(BuildContext context) {
    final typeOptions = <String, String>{
      'all': context.l10n.insFilterAll,
      'NotifyUser': 'NotifyUser',
      'SkipReminder': 'SkipReminder',
      'DowngradeIntensity': 'DowngradeIntensity',
      'ReplanLocally': 'ReplanLocally',
    };
    final timeOptions = <int, String>{
      24: context.l10n.insFilter24h,
      24 * 7: context.l10n.insFilter7d,
      24 * 30: context.l10n.insFilter30d,
    };

    return GraphiteCardSurface(
      padding: const EdgeInsets.all(DS.spacing14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              for (final option in typeOptions.entries)
                ChoiceChip(
                  label: Text(option.value),
                  selected: directiveType == option.key,
                  onSelected: (_) => onDirectiveTypeChanged(option.key),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              for (final option in timeOptions.entries)
                ChoiceChip(
                  label: Text(option.value),
                  selected: hours == option.key,
                  onSelected: (_) => onHoursChanged(option.key),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class DirectiveAuditTimeline extends StatelessWidget {
  const DirectiveAuditTimeline({required this.entries, super.key});

  final List<DirectiveAuditEntry> entries;

  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) {
      return GraphiteCardSurface(
        padding: const EdgeInsets.all(DS.spacing24),
        child: Column(
          children: [
            Icon(Icons.timeline_rounded, size: 40, color: DS.textSecondary),
            const SizedBox(height: DS.spacing12),
            Text(
              context.l10n.insDecisionLogEmpty,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        for (var i = 0; i < entries.length; i++) ...[
          if (i > 0) const SizedBox(height: DS.spacing12),
          DirectiveAuditCard(entry: entries[i]),
        ],
      ],
    );
  }
}

class DirectiveAuditCard extends StatelessWidget {
  const DirectiveAuditCard({required this.entry, super.key});

  final DirectiveAuditEntry entry;

  @override
  Widget build(BuildContext context) {
    final time = DateFormat('MM/dd HH:mm').format(entry.createdAt.toLocal());
    final signal = entry.triggerSignal?['claim']?.toString() ??
        entry.triggerSignal?['state_key']?.toString() ??
        context.l10n.insNoSignalRecorded;
    final policy = entry.policy?['primary_strategy']?.toString() ??
        context.l10n.insNoPolicyRecorded;
    final result = entry.actualResult == null
        ? context.l10n.insResultPending
        : entry.wasApplied
            ? context.l10n.insResultApplied
            : context.l10n.insResultNeedsReview;
    final resultColor = entry.actualResult == null
        ? DS.textSecondary
        : entry.wasApplied
            ? DS.success
            : DS.warning;

    return GraphiteCardSurface(
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: DS.info.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                  border: Border.all(color: DS.info.withValues(alpha: 0.22)),
                ),
                child: Icon(
                  _iconFor(entry.displayType),
                  color: DS.info,
                  size: 20,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.displayType.isEmpty
                          ? entry.directiveType
                          : entry.displayType,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      '$time · ${entry.targetModule}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: resultColor.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  result,
                  style: TextStyle(
                    color: resultColor,
                    fontSize: DS.fontSizeXs,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
            ],
          ),
          if (entry.userVisibleReason.trim().isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              entry.userVisibleReason.trim(),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.textPrimary,
                    height: 1.52,
                  ),
            ),
          ],
          const SizedBox(height: DS.spacing12),
          _DirectiveAuditFactRow(
            icon: Icons.sensors_rounded,
            label: context.l10n.insSignalLabel,
            value: signal,
          ),
          const SizedBox(height: DS.spacing8),
          _DirectiveAuditFactRow(
            icon: Icons.rule_rounded,
            label: context.l10n.insPolicyLabel,
            value: policy,
          ),
        ],
      ),
    );
  }

  IconData _iconFor(String displayType) {
    switch (displayType) {
      case 'NotifyUser':
        return Icons.notifications_active_outlined;
      case 'SkipReminder':
        return Icons.notifications_off_outlined;
      case 'DowngradeIntensity':
        return Icons.compress_rounded;
      case 'ReplanLocally':
        return Icons.alt_route_rounded;
      default:
        return Icons.account_tree_outlined;
    }
  }
}

class _DirectiveAuditFactRow extends StatelessWidget {
  const _DirectiveAuditFactRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 16, color: DS.textSecondary),
          const SizedBox(width: DS.spacing8),
          SizedBox(
            width: 74,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    fontWeight: DS.fontWeightMedium,
                  ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textPrimary,
                    height: 1.52,
                  ),
            ),
          ),
        ],
      );
}

class _DirectiveAuditError extends StatelessWidget {
  const _DirectiveAuditError({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return GraphiteCardSurface(
      child: Column(
        children: [
          Icon(Icons.error_outline_rounded, color: DS.error),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.insLoadFailedDecisionLog,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            message,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          const SizedBox(height: DS.spacing12),
          TextButton(
            onPressed: onRetry,
            child: Text(context.l10n.insRetry),
          ),
        ],
      ),
    );
  }
}
