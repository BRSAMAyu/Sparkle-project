import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';

/// 胶囊详情页
///
/// 显示胶囊完整内容，支持收藏和反馈
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
  final _feedbackCommentController = TextEditingController();
  int? _selectedRating;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    // Load capsule detail
    unawaited(
      Future.microtask(
        () => ref
            .read(capsuleDetailProvider(widget.capsuleId).notifier)
            .fetchDetail(widget.capsuleId),
      ),
    );
  }

  @override
  void dispose() {
    _feedbackCommentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final detailState = ref.watch(capsuleDetailProvider(widget.capsuleId));
    final l10n = context.l10n;

    return Scaffold(
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        title: Text(l10n.capsuleDetailTitle),
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        elevation: 0,
        actions: [
          detailState.whenOrNull(
                data: (capsule) => SparkleIconButton(
                  icon: Icon(
                    capsule?.isFavorite ?? false
                        ? Icons.favorite
                        : Icons.favorite_border,
                  ),
                  onPressed: () => _toggleFavorite(capsule),
                  variant: capsule?.isFavorite ?? false
                      ? ButtonVariant.destructive
                      : ButtonVariant.ghost,
                ),
              ) ??
              const SizedBox.shrink(),
        ],
      ),
      body: ContentConstraint(
        child: detailState.when(
          data: (capsule) {
            if (capsule == null) {
              return Center(child: Text(l10n.capsuleMissing));
            }
            return _buildContent(capsule);
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, stack) =>
              Center(child: Text(l10n.capsuleLoadFailed('$err'))),
        ),
      ),
    );
  }

  Widget _buildContent(CuriosityCapsuleModel capsule) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final l10n = context.l10n;

    return SingleChildScrollView(
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 深度级别标签
          if (capsule.depthLevel != null)
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing6,
              ),
              decoration: BoxDecoration(
                color: capsule.depthLevelEnum == CapsuleDepthLevel.deep
                    ? DS.info.withValues(alpha: 0.15)
                    : capsule.depthLevelEnum == CapsuleDepthLevel.medium
                        ? DS.warning.withValues(alpha: 0.15)
                        : DS.success.withValues(alpha: 0.15),
                borderRadius: DS.borderRadius8,
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(capsule.depthEmoji),
                  const SizedBox(width: DS.sm),
                  Text(
                    capsule.depthLabel,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: isDark ? DS.textPrimary : DS.textPrimary,
                    ),
                  ),
                ],
              ),
            ),
          const SizedBox(height: DS.spacing16),

          // 标题
          Text(
            capsule.title,
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: DS.spacing8),

          // 元信息行
          Row(
            children: [
              if (capsule.generationMethod != null) ...[
                Icon(
                  Icons.psychology_outlined,
                  size: 14,
                  color: DS.textSecondary,
                ),
                const SizedBox(width: 4),
                Text(
                  capsule.generationMethod!,
                  style: TextStyle(
                    fontSize: 12,
                    color: DS.textSecondary,
                  ),
                ),
                const SizedBox(width: DS.spacing16),
              ],
              Icon(
                Icons.calendar_today_outlined,
                size: 14,
                color: DS.textSecondary,
              ),
              const SizedBox(width: 4),
              Text(
                Formatters.formatRelativeTime(capsule.createdAt),
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing24),

          // 内容
          MarkdownBody(
            data: capsule.content,
            styleSheet: MarkdownStyleSheet(
              p: TextStyle(
                fontSize: 16,
                color: isDark ? DS.textPrimary : DS.textPrimary,
              ),
              h1: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              h2: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              h3: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              strong: TextStyle(
                fontWeight: FontWeight.bold,
                color: isDark ? DS.textPrimary : DS.textPrimary,
              ),
              blockquote: TextStyle(
                color: isDark ? DS.textSecondary : DS.textSecondary,
                fontStyle: FontStyle.italic,
              ),
              code: TextStyle(
                backgroundColor: isDark ? DS.neutral700 : DS.neutral200,
                fontFamily: 'monospace',
              ),
              codeblockDecoration: BoxDecoration(
                color: isDark ? DS.neutral700 : DS.neutral200,
                borderRadius: DS.borderRadius8,
              ),
            ),
          ),
          const SizedBox(height: DS.spacing32),

          // 相关主题
          if (capsule.relatedSubject != null) ...[
            Wrap(
              children: [
                Chip(
                  label: Text(capsule.relatedSubject!),
                  backgroundColor:
                      isDark ? DS.surfaceTertiary : DS.surfaceSecondary,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing24),
          ],

          // 质量评分
          if (capsule.qualityScore != null) ...[
            Row(
              children: [
                Text(
                  l10n.capsuleQualityLabel(capsule.qualityRating),
                  style: TextStyle(
                    fontSize: 14,
                    color: DS.textSecondary,
                  ),
                ),
                const SizedBox(width: DS.sm),
                ...List.generate(
                  5,
                  (index) => Icon(
                    index < (capsule.qualityScore! * 5).round()
                        ? Icons.star
                        : Icons.star_border,
                    size: 16,
                    color: DS.warning,
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing16),
          ],

          // 统计信息
          Row(
            children: [
              Icon(Icons.favorite_border, size: 16, color: DS.textSecondary),
              const SizedBox(width: 4),
              Text(
                l10n.capsuleFeedbackCount(capsule.feedbackCount),
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
              const SizedBox(width: DS.spacing16),
              Icon(Icons.share_outlined, size: 16, color: DS.textSecondary),
              const SizedBox(width: 4),
              Text(
                l10n.capsuleShareCount(capsule.shareCount),
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing32),

          // 反馈按钮
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => _showFeedbackSheet(capsule),
              icon: const Icon(Icons.rate_review_outlined),
              label: Text(l10n.capsuleSubmitFeedback),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
                side: BorderSide(color: DS.primaryBase),
              ),
            ),
          ),
          const SizedBox(height: DS.spacing16),

          // 分享按钮
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => _showShareSheet(capsule),
              icon: const Icon(Icons.share_outlined),
              label: Text(l10n.capsuleShare),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _toggleFavorite(CuriosityCapsuleModel? capsule) {
    if (capsule == null) return;
    unawaited(ref.read(capsuleProvider.notifier).toggleFavorite(capsule.id));
  }

  void _showFeedbackSheet(CuriosityCapsuleModel capsule) {
    unawaited(
      showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (context) => _FeedbackBottomSheet(
          capsule: capsule,
          ratingController: _feedbackCommentController,
          selectedRating: _selectedRating,
          isSubmitting: _isSubmitting,
          onRatingChanged: (rating) => setState(() => _selectedRating = rating),
          onSubmit: () => _submitFeedback(capsule),
        ),
      ),
    );
  }

  void _showShareSheet(CuriosityCapsuleModel capsule) {
    unawaited(
      showModalBottomSheet<void>(
        context: context,
        builder: (context) => SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.link),
                title: Text(context.l10n.capsuleCopyLink),
                onTap: () {
                  // TODO: 实现复制链接
                  Navigator.pop(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.group_outlined),
                title: Text(context.l10n.capsuleShareToGroup),
                onTap: () {
                  // TODO: 实现分享到群组
                  Navigator.pop(context);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _submitFeedback(CuriosityCapsuleModel capsule) async {
    if (_selectedRating == null) {
      AppFeedback.info(context, context.l10n.capsuleRateFirst);
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      await ref
          .read(capsuleDetailProvider(widget.capsuleId).notifier)
          .submitFeedback(
            capsule.id,
            rating: _selectedRating,
            comment: _feedbackCommentController.text.isNotEmpty
                ? _feedbackCommentController.text
                : null,
          );

      if (mounted) {
        Navigator.pop(context);
        AppFeedback.success(context, context.l10n.capsuleFeedbackThanks);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.capsuleSubmitFailed('$e'));
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }
}

class _FeedbackBottomSheet extends StatelessWidget {
  const _FeedbackBottomSheet({
    required this.capsule,
    required this.ratingController,
    required this.selectedRating,
    required this.isSubmitting,
    required this.onRatingChanged,
    required this.onSubmit,
  });

  final CuriosityCapsuleModel capsule;
  final TextEditingController ratingController;
  final int? selectedRating;
  final bool isSubmitting;
  final void Function(int) onRatingChanged;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final l10n = context.l10n;

    return Padding(
      padding: EdgeInsets.only(
        left: DS.spacing16,
        right: DS.spacing16,
        top: DS.spacing16,
        bottom: MediaQuery.of(context).viewInsets.bottom + DS.spacing16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                l10n.capsuleSubmitFeedback,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SparkleIconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.pop(context),
                variant: ButtonVariant.ghost,
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),

          // 评分
          Text(
            l10n.capsuleFeedbackQuestion,
            style: TextStyle(fontSize: 14, color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(5, (index) {
              final starValue = index + 1;
              return InkWell(
                borderRadius: DS.borderRadiusFull,
                onTap: () => onRatingChanged(starValue),
                child: Padding(
                  padding: const EdgeInsets.all(DS.spacing8),
                  child: Icon(
                    selectedRating != null && starValue <= selectedRating!
                        ? Icons.star
                        : Icons.star_border,
                    color: DS.warning,
                    size: DS.spacing40,
                  ),
                ),
              );
            }),
          ),
          const SizedBox(height: DS.spacing16),

          // 评论
          TextField(
            controller: ratingController,
            maxLines: 3,
            decoration: InputDecoration(
              hintText: l10n.capsuleFeedbackHint,
              border: const OutlineInputBorder(
                borderRadius: DS.borderRadius8,
              ),
              filled: true,
              fillColor: isDark ? DS.surfaceTertiary : DS.surfaceSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing16),

          // 提交按钮
          SizedBox(
            width: double.infinity,
            child: SparkleButton(
              label: l10n.capsuleSubmit,
              onPressed: onSubmit,
              loading: isSubmitting,
              disabled: isSubmitting,
              expand: true,
            ),
          ),
        ],
      ),
    );
  }
}
