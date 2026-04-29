/// Seed Library Data Models
/// 种子库数据模型
library;

import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/l10n/app_localizations.dart';

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
  String label(AppLocalizations l10n) => switch (this) {
    LibraryCategory.fewShot => l10n.seedCatFewShot,
    LibraryCategory.teachingContent => l10n.seedCatTeaching,
    LibraryCategory.replyTemplate => l10n.seedCatReplyTemplate,
    LibraryCategory.custom => l10n.seedCatCustom,
  };
}

extension LibraryVisibilityExtension on LibraryVisibility {
  String label(AppLocalizations l10n) => switch (this) {
    LibraryVisibility.private => l10n.seedVisPrivate,
    LibraryVisibility.public => l10n.seedVisPublic,
    LibraryVisibility.official => l10n.seedVisOfficial,
  };
}

extension ItemTypeExtension on ItemType {
  String label(AppLocalizations l10n) => switch (this) {
    ItemType.example => l10n.seedTypeExample,
    ItemType.exercise => l10n.seedTypeExercise,
    ItemType.knowledge => l10n.seedTypeKnowledge,
    ItemType.template => l10n.seedTypeTemplate,
    ItemType.flashcard => l10n.seedTypeFlashcard,
  };
}

extension DifficultyLevelExtension on DifficultyLevel {
  String label(AppLocalizations l10n) => switch (this) {
    DifficultyLevel.beginner => l10n.seedDiffBeginner,
    DifficultyLevel.intermediate => l10n.seedDiffIntermediate,
    DifficultyLevel.advanced => l10n.seedDiffAdvanced,
    DifficultyLevel.expert => l10n.seedDiffExpert,
  };
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
    this.systemQualityScore,
    this.userRatingAvg,
    this.userRatingCount,
    this.currentUserRating,
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
  @JsonKey(name: 'system_quality_score')
  final double? systemQualityScore;
  @JsonKey(name: 'user_rating_avg')
  final double? userRatingAvg;
  @JsonKey(name: 'user_rating_count')
  final int? userRatingCount;
  @JsonKey(name: 'current_user_rating')
  final double? currentUserRating;
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

  String categoryLabel(AppLocalizations l10n) => switch (category) {
    LibraryCategory.fewShot => l10n.seedCatFewShotFull,
    LibraryCategory.teachingContent => l10n.seedCatTeaching,
    LibraryCategory.replyTemplate => l10n.seedCatReplyTemplate,
    LibraryCategory.custom => l10n.seedCatCustom,
  };

  String visibilityLabel(AppLocalizations l10n) => visibility.label(l10n);

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
    double? systemQualityScore,
    double? userRatingAvg,
    int? userRatingCount,
    double? currentUserRating,
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
      systemQualityScore: systemQualityScore ?? this.systemQualityScore,
      userRatingAvg: userRatingAvg ?? this.userRatingAvg,
      userRatingCount: userRatingCount ?? this.userRatingCount,
      currentUserRating: currentUserRating ?? this.currentUserRating,
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

  String itemTypeLabel(AppLocalizations l10n) => itemType.label(l10n);

  String? difficultyLevelLabel(AppLocalizations l10n) =>
      difficultyLevel?.label(l10n);

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

@JsonSerializable()
class UpdateSubscriptionRequest {
  UpdateSubscriptionRequest({
    this.isEnabled,
    this.priority,
    this.notes,
  });

  factory UpdateSubscriptionRequest.fromJson(Map<String, dynamic> json) =>
      _$UpdateSubscriptionRequestFromJson(json);

  @JsonKey(name: 'is_enabled')
  final bool? isEnabled;
  final int? priority;
  final String? notes;

  Map<String, dynamic> toJson() => _$UpdateSubscriptionRequestToJson(this);
}

@JsonSerializable()
class RateLibraryRequest {
  RateLibraryRequest({
    required this.score,
    this.comment,
  });

  factory RateLibraryRequest.fromJson(Map<String, dynamic> json) =>
      _$RateLibraryRequestFromJson(json);

  final double score;
  final String? comment;

  Map<String, dynamic> toJson() => _$RateLibraryRequestToJson(this);
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
