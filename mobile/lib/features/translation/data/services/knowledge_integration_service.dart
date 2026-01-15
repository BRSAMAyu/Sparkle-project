import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// Service for integrating translations into knowledge graph
class KnowledgeIntegrationService {
  KnowledgeIntegrationService(this._dio);

  final Dio _dio;

  /// Create vocabulary node from translation
  ///
  /// Sends translation to backend to create a draft knowledge node
  /// that will be scheduled for spaced repetition review.
  Future<VocabularyNodeResult?> createVocabularyNode({
    required String sourceText,
    required String translation,
    required String context,
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
          'language': language,
          'domain': domain,
          'subject_id': subjectId,
        },
      );

      if (response.statusCode == 200 && response.data['success'] == true) {
        debugPrint('✅ Vocabulary node created: ${response.data['node_id']}');
        return VocabularyNodeResult.fromJson(response.data);
      } else {
        debugPrint('⚠️ Failed to create vocabulary node: ${response.data}');
        return null;
      }
    } catch (e) {
      debugPrint('❌ Failed to create vocabulary node: $e');
      return null;
    }
  }

  /// Publish a draft node to main knowledge graph
  Future<bool> publishNode(String nodeId) async {
    try {
      debugPrint('📤 Publishing node: $nodeId');

      final response = await _dio.post('/galaxy/node/$nodeId/publish');

      if (response.statusCode == 200 && response.data['success'] == true) {
        debugPrint('✅ Node published: $nodeId');
        return true;
      } else {
        debugPrint('⚠️ Failed to publish node: ${response.data}');
        return false;
      }
    } catch (e) {
      debugPrint('❌ Failed to publish node: $e');
      return false;
    }
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
