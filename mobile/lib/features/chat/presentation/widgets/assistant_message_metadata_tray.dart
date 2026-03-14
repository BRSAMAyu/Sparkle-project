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

    if (widget.status != null && widget.status!.trim().isNotEmpty) {
      badges.add(
        _MetadataBadge(
          icon: _statusIcon(widget.status!),
          label: '',
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
          label: '延续',
          selected: _expandedKey == continuity.type,
          onTap: () => _toggle(continuity.type),
        ),
      );
    }
    if (mode != null) {
      badges.add(
        _MetadataBadge(
          icon: Icons.auto_awesome_rounded,
          label: _shortModeLabel(mode.data),
          selected: _expandedKey == mode.type,
          onTap: () => _toggle(mode.type),
        ),
      );
    }
    if (sources != null) {
      badges.add(
        _MetadataBadge(
          icon: Icons.bookmark_border_rounded,
          label: '来源',
          selected: _expandedKey == sources.type,
          onTap: () => _toggle(sources.type),
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
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
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
        final message = continuity?.data['message']?.toString().trim() ?? '';
        if (message.isEmpty) return const SizedBox.shrink();
        return _MetadataPanel(
          key: const ValueKey('continuity_banner'),
          child: Text(
            message,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textPrimary,
                  height: 1.45,
                ),
          ),
        );
      case 'mode_explanation':
        final label = mode?.data['label']?.toString().trim() ?? '';
        final description = mode?.data['description']?.toString().trim() ?? '';
        if (label.isEmpty && description.isEmpty) return const SizedBox.shrink();
        return _MetadataPanel(
          key: const ValueKey('mode_explanation'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (label.isNotEmpty)
                Text(
                  label,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightSemibold,
                      ),
                ),
              if (description.isNotEmpty) ...[
                if (label.isNotEmpty) const SizedBox(height: DS.spacing4),
                Text(
                  description,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                        height: 1.4,
                      ),
                ),
              ],
            ],
          ),
        );
      case 'source_summary':
        if (sources == null) return const SizedBox.shrink();
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

  void _toggle(String key) {
    setState(() {
      _expandedKey = _expandedKey == key ? null : key;
    });
  }

  String _shortModeLabel(Map<String, dynamic> data) {
    final label = data['label']?.toString().trim() ?? '';
    if (label.isEmpty) return '协作';
    if (label.length <= 6) return label;
    return '${label.substring(0, 6)}...';
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
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final bool isCompact;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: EdgeInsets.symmetric(
            horizontal: isCompact ? DS.spacing8 : DS.spacing10,
            vertical: DS.spacing6,
          ),
          decoration: BoxDecoration(
            color: selected
                ? DS.primaryBase.withValues(alpha: 0.12)
                : DS.surfacePanel,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: selected
                  ? DS.primaryBase.withValues(alpha: 0.28)
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
              if (!isCompact && label.trim().isNotEmpty) ...[
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
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing8),
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
}

class _SourceSummaryContent extends StatelessWidget {
  const _SourceSummaryContent({required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final headline = data['headline']?.toString().trim() ?? '';
    final focus = data['first_screen_focus']?.toString().trim() ?? '';
    final evidenceSummary = data['evidence_summary']?.toString().trim() ?? '';
    final citations = (data['citations'] as List<dynamic>? ?? const [])
        .whereType<Map<Object?, Object?>>()
        .map((item) => Map<String, dynamic>.from(item))
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
        if (focus.isNotEmpty) ...[
          if (headline.isNotEmpty) const SizedBox(height: DS.spacing6),
          Text(
            focus,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
        ],
        if (evidenceSummary.isNotEmpty) ...[
          if (headline.isNotEmpty || focus.isNotEmpty)
            const SizedBox(height: DS.spacing8),
          Text(
            evidenceSummary,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textPrimary,
                  height: 1.45,
                ),
          ),
        ],
        if (citations.isNotEmpty) ...[
          const SizedBox(height: DS.spacing10),
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
                          citation['title']?.toString().trim().isNotEmpty == true
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
        .map((item) => Map<String, dynamic>.from(item))
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
