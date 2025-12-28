import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';

class VocabularyRepository {

  VocabularyRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<Map<String, dynamic>> lookup(String word) async {
    final response = await _apiClient.get(
      '/vocabulary/lookup',
      queryParameters: {'word': word},
    );
    return response.data;
  }

  Future<void> addToWordbook(Map<String, dynamic> data) async {
    await _apiClient.post('/vocabulary/wordbook', data: data);
  }

  Future<List<dynamic>> getReviewList() async {
    final response = await _apiClient.get('/vocabulary/wordbook/review');
    return response.data;
  }

  Future<void> recordReview(String wordId, bool success) async {
    await _apiClient.post('/vocabulary/wordbook/review', data: {
      'word_id': wordId,
      'success': success,
    },);
  }

  // LLM Methods
  Future<List<String>> getAssociations(String word) async {
    final response = await _apiClient.get(
      '/vocabulary/llm/associate',
      queryParameters: {'word': word},
    );
    return List<String>.from(response.data['associations']);
  }

  Future<String> generateSentence(String word, {String? context}) async {
    final response = await _apiClient.get(
      '/vocabulary/llm/sentence',
      queryParameters: {
        'word': word,
        if (context != null) 'context': context,
      },
    );
    return response.data['sentence'];
  }
}

final vocabularyRepositoryProvider = Provider<VocabularyRepository>((ref) => VocabularyRepository(ref.watch(apiClientProvider)));
