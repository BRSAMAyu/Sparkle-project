import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';

/// 错题记录仓库
class ErrorRepository {

  ErrorRepository(this._apiClient);
  final ApiClient _apiClient;

  /// 创建错题记录
  Future<Map<String, dynamic>> createError({
    required int subjectId,
    required String topic,
    required String errorType,
    required String description,
    String? aiAnalysis,
    List<String>? imageUrls,
  }) async {
    final response = await _apiClient.post('/errors', data: {
      'subject_id': subjectId,
      'topic': topic,
      'error_type': errorType,
      'description': description,
      if (aiAnalysis != null) 'ai_analysis': aiAnalysis,
      if (imageUrls != null && imageUrls.isNotEmpty) 'image_urls': imageUrls,
    },);
    return response.data;
  }

  /// 获取科目列表
  Future<List<Map<String, dynamic>>> getSubjects() async {
    final response = await _apiClient.get('/subjects');
    final data = response.data;
    if (data is List) {
      return data.cast<Map<String, dynamic>>();
    } else if (data is Map && data.containsKey('data')) {
      return (data['data'] as List).cast<Map<String, dynamic>>();
    }
    return [];
  }
}

final errorRepositoryProvider = Provider<ErrorRepository>((ref) => ErrorRepository(ref.watch(apiClientProvider)));
