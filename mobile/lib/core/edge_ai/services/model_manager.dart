import 'dart:io';
import 'package:dio/dio.dart';
import 'package:logger/logger.dart';
import 'package:path_provider/path_provider.dart';

class ModelManager {
  final Logger _logger = Logger();
  final Dio _dio = Dio();

  // Target model is Qwen3-0.6B
  static const String _modelFileName = 'qwen3-0_6b-instruct-q4_k_m.gguf';
  
  // Future download URL will be provided by user later
  String? _downloadUrl; 

  void setDownloadUrl(String url) => _downloadUrl = url;

  Future<String> getModelPath() async {
    final dir = await getApplicationSupportDirectory();
    return '${dir.path}/$_modelFileName';
  }

  Future<bool> isModelReady() async {
    final path = await getModelPath();
    final file = File(path);
    if (!await file.exists()) return false;
    
    // Qwen3-0.6B Q4_K_M should be around 400MB-500MB
    final length = await file.length();
    return length > 100 * 1024 * 1024; 
  }

  /// In Dev: This ensures the model is ready. 
  /// If not found and no URL provided, it throws to alert manual placement is needed.
  Future<String> ensureModelDownloaded({Function(double)? onProgress}) async {
    final savePath = await getModelPath();
    if (await isModelReady()) {
      _logger.i('Qwen3-0.6B model found at $savePath');
      return savePath;
    }

    if (_downloadUrl == null) {
      _logger.e('Qwen3-0.6B model NOT FOUND at $savePath and no download URL provided. Please place the model file manually.');
      throw Exception('Model missing. Please place $_modelFileName in application support directory.');
    }

    _logger.i('Downloading Qwen3-0.6B from $_downloadUrl...');
    try {
      await _dio.download(
        _downloadUrl!,
        savePath,
        onReceiveProgress: (received, total) {
          if (total != -1 && onProgress != null) {
            onProgress(received / total);
          }
        },
      );
      return savePath;
    } catch (e) {
      _logger.e('Failed to download Qwen3-0.6B', error: e);
      if (await File(savePath).exists()) await File(savePath).delete();
      rethrow;
    }
  }

  Future<void> deleteModel() async {
    final path = await getModelPath();
    final file = File(path);
    if (await file.exists()) {
      await file.delete();
      _logger.i('Model deleted');
    }
  }
}
