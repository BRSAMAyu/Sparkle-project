import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/file/file.dart';

final fileRepositoryProvider = Provider<FileRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return FileRepository(apiClient.dio);
});

class FileRepository {
  FileRepository(this._dio);

  final Dio _dio;

  Future<UploadSession> prepareUpload({
    required String filename,
    required int fileSize,
    required String mimeType,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.filesPrepareUpload,
      data: {
        'filename': filename,
        'file_size': fileSize,
        'mime_type': mimeType,
      },
    );
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'prepareUpload');
    return UploadSession.fromJson(payload);
  }

  Future<DocumentUploadSession> prepareDocumentUpload({
    required String filename,
    required int fileSize,
    required String mimeType,
    String visibility = 'private',
    String? groupId,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.documentsUpload,
      data: {
        'filename': filename,
        'file_size': fileSize,
        'mime_type': mimeType,
        'visibility': visibility,
        if (groupId != null) 'group_id': groupId,
      },
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'prepareDocumentUpload',
    );
    return DocumentUploadSession.fromJson(payload);
  }

  Future<DocumentUploadConfirmation> confirmDocumentUpload(
    String fileId,
  ) async {
    final response = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.documentConfirmUpload(fileId),
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'confirmDocumentUpload',
    );
    return DocumentUploadConfirmation.fromJson(payload);
  }

  Future<DocumentProcessingStatus> getDocumentStatus(String fileId) async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.documentStatus(fileId),
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'getDocumentStatus',
    );
    return DocumentProcessingStatus.fromJson(payload);
  }

  Future<StoredFile> completeUpload({
    required String uploadId,
    String? groupId,
    String? visibility,
    String? description,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.filesCompleteUpload,
      data: {
        'upload_id': uploadId,
        if (groupId != null) 'group_id': groupId,
        if (visibility != null) 'visibility': visibility,
        if (description != null) 'description': description,
      },
    );
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'fileOperation');
    return StoredFile.fromJson(payload);
  }

  Future<StoredFile> getFile(String fileId, {String? groupId}) async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.file(fileId),
      queryParameters: {
        if (groupId != null) 'group_id': groupId,
      },
    );
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'fileOperation');
    return StoredFile.fromJson(payload);
  }

  Future<PresignedUrl> getDownloadUrl(String fileId, {String? groupId}) async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.fileDownload(fileId),
      queryParameters: {
        if (groupId != null) 'group_id': groupId,
      },
    );
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'getDownloadUrl');
    return PresignedUrl.fromJson(payload, 'download_url');
  }

  Future<PresignedUrl> getThumbnailUrl(String fileId, {String? groupId}) async {
    final response = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.fileThumbnail(fileId),
      queryParameters: {
        if (groupId != null) 'group_id': groupId,
      },
    );
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'getThumbnailUrl');
    return PresignedUrl.fromJson(payload, 'thumbnail_url');
  }

  Future<List<StoredFile>> listMyFiles({
    String? status,
    int limit = 20,
    int offset = 0,
  }) async {
    final response = await _dio.get<dynamic>(
      ApiEndpoints.myFiles,
      queryParameters: {
        if (status != null) 'status': status,
        'limit': limit,
        'offset': offset,
      },
    );
    final data =
        ApiResponseParser.unwrapList(response.data, action: 'listMyFiles');
    return data
        .map((item) => StoredFile.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<StoredFile>> searchMyFiles({
    required String query,
    int limit = 20,
  }) async {
    final response = await _dio.get<dynamic>(
      ApiEndpoints.myFilesSearch,
      queryParameters: {
        'q': query,
        'limit': limit,
      },
    );
    final data =
        ApiResponseParser.unwrapList(response.data, action: 'listMyFiles');
    return data
        .map((item) => StoredFile.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<GroupFileInfo>> listGroupFiles(
    String groupId, {
    String? category,
    int limit = 20,
    int offset = 0,
  }) async {
    final response = await _dio.get<dynamic>(
      ApiEndpoints.groupFiles(groupId),
      queryParameters: {
        if (category != null) 'category': category,
        'limit': limit,
        'offset': offset,
      },
    );
    final data =
        ApiResponseParser.unwrapList(response.data, action: 'listGroupFiles');
    return data
        .map((item) => GroupFileInfo.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<GroupFileInfo> shareToGroup(
    String groupId,
    String fileId, {
    String? category,
    String? description,
    List<String>? tags,
    GroupFilePermissions? permissions,
    bool addToGroupGalaxy = false,
    bool? isOfficial,
    bool sendMessage = true,
  }) async {
    final mergedTags = <String>{
      ...?tags,
      if (addToGroupGalaxy) 'group_galaxy',
      if (isOfficial ?? false) 'official',
    }.toList();

    final response = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.groupFileShare(groupId, fileId),
      data: {
        if (category != null) 'category': category,
        if (description != null) 'description': description,
        if (mergedTags.isNotEmpty) 'tags': mergedTags,
        if (addToGroupGalaxy) 'add_to_group_galaxy': true,
        if (isOfficial ?? false) 'trust_level': 'official',
        if (permissions != null) 'permissions': permissions.toJson(),
        'send_message': sendMessage,
      },
    );
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'shareToGroup');
    return GroupFileInfo.fromJson(payload);
  }

  Future<GroupFileInfo> updateGroupFilePermissions(
    String groupId,
    String fileId,
    GroupFilePermissions permissions,
  ) async {
    final response = await _dio.put<Map<String, dynamic>>(
      ApiEndpoints.groupFilePermissions(groupId, fileId),
      data: {
        'permissions': permissions.toJson(),
      },
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'updateGroupFilePermissions',
    );
    return GroupFileInfo.fromJson(payload);
  }

  Future<List<GroupFileCategoryStat>> getGroupFileCategories(
    String groupId,
  ) async {
    final response =
        await _dio.get<dynamic>(ApiEndpoints.groupFileCategories(groupId));
    final data = ApiResponseParser.unwrapList(
      response.data,
      action: 'getGroupFileCategories',
    );
    return data
        .map(
          (item) =>
              GroupFileCategoryStat.fromJson(item as Map<String, dynamic>),
        )
        .toList();
  }

  Future<void> copyGroupFileToMyLibrary(String groupId, String fileId) async {
    await _dio.post<void>(
      '/api/v1/community/groups/$groupId/files/$fileId/copy-to-library',
    );
  }
}
