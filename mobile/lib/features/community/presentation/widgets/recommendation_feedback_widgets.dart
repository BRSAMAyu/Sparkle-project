import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';

class RecommendationFeedbackDraft {
  RecommendationFeedbackDraft({
    this.promptId,
    this.stage,
    this.overallScore,
    this.relevanceScore,
    this.explanationScore,
    this.actionabilityScore,
    this.similarityScore,
    this.complementaryScore,
    this.comfortScore,
    this.interestMatchScore,
    this.activityScore,
    this.atmosphereScore,
    this.selectedIssues = const [],
    this.selectedStrengths = const [],
    this.freeText,
  });

  final String? promptId;
  final RecommendationFeedbackStage? stage;
  final int? overallScore;
  final int? relevanceScore;
  final int? explanationScore;
  final int? actionabilityScore;
  final int? similarityScore;
  final int? complementaryScore;
  final int? comfortScore;
  final int? interestMatchScore;
  final int? activityScore;
  final int? atmosphereScore;
  final List<String> selectedIssues;
  final List<String> selectedStrengths;
  final String? freeText;
}

Future<RecommendationFeedbackDraft?> showRecommendationFeedbackSheet({
  required BuildContext context,
  required RecommendationItemType itemType,
  RecommendationFeedbackPrompt? prompt,
  UserBrief? user,
  GroupListItem? group,
  String? strategy,
  String? target,
}) => showSensoryModalBottomSheet<RecommendationFeedbackDraft>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _RecommendationFeedbackSheet(
      itemType: itemType,
      prompt: prompt,
      user: user,
      group: group,
      strategy: strategy,
      target: target,
    ),
  );

class RecommendationFeedbackPromptCard extends StatelessWidget {
  const RecommendationFeedbackPromptCard({
    required this.prompt,
    required this.onRespond,
    super.key,
  });

  final RecommendationFeedbackPrompt prompt;
  final VoidCallback onRespond;

  @override
  Widget build(BuildContext context) {
    final accent = _accentColor(prompt.itemType);
    final targetLabel = prompt.user?.displayName ?? prompt.group?.name ?? context.l10n.recommendationTargetFallback;

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: EdgeInsets.zero,
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              accent.withValues(alpha: 0.14),
              DS.surfaceRoleColor(SparkleSurfaceRole.card),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(24),
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Icon(
                    prompt.isFriend
                        ? Icons.handshake_outlined
                        : Icons.groups_2_outlined,
                    color: accent,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        prompt.title,
                        style: context.typo.titleLarge.copyWith(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        context.l10n.recommendationFeedbackAbout(targetLabel, _stageLabel(context, prompt.stage)),
                        style: context.typo.labelSmall.copyWith(
                          color: DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                SemanticPill(
                  label: _stageLabel(context, prompt.stage),
                  tone: prompt.isFriend ? PillTone.brand : PillTone.warning,
                  dense: true,
                ),
              ],
            ),
            if ((prompt.subtitle ?? '').isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                prompt.subtitle!,
                style: context.typo.bodyMedium.copyWith(
                  color: DS.textSecondary,
                  height: 1.35,
                ),
              ),
            ],
            if (prompt.reasonTags.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: prompt.reasonTags
                    .take(3)
                    .map(
                      (tag) => SemanticPill(
                        label: _reasonLabel(context, tag),
                        tone: PillTone.neutral,
                        dense: true,
                      ),
                    )
                    .toList(),
              ),
            ],
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: Text(
                    context.l10n.recommendationFeedbackHint,
                    style: context.typo.labelSmall.copyWith(
                      color: DS.textSecondary,
                    ),
                  ),
                ),
                SparkleButton(
                  label: context.l10n.recommendationStartCalibration,
                  size: ButtonSize.small,
                  onPressed: onRespond,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class RecommendationFeedbackInsightCard extends StatelessWidget {
  const RecommendationFeedbackInsightCard({
    required this.insight,
    super.key,
  });

  final RecommendationFeedbackInsight insight;

  @override
  Widget build(BuildContext context) {
    final accent = _accentColor(insight.itemType);
    final topAdjustments = insight.globalAdjustments.entries
        .where((entry) => entry.value > 1.0)
        .take(2)
        .toList();
    final topScores = insight.averageScores.entries.take(3).toList();

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: EdgeInsets.zero,
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              accent.withValues(alpha: 0.1),
              DS.surfaceRoleColor(SparkleSurfaceRole.card),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(24),
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    insight.itemType == RecommendationItemType.friend
                        ? context.l10n.recommendationFriendPreferenceTitle
                        : context.l10n.recommendationGroupPreferenceTitle,
                    style: context.typo.titleLarge.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
                SemanticPill(
                  label: context.l10n.recommendationRecentCount(insight.recentFeedbackCount),
                  tone: PillTone.info,
                  dense: true,
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              insight.itemType == RecommendationItemType.friend
                  ? context.l10n.recommendationFriendLearningHint
                  : context.l10n.recommendationGroupLearningHint,
              style: context.typo.bodyMedium.copyWith(
                color: DS.textSecondary,
                height: 1.35,
              ),
            ),
            if (topScores.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: topScores
                    .map(
                      (entry) => SemanticPill(
                        label:
                            '${_metricLabel(context, entry.key)} ${entry.value.toStringAsFixed(1)}',
                        tone: PillTone.brand,
                        dense: true,
                      ),
                    )
                    .toList(),
              ),
            ],
            if (insight.topNegativeSignals.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                context.l10n.recommendationSystemAvoiding(
                  insight.topNegativeSignals.take(2).map((s) => _signalLabel(context, s)).join(' \u00b7 '),
                ),
                style: context.typo.labelSmall.copyWith(color: DS.textSecondary),
              ),
            ],
            if (topAdjustments.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                context.l10n.recommendationCurrentlyBiasing(
                  topAdjustments.map((entry) => _metricLabel(context, entry.key)).join(context.l10n.recommendationListSeparator),
                ),
                style: context.typo.labelSmall.copyWith(color: accent),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _RecommendationFeedbackSheet extends StatefulWidget {
  const _RecommendationFeedbackSheet({
    required this.itemType,
    this.prompt,
    this.user,
    this.group,
    this.strategy,
    this.target,
  });

  final RecommendationItemType itemType;
  final RecommendationFeedbackPrompt? prompt;
  final UserBrief? user;
  final GroupListItem? group;
  final String? strategy;
  final String? target;

  @override
  State<_RecommendationFeedbackSheet> createState() =>
      _RecommendationFeedbackSheetState();
}

class _RecommendationFeedbackSheetState
    extends State<_RecommendationFeedbackSheet> {
  late final TextEditingController _controller;
  final Set<String> _issues = <String>{};
  final Set<String> _strengths = <String>{};

  int? _overallScore;
  int? _relevanceScore;
  int? _explanationScore;
  int? _actionabilityScore;
  int? _similarityScore;
  int? _complementaryScore;
  int? _comfortScore;
  int? _interestMatchScore;
  int? _activityScore;
  int? _atmosphereScore;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final subjectName = widget.user?.displayName ?? widget.group?.name ?? context.l10n.recommendationThisItem;
    final issueOptions = widget.itemType == RecommendationItemType.friend
        ? ['not_similar', 'not_complementary', 'not_proactive', 'too_much_pressure', 'not_familiar']
        : ['inaccurate_tags', 'too_quiet', 'too_crowded', 'mediocre_vibe', 'unsuitable_threshold'];
    final strengthOptions = widget.itemType == RecommendationItemType.friend
        ? ['great_fit', 'complementary', 'reliable', 'clear_reason']
        : ['interest_match', 'great_vibe', 'active_fit', 'clear_reason'];

    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: GraphiteModalSurface(
        title: widget.prompt?.title ?? context.l10n.recommendationCalibrateTitle,
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                widget.prompt?.subtitle ??
                    context.l10n.recommendationFeedbackSubtitle(subjectName),
                style: context.typo.bodyMedium.copyWith(
                  color: DS.textSecondary,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: 16),
              _TargetSnapshot(
                itemType: widget.itemType,
                user: widget.user ?? widget.prompt?.user,
                group: widget.group ?? widget.prompt?.group,
                stage: widget.prompt?.stage,
              ),
              const SizedBox(height: 16),
              _ScoreRow(
                label: context.l10n.recommendationScoreOverall,
                value: _overallScore,
                onChanged: (value) => setState(() => _overallScore = value),
              ),
              _ScoreRow(
                label: context.l10n.recommendationScoreExplanationClarity,
                value: _explanationScore,
                onChanged: (value) => setState(() => _explanationScore = value),
              ),
              _ScoreRow(
                label: context.l10n.recommendationScoreActionability,
                value: _actionabilityScore,
                onChanged: (value) => setState(() => _actionabilityScore = value),
              ),
              if (widget.itemType == RecommendationItemType.friend) ...[
                _ScoreRow(
                  label: context.l10n.recommendationScoreRelevance,
                  value: _relevanceScore,
                  onChanged: (value) => setState(() => _relevanceScore = value),
                ),
                _ScoreRow(
                  label: context.l10n.recommendationScoreSimilarity,
                  value: _similarityScore,
                  onChanged: (value) => setState(() => _similarityScore = value),
                ),
                _ScoreRow(
                  label: context.l10n.recommendationScoreComplementary,
                  value: _complementaryScore,
                  onChanged: (value) =>
                      setState(() => _complementaryScore = value),
                ),
                _ScoreRow(
                  label: context.l10n.recommendationScoreComfort,
                  value: _comfortScore,
                  onChanged: (value) => setState(() => _comfortScore = value),
                ),
              ] else ...[
                _ScoreRow(
                  label: context.l10n.recommendationScoreInterestMatch,
                  value: _interestMatchScore,
                  onChanged: (value) =>
                      setState(() => _interestMatchScore = value),
                ),
                _ScoreRow(
                  label: context.l10n.recommendationScoreActivity,
                  value: _activityScore,
                  onChanged: (value) => setState(() => _activityScore = value),
                ),
                _ScoreRow(
                  label: context.l10n.recommendationScoreAtmosphere,
                  value: _atmosphereScore,
                  onChanged: (value) => setState(() => _atmosphereScore = value),
                ),
              ],
              const SizedBox(height: 10),
              _ChipSelector(
                title: context.l10n.recommendationIssuesTitle,
                options: issueOptions,
                selected: _issues,
                tone: PillTone.warning,
                labelBuilder: (key) => _issueDisplayLabel(context, key),
                onToggle: (value) {
                  setState(() {
                    if (!_issues.add(value)) {
                      _issues.remove(value);
                    }
                  });
                },
              ),
              const SizedBox(height: 12),
              _ChipSelector(
                title: context.l10n.recommendationStrengthsTitle,
                options: strengthOptions,
                selected: _strengths,
                tone: PillTone.success,
                labelBuilder: (key) => _strengthDisplayLabel(context, key),
                onToggle: (value) {
                  setState(() {
                    if (!_strengths.add(value)) {
                      _strengths.remove(value);
                    }
                  });
                },
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _controller,
                minLines: 3,
                maxLines: 5,
                decoration: InputDecoration(
                  labelText: context.l10n.recommendationFreeTextLabel,
                  hintText: widget.itemType == RecommendationItemType.friend
                      ? context.l10n.recommendationFriendHint
                      : context.l10n.recommendationGroupHint,
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.privacy_tip_outlined,
                        color: _accentColor(widget.itemType), size: 18,),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        context.l10n.recommendationPrivacyNotice,
                        style: context.typo.labelSmall.copyWith(
                          color: DS.textSecondary,
                          height: 1.35,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton(
                      label: context.l10n.recommendationLater,
                      variant: ButtonVariant.secondary,
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: SparkleButton(
                      label: context.l10n.recommendationSubmitFeedback,
                      onPressed: _submit,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _submit() {
    Navigator.of(context).pop(
      RecommendationFeedbackDraft(
        promptId: widget.prompt?.promptId,
        stage: widget.prompt?.stage ?? RecommendationFeedbackStage.immediate,
        overallScore: _overallScore,
        relevanceScore: _relevanceScore,
        explanationScore: _explanationScore,
        actionabilityScore: _actionabilityScore,
        similarityScore: _similarityScore,
        complementaryScore: _complementaryScore,
        comfortScore: _comfortScore,
        interestMatchScore: _interestMatchScore,
        activityScore: _activityScore,
        atmosphereScore: _atmosphereScore,
        selectedIssues: _issues.toList(),
        selectedStrengths: _strengths.toList(),
        freeText: _controller.text.trim(),
      ),
    );
  }
}

class _TargetSnapshot extends StatelessWidget {
  const _TargetSnapshot({
    required this.itemType,
    this.user,
    this.group,
    this.stage,
  });

  final RecommendationItemType itemType;
  final UserBrief? user;
  final GroupListItem? group;
  final RecommendationFeedbackStage? stage;

  @override
  Widget build(BuildContext context) {
    final accent = _accentColor(itemType);
    final title = user?.displayName ?? group?.name ?? context.l10n.recommendationTargetFallback;
    final subtitle = user != null
        ? context.l10n.recommendationMatchingStrategy(user!.nickname ?? user!.username)
        : context.l10n.recommendationGroupSubtitle(
            '${group?.memberCount ?? 0}',
            group?.focusTags.take(2).join(' / ') ?? context.l10n.recommendationPublicGroup,
          );

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: 0.18)),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              itemType == RecommendationItemType.friend
                  ? Icons.person_outline
                  : Icons.groups_2_outlined,
              color: accent,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: context.typo.titleLarge.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: context.typo.labelSmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          if (stage != null)
            SemanticPill(
              label: _stageLabel(context, stage!),
              tone: itemType == RecommendationItemType.friend
                  ? PillTone.brand
                  : PillTone.warning,
              dense: true,
            ),
        ],
      ),
    );
  }
}

class _ScoreRow extends StatelessWidget {
  const _ScoreRow({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final int? value;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: context.typo.bodyMedium.copyWith(fontWeight: DS.fontWeightSemibold),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: List.generate(5, (index) {
              final score = index + 1;
              final selected = value == score;
              return ChoiceChip(
                label: Text('$score'),
                selected: selected,
                onSelected: (_) => onChanged(score),
              );
            }),
          ),
        ],
      ),
    );
}

class _ChipSelector extends StatelessWidget {
  const _ChipSelector({
    required this.title,
    required this.options,
    required this.selected,
    required this.tone,
    required this.onToggle,
    this.labelBuilder,
  });

  final String title;
  final List<String> options;
  final Set<String> selected;
  final PillTone tone;
  final ValueChanged<String> onToggle;
  final String Function(String)? labelBuilder;

  @override
  Widget build(BuildContext context) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: context.typo.bodyMedium.copyWith(fontWeight: DS.fontWeightSemibold),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: options
              .map(
                (option) => FilterChip(
                  label: Text(labelBuilder != null ? labelBuilder!(option) : option),
                  selected: selected.contains(option),
                  onSelected: (_) => onToggle(option),
                ),
              )
              .toList(),
        ),
      ],
    );
}

Color _accentColor(RecommendationItemType itemType) => itemType == RecommendationItemType.friend
      ? DS.brandPrimaryConst
      : DS.warning;

String _stageLabel(BuildContext context, RecommendationFeedbackStage stage) {
  switch (stage) {
    case RecommendationFeedbackStage.immediate:
      return context.l10n.recommendationStageImmediate;
    case RecommendationFeedbackStage.followUp:
      return context.l10n.recommendationStageFollowUp;
    case RecommendationFeedbackStage.outcome:
      return context.l10n.recommendationStageOutcome;
  }
}

String _reasonLabel(BuildContext context, String value) {
  switch (value) {
    case 'subject_overlap':
      return context.l10n.recommendationReasonSubjectOverlap;
    case 'preference_alignment':
      return context.l10n.recommendationReasonPreferenceAlignment;
    case 'tag_overlap':
      return context.l10n.recommendationReasonTagOverlap;
    case 'trending':
      return context.l10n.recommendationReasonTrending;
    default:
      return value.replaceAll('_', ' ');
  }
}

String _metricLabel(BuildContext context, String value) {
  switch (value) {
    case 'overall_score':
      return context.l10n.recommendationMetricOverall;
    case 'similarity_score':
      return context.l10n.recommendationMetricSimilarity;
    case 'comfort_score':
      return context.l10n.recommendationMetricComfort;
    case 'interest_match_score':
      return context.l10n.recommendationMetricInterestMatch;
    case 'activity_score':
      return context.l10n.recommendationMetricActivity;
    case 'subject_overlap':
      return context.l10n.recommendationMetricSubjectSimilarity;
    case 'relationship_readiness':
      return context.l10n.recommendationMetricRelationshipReadiness;
    case 'tag_score':
      return context.l10n.recommendationMetricTagMatch;
    case 'quality':
      return context.l10n.recommendationMetricQuality;
    default:
      return value.replaceAll('_', ' ');
  }
}

String _signalLabel(BuildContext context, String value) {
  switch (value) {
    case 'too_dissimilar':
      return context.l10n.recommendationSignalTooDissimilar;
    case 'want_more_tag_match':
      return context.l10n.recommendationSignalWantMoreTagMatch;
    case 'trustworthy':
      return context.l10n.recommendationSignalTrustworthy;
    case 'good_interest_match':
      return context.l10n.recommendationSignalGoodInterestMatch;
    default:
      return value.replaceAll('_', ' ');
  }
}

String _issueDisplayLabel(BuildContext context, String key) {
  switch (key) {
    case 'not_similar':
      return context.l10n.recommendationIssueNotSimilar;
    case 'not_complementary':
      return context.l10n.recommendationIssueNotComplementary;
    case 'not_proactive':
      return context.l10n.recommendationIssueNotProactive;
    case 'too_much_pressure':
      return context.l10n.recommendationIssueTooMuchPressure;
    case 'not_familiar':
      return context.l10n.recommendationIssueNotFamiliar;
    case 'inaccurate_tags':
      return context.l10n.recommendationIssueInaccurateTags;
    case 'too_quiet':
      return context.l10n.recommendationIssueTooQuiet;
    case 'too_crowded':
      return context.l10n.recommendationIssueTooCrowded;
    case 'mediocre_vibe':
      return context.l10n.recommendationIssueMediocreVibe;
    case 'unsuitable_threshold':
      return context.l10n.recommendationIssueUnsuitableThreshold;
    default:
      return key;
  }
}

String _strengthDisplayLabel(BuildContext context, String key) {
  switch (key) {
    case 'great_fit':
      return context.l10n.recommendationStrengthGreatFit;
    case 'complementary':
      return context.l10n.recommendationStrengthComplementary;
    case 'reliable':
      return context.l10n.recommendationStrengthReliable;
    case 'clear_reason':
      return context.l10n.recommendationStrengthClearReason;
    case 'interest_match':
      return context.l10n.recommendationStrengthInterestMatch;
    case 'great_vibe':
      return context.l10n.recommendationStrengthGreatVibe;
    case 'active_fit':
      return context.l10n.recommendationStrengthActiveFit;
    default:
      return key;
  }
}
