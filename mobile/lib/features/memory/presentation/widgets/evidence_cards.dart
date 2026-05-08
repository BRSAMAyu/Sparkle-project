import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class EvidenceCard extends StatefulWidget {
  const EvidenceCard({
    required this.item,
    this.onRouteTap,
    this.compact = false,
    super.key,
  });

  final EvidenceResolveItem item;
  final ValueChanged<String>? onRouteTap;
  final bool compact;

  @override
  State<EvidenceCard> createState() => _EvidenceCardState();
}

class _EvidenceCardState extends State<EvidenceCard> {
  bool _showDetails = false;
  bool _showAll = false;

  @override
  Widget build(BuildContext context) {
    final item = widget.item;
    final confidence = _computeConfidence(item);
    final routeAction = _buildRouteAction();
    final statusColor = _statusColor(item.status);

    return Card(
      margin: EdgeInsets.only(bottom: widget.compact ? DS.spacing6 : DS.sm),
      child: Padding(
        padding: EdgeInsets.all(widget.compact ? DS.spacing10 : DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Tier 1: Summary row (always visible)
            _Tier1Summary(
              item: item,
              confidence: confidence,
              statusColor: statusColor,
              onToggleDetails: () => setState(() => _showDetails = !_showDetails),
              showDetails: _showDetails,
            ),
            // Tier 2: Key fields (expandable)
            if (_showDetails) ...[
              const SizedBox(height: DS.spacing10),
              _buildKeyFields(context, item),
              // Tier 3: Show all raw data toggle
              if (_hasExtraFields(item)) ...[
                const SizedBox(height: DS.spacing6),
                _ShowAllToggle(
                  showAll: _showAll,
                  onToggle: () => setState(() => _showAll = !_showAll),
                ),
                if (_showAll) ...[
                  const SizedBox(height: DS.spacing6),
                  _buildAllFields(context, item),
                ],
              ],
              // Go to source button
              if (routeAction != null) ...[
                const SizedBox(height: DS.spacing10),
                Align(
                  alignment: Alignment.centerLeft,
                  child: FilledButton.tonalIcon(
                    onPressed: () => _dispatchRoute(context, routeAction.route),
                    icon: const Icon(Icons.open_in_new_rounded, size: DS.iconSizeXs),
                    label: Text(routeAction.label),
                    style: FilledButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing10,
                        vertical: DS.spacing6,
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  double _computeConfidence(EvidenceResolveItem item) {
    if (item.status == 'missing') return 0.0;
    if (item.status == 'redacted') return 0.35;
    final payload = item.payload;
    if (payload == null || payload.isEmpty) return 0.5;
    var richness = 0;
    for (final value in payload.values) {
      if (value is Map && value.isNotEmpty) richness++;
    }
    return (0.6 + richness * 0.1).clamp(0.0, 1.0);
  }

  Color _statusColor(String status) => switch (status) {
        'ok' => DS.semanticSuccess,
        'redacted' => DS.semanticWarning,
        _ => DS.semanticError,
      };

  Widget _buildKeyFields(BuildContext context, EvidenceResolveItem item) {
    if (item.status != 'ok') {
      return Text(
        item.redactionReason ?? context.l10n.memEvidenceParseFail,
        style: DS.bodySmall.copyWith(color: DS.textSecondary),
      );
    }
    final payload = item.payload ?? const {};
    final pairs = _extractKeyPairs(payload);
    if (pairs.isEmpty) {
      return Text(context.l10n.memEvidenceRecord, style: DS.bodySmall);
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: pairs
          .take(4)
          .map((pair) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 80,
                      child: Text(
                        pair.key,
                        style: DS.labelSmall.copyWith(color: DS.textSecondary),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        pair.value,
                        style: DS.bodySmall.copyWith(color: DS.textPrimary),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ))
          .toList(),
    );
  }

  Widget _buildAllFields(BuildContext context, EvidenceResolveItem item) {
    final payload = item.payload ?? const {};
    final pairs = _extractKeyPairs(payload);
    if (pairs.length <= 4) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: pairs
          .skip(4)
          .map((pair) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 80,
                      child: Text(
                        pair.key,
                        style: DS.labelSmall.copyWith(color: DS.textSecondary),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        pair.value,
                        style: DS.bodySmall.copyWith(color: DS.textPrimary),
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ))
          .toList(),
    );
  }

  bool _hasExtraFields(EvidenceResolveItem item) {
    final payload = item.payload ?? const {};
    return _extractKeyPairs(payload).length > 4;
  }

  List<_KVPair> _extractKeyPairs(Map<String, dynamic> payload) {
    final pairs = <_KVPair>[];
    for (final entry in payload.entries) {
      if (entry.value is Map<String, dynamic>) {
        final inner = entry.value as Map<String, dynamic>;
        for (final innerEntry in inner.entries) {
          final v = innerEntry.value?.toString().trim() ?? '';
          if (v.isNotEmpty && v != '-') {
            pairs.add(_KVPair(_fieldLabel(innerEntry.key), v));
          }
        }
      }
    }
    return pairs;
  }

  String _fieldLabel(String key) {
    final labels = <String, String>{
      'event_type': I18nService.instance.isChinese ? '类型' : 'Type',
      'ts_ms': I18nService.instance.isChinese ? '时间' : 'Time',
      'role': I18nService.instance.isChinese ? '角色' : 'Role',
      'created_at': I18nService.instance.isChinese ? '创建' : 'Created',
      'content': I18nService.instance.isChinese ? '内容' : 'Content',
      'subject_code': I18nService.instance.isChinese ? '科目' : 'Subject',
      'root_cause': I18nService.instance.isChinese ? '根因' : 'Root cause',
      'study_suggestion': I18nService.instance.isChinese ? '建议' : 'Suggestion',
      'review_performance': I18nService.instance.isChinese ? '表现' : 'Performance',
      'mastery_level': I18nService.instance.isChinese ? '掌握' : 'Mastery',
      'reviewed_at': I18nService.instance.isChinese ? '复习时间' : 'Reviewed',
      'summary': I18nService.instance.isChinese ? '摘要' : 'Summary',
      'summary_text': I18nService.instance.isChinese ? '摘要' : 'Summary',
      'review_date': I18nService.instance.isChinese ? '日期' : 'Date',
      'name': I18nService.instance.isChinese ? '名称' : 'Name',
      'description': I18nService.instance.isChinese ? '描述' : 'Description',
      'title': I18nService.instance.isChinese ? '标题' : 'Title',
      'status': I18nService.instance.isChinese ? '状态' : 'Status',
      'due_date': I18nService.instance.isChinese ? '截止' : 'Due',
      'focus_mode': I18nService.instance.isChinese ? '专注' : 'Focus',
      'cognitive_load': I18nService.instance.isChinese ? '负荷' : 'Load',
      'sprint_mode': I18nService.instance.isChinese ? '冲刺' : 'Sprint',
    };
    return labels[key] ?? key;
  }

  _EvidenceRouteAction? _buildRouteAction() {
    if (widget.item.status != 'ok') return null;
    final payload = widget.item.payload ?? const {};
    final concept = payload['concept'] as Map<String, dynamic>?;
    if (concept != null) {
      final nodeId = (concept['id'] ?? widget.item.id).toString().trim();
      if (nodeId.isNotEmpty) {
        return _EvidenceRouteAction(
          route: '/galaxy/node/$nodeId',
          label: S.memGoGalaxy,
        );
      }
    }
    final error = payload['error'] as Map<String, dynamic>?;
    if (error != null) {
      final errorId = (error['id'] ?? widget.item.id).toString().trim();
      if (errorId.isNotEmpty) {
        return _EvidenceRouteAction(
          route: '/errors/$errorId',
          label: S.memGoErrorBook,
        );
      }
    }
    final outcome = payload['practice_outcome'] as Map<String, dynamic>?;
    if (outcome != null) {
      final errorId = (outcome['error_id'] ?? widget.item.id).toString().trim();
      if (errorId.isNotEmpty) {
        return _EvidenceRouteAction(
          route: '/errors/$errorId',
          label: S.memBackToErrorBook,
        );
      }
    }
    final event = payload['event'] as Map<String, dynamic>?;
    if (event != null) {
      final sessionId = _extractSessionId(event);
      if (sessionId.isNotEmpty) {
        return _EvidenceRouteAction(
          route: '/chat?session_id=$sessionId',
          label: S.memOpenRelatedChat,
        );
      }
    }
    final chatTurn = payload['chat_turn'] as Map<String, dynamic>?;
    if (chatTurn != null) {
      final sessionId = (chatTurn['session_id'] ?? '').toString().trim();
      if (sessionId.isNotEmpty) {
        return _EvidenceRouteAction(
          route: '/chat?session_id=$sessionId',
          label: S.memOpenOriginalChat,
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
      if (normalized.isNotEmpty) return normalized;
    }
    return '';
  }

  void _dispatchRoute(BuildContext context, String route) {
    if (widget.onRouteTap != null) {
      widget.onRouteTap!(route);
      return;
    }
    context.go(route);
  }
}

class _KVPair {
  const _KVPair(this.key, this.value);
  final String key;
  final String value;
}

class _Tier1Summary extends StatelessWidget {
  const _Tier1Summary({
    required this.item,
    required this.confidence,
    required this.statusColor,
    required this.onToggleDetails,
    required this.showDetails,
  });

  final EvidenceResolveItem item;
  final double confidence;
  final Color statusColor;
  final VoidCallback onToggleDetails;
  final bool showDetails;

  @override
  Widget build(BuildContext context) {
    final summary = _buildSummary(context);
    return Semantics(
      button: true,
      label: I18nService.instance.isChinese ? '展开证据详情' : 'Expand evidence details',
      child: InkWell(
      onTap: onToggleDetails,
      borderRadius: DS.borderRadius8,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing4),
        child: Row(
          children: [
            _StatusDot(color: statusColor),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    summary,
                    style: DS.bodySmall.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightMedium,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: DS.spacing4),
                  _ConfidenceBar(confidence: confidence),
                ],
              ),
            ),
            const SizedBox(width: DS.spacing8),
            AnimatedRotation(
              turns: showDetails ? 0.5 : 0.0,
              duration: const Duration(milliseconds: 200),
              child: Icon(
                Icons.expand_more_rounded,
                size: DS.iconSizeXs,
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
      ),
      ),
    );
  }

  String _buildSummary(BuildContext context) {
    if (item.status == 'missing') {
      return I18nService.instance.isChinese ? '证据缺失' : 'Evidence missing';
    }
    if (item.status == 'redacted') {
      return item.redactionReason ??
          (I18nService.instance.isChinese ? '证据已隐藏' : 'Evidence redacted');
    }
    final payload = item.payload ?? const {};
    final concept = payload['concept'] as Map<String, dynamic>?;
    if (concept != null) {
      final name = concept['name']?.toString() ?? '';
      return name.isNotEmpty
          ? '${I18nService.instance.isChinese ? '概念' : 'Concept'}: $name'
          : context.l10n.memEvidenceRecord;
    }
    final error = payload['error'] as Map<String, dynamic>?;
    if (error != null) {
      final subject = error['subject_code']?.toString() ?? '';
      return subject.isNotEmpty
          ? '${I18nService.instance.isChinese ? '错题' : 'Error'}: $subject'
          : context.l10n.memEvidenceRecord;
    }
    final task = payload['task'] as Map<String, dynamic>?;
    if (task != null) {
      final title = task['title']?.toString() ?? '';
      return title.isNotEmpty
          ? '${I18nService.instance.isChinese ? '任务' : 'Task'}: $title'
          : context.l10n.memEvidenceRecord;
    }
    final event = payload['event'] as Map<String, dynamic>?;
    if (event != null) {
      final eventType = event['event_type']?.toString() ?? '';
      return eventType.isNotEmpty
          ? '${I18nService.instance.isChinese ? '事件' : 'Event'}: $eventType'
          : context.l10n.memEvidenceRecord;
    }
    final practiceOutcome = payload['practice_outcome'] as Map<String, dynamic>?;
    if (practiceOutcome != null) {
      final summary = practiceOutcome['summary']?.toString() ?? '';
      final perf = practiceOutcome['review_performance']?.toString() ?? '';
      final label = summary.isNotEmpty
          ? summary
          : perf.isNotEmpty
              ? '${I18nService.instance.isChinese ? '练习结果' : 'Practice'}: $perf'
              : '';
      if (label.isNotEmpty) return label;
    }
    final chatTurn = payload['chat_turn'] as Map<String, dynamic>?;
    if (chatTurn != null) {
      final role = chatTurn['role']?.toString() ?? '';
      return role.isNotEmpty
          ? '${I18nService.instance.isChinese ? '对话' : 'Chat'} ($role)'
          : context.l10n.memEvidenceRecord;
    }
    return context.l10n.memEvidenceRecord;
  }
}

class _StatusDot extends StatelessWidget {
  const _StatusDot({required this.color});
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: 0.4),
              blurRadius: 4,
              spreadRadius: 0,
            ),
          ],
        ),
      );
}

class _ConfidenceBar extends StatelessWidget {
  const _ConfidenceBar({required this.confidence});
  final double confidence;

  @override
  Widget build(BuildContext context) {
    final color = confidence >= 0.7
        ? DS.semanticSuccess
        : confidence >= 0.35
            ? DS.semanticWarning
            : DS.semanticError;
    return Container(
      height: 3,
      decoration: BoxDecoration(
        color: DS.borderSubtle,
        borderRadius: BorderRadius.circular(2),
      ),
      child: FractionallySizedBox(
        alignment: Alignment.centerLeft,
        widthFactor: confidence.clamp(0.0, 1.0),
        child: Container(
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
      ),
    );
  }
}

class _ShowAllToggle extends StatelessWidget {
  const _ShowAllToggle({required this.showAll, required this.onToggle});
  final bool showAll;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    return GestureDetector(
      onTap: onToggle,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            showAll ? Icons.unfold_less_rounded : Icons.unfold_more_rounded,
            size: DS.iconSizeXs,
            color: DS.textSecondary,
          ),
          const SizedBox(width: DS.spacing4),
          Text(
            showAll
                ? (zh ? '收起详情' : 'Show less')
                : (zh ? '查看全部' : 'Show all'),
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _EvidenceRouteAction {
  const _EvidenceRouteAction({required this.route, required this.label});
  final String route;
  final String label;
}
