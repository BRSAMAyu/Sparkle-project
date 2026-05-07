import 'dart:convert';
import 'dart:io';
import 'dart:isolate';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

bool _looksLikeUnavailableDefinition(String value) {
  final normalized = value.trim().toLowerCase();
  if (normalized.isEmpty) {
    return true;
  }
  return normalized.contains('definition unavailable') ||
      normalized.contains('no definition found');
}

bool _hasUsableDefinitions(Map<String, dynamic> entry) {
  final definitions = entry['definitions'];
  if (definitions is List) {
    return definitions
        .whereType<Object>()
        .map((item) => item.toString().trim())
        .any((item) => !_looksLikeUnavailableDefinition(item));
  }
  if (definitions is String) {
    return !_looksLikeUnavailableDefinition(definitions);
  }
  return false;
}

class DictionaryPackageInfo {
  const DictionaryPackageInfo({
    required this.id,
    required this.name,
    required this.version,
    required this.description,
    required this.packageScope,
    required this.source,
    required this.format,
    required this.entryCount,
    required this.downloadAvailable,
    required this.downloadUrl,
    this.sizeBytes,
    this.sha256,
    this.generatedAt,
  });

  factory DictionaryPackageInfo.fromJson(Map<String, dynamic> json) =>
      DictionaryPackageInfo(
        id: json['id'] as String,
        name: json['name'] as String,
        version: json['version'] as String,
        description: json['description'] as String? ?? '',
        packageScope: json['package_scope'] as String? ?? 'starter',
        source: json['source'] as String? ?? 'unknown',
        format: json['format'] as String? ?? 'json.gz',
        entryCount: json['entry_count'] as int? ?? 0,
        downloadAvailable: json['download_available'] as bool? ?? false,
        downloadUrl: json['download_url'] as String? ?? '',
        sizeBytes: json['size_bytes'] as int?,
        sha256: json['sha256'] as String?,
        generatedAt: json['generated_at'] as String?,
      );

  final String id;
  final String name;
  final String version;
  final String description;
  final String packageScope;
  final String source;
  final String format;
  final int entryCount;
  final bool downloadAvailable;
  final String downloadUrl;
  final int? sizeBytes;
  final String? sha256;
  final String? generatedAt;
}

class InstalledDictionaryPackage {
  const InstalledDictionaryPackage({
    required this.id,
    required this.filePath,
    required this.sizeBytes,
    required this.installedAt,
  });

  final String id;
  final String filePath;
  final int sizeBytes;
  final DateTime installedAt;
}

class OfflineDictionaryService {
  OfflineDictionaryService(this._apiClient);

  final ApiClient _apiClient;
  Map<String, Map<String, dynamic>>? _mergedEntries;

  Future<List<DictionaryPackageInfo>> listPackages() async {
    final response = await _apiClient.get<List<dynamic>>(
      ApiEndpoints.dictionaryPackages,
    );
    final data = response.data ?? <dynamic>[];
    return data
        .whereType<Map<String, dynamic>>()
        .map(DictionaryPackageInfo.fromJson)
        .toList();
  }

  Future<List<String>> getInstalledPackageIds() async {
    final packages = await getInstalledPackages();
    return packages.map((package) => package.id).toList(growable: false);
  }

  Future<List<InstalledDictionaryPackage>> getInstalledPackages() async {
    final dir = await _packageDirectory();
    final dirPath = dir.path;
    return Isolate.run(() {
      final packageDir = Directory(dirPath);
      if (!packageDir.existsSync()) {
        return <InstalledDictionaryPackage>[];
      }

      final packages = packageDir
          .listSync()
          .whereType<File>()
          .where((file) => file.path.endsWith('.json'))
          .map((file) {
            final id = file.uri.pathSegments.last.replaceAll('.json', '');
            final stats = file.statSync();
            return InstalledDictionaryPackage(
              id: id,
              filePath: file.path,
              sizeBytes: stats.size,
              installedAt: stats.modified,
            );
          })
          .where((package) => package.id != 'lookup_cache')
          .toList()
        ..sort((left, right) => left.id.compareTo(right.id));

      return packages;
    });
  }

  Future<void> downloadPackage(String packageId) async {
    final response = await _apiClient.dio.get<List<int>>(
      ApiEndpoints.dictionaryPackageDownload(packageId),
      options: Options(responseType: ResponseType.bytes),
    );
    final bytes = response.data;
    if (bytes == null || bytes.isEmpty) {
      throw Exception('Downloaded dictionary package is empty');
    }

    final decoded = json.decode(utf8.decode(gzip.decode(bytes)));
    if (decoded is! Map<String, dynamic>) {
      throw Exception('Invalid offline dictionary package format');
    }
    final entries = decoded['entries'];
    if (entries is! Map<String, dynamic>) {
      throw Exception('Offline dictionary package missing entries');
    }

    final dir = await _packageDirectory();
    await dir.create(recursive: true);
    final file = File('${dir.path}/$packageId.json');
    await _writeJsonFile(file.path, entries);
    _mergedEntries = null;
  }

  Future<Map<String, dynamic>?> lookup(String word) async {
    final normalized = word.trim().toLowerCase();
    if (normalized.isEmpty) {
      return null;
    }
    final entries = await _loadEntries();
    final match = entries[normalized];
    if (match == null) {
      return null;
    }
    if (!_hasUsableDefinitions(match)) {
      return null;
    }
    return Map<String, dynamic>.from(match)
      ..putIfAbsent('source', () => 'offline_dictionary');
  }

  Future<void> cacheLookupResult(Map<String, dynamic> entry) async {
    final word = (entry['word'] as String?)?.trim().toLowerCase();
    if (word == null || word.isEmpty) {
      return;
    }
    if (!_hasUsableDefinitions(entry)) {
      return;
    }

    final dir = await _packageDirectory();
    await dir.create(recursive: true);
    final cacheFile = File('${dir.path}/lookup_cache.json');
    var payload = <String, dynamic>{};
    if (await _fileExists(cacheFile.path)) {
      final decoded = await _readJsonMap(cacheFile.path);
      if (decoded != null) {
        payload = decoded;
      }
    }
    payload[word] = entry;
    await _writeJsonFile(cacheFile.path, payload);
    _mergedEntries = null;
  }

  Future<void> removePackage(String packageId) async {
    final dir = await _packageDirectory();
    final filePath = '${dir.path}/$packageId.json';
    await Isolate.run(() {
      final file = File(filePath);
      if (file.existsSync()) {
        file.deleteSync();
      }
    });
    _mergedEntries = null;
  }

  Future<Map<String, Map<String, dynamic>>> _loadEntries() async {
    final merged = _mergedEntries;
    if (merged != null) {
      return merged;
    }

    final dir = await _packageDirectory();
    if (!await _directoryExists(dir.path)) {
      _mergedEntries = <String, Map<String, dynamic>>{};
      return _mergedEntries!;
    }

    final result = await _loadEntriesFromDirectory(dir.path);

    _mergedEntries = result;
    return result;
  }

  Future<Directory> _packageDirectory() async {
    final root = await getApplicationDocumentsDirectory();
    return Directory('${root.path}/offline_dictionary');
  }

  Future<bool> _directoryExists(String path) async =>
      Isolate.run(() => Directory(path).existsSync());

  Future<bool> _fileExists(String path) async =>
      Isolate.run(() => File(path).existsSync());

  Future<Map<String, dynamic>?> _readJsonMap(String path) async =>
      Isolate.run(() {
        final file = File(path);
        if (!file.existsSync()) {
          return null;
        }
        final decoded = json.decode(file.readAsStringSync());
        if (decoded is Map<String, dynamic>) {
          return decoded;
        }
        return null;
      });

  Future<void> _writeJsonFile(String path, Object value) async {
    await Isolate.run(() {
      File(path).writeAsStringSync(json.encode(value), flush: true);
    });
  }

  Future<Map<String, Map<String, dynamic>>> _loadEntriesFromDirectory(
    String dirPath,
  ) async =>
      Isolate.run(() {
        final result = <String, Map<String, dynamic>>{};
        final dir = Directory(dirPath);

        for (final entity in dir.listSync()) {
          if (entity is! File || !entity.path.endsWith('.json')) {
            continue;
          }
          final decoded = json.decode(entity.readAsStringSync());
          if (decoded is! Map<String, dynamic>) {
            continue;
          }
          for (final entry in decoded.entries) {
            final value = entry.value;
            if (value is Map<String, dynamic>) {
              result[entry.key.toLowerCase()] =
                  Map<String, dynamic>.from(value);
            }
          }
        }

        return result;
      });
}

final offlineDictionaryServiceProvider = Provider<OfflineDictionaryService>(
  (ref) => OfflineDictionaryService(ref.watch(apiClientProvider)),
);
