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

    final response = await _dio.post(
      '/documents/clean', // Assuming base URL is set in Dio
      data: formData,
    );

    return response.data['task_id'];
  }

  /// Polls the status of a cleaning task.
  Future<CleaningTaskStatus> getTaskStatus(String taskId) async {
    final response = await _dio.get('/documents/clean/$taskId');
    return CleaningTaskStatus.fromJson(response.data);
  }
}
