import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_accessory_pill.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class AssistantAgentBadge extends StatelessWidget {
  const AssistantAgentBadge({
    required this.agentId,
    this.displayName,
    this.colorHex,
    this.iconName,
    this.onTap,
    super.key,
  });

  final String agentId;
  final String? displayName;
  final String? colorHex;
  final String? iconName;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final color = _hexToColor(colorHex) ?? DS.brandPrimary;
    return ChatAccessoryPill(
      icon: _iconForName(iconName),
      label: displayName ?? _labelForAgent(context, agentId),
      accentColor: color,
      onTap: onTap,
    );
  }
}

class ExpertRoundtableWidget extends StatefulWidget {
  const ExpertRoundtableWidget({
    super.key,
    this.routingPreview,
    this.turns = const [],
    this.compact = false,
    this.initiallyCollapsed = false,
    this.autoCollapse = true,
    this.collapseDelay = const Duration(seconds: 4),
    this.collapseId,
  });

  final Map<String, dynamic>? routingPreview;
  final List<Map<String, dynamic>> turns;
  final bool compact;
  final bool initiallyCollapsed;
  final bool autoCollapse;
  final Duration collapseDelay;
  final String? collapseId;

  @override
  State<ExpertRoundtableWidget> createState() => _ExpertRoundtableWidgetState();
}

class _ExpertRoundtableWidgetState extends State<ExpertRoundtableWidget> {
  static final Set<String> _collapsedIds = <String>{};

  Timer? _collapseTimer;
  late bool _isCollapsed;

  String? get _collapseId => widget.collapseId;

  bool get _hasContent =>
      (widget.routingPreview != null && widget.routingPreview!.isNotEmpty) ||
      widget.turns.isNotEmpty;

  @override
  void initState() {
    super.initState();
    _isCollapsed = widget.initiallyCollapsed ||
        (_collapseId != null && _collapsedIds.contains(_collapseId));
    _scheduleAutoCollapse();
  }

  @override
  void didUpdateWidget(covariant ExpertRoundtableWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    final collapseIdChanged = oldWidget.collapseId != widget.collapseId;
    final contentChanged = oldWidget.routingPreview != widget.routingPreview ||
        oldWidget.turns != widget.turns;

    if (collapseIdChanged) {
      _isCollapsed = widget.initiallyCollapsed ||
          (_collapseId != null && _collapsedIds.contains(_collapseId));
    }

    if (collapseIdChanged || contentChanged) {
      _collapseTimer?.cancel();
      _scheduleAutoCollapse();
    }
  }

  @override
  void dispose() {
    _collapseTimer?.cancel();
    super.dispose();
  }

  void _scheduleAutoCollapse() {
    if (!_hasContent || !widget.autoCollapse || _isCollapsed) {
      return;
    }

    _collapseTimer = Timer(widget.collapseDelay, () {
      if (!mounted) return;
      setState(() => _isCollapsed = true);
      if (_collapseId != null) {
        _collapsedIds.add(_collapseId!);
      }
    });
  }

  void _setCollapsed(bool collapsed) {
    _collapseTimer?.cancel();
    setState(() => _isCollapsed = collapsed);
    if (collapsed && _collapseId != null) {
      _collapsedIds.add(_collapseId!);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_hasContent) {
      return const SizedBox.shrink();
    }

    final experts = (widget.routingPreview?['experts'] as List<dynamic>? ??
            const <dynamic>[])
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    final complexityTier =
        widget.routingPreview?['complexity_tier']?.toString();
    final complexityScore =
        (widget.routingPreview?['complexity_score'] as num?)?.toDouble();
    final etaMin = (widget.routingPreview?['eta_seconds_min'] as num?)?.toInt();
    final etaMax = (widget.routingPreview?['eta_seconds_max'] as num?)?.toInt();

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 220),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      child: _isCollapsed
          ? _CollapsedExpertRoundtable(
              key: const ValueKey('collapsed'),
              experts: experts,
              turnCount: widget.turns.length,
              complexityTier: complexityTier,
              onExpand: () => _setCollapsed(false),
            )
          : _ExpandedExpertRoundtable(
              key: const ValueKey('expanded'),
              experts: experts,
              turns: widget.turns,
              compact: widget.compact,
              complexityTier: complexityTier,
              complexityScore: complexityScore,
              etaMin: etaMin,
              etaMax: etaMax,
              onCollapse: () => _setCollapsed(true),
            ),
    );
  }
}

class _CollapsedExpertRoundtable extends StatelessWidget {
  const _CollapsedExpertRoundtable({
    required this.experts,
    required this.turnCount,
    required this.onExpand,
    super.key,
    this.complexityTier,
  });

  final List<Map<String, dynamic>> experts;
  final int turnCount;
  final String? complexityTier;
  final VoidCallback onExpand;

  @override
  Widget build(BuildContext context) {
    final displayedExperts = experts.take(2).toList();
    final remainingExperts = experts.length - displayedExperts.length;

    return Wrap(
      spacing: DS.spacing6,
      runSpacing: DS.spacing6,
      children: [
        ChatAccessoryPill(
          icon: Icons.forum_rounded,
          label: experts.isEmpty
              ? context.l10n.chatRoundtableExpertCollab
              : '专家协作 ${experts.length}位',
          emphasize: true,
          onTap: onExpand,
          trailing: Icon(
            Icons.expand_more_rounded,
            size: 14,
            color: DS.primaryBase,
          ),
        ),
        ...displayedExperts.map(
          (expert) => AssistantAgentBadge(
            agentId: expert['agent_id']?.toString() ?? '',
            displayName: expert['display_name']?.toString(),
            colorHex: expert['color']?.toString(),
            iconName: expert['icon']?.toString(),
            onTap: onExpand,
          ),
        ),
        if (remainingExperts > 0)
          ChatAccessoryPill(
            icon: Icons.add_rounded,
            label: context.l10n.chatRoundtableMoreExperts(remainingExperts),
            onTap: onExpand,
          ),
        if (turnCount > 0)
          ChatAccessoryPill(
            icon: Icons.notes_rounded,
            label: context.l10n.chatRoundtableTurnCount(turnCount),
            onTap: onExpand,
          ),
        if (complexityTier != null && complexityTier!.isNotEmpty)
          ChatAccessoryPill(
            icon: Icons.auto_graph_rounded,
            label: _complexityLabel(context, complexityTier!),
            onTap: onExpand,
          ),
      ],
    );
  }
}

class _ExpandedExpertRoundtable extends StatelessWidget {
  const _ExpandedExpertRoundtable({
    required this.experts,
    required this.turns,
    required this.compact,
    required this.onCollapse,
    super.key,
    this.complexityTier,
    this.complexityScore,
    this.etaMin,
    this.etaMax,
  });

  final List<Map<String, dynamic>> experts;
  final List<Map<String, dynamic>> turns;
  final bool compact;
  final String? complexityTier;
  final double? complexityScore;
  final int? etaMin;
  final int? etaMax;
  final VoidCallback onCollapse;

  @override
  Widget build(BuildContext context) {
    final previewTurns = compact ? turns.take(2).toList() : turns;
    final hiddenTurns = turns.length - previewTurns.length;

    return Container(
      padding: EdgeInsets.all(compact ? 12 : 14),
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? DS.surfacePrimaryElevated
            : const Color(0xFFF7F9FC),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Theme.of(context).brightness == Brightness.dark
              ? DS.borderSubtle
              : const Color(0xFFD8E1EF),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              ChatAccessoryPill(
                icon: Icons.forum_rounded,
                label: context.l10n.chatRoundtableExpertCollab,
                selected: true,
                padding: EdgeInsets.symmetric(
                  horizontal: DS.spacing10,
                  vertical: DS.spacing6,
                ),
              ),
              const Spacer(),
              IconButton(
                onPressed: onCollapse,
                icon: const Icon(Icons.unfold_less_rounded, size: 18),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints.tightFor(
                  width: 28,
                  height: 28,
                ),
                splashRadius: 18,
                color: DS.textSecondary,
                tooltip: '收起',
              ),
            ],
          ),
          if (experts.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing6,
              runSpacing: DS.spacing6,
              children: experts
                  .map(
                    (expert) => AssistantAgentBadge(
                      agentId: expert['agent_id']?.toString() ?? '',
                      displayName: expert['display_name']?.toString(),
                      colorHex: expert['color']?.toString(),
                      iconName: expert['icon']?.toString(),
                    ),
                  )
                  .toList(),
            ),
          ],
          if (complexityTier != null ||
              complexityScore != null ||
              etaMin != null ||
              etaMax != null) ...[
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing6,
              runSpacing: DS.spacing6,
              children: [
                if (complexityTier != null && complexityTier!.isNotEmpty)
                  ChatAccessoryPill(
                    icon: Icons.auto_graph_rounded,
                    label:
                        '${_complexityLabel(context, complexityTier!)}${complexityScore == null ? '' : ' ${(complexityScore! * 100).round()}%'}',
                  ),
                if (etaMin != null || etaMax != null)
                  ChatAccessoryPill(
                    icon: Icons.schedule_rounded,
                    label: _etaLabel(context, etaMin, etaMax),
                  ),
              ],
            ),
          ],
          if (previewTurns.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            ...previewTurns.map(
              (turn) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing8),
                child: _TurnCard(turn: turn),
              ),
            ),
            if (hiddenTurns > 0)
              ChatAccessoryPill(
                icon: Icons.more_horiz_rounded,
                label: context.l10n.chatRoundtableHiddenTurns(hiddenTurns),
              ),
          ],
        ],
      ),
    );
  }
}

class _TurnCard extends StatelessWidget {
  const _TurnCard({required this.turn});

  final Map<String, dynamic> turn;

  @override
  Widget build(BuildContext context) {
    final color = _hexToColor(turn['color']?.toString()) ?? DS.brandPrimary;
    final label = turn['display_name']?.toString() ??
        _labelForAgent(context, turn['agent_id']?.toString() ?? '');
    final content = turn['content']?.toString() ?? '';
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AssistantAgentBadge(
            agentId: turn['agent_id']?.toString() ?? '',
            displayName: label,
            colorHex: turn['color']?.toString(),
            iconName: turn['icon']?.toString(),
          ),
          if (content.trim().isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              content,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: DS.textPrimary,
                height: 1.45,
                fontSize: 12.5,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

String _etaLabel(BuildContext context, int? etaMin, int? etaMax) {
  final low = etaMin ?? etaMax;
  final high = etaMax ?? etaMin;
  if (low == null || high == null)
    return context.l10n.chatRoundtableEstimatedProcessing;
  if (low == high) return context.l10n.chatRoundtableAboutSeconds(low);
  return '$low-$high s';
}

String _complexityLabel(BuildContext context, String tier) {
  switch (tier) {
    case 'high':
      return context.l10n.chatRoundtableHighComplexity;
    case 'medium':
      return context.l10n.chatRoundtableMediumComplexity;
    default:
      return context.l10n.chatRoundtableLowComplexity;
  }
}

String _labelForAgent(BuildContext context, String raw) {
  switch (raw) {
    case 'galaxy_guide':
      return context.l10n.chatRoundtableGalaxyNavigator;
    case 'exam_oracle':
      return context.l10n.chatRoundtableExamStrategist;
    case 'time_tutor':
      return context.l10n.chatRoundtableTimeCoach;
    case 'deep_analyst':
      return context.l10n.chatExpertDeepAnalyst;
    case 'error_analyst':
      return context.l10n.chatRoundtableErrorSpecialist;
    case 'study_buddy':
      return '学伴';
    case 'math_agent':
      return context.l10n.chatExpertMath;
    case 'code_agent':
      return context.l10n.chatExpertCoding;
    case 'writing_agent':
      return context.l10n.chatExpertWriting;
    case 'science_agent':
      return context.l10n.chatRoundtableScienceExpert;
    case 'search_agent':
      return context.l10n.chatExpertSearch;
    case 'orchestrator':
      return context.l10n.chatRoundtableCoordinator;
    case 'synthesis':
      return context.l10n.chatRoundtableConclusion;
    default:
      return raw.replaceAll('_', ' ').trim();
  }
}

IconData _iconForName(String? iconName) {
  switch (iconName) {
    case 'constellation':
      return Icons.auto_awesome_rounded;
    case 'target':
      return Icons.track_changes_rounded;
    case 'clock':
      return Icons.schedule_rounded;
    case 'microscope':
      return Icons.biotech_rounded;
    case 'debug':
      return Icons.bug_report_rounded;
    case 'handshake':
      return Icons.diversity_3_rounded;
    case 'calculator':
      return Icons.calculate_rounded;
    case 'code':
      return Icons.code_rounded;
    case 'pen':
      return Icons.edit_rounded;
    case 'flask':
      return Icons.science_rounded;
    case 'search':
      return Icons.search_rounded;
    case 'layers':
      return Icons.layers_rounded;
    default:
      return Icons.smart_toy_rounded;
  }
}

Color? _hexToColor(String? hex) {
  if (hex == null || hex.isEmpty) return null;
  final cleaned = hex.replaceFirst('#', '');
  final normalized = cleaned.length == 6 ? 'FF$cleaned' : cleaned;
  final parsed = int.tryParse(normalized, radix: 16);
  if (parsed == null) return null;
  return Color(parsed);
}
