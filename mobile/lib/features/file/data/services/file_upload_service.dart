import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http_parser/http_parser.dart';
import 'package:path/path.dart' as p;
import 'package:sparkle/features/file/data/models/file_models.dart';
import 'package:sparkle/features/file/data/repositories/file_repository.dart';

const List<String> supportedStudyMaterialExtensions = <String>[
  'pdf',
  'docx',
  'pptx',
  'md',
  'markdown',
  'png',
  'jpg',
  'jpeg',
  'gif',
  'webp',
];

final fileUploadServiceProvider = Provider<FileUploadService>(
  (ref) => FileUploadService(ref.read(fileRepositoryProvider)),
);

class FileUploadService {
  FileUploadService(this._repository)
      : _uploadDio = Dio(
          BaseOptions(
            connectTimeout: const Duration(seconds: 15),
            receiveTimeout: const Duration(seconds: 30),
          ),
        );

  final FileRepository _repository;
  final Dio _uploadDio;

  Future<DocumentUploadTicket> uploadDocument(
    File file, {
    String visibility = 'private',
    String? groupId,
    void Function(double progress)? onProgress,
  }) async {
    final fileSize = await file.length();
    final fileName = p.basename(file.path);
    final mimeType = _guessMimeType(fileName, forDocumentUpload: true);

    final session = await _repository.prepareDocumentUpload(
      filename: fileName,
      fileSize: fileSize,
      mimeType: mimeType,
      visibility: visibility,
      groupId: groupId,
    );

    try {
      await _uploadBinaryWithRetry(
        session.presignedUrl,
        file,
        mimeType: mimeType,
        fileSize: fileSize,
        onProgress: onProgress,
      );
    } on DioException catch (e) {
      if (_isNetworkError(e)) {
        throw UploadInterruptedException(
          file: file,
          session: UploadSession(
            uploadId: session.fileId,
            fileId: session.fileId,
            presignedUrl: session.presignedUrl,
            expiresIn: session.expiresIn,
            fields: const <String, String>{},
            bucket: '',
            objectKey: '',
          ),
        );
      }
      throw UploadFailedException.fromDio(e);
    }

    final confirmation =
        await _repository.confirmDocumentUpload(session.fileId);
    return DocumentUploadTicket(
      fileId: session.fileId,
      jobId: confirmation.jobId,
      estimatedSeconds: confirmation.estimatedSeconds,
      fileName: fileName,
      mimeType: mimeType,
      fileSize: fileSize,
    );
  }

  Future<DocumentProcessingStatus> getDocumentStatus(String fileId) =>
      _repository.getDocumentStatus(fileId);

  Future<StoredFile> uploadFile(
    File file, {
    String? visibility,
    String? groupId,
    void Function(double progress)? onProgress,
  }) async {
    final fileSize = await file.length();
    final filename = p.basename(file.path);
    final mimeType = _guessMimeType(filename);

    final session = await _repository.prepareUpload(
      filename: filename,
      fileSize: fileSize,
      mimeType: mimeType,
    );

    try {
      await _uploadWithRetry(
        session,
        file,
        filename,
        mimeType,
        onProgress: onProgress,
      );
    } on DioException catch (e) {
      if (_isNetworkError(e)) {
        throw UploadInterruptedException(file: file, session: session);
      }
      throw UploadFailedException.fromDio(e);
    }

    return _repository.completeUpload(
      uploadId: session.uploadId,
      groupId: groupId,
      visibility: visibility,
    );
  }

  Future<StoredFile> resumeUpload(
    File file,
    UploadSession session, {
    String? visibility,
    String? groupId,
    void Function(double progress)? onProgress,
  }) async {
    try {
      await _uploadWithRetry(
        session,
        file,
        p.basename(file.path),
        _guessMimeType(file.path),
        onProgress: onProgress,
      );
    } on DioException catch (e) {
      if (_isNetworkError(e)) {
        throw UploadInterruptedException(file: file, session: session);
      }
      throw UploadFailedException.fromDio(e);
    }

    return _repository.completeUpload(
      uploadId: session.uploadId,
      groupId: groupId,
      visibility: visibility,
    );
  }

  Future<void> _uploadBinaryWithRetry(
    String presignedUrl,
    File file, {
    required String mimeType,
    required int fileSize,
    void Function(double progress)? onProgress,
  }) async {
    const maxAttempts = 3;
    var attempt = 0;
    var delay = const Duration(seconds: 1);

    while (true) {
      attempt += 1;
      try {
        await _uploadDio.put<void>(
          presignedUrl,
          data: file.openRead(),
          options: Options(
            contentType: mimeType,
            headers: <String, Object>{
              Headers.contentLengthHeader: fileSize,
            },
          ),
          onSendProgress: (sent, total) {
            final effectiveTotal = total > 0 ? total : fileSize;
            if (effectiveTotal <= 0) {
              return;
            }
            onProgress?.call(sent / effectiveTotal);
          },
        );
        return;
      } on DioException {
        if (attempt >= maxAttempts) {
          rethrow;
        }
        await Future<void>.delayed(delay);
        delay *= 2;
      }
    }
  }

  Future<void> _uploadWithRetry(
    UploadSession session,
    File file,
    String filename,
    String mimeType, {
    void Function(double progress)? onProgress,
  }) async {
    const maxAttempts = 3;
    var attempt = 0;
    var delay = const Duration(seconds: 1);

    while (true) {
      attempt += 1;
      try {
        final formMap = <String, dynamic>{
          ...session.fields,
          'file': await MultipartFile.fromFile(
            file.path,
            filename: filename,
            contentType: MediaType.parse(mimeType),
          ),
        };
        await _uploadDio.post<void>(
          session.presignedUrl,
          data: FormData.fromMap(formMap),
          options: Options(
            contentType: 'multipart/form-data',
            followRedirects: false,
          ),
          onSendProgress: (sent, total) {
            if (total <= 0) return;
            onProgress?.call(sent / total);
          },
        );
        return;
      } on DioException {
        if (attempt >= maxAttempts) {
          rethrow;
        }
        await Future<void>.delayed(delay);
        delay *= 2;
      }
    }
  }

  bool _isNetworkError(DioException error) =>
      error.type == DioExceptionType.connectionTimeout ||
      error.type == DioExceptionType.receiveTimeout ||
      error.type == DioExceptionType.sendTimeout ||
      error.type == DioExceptionType.connectionError;

  String _guessMimeType(String filename, {bool forDocumentUpload = false}) {
    final ext = p.extension(filename).toLowerCase();
    switch (ext) {
      case '.pdf':
        return 'application/pdf';
      case '.docx':
        return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
      case '.pptx':
        return 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
      case '.md':
      case '.markdown':
        return 'text/markdown';
      case '.txt':
        return 'text/plain';
      case '.png':
        return 'image/png';
      case '.jpg':
      case '.jpeg':
        return 'image/jpeg';
      case '.gif':
        return 'image/gif';
      case '.webp':
        return 'image/webp';
      default:
        return forDocumentUpload
            ? 'application/pdf'
            : 'application/octet-stream';
    }
  }
}

class UploadInterruptedException implements Exception {
  UploadInterruptedException({required this.file, required this.session});

  final File file;
  final UploadSession session;

  @override
  String toString() => 'Upload interrupted, can resume with existing session.';
}

class UploadFailedException implements Exception {
  UploadFailedException(this.message, this.type, {this.statusCode});

  factory UploadFailedException.fromDio(DioException e) {
    // Sanitize message to remove URLs (simple heuristic)
    var msg = e.message ?? '未知错误';
    if (msg.contains('http')) {
      msg = 'Request failed';
    }
    return UploadFailedException(
      msg,
      e.type,
      statusCode: e.response?.statusCode,
    );
  }

  final String message;
  final DioExceptionType type;
  final int? statusCode;

  @override
  String toString() =>
      'UploadFailedException: $type (Status: $statusCode) - $message';
}
