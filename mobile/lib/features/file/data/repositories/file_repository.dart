import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
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
    final response = await _dio.post(
      ApiEndpoints.filesPrepareUpload,
      data: {
        'filename': filename,
        'file_size': fileSize,
        'mime_type': mimeType,
      },
    );
    return UploadSession.fromJson(response.data as Map<String, dynamic>);
  }

  Future<StoredFile> completeUpload({
    required String uploadId,
    String? groupId,
    String? visibility,
    String? description,
  }) async {
    final response = await _dio.post(
      ApiEndpoints.filesCompleteUpload,
      data: {
        'upload_id': uploadId,
        if (groupId != null) 'group_id': groupId,
        if (visibility != null) 'visibility': visibility,
        if (description != null) 'description': description,
      },
    );
    return StoredFile.fromJson(response.data as Map<String, dynamic>);
  }

  Future<StoredFile> getFile(String fileId, {String? groupId}) async {
    final response = await _dio.get(
      ApiEndpoints.file(fileId),
      queryParameters: {
        if (groupId != null) 'group_id': groupId,
      },
    );
    return StoredFile.fromJson(response.data as Map<String, dynamic>);
  }

  Future<PresignedUrl> getDownloadUrl(String fileId, {String? groupId}) async {
    final response = await _dio.get(
      ApiEndpoints.fileDownload(fileId),
      queryParameters: {
        if (groupId != null) 'group_id': groupId,
      },
    );
    return PresignedUrl.fromJson(
        response.data as Map<String, dynamic>, 'download_url',);
  }

  Future<PresignedUrl> getThumbnailUrl(String fileId, {String? groupId}) async {
    final response = await _dio.get(
      ApiEndpoints.fileThumbnail(fileId),
      queryParameters: {
        if (groupId != null) 'group_id': groupId,
      },
    );
    return PresignedUrl.fromJson(
        response.data as Map<String, dynamic>, 'thumbnail_url',);
  }

  Future<List<StoredFile>> listMyFiles(
      {String? status, int limit = 20, int offset = 0,}) async {
    final response = await _dio.get(
      ApiEndpoints.myFiles,
      queryParameters: {
        if (status != null) 'status': status,
        'limit': limit,
        'offset': offset,
      },
    );
    final data = response.data as List<dynamic>;
    return data
        .map((item) => StoredFile.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<StoredFile>> searchMyFiles(
      {required String query, int limit = 20,}) async {
    final response = await _dio.get(
      ApiEndpoints.myFilesSearch,
      queryParameters: {
        'q': query,
        'limit': limit,
      },
    );
    final data = response.data as List<dynamic>;
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
    final response = await _dio.get(
      ApiEndpoints.groupFiles(groupId),
      queryParameters: {
        if (category != null) 'category': category,
        'limit': limit,
        'offset': offset,
      },
    );
    final data = response.data as List<dynamic>;
    return data
        .map((item) => GroupFileInfo.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<GroupFileInfo> shareToGroup(
    String groupId,
    String fileId, {
    String? category,
    List<String>? tags,
    GroupFilePermissions? permissions,
    bool sendMessage = true,
  }) async {
    final response = await _dio.post(
      ApiEndpoints.groupFileShare(groupId, fileId),
      data: {
        if (category != null) 'category': category,
        if (tags != null) 'tags': tags,
        if (permissions != null) 'permissions': permissions.toJson(),
        'send_message': sendMessage,
      },
    );
    return GroupFileInfo.fromJson(response.data as Map<String, dynamic>);
  }

  Future<GroupFileInfo> updateGroupFilePermissions(
    String groupId,
    String fileId,
    GroupFilePermissions permissions,
  ) async {
    final response = await _dio.put(
      ApiEndpoints.groupFilePermissions(groupId, fileId),
      data: {
        'permissions': permissions.toJson(),
      },
    );
    return GroupFileInfo.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<GroupFileCategoryStat>> getGroupFileCategories(
      String groupId,) async {
    final response = await _dio.get(ApiEndpoints.groupFileCategories(groupId));
    final data = response.data as List<dynamic>;
    return data
        .map((item) =>
            GroupFileCategoryStat.fromJson(item as Map<String, dynamic>),)
        .toList();
  }
}
