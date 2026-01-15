import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';

/// Translation service provider
final translationServiceProvider = Provider<TranslationService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return TranslationService(apiClient);
});

/// Translation segment data
class TranslationSegmentData {
  final String id;
  final String translation;
  final List<String> notes;

  TranslationSegmentData({
    required this.id,
    required this.translation,
    required this.notes,
  });

  factory TranslationSegmentData.fromJson(Map<String, dynamic> json) {
    return TranslationSegmentData(
      id: json['id'] as String,
      translation: json['translation'] as String,
      notes: (json['notes'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
    );
  }
}

/// Translation result
class TranslationResult {
  final bool success;
  final String translation;
  final List<TranslationSegmentData> segments;
  final Map<String, dynamic> meta;

  TranslationResult({
    required this.success,
    required this.translation,
    required this.segments,
    required this.meta,
  });

  factory TranslationResult.fromJson(Map<String, dynamic> json) {
    return TranslationResult(
      success: json['success'] as bool,
      translation: json['translation'] as String,
      segments: (json['segments'] as List<dynamic>)
          .map((e) => TranslationSegmentData.fromJson(e as Map<String, dynamic>))
          .toList(),
      meta: json['meta'] as Map<String, dynamic>,
    );
  }

  /// Check if result was from cache
  bool get isCacheHit => meta['cache_hit'] == true;

  /// Get provider name
  String get provider => meta['provider'] as String? ?? 'unknown';

  /// Get latency in milliseconds
  int get latencyMs => meta['latency_ms'] as int? ?? 0;

  /// Get source language
  String get sourceLang => meta['source_lang'] as String? ?? 'en';

  /// Get target language
  String get targetLang => meta['target_lang'] as String? ?? 'zh-CN';
}

/// Translation service for API calls
class TranslationService {
  final ApiClient _apiClient;

  TranslationService(this._apiClient);

  /// Translate text from one language to another
  ///
  /// [text] - Text to translate
  /// [sourceLang] - Source language code (default: 'en')
  /// [targetLang] - Target language code (default: 'zh-CN')
  /// [domain] - Domain for terminology: 'cs', 'math', 'business', 'general'
  /// [style] - Translation style: 'concise', 'literal', 'natural'
  /// [glossaryId] - Optional glossary ID for terminology consistency
  Future<TranslationResult> translate({
    required String text,
    String sourceLang = 'en',
    String targetLang = 'zh-CN',
    String domain = 'general',
    String style = 'natural',
    String? glossaryId,
  }) async {
    final response = await _apiClient.post(
      '/translation/translate',
      data: {
        'text': text,
        'source_lang': sourceLang,
        'target_lang': targetLang,
        'domain': domain,
        'style': style,
        if (glossaryId != null) 'glossary_id': glossaryId,
      },
    );

    return TranslationResult.fromJson(response.data as Map<String, dynamic>);
  }

  /// Get available glossaries
  Future<List<Map<String, dynamic>>> getGlossaries() async {
    final response = await _apiClient.get('/translation/glossaries');
    final data = response.data as Map<String, dynamic>;
    return (data['glossaries'] as List<dynamic>)
        .map((e) => e as Map<String, dynamic>)
        .toList();
  }
}
