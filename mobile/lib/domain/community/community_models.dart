import 'package:freezed_annotation/freezed_annotation.dart';

part 'community_models.freezed.dart';
part 'community_models.g.dart';

@freezed
class PostUser with _$PostUser {
  const factory PostUser({
    required String id,
    required String username,
    @JsonKey(name: 'avatar_url') String? avatarUrl,
  }) = _PostUser;

  factory PostUser.fromJson(Map<String, dynamic> json) => _$PostUserFromJson(json);
}

@freezed
class Post with _$Post {
  const factory Post({
    required String id,
    @JsonKey(name: 'user_id') required String userId,
    required String content,
    @JsonKey(name: 'created_at') required DateTime createdAt, required PostUser user, @JsonKey(name: 'image_urls') List<String>? imageUrls,
    String? topic,
    @JsonKey(name: 'like_count') @Default(0) int likeCount,
    @Default(false) bool isOptimistic, // For optimistic UI
  }) = _Post;

  factory Post.fromJson(Map<String, dynamic> json) => _$PostFromJson(json);
}

@freezed
class CreatePostRequest with _$CreatePostRequest {
  const factory CreatePostRequest({
    @JsonKey(name: 'user_id') required String userId,
    required String content,
    @JsonKey(name: 'image_urls') List<String>? imageUrls,
    String? topic,
  }) = _CreatePostRequest;

  factory CreatePostRequest.fromJson(Map<String, dynamic> json) => _$CreatePostRequestFromJson(json);
}
