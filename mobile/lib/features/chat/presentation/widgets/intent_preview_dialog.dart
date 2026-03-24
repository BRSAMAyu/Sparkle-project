import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/intent/data/models/intent_data.dart';
import 'package:sparkle/features/intent/data/repositories/intent_repository.dart';

/// Intent Preview Dialog
///
/// Shows a preview of detected intents in the user's message
/// before execution. Allows the user to confirm or modify.
class IntentPreviewDialog extends ConsumerStatefulWidget {
  const IntentPreviewDialog({
    required this.message,
    required this.onConfirm,
    super.key,
  });

  final String message;
  final VoidCallback onConfirm;

  @override
  ConsumerState<IntentPreviewDialog> createState() =>
      _IntentPreviewDialogState();
}

class _IntentPreviewDialogState extends ConsumerState<IntentPreviewDialog> {
  bool _isAnalyzing = true;
  bool _isExecuting = false;
  List<IntentData> _intents = [];
  String? _errorMessage;
  String? _executionPlan;
  int? _estimatedTime;

  @override
  void initState() {
    super.initState();
    _analyzeIntents();
  }

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              DS.surfacePrimary,
              Color.alphaBlend(
                DS.info.withValues(alpha: 0.03),
                DS.surfaceSecondary,
              ),
            ],
          ),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header
            _buildHeader(context),

            // Content
            Flexible(
              child: _buildContent(context),
            ),

            // Actions
            _buildActions(context),
          ],
        ),
      );

  Widget _buildHeader(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: DS.border,
            ),
          ),
        ),
        child: Row(
          children: [
            Icon(Icons.auto_awesome, color: DS.info),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Text(
                context.l10n.intentPreviewTitle,
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: DS.textPrimary,
                ),
              ),
            ),
            SparkleIconButton(
              icon: const Icon(Icons.close),
              onPressed: () => Navigator.of(context).pop(false),
              variant: ButtonVariant.ghost,
            ),
          ],
        ),
      );

  Widget _buildContent(BuildContext context) {
    if (_isAnalyzing) {
      return SizedBox(
        height: 200,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              Text(context.l10n.intentPreviewAnalyzing),
            ],
          ),
        ),
      );
    }

    if (_errorMessage != null) {
      return SizedBox(
        height: 200,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, color: DS.error, size: 48),
              const SizedBox(height: DS.md),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: DS.md),
                child: Text(
                  _errorMessage!,
                  style: TextStyle(color: DS.textSecondary),
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: DS.md),
              SparkleButton.outline(
                label: context.l10n.retry,
                onPressed: () {
                  SensoryFeedbackService.emit(
                    SensoryFeedbackEvent.selection,
                  );
                  _analyzeIntents();
                },
              ),
            ],
          ),
        ),
      );
    }

    if (_intents.isEmpty) {
      return SizedBox(
        height: 200,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.info_outline, color: DS.info, size: 48),
              const SizedBox(height: DS.md),
              Text(
                context.l10n.intentPreviewSingleIntent,
                style: TextStyle(color: DS.textPrimary),
              ),
              const SizedBox(height: DS.sm),
              Text(
                '"${widget.message}"',
                style: TextStyle(
                  color: DS.textSecondary,
                  fontStyle: FontStyle.italic,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(DS.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            context.l10n.intentPreviewDetectedCount(_intents.length),
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: DS.textPrimary,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          ...List.generate(
            _intents.length,
            (index) => _buildIntentItem(context, _intents[index], index + 1),
          ),
          const SizedBox(height: DS.spacing12),
          _buildExecutionPlan(context),
        ],
      ),
    );
  }

  Widget _buildIntentItem(BuildContext context, IntentData intent, int index) =>
      Container(
        margin: const EdgeInsets.only(bottom: DS.spacing12),
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              DS.surfaceTertiary.withValues(alpha: 0.6),
              Color.alphaBlend(
                _getIntentColor(intent.type).withValues(alpha: 0.04),
                DS.surfacePrimary,
              ),
            ],
          ),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _getIntentColor(intent.type).withValues(alpha: 0.3),
            width: 2,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.sm,
                    vertical: DS.xs,
                  ),
                  decoration: BoxDecoration(
                    color: _getIntentColor(intent.type),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '#$index',
                    style: TextStyle(
                      color: DS.onBrandPrimary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(width: DS.sm),
                Expanded(
                  child: Text(
                    _getIntentLabel(intent.type),
                    style: TextStyle(
                      fontWeight: FontWeight.w500,
                      color: DS.textPrimary,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: _getConfidenceColor(intent.confidence),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '${(intent.confidence * 100).toInt()}%',
                    style: TextStyle(
                      color: DS.onBrandPrimary,
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.sm),
            Text(
              intent.content,
              style: TextStyle(
                fontSize: 14,
                color: DS.textPrimary,
              ),
            ),
            if (intent.agentRole != null) ...[
              const SizedBox(height: DS.xs),
              Row(
                children: [
                  Icon(
                    Icons.person,
                    size: 14,
                    color: DS.textSecondary,
                  ),
                  const SizedBox(width: DS.xs),
                  Text(
                    context.l10n.intentPreviewAssistantRole(
                      _getAgentRoleLabel(intent.agentRole!),
                    ),
                    style: TextStyle(
                      fontSize: 11,
                      color: DS.textSecondary,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      );

  Widget _buildExecutionPlan(BuildContext context) {
    final planText = _executionPlan ?? _generateExecutionPlan();
    final title = _estimatedTime != null
        ? context.l10n.intentPreviewExecutionPlanWithTime(_estimatedTime!)
        : context.l10n.intentPreviewExecutionPlan;

    return Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.info.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: DS.info.withValues(alpha: 0.25),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.schedule, size: 16, color: DS.info),
              const SizedBox(width: DS.sm),
              Text(
                title,
                style: TextStyle(
                  color: DS.info,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.sm),
          Text(
            planText,
            style: TextStyle(
              fontSize: 12,
              color: DS.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActions(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          border: Border(
            top: BorderSide(
              color: DS.border,
            ),
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: SparkleButton.outline(
                label: context.l10n.cancel,
                onPressed: () => Navigator.of(context).pop(false),
                expand: true,
              ),
            ),
            const SizedBox(width: DS.md),
            Expanded(
              child: SparkleButton(
                label: context.l10n.intentPreviewConfirmExecute,
                onPressed: _executeIntents,
                expand: true,
                loading: _isExecuting,
                disabled: _isExecuting,
              ),
            ),
          ],
        ),
      );

  Color _getIntentColor(String type) {
    switch (type) {
      case 'task_management':
        return DS.taskPlanning;
      case 'knowledge_query':
        return DS.info;
      case 'time_planning':
        return DS.success;
      case 'social':
        return DS.taskSocial;
      case 'learning':
        return DS.taskLearning;
      case 'reflection':
        return DS.taskReflection;
      case 'tool_call':
        return DS.error;
      default:
        return DS.neutral500;
    }
  }

  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.8) return DS.success;
    if (confidence >= 0.6) return DS.warning;
    return DS.error;
  }

  String _getIntentLabel(String type) {
    switch (type) {
      case 'task_management':
        return context.l10n.intentTypeTaskManagement;
      case 'knowledge_query':
        return context.l10n.intentTypeKnowledgeQuery;
      case 'time_planning':
        return context.l10n.intentTypeTimePlanning;
      case 'social':
        return context.l10n.intentTypeSocial;
      case 'learning':
        return context.l10n.intentTypeLearning;
      case 'reflection':
        return context.l10n.intentTypeReflection;
      case 'tool_call':
        return context.l10n.intentTypeToolCall;
      default:
        return context.l10n.intentTypeUnknown;
    }
  }

  String _getAgentRoleLabel(String role) {
    switch (role) {
      case 'galaxy_guide':
        return context.l10n.intentAgentGalaxyGuide;
      case 'time_tutor':
        return context.l10n.intentAgentTimeTutor;
      case 'exam_oracle':
        return context.l10n.intentAgentExamOracle;
      case 'study_buddy':
        return context.l10n.intentAgentStudyBuddy;
      default:
        return role;
    }
  }

  String _generateExecutionPlan() {
    if (_intents.isEmpty) return context.l10n.intentPreviewDirectExecute;

    final buffer = StringBuffer();
    for (var i = 0; i < _intents.length; i++) {
      if (i > 0) buffer.write(' → ');
      buffer.write(_getIntentLabel(_intents[i].type));
    }

    return buffer.toString();
  }

  Future<void> _analyzeIntents() async {
    setState(() {
      _isAnalyzing = true;
      _errorMessage = null;
      _executionPlan = null;
      _estimatedTime = null;
    });

    try {
      final repository = ref.read(intentRepositoryProvider);
      final response = await repository.previewIntents(widget.message);

      if (mounted) {
        setState(() {
          _isAnalyzing = false;
          _intents = response.detectedIntents;
          _executionPlan = response.executionPlan;
          _estimatedTime = response.estimatedTime;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isAnalyzing = false;
          _errorMessage = context.l10n.intentAnalysisFailed(e.toString());
        });
      }
    }
  }

  Future<void> _executeIntents() async {
    setState(() => _isExecuting = true);

    try {
      final repository = ref.read(intentRepositoryProvider);
      final response = await repository.analyzeAndExecute(
        widget.message,
        autoExecute: true, // 用户已确认，直接执行
      );

      if (mounted) {
        // 先关闭弹窗
        Navigator.of(context).pop(true);

        final result = response.executionResult;
        if (result?.success ?? false) {
          // 执行成功，调用确认回调
          widget.onConfirm();
        } else {
          // 执行失败，显示错误
          final errorMsg =
              result?.errorMessages ?? context.l10n.intentExecutionFailed;
          AppFeedback.error(context, errorMsg);
        }
      }
    } catch (e) {
      if (mounted) {
        // 错误时也关闭弹窗
        Navigator.of(context).pop(false);
        AppFeedback.error(
          context,
          context.l10n.intentExecutionFailedWithDetail(e.toString()),
        );
      }
    }
  }
}
