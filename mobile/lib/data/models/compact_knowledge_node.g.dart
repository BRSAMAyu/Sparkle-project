// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'compact_knowledge_node.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CompactKnowledgeNode _$CompactKnowledgeNodeFromJson(
        Map<String, dynamic> json) =>
    CompactKnowledgeNode(
      id: json['id'] as String,
      name: json['name'] as String,
      x: (json['x'] as num).toDouble(),
      y: (json['y'] as num).toDouble(),
      radius: (json['radius'] as num).toDouble(),
      color: (json['color'] as num).toInt(),
      status: (json['status'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$CompactKnowledgeNodeToJson(
        CompactKnowledgeNode instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'x': instance.x,
      'y': instance.y,
      'radius': instance.radius,
      'color': instance.color,
      'status': instance.status,
    };
