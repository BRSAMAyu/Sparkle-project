import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';

class EvidenceCard extends StatelessWidget {
  const EvidenceCard({
    required this.item,
    this.onRouteTap,
    super.key,
  });

  final EvidenceResolveItem item;
  final ValueChanged<String>? onRouteTap;

  @override
  Widget build(BuildContext context) {
    final content = _buildContent(context);
    final routeAction = _buildRouteAction();
    return Card(
      margin: const EdgeInsets.only(bottom: DS.sm),
      child: Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text('${item.type} · ${item.id}',
                    style: Theme.of(context).textTheme.bodyMedium,),
                const Spacer(),
                _StatusBadge(status: item.status),
              ],
            ),
            const SizedBox(height: DS.sm),
            content,
            if (routeAction != null) ...[
              const SizedBox(height: DS.sm),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: () => _dispatchRoute(context, routeAction.route),
                  icon: const Icon(Icons.open_in_new_rounded),
                  label: Text(routeAction.label),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context) {
    if (item.status != 'ok') {
      return Text(item.redactionReason ?? '无法解析证据');
    }
    final payload = item.payload ?? const {};
    if (payload['event'] != null) {
      final event = payload['event'] as Map<String, dynamic>;
      return _KeyValueList(items: {
        'Type': event['event_type']?.toString() ?? '-',
        'Timestamp': event['ts_ms']?.toString() ?? '-',
      },);
    }
    if (payload['error'] != null) {
      final error = payload['error'] as Map<String, dynamic>;
      return _KeyValueList(items: {
        'Subject': error['subject_code']?.toString() ?? '-',
        'Root Cause': error['root_cause']?.toString() ?? '-',
        'Suggestion': error['study_suggestion']?.toString() ?? '-',
      },);
    }
    if (payload['practice_outcome'] != null) {
      final outcome = payload['practice_outcome'] as Map<String, dynamic>;
      return _KeyValueList(items: {
        'Performance': outcome['review_performance']?.toString() ?? '-',
        'Mastery': outcome['mastery_level']?.toString() ?? '-',
        'Reviewed': outcome['reviewed_at']?.toString() ?? '-',
        'Summary': outcome['summary']?.toString() ?? '-',
      },);
    }
    if (payload['concept'] != null) {
      final concept = payload['concept'] as Map<String, dynamic>;
      return _KeyValueList(items: {
        'Name': concept['name']?.toString() ?? '-',
        'Description': concept['description']?.toString() ?? '-',
      },);
    }
    if (payload['task'] != null) {
      final task = payload['task'] as Map<String, dynamic>;
      return _KeyValueList(items: {
        'Title': task['title']?.toString() ?? '-',
        'Status': task['status']?.toString() ?? '-',
        'Due': task['due_date']?.toString() ?? '-',
      },);
    }
    if (payload['summary'] != null) {
      final summary = payload['summary'] as Map<String, dynamic>;
      return _KeyValueList(items: {
        'Date': summary['review_date']?.toString() ?? '-',
        'Summary': summary['summary_text']?.toString() ?? '-',
      },);
    }
    if (payload['state'] != null) {
      final state = payload['state'] as Map<String, dynamic>;
      return _KeyValueList(items: {
        'Focus': state['focus_mode']?.toString() ?? '-',
        'Load': state['cognitive_load']?.toString() ?? '-',
        'Sprint': state['sprint_mode']?.toString() ?? '-',
      },);
    }
    return const Text('证据记录');
  }

  _EvidenceRouteAction? _buildRouteAction() {
    if (item.status != 'ok') {
      return null;
    }
    final payload = item.payload ?? const {};
    final concept = payload['concept'] as Map<String, dynamic>?;
    if (concept != null) {
      final nodeId = (concept['id'] ?? item.id).toString().trim();
      if (nodeId.isNotEmpty) {
        return _EvidenceRouteAction(
          route: '/galaxy/node/$nodeId',
          label: '去星图看',
        );
      }
    }

    final error = payload['error'] as Map<String, dynamic>?;
    if (error != null) {
      final errorId = (error['id'] ?? item.id).toString().trim();
      if (errorId.isNotEmpty) {
        return _EvidenceRouteAction(
          route: '/errors/$errorId',
          label: '去错题本看',
        );
      }
    }

    final outcome = payload['practice_outcome'] as Map<String, dynamic>?;
    if (outcome != null) {
      final errorId = (outcome['error_id'] ?? item.id).toString().trim();
      if (errorId.isNotEmpty) {
        return _EvidenceRouteAction(
          route: '/errors/$errorId',
          label: '回到错题本看',
        );
      }
    }

    final event = payload['event'] as Map<String, dynamic>?;
    if (event != null) {
      final sessionId = _extractSessionId(event);
      if (sessionId.isNotEmpty) {
        return _EvidenceRouteAction(
          route: '/chat?session_id=$sessionId',
          label: '打开相关对话',
        );
      }
    }
    return null;
  }

  String _extractSessionId(Map<String, dynamic> event) {
    final candidates = <Object?>[
      event['session_id'],
      event['conversation_id'],
      (event['payload'] as Map<String, dynamic>?)?['session_id'],
      (event['payload'] as Map<String, dynamic>?)?['conversation_id'],
      (event['entities'] as Map<String, dynamic>?)?['session_id'],
      (event['entities'] as Map<String, dynamic>?)?['conversation_id'],
    ];
    for (final candidate in candidates) {
      final normalized = candidate?.toString().trim() ?? '';
      if (normalized.isNotEmpty) {
        return normalized;
      }
    }
    return '';
  }

  void _dispatchRoute(BuildContext context, String route) {
    if (onRouteTap != null) {
      onRouteTap!(route);
      return;
    }
    context.go(route);
  }
}

class _KeyValueList extends StatelessWidget {
  const _KeyValueList({required this.items});

  final Map<String, String> items;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: items.entries
            .map(
              (entry) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text('${entry.key}: ${_truncate(entry.value)}'),
              ),
            )
            .toList(),
      );

  String _truncate(String value) {
    if (value.length <= 120) {
      return value;
    }
    return '${value.substring(0, 120)}...';
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final label = switch (status) {
      'ok' => 'OK',
      'redacted' => '已隐藏',
      _ => '缺失',
    };
    final color = switch (status) {
      'ok' => DS.semanticSuccess,
      'redacted' => DS.semanticWarning,
      _ => DS.semanticError,
    };
    return Chip(
      label: Text(label, style: TextStyle(color: color)),
      backgroundColor: color.withValues(alpha: 0.12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: color.withValues(alpha: 0.4)),
      ),
    );
  }
}

class _EvidenceRouteAction {
  const _EvidenceRouteAction({
    required this.route,
    required this.label,
  });

  final String route;
  final String label;
}
