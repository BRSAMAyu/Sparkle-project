// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'galaxy_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

GalaxyEdgeModel _$GalaxyEdgeModelFromJson(Map<String, dynamic> json) =>
    GalaxyEdgeModel(
      id: json['id'] as String,
      sourceId: json['source_id'] as String,
      targetId: json['target_id'] as String,
      relationType: $enumDecodeNullable(
              _$EdgeRelationTypeEnumMap, json['relation_type']) ??
          EdgeRelationType.related,
      strength: (json['strength'] as num?)?.toDouble() ?? 0.5,
      bidirectional: json['bidirectional'] as bool? ?? false,
    );

Map<String, dynamic> _$GalaxyEdgeModelToJson(GalaxyEdgeModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'source_id': instance.sourceId,
      'target_id': instance.targetId,
      'relation_type': _$EdgeRelationTypeEnumMap[instance.relationType]!,
      'strength': instance.strength,
      'bidirectional': instance.bidirectional,
    };

const _$EdgeRelationTypeEnumMap = {
  EdgeRelationType.prerequisite: 'prerequisite',
  EdgeRelationType.derived: 'derived',
  EdgeRelationType.related: 'related',
  EdgeRelationType.similar: 'similar',
  EdgeRelationType.contrast: 'contrast',
  EdgeRelationType.application: 'application',
  EdgeRelationType.example: 'example',
  EdgeRelationType.parentChild: 'parent_child',
};

NodePositionHint _$NodePositionHintFromJson(Map<String, dynamic> json) =>
    NodePositionHint(
      angleOffset: (json['angle_offset'] as num?)?.toDouble(),
      radiusRatio: (json['radius_ratio'] as num?)?.toDouble(),
      nearNodeId: json['near_node_id'] as String?,
      distanceFromReference:
          (json['distance_from_reference'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$NodePositionHintToJson(NodePositionHint instance) =>
    <String, dynamic>{
      'angle_offset': instance.angleOffset,
      'radius_ratio': instance.radiusRatio,
      'near_node_id': instance.nearNodeId,
      'distance_from_reference': instance.distanceFromReference,
    };

GalaxyNodeModel _$GalaxyNodeModelFromJson(Map<String, dynamic> json) =>
    GalaxyNodeModel(
      id: json['id'] as String,
      name: json['name'] as String,
      importance: (json['importance'] as num).toInt(),
      sector: $enumDecode(_$SectorEnumEnumMap, json['sector']),
      isUnlocked: json['is_unlocked'] as bool,
      masteryScore: (json['mastery_score'] as num).toInt(),
      parentId: json['parent_id'] as String?,
      baseColor: json['base_color'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      description: json['description'] as String?,
      positionHint: json['position_hint'] == null
          ? null
          : NodePositionHint.fromJson(
              json['position_hint'] as Map<String, dynamic>),
      outgoingEdgeIds: (json['outgoing_edge_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      incomingEdgeIds: (json['incoming_edge_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$GalaxyNodeModelToJson(GalaxyNodeModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'parent_id': instance.parentId,
      'name': instance.name,
      'importance': instance.importance,
      'sector': _$SectorEnumEnumMap[instance.sector]!,
      'base_color': instance.baseColor,
      'is_unlocked': instance.isUnlocked,
      'mastery_score': instance.masteryScore,
      'tags': instance.tags,
      'description': instance.description,
      'position_hint': instance.positionHint,
      'outgoing_edge_ids': instance.outgoingEdgeIds,
      'incoming_edge_ids': instance.incomingEdgeIds,
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

GalaxyGraphResponse _$GalaxyGraphResponseFromJson(Map<String, dynamic> json) =>
    GalaxyGraphResponse(
      nodes: (json['nodes'] as List<dynamic>)
          .map((e) => GalaxyNodeModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      edges: (json['edges'] as List<dynamic>?)
              ?.map((e) => GalaxyEdgeModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      userFlameIntensity: (json['user_flame_intensity'] as num).toDouble(),
    );

Map<String, dynamic> _$GalaxyGraphResponseToJson(
        GalaxyGraphResponse instance) =>
    <String, dynamic>{
      'nodes': instance.nodes,
      'edges': instance.edges,
      'user_flame_intensity': instance.userFlameIntensity,
    };
