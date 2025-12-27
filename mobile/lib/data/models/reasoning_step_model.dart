import 'package:json_annotation/json_annotation.dart';

part 'reasoning_step_model.g.dart';

/// 步骤状态枚举
enum StepStatus {
  @JsonValue('pending')
  pending,

  @JsonValue('in_progress')
  inProgress,

  @JsonValue('completed')
  completed,

  @JsonValue('failed')
  failed,
}

/// 智能体类型枚举 (与protobuf AgentType保持同步)
enum AgentType {
  @JsonValue('orchestrator')
  orchestrator,  // 协调者

  @JsonValue('math')
  math,          // 数学专家

  @JsonValue('code')
  code,          // 代码专家

  @JsonValue('writing')
  writing,       // 写作专家

  @JsonValue('science')
  science,       // 科学专家（保留用于兼容性）

  @JsonValue('knowledge')
  knowledge,     // 知识检索专家

  @JsonValue('search')
  search,        // 搜索专家（保留用于兼容性）

  @JsonValue('data_analysis')
  dataAnalysis,  // 数据分析专家

  @JsonValue('translation')
  translation,   // 翻译专家

  @JsonValue('image')
  image,         // 图像处理专家

  @JsonValue('audio')
  audio,         // 音频处理专家

  @JsonValue('reasoning')
  reasoning,     // 逻辑推理专家
}

/// 推理步骤模型
///
/// 代表AI思考过程中的一个步骤，用于前端可视化展示
@JsonSerializable()
class ReasoningStep {
  /// 唯一标识符
  final String id;

  /// 步骤描述（简短）
  final String description;

  /// 执行此步骤的智能体类型
  final AgentType agent;

  /// 步骤当前状态
  final StepStatus status;

  /// 工具执行结果（JSON字符串或代码片段）
  final String? toolOutput;

  /// GraphRAG引用的知识节点ID列表
  final List<String>? citations;

  /// 步骤创建时间
  @JsonKey(name: 'created_at')
  final DateTime? createdAt;

  /// 步骤完成时间
  @JsonKey(name: 'completed_at')
  final DateTime? completedAt;

  /// 额外元数据
  final Map<String, dynamic>? metadata;

  const ReasoningStep({
    required this.id,
    required this.description,
    required this.agent,
    required this.status,
    this.toolOutput,
    this.citations,
    this.createdAt,
    this.completedAt,
    this.metadata,
  });

  /// 计算步骤耗时（毫秒）
  int? get durationMs {
    if (createdAt != null && completedAt != null) {
      return completedAt!.difference(createdAt!).inMilliseconds;
    }
    return null;
  }

  /// 是否已完成
  bool get isCompleted => status == StepStatus.completed;

  /// 是否失败
  bool get isFailed => status == StepStatus.failed;

  /// 是否正在进行中
  bool get isInProgress => status == StepStatus.inProgress;

  factory ReasoningStep.fromJson(Map<String, dynamic> json) =>
      _$ReasoningStepFromJson(json);

  Map<String, dynamic> toJson() => _$ReasoningStepToJson(this);

  ReasoningStep copyWith({
    String? id,
    String? description,
    AgentType? agent,
    StepStatus? status,
    String? toolOutput,
    List<String>? citations,
    DateTime? createdAt,
    DateTime? completedAt,
    Map<String, dynamic>? metadata,
  }) {
    return ReasoningStep(
      id: id ?? this.id,
      description: description ?? this.description,
      agent: agent ?? this.agent,
      status: status ?? this.status,
      toolOutput: toolOutput ?? this.toolOutput,
      citations: citations ?? this.citations,
      createdAt: createdAt ?? this.createdAt,
      completedAt: completedAt ?? this.completedAt,
      metadata: metadata ?? this.metadata,
    );
  }

  @override
  String toString() {
    return 'ReasoningStep(id: $id, agent: $agent, status: $status, desc: $description)';
  }
}

/// 智能体贡献信息（用于多智能体协作展示）
class AgentContribution {
  final String agentName;
  final AgentType agentType;
  final String reasoning;
  final String responseText;
  final double? confidence;
  final List<String>? citations;

  AgentContribution({
    required this.agentName,
    required this.agentType,
    required this.reasoning,
    required this.responseText,
    this.confidence,
    this.citations,
  });
}
