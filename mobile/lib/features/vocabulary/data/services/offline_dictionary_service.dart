import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

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
    final dir = await _packageDirectory();
    if (!await dir.exists()) {
      return const [];
    }
    final files = dir
        .listSync()
        .whereType<File>()
        .where((file) => file.path.endsWith('.json'))
        .map((file) => file.uri.pathSegments.last.replaceAll('.json', ''))
        .where((name) => name != 'lookup_cache')
        .toList()
      ..sort();
    return files;
  }

  Future<void> downloadPackage(String packageId) async {
    final response = await _apiClient.dio.get<List<int>>(
      ApiEndpoints.dictionaryPackageDownload(packageId),
      options: Options(responseType: ResponseType.bytes),
    );
    final bytes = response.data;
    if (bytes == null || bytes.isEmpty) {
      throw Exception('下载的词典包为空');
    }

    final decoded = json.decode(utf8.decode(gzip.decode(bytes)));
    if (decoded is! Map<String, dynamic>) {
      throw Exception('离线词典包格式无效');
    }
    final entries = decoded['entries'];
    if (entries is! Map<String, dynamic>) {
      throw Exception('离线词典包缺少 entries');
    }

    final dir = await _packageDirectory();
    await dir.create(recursive: true);
    final file = File('${dir.path}/$packageId.json');
    await file.writeAsString(
      json.encode(entries),
      flush: true,
    );
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
    return Map<String, dynamic>.from(match)
      ..putIfAbsent('source', () => 'offline_dictionary');
  }

  Future<void> cacheLookupResult(Map<String, dynamic> entry) async {
    final word = (entry['word'] as String?)?.trim().toLowerCase();
    if (word == null || word.isEmpty) {
      return;
    }

    final dir = await _packageDirectory();
    await dir.create(recursive: true);
    final cacheFile = File('${dir.path}/lookup_cache.json');
    var payload = <String, dynamic>{};
    if (await cacheFile.exists()) {
      final raw = await cacheFile.readAsString();
      final decoded = json.decode(raw);
      if (decoded is Map<String, dynamic>) {
        payload = decoded;
      }
    }
    payload[word] = entry;
    await cacheFile.writeAsString(json.encode(payload), flush: true);
    _mergedEntries = null;
  }

  Future<Map<String, Map<String, dynamic>>> _loadEntries() async {
    final merged = _mergedEntries;
    if (merged != null) {
      return merged;
    }

    final dir = await _packageDirectory();
    if (!await dir.exists()) {
      _mergedEntries = <String, Map<String, dynamic>>{};
      return _mergedEntries!;
    }

    final result = <String, Map<String, dynamic>>{};
    for (final entity in dir.listSync()) {
      if (entity is! File || !entity.path.endsWith('.json')) {
        continue;
      }
      final decoded = json.decode(await entity.readAsString());
      if (decoded is! Map<String, dynamic>) {
        continue;
      }
      for (final entry in decoded.entries) {
        final value = entry.value;
        if (value is Map<String, dynamic>) {
          result[entry.key.toLowerCase()] = value;
        }
      }
    }

    _mergedEntries = result;
    return result;
  }

  Future<Directory> _packageDirectory() async {
    final root = await getApplicationDocumentsDirectory();
    return Directory('${root.path}/offline_dictionary');
  }
}

final offlineDictionaryServiceProvider = Provider<OfflineDictionaryService>(
  (ref) => OfflineDictionaryService(ref.watch(apiClientProvider)),
);
