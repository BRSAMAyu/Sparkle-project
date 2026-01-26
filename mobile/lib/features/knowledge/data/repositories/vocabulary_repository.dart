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

  Future<void> addToWordbook({
    required String word,
    required String definition,
    String? phonetic,
    String? contextSentence,
    String? taskId,
    int importance = 3,
    String? partOfSpeech,
    String? sourceTranslationId,
  }) async {
    await _apiClient.post<dynamic>('/vocabulary/wordbook', data: {
      'word': word,
      'definition': definition,
      if (phonetic != null) 'phonetic': phonetic,
      if (contextSentence != null) 'context_sentence': contextSentence,
      if (taskId != null) 'task_id': taskId,
      'importance': importance,
      if (partOfSpeech != null) 'part_of_speech': partOfSpeech,
      if (sourceTranslationId != null) 'source_translation_id': sourceTranslationId,
    },);
  }

  /// 新增：添加生词到生词本（使用 Map 参数，向后兼容）
  Future<void> addToWordbookLegacy(Map<String, dynamic> data) async {
    await _apiClient.post<dynamic>('/vocabulary/wordbook', data: data);
  }

  Future<List<dynamic>> getReviewList() async {
    final response =
        await _apiClient.get<dynamic>('/vocabulary/wordbook/review');
    return response.data as List<dynamic>;
  }

  Future<void> recordReview(String wordId, bool remembered) async {
    await _apiClient.post<dynamic>(
      '/vocabulary/wordbook/review',
      data: {
        'word_id': wordId,
        'remembered': remembered,
      },
    );
  }

  /// 新增：更新单词重要度
  Future<void> updateImportance(String wordId, int importance) async {
    if (importance < 1 || importance > 5) {
      throw ArgumentError('Importance must be between 1 and 5');
    }
    await _apiClient.patch<dynamic>(
      '/vocabulary/wordbook/$wordId/importance',
      data: {'importance': importance},
    );
  }

  /// 新增：获取词汇统计
  Future<Map<String, dynamic>> getStats() async {
    final response = await _apiClient.get<dynamic>('/vocabulary/wordbook/stats');
    return response.data as Map<String, dynamic>;
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
