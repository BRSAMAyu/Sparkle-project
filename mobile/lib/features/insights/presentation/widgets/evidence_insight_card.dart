import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/insights/data/models/evidence_insight_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// D-07 证据洞察卡：fact → interpretation → uncertainty → evidence →
/// implication 五要素呈现。
///
/// - 事实行只渲染真实计数/标题（后端契约禁止分数与百分比）；
/// - 解读与不确定性用定性词（M-10 置信度黑话清除口径）；
/// - 证据行是可点深链（决策日志 / 目标账本）；
/// - 行动含义给出可执行下一步。
///
/// 本组件不发起请求：数据由 [card] 传入（overview 的
/// `evidenceInsightCardsProvider`），深链跳转经 [onOpenDeepLink] 回调。
class EvidenceInsightCardWidget extends StatelessWidget {
  const EvidenceInsightCardWidget({
    required this.card,
    this.onOpenDeepLink,
    super.key,
  });

  final EvidenceInsightCardData card;
  final ValueChanged<String>? onOpenDeepLink;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(_kindIcon, color: DS.brandPrimary, size: 20),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  _kindTitle(l10n),
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          _ElementBlock(
            label: l10n.eicFactLabel,
            children: _factChildren(l10n),
          ),
          const SizedBox(height: DS.spacing8),
          _ElementBlock(
            label: l10n.eicInterpretationLabel,
            children: [
              Text(
                _interpretationText(l10n),
                style: const TextStyle(fontWeight: DS.fontWeightSemibold),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          _ElementBlock(
            label: l10n.eicUncertaintyLabel,
            children: [
              for (final line in _uncertaintyLines(l10n))
                Text(
                  line,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: DS.textSecondary, height: 1.52),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          _ElementBlock(
            label: l10n.eicEvidenceLabel,
            children: [
              for (final link in card.evidence)
                Padding(
                  padding: const EdgeInsets.only(bottom: DS.spacing4),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: link.deepLink.isEmpty
                          ? null
                          : () => onOpenDeepLink?.call(link.deepLink),
                      icon: const Icon(Icons.link, size: 16),
                      label: Text(_evidenceLabel(l10n, link.labelKey)),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          _ElementBlock(
            label: l10n.eicImplicationLabel,
            children: [Text(_actionText(l10n))],
          ),
        ],
      ),
    );
  }

  // ---- 封闭词表映射（不做原始字符串透传上屏）----------------------------
  String _kindTitle(AppLocalizations l10n) {
    if (card.isFrictionPattern) return l10n.eicKindFriction;
    if (card.isHelpedInterventions) return l10n.eicKindHelpedInterventions;
    if (card.isGoalProgress) return l10n.eicKindGoalProgress;
    return l10n.eicFrictionTagUnknown;
  }

  IconData get _kindIcon {
    if (card.isFrictionPattern) return Icons.report_problem_outlined;
    if (card.isHelpedInterventions) return Icons.volunteer_activism_outlined;
    return Icons.flag_outlined;
  }

  String _frictionTagLabel(AppLocalizations l10n, String tag) {
    switch (tag) {
      case 'execution_friction':
        return l10n.eicFrictionTagExecutionFriction;
      case 'knowledge_bottleneck':
        return l10n.eicFrictionTagKnowledgeBottleneck;
      case 'material_gap':
        return l10n.eicFrictionTagMaterialGap;
      case 'deadline_pressure':
        return l10n.eicFrictionTagDeadlinePressure;
      case 'overload_crisis':
        return l10n.eicFrictionTagOverloadCrisis;
      case 'cognitive_overload':
        return l10n.eicFrictionTagCognitiveOverload;
      case 'affective_pressure':
        return l10n.eicFrictionTagAffectivePressure;
      case 'engagement_momentum':
        return l10n.eicFrictionTagEngagementMomentum;
      case 'recall_gap':
        return l10n.eicFrictionTagRecallGap;
      case 'community_gap':
        return l10n.eicFrictionTagCommunityGap;
      default:
        return l10n.eicFrictionTagUnknown;
    }
  }

  List<Widget> _factChildren(AppLocalizations l10n) {
    if (card.isFrictionPattern) {
      return [
        Text(
          l10n.eicFrictionFact(
            card.windowDays,
            card.exposures,
            _frictionTagLabel(l10n, card.frictionTag),
          ),
        ),
        Text(
          l10n.eicFrictionResponses(
            card.acceptedCount,
            card.editedCount,
            card.rejectedCount,
          ),
          style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
        ),
      ];
    }
    if (card.isHelpedInterventions) {
      return [
        Text(l10n.eicHelpedFact(card.nObserved, card.nPositive)),
        if (card.frictionTag.isNotEmpty && card.frictionTag != 'unattributed')
          Text(
            l10n.eicHelpedAgainst(_frictionTagLabel(l10n, card.frictionTag)),
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          ),
      ];
    }
    if (card.isGoalProgress) {
      return [
        Text(
          l10n.eicGoalFact(
            card.goalTitle,
            card.ledgerCompleted,
            card.ledgerTotal,
          ),
        ),
      ];
    }
    return const <Widget>[];
  }

  String _interpretationText(AppLocalizations l10n) {
    if (card.isFrictionPattern) {
      return card.frictionRole == 'most_frequent'
          ? l10n.eicFrictionRoleMostFrequent
          : l10n.eicFrictionRoleObserved;
    }
    if (card.isHelpedInterventions) {
      switch (card.evidenceStrength) {
        case 'single_observation':
          return l10n.eicHelpedTierSingle;
        case 'accumulated':
          return l10n.eicHelpedTierAccumulated;
        case 'repeated':
        default:
          return l10n.eicHelpedTierRepeated;
      }
    }
    if (card.isGoalProgress) {
      switch (card.goalBand) {
        case 'just_started':
          return l10n.eicGoalBandJustStarted;
        case 'nearly_done':
          return l10n.eicGoalBandNearlyDone;
        case 'all_complete':
          return l10n.eicGoalBandAllComplete;
        case 'no_task_evidence':
          return l10n.eicGoalBandNoTaskEvidence;
        case 'in_progress':
        default:
          return l10n.eicGoalBandInProgress;
      }
    }
    return '';
  }

  List<String> _uncertaintyLines(AppLocalizations l10n) {
    final lines = <String>[];
    for (final qualifier in card.uncertaintyQualifiers) {
      final line = switch (qualifier) {
        'counts_only_from_lifecycle_events' => l10n.eicUniqCountsOnly,
        'small_sample' => l10n.eicUniqSmallSample,
        'correlation_not_causation' => l10n.eicUniqCorrelationNotCausation,
        'task_ledger_is_honest_progress' => l10n.eicUniqLedgerHonest,
        'progress_column_may_lag_ledger' => l10n.eicUniqProgressColumnMayLag,
        'no_task_ledger' => l10n.eicUniqNoTaskLedger,
        _ => null,
      };
      if (line != null) {
        lines.add(line);
      }
    }
    if (card.notYetObserved > 0) {
      lines.add(l10n.eicUniqNotYetObserved(card.notYetObserved));
    }
    if (lines.isEmpty) {
      lines.add(l10n.eicUniqCountsOnly);
    }
    return lines;
  }

  String _evidenceLabel(AppLocalizations l10n, String labelKey) {
    switch (labelKey) {
      case 'evidence_goal_ledger':
        return l10n.eicEvidenceGoalLedger;
      case 'evidence_directive_log':
      default:
        return l10n.eicEvidenceDirectiveLog;
    }
  }

  String _actionText(AppLocalizations l10n) {
    switch (card.actionKey) {
      case 'keep_observing':
        return l10n.eicActionKeepObserving;
      case 'open_goal':
        return l10n.eicActionOpenGoal;
      case 'review_directives':
      default:
        return l10n.eicActionReviewDirectives;
    }
  }
}

class _ElementBlock extends StatelessWidget {
  const _ElementBlock({required this.label, required this.children});

  final String label;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing8,
              vertical: DS.spacing4,
            ),
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(DS.radius12),
            ),
            child: Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: DS.brandPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: children,
            ),
          ),
        ],
      );
}
