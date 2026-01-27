import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
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
    Future.microtask(() {
      ref.read(capsuleDetailProvider(widget.capsuleId).notifier).fetchDetail(widget.capsuleId);
    });
  }

  @override
  void dispose() {
    _feedbackCommentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final detailState = ref.watch(capsuleDetailProvider(widget.capsuleId));

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('胶囊详情'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          detailState.whenOrNull(
            data: (capsule) => IconButton(
              icon: Icon(
                capsule?.isFavorite ?? false ? Icons.favorite : Icons.favorite_border,
                color: capsule?.isFavorite ?? false ? DS.error : null,
              ),
              onPressed: () => _toggleFavorite(capsule),
            ),
          ) ?? const SizedBox.shrink(),
        ],
      ),
      body: detailState.when(
        data: (capsule) {
          if (capsule == null) {
            return const Center(child: Text('胶囊不存在'));
          }
          return _buildContent(capsule);
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('加载失败: $err')),
      ),
    );
  }

  Widget _buildContent(CuriosityCapsuleModel capsule) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(DS.spacing16),
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
                    capsule.depthLevelEnum.label,
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
                Icon(Icons.psychology_outlined, size: 14, color: DS.textSecondary),
                const SizedBox(width: 4),
                Text(
                  capsule.generationMethod!,
                  style: TextStyle(fontSize: 12, color: DS.textSecondary),
                ),
                const SizedBox(width: DS.spacing16),
              ],
              Icon(Icons.calendar_today_outlined, size: 14, color: DS.textSecondary),
              const SizedBox(width: 4),
              Text(
                _formatDate(capsule.createdAt),
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing24),

          // 内容
          MarkdownBody(
            data: capsule.content,
            styleSheet: MarkdownStyleSheet(
              p: TextStyle(fontSize: 16, color: isDark ? DS.textPrimary : DS.textPrimary),
              h1: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              h2: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              h3: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              strong: TextStyle(fontWeight: FontWeight.bold, color: isDark ? DS.textPrimary : DS.textPrimary),
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
                  backgroundColor: isDark ? DS.surfaceTertiary : DS.surfaceSecondary,
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
                  '质量评分: ${capsule.qualityRating}',
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
              Text('${capsule.feedbackCount} 反馈', style: TextStyle(fontSize: 12, color: DS.textSecondary)),
              const SizedBox(width: DS.spacing16),
              Icon(Icons.share_outlined, size: 16, color: DS.textSecondary),
              const SizedBox(width: 4),
              Text('${capsule.shareCount} 分享', style: TextStyle(fontSize: 12, color: DS.textSecondary)),
            ],
          ),
          const SizedBox(height: DS.spacing32),

          // 反馈按钮
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => _showFeedbackSheet(capsule),
              icon: const Icon(Icons.rate_review_outlined),
              label: const Text('提交反馈'),
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
              label: const Text('分享胶囊'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inDays == 0) {
      return '今天';
    } else if (diff.inDays == 1) {
      return '昨天';
    } else if (diff.inDays < 7) {
      return '${diff.inDays} 天前';
    } else {
      return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    }
  }

  void _toggleFavorite(CuriosityCapsuleModel? capsule) {
    if (capsule == null) return;
    ref.read(capsuleProvider.notifier).toggleFavorite(capsule.id);
  }

  void _showFeedbackSheet(CuriosityCapsuleModel capsule) {
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
    );
  }

  void _showShareSheet(CuriosityCapsuleModel capsule) {
    showModalBottomSheet<void>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.link),
              title: const Text('复制链接'),
              onTap: () {
                // TODO: 实现复制链接
                Navigator.pop(context);
              },
            ),
            ListTile(
              leading: const Icon(Icons.group_outlined),
              title: const Text('分享到群组'),
              onTap: () {
                // TODO: 实现分享到群组
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submitFeedback(CuriosityCapsuleModel capsule) async {
    if (_selectedRating == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请先评分')),
      );
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      await ref.read(capsuleDetailProvider(widget.capsuleId).notifier).submitFeedback(
        capsule.id,
        rating: _selectedRating,
        comment: _feedbackCommentController.text.isNotEmpty
            ? _feedbackCommentController.text
            : null,
      );

      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('感谢您的反馈！'),
            backgroundColor: DS.success,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('提交失败: $e'),
            backgroundColor: DS.error,
          ),
        );
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
              const Text(
                '提交反馈',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),

          // 评分
          Text(
            '这个胶囊对你有帮助吗？',
            style: TextStyle(fontSize: 14, color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(5, (index) {
              final starValue = index + 1;
              return IconButton(
                iconSize: 40,
                onPressed: () => onRatingChanged(starValue),
                icon: Icon(
                  selectedRating != null && starValue <= selectedRating!
                      ? Icons.star
                      : Icons.star_border,
                  color: DS.warning,
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
              hintText: '说说你的想法（可选）',
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
            child: ElevatedButton(
              onPressed: isSubmitting ? null : onSubmit,
              style: ElevatedButton.styleFrom(
                backgroundColor: DS.primaryBase,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
                shape: const RoundedRectangleBorder(
                  borderRadius: DS.borderRadius12,
                ),
              ),
              child: isSubmitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('提交'),
            ),
          ),
        ],
      ),
    );
  }
}
