import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/network/dio_provider.dart';
import 'package:sparkle/features/document/models/document_cleaning_model.dart';

part 'document_repository.g.dart';

@riverpod
DocumentRepository documentRepository(DocumentRepositoryRef ref) =>
    DocumentRepository(ref.watch(dioProvider));

class DocumentRepository {
  DocumentRepository(this._dio);
  final Dio _dio;

  /// Uploads a document and starts the cleaning task.
  /// Returns the task_id.
  Future<String> uploadAndClean(File file, {bool enableOcr = true}) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path),
      'options': jsonEncode({'enable_ocr': enableOcr}),
    });

    final response = await _dio.post<Map<String, dynamic>>(
      '/documents/clean', // Assuming base URL is set in Dio
      data: formData,
    );

    final data = response.data;
    if (data == null || data['task_id'] == null) {
      throw Exception('Missing task_id in response');
    }
    return data['task_id'] as String;
  }

  /// Polls the status of a cleaning task.
  Future<CleaningTaskStatus> getTaskStatus(String taskId) async {
    final response =
        await _dio.get<Map<String, dynamic>>('/documents/clean/$taskId');
    return CleaningTaskStatus.fromJson(response.data ?? <String, dynamic>{});
  }
}
