import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// Service for integrating translations into knowledge graph
class KnowledgeIntegrationService {
  KnowledgeIntegrationService(this._dio);

  final Dio _dio;

  /// Create vocabulary node from translation
  ///
  /// Sends translation to backend to create a knowledge node
  /// that will be scheduled for spaced repetition review immediately.
  /// Handles idempotency (if node exists, it updates context).
  ///
  /// Returns:
  /// - VocabularyNodeResult on success
  /// - null on error (check error type via exception)
  ///
  /// Throws:
  /// - ServiceUnavailableException on 503 (circuit breaker triggered)
  /// - NetworkException on network errors
  Future<VocabularyNodeResult?> createVocabularyNode({
    required String sourceText,
    required String translation,
    required String context,
    String? sourceUrl,
    String? sourceDocumentId,
    String language = 'en',
    String? domain,
    int? subjectId,
  }) async {
    try {
      debugPrint('📚 Creating vocabulary node: $sourceText → $translation');

      final response = await _dio.post(
        '/galaxy/vocabulary',
        data: {
          'source_text': sourceText,
          'translation': translation,
          'context': context,
          'source_url': sourceUrl,
          'source_document_id': sourceDocumentId,
          'language': language,
          'domain': domain,
          'subject_id': subjectId,
        },
      );

      if (response.statusCode == 200 && response.data['success'] == true) {
        debugPrint('✅ Vocabulary node created/updated: ${response.data['node_id']}');
        return VocabularyNodeResult.fromJson(response.data);
      } else {
        debugPrint('⚠️ Failed to create vocabulary node: ${response.data}');
        return null;
      }
    } on DioException catch (e) {
      // Handle specific error cases for better UX
      if (e.response?.statusCode == 503) {
        debugPrint('🚨 Service unavailable (circuit breaker): ${e.message}');
        throw ServiceUnavailableException(
          '服务繁忙，请稍后重试',
          originalError: e,
        );
      } else if (e.response?.statusCode == 429) {
        debugPrint('⚠️ Rate limited: ${e.message}');
        throw RateLimitException(
          '请求过于频繁，请稍后再试',
          retryAfter: _parseRetryAfter(e.response?.headers),
        );
      } else if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout) {
        debugPrint('⏱️ Timeout: ${e.message}');
        throw NetworkException(
          '网络连接超时，请检查网络',
          originalError: e,
        );
      } else {
        debugPrint('❌ Failed to create vocabulary node: $e');
        throw NetworkException(
          '保存失败，请重试',
          originalError: e,
        );
      }
    } catch (e) {
      debugPrint('❌ Unexpected error: $e');
      throw NetworkException(
        '未知错误，请重试',
        originalError: e,
      );
    }
  }

  int? _parseRetryAfter(Headers? headers) {
    try {
      final retryAfter = headers?.value('retry-after');
      if (retryAfter != null) {
        return int.tryParse(retryAfter);
      }
    } catch (_) {}
    return null;
  }

  /// Delete a draft node
  Future<bool> deleteDraftNode(String nodeId) async {
    try {
      debugPrint('🗑️ Deleting draft node: $nodeId');

      final response = await _dio.delete('/galaxy/node/$nodeId/draft');

      if (response.statusCode == 200 && response.data['success'] == true) {
        debugPrint('✅ Draft node deleted: $nodeId');
        return true;
      } else {
        debugPrint('⚠️ Failed to delete draft node: ${response.data}');
        return false;
      }
    } catch (e) {
      debugPrint('❌ Failed to delete draft node: $e');
      return false;
    }
  }

  /// Update node content before publishing
  Future<bool> updateNodeContent({
    required String nodeId,
    String? name,
    String? description,
    List<String>? keywords,
  }) async {
    try {
      debugPrint('✏️ Updating node content: $nodeId');

      final response = await _dio.patch(
        '/galaxy/node/$nodeId/content',
        data: {
          if (name != null) 'name': name,
          if (description != null) 'description': description,
          if (keywords != null) 'keywords': keywords,
        },
      );

      if (response.statusCode == 200 && response.data['success'] == true) {
        debugPrint('✅ Node content updated: $nodeId');
        return true;
      } else {
        debugPrint('⚠️ Failed to update node content: ${response.data}');
        return false;
      }
    } catch (e) {
      debugPrint('❌ Failed to update node content: $e');
      return false;
    }
  }
}

/// Result of vocabulary node creation
class VocabularyNodeResult {
  const VocabularyNodeResult({
    required this.success,
    required this.nodeId,
    required this.status,
    required this.message,
  });

  final bool success;
  final String nodeId;
  final String status;
  final String message;

  factory VocabularyNodeResult.fromJson(Map<String, dynamic> json) {
    return VocabularyNodeResult(
      success: json['success'] as bool,
      nodeId: json['node_id'] as String,
      status: json['status'] as String,
      message: json['message'] as String,
    );
  }
}

/// Exception thrown when service is unavailable (503)
/// Usually indicates circuit breaker is open
class ServiceUnavailableException implements Exception {
  const ServiceUnavailableException(this.message, {this.originalError});

  final String message;
  final Object? originalError;

  @override
  String toString() => message;
}

/// Exception thrown when rate limit is exceeded (429)
class RateLimitException implements Exception {
  const RateLimitException(this.message, {this.retryAfter});

  final String message;
  final int? retryAfter; // Seconds to wait

  @override
  String toString() =>
      retryAfter != null ? '$message (重试间隔: ${retryAfter}秒)' : message;
}

/// Generic network exception
class NetworkException implements Exception {
  const NetworkException(this.message, {this.originalError});

  final String message;
  final Object? originalError;

  @override
  String toString() => message;
}
