import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Review feedback types
enum ReviewFeedbackType {
  rating,
  quality,
  accuracy,
  specificity,
}

/// Specificity level options
enum SpecificityLevel {
  tooVague('too_vague'),
  appropriate('appropriate'),
  tooDetailed('too_detailed');

  const SpecificityLevel(this.value);
  final String value;

  String label(BuildContext context) {
    final l10n = context.l10n;
    switch (this) {
      case SpecificityLevel.tooVague:
        return l10n.reviewSpecificityTooVague;
      case SpecificityLevel.appropriate:
        return l10n.reviewSpecificityAppropriate;
      case SpecificityLevel.tooDetailed:
        return l10n.reviewSpecificityTooDetailed;
    }
  }
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
  }) =>
      showModalBottomSheet<ReviewFeedbackData>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (ctx) => ReviewRatingDialog(
          reviewId: reviewId,
          onSubmit: onSubmit,
          initialRating: initialRating,
          showDetailedFeedback: showDetailedFeedback,
        ),
      );

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

  List<String> _availableTags(BuildContext context) => [
        context.l10n.reviewTagAccurate,
        context.l10n.reviewTagClear,
        context.l10n.reviewTagPractical,
        context.l10n.reviewTagNeedsImprovement,
        context.l10n.reviewTagTooStrict,
        context.l10n.reviewTagTooLenient,
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
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(DS.spacing20)),
      ),
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(DS.spacing20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Handle bar
            Center(
              child: Container(
                width: DS.spacing40,
                height: DS.spacing4,
                decoration: BoxDecoration(
                  color: theme.colorScheme.outline.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(DS.spacing4 / 2),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing16),

            // Title
            Text(
              context.l10n.reviewRatingTitle,
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.reviewRatingSubtitle,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.spacing24),

            // Star rating
            _buildStarRating(theme),
            const SizedBox(height: DS.spacing24),

            // Quick feedback buttons
            _buildQuickFeedback(theme),
            const SizedBox(height: DS.spacing16),

            // Accuracy feedback
            if (widget.showDetailedFeedback || _showAdvancedOptions) ...[
              _buildAccuracySection(theme),
              const SizedBox(height: DS.spacing16),

              // Specificity feedback
              _buildSpecificitySection(theme),
              const SizedBox(height: DS.spacing16),

              // Inaccurate points
              if (_wasAccurate == false) ...[
                _buildInaccuratePointsSection(theme),
                const SizedBox(height: DS.spacing16),
              ],

              // Tags
              _buildTagsSection(theme),
              const SizedBox(height: DS.spacing16),
            ],

            // Show more options toggle
            if (!widget.showDetailedFeedback)
              Center(
                child: SparkleButton.ghost(
                  label: _showAdvancedOptions
                      ? context.l10n.reviewRatingLessOptions
                      : context.l10n.reviewRatingMoreOptions,
                  icon: Icon(
                    _showAdvancedOptions
                        ? Icons.expand_less
                        : Icons.expand_more,
                  ),
                  onPressed: () {
                    setState(() {
                      _showAdvancedOptions = !_showAdvancedOptions;
                    });
                  },
                ),
              ),

            // Comments
            _buildCommentsSection(theme),
            const SizedBox(height: DS.spacing24),

            // Submit button
            _buildSubmitButton(),
            const SizedBox(height: DS.spacing8),

            // Cancel button
            SparkleButton(
              label: context.l10n.cancel,
              onPressed: _isSubmitting ? null : () => Navigator.pop(context),
              variant: ButtonVariant.ghost,
              expand: true,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStarRating(ThemeData theme) => Row(
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
              padding: const EdgeInsets.symmetric(horizontal: DS.spacing4),
              child: AnimatedScale(
                duration: const Duration(milliseconds: 150),
                scale: isSelected ? 1.1 : 1.0,
                child: Icon(
                  isSelected ? Icons.star_rounded : Icons.star_outline_rounded,
                  size: 44,
                  color: isSelected
                      ? DS.warning
                      : theme.colorScheme.outline.withValues(alpha: 0.5),
                ),
              ),
            ),
          );
        }),
      );

  Widget _buildQuickFeedback(ThemeData theme) => Row(
        children: [
          Expanded(
            child: _buildQuickButton(
              theme: theme,
              icon: Icons.thumb_up_outlined,
              selectedIcon: Icons.thumb_up,
              label: context.l10n.reviewRatingHelpful,
              isSelected: _wasHelpful ?? false,
              onTap: () {
                setState(() {
                  _wasHelpful = _wasHelpful ?? false ? null : true;
                });
              },
            ),
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: _buildQuickButton(
              theme: theme,
              icon: Icons.thumb_down_outlined,
              selectedIcon: Icons.thumb_down,
              label: context.l10n.reviewRatingNotHelpful,
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

  Widget _buildQuickButton({
    required ThemeData theme,
    required IconData icon,
    required IconData selectedIcon,
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
    bool isNegative = false,
  }) {
    final selectedColor =
        isNegative ? theme.colorScheme.error : theme.colorScheme.primary;

    return Material(
      color: isSelected
          ? selectedColor.withValues(alpha: 0.1)
          : theme.colorScheme.surfaceContainerHighest,
      borderRadius: BorderRadius.circular(DS.spacing12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(DS.spacing12),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            vertical: DS.spacing12,
            horizontal: DS.spacing16,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                isSelected ? selectedIcon : icon,
                size: DS.iconSizeSm,
                color: isSelected
                    ? selectedColor
                    : theme.colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: DS.spacing8),
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

  Widget _buildAccuracySection(ThemeData theme) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.reviewRatingAccuracyTitle,
            style: theme.textTheme.titleSmall,
          ),
          const SizedBox(height: DS.spacing8),
          Row(
            children: [
              Expanded(
                child: _buildChoiceChip(
                  theme: theme,
                  label: context.l10n.reviewRatingAccurate,
                  icon: Icons.check_circle_outline,
                  isSelected: _wasAccurate ?? false,
                  onTap: () {
                    setState(() {
                      _wasAccurate = _wasAccurate ?? false ? null : true;
                    });
                  },
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: _buildChoiceChip(
                  theme: theme,
                  label: context.l10n.reviewRatingInaccurate,
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

  Widget _buildSpecificitySection(ThemeData theme) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.reviewRatingSpecificityTitle,
            style: theme.textTheme.titleSmall,
          ),
          const SizedBox(height: DS.spacing8),
          Row(
            children: SpecificityLevel.values
                .map(
                  (level) => Expanded(
                    child: Padding(
                      padding: EdgeInsets.only(
                        left: level == SpecificityLevel.values.first
                            ? 0
                            : DS.spacing4,
                        right: level == SpecificityLevel.values.last
                            ? 0
                            : DS.spacing4,
                      ),
                      child: _buildChoiceChip(
                        theme: theme,
                        label: level.label(context),
                        isSelected: _specificityLevel == level,
                        onTap: () {
                          setState(() {
                            _specificityLevel =
                                _specificityLevel == level ? null : level;
                          });
                        },
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      );

  Widget _buildChoiceChip({
    required ThemeData theme,
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
    IconData? icon,
    bool isNegative = false,
  }) {
    final selectedColor =
        isNegative ? theme.colorScheme.error : theme.colorScheme.primary;

    return Material(
      color: isSelected
          ? selectedColor.withValues(alpha: 0.1)
          : theme.colorScheme.surfaceContainerHighest,
      borderRadius: BorderRadius.circular(DS.spacing8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(DS.spacing8),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            vertical: DS.spacing10,
            horizontal: DS.spacing12,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(
                  icon,
                  size: DS.iconSizeXs,
                  color: isSelected
                      ? selectedColor
                      : theme.colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: DS.spacing4),
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

  Widget _buildInaccuratePointsSection(ThemeData theme) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.reviewRatingInaccuratePointsTitle,
            style: theme.textTheme.titleSmall,
          ),
          const SizedBox(height: DS.spacing8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _inaccuratePointController,
                  decoration: InputDecoration(
                    hintText: context.l10n.reviewRatingInaccuratePointHint,
                    isDense: true,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(DS.spacing8),
                    ),
                  ),
                  onSubmitted: _addInaccuratePoint,
                ),
              ),
              SparkleIconButton(
                icon: const Icon(Icons.add_circle_outline),
                onPressed: () => _addInaccuratePoint(
                  _inaccuratePointController.text,
                ),
                semanticLabel: context.l10n.reviewRatingAddInaccuratePoint,
                variant: ButtonVariant.ghost,
              ),
            ],
          ),
          if (_inaccuratePoints.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing4,
              children: _inaccuratePoints
                  .map(
                    (point) => Chip(
                      label: Text(
                        point,
                        style: theme.textTheme.bodySmall,
                      ),
                      onDeleted: () {
                        setState(() {
                          _inaccuratePoints.remove(point);
                        });
                      },
                      deleteIcon: const Icon(Icons.close, size: DS.iconSizeXs),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      );

  void _addInaccuratePoint(String point) {
    final trimmed = point.trim();
    if (trimmed.isNotEmpty && !_inaccuratePoints.contains(trimmed)) {
      setState(() {
        _inaccuratePoints.add(trimmed);
        _inaccuratePointController.clear();
      });
    }
  }

  Widget _buildTagsSection(ThemeData theme) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.reviewRatingTagsTitle,
            style: theme.textTheme.titleSmall,
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: _availableTags(context).map((tag) {
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

  Widget _buildCommentsSection(ThemeData theme) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.reviewRatingCommentsTitle,
            style: theme.textTheme.titleSmall,
          ),
          const SizedBox(height: DS.spacing8),
          TextField(
            controller: _commentsController,
            maxLines: 3,
            decoration: InputDecoration(
              hintText: context.l10n.reviewRatingCommentsHint,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(DS.spacing12),
              ),
            ),
          ),
        ],
      );

  Widget _buildSubmitButton() {
    final hasValidFeedback = _rating != null || _wasHelpful != null;

    return SparkleButton(
      label: context.l10n.reviewRatingSubmit,
      onPressed: hasValidFeedback && !_isSubmitting ? _handleSubmit : null,
      loading: _isSubmitting,
      disabled: !hasValidFeedback || _isSubmitting,
      expand: true,
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
          AppFeedback.success(context, context.l10n.reviewRatingSubmitSuccess);
        } else {
          AppFeedback.error(context, context.l10n.reviewRatingSubmitFailed);
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
