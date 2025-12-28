import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/domain/community/community_models.dart';

final communityRepositoryProvider = Provider((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CommunityRepository(apiClient);
});

class CommunityRepository {

  CommunityRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<List<Post>> getFeed({int page = 1, int limit = 20}) async {
    final response = await _apiClient.get(
      '/api/v1/community/feed',
      queryParameters: {'page': page, 'limit': limit},
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = response.data;
      return data.map((e) => Post.fromJson(e)).toList();
    } else {
      throw Exception('Failed to load feed');
    }
  }

  Future<String> createPost(CreatePostRequest request) async {
    final response = await _apiClient.post(
      '/api/v1/community/posts',
      data: request.toJson(),
    );

    if (response.statusCode == 201) {
      return response.data['id'];
    } else {
      throw Exception('Failed to create post');
    }
  }

  Future<void> likePost(String postId, String userId) async {
    await _apiClient.post(
      '/api/v1/community/posts/$postId/like',
      data: {'user_id': userId},
    );
  }
}