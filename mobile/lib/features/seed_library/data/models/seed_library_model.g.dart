// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'seed_library_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

SeedAdoptionAction _$SeedAdoptionActionFromJson(Map<String, dynamic> json) =>
    SeedAdoptionAction(
      actionType: json['action_type'] as String,
      label: json['label'] as String,
      resourceType: json['resource_type'] as String,
      description: json['description'] as String?,
      resourceId: json['resource_id'] as String?,
      route: json['route'] as String?,
      payload:
          json['payload'] as Map<String, dynamic>? ?? const <String, dynamic>{},
    );

Map<String, dynamic> _$SeedAdoptionActionToJson(SeedAdoptionAction instance) =>
    <String, dynamic>{
      'action_type': instance.actionType,
      'label': instance.label,
      'description': instance.description,
      'resource_type': instance.resourceType,
      'resource_id': instance.resourceId,
      'route': instance.route,
      'payload': instance.payload,
    };

SeedLibrary _$SeedLibraryFromJson(Map<String, dynamic> json) => SeedLibrary(
      id: json['id'] as String,
      name: json['name'] as String,
      category: $enumDecode(_$LibraryCategoryEnumMap, json['category']),
      visibility: $enumDecode(_$LibraryVisibilityEnumMap, json['visibility']),
      language: json['language'] as String,
      isOfficial: json['is_official'] as bool,
      isFeatured: json['is_featured'] as bool,
      usageCount: (json['usage_count'] as num).toInt(),
      itemCount: (json['item_count'] as num).toInt(),
      subscriberCount: (json['subscriber_count'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      description: json['description'] as String?,
      ownerId: json['owner_id'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      extraMetadata: json['extra_metadata'] as Map<String, dynamic>?,
      qualityScore: (json['quality_score'] as num?)?.toDouble(),
      systemQualityScore: (json['system_quality_score'] as num?)?.toDouble(),
      userRatingAvg: (json['user_rating_avg'] as num?)?.toDouble(),
      userRatingCount: (json['user_rating_count'] as num?)?.toInt(),
      currentUserRating: (json['current_user_rating'] as num?)?.toDouble(),
      adoptionNextActions: (json['adoption_next_actions'] as List<dynamic>?)
              ?.map(
                  (e) => SeedAdoptionAction.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const <SeedAdoptionAction>[],
    );

Map<String, dynamic> _$SeedLibraryToJson(SeedLibrary instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'description': instance.description,
      'category': _$LibraryCategoryEnumMap[instance.category]!,
      'visibility': _$LibraryVisibilityEnumMap[instance.visibility]!,
      'owner_id': instance.ownerId,
      'language': instance.language,
      'tags': instance.tags,
      'extra_metadata': instance.extraMetadata,
      'is_official': instance.isOfficial,
      'is_featured': instance.isFeatured,
      'usage_count': instance.usageCount,
      'quality_score': instance.qualityScore,
      'system_quality_score': instance.systemQualityScore,
      'user_rating_avg': instance.userRatingAvg,
      'user_rating_count': instance.userRatingCount,
      'current_user_rating': instance.currentUserRating,
      'adoption_next_actions':
          instance.adoptionNextActions.map((e) => e.toJson()).toList(),
      'item_count': instance.itemCount,
      'subscriber_count': instance.subscriberCount,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

const _$LibraryCategoryEnumMap = {
  LibraryCategory.fewShot: 'few_shot',
  LibraryCategory.teachingContent: 'teaching_content',
  LibraryCategory.replyTemplate: 'reply_template',
  LibraryCategory.custom: 'custom',
};

const _$LibraryVisibilityEnumMap = {
  LibraryVisibility.private: 'private',
  LibraryVisibility.public: 'public',
  LibraryVisibility.official: 'official',
};

SeedItem _$SeedItemFromJson(Map<String, dynamic> json) => SeedItem(
      id: json['id'] as String,
      libraryId: json['library_id'] as String,
      itemType: $enumDecode(_$ItemTypeEnumMap, json['item_type']),
      isActive: json['is_active'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      title: json['title'] as String?,
      content: json['content'] as String?,
      contentData: json['content_data'] as Map<String, dynamic>?,
      subject: json['subject'] as String?,
      difficultyLevel: $enumDecodeNullable(
          _$DifficultyLevelEnumMap, json['difficulty_level']),
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      orderIndex: (json['order_index'] as num?)?.toInt(),
      adoptionNextActions: (json['adoption_next_actions'] as List<dynamic>?)
              ?.map(
                  (e) => SeedAdoptionAction.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const <SeedAdoptionAction>[],
    );

Map<String, dynamic> _$SeedItemToJson(SeedItem instance) => <String, dynamic>{
      'id': instance.id,
      'library_id': instance.libraryId,
      'item_type': _$ItemTypeEnumMap[instance.itemType]!,
      'title': instance.title,
      'content': instance.content,
      'content_data': instance.contentData,
      'subject': instance.subject,
      'difficulty_level': _$DifficultyLevelEnumMap[instance.difficultyLevel],
      'tags': instance.tags,
      'order_index': instance.orderIndex,
      'adoption_next_actions':
          instance.adoptionNextActions.map((e) => e.toJson()).toList(),
      'is_active': instance.isActive,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

const _$ItemTypeEnumMap = {
  ItemType.example: 'example',
  ItemType.exercise: 'exercise',
  ItemType.knowledge: 'knowledge',
  ItemType.template: 'template',
  ItemType.flashcard: 'flashcard',
};

const _$DifficultyLevelEnumMap = {
  DifficultyLevel.beginner: 'beginner',
  DifficultyLevel.intermediate: 'intermediate',
  DifficultyLevel.advanced: 'advanced',
  DifficultyLevel.expert: 'expert',
};

UserLibrarySubscription _$UserLibrarySubscriptionFromJson(
        Map<String, dynamic> json) =>
    UserLibrarySubscription(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      libraryId: json['library_id'] as String,
      isEnabled: json['is_enabled'] as bool,
      priority: (json['priority'] as num).toInt(),
      subscribedAt: DateTime.parse(json['subscribed_at'] as String),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      notes: json['notes'] as String?,
      lastUsedAt: json['last_used_at'] == null
          ? null
          : DateTime.parse(json['last_used_at'] as String),
      adoptionNextActions: (json['adoption_next_actions'] as List<dynamic>?)
              ?.map(
                  (e) => SeedAdoptionAction.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const <SeedAdoptionAction>[],
      communityShare: json['community_share'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$UserLibrarySubscriptionToJson(
        UserLibrarySubscription instance) =>
    <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'library_id': instance.libraryId,
      'is_enabled': instance.isEnabled,
      'priority': instance.priority,
      'notes': instance.notes,
      'subscribed_at': instance.subscribedAt.toIso8601String(),
      'last_used_at': instance.lastUsedAt?.toIso8601String(),
      'adoption_next_actions':
          instance.adoptionNextActions.map((e) => e.toJson()).toList(),
      'community_share': instance.communityShare,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

UpdateSubscriptionRequest _$UpdateSubscriptionRequestFromJson(
        Map<String, dynamic> json) =>
    UpdateSubscriptionRequest(
      isEnabled: json['is_enabled'] as bool?,
      priority: (json['priority'] as num?)?.toInt(),
      notes: json['notes'] as String?,
    );

Map<String, dynamic> _$UpdateSubscriptionRequestToJson(
        UpdateSubscriptionRequest instance) =>
    <String, dynamic>{
      'is_enabled': instance.isEnabled,
      'priority': instance.priority,
      'notes': instance.notes,
    };

RateLibraryRequest _$RateLibraryRequestFromJson(Map<String, dynamic> json) =>
    RateLibraryRequest(
      score: (json['score'] as num).toDouble(),
      comment: json['comment'] as String?,
    );

Map<String, dynamic> _$RateLibraryRequestToJson(RateLibraryRequest instance) =>
    <String, dynamic>{
      'score': instance.score,
      'comment': instance.comment,
    };

PaginatedResponse<T> _$PaginatedResponseFromJson<T>(
  Map<String, dynamic> json,
  T Function(Object? json) fromJsonT,
) =>
    PaginatedResponse<T>(
      items: (json['items'] as List<dynamic>).map(fromJsonT).toList(),
      total: (json['total'] as num).toInt(),
      page: (json['page'] as num).toInt(),
      pageSize: (json['pageSize'] as num).toInt(),
      totalPages: (json['total_pages'] as num).toInt(),
    );

Map<String, dynamic> _$PaginatedResponseToJson<T>(
  PaginatedResponse<T> instance,
  Object? Function(T value) toJsonT,
) =>
    <String, dynamic>{
      'items': instance.items.map(toJsonT).toList(),
      'total': instance.total,
      'page': instance.page,
      'pageSize': instance.pageSize,
      'total_pages': instance.totalPages,
    };

CreateLibraryRequest _$CreateLibraryRequestFromJson(
        Map<String, dynamic> json) =>
    CreateLibraryRequest(
      name: json['name'] as String,
      category: $enumDecode(_$LibraryCategoryEnumMap, json['category']),
      visibility: $enumDecode(_$LibraryVisibilityEnumMap, json['visibility']),
      description: json['description'] as String?,
      language: json['language'] as String? ?? 'zh',
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      extraMetadata: json['extra_metadata'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$CreateLibraryRequestToJson(
        CreateLibraryRequest instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'category': _$LibraryCategoryEnumMap[instance.category]!,
      'visibility': _$LibraryVisibilityEnumMap[instance.visibility]!,
      'language': instance.language,
      'tags': instance.tags,
      'extra_metadata': instance.extraMetadata,
    };

UpdateLibraryRequest _$UpdateLibraryRequestFromJson(
        Map<String, dynamic> json) =>
    UpdateLibraryRequest(
      name: json['name'] as String?,
      description: json['description'] as String?,
      category: $enumDecodeNullable(_$LibraryCategoryEnumMap, json['category']),
      visibility:
          $enumDecodeNullable(_$LibraryVisibilityEnumMap, json['visibility']),
      language: json['language'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      extraMetadata: json['extra_metadata'] as Map<String, dynamic>?,
      qualityScore: (json['quality_score'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$UpdateLibraryRequestToJson(
        UpdateLibraryRequest instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'category': _$LibraryCategoryEnumMap[instance.category],
      'visibility': _$LibraryVisibilityEnumMap[instance.visibility],
      'language': instance.language,
      'tags': instance.tags,
      'extra_metadata': instance.extraMetadata,
      'quality_score': instance.qualityScore,
    };
