import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class AssistantAgentBadge extends StatelessWidget {
  const AssistantAgentBadge({
    required this.agentId,
    this.displayName,
    this.colorHex,
    this.iconName,
    super.key,
  });

  final String agentId;
  final String? displayName;
  final String? colorHex;
  final String? iconName;

  @override
  Widget build(BuildContext context) {
    final color = _hexToColor(colorHex) ?? DS.brandPrimary;
    return Container(
      margin: const EdgeInsets.only(bottom: DS.spacing8),
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(_iconForName(iconName), size: 14, color: color),
          const SizedBox(width: DS.spacing6),
          Text(
            displayName ?? _labelForAgent(agentId),
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class ExpertRoundtableWidget extends StatelessWidget {
  const ExpertRoundtableWidget({
    super.key,
    this.routingPreview,
    this.turns = const [],
    this.compact = false,
  });

  final Map<String, dynamic>? routingPreview;
  final List<Map<String, dynamic>> turns;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    if ((routingPreview == null || routingPreview!.isEmpty) && turns.isEmpty) {
      return const SizedBox.shrink();
    }

    final experts = (routingPreview?['experts'] as List<dynamic>? ?? const [])
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    final complexityTier = routingPreview?['complexity_tier']?.toString();
    final complexityScore =
        (routingPreview?['complexity_score'] as num?)?.toDouble();
    final etaMin = (routingPreview?['eta_seconds_min'] as num?)?.toInt();
    final etaMax = (routingPreview?['eta_seconds_max'] as num?)?.toInt();

    return Container(
      padding: EdgeInsets.all(compact ? 12 : 14),
      decoration: BoxDecoration(
        color: const Color(0xFFF6F8FC),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFDCE4F2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Icon(
                  Icons.forum_rounded,
                  size: 16,
                  color: DS.brandPrimary,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                '专家圆桌',
                style: TextStyle(
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.textPrimary,
                ),
              ),
              const Spacer(),
              if (complexityTier != null && complexityTier.isNotEmpty)
                _InfoChip(
                  label: '${_complexityLabel(complexityTier)}'
                      '${complexityScore != null ? ' ${(complexityScore * 100).round()}%' : ''}',
                ),
            ],
          ),
          if (experts.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
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
          if (etaMin != null || etaMax != null) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              '预计 ${etaMin ?? etaMax}-${etaMax ?? etaMin} 秒',
              style: TextStyle(
                fontSize: 12,
                color: DS.textSecondary,
              ),
            ),
          ],
          if (turns.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            ...turns.map(
              (turn) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing8),
                child: _TurnCard(turn: turn),
              ),
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
        _labelForAgent(turn['agent_id']?.toString() ?? '');
    final content = turn['content']?.toString() ?? '';
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                _iconForName(turn['icon']?.toString()),
                size: 14,
                color: color,
              ),
              const SizedBox(width: DS.spacing6),
              Text(
                label,
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: color,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            content,
            style: TextStyle(
              color: DS.textPrimary,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: const Color(0xFFDCE4F2)),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            color: DS.textSecondary,
            fontWeight: FontWeight.w600,
          ),
        ),
      );
}

String _complexityLabel(String tier) {
  switch (tier) {
    case 'high':
      return '高复杂度';
    case 'medium':
      return '中等复杂度';
    default:
      return '低复杂度';
  }
}

String _labelForAgent(String raw) {
  switch (raw) {
    case 'galaxy_guide':
      return '星图导航';
    case 'exam_oracle':
      return '考试策略师';
    case 'time_tutor':
      return '时间教练';
    case 'deep_analyst':
      return '深度分析师';
    case 'error_analyst':
      return '纠错专家';
    case 'study_buddy':
      return '学伴';
    case 'math_agent':
      return '数学专家';
    case 'code_agent':
      return '编程专家';
    case 'writing_agent':
      return '写作专家';
    case 'science_agent':
      return '理科专家';
    case 'search_agent':
      return '搜索专家';
    case 'orchestrator':
      return '协调器';
    case 'synthesis':
      return '综合结论';
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
