import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Regeneration type options
enum RegenerationType {
  improveQuality('improve_quality', Icons.auto_awesome),
  fixIssues('fix_issues', Icons.build_outlined),
  changeStyle('change_style', Icons.style_outlined),
  addDetails('add_details', Icons.add_circle_outline),
  simplify('simplify', Icons.compress),
  custom('custom', Icons.edit_outlined);

  const RegenerationType(this.value, this.icon);
  final String value;
  final IconData icon;

  String label(BuildContext context) {
    final l10n = context.l10n;
    switch (this) {
      case RegenerationType.improveQuality:
        return l10n.regenTypeImproveQuality;
      case RegenerationType.fixIssues:
        return l10n.regenTypeFixIssues;
      case RegenerationType.changeStyle:
        return l10n.regenTypeChangeStyle;
      case RegenerationType.addDetails:
        return l10n.regenTypeAddDetails;
      case RegenerationType.simplify:
        return l10n.regenTypeSimplify;
      case RegenerationType.custom:
        return l10n.regenTypeCustom;
    }
  }
}

/// Regeneration status
enum RegenerationStatus {
  idle,
  pending,
  inProgress,
  completed,
  failed,
}

/// Regeneration request data
class RegenerationRequestData {
  const RegenerationRequestData({
    required this.originalContentId,
    required this.reviewId,
    required this.regenerationType,
    this.improvementHints = const [],
    this.focusAreas = const [],
    this.customInstructions,
  });

  final String originalContentId;
  final String reviewId;
  final RegenerationType regenerationType;
  final List<String> improvementHints;
  final List<String> focusAreas;
  final String? customInstructions;

  Map<String, dynamic> toJson() => {
        'original_content_id': originalContentId,
        'review_id': reviewId,
        'regeneration_type': regenerationType.value,
        if (improvementHints.isNotEmpty) 'improvement_hints': improvementHints,
        if (focusAreas.isNotEmpty) 'focus_areas': focusAreas,
        if (customInstructions != null)
          'custom_instructions': customInstructions,
      };
}

/// Regeneration result data
class RegenerationResultData {
  const RegenerationResultData({
    required this.requestId,
    required this.success,
    this.newContent,
    this.improvementSummary,
    this.changesMade = const [],
    this.scoreImprovement = 0.0,
  });

  factory RegenerationResultData.fromJson(Map<String, dynamic> json) =>
      RegenerationResultData(
        requestId: json['request_id'] as String? ?? '',
        success: json['success'] as bool? ?? false,
        newContent: json['new_content'] as String?,
        improvementSummary: json['improvement_summary'] as String?,
        changesMade: (json['changes_made'] as List<dynamic>?)
                ?.map((e) => e.toString())
                .toList() ??
            [],
        scoreImprovement:
            (json['score_improvement'] as num?)?.toDouble() ?? 0.0,
      );

  final String requestId;
  final bool success;
  final String? newContent;
  final String? improvementSummary;
  final List<String> changesMade;
  final double scoreImprovement;
}

/// Regeneration prompt widget - shows regeneration options and status
class RegenerationPrompt extends StatefulWidget {
  const RegenerationPrompt({
    required this.originalContentId,
    required this.reviewId,
    required this.onRegenerate,
    this.status = RegenerationStatus.idle,
    this.result,
    this.suggestedType,
    this.suggestedHints = const [],
    super.key,
  });

  final String originalContentId;
  final String reviewId;
  final Future<RegenerationResultData?> Function(
    RegenerationRequestData request,
  ) onRegenerate;
  final RegenerationStatus status;
  final RegenerationResultData? result;
  final RegenerationType? suggestedType;
  final List<String> suggestedHints;

  @override
  State<RegenerationPrompt> createState() => _RegenerationPromptState();
}

class _RegenerationPromptState extends State<RegenerationPrompt>
    with SingleTickerProviderStateMixin {
  RegenerationType? _selectedType;
  final List<String> _selectedHints = [];
  final _customInstructionsController = TextEditingController();
  bool _isExpanded = false;
  bool _isSubmitting = false;

  late AnimationController _animationController;
  late Animation<double> _progressAnimation;

  List<String> _availableHints(BuildContext context) => [
        context.l10n.regenHintMoreAccurate,
        context.l10n.regenHintMoreDetailed,
        context.l10n.regenHintMoreConcise,
        context.l10n.regenHintFriendlierTone,
        context.l10n.regenHintAddExamples,
        context.l10n.regenHintFixErrors,
      ];

  @override
  void initState() {
    super.initState();
    _selectedType = widget.suggestedType;
    _selectedHints.addAll(widget.suggestedHints);

    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
    _progressAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeInOut),
    );

    if (widget.status == RegenerationStatus.inProgress) {
      unawaited(_animationController.repeat());
    }
  }

  @override
  void didUpdateWidget(RegenerationPrompt oldWidget) {
    super.didUpdateWidget(oldWidget);

    if (widget.status == RegenerationStatus.inProgress &&
        oldWidget.status != RegenerationStatus.inProgress) {
      unawaited(_animationController.repeat());
    } else if (widget.status != RegenerationStatus.inProgress &&
        oldWidget.status == RegenerationStatus.inProgress) {
      _animationController
        ..stop()
        ..reset();
    }
  }

  @override
  void dispose() {
    _animationController.dispose();
    _customInstructionsController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: theme.colorScheme.outline.withValues(alpha: 0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          _buildHeader(theme),

          // Content based on status
          if (widget.status == RegenerationStatus.inProgress)
            _buildProgressContent(theme)
          else if (widget.status == RegenerationStatus.completed &&
              widget.result != null)
            _buildResultContent(theme)
          else if (widget.status == RegenerationStatus.failed)
            _buildFailedContent(theme)
          else if (_isExpanded)
            _buildOptionsContent(theme),
        ],
      ),
    );
  }

  Widget _buildHeader(ThemeData theme) => InkWell(
        onTap: widget.status == RegenerationStatus.idle
            ? () {
                setState(() {
                  _isExpanded = !_isExpanded;
                });
              }
            : null,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing16),
          child: Row(
            children: [
              Icon(
                _getStatusIcon(),
                color: _getStatusColor(theme),
                size: 20,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _getStatusTitle(),
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (widget.status != RegenerationStatus.idle)
                      Text(
                        _getStatusDescription(),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                  ],
                ),
              ),
              if (widget.status == RegenerationStatus.idle)
                Icon(
                  _isExpanded ? Icons.expand_less : Icons.expand_more,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
            ],
          ),
        ),
      );

  Widget _buildProgressContent(ThemeData theme) => Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing16,
        ),
        child: Column(
          children: [
            // Animated progress indicator
            AnimatedBuilder(
              animation: _progressAnimation,
              builder: (context, child) => LinearProgressIndicator(
                backgroundColor:
                    theme.colorScheme.primary.withValues(alpha: 0.2),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  context.l10n.regenProgressTitle,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ],
        ),
      );

  Widget _buildResultContent(ThemeData theme) {
    final result = widget.result!;

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing16,
        0,
        DS.spacing16,
        DS.spacing16,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Success indicator
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: result.success
                  ? DS.success.withValues(alpha: 0.1)
                  : theme.colorScheme.error.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Icon(
                  result.success ? Icons.check_circle : Icons.error,
                  size: 16,
                  color: result.success ? DS.success : theme.colorScheme.error,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    result.success
                        ? context.l10n.regenResultSuccess
                        : result.improvementSummary ??
                            context.l10n.regenResultFailed,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color:
                          result.success ? DS.success : theme.colorScheme.error,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Changes made
          if (result.success && result.changesMade.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              context.l10n.regenImprovementsTitle,
              style: theme.textTheme.labelMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            ...result.changesMade.map(
              (change) => Padding(
                padding: const EdgeInsets.only(left: 8, top: 2),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('• '),
                    Expanded(
                      child: Text(
                        change,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],

          // Score improvement
          if (result.success && result.scoreImprovement > 0) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(DS.spacing8),
              decoration: BoxDecoration(
                color: DS.success.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.trending_up,
                    size: DS.iconSizeXs,
                    color: DS.success,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    context.l10n.regenQualityImprovement(
                      (result.scoreImprovement * 100).toStringAsFixed(0),
                    ),
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: DS.success,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildFailedContent(ThemeData theme) => Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing16,
        ),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: theme.colorScheme.error.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.error_outline,
                    color: theme.colorScheme.error,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      context.l10n.regenRetryMessage,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.error,
                      ),
                    ),
                  ),
                  SparkleButton(
                    label: context.l10n.commonRetry,
                    icon: const Icon(Icons.refresh_rounded),
                    onPressed: _submitRegeneration,
                    variant: ButtonVariant.ghost,
                    size: ButtonSize.small,
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _buildOptionsContent(ThemeData theme) => Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing16,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Regeneration type selection
            Text(
              context.l10n.regenSelectType,
              style: theme.textTheme.labelMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: RegenerationType.values.map((type) {
                final isSelected = _selectedType == type;
                return ChoiceChip(
                  label: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(type.icon, size: 16),
                      const SizedBox(width: 4),
                      Text(type.label(context)),
                    ],
                  ),
                  selected: isSelected,
                  onSelected: (selected) {
                    setState(() {
                      _selectedType = selected ? type : null;
                    });
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 16),

            // Improvement hints
            Text(
              context.l10n.regenHintsOptional,
              style: theme.textTheme.labelMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _availableHints(context).map((hint) {
                final isSelected = _selectedHints.contains(hint);
                return FilterChip(
                  label: Text(hint),
                  selected: isSelected,
                  onSelected: (selected) {
                    setState(() {
                      if (selected) {
                        _selectedHints.add(hint);
                      } else {
                        _selectedHints.remove(hint);
                      }
                    });
                  },
                );
              }).toList(),
            ),

            // Custom instructions (only for custom type)
            if (_selectedType == RegenerationType.custom) ...[
              const SizedBox(height: 16),
              TextField(
                controller: _customInstructionsController,
                maxLines: 3,
                decoration: InputDecoration(
                  hintText: context.l10n.regenCustomHint,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 16),

            // Submit button
            SparkleButton(
              label: _isSubmitting
                  ? context.l10n.commonProcessing
                  : context.l10n.regenStart,
              onPressed: _selectedType != null && !_isSubmitting
                  ? _submitRegeneration
                  : null,
              icon: _isSubmitting
                  ? null
                  : const Icon(Icons.refresh, size: DS.iconSizeXs),
              loading: _isSubmitting,
              disabled: _selectedType == null || _isSubmitting,
              expand: true,
            ),
          ],
        ),
      );

  IconData _getStatusIcon() {
    switch (widget.status) {
      case RegenerationStatus.idle:
        return Icons.refresh;
      case RegenerationStatus.pending:
      case RegenerationStatus.inProgress:
        return Icons.hourglass_empty;
      case RegenerationStatus.completed:
        return widget.result?.success ?? false
            ? Icons.check_circle
            : Icons.error;
      case RegenerationStatus.failed:
        return Icons.error;
    }
  }

  Color _getStatusColor(ThemeData theme) {
    switch (widget.status) {
      case RegenerationStatus.idle:
        return theme.colorScheme.primary;
      case RegenerationStatus.pending:
      case RegenerationStatus.inProgress:
        return theme.colorScheme.secondary;
      case RegenerationStatus.completed:
        return widget.result?.success ?? false
            ? DS.success
            : theme.colorScheme.error;
      case RegenerationStatus.failed:
        return theme.colorScheme.error;
    }
  }

  String _getStatusTitle() {
    final l10n = context.l10n;
    switch (widget.status) {
      case RegenerationStatus.idle:
        return l10n.regenTitleIdle;
      case RegenerationStatus.pending:
        return l10n.regenTitlePending;
      case RegenerationStatus.inProgress:
        return l10n.regenTitleInProgress;
      case RegenerationStatus.completed:
        return widget.result?.success ?? false
            ? l10n.regenTitleCompleted
            : l10n.regenTitleFailed;
      case RegenerationStatus.failed:
        return l10n.regenTitleFailed;
    }
  }

  String _getStatusDescription() {
    final l10n = context.l10n;
    switch (widget.status) {
      case RegenerationStatus.idle:
        return '';
      case RegenerationStatus.pending:
        return l10n.regenDescPending;
      case RegenerationStatus.inProgress:
        return l10n.regenDescInProgress;
      case RegenerationStatus.completed:
        return widget.result?.improvementSummary ?? l10n.regenDescCompleted;
      case RegenerationStatus.failed:
        return l10n.regenDescFailed;
    }
  }

  Future<void> _submitRegeneration() async {
    if (_selectedType == null || _isSubmitting) return;

    setState(() {
      _isSubmitting = true;
    });

    final request = RegenerationRequestData(
      originalContentId: widget.originalContentId,
      reviewId: widget.reviewId,
      regenerationType: _selectedType!,
      improvementHints: _selectedHints,
      customInstructions: _selectedType == RegenerationType.custom
          ? _customInstructionsController.text.trim()
          : null,
    );

    try {
      await widget.onRegenerate(request);
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }
}
