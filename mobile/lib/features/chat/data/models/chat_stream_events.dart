import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:sparkle/core/models/intervention.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// 聊天流事件基类
abstract class ChatStreamEvent {
  const ChatStreamEvent({
    this.responseId,
    this.traceId,
    this.workflowId,
    this.promptVersion,
    this.metadata,
    this.sessionId,
  });

  final String? responseId;
  final String? traceId;
  final String? workflowId;
  final String? promptVersion;
  final Map<String, dynamic>? metadata;
  final String? sessionId;
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
class ContinueEvent extends ChatStreamEvent {
  ContinueEvent({
    this.finishReason,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
    super.metadata,
    super.sessionId,
  });
  final String? finishReason;
}

/// 完成事件
class DoneEvent extends ChatStreamEvent {
  DoneEvent({
    this.finishReason,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
    super.metadata,
    super.sessionId,
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
    super.metadata,
    super.sessionId,
  });
  final Map<String, dynamic> data;
}

class MetaEvent extends ChatStreamEvent {
  const MetaEvent({
    required this.meta,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
    super.sessionId,
  }) : super(metadata: meta);

  final Map<String, dynamic> meta;
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
    super.metadata,
  });
  final String state;
  final String details;
  final String? currentAgentName;
  final String? activeAgentType;
}

/// DAG execution signal payload embedded in metadata['dag_execution_event'].
class DagExecutionSignal {
  DagExecutionSignal({
    required this.event,
    this.layerIndex,
    this.layerNumber,
    this.totalLayers,
    this.stepId,
    this.toolName,
    this.success,
    this.durationMs,
    this.aborted,
    this.reason,
    this.completedSteps,
    this.stepIds,
    this.toolNames,
    this.planId,
    this.layersCompleted,
    this.stepsTotal,
    this.abortReason,
  });

  final String event;
  final int? layerIndex;
  final int? layerNumber;
  final int? totalLayers;
  final String? stepId;
  final String? toolName;
  final bool? success;
  final int? durationMs;
  final bool? aborted;
  final String? reason;
  final int? completedSteps;
  final List<String>? stepIds;
  final List<String>? toolNames;
  final String? planId;
  final int? layersCompleted;
  final int? stepsTotal;
  final String? abortReason;

  static DagExecutionSignal? fromDynamic(dynamic raw) {
    Map<String, dynamic>? data;
    if (raw is String && raw.isNotEmpty) {
      try {
        final decoded = json.decode(raw);
        if (decoded is Map<String, dynamic>) {
          data = decoded;
        }
      } catch (error, stackTrace) {
        debugPrint(
          'DagExecutionSignal.fromDynamic failed to decode payload: $error',
        );
        debugPrintStack(stackTrace: stackTrace);
      }
    } else if (raw is Map<String, dynamic>) {
      data = raw;
    }

    if (data == null) {
      return null;
    }

    final event = data['event'] as String?;
    if (event == null || event.isEmpty) {
      return null;
    }
    final payload = data;

    int? asInt(String camel, String snake) =>
        (payload[camel] ?? payload[snake]) as int?;
    String? asString(String camel, String snake) =>
        (payload[camel] ?? payload[snake]) as String?;
    List<String>? asStringList(String camel, String snake) =>
        ((payload[camel] ?? payload[snake]) as List<dynamic>?)
            ?.map((e) => e.toString())
            .toList();

    return DagExecutionSignal(
      event: event,
      layerIndex: asInt('layerIndex', 'layer_index'),
      layerNumber: asInt('layerNumber', 'layer_number'),
      totalLayers: asInt('totalLayers', 'total_layers'),
      stepId: asString('stepId', 'step_id'),
      toolName: asString('toolName', 'tool_name'),
      success: data['success'] as bool?,
      durationMs: asInt('durationMs', 'duration_ms'),
      aborted: data['aborted'] as bool?,
      reason: data['reason'] as String?,
      completedSteps: asInt('completedSteps', 'completed_steps'),
      stepIds: asStringList('stepIds', 'step_ids'),
      toolNames: asStringList('toolNames', 'tool_names'),
      planId: asString('planId', 'plan_id'),
      layersCompleted: asInt('layersCompleted', 'layers_completed'),
      stepsTotal: asInt('stepsTotal', 'steps_total'),
      abortReason: asString('abortReason', 'abort_reason'),
    );
  }

  String? get statusDetails {
    final l10n = I18nService.instance.l10n;
    switch (event) {
      case 'layer_start':
        final layer = layerNumber ?? 0;
        final total = totalLayers ?? 0;
        final count = toolNames?.length ?? stepIds?.length ?? 0;
        return l10n.chatDagLayerStart(layer, total, count);
      case 'step_completed':
        final name = toolName ?? l10n.chatDagStepFallback;
        if (success == false) {
          return l10n.chatDagStepFailed(name);
        }
        if (durationMs != null) {
          return l10n.chatDagStepCompletedWithDuration(name, durationMs!);
        }
        return l10n.chatDagStepCompleted(name);
      case 'layer_end':
        final layer = layerNumber ?? 0;
        if (aborted ?? false) {
          return l10n.chatDagLayerAborted(layer);
        }
        return l10n.chatDagLayerCompleted(layer);
      case 'execution_aborted':
        return reason ?? l10n.chatDagExecutionAbortedDefault;
      case 'execution_end':
        if (aborted ?? false) {
          return abortReason ?? l10n.chatDagExecutionEndAbortedDefault;
        }
        return l10n.chatDagExecutionCompleted;
      default:
        return null;
    }
  }
}

class DagExecutionEvent extends ChatStreamEvent {
  DagExecutionEvent({
    required this.signal,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
    super.metadata,
  });

  final DagExecutionSignal signal;
}

/// 完整文本事件
class FullTextEvent extends ChatStreamEvent {
  FullTextEvent({
    required this.content,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
    super.metadata,
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

/// ACK确认事件 - 服务端确认收到消息
class AckEvent extends ChatStreamEvent {
  AckEvent({
    required this.messageId,
    required this.status,
    required this.timestamp,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final String messageId;
  final String status; // received, processing, failed
  final int timestamp;

  bool get isReceived => status == 'received';
  bool get isProcessing => status == 'processing';
  bool get isFailed => status == 'failed';
}

/// NACK否定确认事件 - 服务端拒绝消息
class NackEvent extends ChatStreamEvent {
  NackEvent({
    required this.messageId,
    required this.errorCode,
    required this.errorMessage,
    this.retryAfterMs,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final String messageId;
  final String errorCode;
  final String errorMessage;
  final int? retryAfterMs;

  bool get canRetry => retryAfterMs != null;
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
  final String
      status; // 'approved', 'rejected', 'modify_requested', 'acknowledged'
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
  String get interventionLevel =>
      changeData['intervention_level'] as String? ?? 'toast';

  /// Priority: low, medium, high
  String get priority => changeData['priority'] as String? ?? 'low';

  /// Pre-formatted user-friendly message
  String get formattedMessage =>
      changeData['formatted_message'] as String? ?? '';

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
  double get spaceFreedMb =>
      (changeData['space_freed_mb'] as num?)?.toDouble() ?? 0.0;

  /// Convert to InterventionPushMessage for display
  InterventionPushMessage toInterventionMessage() => InterventionPushMessage(
        interventionId: changeId,
        level: _mapInterventionLevel(),
        content: InterventionContent(
          renderedMessage: formattedMessage,
          intentType: changeType,
          templateId: 'state_change_$changeType',
          scaffoldingLevel: 0,
          srlPhaseHint: '',
          srlPhaseMessage: '',
          reflectionPromptStyle: '',
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
    final l10n = I18nService.instance.l10n;
    // For plan changes, offer to view the plan
    if (planId != null && changeType.startsWith('plan_')) {
      return [
        InterventionAction(
          id: 'view_plan',
          label: l10n.chatInterventionViewPlan,
          type: 'navigation',
        ),
      ];
    }

    // For settings changes, offer to view settings
    if (changeType == 'user_settings_updated') {
      return [
        InterventionAction(
          id: 'view_settings',
          label: l10n.chatInterventionViewSettings,
          type: 'navigation',
        ),
      ];
    }

    // Default: just acknowledge
    return [
      InterventionAction(
        id: 'acknowledge',
        label: l10n.commonOk,
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
  String get decision =>
      reviewData['decision'] as String? ?? 'needs_refinement';

  /// 总体评分 0-1
  double get overallScore =>
      (reviewData['overall_score'] as num?)?.toDouble() ?? 0.0;

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
  bool get requiresReflection =>
      reviewData['requires_reflection'] as bool? ?? false;
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
  double get scoreDelta =>
      (reflectionData['score_delta'] as num?)?.toDouble() ?? 0.0;

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
  String get originalDecision =>
      overrideData['original_decision'] as String? ?? '';

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
  double? get secondaryScore =>
      (resultData['secondary_score'] as num?)?.toDouble();

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
  String get achievementId =>
      achievementData['achievement_id'] as String? ?? '';

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

  List<String> get rewardPreview =>
      (achievementData['reward_preview'] as List<dynamic>?)
          ?.map((e) => '$e')
          .toList() ??
      const [];

  List<String> get surfacePreview =>
      (achievementData['surface_preview'] as List<dynamic>?)
          ?.map((e) => '$e')
          .toList() ??
      const [];

  List<String> get gloryLines =>
      (achievementData['glory_lines'] as List<dynamic>?)
          ?.map((e) => '$e')
          .toList() ??
      const [];

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
        rewardPreview: rewardPreview,
        surfacePreview: surfacePreview,
        gloryLines: gloryLines,
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
    this.rewardPreview = const [],
    this.surfacePreview = const [],
    this.gloryLines = const [],
  });

  final String achievementId;
  final String name;
  final AchievementRarity rarity;
  final DateTime unlockedAt;
  final bool isFirst;
  final Map<String, dynamic>? visualEffect;
  final VisualEffectType? visualEffectType;
  final List<Map<String, dynamic>>? rewards;
  final List<String> rewardPreview;
  final List<String> surfacePreview;
  final List<String> gloryLines;
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
  String get achievementName =>
      milestoneData['achievement_name'] as String? ?? '';

  /// 里程碑百分比（25、50、75）
  int get milestonePercent => milestoneData['milestone_percent'] as int? ?? 0;

  /// 提示消息
  String get message => milestoneData['message'] as String? ?? '';

  /// 事件类型
  String get type => milestoneData['type'] as String? ?? 'progress_milestone';
}

/// ============================================
/// Notification Event (Real-time Push)
/// ============================================

/// Notification Event - 用于实时推送新通知
/// 支持系统通知和干预通知的实时推送
class NotificationEvent extends ChatStreamEvent {
  NotificationEvent({
    required this.notificationData,
    required this.notificationType,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  /// 工厂方法：从 JSON 创建
  factory NotificationEvent.fromJson(Map<String, dynamic> json) {
    final rawNotification =
        json['notification'] ?? json['data'] ?? <String, dynamic>{};
    final notificationData = rawNotification is Map<String, dynamic>
        ? rawNotification
        : rawNotification is Map
            ? Map<String, dynamic>.from(rawNotification)
            : <String, dynamic>{};
    return NotificationEvent(
      notificationData: notificationData,
      notificationType: json['notification_type'] as String? ?? 'system',
      responseId: json['response_id'] as String?,
      traceId: json['trace_id'] as String?,
      workflowId: json['workflow_id'] as String?,
      promptVersion: json['prompt_version'] as String?,
    );
  }

  /// 通知数据
  final Map<String, dynamic> notificationData;

  /// 通知类型: 'system' | 'intervention'
  final String notificationType;

  /// 通知 ID
  String get notificationId =>
      notificationData['id'] as String? ??
      notificationData['notification_id'] as String? ??
      '';

  /// 通知标题
  String get title => notificationData['title'] as String? ?? '';

  /// 通知内容
  String get content => notificationData['content'] as String? ?? '';

  /// 通知类型字段（task_reminder, achievement, system 等）
  String get type =>
      notificationData['type'] as String? ??
      notificationData['notification_type'] as String? ??
      'system';

  /// 是否已读
  bool get isRead => notificationData['is_read'] as bool? ?? false;

  /// 创建时间
  String get createdAt => notificationData['created_at'] as String? ?? '';

  /// 优先级
  String get priority => notificationData['priority'] as String? ?? 'normal';

  /// 附加数据
  Map<String, dynamic> get data =>
      notificationData['data'] as Map<String, dynamic>? ?? const {};

  /// 获取完整的通知数据（用于传递给通知中心）
  Map<String, dynamic> get fullNotificationData => {
        'id': notificationId,
        'title': title,
        'content': content,
        'type': type,
        'is_read': isRead,
        'created_at': createdAt,
        'priority': priority,
        'data': data,
        'metadata': data,
        ...notificationData,
      };
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

// ============================================
// Orchestration Trace Events
// ============================================

class OrchestrationTraceEvent extends ChatStreamEvent {
  OrchestrationTraceEvent({
    required this.traceData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> traceData;

  List<OrchestrationTraceStep> get steps =>
      (traceData['steps'] as List<dynamic>?)
          ?.whereType<Map<String, dynamic>>()
          .map(OrchestrationTraceStep.fromJson)
          .toList() ??
      [];

  String get mode => traceData['mode'] as String? ?? '';
  List<String> get agents =>
      (traceData['agents'] as List<dynamic>?)
          ?.map((e) => e.toString())
          .toList() ??
      [];
}

class OrchestrationTraceStep {
  const OrchestrationTraceStep({
    required this.stepId,
    required this.label,
    required this.decision,
    required this.reason,
    this.confidence,
    this.metadata,
    this.durationMs,
  });

  factory OrchestrationTraceStep.fromJson(Map<String, dynamic> json) =>
      OrchestrationTraceStep(
        stepId: json['step_id'] as String? ?? '',
        label: json['label'] as String? ?? '',
        decision: json['decision'] as String? ?? '',
        reason: json['reason'] as String? ?? '',
        confidence: (json['confidence'] as num?)?.toDouble(),
        metadata: json['metadata'] as Map<String, dynamic>?,
        durationMs: (json['duration_ms'] as num?)?.toDouble(),
      );

  final String stepId;
  final String label;
  final String decision;
  final String reason;
  final double? confidence;
  final Map<String, dynamic>? metadata;
  final double? durationMs;
}

// ============================================
// Run Ledger Events
// ============================================

class RunLedgerSnapshotEvent extends ChatStreamEvent {
  RunLedgerSnapshotEvent({
    required this.summary,
    this.latestEvent,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final RunLedgerSummary summary;
  final RunLedgerEvent? latestEvent;
}

class RunLedgerSummary {
  const RunLedgerSummary({
    required this.traceId,
    required this.status,
    required this.route,
    required this.models,
    required this.agents,
    required this.quality,
    required this.evidence,
    required this.response,
    required this.feedback,
    required this.timeline,
    required this.eventCount,
    this.workflowId = '',
    this.promptVersion = '',
  });

  factory RunLedgerSummary.fromJson(Map<String, dynamic> json) =>
      RunLedgerSummary(
        traceId: json['trace_id'] as String? ?? '',
        workflowId: json['workflow_id'] as String? ?? '',
        promptVersion: json['prompt_version'] as String? ?? '',
        status: json['status'] as String? ?? 'running',
        route: (json['route'] as Map?)?.cast<String, dynamic>() ??
            const <String, dynamic>{},
        models: ((json['models'] as List<dynamic>?) ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList(),
        agents: ((json['agents'] as List<dynamic>?) ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList(),
        quality: (json['quality'] as Map?)?.cast<String, dynamic>() ??
            const <String, dynamic>{},
        evidence: (json['evidence'] as Map?)?.cast<String, dynamic>() ??
            const <String, dynamic>{},
        response: (json['response'] as Map?)?.cast<String, dynamic>() ??
            const <String, dynamic>{},
        feedback: (json['feedback'] as Map?)?.cast<String, dynamic>() ??
            const <String, dynamic>{},
        timeline: ((json['timeline'] as List<dynamic>?) ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList(),
        eventCount: json['event_count'] as int? ?? 0,
      );

  final String traceId;
  final String workflowId;
  final String promptVersion;
  final String status;
  final Map<String, dynamic> route;
  final List<Map<String, dynamic>> models;
  final List<Map<String, dynamic>> agents;
  final Map<String, dynamic> quality;
  final Map<String, dynamic> evidence;
  final Map<String, dynamic> response;
  final Map<String, dynamic> feedback;
  final List<Map<String, dynamic>> timeline;
  final int eventCount;

  String get executionMode => route['execution_mode'] as String? ?? '';
  String get routeReason => route['reason'] as String? ?? '';
  double? get reviewScore => (quality['review_score'] as num?)?.toDouble();
  double get reflectionDelta =>
      (quality['reflection_delta'] as num?)?.toDouble() ?? 0.0;
  bool get reflectionCompleted => quality['reflection_completed'] == true;
  int get totalTokens => response['total_tokens'] as int? ?? 0;
  double get estimatedCostUsd =>
      (response['estimated_cost_usd'] as num?)?.toDouble() ?? 0.0;
}

class RunLedgerEvent {
  const RunLedgerEvent({
    required this.eventType,
    required this.label,
    required this.workflowStage,
    required this.status,
    required this.timestamp,
    required this.metadata,
  });

  factory RunLedgerEvent.fromJson(Map<String, dynamic> json) => RunLedgerEvent(
        eventType: json['event_type'] as String? ?? '',
        label: json['label'] as String? ?? '',
        workflowStage: json['workflow_stage'] as String? ?? '',
        status: json['status'] as String? ?? '',
        timestamp: json['timestamp'] as String? ?? '',
        metadata: (json['metadata'] as Map?)?.cast<String, dynamic>() ??
            const <String, dynamic>{},
      );

  final String eventType;
  final String label;
  final String workflowStage;
  final String status;
  final String timestamp;
  final Map<String, dynamic> metadata;
}

// ============================================
// Mode Suggestion Events
// ============================================

class ModeSuggestionEvent extends ChatStreamEvent {
  ModeSuggestionEvent({
    required this.suggestion,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> suggestion;

  String get suggestedMode => suggestion['suggested_mode'] as String? ?? '';
  String get reason => suggestion['reason'] as String? ?? '';
  double get confidence =>
      (suggestion['confidence'] as num?)?.toDouble() ?? 0.0;
}

class RoutingPreviewEvent extends ChatStreamEvent {
  RoutingPreviewEvent({
    required this.preview,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> preview;
}

class AgentTurnEvent extends ChatStreamEvent {
  AgentTurnEvent({
    required this.turn,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> turn;
}

// ============================================
// Agent Activity Events
// ============================================

class AgentActivityEvent extends ChatStreamEvent {
  AgentActivityEvent({
    required this.agentId,
    required this.status,
    required this.displayName,
    required this.icon,
    required this.color,
    required this.description,
    this.durationMs,
    this.resultSummary,
    this.collaborationMode,
    this.phase,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  factory AgentActivityEvent.fromJson(Map<String, dynamic> json) {
    final rawMeta = json['metadata'];
    final metadata = rawMeta is Map<String, dynamic>
        ? rawMeta
        : rawMeta is Map
            ? Map<String, dynamic>.from(rawMeta)
            : const <String, dynamic>{};
    return AgentActivityEvent(
      agentId: json['agent_id'] as String? ?? '',
      status: json['status'] as String? ?? 'pending',
      displayName:
          json['display_name'] as String? ?? json['agent_id'] as String? ?? '',
      icon: json['icon'] as String? ?? 'bot',
      color: json['color'] as String? ?? '#636E72',
      description: json['description'] as String? ?? '',
      durationMs: (json['duration_ms'] as num?)?.toDouble(),
      resultSummary: json['result_summary'] as String?,
      collaborationMode: metadata['collaboration_mode']?.toString() ??
          json['collaboration_mode'] as String?,
      phase: metadata['phase']?.toString() ?? json['phase'] as String?,
    );
  }

  final String agentId;
  final String status;
  final String displayName;
  final String icon;
  final String color;
  final String description;
  final double? durationMs;
  final String? resultSummary;
  final String? collaborationMode;
  final String? phase;
}

/// 透明度数据模型
class TransparencyData {
  const TransparencyData({
    required this.steps,
    required this.totalDurationMs,
    required this.requestId,
    this.totalTokens = 0,
  });

  factory TransparencyData.fromJson(Map<String, dynamic> json) =>
      TransparencyData(
        steps: (json['steps'] as List<dynamic>?)
                ?.map(
                  (e) => TransparencyStep.fromJson(e as Map<String, dynamic>),
                )
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

  factory TransparencyStep.fromJson(Map<String, dynamic> json) =>
      TransparencyStep(
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
    final l10n = I18nService.instance.l10n;
    switch (status) {
      case 'pending':
        return l10n.statusPending;
      case 'in_progress':
        return l10n.statusInProgress;
      case 'completed':
        return l10n.statusCompleted;
      case 'failed':
        return l10n.statusFailed;
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
  String get workflowType =>
      collaborationData['workflow_type'] as String? ?? 'unknown';

  /// 总执行时间 (ms)
  int get executionTimeMs =>
      collaborationData['execution_time_ms'] as int? ?? 0;

  /// 参与者数量
  int get participantCount =>
      collaborationData['participant_count'] as int? ?? 0;

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
  List<TimelineStep> toTimelineSteps() => steps
      .map(
        (step) => TimelineStep(
          agentName: step.agentName,
          agentRole: step.agentRole,
          action: step.action,
          status: step.status,
          startTimeMs: step.startTimeMs,
          durationMs: step.durationMs,
          outputSummary: step.outputSummary,
          metadata: step.metadata,
        ),
      )
      .toList();
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

  factory CollaborationStep.fromJson(Map<String, dynamic> json) =>
      CollaborationStep(
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
    final l10n = I18nService.instance.l10n;
    switch (status) {
      case 'completed':
        return l10n.statusCompleted;
      case 'failed':
        return l10n.statusFailed;
      case 'in_progress':
        return l10n.statusInProgress;
      case 'pending':
        return l10n.statusPending;
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

// ============================================
// Spine Directive UI Events
// ============================================

/// Time-Aware Recovery Card Event
/// Emitted when StaleStateGuard detects user return after >60 min absence.
/// Backend key: response_metadata['spine_stale_card']
class StaleRecoveryEvent extends ChatStreamEvent {
  StaleRecoveryEvent({
    required this.staleData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> staleData;

  int get elapsedMinutes =>
      staleData['elapsed_since_last_seen_min'] as int? ?? 0;

  String get pendingTaskStatus =>
      staleData['pending_task_status'] as String? ?? 'unknown';

  List<String> get resumeOptions {
    final raw = staleData['resume_options'];
    if (raw is List) return raw.map((e) => e.toString()).toList();
    return [S.chatCompleted, S.chatStreamStuck, S.chatStreamNotStarted, S.chatStreamSwitchTask];
  }

  String get formattedElapsed {
    if (elapsedMinutes < 60) return '$elapsedMinutes 分钟';
    final hours = elapsedMinutes ~/ 60;
    final mins = elapsedMinutes % 60;
    return mins > 0 ? '$hours 小时 $mins 分钟' : '$hours 小时';
  }
}

/// UX Risk Warning Event — divine moment #5 "阻止低收益"
/// Proactive intervention when Aurora detects a risk in the user's current path.
/// Backend key: response_metadata['spine_ux_warning']
class UXWarningEvent extends ChatStreamEvent {
  UXWarningEvent({
    required this.warningData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> warningData;

  String get label => warningData['label'] as String? ?? S.chatStreamStrategyRisk;
  String get reason => warningData['reason'] as String? ?? '';
  String get suggestedAction =>
      warningData['suggested_action'] as String? ?? S.chatStreamAdjustStrategy;
  String get riskLevel => warningData['risk_level'] as String? ?? 'medium';
  List<String> get predictedReplyOptions {
    final raw = warningData['predicted_reply_options'];
    if (raw is List) return raw.map((e) => e.toString()).toList();
    return [];
  }
}

/// Community Insight Event — divine moment #6 "社群经验转策略"
/// Emitted when backend returns a privacy-safe community hint in metadata.
/// Backend key: response_metadata['spine_community_hint']
class CommunityHintEvent extends ChatStreamEvent {
  CommunityHintEvent({
    required this.hintData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> hintData;

  String get hintType => hintData['hint_type'] as String? ?? 'cohort_mistake';
  String get title => hintData['title'] as String? ?? S.chatStreamCommunityInsight;
  String get anonymousSummary => hintData['anonymous_summary'] as String? ?? '';
  String get tip => hintData['tip'] as String? ?? '';

  List<String> get affectedNodes {
    final raw = hintData['affected_nodes'];
    if (raw is List) return raw.map((e) => e.toString()).toList();
    return [];
  }
}

/// Spine Receipt Event
/// Emitted when orchestrator returns a UserVisibleReceipt in metadata.
/// Backend key: response_metadata['spine_receipt']
class SpineReceiptEvent extends ChatStreamEvent {
  SpineReceiptEvent({
    required this.receiptData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> receiptData;

  String get receiptId => receiptData['receipt_id'] as String? ?? '';
  String get trigger => receiptData['trigger'] as String? ?? '';
  String get summary => receiptData['summary'] as String? ?? '';
  bool get correctable => receiptData['correctable'] as bool? ?? false;
  List<String> get correctionOptions {
    final raw = receiptData['correction_options'];
    if (raw is List) return raw.map((e) => e.toString()).toList();
    return [];
  }
}

/// Growth Card Event — divine moment #1 "看见坚持"
/// Emitted when backend detects a significant streak or growth milestone.
/// Backend key: response_metadata['spine_growth_card']
class GrowthCardEvent extends ChatStreamEvent {
  GrowthCardEvent({
    required this.cardData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> cardData;

  String get title => cardData['title'] as String? ?? S.chatStreamSeePersistence;
  String get narrative => cardData['narrative'] as String? ?? '';
  int get streakDays => cardData['streak_days'] as int? ?? 0;
  String get strategyEffect => cardData['strategy_effect'] as String? ?? '';
  bool get isMilestone => cardData['is_milestone'] as bool? ?? false;

  List<String> get actions {
    final raw = cardData['actions'];
    if (raw is List) return raw.map((e) => e.toString()).toList();
    return ['收到', S.chatStreamReallyTired];
  }
}

/// Goal Arbitration Event — multi-goal conflict surface
/// Emitted when Aurora detects ≥2 active goals with priority tension.
/// Backend key: response_metadata['spine_goal_arbitration']
class GoalArbitrationEvent extends ChatStreamEvent {
  GoalArbitrationEvent({
    required this.arbData,
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });

  final Map<String, dynamic> arbData;

  String get primaryGoalId =>
      arbData['primary_goal_id'] as String? ?? '';

  String get primaryGoalTitle =>
      arbData['primary_goal_title'] as String? ?? '';

  String get reason => arbData['reason'] as String? ?? '';

  List<Map<String, dynamic>> get goals {
    final raw = arbData['goals'];
    if (raw is List) {
      return raw
          .whereType<Map<dynamic, dynamic>>()
          .map(Map<String, dynamic>.from)
          .toList();
    }
    return [];
  }

  List<String> get conflicts {
    final raw = arbData['conflicts'];
    if (raw is List) return raw.map((e) => e.toString()).toList();
    return [];
  }
}

/// Spine Degraded Event — STAB-012 graceful degradation indicator.
/// Emitted when the Spine pipeline fails and falls back to safe defaults.
/// Backend key: response_metadata['spine_degraded']
class SpineDegradedEvent extends ChatStreamEvent {
  SpineDegradedEvent({
    super.responseId,
    super.traceId,
    super.workflowId,
    super.promptVersion,
  });
}
