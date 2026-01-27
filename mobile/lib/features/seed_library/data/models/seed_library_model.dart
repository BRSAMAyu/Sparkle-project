/// Seed Library Data Models
/// 种子库数据模型
library;

import 'package:json_annotation/json_annotation.dart';

part 'seed_library_model.g.dart';

/// Library category enumeration
enum LibraryCategory {
  @JsonValue('few_shot')
  fewShot,
  @JsonValue('teaching_content')
  teachingContent,
  @JsonValue('reply_template')
  replyTemplate,
  @JsonValue('custom')
  custom,
}

/// Library visibility enumeration
enum LibraryVisibility {
  @JsonValue('private')
  private,
  @JsonValue('public')
  public,
  @JsonValue('official')
  official,
}

/// Item type enumeration
enum ItemType {
  @JsonValue('example')
  example,
  @JsonValue('exercise')
  exercise,
  @JsonValue('knowledge')
  knowledge,
  @JsonValue('template')
  template,
  @JsonValue('flashcard')
  flashcard,
}

/// Difficulty level enumeration
enum DifficultyLevel {
  @JsonValue('beginner')
  beginner,
  @JsonValue('intermediate')
  intermediate,
  @JsonValue('advanced')
  advanced,
  @JsonValue('expert')
  expert,
}

/// Extensions for enumerations
extension LibraryCategoryExtension on LibraryCategory {
  String get displayName {
    switch (this) {
      case LibraryCategory.fewShot:
        return 'Few Shot';
      case LibraryCategory.teachingContent:
        return '教学内容';
      case LibraryCategory.replyTemplate:
        return '回复模板';
      case LibraryCategory.custom:
        return '自定义';
    }
  }
}

extension LibraryVisibilityExtension on LibraryVisibility {
  String get displayName {
    switch (this) {
      case LibraryVisibility.private:
        return '私有';
      case LibraryVisibility.public:
        return '公开';
      case LibraryVisibility.official:
        return '官方';
    }
  }
}

extension ItemTypeExtension on ItemType {
  String get displayName {
    switch (this) {
      case ItemType.example:
        return '示例';
      case ItemType.exercise:
        return '练习';
      case ItemType.knowledge:
        return '知识点';
      case ItemType.template:
        return '模板';
      case ItemType.flashcard:
        return '闪卡';
    }
  }
}

extension DifficultyLevelExtension on DifficultyLevel {
  String get displayName {
    switch (this) {
      case DifficultyLevel.beginner:
        return '初级';
      case DifficultyLevel.intermediate:
        return '中级';
      case DifficultyLevel.advanced:
        return '高级';
      case DifficultyLevel.expert:
        return '专家';
    }
  }
}

/// Seed Library model
@JsonSerializable()
class SeedLibrary {

  SeedLibrary({
    required this.id,
    required this.name,
    required this.category, required this.visibility, required this.language, required this.isOfficial, required this.isFeatured, required this.usageCount, required this.itemCount, required this.subscriberCount, required this.createdAt, required this.updatedAt, this.description,
    this.ownerId,
    this.tags,
    this.extraMetadata,
    this.qualityScore,
    this.isSubscribed,
    this.subscriptionPriority,
  });

  factory SeedLibrary.fromJson(Map<String, dynamic> json) =>
      _$SeedLibraryFromJson(json);
  final String id;
  final String name;
  final String? description;
  @JsonKey(name: 'category')
  final LibraryCategory category;
  @JsonKey(name: 'visibility')
  final LibraryVisibility visibility;
  @JsonKey(name: 'owner_id')
  final String? ownerId;
  final String language;
  final List<String>? tags;
  @JsonKey(name: 'extra_metadata')
  final Map<String, dynamic>? extraMetadata;
  @JsonKey(name: 'is_official')
  final bool isOfficial;
  @JsonKey(name: 'is_featured')
  final bool isFeatured;
  @JsonKey(name: 'usage_count')
  final int usageCount;
  @JsonKey(name: 'quality_score')
  final double? qualityScore;
  @JsonKey(name: 'item_count')
  final int itemCount;
  @JsonKey(name: 'subscriber_count')
  final int subscriberCount;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  // Non-API fields
  @JsonKey(includeFromJson: false, includeToJson: false)
  bool? isSubscribed;
  @JsonKey(includeFromJson: false, includeToJson: false)
  int? subscriptionPriority;

  Map<String, dynamic> toJson() => _$SeedLibraryToJson(this);

  /// Get display name for category
  String get categoryDisplayName {
    switch (category) {
      case LibraryCategory.fewShot:
        return 'Few-shot示例';
      case LibraryCategory.teachingContent:
        return '教学内容';
      case LibraryCategory.replyTemplate:
        return '回复模板';
      case LibraryCategory.custom:
        return '自定义';
    }
  }

  /// Get display name for visibility
  String get visibilityDisplayName {
    switch (visibility) {
      case LibraryVisibility.private:
        return '私有';
      case LibraryVisibility.public:
        return '公开';
      case LibraryVisibility.official:
        return '官方';
    }
  }

  /// Check if library is editable by user
  bool get isEditable =>
      visibility == LibraryVisibility.public ||
      visibility == LibraryVisibility.private;

  SeedLibrary copyWith({
    String? id,
    String? name,
    String? description,
    LibraryCategory? category,
    LibraryVisibility? visibility,
    String? ownerId,
    String? language,
    List<String>? tags,
    Map<String, dynamic>? extraMetadata,
    bool? isOfficial,
    bool? isFeatured,
    int? usageCount,
    double? qualityScore,
    int? itemCount,
    int? subscriberCount,
    DateTime? createdAt,
    DateTime? updatedAt,
    bool? isSubscribed,
    int? subscriptionPriority,
  }) => SeedLibrary(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      category: category ?? this.category,
      visibility: visibility ?? this.visibility,
      ownerId: ownerId ?? this.ownerId,
      language: language ?? this.language,
      tags: tags ?? this.tags,
      extraMetadata: extraMetadata ?? this.extraMetadata,
      isOfficial: isOfficial ?? this.isOfficial,
      isFeatured: isFeatured ?? this.isFeatured,
      usageCount: usageCount ?? this.usageCount,
      qualityScore: qualityScore ?? this.qualityScore,
      itemCount: itemCount ?? this.itemCount,
      subscriberCount: subscriberCount ?? this.subscriberCount,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      isSubscribed: isSubscribed ?? this.isSubscribed,
      subscriptionPriority: subscriptionPriority ?? this.subscriptionPriority,
    );
}

/// Seed Item model
@JsonSerializable()
class SeedItem {

  SeedItem({
    required this.id,
    required this.libraryId,
    required this.itemType,
    required this.isActive, required this.createdAt, required this.updatedAt, this.title,
    this.content,
    this.contentData,
    this.subject,
    this.difficultyLevel,
    this.tags,
    this.orderIndex,
  });

  factory SeedItem.fromJson(Map<String, dynamic> json) =>
      _$SeedItemFromJson(json);
  final String id;
  @JsonKey(name: 'library_id')
  final String libraryId;
  @JsonKey(name: 'item_type')
  final ItemType itemType;
  final String? title;
  final String? content;
  @JsonKey(name: 'content_data')
  final Map<String, dynamic>? contentData;
  final String? subject;
  @JsonKey(name: 'difficulty_level')
  final DifficultyLevel? difficultyLevel;
  final List<String>? tags;
  @JsonKey(name: 'order_index')
  final int? orderIndex;
  @JsonKey(name: 'is_active')
  final bool isActive;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  Map<String, dynamic> toJson() => _$SeedItemToJson(this);

  /// Get display name for item type
  String get itemTypeDisplayName {
    switch (itemType) {
      case ItemType.example:
        return '示例';
      case ItemType.exercise:
        return '练习';
      case ItemType.knowledge:
        return '知识点';
      case ItemType.template:
        return '模板';
      case ItemType.flashcard:
        return '抽认卡';
    }
  }

  /// Get display name for difficulty level
  String? get difficultyLevelDisplayName {
    if (difficultyLevel == null) return null;
    switch (difficultyLevel!) {
      case DifficultyLevel.beginner:
        return '初级';
      case DifficultyLevel.intermediate:
        return '中级';
      case DifficultyLevel.advanced:
        return '高级';
      case DifficultyLevel.expert:
        return '专家';
    }
  }

  SeedItem copyWith({
    String? id,
    String? libraryId,
    ItemType? itemType,
    String? title,
    String? content,
    Map<String, dynamic>? contentData,
    String? subject,
    DifficultyLevel? difficultyLevel,
    List<String>? tags,
    int? orderIndex,
    bool? isActive,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) => SeedItem(
      id: id ?? this.id,
      libraryId: libraryId ?? this.libraryId,
      itemType: itemType ?? this.itemType,
      title: title ?? this.title,
      content: content ?? this.content,
      contentData: contentData ?? this.contentData,
      subject: subject ?? this.subject,
      difficultyLevel: difficultyLevel ?? this.difficultyLevel,
      tags: tags ?? this.tags,
      orderIndex: orderIndex ?? this.orderIndex,
      isActive: isActive ?? this.isActive,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
}

/// User Library Subscription model
@JsonSerializable()
class UserLibrarySubscription {

  UserLibrarySubscription({
    required this.id,
    required this.userId,
    required this.libraryId,
    required this.isEnabled,
    required this.priority,
    required this.subscribedAt, required this.createdAt, required this.updatedAt, this.notes,
    this.lastUsedAt,
    this.library,
  });

  factory UserLibrarySubscription.fromJson(Map<String, dynamic> json) =>
      _$UserLibrarySubscriptionFromJson(json);
  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'library_id')
  final String libraryId;
  @JsonKey(name: 'is_enabled')
  final bool isEnabled;
  final int priority;
  final String? notes;
  @JsonKey(name: 'subscribed_at')
  final DateTime subscribedAt;
  @JsonKey(name: 'last_used_at')
  final DateTime? lastUsedAt;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  // Expanded library data (non-API field)
  @JsonKey(includeFromJson: false, includeToJson: false)
  SeedLibrary? library;

  Map<String, dynamic> toJson() => _$UserLibrarySubscriptionToJson(this);

  UserLibrarySubscription copyWith({
    String? id,
    String? userId,
    String? libraryId,
    bool? isEnabled,
    int? priority,
    String? notes,
    DateTime? subscribedAt,
    DateTime? lastUsedAt,
    DateTime? createdAt,
    DateTime? updatedAt,
    SeedLibrary? library,
  }) => UserLibrarySubscription(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      libraryId: libraryId ?? this.libraryId,
      isEnabled: isEnabled ?? this.isEnabled,
      priority: priority ?? this.priority,
      notes: notes ?? this.notes,
      subscribedAt: subscribedAt ?? this.subscribedAt,
      lastUsedAt: lastUsedAt ?? this.lastUsedAt,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      library: library ?? this.library,
    );
}

/// Paginated response model
@JsonSerializable(genericArgumentFactories: true)
class PaginatedResponse<T> {

  PaginatedResponse({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
    required this.totalPages,
  });

  factory PaginatedResponse.fromJson(
    Map<String, dynamic> json,
    T Function(Object? json) fromJsonT,
  ) =>
      _$PaginatedResponseFromJson(json, fromJsonT);
  final List<T> items;
  final int total;
  final int page;
  final int pageSize;
  @JsonKey(name: 'total_pages')
  final int totalPages;

  Map<String, dynamic> toJson(Object? Function(T value) toJsonT) =>
      _$PaginatedResponseToJson(this, toJsonT);
}

/// Create library request model
@JsonSerializable()
class CreateLibraryRequest {

  CreateLibraryRequest({
    required this.name,
    required this.category, required this.visibility, this.description,
    this.language = 'zh',
    this.tags,
    this.extraMetadata,
  });

  factory CreateLibraryRequest.fromJson(Map<String, dynamic> json) =>
      _$CreateLibraryRequestFromJson(json);
  final String name;
  final String? description;
  final LibraryCategory category;
  final LibraryVisibility visibility;
  final String language;
  final List<String>? tags;
  @JsonKey(name: 'extra_metadata')
  final Map<String, dynamic>? extraMetadata;

  Map<String, dynamic> toJson() => _$CreateLibraryRequestToJson(this);
}

/// Update library request model
@JsonSerializable()
class UpdateLibraryRequest {

  UpdateLibraryRequest({
    this.name,
    this.description,
    this.category,
    this.visibility,
    this.language,
    this.tags,
    this.extraMetadata,
    this.qualityScore,
  });

  factory UpdateLibraryRequest.fromJson(Map<String, dynamic> json) =>
      _$UpdateLibraryRequestFromJson(json);
  final String? name;
  final String? description;
  final LibraryCategory? category;
  final LibraryVisibility? visibility;
  final String? language;
  final List<String>? tags;
  @JsonKey(name: 'extra_metadata')
  final Map<String, dynamic>? extraMetadata;
  @JsonKey(name: 'quality_score')
  final double? qualityScore;

  Map<String, dynamic> toJson() => _$UpdateLibraryRequestToJson(this);
}
