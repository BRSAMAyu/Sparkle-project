/// V4-F03 · experience_event.v1 呈现事件模型（移动端消费面的封闭解析）。
///
/// 契约真源：`v4/evidence/V4-B05/contract_receipt_min.md` §3（词表/字段/不变量
/// 冻结）+ D01 投影器 `backend/app/core/experience_event.py`（同一 schema 的
/// 服务端产出面）。本模型是移动端**唯一**解析入口，解析纪律 fail-safe：
///
/// - 任何结构违规（缺字段 / 词表外 kind·commitState·errorState·subjectType·
///   modality / E1·E2 被破坏）→ [ExperienceEventModel.tryParse] 返回
///   `null`，调用方必须「忽略 + 静默计数」（B05 §8 双读纪律：未注册 kind
///   **不得**当成功处理）；
/// - 解析成功 = 事件携带完整去重身份（[ExperienceEventModel.eventId]，内容
///   寻址），消费方按其做 replay 抑制（B05 §3「同 event_id 重播不重复触觉/
///   音效」——抑制键位冻结）；
/// - 本模型是**呈现投影**，不是业务事实（契约 I1）：无任何权限语义字段，
///   不得由 kind/subject 推导任何写操作资格。
///
/// WS 下发面（`ExperienceEventFrame` proto 增量）归 contract-owner 单独合并
/// （D01 limitations #1 / B05 §8）；本模型按 JSON 形状解析，transport 无关。
library;

import 'package:flutter/foundation.dart';

/// schema 版本常量（与 D01 `EXPERIENCE_EVENT_SCHEMA_VERSION` 逐字对齐）。
const String kExperienceEventSchemaVersion = 'experience_event.v1';

/// kind 封闭七元集（冻结；扩展 = 契约变更）。
const Set<String> kExperienceEventKinds = <String>{
  'state_confirmed',
  'state_syncing',
  'correction_applied',
  'calibration_notice',
  'resume_available',
  'progress_delta',
  'terminal_failed',
};

/// commit_state 封闭二元集。
const Set<String> kExperienceCommitStates = <String>{'committed', 'error'};

/// error_state 封闭五元集（1:1 复用 ACTION_ERROR_CODES 五值投影）。
const Set<String> kExperienceErrorStates = <String>{
  'version_conflict',
  'unauthorized',
  'not_pending',
  'expired',
  'not_found',
};

/// subject.type 封闭六元集。
const Set<String> kExperienceSubjectTypes = <String>{
  'task',
  'goal',
  'run',
  'intervention',
  'memory',
  'plan',
};

/// presentation.modalities 封闭三元集。
const Set<String> kExperienceModalities = <String>{'visual', 'audio', 'haptic'};

/// 事件锚定的对象 + 投影时点版本 token（当前对象 version 校验的输入位）。
@immutable
class ExperienceSubject {
  const ExperienceSubject({required this.type, required this.id, required this.versionToken});

  final String type;
  final String id;
  final String versionToken;
}

/// 呈现模态 + 冻结文案表键（非模型自由文本；asset_ref 仅指已过审 token 集）。
@immutable
class ExperiencePresentation {
  const ExperiencePresentation({required this.modalities, required this.copyKey, this.assetRef});

  final List<String> modalities;
  final String copyKey;
  final String? assetRef;
}

/// experience_event.v1 呈现回执（封闭结构；I1：无任何权限语义字段）。
@immutable
class ExperienceEventModel {
  const ExperienceEventModel({
    required this.schemaVersion,
    required this.eventId,
    required this.kind,
    required this.receiptRef,
    required this.commitState,
    required this.errorState,
    required this.subject,
    required this.presentation,
    required this.dedupeKey,
    required this.issuedAt,
    required this.expiresAt,
  });

  final String schemaVersion;

  /// 去重/replay 抑制键锚（内容寻址 id；同权威回执重放恒同）。
  final String eventId;

  final String kind;
  final String? receiptRef;
  final String commitState;
  final String? errorState;
  final ExperienceSubject subject;
  final ExperiencePresentation presentation;
  final String dedupeKey;
  final String issuedAt;
  final String? expiresAt;

  /// kind=state_confirmed 是唯一成功面孔 kind（E1：恒 committed + receipt 必选）。
  bool get isSuccessKind => kind == 'state_confirmed';

  /// 结构失败安全解析：任何违规返回 null（调用方忽略 + 计数，绝不渲染成功）。
  static ExperienceEventModel? tryParse(Map<String, dynamic>? json) {
    if (json == null) return null;
    final schemaVersion = _nonEmptyString(json['schema_version']);
    final eventId = _nonEmptyString(json['event_id']);
    final kind = _nonEmptyString(json['kind']);
    final commitState = _nonEmptyString(json['commit_state']);
    final dedupeKey = _nonEmptyString(json['dedupe_key']);
    final issuedAt = _nonEmptyString(json['issued_at']);
    final expiresAt = _nonEmptyString(json['expires_at']);
    if (schemaVersion == null ||
        eventId == null ||
        kind == null ||
        commitState == null ||
        dedupeKey == null ||
        issuedAt == null ||
        schemaVersion != kExperienceEventSchemaVersion) {
      return null;
    }
    if (!kExperienceEventKinds.contains(kind) || !kExperienceCommitStates.contains(commitState)) {
      return null;
    }
    final receiptRef = _nonEmptyString(json['receipt_ref']);
    final errorState = _nonEmptyString(json['error_state']);
    // E1：state_confirmed ⇒ committed 且 receipt_ref 必选（无例外）。
    if (kind == 'state_confirmed' && (commitState != 'committed' || receiptRef == null)) {
      return null;
    }
    // E2：error ⇒ error_state 必选；committed ⇒ error_state 必为 null（互斥）。
    if (commitState == 'error' && errorState == null) return null;
    if (commitState == 'committed' && errorState != null) return null;
    if (errorState != null && !kExperienceErrorStates.contains(errorState)) return null;

    final Object? subjectJson = json['subject'];
    final Object? presentationJson = json['presentation'];
    if (subjectJson is! Map || presentationJson is! Map) return null;
    final subjectType = _nonEmptyString(subjectJson['type']);
    final subjectId = _nonEmptyString(subjectJson['id']);
    final versionToken = _nonEmptyString(subjectJson['version_token']);
    if (subjectType == null ||
        subjectId == null ||
        versionToken == null ||
        !kExperienceSubjectTypes.contains(subjectType)) {
      return null;
    }
    final Object? modalitiesJson = presentationJson['modalities'];
    final copyKey = _nonEmptyString(presentationJson['copy_key']);
    if (copyKey == null || modalitiesJson is! List) return null;
    final modalities = <String>[];
    for (final Object? mod in modalitiesJson) {
      final value = _nonEmptyString(mod);
      if (value == null || !kExperienceModalities.contains(value)) return null;
      if (modalities.contains(value)) return null; // 重复模态 = 结构违规
      modalities.add(value);
    }
    final assetRef = _nonEmptyString(presentationJson['asset_ref']);
    return ExperienceEventModel(
      schemaVersion: schemaVersion,
      eventId: eventId,
      kind: kind,
      receiptRef: receiptRef,
      commitState: commitState,
      errorState: errorState,
      subject: ExperienceSubject(type: subjectType, id: subjectId, versionToken: versionToken),
      presentation: ExperiencePresentation(
        modalities: List<String>.unmodifiable(modalities),
        copyKey: copyKey,
        assetRef: assetRef,
      ),
      dedupeKey: dedupeKey,
      issuedAt: issuedAt,
      expiresAt: expiresAt,
    );
  }

  static String? _nonEmptyString(Object? value) {
    if (value is! String) return null;
    final trimmed = value.trim();
    return trimmed.isEmpty ? null : trimmed;
  }
}
