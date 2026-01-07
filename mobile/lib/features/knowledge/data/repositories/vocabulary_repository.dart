import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';

class VocabularyRepository {
  VocabularyRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<Map<String, dynamic>> lookup(String word) async {
    final response = await _apiClient.get<dynamic>(
      '/vocabulary/lookup',
      queryParameters: {'word': word},
    );
    return response.data as Map<String, dynamic>;
  }

  Future<void> addToWordbook(Map<String, dynamic> data) async {
    await _apiClient.post<dynamic>('/vocabulary/wordbook', data: data);
  }

  Future<List<dynamic>> getReviewList() async {
    final response =
        await _apiClient.get<dynamic>('/vocabulary/wordbook/review');
    return response.data as List<dynamic>;
  }

  Future<void> recordReview(String wordId, bool success) async {
    await _apiClient.post<dynamic>(
      '/vocabulary/wordbook/review',
      data: {
        'word_id': wordId,
        'success': success,
      },
    );
  }

  // LLM Methods
  Future<List<String>> getAssociations(String word) async {
    final response = await _apiClient.get<dynamic>(
      '/vocabulary/llm/associate',
      queryParameters: {'word': word},
    );
    final data = response.data as Map<String, dynamic>;
    final associations = data['associations'] as List<dynamic>?;
    return List<String>.from(associations ?? const []);
  }

  Future<String> generateSentence(String word, {String? context}) async {
    final response = await _apiClient.get<dynamic>(
      '/vocabulary/llm/sentence',
      queryParameters: {
        'word': word,
        if (context != null) 'context': context,
      },
    );
    final data = response.data as Map<String, dynamic>;
    return data['sentence'] as String;
  }
}

final vocabularyRepositoryProvider = Provider<VocabularyRepository>(
    (ref) => VocabularyRepository(ref.watch(apiClientProvider)),);
