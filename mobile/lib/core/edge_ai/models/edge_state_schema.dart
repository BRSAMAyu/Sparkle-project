import 'package:freezed_annotation/freezed_annotation.dart';

part 'edge_state_schema.freezed.dart';
part 'edge_state_schema.g.dart';

/// [RawStateVector] 是 LLM 的直接输出产物。
/// 核心策略：扁平化 + 整数化 + 强枚举。
/// 0.6B 小模型输出这种结构比输出复杂嵌套 JSON 稳定得多。
@freezed
class RawStateVector with _$RawStateVector {
  const factory RawStateVector({
    /// 注意力集中度 (0-100)
    @JsonKey(name: 'a') required int attention,

    /// 疲劳度 (0-100)
    @JsonKey(name: 'f') required int fatigue,

    /// 压力值 (0-100)
    @JsonKey(name: 's') required int stress,

    /// 拖延风险 (0-100)
    @JsonKey(name: 'p') required int procrastination,

    /// 推荐打断指数 (0-100, >60 建议打断)
    @JsonKey(name: 'i') required int interruptScore,

    /// 最佳介入时间窗口 (分钟, 0-120)
    @JsonKey(name: 'w') required int windowMinutes,

    /// 语气枚举 (0: gentle, 1: firm, 2: direct, 3: silent)
    @JsonKey(name: 't') required int toneEnum,
  }) = _RawStateVector;

  factory RawStateVector.fromJson(Map<String, dynamic> json) =>
      _$RawStateVectorFromJson(json);
}

/// [EdgeState] 是 App 消费的富状态对象。
/// 由 [RawStateVector] 经过确定性逻辑映射而来。
@freezed
class EdgeState with _$EdgeState {
  const factory EdgeState({
    required double attentionScore, // 0.0 - 1.0
    required double fatigueScore,   // 0.0 - 1.0
    required double stressScore,    // 0.0 - 1.0
    required bool shouldInterrupt,
    required String nudgeTone,      // 'gentle', 'firm', etc.
    required Duration bestWindow,
    required int timestamp,         // 生成时间
  }) = _EdgeState;

  factory EdgeState.fromJson(Map<String, dynamic> json) =>
      _$EdgeStateFromJson(json);
}

/// 确定性映射逻辑：将 Raw 向量转为 Rich State
extension StateMapper on RawStateVector {
  EdgeState toEdgeState() {
    return EdgeState(
      attentionScore: (attention / 100).clamp(0.0, 1.0),
      fatigueScore: (fatigue / 100).clamp(0.0, 1.0),
      stressScore: (stress / 100).clamp(0.0, 1.0),
      shouldInterrupt: interruptScore > 60, // 阈值由代码控制，方便热更
      nudgeTone: _mapTone(toneEnum),
      bestWindow: Duration(minutes: windowMinutes),
      timestamp: DateTime.now().millisecondsSinceEpoch ~/ 1000,
    );
  }

  String _mapTone(int tone) {
    switch (tone) {
      case 0: return 'gentle';
      case 1: return 'firm';
      case 2: return 'direct';
      case 3: return 'silent';
      default: return 'gentle'; // 兜底
    }
  }
}
