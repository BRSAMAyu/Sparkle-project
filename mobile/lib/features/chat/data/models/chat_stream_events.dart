import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:sparkle/core/models/intervention.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

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

class SprintModeSwitchEvent extends ChatStreamEvent {
  SprintModeSwitchEvent({
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
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
    this.currentAgentName,
    this.activeAgentType,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final String state;
  final String details;
  final String? currentAgentName;
  final String? activeAgentType;
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
    this.costMicroUsd,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final int promptTokens;
  final int completionTokens;
  final int totalTokens;
  final int? costMicroUsd;
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

/// State Change Event - Major state change notifications
/// Triggered when: plan archived/restored/deleted, settings updated, memory cleanup
class StateChangeEvent extends ChatStreamEvent {
  StateChangeEvent({
    required this.changeData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> changeData;

  /// Type of state change
  String get changeType => changeData['change_type'] as String? ?? 'unknown';

  /// Change ID (UUID)
  String get changeId => changeData['change_id'] as String? ?? '';

  /// ISO timestamp
  String get timestamp => changeData['timestamp'] as String? ?? '';

  /// Intervention level: toast, card, modal
  String get interventionLevel => changeData['intervention_level'] as String? ?? 'toast';

  /// Priority: low, medium, high
  String get priority => changeData['priority'] as String? ?? 'low';

  /// Pre-formatted user-friendly message
  String get formattedMessage => changeData['formatted_message'] as String? ?? '';

  /// Plan-specific fields (for plan_archived, plan_restored, plan_deleted)
  String? get planName => changeData['plan_name'] as String?;
  String? get planId => changeData['plan_id'] as String?;
  int get taskCountFreed => changeData['task_count_freed'] as int? ?? 0;
  int get memoryCountRemoved => changeData['memory_count_removed'] as int? ?? 0;
  String? get newPrimaryPlan => changeData['new_primary_plan'] as String?;

  /// Settings-specific fields (for user_settings_updated)
  String? get settingField => changeData['setting_field'] as String?;
  String? get fieldLabel => changeData['field_label'] as String?;
  dynamic get oldValue => changeData['old_value'];
  dynamic get newValue => changeData['new_value'];
  String? get impactDescription => changeData['impact_description'] as String?;

  /// Memory-specific fields (for memory_cleanup)
  int get memoriesRemoved => changeData['memories_removed'] as int? ?? 0;
  double get spaceFreedMb => (changeData['space_freed_mb'] as num?)?.toDouble() ?? 0.0;

  /// Convert to InterventionPushMessage for display
  InterventionPushMessage toInterventionMessage() => InterventionPushMessage(
      interventionId: changeId,
      level: _mapInterventionLevel(),
      content: InterventionContent(
        renderedMessage: formattedMessage,
        intentType: changeType,
        templateId: 'state_change_$changeType',
        scaffoldingLevel: 0,
        contextVariables: {
          'change_type': changeType,
          'change_id': changeId,
          'timestamp': timestamp,
          if (planId != null) 'plan_id': planId!,
          if (planName != null) 'plan_name': planName!,
        },
      ),
      actions: _getActions(),
      expiresAt: DateTime.now().add(const Duration(hours: 24)),
    );

  InterventionLevel _mapInterventionLevel() {
    switch (interventionLevel) {
      case 'modal':
        return InterventionLevel.modal;
      case 'card':
        return InterventionLevel.card;
      case 'toast':
      default:
        return InterventionLevel.toast;
    }
  }

  List<InterventionAction> _getActions() {
    // For plan changes, offer to view the plan
    if (planId != null && changeType.startsWith('plan_')) {
      return [
        const InterventionAction(
          id: 'view_plan',
          label: '查看计划',
          type: 'navigation',
        ),
      ];
    }

    // For settings changes, offer to view settings
    if (changeType == 'user_settings_updated') {
      return [
        const InterventionAction(
          id: 'view_settings',
          label: '查看设置',
          type: 'navigation',
        ),
      ];
    }

    // Default: just acknowledge
    return [
      const InterventionAction(
        id: 'acknowledge',
        label: '知道了',
        type: 'secondary',
      ),
    ];
  }
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

/// ============================================
/// Phase 2e: Review Override & Appeal Events
/// ============================================

/// Review Override Event - 用户覆盖审查决策事件
class ReviewOverrideEvent extends ChatStreamEvent {
  ReviewOverrideEvent({
    required this.overrideData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> overrideData;

  /// 覆盖ID
  String get overrideId => overrideData['override_id'] as String? ?? '';

  /// 审查ID
  String get reviewId => overrideData['review_id'] as String? ?? '';

  /// 原决策
  String get originalDecision => overrideData['original_decision'] as String? ?? '';

  /// 新决策
  String get newDecision => overrideData['new_decision'] as String? ?? '';

  /// 是否成功
  bool get success => overrideData['success'] as bool? ?? false;

  /// 消息
  String? get message => overrideData['message'] as String?;
}

/// Review Appeal Event - 用户提交申诉事件
class ReviewAppealEvent extends ChatStreamEvent {
  ReviewAppealEvent({
    required this.appealData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> appealData;

  /// 申诉ID
  String get appealId => appealData['appeal_id'] as String? ?? '';

  /// 审查ID
  String get reviewId => appealData['review_id'] as String? ?? '';

  /// 申诉状态: pending, in_review, resolved, rejected, escalated
  String get status => appealData['status'] as String? ?? 'pending';

  /// 是否成功提交
  bool get success => appealData['success'] as bool? ?? false;

  /// 消息
  String? get message => appealData['message'] as String?;
}

/// Appeal Result Event - 申诉处理结果事件
class AppealResultEvent extends ChatStreamEvent {
  AppealResultEvent({
    required this.resultData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> resultData;

  /// 申诉ID
  String get appealId => resultData['appeal_id'] as String? ?? '';

  /// 申诉状态
  String get status => resultData['status'] as String? ?? '';

  /// 解决方案
  String? get resolution => resultData['resolution'] as String?;

  /// 解决者
  String? get resolvedBy => resultData['resolved_by'] as String?;

  /// 解决时间
  String? get resolvedAt => resultData['resolved_at'] as String?;

  /// 二次审查决策
  String? get secondaryDecision => resultData['secondary_decision'] as String?;

  /// 二次审查分数
  double? get secondaryScore => (resultData['secondary_score'] as num?)?.toDouble();

  /// 是否申诉通过
  bool get isApproved => status == 'resolved';

  /// 是否被拒绝
  bool get isRejected => status == 'rejected';

  /// 是否升级到人工
  bool get isEscalated => status == 'escalated';
}

/// ============================================
/// Achievement Unlock Event
/// ============================================

/// Achievement Unlock Widget Event - 成就解锁通知事件
/// 用于实时通知用户成就解锁
class AchievementUnlockEvent extends ChatStreamEvent {
  AchievementUnlockEvent({
    required this.achievementData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  /// 成就数据
  final Map<String, dynamic> achievementData;

  /// 成就ID
  String get achievementId => achievementData['achievement_id'] as String? ?? '';

  /// 成就名称
  String get name => achievementData['name'] as String? ?? '';

  /// 成就稀有度
  AchievementRarity get rarity {
    final rarityStr = achievementData['rarity'] as String?;
    return AchievementRarity.values.firstWhere(
      (r) => r.name == rarityStr,
      orElse: () => AchievementRarity.common,
    );
  }

  /// 解锁时间
  DateTime get unlockedAt {
    final timestamp = achievementData['unlocked_at'];
    if (timestamp is String) {
      return DateTime.parse(timestamp);
    }
    return DateTime.now();
  }

  /// 是否首位解锁者
  bool get isFirst => achievementData['is_first'] as bool? ?? false;

  /// 视觉效果类型
  VisualEffectType? get visualEffectType {
    final effectStr = achievementData['visual_effect_type'] as String?;
    if (effectStr == null) return null;
    return VisualEffectType.values.firstWhere(
      (e) => e.name == effectStr,
      orElse: () => VisualEffectType.none,
    );
  }

  /// 视觉效果配置
  Map<String, dynamic>? get visualEffect =>
      achievementData['visual_effect'] as Map<String, dynamic>?;

  /// 奖励配置
  List<Map<String, dynamic>>? get rewards =>
      achievementData['rewards'] as List<Map<String, dynamic>>?;

  /// 转换为AchievementUnlockEvent模型用于弹窗显示
  AchievementUnlockModel toUnlockModel() => AchievementUnlockModel(
        achievementId: achievementId,
        name: name,
        rarity: rarity,
        unlockedAt: unlockedAt,
        isFirst: isFirst,
        visualEffect: visualEffect,
        visualEffectType: visualEffectType,
        rewards: rewards,
      );
}

/// 成就解锁弹窗数据模型
class AchievementUnlockModel {
  AchievementUnlockModel({
    required this.achievementId,
    required this.name,
    required this.rarity,
    required this.unlockedAt,
    this.isFirst = false,
    this.visualEffect,
    this.visualEffectType,
    this.rewards,
  });

  final String achievementId;
  final String name;
  final AchievementRarity rarity;
  final DateTime unlockedAt;
  final bool isFirst;
  final Map<String, dynamic>? visualEffect;
  final VisualEffectType? visualEffectType;
  final List<Map<String, dynamic>>? rewards;
}

/// ============================================
/// Achievement Milestone Event
/// ============================================

/// 成就里程碑通知事件 - 当成就进度达到25%、50%、75%时触发
class AchievementMilestoneEvent extends ChatStreamEvent {
  AchievementMilestoneEvent({
    required this.milestoneData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> milestoneData;

  /// 成就ID
  String get achievementId => milestoneData['achievement_id'] as String? ?? '';

  /// 成就名称
  String get achievementName => milestoneData['achievement_name'] as String? ?? '';

  /// 里程碑百分比（25、50、75）
  int get milestonePercent => milestoneData['milestone_percent'] as int? ?? 0;

  /// 提示消息
  String get message => milestoneData['message'] as String? ?? '';

  /// 事件类型
  String get type => milestoneData['type'] as String? ?? 'progress_milestone';
}

// ============================================
// Transparency Events
// ============================================

/// 透明度步骤事件
class TransparencyStepEvent extends ChatStreamEvent {
  TransparencyStepEvent({
    required this.stepData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final Map<String, dynamic> stepData;

  /// 当前步骤索引 (1-based, from backend)
  int get currentStep => stepData['currentStep'] as int? ?? 0;

  /// 总步骤数
  int get totalSteps => stepData['totalSteps'] as int? ?? 0;

  /// 步骤数据
  Map<String, dynamic>? get step => stepData['step'] as Map<String, dynamic>?;

  /// 步骤名称 (从step中获取)
  String get stepName => step?['name'] as String? ?? '';

  /// 步骤索引 (0-based, for display)
  int get stepIndex => (currentStep > 0 ? currentStep - 1 : 0);
}

/// 透明度完整数据事件（流结束时）
class TransparencyCompleteEvent extends ChatStreamEvent {
  TransparencyCompleteEvent({
    required this.transparencyData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
  final TransparencyData? transparencyData;
}

/// 透明度数据模型
class TransparencyData {
  const TransparencyData({
    required this.steps,
    required this.totalDurationMs,
    required this.requestId,
    this.totalTokens = 0,
  });

  factory TransparencyData.fromJson(Map<String, dynamic> json) => TransparencyData(
      steps: (json['steps'] as List<dynamic>?)
              ?.map((e) => TransparencyStep.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      totalDurationMs: json['totalDurationMs'] as int? ?? 0,
      requestId: json['requestId'] as String? ?? '',
      totalTokens: json['totalTokens'] as int? ?? 0,
    );

  final List<TransparencyStep> steps;
  final int totalDurationMs;
  final String requestId;
  final int totalTokens;

  /// 格式化总耗时
  String get formattedTotalDuration {
    if (totalDurationMs < 1000) {
      return '${totalDurationMs}ms';
    }
    return '${(totalDurationMs / 1000).toStringAsFixed(1)}s';
  }
}

/// 透明度步骤模型（数据定义）
class TransparencyStep {
  const TransparencyStep({
    required this.stepId,
    required this.name,
    required this.status,
    this.durationMs,
    this.result,
    this.error,
    this.agentType,
    this.stepType,
    this.metadata,
  });

  factory TransparencyStep.fromJson(Map<String, dynamic> json) => TransparencyStep(
      stepId: json['stepId'] as String? ?? '',
      name: json['name'] as String? ?? '',
      status: json['status'] as String? ?? 'pending',
      durationMs: json['durationMs'] as int?,
      result: json['result'] as Map<String, dynamic>?,
      error: json['error'] as String?,
      agentType: json['agentType'] as String?,
      stepType: json['type'] as String?,
      metadata: json['metadata'] as Map<String, dynamic>?,
    );

  final String stepId;
  final String name;
  final String status; // pending, in_progress, completed, failed
  final int? durationMs;
  final Map<String, dynamic>? result;
  final String? error;
  final String? agentType;
  final String? stepType;
  final Map<String, dynamic>? metadata;

  /// 获取本地化状态标签
  String get statusLabel {
    switch (status) {
      case 'pending':
        return '等待中';
      case 'in_progress':
        return '进行中';
      case 'completed':
        return '已完成';
      case 'failed':
        return '失败';
      default:
        return status;
    }
  }

  /// 格式化耗时
  String? get formattedDuration {
    if (durationMs == null) return null;
    if (durationMs! < 1000) {
      return '${durationMs}ms';
    }
    return '${(durationMs! / 1000).toStringAsFixed(1)}s';
  }
}

/// ============================================
/// Multi-Agent Collaboration Events
/// ============================================

/// Multi-Agent Collaboration Timeline Event
/// Shows real-time collaboration between multiple AI agents
class CollaborationTimelineEvent extends ChatStreamEvent {
  CollaborationTimelineEvent({
    required this.collaborationData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> collaborationData;

  /// 工作流类型 (e.g., 'deep_analysis', 'study_plan', 'error_diagnosis')
  String get workflowType => collaborationData['workflow_type'] as String? ?? 'unknown';

  /// 总执行时间 (ms)
  int get executionTimeMs => collaborationData['execution_time_ms'] as int? ?? 0;

  /// 参与者数量
  int get participantCount => collaborationData['participant_count'] as int? ?? 0;

  /// 协作步骤列表
  List<CollaborationStep> get steps {
    final stepsList = collaborationData['steps'] as List<dynamic>?;
    return stepsList
            ?.map((e) => CollaborationStep.fromJson(e as Map<String, dynamic>))
            .toList() ??
        [];
  }

  /// 格式化执行时间
  String get formattedExecutionTime {
    if (executionTimeMs < 1000) {
      return '${executionTimeMs}ms';
    }
    return '${(executionTimeMs / 1000).toStringAsFixed(1)}s';
  }

  /// 转换为UI步骤列表
  List<TimelineStep> toTimelineSteps() {
    return steps.map((step) => TimelineStep(
      agentName: step.agentName,
      agentRole: step.agentRole,
      action: step.action,
      status: step.status,
      startTimeMs: step.startTimeMs,
      durationMs: step.durationMs,
      outputSummary: step.outputSummary,
      metadata: step.metadata,
    )).toList();
  }
}

/// 协作步骤数据模型
class CollaborationStep {
  const CollaborationStep({
    required this.agentName,
    required this.agentRole,
    required this.action,
    required this.status,
    required this.startTimeMs,
    this.durationMs,
    this.outputSummary,
    this.metadata,
  });

  factory CollaborationStep.fromJson(Map<String, dynamic> json) => CollaborationStep(
        agentName: json['agent_name'] as String? ?? 'Unknown',
        agentRole: json['agent_role'] as String? ?? 'Agent',
        action: json['action'] as String? ?? '',
        status: json['status'] as String? ?? 'pending',
        startTimeMs: json['start_time_ms'] as int? ?? 0,
        durationMs: json['duration_ms'] as int?,
        outputSummary: json['output_summary'] as String?,
        metadata: json['metadata'] as Map<String, dynamic>?,
      );

  final String agentName;
  final String agentRole;
  final String action;
  final String status; // pending, in_progress, completed, failed
  final int startTimeMs;
  final int? durationMs;
  final String? outputSummary;
  final Map<String, dynamic>? metadata;

  Map<String, dynamic> toJson() => {
        'agent_name': agentName,
        'agent_role': agentRole,
        'action': action,
        'status': status,
        'start_time_ms': startTimeMs,
        'duration_ms': durationMs,
        'output_summary': outputSummary,
        'metadata': metadata,
      };
}

/// UI步骤模型 (用于渲染)
class TimelineStep {
  const TimelineStep({
    required this.agentName,
    required this.agentRole,
    required this.action,
    required this.status,
    required this.startTimeMs,
    this.durationMs,
    this.outputSummary,
    this.metadata,
  });

  final String agentName;
  final String agentRole;
  final String action;
  final String status;
  final int startTimeMs;
  final int? durationMs;
  final String? outputSummary;
  final Map<String, dynamic>? metadata;

  /// 获取状态颜色
  String getStatusColor() {
    switch (status) {
      case 'completed':
        return '#66BB6A';
      case 'failed':
        return '#EF5350';
      case 'in_progress':
        return '#42A5F5';
      default:
        return '#BDBDBD';
    }
  }

  /// 获取本地化状态标签
  String getStatusLabel() {
    switch (status) {
      case 'completed':
        return '已完成';
      case 'failed':
        return '失败';
      case 'in_progress':
        return '进行中';
      case 'pending':
        return '等待中';
      default:
        return status;
    }
  }

  /// 格式化耗时
  String? get formattedDuration {
    if (durationMs == null) return null;
    if (durationMs! < 1000) {
      return '${durationMs}ms';
    }
    return '${(durationMs! / 1000).toStringAsFixed(1)}s';
  }
}
