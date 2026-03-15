import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';

IconData _mapAgentIcon(String icon) {
  switch (icon) {
    case 'constellation':
      return Icons.auto_awesome;
    case 'target':
      return Icons.track_changes;
    case 'clock':
      return Icons.schedule;
    case 'microscope':
      return Icons.biotech;
    case 'debug':
      return Icons.bug_report;
    case 'handshake':
      return Icons.handshake;
    case 'calculator':
      return Icons.calculate;
    case 'code':
      return Icons.code;
    case 'pen':
      return Icons.edit_note;
    case 'flask':
      return Icons.science;
    case 'search':
      return Icons.search;
    default:
      return Icons.smart_toy;
  }
}

Color _hexToColor(String hex) {
  var cleaned = hex.replaceFirst('#', '');
  if (cleaned.length == 6) {
    cleaned = 'FF$cleaned';
  }
  return Color(int.parse(cleaned, radix: 16));
}

String _formatDuration(double ms) {
  if (ms < 1000) {
    return '${ms.toStringAsFixed(0)}ms';
  }
  return '${(ms / 1000).toStringAsFixed(1)}s';
}

class AgentWorkflowPanel extends StatelessWidget {
  const AgentWorkflowPanel({
    super.key,
    this.liveActivities,
    this.snapshotActivities,
    this.narrative,
  });

  final List<AgentActivityEvent>? liveActivities;
  final List<Map<String, dynamic>>? snapshotActivities;
  final String? narrative;

  @override
  Widget build(BuildContext context) {
    final entries = _buildEntries();
    if (entries.isEmpty) {
      return const SizedBox.shrink();
    }

    if (entries.length == 1) {
      return _SingleAgentBadge(entry: entries.first);
    }

    final mode = _resolveMode(entries);
    switch (mode) {
      case 'parallel':
        return _ParallelAgentRow(entries: entries, narrative: narrative);
      case 'debate':
        return _DebateTimeline(entries: entries, narrative: narrative);
      case 'delegation':
        return _DelegationTree(entries: entries, narrative: narrative);
      default:
        return _SequentialTimeline(entries: entries, narrative: narrative);
    }
  }

  List<_AgentEntry> _buildEntries() {
    if (liveActivities != null && liveActivities!.isNotEmpty) {
      return liveActivities!
          .map(
            (event) => _AgentEntry(
              agentId: event.agentId,
              status: event.status,
              displayName: event.displayName,
              icon: event.icon,
              color: event.color,
              description: event.description,
              durationMs: event.durationMs,
              resultSummary: event.resultSummary,
              collaborationMode: event.collaborationMode,
              phase: event.phase,
            ),
          )
          .toList();
    }

    if (snapshotActivities != null && snapshotActivities!.isNotEmpty) {
      return snapshotActivities!
          .map(
            (entry) => _AgentEntry(
              agentId: entry['agent_id'] as String? ?? '',
              status: entry['status'] as String? ?? 'completed',
              displayName: entry['display_name'] as String? ?? '',
              icon: entry['icon'] as String? ?? 'bot',
              color: entry['color'] as String? ?? '#636E72',
              description: entry['description'] as String? ?? '',
              durationMs: (entry['duration_ms'] as num?)?.toDouble(),
              resultSummary: entry['result_summary'] as String?,
              collaborationMode: entry['collaboration_mode'] as String?,
              phase: entry['phase'] as String?,
            ),
          )
          .toList();
    }

    return const [];
  }

  String _resolveMode(List<_AgentEntry> entries) {
    for (final entry in entries) {
      final mode = entry.collaborationMode?.trim();
      if (mode != null && mode.isNotEmpty) {
        return mode;
      }
    }
    final activeCount = entries.where((entry) => entry.status == 'active').length;
    return activeCount > 1 ? 'parallel' : 'sequential';
  }
}

class _AgentEntry {
  const _AgentEntry({
    required this.agentId,
    required this.status,
    required this.displayName,
    required this.icon,
    required this.color,
    required this.description,
    this.durationMs,
    this.resultSummary,
    this.collaborationMode,
    this.phase,
  });

  final String agentId;
  final String status;
  final String displayName;
  final String icon;
  final String color;
  final String description;
  final double? durationMs;
  final String? resultSummary;
  final String? collaborationMode;
  final String? phase;
}

class _SingleAgentBadge extends StatelessWidget {
  const _SingleAgentBadge({required this.entry});

  final _AgentEntry entry;

  @override
  Widget build(BuildContext context) {
    final agentColor = _hexToColor(entry.color);
    final isActive = entry.status == 'active';

    return Container(
      margin: const EdgeInsets.only(top: DS.spacing6),
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: agentColor.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: agentColor.withValues(alpha: 0.2)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(_mapAgentIcon(entry.icon), size: 14, color: agentColor),
          const SizedBox(width: DS.spacing6),
          Text(
            entry.displayName,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: agentColor,
            ),
          ),
          if (isActive) ...[
            const SizedBox(width: DS.spacing6),
            SizedBox(
              width: 10,
              height: 10,
              child: CircularProgressIndicator(
                strokeWidth: 1.5,
                color: agentColor,
              ),
            ),
          ],
          if (entry.durationMs != null) ...[
            const SizedBox(width: DS.spacing6),
            Text(
              _formatDuration(entry.durationMs!),
              style: TextStyle(
                fontSize: 11,
                color: agentColor.withValues(alpha: 0.7),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _WorkflowShell extends StatelessWidget {
  const _WorkflowShell({
    required this.title,
    required this.icon,
    required this.child,
    required this.identities,
    this.totalDuration,
    this.subtitle,
    this.narrative,
  });

  final String title;
  final IconData icon;
  final Widget child;
  final List<_AgentIdentity> identities;
  final double? totalDuration;
  final String? subtitle;
  final String? narrative;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      margin: const EdgeInsets.only(top: DS.spacing8),
      padding: const EdgeInsets.all(DS.spacing10),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: theme.colorScheme.primary),
              const SizedBox(width: DS.spacing4),
              Text(
                title,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.primary,
                ),
              ),
              const Spacer(),
              if (totalDuration != null)
                Text(
                  _formatDuration(totalDuration!),
                  style: TextStyle(
                    fontSize: 11,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
            ],
          ),
          if (subtitle != null) ...[
            const SizedBox(height: DS.spacing4),
            Text(
              subtitle!,
              style: TextStyle(
                fontSize: 11,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
          if (identities.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing6,
              runSpacing: DS.spacing6,
              children: identities
                  .map(
                    (identity) => _AgentIdentityChip(identity: identity),
                  )
                  .toList(),
            ),
          ],
          if (narrative != null && narrative!.trim().isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              narrative!,
              style: TextStyle(
                fontSize: 11,
                height: 1.45,
                color: theme.colorScheme.onSurface,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
          const SizedBox(height: DS.spacing8),
          child,
        ],
      ),
    );
  }
}

class _SequentialTimeline extends StatelessWidget {
  const _SequentialTimeline({
    required this.entries,
    this.narrative,
  });

  final List<_AgentEntry> entries;
  final String? narrative;

  @override
  Widget build(BuildContext context) => _WorkflowShell(
        title: '${entries.length} 位专家协作',
        icon: Icons.account_tree,
        identities: _buildIdentityModels(entries),
        narrative: narrative,
        totalDuration: _totalDuration(entries),
        child: Column(
          children: entries
              .asMap()
              .entries
              .map(
                (entry) => _AgentTimelineRow(
                  entry: entry.value,
                  isLast: entry.key == entries.length - 1,
                ),
              )
              .toList(),
        ),
      );
}

class _ParallelAgentRow extends StatelessWidget {
  const _ParallelAgentRow({
    required this.entries,
    this.narrative,
  });

  final List<_AgentEntry> entries;
  final String? narrative;

  @override
  Widget build(BuildContext context) => _WorkflowShell(
        title: '${entries.length} 位专家并行协作',
        icon: Icons.view_week,
        subtitle: '多个专家在独立分析不同侧面，系统随后会统一整合。',
        identities: _buildIdentityModels(entries),
        narrative: narrative,
        totalDuration: _totalDuration(entries, parallel: true),
        child: Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: entries
              .map(
                (entry) => SizedBox(
                  width: 156,
                  child: _ParallelAgentCard(entry: entry),
                ),
              )
              .toList(),
        ),
      );
}

class _DebateTimeline extends StatelessWidget {
  const _DebateTimeline({
    required this.entries,
    this.narrative,
  });

  final List<_AgentEntry> entries;
  final String? narrative;

  @override
  Widget build(BuildContext context) => _WorkflowShell(
        title: '多视角辩论协作',
        icon: Icons.compare_arrows,
        subtitle: '专家先独立分析，再交叉评审，最后由系统综合差异观点。',
        identities: _buildIdentityModels(entries),
        narrative: narrative,
        totalDuration: _totalDuration(entries, parallel: true),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: entries
                  .map(
                    (entry) => SizedBox(
                      width: 156,
                      child: _ParallelAgentCard(entry: entry),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: DS.spacing10),
            const _FooterBanner(
              icon: Icons.gavel_rounded,
              label: '系统正在综合各方观点与评审意见',
            ),
          ],
        ),
      );
}

class _DelegationTree extends StatelessWidget {
  const _DelegationTree({
    required this.entries,
    this.narrative,
  });

  final List<_AgentEntry> entries;
  final String? narrative;

  @override
  Widget build(BuildContext context) {
    final lead = entries.first;
    final delegates = entries.length > 1 ? entries.sublist(1) : const <_AgentEntry>[];
    return _WorkflowShell(
      title: '委派式协作',
      icon: Icons.hub_rounded,
      subtitle: '主专家先拆分任务，再把子任务委派给其他专家并汇总结果。',
      identities: _buildIdentityModels(entries),
      narrative: narrative,
      totalDuration: _totalDuration(entries),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _ParallelAgentCard(entry: lead, emphasized: true),
          if (delegates.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Padding(
              padding: const EdgeInsets.only(left: DS.spacing16),
              child: Container(
                width: 2,
                height: 16,
                color: Theme.of(context).colorScheme.outlineVariant,
              ),
            ),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: delegates
                  .map(
                    (entry) => SizedBox(
                      width: 156,
                      child: _ParallelAgentCard(entry: entry),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _AgentIdentity {
  const _AgentIdentity({
    required this.label,
    required this.color,
    required this.icon,
  });

  final String label;
  final String color;
  final String icon;
}

List<_AgentIdentity> _buildIdentityModels(List<_AgentEntry> entries) {
  final identities = <_AgentIdentity>[];
  final seen = <String>{};
  for (final entry in entries) {
    final key = entry.agentId.trim();
    if (key.isEmpty || !seen.add(key)) {
      continue;
    }
    identities.add(
      _AgentIdentity(
        label: entry.displayName,
        color: entry.color,
        icon: entry.icon,
      ),
    );
  }
  return identities;
}

class _AgentIdentityChip extends StatelessWidget {
  const _AgentIdentityChip({required this.identity});

  final _AgentIdentity identity;

  @override
  Widget build(BuildContext context) {
    final chipColor = _hexToColor(identity.color);
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: chipColor.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: chipColor.withValues(alpha: 0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(_mapAgentIcon(identity.icon), size: 12, color: chipColor),
          const SizedBox(width: DS.spacing4),
          Text(
            identity.label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: chipColor,
            ),
          ),
        ],
      ),
    );
  }
}

class _ParallelAgentCard extends StatelessWidget {
  const _ParallelAgentCard({
    required this.entry,
    this.emphasized = false,
  });

  final _AgentEntry entry;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    final color = _hexToColor(entry.color);
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(DS.spacing8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: emphasized ? 0.12 : 0.07),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: color.withValues(alpha: emphasized ? 0.28 : 0.18),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(_mapAgentIcon(entry.icon), size: 14, color: color),
              const SizedBox(width: DS.spacing4),
              Expanded(
                child: Text(
                  entry.displayName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: theme.colorScheme.onSurface,
                  ),
                ),
              ),
              _StatusLabel(status: entry.status, color: color),
            ],
          ),
          if (entry.phase != null && entry.phase!.isNotEmpty) ...[
            const SizedBox(height: DS.spacing4),
            Text(
              '阶段: ${entry.phase}',
              style: TextStyle(
                fontSize: 10,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
          if (entry.resultSummary != null && entry.resultSummary!.isNotEmpty) ...[
            const SizedBox(height: DS.spacing4),
            Text(
              entry.resultSummary!,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 11,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
          if (entry.durationMs != null) ...[
            const SizedBox(height: DS.spacing6),
            Text(
              _formatDuration(entry.durationMs!),
              style: TextStyle(
                fontSize: 10,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _AgentTimelineRow extends StatelessWidget {
  const _AgentTimelineRow({
    required this.entry,
    required this.isLast,
  });

  final _AgentEntry entry;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final agentColor = _hexToColor(entry.color);
    final theme = Theme.of(context);

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 24,
            child: Column(
              children: [
                _StatusDot(status: entry.status, color: agentColor),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 1.5,
                      color: agentColor.withValues(alpha: 0.2),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : DS.spacing10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(_mapAgentIcon(entry.icon), size: 13, color: agentColor),
                      const SizedBox(width: DS.spacing4),
                      Expanded(
                        child: Text(
                          entry.displayName,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: theme.colorScheme.onSurface,
                          ),
                        ),
                      ),
                      _StatusLabel(status: entry.status, color: agentColor),
                      if (entry.durationMs != null) ...[
                        const SizedBox(width: DS.spacing6),
                        Text(
                          _formatDuration(entry.durationMs!),
                          style: TextStyle(
                            fontSize: 10,
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ],
                  ),
                  if (entry.resultSummary != null && entry.resultSummary!.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing4),
                    Text(
                      entry.resultSummary!,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 11,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FooterBanner extends StatelessWidget {
  const _FooterBanner({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(icon, size: 14, color: theme.colorScheme.primary),
          const SizedBox(width: DS.spacing6),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 11,
                color: theme.colorScheme.primary,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusDot extends StatelessWidget {
  const _StatusDot({required this.status, required this.color});

  final String status;
  final Color color;

  @override
  Widget build(BuildContext context) {
    const size = 18.0;
    if (status == 'active') {
      return SizedBox(
        width: size,
        height: size,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          color: color,
        ),
      );
    }
    if (status == 'error') {
      return const Icon(Icons.error, size: size, color: Colors.red);
    }
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: status == 'completed' ? color : color.withValues(alpha: 0.15),
        border: Border.all(color: color, width: 1.5),
      ),
      child: status == 'completed'
          ? const Icon(Icons.check, size: 11, color: Colors.white)
          : null,
    );
  }
}

class _StatusLabel extends StatelessWidget {
  const _StatusLabel({required this.status, required this.color});

  final String status;
  final Color color;

  String get _label {
    switch (status) {
      case 'pending':
        return '等待中';
      case 'active':
        return '进行中';
      case 'completed':
        return '完成';
      case 'error':
        return '异常';
      default:
        return status;
    }
  }

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
      decoration: BoxDecoration(
        color: status == 'error'
            ? Colors.red.withValues(alpha: 0.1)
            : color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        _label,
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w500,
          color: status == 'error' ? Colors.red : color,
          ),
        ),
      );
}

double? _totalDuration(List<_AgentEntry> entries, {bool parallel = false}) {
  final durations = entries.where((entry) => entry.durationMs != null).map((entry) => entry.durationMs!);
  if (durations.isEmpty) {
    return null;
  }
  return parallel
      ? durations.reduce((a, b) => a > b ? a : b)
      : durations.reduce((a, b) => a + b);
}
