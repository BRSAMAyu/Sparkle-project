import 'package:sparkle/core/utils/text_rendering.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class CardProtocolRef {
  const CardProtocolRef({
    required this.cardId,
    required this.cardType,
    this.lifecycleStatus,
    this.metadata = const <String, dynamic>{},
    this.tags = const <String>[],
  });

  factory CardProtocolRef.fromRaw(Map<String, dynamic> raw) {
    final metadata = raw['metadata'] is Map
        ? Map<String, dynamic>.from(raw['metadata'] as Map)
        : const <String, dynamic>{};
    return CardProtocolRef(
      cardId: _asString(raw['card_id'] ?? raw['id']) ?? '',
      cardType: _asString(raw['card_type'] ?? raw['type']) ?? 'CUSTOM',
      lifecycleStatus: _asString(raw['lifecycle_status'] ?? raw['status']),
      metadata: metadata,
      tags: (raw['tags'] as List<dynamic>? ?? const <dynamic>[])
          .map((item) => item.toString())
          .toList(),
    );
  }

  static CardProtocolRef? maybeFromRaw(Map<String, dynamic> raw) {
    final hasCardShape = raw.containsKey('card_id') ||
        raw.containsKey('card_type') ||
        raw['metadata'] is Map;
    if (!hasCardShape) return null;
    final ref = CardProtocolRef.fromRaw(raw);
    return ref.cardId.isEmpty ? null : ref;
  }

  final String cardId;
  final String cardType;
  final String? lifecycleStatus;
  final Map<String, dynamic> metadata;
  final List<String> tags;

  String? get legacyPlanId => _asString(metadata['legacy_plan_id']);
  String? get legacyTaskId => _asString(metadata['legacy_task_id']);
  String get normalizedEntityType {
    switch (cardType.toUpperCase()) {
      case 'PLAN':
        return 'plan';
      case 'TASK':
        return 'task';
      case 'KNOWLEDGE':
        return 'knowledge_card';
      default:
        return cardType.toLowerCase();
    }
  }
}

class EntityCardActionPayload {
  const EntityCardActionPayload({
    required this.id,
    required this.type,
    required this.label,
    this.route,
    this.style,
    this.payload = const <String, dynamic>{},
  });

  factory EntityCardActionPayload.fromMap(Map<String, dynamic> raw) {
    final normalizedPayload = raw['payload'] is Map
        ? Map<String, dynamic>.from(raw['payload'] as Map)
        : const <String, dynamic>{};
    return EntityCardActionPayload(
      id: _asString(raw['id']) ?? 'unknown_action',
      type: _asString(raw['type']) ?? 'custom',
      label: _asString(raw['label']) ?? 'Execute',
      route: _asString(raw['route']),
      style: _asString(raw['style']),
      payload: normalizedPayload,
    );
  }

  final String id;
  final String type;
  final String label;
  final String? route;
  final String? style;
  final Map<String, dynamic> payload;
}

class EntityCardSharePayload {
  const EntityCardSharePayload({
    required this.resourceType,
    required this.resourceId,
    required this.title,
    this.subtitle,
    this.meta = const <String, dynamic>{},
    this.owner = const <String, dynamic>{},
    this.visibility,
    this.preview = const <String, dynamic>{},
    this.sourceReceipt = const <String, dynamic>{},
    this.adoptionAction,
    this.expiresAt,
    this.revokedAt,
    this.availability,
  });

  factory EntityCardSharePayload.fromMap(Map<String, dynamic> raw) =>
      EntityCardSharePayload(
        resourceType: _asString(raw['resource_type']) ?? 'unknown',
        resourceId: _asString(raw['resource_id']) ?? '',
        title: _asString(raw['title']) ?? 'Unnamed Card',
        subtitle: _asString(raw['subtitle']),
        meta: raw['meta'] is Map<String, dynamic>
            ? Map<String, dynamic>.from(raw['meta'] as Map<String, dynamic>)
            : raw['meta'] is Map
                ? Map<String, dynamic>.from(
                    raw['meta'] as Map<Object?, Object?>,
                  )
                : const <String, dynamic>{},
        owner: raw['owner'] is Map
            ? Map<String, dynamic>.from(raw['owner'] as Map)
            : const <String, dynamic>{},
        visibility: _asString(raw['visibility']),
        preview: raw['preview'] is Map
            ? Map<String, dynamic>.from(raw['preview'] as Map)
            : const <String, dynamic>{},
        sourceReceipt: raw['source_receipt'] is Map
            ? Map<String, dynamic>.from(raw['source_receipt'] as Map)
            : const <String, dynamic>{},
        adoptionAction: raw['adoption_action'] is Map
            ? EntityCardActionPayload.fromMap(
                Map<String, dynamic>.from(raw['adoption_action'] as Map),
              )
            : null,
        expiresAt: _parseDate(raw['expires_at']),
        revokedAt: _parseDate(raw['revoked_at']),
        availability: _asString(raw['availability']),
      );

  final String resourceType;
  final String resourceId;
  final String title;
  final String? subtitle;
  final Map<String, dynamic> meta;
  final Map<String, dynamic> owner;
  final String? visibility;
  final Map<String, dynamic> preview;
  final Map<String, dynamic> sourceReceipt;
  final EntityCardActionPayload? adoptionAction;
  final DateTime? expiresAt;
  final DateTime? revokedAt;
  final String? availability;
}

class EntityCardFeedbackPayload {
  const EntityCardFeedbackPayload({
    this.toolResultId,
    this.confirmationRequired = false,
    this.canConfirmAll = false,
  });

  factory EntityCardFeedbackPayload.fromMap(Map<String, dynamic> raw) =>
      EntityCardFeedbackPayload(
        toolResultId: _asString(raw['tool_result_id']),
        confirmationRequired: _asBool(raw['confirmation_required']) ?? false,
        canConfirmAll: _asBool(raw['can_confirm_all']) ?? false,
      );

  final String? toolResultId;
  final bool confirmationRequired;
  final bool canConfirmAll;
}

class EntityCardPayload {
  const EntityCardPayload({
    required this.entityType,
    required this.title,
    this.schemaVersion,
    this.entityId,
    this.summary,
    this.status,
    this.executionState,
    this.source = const <String, dynamic>{},
    this.primaryAction,
    this.secondaryActions = const <EntityCardActionPayload>[],
    this.share,
    this.feedback,
    this.linkedEntities = const <String, dynamic>{},
    this.metrics = const <String, dynamic>{},
    this.tags = const <String>[],
    this.children = const <EntityCardPayload>[],
    this.cardRef,
    this.raw = const <String, dynamic>{},
  });

  factory EntityCardPayload.fromRaw(
    Map<String, dynamic> raw, {
    String? fallbackType,
  }) {
    final entityMap = raw['entity_card'] is Map<String, dynamic>
        ? Map<String, dynamic>.from(raw['entity_card'] as Map<String, dynamic>)
        : raw['entity_card'] is Map
            ? Map<String, dynamic>.from(
                raw['entity_card'] as Map<Object?, Object?>,
              )
            : _buildLegacyEntityMap(raw, fallbackType: fallbackType);
    return EntityCardPayload._fromEntityMap(entityMap);
  }

  factory EntityCardPayload._fromEntityMap(Map<String, dynamic> raw) {
    final childrenRaw = raw['children'] as List<dynamic>? ?? const <dynamic>[];
    return EntityCardPayload(
      schemaVersion: _asString(raw['schema_version']),
      entityType: _asString(raw['entity_type']) ?? 'unknown',
      entityId: _asString(raw['entity_id']),
      title: _asString(raw['title']) ?? 'Unnamed Entity',
      summary: _asString(raw['summary']),
      status: _asString(raw['status']),
      executionState: _asString(raw['execution_state']),
      source: raw['source'] is Map
          ? Map<String, dynamic>.from(raw['source'] as Map)
          : const <String, dynamic>{},
      primaryAction: raw['primary_action'] is Map
          ? EntityCardActionPayload.fromMap(
              Map<String, dynamic>.from(raw['primary_action'] as Map),
            )
          : null,
      secondaryActions:
          (raw['secondary_actions'] as List<dynamic>? ?? const <dynamic>[])
              .whereType<Map<Object?, Object?>>()
              .map(
                (item) => EntityCardActionPayload.fromMap(
                  Map<String, dynamic>.from(item),
                ),
              )
              .toList(),
      share: raw['share'] is Map
          ? EntityCardSharePayload.fromMap(
              Map<String, dynamic>.from(raw['share'] as Map),
            )
          : null,
      feedback: raw['feedback'] is Map
          ? EntityCardFeedbackPayload.fromMap(
              Map<String, dynamic>.from(raw['feedback'] as Map),
            )
          : null,
      linkedEntities: raw['linked_entities'] is Map
          ? Map<String, dynamic>.from(raw['linked_entities'] as Map)
          : const <String, dynamic>{},
      metrics: raw['metrics'] is Map
          ? Map<String, dynamic>.from(raw['metrics'] as Map)
          : const <String, dynamic>{},
      tags: (raw['tags'] as List<dynamic>? ?? const <dynamic>[])
          .map((item) => item.toString())
          .toList(),
      children: childrenRaw
          .whereType<Map<Object?, Object?>>()
          .map(
            (child) => EntityCardPayload._fromEntityMap(
              Map<String, dynamic>.from(child),
            ),
          )
          .toList(),
      cardRef: raw['card_protocol'] is Map
          ? CardProtocolRef.maybeFromRaw(
              Map<String, dynamic>.from(raw['card_protocol'] as Map),
            )
          : CardProtocolRef.maybeFromRaw(raw),
      raw: raw['raw'] is Map
          ? Map<String, dynamic>.from(raw['raw'] as Map)
          : const <String, dynamic>{},
    );
  }

  final String? schemaVersion;
  final String entityType;
  final String? entityId;
  final String title;
  final String? summary;
  final String? status;
  final String? executionState;
  final Map<String, dynamic> source;
  final EntityCardActionPayload? primaryAction;
  final List<EntityCardActionPayload> secondaryActions;
  final EntityCardSharePayload? share;
  final EntityCardFeedbackPayload? feedback;
  final Map<String, dynamic> linkedEntities;
  final Map<String, dynamic> metrics;
  final List<String> tags;
  final List<EntityCardPayload> children;
  final CardProtocolRef? cardRef;
  final Map<String, dynamic> raw;

  String? get detailRoute => primaryAction?.route;
  String? get shareResourceType => share?.resourceType;
  String? get shareResourceId => share?.resourceId;
  String? get toolResultId => feedback?.toolResultId;
  String? get planId =>
      _asString(linkedEntities['plan_id']) ??
      _asString(raw['plan_id']) ??
      _asString(raw['id'] ?? raw['plan_id']);
}

class PlanCardPayload {
  const PlanCardPayload({
    required this.title,
    required this.type,
    required this.entity,
    this.id,
    this.description,
    this.subject,
    this.planStage,
    this.targetDate,
    this.progress,
    this.taskCount,
    this.targetMastery,
    this.isActive,
    this.isPrimary,
    this.source,
    this.cardRef,
  });

  factory PlanCardPayload.fromMap(Map<String, dynamic> raw) {
    final entity = EntityCardPayload.fromRaw(raw, fallbackType: 'plan');
    final cardRef = CardProtocolRef.maybeFromRaw(raw) ?? entity.cardRef;
    final metadata = cardRef?.metadata ?? const <String, dynamic>{};
    final normalizedType = _normalizePlanType(
      raw['type'] ??
          raw['plan_type'] ??
          raw['category'] ??
          metadata['plan_kind'] ??
          entity.status,
    );
    return PlanCardPayload(
      entity: entity,
      cardRef: cardRef,
      id: entity.entityId ??
          _asString(metadata['legacy_plan_id'] ?? raw['id'] ?? raw['plan_id']),
      title: entity.title,
      type: normalizedType,
      description: entity.summary ??
          _asString(raw['description'] ?? metadata['description']),
      subject: _asString(
        raw['subject'] ??
            metadata['subject'] ??
            entity.linkedEntities['subject'],
      ),
      planStage: _asString(raw['plan_stage'] ?? metadata['legacy_plan_stage']),
      targetDate: _parseDate(raw['target_date'] ?? metadata['target_date']),
      progress: _asDouble(
        raw['progress'] ?? metadata['progress'] ?? entity.metrics['progress'],
      ),
      taskCount: _asInt(raw['task_count'] ?? entity.metrics['task_count']),
      targetMastery:
          _asDouble(raw['target_mastery'] ?? entity.metrics['target_mastery']),
      isActive: _asBool(raw['is_active']),
      isPrimary: _asBool(raw['is_primary']),
      source: _asString(raw['source'] ?? entity.linkedEntities['source']),
    );
  }

  final EntityCardPayload entity;
  final String? id;
  final String title;
  final String type;
  final String? description;
  final String? subject;
  final String? planStage;
  final DateTime? targetDate;
  final double? progress;
  final int? taskCount;
  final double? targetMastery;
  final bool? isActive;
  final bool? isPrimary;
  final String? source;
  final CardProtocolRef? cardRef;

  String? get cardId => cardRef?.cardId;

  PlanType? get planType {
    switch (type) {
      case 'growth':
        return PlanType.growth;
      case 'sprint':
        return PlanType.sprint;
      default:
        return null;
    }
  }
}

TaskModel? taskModelFromEntityPayload(Map<String, dynamic> raw) {
  try {
    final entity = EntityCardPayload.fromRaw(raw, fallbackType: 'task');
    final source = entity.raw.isNotEmpty ? entity.raw : raw;
    final now = DateTime.now().toIso8601String();
    final normalized = <String, dynamic>{
      ...source,
      'id': entity.entityId ?? _asString(source['id']) ?? '',
      'user_id': _asString(source['user_id']) ?? 'current_user',
      'plan_id':
          _asString(source['plan_id'] ?? entity.linkedEntities['plan_id']),
      'title': entity.title,
      'type': _normalizeTaskType(source['type']),
      'tags': (source['tags'] as List<dynamic>? ?? entity.tags)
          .map((item) => item.toString())
          .toList(),
      'estimated_minutes': _asInt(
            source['estimated_minutes'] ?? entity.metrics['estimated_minutes'],
          ) ??
          30,
      'difficulty':
          _asInt(source['difficulty'] ?? entity.metrics['difficulty']) ?? 1,
      'energy_cost':
          _asInt(source['energy_cost'] ?? entity.metrics['energy_cost']) ?? 1,
      'guide_content': _asString(source['guide_content']) ??
          _asString(source['description']) ??
          entity.summary,
      'status': _normalizeTaskStatus(source['status'] ?? entity.status),
      'started_at': _parseDate(source['started_at'])?.toIso8601String(),
      'completed_at': _parseDate(source['completed_at'])?.toIso8601String(),
      'actual_minutes': _asInt(source['actual_minutes']),
      'user_note': _asString(source['user_note']),
      'priority': _asInt(source['priority'] ?? entity.metrics['priority']) ?? 2,
      'due_date': _parseDate(source['due_date'])?.toIso8601String(),
      'knowledge_node_id': _asString(source['knowledge_node_id']),
      'subtasks_total': _asInt(source['subtasks_total']) ?? 0,
      'subtasks_completed': _asInt(source['subtasks_completed']) ?? 0,
      'created_at': _parseDate(source['created_at'])?.toIso8601String() ?? now,
      'updated_at': _parseDate(source['updated_at'] ?? source['created_at'])
              ?.toIso8601String() ??
          now,
    };
    if ((normalized['id'] as String).isEmpty) {
      return null;
    }
    return TaskModel.fromJson(normalized);
  } catch (_) {
    return null;
  }
}

Map<String, dynamic> _buildLegacyEntityMap(
  Map<String, dynamic> raw, {
  String? fallbackType,
}) {
  final cardRef = CardProtocolRef.maybeFromRaw(raw);
  final cardMetadata = cardRef?.metadata ?? const <String, dynamic>{};
  final source = cardRef == null
      ? raw
      : <String, dynamic>{
          ...cardMetadata,
          ...raw,
          'id': cardRef.legacyTaskId ?? cardRef.legacyPlanId ?? cardRef.cardId,
        };
  final type = fallbackType ??
      cardRef?.normalizedEntityType ??
      _asString(raw['entity_type']) ??
      'unknown';
  if (type == 'task') {
    final taskId = _asString(source['legacy_task_id'] ?? source['id']);
    return <String, dynamic>{
      'entity_type': 'task',
      'entity_id': taskId,
      'title': _asString(source['title']) ?? 'Unnamed Task',
      'summary': _asString(source['guide_content']) ??
          _asString(source['description']),
      'status': _normalizeTaskStatus(
        source['status'] ??
            source['lifecycle_status'] ??
            cardRef?.lifecycleStatus,
      ),
      'execution_state':
          (_asString(source['status'])?.toUpperCase() == 'COMPLETED')
              ? 'confirmed'
              : 'draft',
      'linked_entities': {
        if (_asString(source['legacy_plan_id'] ?? source['plan_id']) != null)
          'plan_id': _asString(source['legacy_plan_id'] ?? source['plan_id']),
      },
      'metrics': {
        if (_asInt(
              source['estimated_minutes'] ?? source['effort_minutes_default'],
            ) !=
            null)
          'estimated_minutes': _asInt(
            source['estimated_minutes'] ?? source['effort_minutes_default'],
          ),
        if (_asInt(source['priority']) != null)
          'priority': _asInt(source['priority']),
        if (_asInt(source['difficulty']) != null)
          'difficulty': _asInt(source['difficulty']),
      },
      'share': taskId == null
          ? null
          : {
              'resource_type': 'task',
              'resource_id': taskId,
              'title': _asString(source['title']) ?? 'Unnamed Task',
              'subtitle': _asString(source['guide_content']) ??
                  _asString(source['description']),
            },
      'feedback': {
        'tool_result_id': _asString(source['tool_result_id']),
        'confirmation_required': _asString(source['tool_result_id']) != null,
      },
      if (cardRef != null) 'card_protocol': raw,
      'raw': raw,
    };
  }
  if (type == 'task_list') {
    final taskChildren = (raw['tasks'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<Object?, Object?>>()
        .map(
          (item) => _buildLegacyEntityMap(
            Map<String, dynamic>.from(item),
            fallbackType: 'task',
          ),
        )
        .toList();
    return <String, dynamic>{
      'entity_type': 'task_list',
      'entity_id': _asString(raw['tool_result_id'] ?? raw['id']),
      'title': _asString(raw['plan_title'] ?? raw['plan_name']) ??
          '${taskChildren.length} executable tasks',
      'summary': _asString(raw['message']) ?? 'AI organized task list',
      'status': 'batch',
      'execution_state': 'draft',
      'linked_entities': {
        if (_asString(raw['plan_id']) != null)
          'plan_id': _asString(raw['plan_id']),
        if (_asString(raw['plan_title'] ?? raw['plan_name']) != null)
          'plan_title': _asString(raw['plan_title'] ?? raw['plan_name']),
      },
      'metrics': {
        'task_count': taskChildren.length,
        if (_asString(raw['rag_quality']) != null)
          'rag_quality': _asString(raw['rag_quality']),
      },
      'feedback': {
        'tool_result_id': _asString(raw['tool_result_id'] ?? raw['id']),
        'confirmation_required':
            _asString(raw['tool_result_id'] ?? raw['id']) != null,
        'can_confirm_all': true,
      },
      'children': taskChildren,
      'raw': raw,
    };
  }
  if (type == 'plan') {
    final planId = _asString(
      source['legacy_plan_id'] ?? source['id'] ?? source['plan_id'],
    );
    return <String, dynamic>{
      'entity_type': 'plan',
      'entity_id': planId,
      'title': _asString(source['title'] ?? source['name']) ?? 'Unnamed Plan',
      'summary': _asString(source['description']),
      'status': _normalizePlanType(
        source['type'] ?? source['plan_type'] ?? source['plan_kind'],
      ),
      'execution_state':
          (_asBool(source['is_active']) ?? true) ? 'active' : 'draft',
      'linked_entities': {
        if (_asString(source['subject']) != null)
          'subject': _asString(source['subject']),
        if (_asString(source['source']) != null)
          'source': _asString(source['source']),
      },
      'metrics': {
        if (_asDouble(source['progress']) != null)
          'progress': _asDouble(source['progress']),
        if (_asInt(source['task_count']) != null)
          'task_count': _asInt(source['task_count']),
        if (_asDouble(source['target_mastery']) != null)
          'target_mastery': _asDouble(source['target_mastery']),
      },
      'share': planId == null
          ? null
          : {
              'resource_type': 'plan',
              'resource_id': planId,
              'title':
                  _asString(source['title'] ?? source['name']) ?? 'Study Plan',
              'subtitle': _asString(source['description']),
            },
      'feedback': {
        'tool_result_id': _asString(source['tool_result_id']),
      },
      if (cardRef != null) 'card_protocol': raw,
      'raw': raw,
    };
  }
  if (type == 'knowledge_node' || type == 'knowledge_card') {
    final nodeId = _asString(raw['id'] ?? raw['node_id']);
    return <String, dynamic>{
      'entity_type': 'knowledge_node',
      'entity_id': nodeId,
      'title': _asString(raw['title']) ?? 'Unnamed Knowledge Node',
      'summary': _asString(raw['summary']) ?? _asString(raw['description']),
      'status': 'mastery',
      'execution_state': 'active',
      'metrics': {
        if (_asInt(raw['mastery_level']) != null)
          'mastery_level': _asInt(raw['mastery_level']),
      },
      'tags': (raw['tags'] as List<dynamic>? ?? const <dynamic>[])
          .map((item) => item.toString())
          .toList(),
      'share': nodeId == null
          ? null
          : {
              'resource_type': 'knowledge_node',
              'resource_id': nodeId,
              'title': _asString(raw['title']) ?? 'Knowledge Node',
              'subtitle':
                  _asString(raw['summary']) ?? _asString(raw['description']),
            },
      'raw': raw,
    };
  }
  if (type == 'review' || type == 'review_card') {
    final reviewId = _asString(raw['review_id'] ?? raw['id']);
    final mode = _asString(raw['mode']) ?? 'today';
    final query = _compactQuery({
      'mode': mode,
      'subject': _asString(raw['subject'] ?? raw['subject_code']),
      'plan_id': _asString(raw['plan_id']),
      'review_id': reviewId,
    });
    return <String, dynamic>{
      'entity_type': 'review',
      'entity_id': reviewId,
      'title': _asString(raw['title'] ?? raw['name']) ?? 'Review',
      'summary': _asString(
        raw['summary'] ?? raw['description'] ?? raw['diagnosis'],
      ),
      'status': _asString(raw['status'] ?? raw['decision']),
      'execution_state': _asString(raw['execution_state']) ?? 'suggested',
      'primary_action': {
        'id': 'open_review',
        'type': 'open_detail',
        'label': 'Open review',
        'route': query.isEmpty ? '/review?mode=today' : '/review?$query',
      },
      'linked_entities': {
        if (_asString(raw['plan_id']) != null)
          'plan_id': _asString(raw['plan_id']),
        if (_asString(raw['subject'] ?? raw['subject_code']) != null)
          'subject': _asString(raw['subject'] ?? raw['subject_code']),
      },
      'metrics': {
        if (_asDouble(raw['score'] ?? raw['overall_score']) != null)
          'score': _asDouble(raw['score'] ?? raw['overall_score']),
        if (_asInt(raw['due_count']) != null)
          'due_count': _asInt(raw['due_count']),
      },
      'share': reviewId == null
          ? null
          : {
              'resource_type': 'review',
              'resource_id': reviewId,
              'title': _asString(raw['title'] ?? raw['name']) ?? 'Review',
              'subtitle': _asString(raw['summary'] ?? raw['description']),
            },
      'raw': raw,
    };
  }
  if (type == 'vocabulary' || type == 'vocabulary_card') {
    final word = _asString(raw['word'] ?? raw['term']);
    final wordId = _asString(raw['word_id'] ?? raw['id']) ?? word;
    final query = _compactQuery({'word': word});
    return <String, dynamic>{
      'entity_type': 'vocabulary',
      'entity_id': wordId,
      'title': _asString(raw['title']) ?? word ?? 'Vocabulary',
      'summary': _asString(
        raw['definition'] ?? raw['translation'] ?? raw['summary'],
      ),
      'status': _asString(raw['status']) ??
          ((_asBool(raw['in_wordbook']) ?? false) ? 'saved' : 'lookup'),
      'execution_state': _asString(raw['execution_state']) ?? 'suggested',
      'primary_action': {
        'id': 'open_vocabulary',
        'type': 'open_detail',
        'label': 'Open vocabulary',
        'route': query.isEmpty
            ? '/tools/vocabulary_lookup'
            : '/tools/vocabulary_lookup?$query',
        'payload': {
          if (word != null) 'word': word,
          if (wordId != null) 'word_id': wordId,
        },
      },
      'secondary_actions': [
        {
          'id': 'review_wordbook',
          'type': 'open_detail',
          'label': 'Review wordbook',
          'route': '/tools/wordbook',
        },
      ],
      'linked_entities': {
        if (_asString(raw['knowledge_node_id']) != null)
          'knowledge_node_id': _asString(raw['knowledge_node_id']),
        if (_asString(raw['source_translation_id']) != null)
          'source_translation_id': _asString(raw['source_translation_id']),
      },
      'metrics': {
        if (_asInt(raw['importance']) != null)
          'importance': _asInt(raw['importance']),
        if (_asInt(raw['review_count']) != null)
          'review_count': _asInt(raw['review_count']),
      },
      'share': wordId == null
          ? null
          : {
              'resource_type': 'vocabulary',
              'resource_id': wordId,
              'title': _asString(raw['title']) ?? word ?? 'Vocabulary',
              'subtitle': _asString(raw['definition'] ?? raw['translation']),
            },
      'raw': raw,
    };
  }
  if (type == 'seed' || type == 'seed_card' || type == 'seed_library') {
    final seedId = _asString(raw['seed_id'] ?? raw['library_id'] ?? raw['id']);
    return <String, dynamic>{
      'entity_type': 'seed',
      'entity_id': seedId,
      'title': _asString(raw['title'] ?? raw['name']) ?? 'Seed',
      'summary': _asString(
        raw['summary'] ?? raw['description'] ?? raw['content'],
      ),
      'status': _asString(raw['status'] ?? raw['category']),
      'execution_state': _asString(raw['execution_state']) ?? 'adoptable',
      'primary_action': {
        'id': 'open_seed',
        'type': 'open_detail',
        'label': 'Open seed',
        'route': seedId == null ? '/seed-libraries' : '/seed-libraries/$seedId',
      },
      'secondary_actions': seedId == null
          ? <Map<String, dynamic>>[]
          : [
              {
                'id': 'adopt_seed',
                'type': 'adopt_resource',
                'label': 'Adopt seed',
                'payload': {'resource_type': 'seed', 'resource_id': seedId},
              },
              {
                'id': 'share_seed',
                'type': 'share_resource',
                'label': 'Share seed',
                'payload': {'resource_type': 'seed', 'resource_id': seedId},
              },
            ],
      'linked_entities': {
        if (_asString(raw['plan_id']) != null)
          'plan_id': _asString(raw['plan_id']),
        if (_asString(raw['task_id']) != null)
          'task_id': _asString(raw['task_id']),
        if (_asString(raw['knowledge_node_id']) != null)
          'knowledge_node_id': _asString(raw['knowledge_node_id']),
      },
      'metrics': {
        if (_asInt(raw['adoption_count']) != null)
          'adoption_count': _asInt(raw['adoption_count']),
        if (_asDouble(raw['rating']) != null)
          'rating': _asDouble(raw['rating']),
      },
      'share': seedId == null
          ? null
          : {
              'resource_type': 'seed',
              'resource_id': seedId,
              'title': _asString(raw['title'] ?? raw['name']) ?? 'Seed',
              'subtitle': _asString(raw['summary'] ?? raw['description']),
            },
      'raw': raw,
    };
  }
  if (type == 'shared_resource' || type == 'share_card') {
    final shareId =
        _asString(raw['shared_resource_id'] ?? raw['share_id'] ?? raw['id']);
    final resourceType = _asString(raw['resource_type']) ?? 'unknown';
    final resourceId = _asString(raw['resource_id']);
    final availability = _asString(raw['availability']) ?? 'available';
    final adoptionAction = raw['adoption_action'] is Map
        ? Map<String, dynamic>.from(raw['adoption_action'] as Map)
        : <String, dynamic>{
            'id': 'adopt_shared_resource',
            'type': 'adopt_resource',
            'label': 'Adopt resource',
            if (shareId != null)
              'route': '/community/shared-resources/$shareId/adopt',
            'payload': {
              if (shareId != null) 'shared_resource_id': shareId,
              'resource_type': resourceType,
              if (resourceId != null) 'resource_id': resourceId,
            },
          };
    final route =
        _resourceDetailRoute(resourceType, resourceId) ?? '/community';
    return <String, dynamic>{
      'entity_type': 'shared_resource',
      'entity_id': shareId,
      'title':
          _asString(raw['title'] ?? raw['resource_title']) ?? 'Shared Resource',
      'summary': _asString(
        raw['comment'] ?? raw['summary'] ?? raw['resource_summary'],
      ),
      'status': _asString(raw['permission'] ?? raw['visibility']),
      'execution_state': availability,
      'primary_action': {
        'id': 'open_shared_resource',
        'type': 'open_detail',
        'label': 'Open resource',
        'route': route,
      },
      'secondary_actions':
          const {'revoked', 'expired', 'private'}.contains(availability)
              ? <Map<String, dynamic>>[]
              : [adoptionAction],
      'linked_entities': {
        'resource_type': resourceType,
        if (resourceId != null) 'resource_id': resourceId,
        if (shareId != null) 'shared_resource_id': shareId,
      },
      'share': resourceId == null
          ? null
          : {
              'resource_type': resourceType,
              'resource_id': resourceId,
              'title': _asString(raw['title'] ?? raw['resource_title']) ??
                  'Shared Resource',
              'subtitle': _asString(raw['summary'] ?? raw['resource_summary']),
              if (raw['owner'] is Map) 'owner': raw['owner'],
              if (_asString(raw['visibility']) != null)
                'visibility': _asString(raw['visibility']),
              if (raw['preview'] is Map) 'preview': raw['preview'],
              if (raw['source_receipt'] is Map)
                'source_receipt': raw['source_receipt'],
              'adoption_action': adoptionAction,
              if (_asString(raw['expires_at']) != null)
                'expires_at': _asString(raw['expires_at']),
              if (_asString(raw['revoked_at']) != null)
                'revoked_at': _asString(raw['revoked_at']),
              'availability': availability,
            },
      'raw': raw,
    };
  }
  return <String, dynamic>{
    'entity_type': type,
    'entity_id': _asString(raw['id']),
    'title': _asString(raw['title']) ?? '未命名实体',
    'summary': _asString(raw['summary']) ?? _asString(raw['description']),
    'raw': raw,
  };
}

String _normalizeTaskType(dynamic raw) {
  final value = _asString(raw)?.trim().toLowerCase();
  switch (value) {
    case 'learning':
      return 'LEARNING';
    case 'training':
    case 'practice':
      return 'TRAINING';
    case 'error_fix':
    case 'errorfix':
      return 'ERROR_FIX';
    case 'reflection':
    case 'review':
      return 'REFLECTION';
    case 'social':
      return 'SOCIAL';
    case 'planning':
      return 'PLANNING';
    case 'ocr':
      return 'OCR';
    default:
      return 'LEARNING';
  }
}

String _normalizeTaskStatus(dynamic raw) {
  final value = _asString(raw)?.trim().toLowerCase();
  switch (value) {
    case 'pending':
    case 'active':
    case 'draft':
      return 'PENDING';
    case 'in_progress':
    case 'inprogress':
      return 'IN_PROGRESS';
    case 'paused':
      return 'PAUSED';
    case 'completed':
      return 'COMPLETED';
    case 'abandoned':
      return 'ABANDONED';
    default:
      return 'PENDING';
  }
}

String _normalizePlanType(dynamic raw) {
  final value = _asString(raw)?.trim().toLowerCase();
  switch (value) {
    case 'growth':
      return 'growth';
    case 'sprint':
      return 'sprint';
    default:
      return 'growth';
  }
}

String? _asString(dynamic value) => sanitizeNullableDisplayText(value);

int? _asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '');
}

double? _asDouble(dynamic value) {
  if (value is double) return value;
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '');
}

bool? _asBool(dynamic value) {
  if (value is bool) return value;
  final text = value?.toString().toLowerCase();
  switch (text) {
    case 'true':
    case '1':
      return true;
    case 'false':
    case '0':
      return false;
    default:
      return null;
  }
}

DateTime? _parseDate(dynamic value) {
  if (value is DateTime) return value;
  final text = _asString(value);
  if (text == null) return null;
  return DateTime.tryParse(text);
}

String _compactQuery(Map<String, String?> raw) {
  final query = <String, String>{};
  for (final entry in raw.entries) {
    final value = entry.value?.trim();
    if (value != null && value.isNotEmpty) {
      query[entry.key] = value;
    }
  }
  return Uri(queryParameters: query).query;
}

String? _resourceDetailRoute(String resourceType, String? resourceId) {
  if (resourceId == null || resourceId.isEmpty) return null;
  switch (resourceType) {
    case 'plan':
      return '/plans/$resourceId';
    case 'task':
      return '/tasks/$resourceId';
    case 'knowledge_node':
      return '/galaxy?nodeId=$resourceId';
    case 'seed':
    case 'seed_library':
      return '/seed-libraries/$resourceId';
    case 'vocabulary':
    case 'vocabulary_set':
      return '/tools/wordbook';
    case 'review':
    case 'review_result':
      return '/review?review_id=$resourceId';
    default:
      return null;
  }
}
