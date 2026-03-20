import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
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
}) {
  return showSensoryModalBottomSheet<RecommendationFeedbackDraft>(
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
}

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
    final targetLabel = prompt.user?.displayName ?? prompt.group?.name ?? '推荐对象';

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
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '关于 $targetLabel 的${_stageLabel(prompt.stage)}反馈',
                        style: context.typo.labelSmall.copyWith(
                          color: DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                SemanticPill(
                  label: _stageLabel(prompt.stage),
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
                        label: _reasonLabel(tag),
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
                    '你的反馈会直接更新下一轮推荐权重',
                    style: context.typo.labelSmall.copyWith(
                      color: DS.textSecondary,
                    ),
                  ),
                ),
                SparkleButton(
                  label: '开始校准',
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
                        ? '你的伙伴匹配偏好'
                        : '你的社群推荐偏好',
                    style: context.typo.titleLarge.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                SemanticPill(
                  label: '近 ${insight.recentFeedbackCount} 次',
                  tone: PillTone.info,
                  dense: true,
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              insight.itemType == RecommendationItemType.friend
                  ? '系统正在学习你更看重相似度、互补性还是合作舒适度。'
                  : '系统正在学习你更偏好兴趣对口、活跃氛围还是新鲜发现。',
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
                            '${_metricLabel(entry.key)} ${entry.value.toStringAsFixed(1)}',
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
                '系统在回避：${insight.topNegativeSignals.take(2).map(_signalLabel).join(' · ')}',
                style: context.typo.labelSmall.copyWith(color: DS.textSecondary),
              ),
            ],
            if (topAdjustments.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                '当前更偏向：${topAdjustments.map((entry) => _metricLabel(entry.key)).join('、')}',
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
    final subjectName = widget.user?.displayName ?? widget.group?.name ?? '这条推荐';
    final issueOptions = widget.itemType == RecommendationItemType.friend
        ? const ['不够相似', '缺少互补', '不够主动', '压力太大', '不够熟悉']
        : const ['标签不准', '太冷清', '太拥挤', '氛围一般', '门槛不合适'];
    final strengthOptions = widget.itemType == RecommendationItemType.friend
        ? const ['很契合', '很互补', '很靠谱', '理由清楚']
        : const ['兴趣对口', '氛围很好', '活跃合适', '理由清楚'];

    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: GraphiteModalSurface(
        title: widget.prompt?.title ?? '帮我们校准推荐',
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                widget.prompt?.subtitle ??
                    '你对 $subjectName 的评价会直接作用到接下来的推荐算法。',
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
                label: '整体感受',
                value: _overallScore,
                onChanged: (value) => setState(() => _overallScore = value),
              ),
              _ScoreRow(
                label: '推荐理由清晰度',
                value: _explanationScore,
                onChanged: (value) => setState(() => _explanationScore = value),
              ),
              _ScoreRow(
                label: '采取行动的意愿',
                value: _actionabilityScore,
                onChanged: (value) => setState(() => _actionabilityScore = value),
              ),
              if (widget.itemType == RecommendationItemType.friend) ...[
                _ScoreRow(
                  label: '契合度',
                  value: _relevanceScore,
                  onChanged: (value) => setState(() => _relevanceScore = value),
                ),
                _ScoreRow(
                  label: '相似度是否到位',
                  value: _similarityScore,
                  onChanged: (value) => setState(() => _similarityScore = value),
                ),
                _ScoreRow(
                  label: '互补性是否成立',
                  value: _complementaryScore,
                  onChanged: (value) =>
                      setState(() => _complementaryScore = value),
                ),
                _ScoreRow(
                  label: '合作舒适度',
                  value: _comfortScore,
                  onChanged: (value) => setState(() => _comfortScore = value),
                ),
              ] else ...[
                _ScoreRow(
                  label: '兴趣匹配度',
                  value: _interestMatchScore,
                  onChanged: (value) =>
                      setState(() => _interestMatchScore = value),
                ),
                _ScoreRow(
                  label: '活跃度是否合适',
                  value: _activityScore,
                  onChanged: (value) => setState(() => _activityScore = value),
                ),
                _ScoreRow(
                  label: '社群氛围',
                  value: _atmosphereScore,
                  onChanged: (value) => setState(() => _atmosphereScore = value),
                ),
              ],
              const SizedBox(height: 10),
              _ChipSelector(
                title: '哪里不够对味',
                options: issueOptions,
                selected: _issues,
                tone: PillTone.warning,
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
                title: '哪些地方做得好',
                options: strengthOptions,
                selected: _strengths,
                tone: PillTone.success,
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
                  labelText: '自然语言补充',
                  hintText: widget.itemType == RecommendationItemType.friend
                      ? '例如：我更希望责任伙伴跟我节奏接近，但也能在拖延时推我一把。'
                      : '例如：我想找更对口的小组，最好活跃但不要太嘈杂。',
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
                        color: _accentColor(widget.itemType), size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '我们只使用你填写的分数和总结来优化推荐，不会把私密原始数据直接暴露给其他用户。',
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
                      label: '稍后再说',
                      variant: ButtonVariant.secondary,
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: SparkleButton(
                      label: '提交反馈',
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
    final title = user?.displayName ?? group?.name ?? '推荐对象';
    final subtitle = user != null
        ? '匹配策略：${user!.nickname ?? user!.username}'
        : '${group?.memberCount ?? 0} 人 · ${group?.focusTags.take(2).join(' / ') ?? '公开社群'}';

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
                    fontWeight: FontWeight.w700,
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
              label: _stageLabel(stage!),
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
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: context.typo.bodyMedium.copyWith(fontWeight: FontWeight.w600),
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
}

class _ChipSelector extends StatelessWidget {
  const _ChipSelector({
    required this.title,
    required this.options,
    required this.selected,
    required this.tone,
    required this.onToggle,
  });

  final String title;
  final List<String> options;
  final Set<String> selected;
  final PillTone tone;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: context.typo.bodyMedium.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: options
              .map(
                (option) => FilterChip(
                  label: Text(option),
                  selected: selected.contains(option),
                  onSelected: (_) => onToggle(option),
                ),
              )
              .toList(),
        ),
      ],
    );
  }
}

Color _accentColor(RecommendationItemType itemType) {
  return itemType == RecommendationItemType.friend
      ? DS.brandPrimaryConst
      : DS.warning;
}

String _stageLabel(RecommendationFeedbackStage stage) {
  switch (stage) {
    case RecommendationFeedbackStage.immediate:
      return '即时';
    case RecommendationFeedbackStage.followUp:
      return '跟进';
    case RecommendationFeedbackStage.outcome:
      return '结果';
  }
}

String _reasonLabel(String value) {
  switch (value) {
    case 'subject_overlap':
      return '主题重合';
    case 'preference_alignment':
      return '学习节奏接近';
    case 'tag_overlap':
      return '兴趣命中';
    case 'trending':
      return '近期活跃';
    default:
      return value.replaceAll('_', ' ');
  }
}

String _metricLabel(String value) {
  switch (value) {
    case 'overall_score':
      return '整体';
    case 'similarity_score':
      return '相似度';
    case 'comfort_score':
      return '舒适度';
    case 'interest_match_score':
      return '兴趣匹配';
    case 'activity_score':
      return '活跃度';
    case 'subject_overlap':
      return '主题相似';
    case 'relationship_readiness':
      return '关系熟悉度';
    case 'tag_score':
      return '标签匹配';
    case 'quality':
      return '质量';
    default:
      return value.replaceAll('_', ' ');
  }
}

String _signalLabel(String value) {
  switch (value) {
    case 'too_dissimilar':
      return '不够相似';
    case 'want_more_tag_match':
      return '兴趣不够对口';
    case 'trustworthy':
      return '合作感靠谱';
    case 'good_interest_match':
      return '兴趣对口';
    default:
      return value.replaceAll('_', ' ');
  }
}
