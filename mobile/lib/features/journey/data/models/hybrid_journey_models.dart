import 'package:flutter/foundation.dart';
import 'package:sparkle/core/services/agent_run_read_service.dart';

/// J-06 · Hybrid Flagship Journey 数据模型（四段链的移动端投影）.
///
/// 真源对齐（不重建）：旅程脊柱与 handoff 权威在引擎
/// `app.services.hybrid_journey_service` + X-07 `agent_runs`；本文件只解析
/// wire 投影。awaiting step 复用 X-07 统一读面 [AgentRunAwaitingStep]——
/// 「轮到谁」与恢复点从同一投影推导，零第二交接面。
@immutable
class HybridJourneyCitation {
  const HybridJourneyCitation({
    required this.citationId,
    required this.scheme,
    required this.ref,
    required this.sourceRef,
    required this.fileName,
    required this.snippet,
    this.fileId,
    this.pageNumbers = const <int>[],
    this.score,
  });

  factory HybridJourneyCitation.fromJson(Map<String, dynamic> json) =>
      HybridJourneyCitation(
        citationId: (json['citation_id'] ?? '').toString(),
        scheme: (json['scheme'] ?? '').toString(),
        ref: (json['ref'] ?? '').toString(),
        sourceRef: (json['source_ref'] ?? '').toString(),
        fileId: json['file_id']?.toString(),
        fileName: (json['file_name'] ?? '').toString(),
        pageNumbers: (json['page_numbers'] as List? ?? const <dynamic>[])
            .whereType<num>()
            .map((e) => e.toInt())
            .toList(),
        score: json['score'] is num ? (json['score'] as num).toDouble() : null,
        snippet: (json['snippet'] ?? '').toString(),
      );

  final String citationId;
  final String scheme;

  /// 真实 chunk 行 id（材料本体真源 = document_chunks，非复制内容）。
  final String ref;

  /// `document_chunk://<chunk_id>`（每段产物可溯源的统一引用面）。
  final String sourceRef;
  final String? fileId;
  final String fileName;
  final List<int> pageNumbers;
  final double? score;
  final String snippet;

  String get pageLabel =>
      pageNumbers.isEmpty ? '' : pageNumbers.join('/');
}

/// 判断段说明：显式回答「为什么这一步需要你来决定」（卡魂）.
@immutable
class HybridJudgmentBrief {
  const HybridJudgmentBrief({
    required this.whyHumanKey,
    required this.whyHuman,
    required this.options,
  });

  factory HybridJudgmentBrief.fromJson(Map<String, dynamic> json) =>
      HybridJudgmentBrief(
        whyHumanKey: (json['why_human_key'] ?? '').toString(),
        whyHuman: (json['why_human'] ?? '').toString(),
        options: (json['options'] as List? ?? const <dynamic>[])
            .whereType<Map<dynamic, dynamic>>()
            .map((e) => HybridJourneyCitation.fromJson(
                  Map<String, dynamic>.from(e),
                ),)
            .toList(),
      );

  final String whyHumanKey;

  /// 服务端单一说明句（l10n 键的回退兜底；展示以 l10n 优先）。
  final String whyHuman;
  final List<HybridJourneyCitation> options;
}

/// 分段产物行（每段产物带统一 citation 结构）.
@immutable
class HybridJourneyArtifactView {
  const HybridJourneyArtifactView({
    required this.id,
    required this.stage,
    required this.artifactKind,
    required this.citations,
    required this.payload,
  });

  factory HybridJourneyArtifactView.fromJson(Map<String, dynamic> json) =>
      HybridJourneyArtifactView(
        id: (json['id'] ?? '').toString(),
        stage: (json['stage'] ?? '').toString(),
        artifactKind: (json['artifact_kind'] ?? '').toString(),
        citations: (json['citations'] as List? ?? const <dynamic>[])
            .whereType<Map<dynamic, dynamic>>()
            .map((e) => HybridJourneyCitation.fromJson(
                  Map<String, dynamic>.from(e),
                ),)
            .toList(),
        payload: json['payload'] is Map
            ? Map<String, dynamic>.from(json['payload'] as Map)
            : const <String, dynamic>{},
      );

  final String id;
  final String stage;
  final String artifactKind;
  final List<HybridJourneyCitation> citations;
  final Map<String, dynamic> payload;

  bool get checkPassed =>
      payload['check'] is Map &&
      (payload['check'] as Map)['passed'] == true;
}

/// `/journey/hybrid` 的旅程投影（四段链 + awaiting step + 判断面）.
@immutable
class HybridJourneyPayload {
  const HybridJourneyPayload({
    required this.runId,
    required this.runStatus,
    required this.artifacts,
    this.version = '',
    this.goalTitle = '',
    this.taskId,
    this.taskTitle = '',
    this.citations = const <HybridJourneyCitation>[],
    this.judgmentBrief,
    this.awaitingStep,
    this.steps = const <AgentRunStepView>[],
  });

  factory HybridJourneyPayload.fromJson(Map<String, dynamic> json) {
    final run = json['run'] is Map
        ? Map<String, dynamic>.from(json['run'] as Map)
        : const <String, dynamic>{};
    final goal = json['goal'] is Map
        ? Map<String, dynamic>.from(json['goal'] as Map)
        : const <String, dynamic>{};
    final task = json['task'] is Map
        ? Map<String, dynamic>.from(json['task'] as Map)
        : const <String, dynamic>{};
    final brief = json['judgment_brief'] is Map
        ? HybridJudgmentBrief.fromJson(
            Map<String, dynamic>.from(json['judgment_brief'] as Map),
          )
        : null;
    final awaiting = run['awaiting_step'] is Map
        ? AgentRunAwaitingStep.fromJson(
            Map<String, dynamic>.from(run['awaiting_step'] as Map),
          )
        : null;
    return HybridJourneyPayload(
      version: (json['version'] ?? '').toString(),
      runId: (run['run_id'] ?? '').toString(),
      runStatus: (run['status'] ?? '').toString(),
      goalTitle: (goal['title'] ?? '').toString(),
      taskId: task['id']?.toString(),
      taskTitle: (task['title'] ?? '').toString(),
      citations: (json['citations'] as List? ?? const <dynamic>[])
          .whereType<Map<dynamic, dynamic>>()
          .map((e) => HybridJourneyCitation.fromJson(
                Map<String, dynamic>.from(e),
              ),)
          .toList(),
      judgmentBrief: brief,
      awaitingStep: awaiting,
      steps: (run['steps'] as List? ?? const <dynamic>[])
          .whereType<Map<dynamic, dynamic>>()
          .map((e) => AgentRunStepView.fromJson(
                Map<String, dynamic>.from(e),
              ),)
          .toList(),
      artifacts: (json['artifacts'] as List? ?? const <dynamic>[])
          .whereType<Map<dynamic, dynamic>>()
          .map((e) => HybridJourneyArtifactView.fromJson(
                Map<String, dynamic>.from(e),
              ),)
          .toList(),
    );
  }

  final String version;
  final String runId;
  final String runStatus;
  final String goalTitle;
  final String? taskId;
  final String taskTitle;
  final List<HybridJourneyCitation> citations;
  final HybridJudgmentBrief? judgmentBrief;

  /// X-07 统一 awaiting step 投影（「轮到谁」的单一读面，不重建）。
  final AgentRunAwaitingStep? awaitingStep;
  final List<AgentRunStepView> steps;
  final List<HybridJourneyArtifactView> artifacts;

  bool get isAwaitingJudgment =>
      (awaitingStep?.isAwaiting ?? false) &&
      awaitingStep!.stepId == 'judgment';

  bool get isAwaitingOutcome =>
      (awaitingStep?.isAwaiting ?? false) &&
      awaitingStep!.stepId == 'outcome';

  bool get isSucceeded => runStatus == 'SUCCEEDED';
}
