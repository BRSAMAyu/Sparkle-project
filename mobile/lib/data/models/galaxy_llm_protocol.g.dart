// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'galaxy_llm_protocol.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PositionHint _$PositionHintFromJson(Map<String, dynamic> json) => PositionHint(
      strategy: $enumDecode(_$PositionStrategyEnumMap, json['strategy']),
      angleOffset: (json['angle_offset'] as num?)?.toDouble(),
      radiusRatio: (json['radius_ratio'] as num?)?.toDouble(),
      referenceNodeId: json['reference_node_id'] as String?,
      distance:
          $enumDecodeNullable(_$RelativeDistanceEnumMap, json['distance']),
      region: $enumDecodeNullable(_$SectorRegionEnumMap, json['region']),
      x: (json['x'] as num?)?.toDouble(),
      y: (json['y'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$PositionHintToJson(PositionHint instance) =>
    <String, dynamic>{
      'strategy': _$PositionStrategyEnumMap[instance.strategy]!,
      'angle_offset': instance.angleOffset,
      'radius_ratio': instance.radiusRatio,
      'reference_node_id': instance.referenceNodeId,
      'distance': _$RelativeDistanceEnumMap[instance.distance],
      'region': _$SectorRegionEnumMap[instance.region],
      'x': instance.x,
      'y': instance.y,
    };

const _$PositionStrategyEnumMap = {
  PositionStrategy.polar: 'polar',
  PositionStrategy.nearNode: 'near_node',
  PositionStrategy.sectorRegion: 'sector_region',
  PositionStrategy.auto: 'auto',
  PositionStrategy.absolute: 'absolute',
};

const _$RelativeDistanceEnumMap = {
  RelativeDistance.veryClose: 'very_close',
  RelativeDistance.close: 'close',
  RelativeDistance.medium: 'medium',
  RelativeDistance.far: 'far',
  RelativeDistance.veryFar: 'very_far',
};

const _$SectorRegionEnumMap = {
  SectorRegion.inner: 'inner',
  SectorRegion.middle: 'middle',
  SectorRegion.outer: 'outer',
  SectorRegion.centerAngle: 'center_angle',
};

NodeConnection _$NodeConnectionFromJson(Map<String, dynamic> json) =>
    NodeConnection(
      targetId: json['target_id'] as String,
      relationType: $enumDecode(_$RelationTypeEnumMap, json['relation_type']),
      strength: (json['strength'] as num?)?.toDouble() ?? 0.5,
      bidirectional: json['bidirectional'] as bool? ?? false,
    );

Map<String, dynamic> _$NodeConnectionToJson(NodeConnection instance) =>
    <String, dynamic>{
      'target_id': instance.targetId,
      'relation_type': _$RelationTypeEnumMap[instance.relationType]!,
      'strength': instance.strength,
      'bidirectional': instance.bidirectional,
    };

const _$RelationTypeEnumMap = {
  RelationType.prerequisite: 'prerequisite',
  RelationType.derived: 'derived',
  RelationType.related: 'related',
  RelationType.similar: 'similar',
  RelationType.contrast: 'contrast',
  RelationType.application: 'application',
  RelationType.example: 'example',
};

LLMNodeSpec _$LLMNodeSpecFromJson(Map<String, dynamic> json) => LLMNodeSpec(
      id: json['id'] as String,
      name: json['name'] as String,
      sector: $enumDecode(_$SectorEnumEnumMap, json['sector']),
      importance: (json['importance'] as num?)?.toInt() ?? 3,
      baseColor: json['base_color'] as String?,
      masteryScore: (json['mastery_score'] as num?)?.toInt() ?? 0,
      isUnlocked: json['is_unlocked'] as bool? ?? true,
      positionHint: json['position_hint'] == null
          ? null
          : PositionHint.fromJson(
              json['position_hint'] as Map<String, dynamic>),
      connections: (json['connections'] as List<dynamic>?)
              ?.map((e) => NodeConnection.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      tags:
          (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList() ??
              const [],
      description: json['description'] as String?,
      parentId: json['parent_id'] as String?,
    );

Map<String, dynamic> _$LLMNodeSpecToJson(LLMNodeSpec instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'sector': _$SectorEnumEnumMap[instance.sector]!,
      'importance': instance.importance,
      'base_color': instance.baseColor,
      'mastery_score': instance.masteryScore,
      'is_unlocked': instance.isUnlocked,
      'position_hint': instance.positionHint,
      'connections': instance.connections,
      'tags': instance.tags,
      'description': instance.description,
      'parent_id': instance.parentId,
    };

const _$SectorEnumEnumMap = {
  SectorEnum.cosmos: 'COSMOS',
  SectorEnum.tech: 'TECH',
  SectorEnum.art: 'ART',
  SectorEnum.civilization: 'CIVILIZATION',
  SectorEnum.life: 'LIFE',
  SectorEnum.wisdom: 'WISDOM',
  SectorEnum.voidSector: 'VOID',
};

LLMNodeMoveSpec _$LLMNodeMoveSpecFromJson(Map<String, dynamic> json) =>
    LLMNodeMoveSpec(
      nodeId: json['node_id'] as String,
      newSector: $enumDecodeNullable(_$SectorEnumEnumMap, json['new_sector']),
      positionHint:
          PositionHint.fromJson(json['position_hint'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$LLMNodeMoveSpecToJson(LLMNodeMoveSpec instance) =>
    <String, dynamic>{
      'node_id': instance.nodeId,
      'new_sector': _$SectorEnumEnumMap[instance.newSector],
      'position_hint': instance.positionHint,
    };

LLMGalaxyAction _$LLMGalaxyActionFromJson(Map<String, dynamic> json) =>
    LLMGalaxyAction(
      action: $enumDecode(_$LLMActionTypeEnumMap, json['action']),
      nodes: (json['nodes'] as List<dynamic>?)
          ?.map((e) => LLMNodeSpec.fromJson(e as Map<String, dynamic>))
          .toList(),
      nodeIds: (json['node_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      connections: (json['connections'] as List<dynamic>?)
          ?.map((e) => LLMConnectionSpec.fromJson(e as Map<String, dynamic>))
          .toList(),
      moveSpecs: (json['move_specs'] as List<dynamic>?)
          ?.map((e) => LLMNodeMoveSpec.fromJson(e as Map<String, dynamic>))
          .toList(),
      batchActions: (json['batch_actions'] as List<dynamic>?)
          ?.map((e) => LLMGalaxyAction.fromJson(e as Map<String, dynamic>))
          .toList(),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$LLMGalaxyActionToJson(LLMGalaxyAction instance) =>
    <String, dynamic>{
      'action': _$LLMActionTypeEnumMap[instance.action]!,
      'nodes': instance.nodes,
      'node_ids': instance.nodeIds,
      'connections': instance.connections,
      'move_specs': instance.moveSpecs,
      'batch_actions': instance.batchActions,
      'metadata': instance.metadata,
    };

const _$LLMActionTypeEnumMap = {
  LLMActionType.addNodes: 'add_nodes',
  LLMActionType.updateNodes: 'update_nodes',
  LLMActionType.deleteNodes: 'delete_nodes',
  LLMActionType.addConnections: 'add_connections',
  LLMActionType.updateConnections: 'update_connections',
  LLMActionType.removeConnections: 'remove_connections',
  LLMActionType.moveNodes: 'move_nodes',
  LLMActionType.batchOperation: 'batch_operation',
};

LLMConnectionSpec _$LLMConnectionSpecFromJson(Map<String, dynamic> json) =>
    LLMConnectionSpec(
      sourceId: json['source_id'] as String,
      targetId: json['target_id'] as String,
      relationType: $enumDecode(_$RelationTypeEnumMap, json['relation_type']),
      strength: (json['strength'] as num?)?.toDouble() ?? 0.5,
      bidirectional: json['bidirectional'] as bool? ?? false,
    );

Map<String, dynamic> _$LLMConnectionSpecToJson(LLMConnectionSpec instance) =>
    <String, dynamic>{
      'source_id': instance.sourceId,
      'target_id': instance.targetId,
      'relation_type': _$RelationTypeEnumMap[instance.relationType]!,
      'strength': instance.strength,
      'bidirectional': instance.bidirectional,
    };

LLMActionResult _$LLMActionResultFromJson(Map<String, dynamic> json) =>
    LLMActionResult(
      success: json['success'] as bool,
      error: json['error'] as String?,
      addedNodeIds: (json['added_node_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      updatedNodeIds: (json['updated_node_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      deletedNodeIds: (json['deleted_node_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      computedPositions:
          (json['computed_positions'] as Map<String, dynamic>?)?.map(
        (k, e) => MapEntry(
            k, (e as List<dynamic>).map((e) => (e as num).toDouble()).toList()),
      ),
    );

Map<String, dynamic> _$LLMActionResultToJson(LLMActionResult instance) =>
    <String, dynamic>{
      'success': instance.success,
      'error': instance.error,
      'added_node_ids': instance.addedNodeIds,
      'updated_node_ids': instance.updatedNodeIds,
      'deleted_node_ids': instance.deletedNodeIds,
      'computed_positions': instance.computedPositions,
    };
