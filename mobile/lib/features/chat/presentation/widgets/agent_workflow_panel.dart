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
  });

  final List<AgentActivityEvent>? liveActivities;
  final List<Map<String, dynamic>>? snapshotActivities;

  @override
  Widget build(BuildContext context) {
    final entries = _buildEntries();
    if (entries.isEmpty) {
      return const SizedBox.shrink();
    }

    if (entries.length == 1) {
      return _SingleAgentBadge(entry: entries.first);
    }

    return _MultiAgentTimeline(entries: entries);
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
            ),
          )
          .toList();
    }

    return const [];
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
  });

  final String agentId;
  final String status;
  final String displayName;
  final String icon;
  final String color;
  final String description;
  final double? durationMs;
  final String? resultSummary;
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

class _MultiAgentTimeline extends StatelessWidget {
  const _MultiAgentTimeline({required this.entries});

  final List<_AgentEntry> entries;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final totalDuration = _totalDuration;

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
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(
                Icons.account_tree,
                size: 14,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: DS.spacing4),
              Text(
                '${entries.length} 位专家协作',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.primary,
                ),
              ),
              const Spacer(),
              if (totalDuration != null)
                Text(
                  _formatDuration(totalDuration),
                  style: TextStyle(
                    fontSize: 11,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          ...entries.asMap().entries.map(
                (entry) => _AgentTimelineRow(
                  entry: entry.value,
                  isLast: entry.key == entries.length - 1,
                ),
              ),
        ],
      ),
    );
  }

  double? get _totalDuration {
    final durations =
        entries.where((item) => item.durationMs != null).map(
              (item) => item.durationMs!,
            );
    if (durations.isEmpty) {
      return null;
    }
    return durations.reduce((value, element) => value + element);
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
                      Icon(_mapAgentIcon(entry.icon),
                          size: 13, color: agentColor,),
                      const SizedBox(width: DS.spacing4),
                      Text(
                        entry.displayName,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: theme.colorScheme.onSurface,
                        ),
                      ),
                      const SizedBox(width: DS.spacing6),
                      _StatusLabel(status: entry.status, color: agentColor),
                      const Spacer(),
                      if (entry.durationMs != null)
                        Text(
                          _formatDuration(entry.durationMs!),
                          style: TextStyle(
                            fontSize: 10,
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                    ],
                  ),
                  if (entry.resultSummary != null) ...[
                    const SizedBox(height: DS.spacing2),
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
        return '分析中';
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
