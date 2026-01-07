import 'package:sparkle/features/community/data/models/community_model.dart';

class UploadSession {
  UploadSession({
    required this.uploadId,
    required this.fileId,
    required this.presignedUrl,
    required this.expiresIn,
    required this.fields,
    required this.bucket,
    required this.objectKey,
  });

  factory UploadSession.fromJson(Map<String, dynamic> json) {
    final rawFields = json['fields'] as Map<String, dynamic>? ?? {};
    return UploadSession(
      uploadId: json['upload_id']?.toString() ?? '',
      fileId: json['file_id']?.toString() ?? '',
      presignedUrl: json['presigned_url']?.toString() ?? '',
      expiresIn: (json['expires_in'] as num?)?.toInt() ?? 0,
      fields: rawFields.map((key, value) => MapEntry(key, value.toString())),
      bucket: json['bucket']?.toString() ?? '',
      objectKey: json['object_key']?.toString() ?? '',
    );
  }

  final String uploadId;
  final String fileId;
  final String presignedUrl;
  final int expiresIn;
  final Map<String, String> fields;
  final String bucket;
  final String objectKey;
}

class PresignedUrl {
  PresignedUrl({required this.url, required this.expiresIn});

  factory PresignedUrl.fromJson(Map<String, dynamic> json, String key) =>
      PresignedUrl(
        url: json[key]?.toString() ?? '',
        expiresIn: (json['expires_in'] as num?)?.toInt() ?? 0,
      );

  final String url;
  final int expiresIn;
}

class StoredFile {
  StoredFile({
    required this.id,
    required this.userId,
    required this.fileName,
    required this.mimeType,
    required this.fileSize,
    required this.bucket,
    required this.objectKey,
    required this.status,
    required this.visibility,
    required this.createdAt,
    required this.updatedAt,
  });

  factory StoredFile.fromJson(Map<String, dynamic> json) => StoredFile(
        id: json['id']?.toString() ?? '',
        userId: json['user_id']?.toString() ?? '',
        fileName: json['file_name']?.toString() ?? '',
        mimeType: json['mime_type']?.toString() ?? '',
        fileSize: (json['file_size'] as num?)?.toInt() ?? 0,
        bucket: json['bucket']?.toString() ?? '',
        objectKey: json['object_key']?.toString() ?? '',
        status: json['status']?.toString() ?? '',
        visibility: json['visibility']?.toString() ?? '',
        createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ??
            DateTime.now(),
        updatedAt: DateTime.tryParse(json['updated_at']?.toString() ?? '') ??
            DateTime.now(),
      );

  final String id;
  final String userId;
  final String fileName;
  final String mimeType;
  final int fileSize;
  final String bucket;
  final String objectKey;
  final String status;
  final String visibility;
  final DateTime createdAt;
  final DateTime updatedAt;
}

class GroupFilePermissions {
  GroupFilePermissions({
    required this.viewRole,
    required this.downloadRole,
    required this.manageRole,
  });

  final GroupRole viewRole;
  final GroupRole downloadRole;
  final GroupRole manageRole;

  Map<String, dynamic> toJson() => {
        'view_role': viewRole.name,
        'download_role': downloadRole.name,
        'manage_role': manageRole.name,
      };
}

class GroupFileInfo {
  GroupFileInfo({
    required this.id,
    required this.groupId,
    required this.fileId,
    required this.fileName,
    required this.mimeType,
    required this.fileSize,
    required this.status,
    required this.visibility,
    required this.viewRole,
    required this.downloadRole,
    required this.manageRole,
    required this.canDownload,
    required this.canManage,
    required this.createdAt,
    required this.updatedAt,
    this.category,
    this.tags = const [],
    this.sharedBy,
  });

  factory GroupFileInfo.fromJson(Map<String, dynamic> json) {
    GroupRole parseRole(String? value) => GroupRole.values.firstWhere(
          (role) => role.name == value,
          orElse: () => GroupRole.member,
        );

    return GroupFileInfo(
      id: json['id']?.toString() ?? '',
      groupId: json['group_id']?.toString() ?? '',
      fileId: json['file_id']?.toString() ?? '',
      fileName: json['file_name']?.toString() ?? '',
      mimeType: json['mime_type']?.toString() ?? '',
      fileSize: (json['file_size'] as num?)?.toInt() ?? 0,
      status: json['status']?.toString() ?? '',
      visibility: json['visibility']?.toString() ?? '',
      viewRole: parseRole(json['view_role']?.toString()),
      downloadRole: parseRole(json['download_role']?.toString()),
      manageRole: parseRole(json['manage_role']?.toString()),
      canDownload: json['can_download'] == true,
      canManage: json['can_manage'] == true,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ??
          DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at']?.toString() ?? '') ??
          DateTime.now(),
      category: json['category']?.toString(),
      tags: (json['tags'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
      sharedBy: json['shared_by'] == null
          ? null
          : UserBrief.fromJson(json['shared_by'] as Map<String, dynamic>),
    );
  }

  final String id;
  final String groupId;
  final String fileId;
  final String fileName;
  final String mimeType;
  final int fileSize;
  final String status;
  final String visibility;
  final GroupRole viewRole;
  final GroupRole downloadRole;
  final GroupRole manageRole;
  final bool canDownload;
  final bool canManage;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? category;
  final List<String> tags;
  final UserBrief? sharedBy;
}

class GroupFileCategoryStat {
  GroupFileCategoryStat({required this.category, required this.count});

  factory GroupFileCategoryStat.fromJson(Map<String, dynamic> json) =>
      GroupFileCategoryStat(
        category: json['category']?.toString(),
        count: (json['count'] as num?)?.toInt() ?? 0,
      );

  final String? category;
  final int count;
}

class FileMessageData {
  FileMessageData({
    required this.fileId,
    required this.fileName,
    this.mimeType,
    this.fileSize,
    this.status,
  });

  factory FileMessageData.fromJson(Map<String, dynamic> json) =>
      FileMessageData(
        fileId: json['file_id']?.toString() ?? '',
        fileName: json['file_name']?.toString() ?? 'File',
        mimeType: json['mime_type']?.toString(),
        fileSize: (json['file_size'] as num?)?.toInt(),
        status: json['status']?.toString(),
      );

  final String fileId;
  final String fileName;
  final String? mimeType;
  final int? fileSize;
  final String? status;
}
