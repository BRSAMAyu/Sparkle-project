import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';

/// 胶囊详情页
class CapsuleDetailScreen extends ConsumerStatefulWidget {
  const CapsuleDetailScreen({
    required this.capsuleId,
    super.key,
  });

  final String capsuleId;

  @override
  ConsumerState<CapsuleDetailScreen> createState() =>
      _CapsuleDetailScreenState();
}

class _CapsuleDetailScreenState extends ConsumerState<CapsuleDetailScreen> {
  @override
  void initState() {
    super.initState();
    unawaited(
      Future.microtask(
        () => ref
            .read(capsuleDetailProvider(widget.capsuleId).notifier)
            .fetchDetail(widget.capsuleId),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final detailState = ref.watch(capsuleDetailProvider(widget.capsuleId));
    final l10n = context.l10n;

    final capsule = detailState.valueOrNull;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        title: Text(l10n.capsuleDetailTitle),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          if (capsule != null)
            SparkleIconButton(
              icon: Icon(
                capsule.isFavorite ? Icons.favorite : Icons.favorite_border,
              ),
              onPressed: () => _toggleFavorite(capsule),
              variant: capsule.isFavorite
                  ? ButtonVariant.destructive
                  : ButtonVariant.ghost,
            ),
        ],
      ),
      bottomNavigationBar: capsule != null ? _buildBottomBar(capsule) : null,
      child: detailState.when(
        data: (c) {
          if (c == null) {
            return EmptyState(
              title: context.l10n.cogCapsuleUnavailable,
              description: context.l10n.cogCapsuleUnavailableDesc,
              icon: Icons.auto_awesome_outlined,
            );
          }
          return _buildContent(c);
        },
        loading: () => LoadingIndicator.circular(
          showText: true,
          loadingText: I18nService.instance.isChinese
              ? '正在整理这枚胶囊...'
              : 'Preparing this capsule...',
        ),
        error: (err, _) => CustomErrorWidget.page(
          context: context,
          message: l10n.capsuleLoadFailed('$err'),
          title: context.l10n.cogCapsuleOpenFailed,
          onRetry: () => ref
              .read(capsuleDetailProvider(widget.capsuleId).notifier)
              .fetchDetail(widget.capsuleId),
        ),
      ),
    );
  }

  Widget _buildContent(CuriosityCapsuleModel capsule) => ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing16,
            DS.spacing16,
            DS.spacing32,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 深度级别标签
              if (capsule.depthLevel != null) ...[
                SparkleStaggerItem(
                  index: 0,
                  child: _DepthBadge(capsule: capsule),
                ),
                const SizedBox(height: DS.spacing16),
              ],

              // 标题
              SparkleStaggerItem(
                index: 1,
                child: Text(
                  capsule.title,
                  style: context.sparkleTypography.headingMedium,
                ),
              ),
              const SizedBox(height: DS.spacing8),

              // 元信息行
              SparkleStaggerItem(
                index: 2,
                child: _MetaRow(capsule: capsule),
              ),
              const SizedBox(height: DS.spacing24),

              // 个性化说明卡片
              if (capsule.personalizationContext != null) ...[
                SparkleStaggerItem(
                  index: 3,
                  child: _PersonalizationCard(
                    capsule: capsule,
                    localizePattern: _localizePatternName,
                  ),
                ),
                const SizedBox(height: DS.spacing24),
              ],

              // 主内容
              SparkleStaggerItem(
                index: 4,
                child: SparkleMarkdown(
                  content: capsule.content,
                  textColor: DS.textPrimary,
                  codeBackgroundColor: DS.surfaceTertiary,
                  linkColor: DS.brandPrimary,
                  lineHeight: 1.65,
                  selectable: true,
                ),
              ),
              const SizedBox(height: DS.spacing24),

              // 相关主题 chip
              if (capsule.relatedSubject != null) ...[
                SparkleStaggerItem(
                  index: 5,
                  child: Wrap(
                    spacing: DS.spacing8,
                    children: [
                      Chip(
                        avatar: const Icon(Icons.tag, size: 14),
                        label: Text(
                          capsule.relatedSubject!,
                          style: context.sparkleTypography.labelSmall,
                        ),
                        backgroundColor: DS.surfaceSecondary,
                        side: BorderSide(color: DS.border, width: 0.5),
                        padding:
                            const EdgeInsets.symmetric(horizontal: DS.spacing4),
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing24),
              ],

              // 质量评分 + 统计信息合并一行
              SparkleStaggerItem(
                index: 6,
                child: _StatsRow(capsule: capsule),
              ),
            ],
          ),
        ),
      );

  Widget _buildBottomBar(CuriosityCapsuleModel capsule) {
    final l10n = context.l10n;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing8,
          DS.spacing16,
          DS.spacing12,
        ),
        child: Row(
          children: [
            Expanded(
              child: SparkleButton(
                label: l10n.capsuleSubmitFeedback,
                variant: ButtonVariant.secondary,
                icon: const Icon(Icons.rate_review_outlined, size: 18),
                onPressed: () => _showFeedbackSheet(capsule),
                expand: true,
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: SparkleButton(
                label: l10n.capsuleShare,
                variant: ButtonVariant.ghost,
                icon: const Icon(Icons.share_outlined, size: 18),
                onPressed: () => _showShareSheet(capsule),
                expand: true,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _toggleFavorite(CuriosityCapsuleModel capsule) {
    unawaited(
      SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
    );
    unawaited(ref.read(capsuleProvider.notifier).toggleFavorite(capsule.id));
  }

  void _showFeedbackSheet(CuriosityCapsuleModel capsule) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        useRootNavigator: true,
        builder: (ctx) => _FeedbackBottomSheet(
          capsule: capsule,
          localizePattern: _localizePatternName,
          onSubmitted: (rating, category, comment) async {
            try {
              await ref
                  .read(capsuleDetailProvider(widget.capsuleId).notifier)
                  .submitFeedback(
                    capsule.id,
                    rating: rating,
                    category: category,
                    comment: comment,
                  );
              if (mounted) {
                AppFeedback.success(
                    context, context.l10n.capsuleFeedbackThanks);
              }
            } catch (_) {
              if (mounted) {
                AppFeedback.error(
                    context, context.l10n.capsuleSubmitFailed(''));
              }
            }
          },
        ),
      ),
    );
  }

  void _showShareSheet(CuriosityCapsuleModel capsule) {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
    final tags = <String>[
      if ((capsule.relatedSubject ?? '').trim().isNotEmpty)
        capsule.relatedSubject!.trim(),
      capsule.depthLabel,
    ];

    unawaited(
      showUniversalShareSheet(
        context,
        payload: UniversalSharePayload(
          contentType: ShareableContentType.capsule,
          resourceId: capsule.id,
          title: capsule.title,
          subtitle: capsule.content.split('\n').first,
          description: capsule.content,
          metadata: {
            'type':
                I18nService.instance.isChinese ? '好奇心胶囊' : 'Curiosity capsule',
            'depth': switch (capsule.depthLevelEnum) {
              CapsuleDepthLevel.shallow => 1,
              CapsuleDepthLevel.medium => 2,
              CapsuleDepthLevel.deep => 3,
            },
            'depth_label': capsule.depthLabel,
            'word_count': capsule.content.trim().length,
            'created_at': capsule.createdAt.toIso8601String(),
            'related_subject': capsule.relatedSubject,
            'tags': tags,
          },
        ),
        onGenerateCard: (payload) =>
            SharePosterService().generatePoster(context, payload),
      ),
    );
  }

  String _localizePatternName(BuildContext context, String name) {
    final l10n = context.l10n;
    switch (name) {
      case 'Planning Optimism':
        return l10n.patternPlanningOptimism;
      case 'Focus Decay':
        return l10n.patternFocusDecay;
      case 'Procrastination':
        return l10n.patternProcrastination;
      default:
        return name;
    }
  }
}

// ─────────────────────────────────────────────
// Sub-widgets
// ─────────────────────────────────────────────

class _DepthBadge extends StatelessWidget {
  const _DepthBadge({required this.capsule});
  final CuriosityCapsuleModel capsule;

  @override
  Widget build(BuildContext context) {
    final Color bg;
    final Color fg;
    switch (capsule.depthLevelEnum) {
      case CapsuleDepthLevel.deep:
        bg = DS.info.withValues(alpha: 0.12);
        fg = DS.info;
      case CapsuleDepthLevel.medium:
        bg = DS.warning.withValues(alpha: 0.12);
        fg = DS.warning;
      case CapsuleDepthLevel.shallow:
        bg = DS.success.withValues(alpha: 0.12);
        fg = DS.success;
    }
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: DS.borderRadius8,
        border: Border.all(color: fg.withValues(alpha: 0.25), width: 0.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(capsule.depthEmoji, style: const TextStyle(fontSize: 13)),
          const SizedBox(width: DS.spacing6),
          Text(
            capsule.depthLabel,
            style: TextStyle(
              fontSize: 12,
              fontWeight: DS.fontWeightSemibold,
              color: fg,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetaRow extends StatelessWidget {
  const _MetaRow({required this.capsule});
  final CuriosityCapsuleModel capsule;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Icon(Icons.auto_awesome_outlined, size: 13, color: DS.textSecondary),
          const SizedBox(width: DS.spacing4),
          Text(
            'AI',
            style: TextStyle(fontSize: 12, color: DS.textSecondary),
          ),
          const SizedBox(width: DS.spacing16),
          Icon(
            Icons.calendar_today_outlined,
            size: 13,
            color: DS.textSecondary,
          ),
          const SizedBox(width: DS.spacing4),
          Text(
            Formatters.formatRelativeTime(capsule.createdAt),
            style: TextStyle(fontSize: 12, color: DS.textSecondary),
          ),
        ],
      );
}

class _PersonalizationCard extends StatelessWidget {
  const _PersonalizationCard({
    required this.capsule,
    required this.localizePattern,
  });
  final CuriosityCapsuleModel capsule;
  final String Function(BuildContext, String) localizePattern;

  @override
  Widget build(BuildContext context) {
    final rawPatterns = capsule.personalizationContext?['based_on_patterns'];
    if (rawPatterns is! List) return const SizedBox.shrink();

    final patterns = rawPatterns
        .map((e) => e.toString())
        .where((e) => e.isNotEmpty)
        .map((e) => localizePattern(context, e))
        .toList();

    if (patterns.isEmpty) return const SizedBox.shrink();

    final l10n = context.l10n;
    final separator =
        Localizations.localeOf(context).languageCode == 'zh' ? '、' : ', ';

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            DS.prismPurple.withValues(alpha: 0.06),
            DS.info.withValues(alpha: 0.04),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: DS.prismPurple.withValues(alpha: 0.15),
          width: 0.5,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(DS.spacing6),
            decoration: BoxDecoration(
              color: DS.prismPurple.withValues(alpha: 0.12),
              borderRadius: DS.borderRadius8,
            ),
            child: Icon(
              Icons.psychology_outlined,
              size: 16,
              color: DS.prismPurple,
            ),
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.capsulePersonalizationTitle,
                  style: const TextStyle(
                    fontWeight: DS.fontWeightSemibold,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  l10n.capsulePersonalizationExplanation(
                    patterns.join(separator),
                  ),
                  style: TextStyle(
                    color: DS.textSecondary,
                    fontSize: 13,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatsRow extends StatelessWidget {
  const _StatsRow({required this.capsule});
  final CuriosityCapsuleModel capsule;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Row(
      children: [
        if (capsule.qualityScore != null) ...[
          ...List.generate(5, (i) {
            final filled = i < (capsule.qualityScore! * 5).round();
            return Icon(
              filled ? Icons.star_rounded : Icons.star_outline_rounded,
              size: 14,
              color: filled ? DS.warning : DS.border,
            );
          }),
          const SizedBox(width: DS.spacing8),
          Text(
            capsule.qualityRating,
            style: TextStyle(fontSize: 12, color: DS.textSecondary),
          ),
          const SizedBox(width: DS.spacing16),
        ],
        Icon(Icons.rate_review_outlined, size: 13, color: DS.textSecondary),
        const SizedBox(width: DS.spacing4),
        Text(
          l10n.capsuleFeedbackCount(capsule.feedbackCount),
          style: TextStyle(fontSize: 12, color: DS.textSecondary),
        ),
        const SizedBox(width: DS.spacing12),
        Icon(Icons.share_outlined, size: 13, color: DS.textSecondary),
        const SizedBox(width: DS.spacing4),
        Text(
          l10n.capsuleShareCount(capsule.shareCount),
          style: TextStyle(fontSize: 12, color: DS.textSecondary),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────
// Feedback bottom sheet — self-contained state
// ─────────────────────────────────────────────

class _FeedbackBottomSheet extends StatefulWidget {
  const _FeedbackBottomSheet({
    required this.capsule,
    required this.localizePattern,
    required this.onSubmitted,
  });

  final CuriosityCapsuleModel capsule;
  final String Function(BuildContext, String) localizePattern;
  final Future<void> Function(int? rating, String? category, String? comment)
      onSubmitted;

  @override
  State<_FeedbackBottomSheet> createState() => _FeedbackBottomSheetState();
}

class _FeedbackBottomSheetState extends State<_FeedbackBottomSheet> {
  final _commentController = TextEditingController();
  int? _rating;
  String? _category;
  bool _submitting = false;

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  static const _categories = [
    ('just_right', Icons.check_circle_outline),
    ('too_long', Icons.unfold_more),
    ('too_short', Icons.unfold_less),
    ('too_complex', Icons.psychology_outlined),
    ('too_simple', Icons.sentiment_satisfied_outlined),
    ('irrelevant', Icons.link_off_outlined),
    ('other', Icons.more_horiz),
  ];

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final labels = {
      'just_right': l10n.capsuleFeedbackJustRight,
      'too_long': l10n.capsuleFeedbackTooLong,
      'too_short': l10n.capsuleFeedbackTooShort,
      'too_complex': l10n.capsuleFeedbackTooComplex,
      'too_simple': l10n.capsuleFeedbackTooSimple,
      'irrelevant': l10n.capsuleFeedbackIrrelevant,
      'other': l10n.capsuleFeedbackOther,
    };

    return Padding(
      padding: EdgeInsets.only(
        left: DS.spacing16,
        right: DS.spacing16,
        top: DS.spacing16,
        bottom: MediaQuery.of(context).viewInsets.bottom + DS.spacing24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 拖拽指示条
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: DS.border,
                borderRadius: DS.borderRadiusFull,
              ),
            ),
          ),
          const SizedBox(height: DS.spacing16),

          // 标题
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                l10n.capsuleSubmitFeedback,
                style: context.sparkleTypography.titleLarge,
              ),
              SparkleIconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.pop(context),
                variant: ButtonVariant.ghost,
              ),
            ],
          ),
          const SizedBox(height: DS.spacing20),

          // 星级评分
          Text(
            l10n.capsuleFeedbackQuestion,
            style: TextStyle(
              fontSize: 13,
              fontWeight: DS.fontWeightMedium,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(5, (i) {
              final v = i + 1;
              final filled = _rating != null && v <= _rating!;
              return GestureDetector(
                onTap: () => setState(() => _rating = v),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: DS.spacing6),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 150),
                    child: Icon(
                      filled ? Icons.star_rounded : Icons.star_outline_rounded,
                      key: ValueKey(filled),
                      color: filled ? DS.warning : DS.border,
                      size: DS.spacing40,
                    ),
                  ),
                ),
              );
            }),
          ),
          const SizedBox(height: DS.spacing20),

          // 分类选择
          Text(
            l10n.capsuleFeedbackCategoryLabel,
            style: TextStyle(
              fontSize: 13,
              fontWeight: DS.fontWeightMedium,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing10),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: _categories.map((pair) {
              final (value, icon) = pair;
              final selected = _category == value;
              return FilterChip(
                avatar: Icon(
                  icon,
                  size: 14,
                  color: selected ? DS.brandPrimary : DS.textSecondary,
                ),
                label: Text(labels[value] ?? value),
                selected: selected,
                onSelected: (_) =>
                    setState(() => _category = selected ? null : value),
                selectedColor: DS.brandPrimary.withValues(alpha: 0.12),
                checkmarkColor: DS.brandPrimary,
                labelStyle: TextStyle(
                  fontSize: 12,
                  color: selected ? DS.brandPrimary : DS.textPrimary,
                  fontWeight:
                      selected ? DS.fontWeightSemibold : FontWeight.normal,
                ),
                side: BorderSide(
                  color: selected
                      ? DS.brandPrimary.withValues(alpha: 0.4)
                      : DS.border,
                  width: 0.5,
                ),
                backgroundColor: DS.surfaceSecondary,
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing4,
                  vertical: DS.spacing4,
                ),
                showCheckmark: false,
              );
            }).toList(),
          ),
          const SizedBox(height: DS.spacing16),

          // 评论输入
          TextField(
            controller: _commentController,
            maxLines: 3,
            maxLength: 200,
            style: context.sparkleTypography.bodyMedium,
            decoration: InputDecoration(
              hintText: l10n.capsuleFeedbackHint,
              hintStyle: TextStyle(color: DS.textSecondary, fontSize: 14),
              filled: true,
              fillColor: DS.surfaceSecondary,
              border: OutlineInputBorder(
                borderRadius: DS.borderRadius12,
                borderSide: BorderSide(color: DS.border, width: 0.5),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: DS.borderRadius12,
                borderSide: BorderSide(color: DS.border, width: 0.5),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: DS.borderRadius12,
                borderSide: BorderSide(color: DS.brandPrimary),
              ),
              contentPadding: const EdgeInsets.all(DS.spacing12),
              counterStyle: TextStyle(color: DS.textSecondary, fontSize: 11),
            ),
          ),
          const SizedBox(height: DS.spacing16),

          // 提交
          SizedBox(
            width: double.infinity,
            child: SparkleButton(
              label: l10n.capsuleSubmit,
              onPressed: _rating == null ? null : _submit,
              loading: _submitting,
              disabled: _submitting || _rating == null,
              expand: true,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submit() async {
    setState(() => _submitting = true);
    try {
      await widget.onSubmitted(
        _rating,
        _category,
        _commentController.text.isNotEmpty ? _commentController.text : null,
      );
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.capsuleSubmitFailed('$e'));
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }
}
