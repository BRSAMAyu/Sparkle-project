// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'galaxy_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

GalaxyNodeModel _$GalaxyNodeModelFromJson(Map<String, dynamic> json) =>
    GalaxyNodeModel(
      id: json['id'] as String,
      parentId: json['parent_id'] as String?,
      name: json['name'] as String,
      importance: (json['importance'] as num).toInt(),
      sector: $enumDecode(_$SectorEnumEnumMap, json['sector']),
      baseColor: json['base_color'] as String?,
      isUnlocked: json['is_unlocked'] as bool,
      masteryScore: (json['mastery_score'] as num).toInt(),
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
    };

const _$SectorEnumEnumMap = {
  SectorEnum.COSMOS: 'COSMOS',
  SectorEnum.TECH: 'TECH',
  SectorEnum.ART: 'ART',
  SectorEnum.CIVILIZATION: 'CIVILIZATION',
  SectorEnum.LIFE: 'LIFE',
  SectorEnum.WISDOM: 'WISDOM',
  SectorEnum.VOID: 'VOID',
};

GalaxyGraphResponse _$GalaxyGraphResponseFromJson(Map<String, dynamic> json) =>
    GalaxyGraphResponse(
      nodes: (json['nodes'] as List<dynamic>)
          .map((e) => GalaxyNodeModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      userFlameIntensity: (json['user_flame_intensity'] as num).toDouble(),
    );

Map<String, dynamic> _$GalaxyGraphResponseToJson(
        GalaxyGraphResponse instance) =>
    <String, dynamic>{
      'nodes': instance.nodes,
      'user_flame_intensity': instance.userFlameIntensity,
    };
