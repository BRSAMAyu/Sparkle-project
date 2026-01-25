import 'package:flutter/material.dart';

/// Review feedback types
enum ReviewFeedbackType {
  rating,
  quality,
  accuracy,
  specificity,
}

/// Specificity level options
enum SpecificityLevel {
  tooVague('too_vague', '太笼统'),
  appropriate('appropriate', '适中'),
  tooDetailed('too_detailed', '太详细');

  const SpecificityLevel(this.value, this.label);
  final String value;
  final String label;
}

/// Review feedback data
class ReviewFeedbackData {
  const ReviewFeedbackData({
    required this.reviewId,
    this.rating,
    this.wasHelpful,
    this.wasAccurate,
    this.inaccuratePoints = const [],
    this.specificityLevel,
    this.comments,
    this.tags = const [],
  });

  final String reviewId;
  final int? rating;
  final bool? wasHelpful;
  final bool? wasAccurate;
  final List<String> inaccuratePoints;
  final SpecificityLevel? specificityLevel;
  final String? comments;
  final List<String> tags;

  Map<String, dynamic> toJson() => {
        'review_id': reviewId,
        if (rating != null) 'rating': rating,
        if (wasHelpful != null) 'was_helpful': wasHelpful,
        if (wasAccurate != null) 'was_accurate': wasAccurate,
        if (inaccuratePoints.isNotEmpty) 'inaccurate_points': inaccuratePoints,
        if (specificityLevel != null)
          'specificity_level': specificityLevel!.value,
        if (comments != null) 'comments': comments,
        if (tags.isNotEmpty) 'tags': tags,
      };
}

/// Review rating dialog - allows users to rate and provide feedback on reviews
class ReviewRatingDialog extends StatefulWidget {
  const ReviewRatingDialog({
    required this.reviewId,
    required this.onSubmit,
    this.initialRating,
    this.showDetailedFeedback = false,
    super.key,
  });

  final String reviewId;
  final Future<bool> Function(ReviewFeedbackData feedback) onSubmit;
  final int? initialRating;
  final bool showDetailedFeedback;

  /// Show the dialog
  static Future<ReviewFeedbackData?> show({
    required BuildContext context,
    required String reviewId,
    required Future<bool> Function(ReviewFeedbackData feedback) onSubmit,
    int? initialRating,
    bool showDetailedFeedback = false,
  }) {
    return showModalBottomSheet<ReviewFeedbackData>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => ReviewRatingDialog(
        reviewId: reviewId,
        onSubmit: onSubmit,
        initialRating: initialRating,
        showDetailedFeedback: showDetailedFeedback,
      ),
    );
  }

  @override
  State<ReviewRatingDialog> createState() => _ReviewRatingDialogState();
}

class _ReviewRatingDialogState extends State<ReviewRatingDialog> {
  late int? _rating;
  bool? _wasHelpful;
  bool? _wasAccurate;
  SpecificityLevel? _specificityLevel;
  final _commentsController = TextEditingController();
  final _inaccuratePointController = TextEditingController();
  final List<String> _inaccuratePoints = [];
  final List<String> _selectedTags = [];
  bool _isSubmitting = false;
  bool _showAdvancedOptions = false;

  final List<String> _availableTags = [
    '内容准确',
    '解释清晰',
    '建议实用',
    '需要改进',
    '太严格',
    '太宽松',
  ];

  @override
  void initState() {
    super.initState();
    _rating = widget.initialRating;
  }

  @override
  void dispose() {
    _commentsController.dispose();
    _inaccuratePointController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Handle bar
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: theme.colorScheme.outline.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Title
            Text(
              '为这次审查评分',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              '您的反馈将帮助我们改进审查质量',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),

            // Star rating
            _buildStarRating(theme),
            const SizedBox(height: 24),

            // Quick feedback buttons
            _buildQuickFeedback(theme),
            const SizedBox(height: 16),

            // Accuracy feedback
            if (widget.showDetailedFeedback || _showAdvancedOptions) ...[
              _buildAccuracySection(theme),
              const SizedBox(height: 16),

              // Specificity feedback
              _buildSpecificitySection(theme),
              const SizedBox(height: 16),

              // Inaccurate points
              if (_wasAccurate == false) ...[
                _buildInaccuratePointsSection(theme),
                const SizedBox(height: 16),
              ],

              // Tags
              _buildTagsSection(theme),
              const SizedBox(height: 16),
            ],

            // Show more options toggle
            if (!widget.showDetailedFeedback)
              TextButton.icon(
                onPressed: () {
                  setState(() {
                    _showAdvancedOptions = !_showAdvancedOptions;
                  });
                },
                icon: Icon(
                  _showAdvancedOptions
                      ? Icons.expand_less
                      : Icons.expand_more,
                ),
                label: Text(
                  _showAdvancedOptions ? '收起详细选项' : '更多反馈选项',
                ),
              ),

            // Comments
            _buildCommentsSection(theme),
            const SizedBox(height: 24),

            // Submit button
            _buildSubmitButton(theme),
            const SizedBox(height: 8),

            // Cancel button
            TextButton(
              onPressed: _isSubmitting ? null : () => Navigator.pop(context),
              child: const Text('取消'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStarRating(ThemeData theme) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(5, (index) {
        final starValue = index + 1;
        final isSelected = _rating != null && starValue <= _rating!;

        return GestureDetector(
          onTap: () {
            setState(() {
              _rating = starValue;
              // Auto-set helpful based on rating
              if (starValue >= 4) {
                _wasHelpful = true;
              } else if (starValue <= 2) {
                _wasHelpful = false;
              }
            });
          },
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: AnimatedScale(
              duration: const Duration(milliseconds: 150),
              scale: isSelected ? 1.1 : 1.0,
              child: Icon(
                isSelected ? Icons.star_rounded : Icons.star_outline_rounded,
                size: 44,
                color: isSelected
                    ? Colors.amber
                    : theme.colorScheme.outline.withValues(alpha: 0.5),
              ),
            ),
          ),
        );
      }),
    );
  }

  Widget _buildQuickFeedback(ThemeData theme) {
    return Row(
      children: [
        Expanded(
          child: _buildQuickButton(
            theme: theme,
            icon: Icons.thumb_up_outlined,
            selectedIcon: Icons.thumb_up,
            label: '有帮助',
            isSelected: _wasHelpful == true,
            onTap: () {
              setState(() {
                _wasHelpful = _wasHelpful == true ? null : true;
              });
            },
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildQuickButton(
            theme: theme,
            icon: Icons.thumb_down_outlined,
            selectedIcon: Icons.thumb_down,
            label: '没帮助',
            isSelected: _wasHelpful == false,
            isNegative: true,
            onTap: () {
              setState(() {
                _wasHelpful = _wasHelpful == false ? null : false;
              });
            },
          ),
        ),
      ],
    );
  }

  Widget _buildQuickButton({
    required ThemeData theme,
    required IconData icon,
    required IconData selectedIcon,
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
    bool isNegative = false,
  }) {
    final selectedColor = isNegative
        ? theme.colorScheme.error
        : theme.colorScheme.primary;

    return Material(
      color: isSelected
          ? selectedColor.withValues(alpha: 0.1)
          : theme.colorScheme.surfaceContainerHighest,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                isSelected ? selectedIcon : icon,
                size: 20,
                color: isSelected
                    ? selectedColor
                    : theme.colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 8),
              Text(
                label,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: isSelected
                      ? selectedColor
                      : theme.colorScheme.onSurfaceVariant,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAccuracySection(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '审查是否准确？',
          style: theme.textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _buildChoiceChip(
                theme: theme,
                label: '准确',
                icon: Icons.check_circle_outline,
                isSelected: _wasAccurate == true,
                onTap: () {
                  setState(() {
                    _wasAccurate = _wasAccurate == true ? null : true;
                  });
                },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _buildChoiceChip(
                theme: theme,
                label: '不准确',
                icon: Icons.error_outline,
                isSelected: _wasAccurate == false,
                isNegative: true,
                onTap: () {
                  setState(() {
                    _wasAccurate = _wasAccurate == false ? null : false;
                  });
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSpecificitySection(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '审查的详细程度',
          style: theme.textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        Row(
          children: SpecificityLevel.values.map((level) {
            return Expanded(
              child: Padding(
                padding: EdgeInsets.only(
                  left: level == SpecificityLevel.values.first ? 0 : 4,
                  right: level == SpecificityLevel.values.last ? 0 : 4,
                ),
                child: _buildChoiceChip(
                  theme: theme,
                  label: level.label,
                  isSelected: _specificityLevel == level,
                  onTap: () {
                    setState(() {
                      _specificityLevel =
                          _specificityLevel == level ? null : level;
                    });
                  },
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildChoiceChip({
    required ThemeData theme,
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
    IconData? icon,
    bool isNegative = false,
  }) {
    final selectedColor = isNegative
        ? theme.colorScheme.error
        : theme.colorScheme.primary;

    return Material(
      color: isSelected
          ? selectedColor.withValues(alpha: 0.1)
          : theme.colorScheme.surfaceContainerHighest,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(
                  icon,
                  size: 16,
                  color: isSelected
                      ? selectedColor
                      : theme.colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 4),
              ],
              Flexible(
                child: Text(
                  label,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: isSelected
                        ? selectedColor
                        : theme.colorScheme.onSurfaceVariant,
                    fontWeight:
                        isSelected ? FontWeight.w600 : FontWeight.normal,
                  ),
                  textAlign: TextAlign.center,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInaccuratePointsSection(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '哪些地方不准确？',
          style: theme.textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _inaccuratePointController,
                decoration: InputDecoration(
                  hintText: '输入不准确的具体内容',
                  isDense: true,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
                onSubmitted: _addInaccuratePoint,
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              onPressed: () => _addInaccuratePoint(
                _inaccuratePointController.text,
              ),
              icon: const Icon(Icons.add_circle_outline),
            ),
          ],
        ),
        if (_inaccuratePoints.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: _inaccuratePoints.map((point) {
              return Chip(
                label: Text(
                  point,
                  style: theme.textTheme.bodySmall,
                ),
                onDeleted: () {
                  setState(() {
                    _inaccuratePoints.remove(point);
                  });
                },
                deleteIcon: const Icon(Icons.close, size: 16),
              );
            }).toList(),
          ),
        ],
      ],
    );
  }

  void _addInaccuratePoint(String point) {
    final trimmed = point.trim();
    if (trimmed.isNotEmpty && !_inaccuratePoints.contains(trimmed)) {
      setState(() {
        _inaccuratePoints.add(trimmed);
        _inaccuratePointController.clear();
      });
    }
  }

  Widget _buildTagsSection(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '标签（可选）',
          style: theme.textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _availableTags.map((tag) {
            final isSelected = _selectedTags.contains(tag);
            return FilterChip(
              label: Text(tag),
              selected: isSelected,
              onSelected: (selected) {
                setState(() {
                  if (selected) {
                    _selectedTags.add(tag);
                  } else {
                    _selectedTags.remove(tag);
                  }
                });
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildCommentsSection(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '其他意见（可选）',
          style: theme.textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _commentsController,
          maxLines: 3,
          decoration: InputDecoration(
            hintText: '请分享您对这次审查的看法...',
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSubmitButton(ThemeData theme) {
    final hasValidFeedback = _rating != null || _wasHelpful != null;

    return FilledButton(
      onPressed: hasValidFeedback && !_isSubmitting ? _handleSubmit : null,
      style: FilledButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      child: _isSubmitting
          ? const SizedBox(
              height: 20,
              width: 20,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Colors.white,
              ),
            )
          : const Text('提交反馈'),
    );
  }

  Future<void> _handleSubmit() async {
    if (_isSubmitting) return;

    setState(() {
      _isSubmitting = true;
    });

    final feedback = ReviewFeedbackData(
      reviewId: widget.reviewId,
      rating: _rating,
      wasHelpful: _wasHelpful,
      wasAccurate: _wasAccurate,
      inaccuratePoints: _inaccuratePoints,
      specificityLevel: _specificityLevel,
      comments: _commentsController.text.trim().isEmpty
          ? null
          : _commentsController.text.trim(),
      tags: _selectedTags,
    );

    try {
      final success = await widget.onSubmit(feedback);

      if (mounted) {
        if (success) {
          Navigator.pop(context, feedback);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('感谢您的反馈！'),
              behavior: SnackBarBehavior.floating,
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('提交失败，请重试'),
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }
}
