import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Storage key prefix for all view state
const String _viewStatePrefix = 'view_state';

/// Version key suffix
const String _versionKeySuffix = '_version';

/// Default version for new namespaces
const int _defaultVersion = 1;

/// Migration function type
typedef MigrationFunction = Future<Map<String, dynamic>> Function(
  Map<String, dynamic> oldData,
  int oldVersion,
);

/// Type-safe storage service for view state persistence.
///
/// Provides namespace-based key management, JSON serialization,
/// batch operations, and migration support.
class ViewStorageService {
  ViewStorageService(this._prefs);

  final SharedPreferences _prefs;
  final Map<String, Timer> _debounceTimers = {};

  /// Get the singleton instance
  static ViewStorageService? _instance;

  static Future<ViewStorageService> getInstance() async {
    _instance ??= ViewStorageService(await SharedPreferences.getInstance());
    return _instance!;
  }

  /// Get or create the singleton instance (synchronous, for providers)
  /// Call ensureInitialized() during app startup first.
  static ViewStorageService get instance {
    if (_instance == null) {
      throw StateError(
        'ViewStorageService not initialized. Call ensureInitialized() first.',
      );
    }
    return _instance!;
  }

  /// Initialize the service (call during app startup)
  static Future<void> ensureInitialized() async {
    await getInstance();
  }

  /// Build a namespaced key
  String _buildKey(String namespace, String key) => '$_viewStatePrefix.$namespace.$key';

  /// Build the version key for a namespace
  String _buildVersionKey(String namespace) => '$_viewStatePrefix.$namespace$_versionKeySuffix';

  /// Get the current version for a namespace
  int _getVersion(String namespace) => _prefs.getInt(_buildVersionKey(namespace)) ?? _defaultVersion;

  /// Set the version for a namespace
  Future<void> _setVersion(String namespace, int version) async {
    await _prefs.setInt(_buildVersionKey(namespace), version);
  }

  /// Clear all persisted view state namespaces.
  Future<void> clearAllViewState() async {
    final keys = _prefs
        .getKeys()
        .where((key) => key.startsWith(_viewStatePrefix))
        .toList();
    for (final timer in _debounceTimers.values) {
      timer.cancel();
    }
    _debounceTimers.clear();
    for (final key in keys) {
      await _prefs.remove(key);
    }
  }

  // ==================== Primitive Get/Set ====================

  /// Get a string value
  String? getString(String namespace, String key) => _prefs.getString(_buildKey(namespace, key));

  /// Set a string value (with optional debounce)
  Future<void> setString(
    String namespace,
    String key,
    String value, {
    Duration debounce = const Duration(milliseconds: 300),
  }) async {
    final storageKey = _buildKey(namespace, key);
    await _debouncedWrite(
      storageKey,
      () => _prefs.setString(storageKey, value),
      debounce,
    );
  }

  /// Get an int value
  int? getInt(String namespace, String key) => _prefs.getInt(_buildKey(namespace, key));

  /// Set an int value (with optional debounce)
  Future<void> setInt(
    String namespace,
    String key,
    int value, {
    Duration debounce = const Duration(milliseconds: 300),
  }) async {
    final storageKey = _buildKey(namespace, key);
    await _debouncedWrite(
      storageKey,
      () => _prefs.setInt(storageKey, value),
      debounce,
    );
  }

  /// Get a double value
  double? getDouble(String namespace, String key) => _prefs.getDouble(_buildKey(namespace, key));

  /// Set a double value (with optional debounce)
  Future<void> setDouble(
    String namespace,
    String key,
    double value, {
    Duration debounce = const Duration(milliseconds: 300),
  }) async {
    final storageKey = _buildKey(namespace, key);
    await _debouncedWrite(
      storageKey,
      () => _prefs.setDouble(storageKey, value),
      debounce,
    );
  }

  /// Get a bool value
  bool? getBool(String namespace, String key) => _prefs.getBool(_buildKey(namespace, key));

  /// Set a bool value (with optional debounce)
  Future<void> setBool(
    String namespace,
    String key,
    bool value, {
    Duration debounce = const Duration(milliseconds: 300),
  }) async {
    final storageKey = _buildKey(namespace, key);
    await _debouncedWrite(
      storageKey,
      () => _prefs.setBool(storageKey, value),
      debounce,
    );
  }

  // ==================== JSON Serialization ====================

  /// Get a JSON object and decode it
  Map<String, dynamic>? getJson(String namespace, String key) {
    final jsonString = getString(namespace, key);
    if (jsonString == null) return null;
    try {
      return jsonDecode(jsonString) as Map<String, dynamic>;
    } catch (e) {
      debugPrint('ViewStorageService: Failed to decode JSON for $namespace.$key: $e');
      return null;
    }
  }

  /// Encode and store a JSON object (with optional debounce)
  Future<void> setJson(
    String namespace,
    String key,
    Map<String, dynamic> value, {
    Duration debounce = const Duration(milliseconds: 300),
  }) async {
    try {
      final jsonString = jsonEncode(value);
      await setString(namespace, key, jsonString, debounce: debounce);
    } catch (e) {
      debugPrint('ViewStorageService: Failed to encode JSON for $namespace.$key: $e');
    }
  }

  /// Get a JSON list and decode it
  List<dynamic>? getJsonList(String namespace, String key) {
    final jsonString = getString(namespace, key);
    if (jsonString == null) return null;
    try {
      return jsonDecode(jsonString) as List<dynamic>;
    } catch (e) {
      debugPrint('ViewStorageService: Failed to decode JSON list for $namespace.$key: $e');
      return null;
    }
  }

  /// Encode and store a JSON list (with optional debounce)
  Future<void> setJsonList(
    String namespace,
    String key,
    List<dynamic> value, {
    Duration debounce = const Duration(milliseconds: 300),
  }) async {
    try {
      final jsonString = jsonEncode(value);
      await setString(namespace, key, jsonString, debounce: debounce);
    } catch (e) {
      debugPrint('ViewStorageService: Failed to encode JSON list for $namespace.$key: $e');
    }
  }

  // ==================== Enum Support ====================

  /// Get an enum value by name
  T? getEnum<T extends Enum>(String namespace, String key, List<T> values) {
    final enumName = getString(namespace, key);
    if (enumName == null) return null;
    try {
      return values.firstWhere(
        (e) => e.name == enumName,
      );
    } catch (e) {
      debugPrint('ViewStorageService: Failed to find enum $enumName in $T');
      return null;
    }
  }

  /// Store an enum value by name (with optional debounce)
  Future<void> setEnum<T extends Enum>(
    String namespace,
    String key,
    T? value, {
    Duration debounce = const Duration(milliseconds: 300),
  }) async {
    if (value == null) {
      await remove(namespace, key);
    } else {
      await setString(namespace, key, value.name, debounce: debounce);
    }
  }

  // ==================== DateTime Support ====================

  /// Get a DateTime value (stored as ISO-8601 string)
  DateTime? getDateTime(String namespace, String key) {
    final isoString = getString(namespace, key);
    if (isoString == null) return null;
    try {
      return DateTime.parse(isoString);
    } catch (e) {
      debugPrint('ViewStorageService: Failed to parse DateTime for $namespace.$key: $e');
      return null;
    }
  }

  /// Store a DateTime value as ISO-8601 string (with optional debounce)
  Future<void> setDateTime(
    String namespace,
    String key,
    DateTime? value, {
    Duration debounce = const Duration(milliseconds: 300),
  }) async {
    if (value == null) {
      await remove(namespace, key);
    } else {
      await setString(namespace, key, value.toIso8601String(), debounce: debounce);
    }
  }

  // ==================== Set Support ====================

  /// Get a Set of strings (stored as JSON list)
  Set<String>? getStringSet(String namespace, String key) {
    final jsonString = _prefs.getString(_buildKey(namespace, key));
    if (jsonString == null) return null;
    try {
      final jsonList = jsonDecode(jsonString) as List<dynamic>;
      return jsonList.map((e) => e.toString()).toSet();
    } catch (e) {
      return null;
    }
  }

  /// Store a Set of strings as JSON list (with optional debounce)
  Future<void> setStringSet(
    String namespace,
    String key,
    Set<String> value, {
    Duration debounce = const Duration(milliseconds: 300),
  }) async {
    try {
      final jsonString = jsonEncode(value.toList());
      await setString(namespace, key, jsonString, debounce: debounce);
    } catch (e) {
      debugPrint('ViewStorageService: Failed to encode Set for $namespace.$key: $e');
    }
  }

  // ==================== Debounce ====================

  /// Execute a write operation with debouncing
  Future<void> _debouncedWrite(
    String key,
    Future<void> Function() writeFn,
    Duration debounce,
  ) async {
    // Cancel existing timer for this key
    _debounceTimers[key]?.cancel();

    if (debounce == Duration.zero) {
      // Immediate write
      await writeFn();
    } else {
      // Debounced write
      _debounceTimers[key] = Timer(debounce, () async {
        await writeFn();
        _debounceTimers.remove(key);
      });
    }
  }

  /// Flush any pending debounced writes immediately
  Future<void> flush() async {
    final timers = _debounceTimers.values.toList();
    for (final timer in timers) {
      timer.cancel();
    }
    _debounceTimers.clear();
  }

  // ==================== Batch Operations ====================

  /// Remove all keys in a namespace
  Future<void> clearNamespace(String namespace) async {
    final keys = _prefs.getKeys().where((key) => key.startsWith('$_viewStatePrefix.$namespace.'));
    for (final key in keys) {
      await _prefs.remove(key);
    }
    // Also remove version key
    await _prefs.remove(_buildVersionKey(namespace));
  }

  /// Remove a specific key
  Future<void> remove(String namespace, String key) async {
    await _prefs.remove(_buildKey(namespace, key));
  }

  // ==================== Migration Support ====================

  /// Registered migrations for each namespace
  final Map<String, Map<int, MigrationFunction>> _migrations = {};

  /// Register a migration function for a namespace
  void registerMigration(
    String namespace,
    int fromVersion,
    MigrationFunction migration,
  ) {
    _migrations.putIfAbsent(namespace, () => {})[fromVersion] = migration;
  }

  /// Get data with automatic migration
  Future<Map<String, dynamic>?> getWithMigration(
    String namespace,
    String key,
  ) async {
    final currentVersion = _getVersion(namespace);
    final data = getJson(namespace, key);

    if (data == null) return null;

    // Check if migration is needed
    if (currentVersion < _getLatestVersion(namespace)) {
      return _migrateData(namespace, data, currentVersion);
    }

    return data;
  }

  /// Get the latest registered version for a namespace
  int _getLatestVersion(String namespace) {
    final namespaceMigrations = _migrations[namespace];
    if (namespaceMigrations == null || namespaceMigrations.isEmpty) {
      return _defaultVersion;
    }
    return namespaceMigrations.keys.reduce((a, b) => a > b ? a : b) + 1;
  }

  /// Run migrations for data
  Future<Map<String, dynamic>> _migrateData(
    String namespace,
    Map<String, dynamic> data,
    int currentVersion,
  ) async {
    var migratedData = data;
    var version = currentVersion;
    final latestVersion = _getLatestVersion(namespace);
    final namespaceMigrations = _migrations[namespace];

    while (version < latestVersion) {
      final migration = namespaceMigrations?[version];
      if (migration != null) {
        migratedData = await migration(migratedData, version);
      }
      version++;
    }

    // Update version
    await _setVersion(namespace, latestVersion);

    return migratedData;
  }

  /// Set data with version tracking
  Future<void> setWithVersion(
    String namespace,
    String key,
    Map<String, dynamic> value, {
    int version = _defaultVersion,
    Duration debounce = const Duration(milliseconds: 300),
  }) async {
    await _setVersion(namespace, version);
    await setJson(namespace, key, value, debounce: debounce);
  }

  // ==================== Diagnostics ====================

  /// Get all keys in a namespace (for debugging)
  Set<String> getKeysInNamespace(String namespace) => _prefs.getKeys()
        .where((key) => key.startsWith('$_viewStatePrefix.$namespace.'))
        .toSet();

  /// Get all view state keys (for debugging)
  Set<String> getAllViewStateKeys() => _prefs.getKeys()
        .where((key) => key.startsWith(_viewStatePrefix))
        .toSet();

  /// Clear all view state data (use with caution)
  Future<void> clearAll() async {
    final keys = getAllViewStateKeys();
    for (final key in keys) {
      await _prefs.remove(key);
    }
  }
}

// ==================== Convenience Helpers ====================

/// Helper for enum serialization
class EnumSerializer {
  /// Serialize an enum to its name
  static String? serializeEnum<T extends Enum>(T? value) => value?.name;

  /// Deserialize an enum from its name
  static T? deserializeEnum<T extends Enum>(
    String? name,
    List<T> values,
  ) {
    if (name == null) return null;
    try {
      return values.firstWhere((e) => e.name == name);
    } catch (e) {
      return null;
    }
  }
}
