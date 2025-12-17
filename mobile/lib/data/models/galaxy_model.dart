import 'package:json_annotation/json_annotation.dart';

part 'galaxy_model.g.dart';

enum SectorEnum {
  COSMOS, TECH, ART, CIVILIZATION, LIFE, WISDOM, VOID
}

@JsonSerializable()
class GalaxyNodeModel {
  final String id;
  @JsonKey(name: 'parent_id')
  final String? parentId;
  final String name;
  final int importance; // importance_level mapped to importance
  final SectorEnum sector;
  @JsonKey(name: 'base_color')
  final String? baseColor;
  
  @JsonKey(name: 'is_unlocked')
  final bool isUnlocked;
  @JsonKey(name: 'mastery_score')
  final int masteryScore;

  GalaxyNodeModel({
    required this.id,
    required this.name, required this.importance, required this.sector, required this.isUnlocked, required this.masteryScore, this.parentId,
    this.baseColor,
  });

  factory GalaxyNodeModel.fromJson(Map<String, dynamic> json) => _$GalaxyNodeModelFromJson(json);
  Map<String, dynamic> toJson() => _$GalaxyNodeModelToJson(this);
}

@JsonSerializable()
class GalaxyGraphResponse {
  final List<GalaxyNodeModel> nodes;
  @JsonKey(name: 'user_flame_intensity')
  final double userFlameIntensity;

  GalaxyGraphResponse({
    required this.nodes,
    required this.userFlameIntensity,
  });

  factory GalaxyGraphResponse.fromJson(Map<String, dynamic> json) => _$GalaxyGraphResponseFromJson(json);
  Map<String, dynamic> toJson() => _$GalaxyGraphResponseToJson(this);
}
