import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sparkle/core/services/smart_cache.dart';

final fileCacheServiceProvider =
    Provider<FileCacheService>((ref) => FileCacheService());

class FileCacheService {
  FileCacheService() : _dio = Dio() {
    _cache = SmartCache<String, _CachedFile>(
      maxSize: _maxEntries,
      maxAge: _maxAge,
      onEvicted: (key, entry) {
        _currentBytes -= entry.size;
        final file = File(entry.path);
        if (file.existsSync()) {
          file.deleteSync();
        }
      },
    );
  }

  static const int _maxEntries = 200;
  static const int _maxBytes = 512 * 1024 * 1024;
  static const Duration _maxAge = Duration(days: 7);

  late final SmartCache<String, _CachedFile> _cache;
  final Dio _dio;
  int _currentBytes = 0;

  Future<File?> getCachedFile(String key) async {
    final entry = _cache.get(key);
    if (entry == null) return null;
    final file = File(entry.path);
    if (!await file.exists()) {
      _removeEntry(key, entry);
      return null;
    }
    return file;
  }

  Future<File?> fetchAndCache(String key, String url,
      {String? extension,}) async {
    final cached = await getCachedFile(key);
    if (cached != null) return cached;

    final dir = await _ensureCacheDir();
    final safeKey = _sanitizeKey(key);
    final filePath = p.join(dir.path, '$safeKey${extension ?? ''}');

    final response = await _dio.get<List<int>>(
      url,
      options: Options(responseType: ResponseType.bytes),
    );

    final bytes = response.data ?? [];
    final file = File(filePath);
    await file.writeAsBytes(bytes, flush: true);

    final entry = _CachedFile(path: filePath, size: bytes.length);
    _cache.set(key, entry);
    _currentBytes += entry.size;
    await _enforceLimits();

    return file;
  }

  Future<void> _enforceLimits() async {
    _cache.cleanup();
    while (_currentBytes > _maxBytes && _cache.keys.isNotEmpty) {
      final oldestKey = _cache.keys.first;
      _cache.remove(oldestKey);
    }
  }

  void _removeEntry(String key, _CachedFile entry) {
    _cache.remove(key);
  }

  Future<Directory> _ensureCacheDir() async {
    final baseDir = await getApplicationDocumentsDirectory();
    final dir = Directory(p.join(baseDir.path, 'file_cache'));
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  String _sanitizeKey(String key) =>
      key.replaceAll(RegExp('[^A-Za-z0-9._-]'), '_');
}

class _CachedFile {
  _CachedFile({required this.path, required this.size});

  final String path;
  final int size;
}
