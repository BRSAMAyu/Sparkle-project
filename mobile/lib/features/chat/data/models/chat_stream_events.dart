import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';

/// 聊天流事件基类
abstract class ChatStreamEvent {
  const ChatStreamEvent({
    this.responseId,
    this.traceId,
    this.workflowId,
    this.promptVersion,
    this.metadata,
  });

  final String? responseId;
  final String? traceId;
  final String? workflowId;
  final String? promptVersion;
  final Map<String, dynamic>? metadata;
}

/// 文本事件
class TextEvent extends ChatStreamEvent {
  TextEvent({
    required this.content,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
    super.metadata,
  });
  final String content;
}

/// 工具开始事件
class ToolStartEvent extends ChatStreamEvent {
  ToolStartEvent({
    required this.toolName,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final String toolName;
}

/// 工具结果事件
class ToolResultEvent extends ChatStreamEvent {
  ToolResultEvent({
    required this.result,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final ToolResultModel result;
}

/// Widget 事件
class WidgetEvent extends ChatStreamEvent {
  WidgetEvent({
    required this.widgetType,
    required this.widgetData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final String widgetType;
  final Map<String, dynamic> widgetData;
}

/// 完成事件
class DoneEvent extends ChatStreamEvent {
  DoneEvent({
    this.finishReason,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final String? finishReason;
}

/// 未知事件
class UnknownEvent extends ChatStreamEvent {
  UnknownEvent({
    required this.data,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final Map<String, dynamic> data;
}

/// 状态更新事件（THINKING, GENERATING 等）
class StatusUpdateEvent extends ChatStreamEvent {
  StatusUpdateEvent({
    required this.state,
    required this.details,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final String state;
  final String details;
}

/// 完整文本事件
class FullTextEvent extends ChatStreamEvent {
  FullTextEvent({
    required this.content,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final String content;
}

/// 错误事件
class ErrorEvent extends ChatStreamEvent {
  ErrorEvent({
    required this.code,
    required this.message,
    required this.retryable,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final String code;
  final String message;
  final bool retryable;
}

/// Token 使用统计事件
class UsageEvent extends ChatStreamEvent {
  UsageEvent({
    required this.promptTokens,
    required this.completionTokens,
    required this.totalTokens,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final int promptTokens;
  final int completionTokens;
  final int totalTokens;
}

/// 推理步骤事件（Chain of Thought Visualization）
class ReasoningStepEvent extends ChatStreamEvent {
  ReasoningStepEvent({
    required this.step,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final ReasoningStep step;
}

/// 引用事件
class CitationEvent extends ChatStreamEvent {
  CitationEvent({
    required this.citations,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final List<Map<String, dynamic>> citations;
}

/// ActionCard 状态事件
class ActionStatusEvent extends ChatStreamEvent {
  ActionStatusEvent({
    required this.actionId,
    required this.status,
    this.message,
    this.widgetType,
    this.timestamp,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final String actionId;
  final String status; // 'confirmed', 'dismissed'
  final String? message;
  final String? widgetType;
  final int? timestamp;
}

/// Plan Review 状态事件
class PlanReviewStatusEvent extends ChatStreamEvent {
  PlanReviewStatusEvent({
    required this.reviewId,
    required this.status,
    this.message,
    this.userDecision,
    this.timestamp,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final String reviewId;
  final String status; // 'approved', 'rejected', 'modify_requested', 'acknowledged'
  final String? message;
  final String? userDecision;
  final int? timestamp;
}

/// Plan Review Widget Event (for displaying review cards)
class PlanReviewWidgetEvent extends ChatStreamEvent {
  PlanReviewWidgetEvent({
    required this.reviewData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final Map<String, dynamic> reviewData;
}

/// Milestone Proposal Event
class MilestoneProposalEvent extends ChatStreamEvent {
  MilestoneProposalEvent({
    required this.proposalData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final Map<String, dynamic> proposalData;
}

/// ============================================
/// Phase 2b: Content Review Event
/// ============================================

/// Content Review Widget Event - 显示内容审查结果
/// 用于展示ReviewResult的审查反馈（非Plan专用）
class ContentReviewWidgetEvent extends ChatStreamEvent {
  ContentReviewWidgetEvent({
    required this.reviewData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  /// 审查结果数据
  final Map<String, dynamic> reviewData;

  /// 审查ID
  String get reviewId => reviewData['review_id'] as String? ?? '';

  /// 审查决策: passed/failed/needs_refinement
  String get decision => reviewData['decision'] as String? ?? 'needs_refinement';

  /// 总体评分 0-1
  double get overallScore => (reviewData['overall_score'] as num?)?.toDouble() ?? 0.0;

  /// 是否通过审查
  bool get passed => decision == 'passed' && overallScore >= 0.7;

  /// 指标列表
  List<Map<String, dynamic>> get metrics {
    final metricsList = reviewData['metrics'] as List<dynamic>?;
    return metricsList
            ?.map((e) => Map<String, dynamic>.from(e as Map))
            .toList() ??
        [];
  }

  /// 问题列表
  List<Map<String, dynamic>> get issues {
    final issuesList = reviewData['issues'] as List<dynamic>?;
    return issuesList
            ?.map((e) => Map<String, dynamic>.from(e as Map))
            .toList() ??
        [];
  }

  /// 严重问题数量
  int get criticalCount => reviewData['critical_count'] as int? ?? 0;

  /// 警告问题数量
  int get warningCount => reviewData['warning_count'] as int? ?? 0;

  /// 改进建议
  List<String> get suggestions {
    final suggestionsList = reviewData['suggestions'] as List<dynamic>?;
    return suggestionsList?.map((e) => e.toString()).toList() ?? [];
  }

  /// 是否需要反思修正
  bool get requiresReflection => reviewData['requires_reflection'] as bool? ?? false;
}

/// Content Reflection Result Event - 反思修正完成事件
class ContentReflectionResultEvent extends ChatStreamEvent {
  ContentReflectionResultEvent({
    required this.reflectionData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> reflectionData;

  /// 反思ID
  String get reflectionId => reflectionData['reflection_id'] as String? ?? '';

  /// 反思结果: fixed/improved/no_change/degraded/failed
  String get outcome => reflectionData['outcome'] as String? ?? 'unknown';

  /// 分数变化
  double get scoreDelta => (reflectionData['score_delta'] as num?)?.toDouble() ?? 0.0;

  /// 执行轮数
  int get rounds => reflectionData['rounds'] as int? ?? 0;

  /// 修正后的内容
  String? get fixedContent => reflectionData['fixed_content'] as String?;
}
