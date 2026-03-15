import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';

class AssistantMessageMetadataTray extends StatefulWidget {
  const AssistantMessageMetadataTray({
    required this.actions,
    required this.isLatestMessage,
    super.key,
    this.status,
    this.onWidgetAction,
  });

  final List<WidgetPayload> actions;
  final bool isLatestMessage;
  final String? status;
  final Future<void> Function(String actionType, Map<String, dynamic> payload)?
      onWidgetAction;

  @override
  State<AssistantMessageMetadataTray> createState() =>
      _AssistantMessageMetadataTrayState();
}

class _AssistantMessageMetadataTrayState
    extends State<AssistantMessageMetadataTray> {
  String? _expandedKey;

  @override
  Widget build(BuildContext context) {
    final badges = <Widget>[];
    final continuity = _findAction('continuity_banner');
    final mode = _findAction('mode_explanation');
    final sources = _findAction('source_summary');
    final nextActions =
        widget.isLatestMessage ? _findAction('next_actions') : null;
    final hasSources = _hasSourceDetails(sources?.data);

    if (widget.status != null && widget.status!.trim().isNotEmpty) {
      badges.add(
        _MetadataBadge(
          icon: _statusIcon(widget.status!),
          label: _statusLabel(widget.status!),
          isCompact: true,
          selected: _expandedKey == 'status',
          onTap: () => _toggle('status'),
        ),
      );
    }
    if (continuity != null) {
      badges.add(
        _MetadataBadge(
          icon: Icons.link_rounded,
          label: '承接上文',
          selected: false,
          onTap: () {},
          enabled: false,
        ),
      );
    }
    if (mode != null) {
      badges.add(
        _MetadataBadge(
          icon: Icons.auto_awesome_rounded,
          label: _shortModeLabel(mode.data),
          selected: false,
          onTap: () {},
          enabled: false,
        ),
      );
    }
    if (sources != null && hasSources) {
      badges.add(
        _MetadataBadge(
          icon: Icons.library_books_outlined,
          label: '依据',
          selected: _expandedKey == sources.type,
          onTap: () => _toggle(sources.type),
          iconOnlyWhenCollapsed: true,
        ),
      );
    }
    if (nextActions != null && _hasActionItems(nextActions.data)) {
      badges.add(
        _MetadataBadge(
          icon: Icons.bookmark_added_rounded,
          label: '下一步',
          selected: _expandedKey == nextActions.type,
          onTap: () => _toggle(nextActions.type),
          iconOnlyWhenCollapsed: true,
          emphasize: true,
        ),
      );
    }

    if (badges.isEmpty) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: DS.spacing6,
            runSpacing: DS.spacing6,
            children: badges,
          ),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 180),
            switchInCurve: Curves.easeOutCubic,
            switchOutCurve: Curves.easeInCubic,
            child: _buildPanel(
              context,
              continuity: continuity,
              mode: mode,
              sources: sources,
              nextActions: nextActions,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPanel(
    BuildContext context, {
    WidgetPayload? continuity,
    WidgetPayload? mode,
    WidgetPayload? sources,
    WidgetPayload? nextActions,
  }) {
    switch (_expandedKey) {
      case 'status':
        final status = widget.status?.trim() ?? '';
        if (status.isEmpty) return const SizedBox.shrink();
        return _MetadataPanel(
          key: const ValueKey('status'),
          child: Text(
            _statusLabel(status),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textPrimary,
                  height: 1.4,
                ),
          ),
        );
      case 'continuity_banner':
        return const SizedBox.shrink();
      case 'mode_explanation':
        return const SizedBox.shrink();
      case 'source_summary':
        if (sources == null || !_hasSourceDetails(sources.data)) {
          return const SizedBox.shrink();
        }
        return _MetadataPanel(
          key: const ValueKey('source_summary'),
          child: _SourceSummaryContent(data: sources.data),
        );
      case 'next_actions':
        if (nextActions == null || !_hasActionItems(nextActions.data)) {
          return const SizedBox.shrink();
        }
        return _MetadataPanel(
          key: const ValueKey('next_actions'),
          child: _NextActionsContent(
            data: nextActions.data,
            onWidgetAction: widget.onWidgetAction,
          ),
        );
      default:
        return const SizedBox.shrink();
    }
  }

  WidgetPayload? _findAction(String type) {
    for (final action in widget.actions) {
      if (action.type == type) {
        return action;
      }
    }
    return null;
  }

  bool _hasActionItems(Map<String, dynamic> data) {
    final actions = data['actions'];
    return actions is List && actions.isNotEmpty;
  }

  bool _hasSourceDetails(Map<String, dynamic>? data) {
    if (data == null) return false;
    final citations = data['citations'];
    if (citations is List && citations.isNotEmpty) {
      return true;
    }
    final headline = data['headline']?.toString().trim() ?? '';
    final evidenceSummary = data['evidence_summary']?.toString().trim() ?? '';
    return headline.isNotEmpty || evidenceSummary.isNotEmpty;
  }

  void _toggle(String key) {
    setState(() {
      _expandedKey = _expandedKey == key ? null : key;
    });
  }

  String _shortModeLabel(Map<String, dynamic> data) {
    final label = data['label']?.toString().trim() ?? '';
    if (label.isEmpty) return '协作';
    if (label.length <= 4) return label;
    return '${label.substring(0, 4)}…';
  }

  IconData _statusIcon(String status) {
    switch (status.toUpperCase()) {
      case 'THINKING':
        return Icons.hourglass_top_rounded;
      case 'SEARCHING':
        return Icons.travel_explore_rounded;
      case 'EXECUTING_TOOL':
        return Icons.build_circle_outlined;
      case 'GENERATING':
        return Icons.auto_awesome_motion_rounded;
      case 'IDLE':
        return Icons.check_circle_outline_rounded;
      default:
        return Icons.circle_notifications_rounded;
    }
  }

  String _statusLabel(String status) {
    switch (status.toUpperCase()) {
      case 'THINKING':
        return '正在思考';
      case 'SEARCHING':
        return '正在检索';
      case 'EXECUTING_TOOL':
        return '正在调用工具';
      case 'GENERATING':
        return '正在生成';
      case 'IDLE':
        return '已完成';
      default:
        return status;
    }
  }
}

class _MetadataBadge extends StatelessWidget {
  const _MetadataBadge({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
    this.isCompact = false,
    this.iconOnlyWhenCollapsed = false,
    this.enabled = true,
    this.emphasize = false,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final bool isCompact;
  final bool iconOnlyWhenCollapsed;
  final bool enabled;
  final bool emphasize;

  @override
  Widget build(BuildContext context) {
    final showLabel = !isCompact &&
        label.trim().isNotEmpty &&
        (!iconOnlyWhenCollapsed || selected);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: enabled ? onTap : null,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: EdgeInsets.symmetric(
            horizontal: isCompact
                ? DS.spacing8
                : (showLabel ? DS.spacing10 : DS.spacing8),
            vertical: emphasize ? DS.spacing8 : DS.spacing6,
          ),
          decoration: BoxDecoration(
            color: selected
                ? DS.primaryBase.withValues(alpha: 0.12)
                : emphasize
                    ? DS.primaryBase.withValues(alpha: 0.08)
                    : DS.surfacePanel,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: selected
                  ? DS.primaryBase.withValues(alpha: 0.28)
                  : emphasize
                      ? DS.primaryBase.withValues(alpha: 0.22)
                      : DS.borderSubtle,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: DS.iconSizeXs,
                color: selected ? DS.primaryBase : DS.textSecondary,
              ),
              if (showLabel) ...[
                const SizedBox(width: DS.spacing4),
                Text(
                  label,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: selected ? DS.primaryBase : DS.textSecondary,
                        fontWeight: DS.fontWeightMedium,
                      ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _MetadataPanel extends StatelessWidget {
  const _MetadataPanel({
    required this.child,
    super.key,
  });

  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.only(top: DS.spacing6),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfacePanel,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing12),
          child: child,
        ),
      ),
    );
}

class _SourceSummaryContent extends StatelessWidget {
  const _SourceSummaryContent({required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final headline = data['headline']?.toString().trim() ?? '';
    final citations = (data['citations'] as List<dynamic>? ?? const [])
        .whereType<Map<Object?, Object?>>()
        .map(Map<String, dynamic>.from)
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (headline.isNotEmpty)
          Text(
            headline,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
        if (citations.isNotEmpty) ...[
          if (headline.isNotEmpty) const SizedBox(height: DS.spacing8),
          ...citations.take(3).map(
                (citation) => Padding(
                  padding: const EdgeInsets.only(bottom: DS.spacing8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.subdirectory_arrow_right_rounded,
                        size: DS.iconSizeXs,
                        color: DS.textSecondary,
                      ),
                      const SizedBox(width: DS.spacing4),
                      Expanded(
                        child: Text(
                          citation['title']?.toString().trim().isNotEmpty ?? false
                              ? citation['title'].toString()
                              : (citation['content']?.toString() ?? ''),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: DS.textSecondary,
                                  ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
        ],
      ],
    );
  }
}

class _NextActionsContent extends StatelessWidget {
  const _NextActionsContent({
    required this.data,
    required this.onWidgetAction,
  });

  final Map<String, dynamic> data;
  final Future<void> Function(String actionType, Map<String, dynamic> payload)?
      onWidgetAction;

  @override
  Widget build(BuildContext context) {
    final actions = (data['actions'] as List<dynamic>? ?? const [])
        .whereType<Map<Object?, Object?>>()
        .map(Map<String, dynamic>.from)
        .toList();

    return Wrap(
      spacing: DS.spacing8,
      runSpacing: DS.spacing8,
      children: actions.map((action) {
        final label = action['label']?.toString().trim() ?? '';
        final actionType = action['type']?.toString().trim() ?? 'prompt';
        if (label.isEmpty) {
          return const SizedBox.shrink();
        }
        return ActionChip(
          avatar: const Icon(Icons.arrow_outward_rounded, size: DS.iconSizeXs),
          label: Text(label),
          onPressed: onWidgetAction == null
              ? null
              : () => unawaited(onWidgetAction!(actionType, action)),
        );
      }).toList(),
    );
  }
}
