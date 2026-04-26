import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/view_storage_service.dart';

/// Signature for converting state to JSON
typedef StateToJson<T> = Map<String, dynamic> Function(T state);

/// Signature for converting JSON to state
typedef StateFromJson<T> = T? Function(Map<String, dynamic> json);

/// Signature for listening to state changes
///
/// **Important**: State changes are detected using the `==` operator.
/// Ensure your state class properly overrides `==` and `hashCode` for
/// accurate change detection.
typedef StateChangeListener<T> = void Function(T oldState, T newState);

/// A StateNotifier that automatically persists and restores its state.
///
/// Features:
/// - Auto-loads state from storage on initialization
/// - Auto-saves state on change (with debouncing)
/// - Fallback to default state if loading fails
/// - Optional selective persistence (persist only specific fields)
/// - State change listeners for behavior analytics
///
/// **State Equality**: Your state class MUST override `==` and `hashCode`
/// for accurate change detection. Without this, listeners may not fire
/// when content changes, or may fire unexpectedly.
///
/// Usage:
/// ```dart
/// class MyNotifier extends PersistentStateNotifier<MyState> {
///   MyNotifier(super.ref) : super(
///     namespace: 'my_feature',
///     key: 'state',
///     defaultValue: MyState(),
///     toJson: (s) => s.toJson(),
///     fromJson: (j) => MyState.fromJson(j),
///   );
///
///   void updateValue(String newValue) {
///     state = state.copyWith(value: newValue); // Auto-saves
///   }
/// }
/// ```
abstract class PersistentStateNotifier<T> extends StateNotifier<T> {
  PersistentStateNotifier(
    this.ref, {
    required this.namespace,
    required this.key,
    required this.defaultValue,
    required this.toJson,
    required this.fromJson,
    this.debounce = const Duration(milliseconds: 300),
    this.enabled = true,
  }) : super(defaultValue) {
    _storage = ViewStorageService.instance;
    if (enabled) {
      _loadState();
    }
  }

  /// The Ref for accessing other providers
  final Ref ref;

  /// Storage namespace (e.g., 'task_board', 'chat_mode')
  final String namespace;

  /// Storage key within namespace (e.g., 'state', 'selected_id')
  final String key;

  /// Default value to use if loading fails or is disabled
  final T defaultValue;

  /// Serialize state to JSON
  final StateToJson<T> toJson;

  /// Deserialize JSON to state
  final StateFromJson<T> fromJson;

  /// Debounce duration for auto-save
  final Duration debounce;

  /// Whether persistence is enabled
  final bool enabled;

  late final ViewStorageService _storage;
  Timer? _saveTimer;
  bool _isLoaded = false;
  final List<StateChangeListener<T>> _listeners = [];

  /// Load state from storage
  Future<void> _loadState() async {
    try {
      final json = await _storage.getWithMigration(namespace, key);
      if (json != null) {
        final loadedState = fromJson(json);
        if (loadedState != null) {
          state = loadedState;
          _isLoaded = true;
          debugPrint('PersistentStateNotifier: Loaded state for $namespace.$key');
          return;
        }
      }
      _isLoaded = true;
    } catch (e) {
      debugPrint('PersistentStateNotifier: Failed to load state for $namespace.$key: $e');
      _isLoaded = true;
    }
  }

  /// Save state to storage (with debouncing)
  void _scheduleSave() {
    if (!enabled) return;

    _saveTimer?.cancel();
    _saveTimer = Timer(debounce, () async {
      await _saveState();
    });
  }

  /// Save state to storage immediately
  Future<void> _saveState() async {
    if (!enabled) return;

    try {
      final json = toJson(state);
      await _storage.setJson(
        namespace,
        key,
        json,
        debounce: Duration.zero,
      );
    } catch (e) {
      debugPrint('PersistentStateNotifier: Failed to save state for $namespace.$key: $e');
    }
  }

  /// Save immediately (override debounce)
  Future<void> saveImmediate() async {
    _saveTimer?.cancel();
    await _saveState();
  }

  /// Force reload state from storage
  Future<void> reload() async {
    await _loadState();
  }

  /// Reset to default value and clear storage
  Future<void> reset() async {
    state = defaultValue;
    try {
      await _storage.remove(namespace, key);
    } catch (e) {
      debugPrint('PersistentStateNotifier: Failed to clear storage for $namespace.$key: $e');
    }
  }

  @override
  set state(T value) {
    final oldState = state;
    super.state = value;
    if (_isLoaded) {
      _scheduleSave();
    }
    // Notify listeners (skip initial load)
    if (_isLoaded && oldState != value) {
      for (var i = 0; i < _listeners.length; i++) {
        try {
          _listeners[i](oldState, value);
        } catch (e, stackTrace) {
          debugPrint('[$namespace.$key] StateListener #$i error: $e\n'
              '  oldState: $oldState\n  newState: $value\n'
              '  stackTrace: $stackTrace');
        }
      }
    }
  }

  /// Add a state change listener.
  ///
  /// Returns `true` if the listener was added, `false` if it was already
  /// registered (duplicate listeners are prevented).
  bool addStateListener(StateChangeListener<T> listener) {
    if (_listeners.contains(listener)) {
      debugPrint('[$namespace.$key] Duplicate listener ignored');
      return false;
    }
    _listeners.add(listener);
    return true;
  }

  /// Remove a state change listener.
  ///
  /// Returns `true` if the listener was found and removed, `false` otherwise.
  bool removeStateListener(StateChangeListener<T> listener) => _listeners.remove(listener);

  /// Clear all listeners.
  ///
  /// Returns the number of listeners that were removed.
  int clearStateListeners() {
    final count = _listeners.length;
    _listeners.clear();
    return count;
  }

  /// Get the current number of registered listeners.
  int get listenerCount => _listeners.length;

  @override
  void dispose() {
    _saveTimer?.cancel();
    _listeners.clear();
    super.dispose();
  }
}

/// A simplified persistent notifier for single-value state (enums, strings, etc.)
///
/// Usage:
/// ```dart
/// final myModeProvider = PersistentProvider<String>(
///   namespace: 'chat',
///   key: 'mode',
///   defaultValue: 'standard',
///   serializer: (s) => s,
///   deserializer: (s) => s,
/// );
/// ```
class PersistentNotifier<T> extends StateNotifier<T> {
  PersistentNotifier({
    required this.namespace,
    required this.key,
    required this.defaultValue,
    required String? Function(T) serializer,
    required T? Function(String?) deserializer,
    this.debounce = const Duration(milliseconds: 300),
    this.enabled = true,
  })  : _serializer = serializer,
        _deserializer = deserializer,
        super(defaultValue) {
    _storage = ViewStorageService.instance;
    if (enabled) {
      _loadState();
    }
  }

  /// Storage namespace
  final String namespace;

  /// Storage key within namespace
  final String key;

  /// Default value
  final T defaultValue;

  /// Serialize value to string
  final String? Function(T) _serializer;

  /// Deserialize value from string
  final T? Function(String?) _deserializer;

  /// Debounce duration
  final Duration debounce;

  /// Whether persistence is enabled
  final bool enabled;

  late final ViewStorageService _storage;
  Timer? _saveTimer;
  bool _isLoaded = false;
  final List<StateChangeListener<T>> _listeners = [];

  /// Load value from storage
  Future<void> _loadState() async {
    try {
      final storedValue = _storage.getString(namespace, key);
      if (storedValue != null) {
        final loadedValue = _deserializer(storedValue);
        if (loadedValue != null) {
          state = loadedValue;
          _isLoaded = true;
          return;
        }
      }
      _isLoaded = true;
    } catch (e) {
      debugPrint('PersistentNotifier: Failed to load $namespace.$key: $e');
      _isLoaded = true;
    }
  }

  /// Save value to storage (with debouncing)
  void _scheduleSave() {
    if (!enabled) return;

    _saveTimer?.cancel();
    _saveTimer = Timer(debounce, () async {
      await _saveState();
    });
  }

  /// Save value to storage immediately
  Future<void> _saveState() async {
    if (!enabled) return;

    try {
      final serialized = _serializer(state);
      if (serialized != null) {
        await _storage.setString(namespace, key, serialized, debounce: debounce);
      } else {
        await _storage.remove(namespace, key);
      }
    } catch (e) {
      debugPrint('PersistentNotifier: Failed to save $namespace.$key: $e');
    }
  }

  /// Save immediately (override debounce)
  Future<void> saveImmediate() async {
    _saveTimer?.cancel();
    await _saveState();
  }

  /// Force reload from storage
  Future<void> reload() async {
    await _loadState();
  }

  /// Reset to default value and clear storage
  Future<void> reset() async {
    state = defaultValue;
    try {
      await _storage.remove(namespace, key);
    } catch (e) {
      debugPrint('PersistentNotifier: Failed to clear storage for $namespace.$key: $e');
    }
  }

  @override
  set state(T value) {
    final oldState = state;
    super.state = value;
    if (_isLoaded) {
      _scheduleSave();
    }
    // Notify listeners (skip initial load)
    if (_isLoaded && oldState != value) {
      for (var i = 0; i < _listeners.length; i++) {
        try {
          _listeners[i](oldState, value);
        } catch (e, stackTrace) {
          debugPrint('[$namespace.$key] StateListener #$i error: $e\n'
              '  oldState: $oldState\n  newState: $value\n'
              '  stackTrace: $stackTrace');
        }
      }
    }
  }

  /// Add a state change listener.
  ///
  /// Returns `true` if the listener was added, `false` if it was already
  /// registered (duplicate listeners are prevented).
  bool addStateListener(StateChangeListener<T> listener) {
    if (_listeners.contains(listener)) {
      debugPrint('[$namespace.$key] Duplicate listener ignored');
      return false;
    }
    _listeners.add(listener);
    return true;
  }

  /// Remove a state change listener.
  ///
  /// Returns `true` if the listener was found and removed, `false` otherwise.
  bool removeStateListener(StateChangeListener<T> listener) => _listeners.remove(listener);

  /// Clear all listeners.
  ///
  /// Returns the number of listeners that were removed.
  int clearStateListeners() {
    final count = _listeners.length;
    _listeners.clear();
    return count;
  }

  /// Get the current number of registered listeners.
  int get listenerCount => _listeners.length;

  @override
  void dispose() {
    _saveTimer?.cancel();
    _listeners.clear();
    super.dispose();
  }
}

/// Provider for a PersistentNotifier
typedef PersistentProvider<T> = StateNotifierProvider<PersistentNotifier<T>, T>;

/// Create a provider for a PersistentNotifier
PersistentProvider<T> makePersistentProvider<T>({
  required String namespace,
  required String key,
  required T defaultValue,
  required String? Function(T) serializer,
  required T? Function(String?) deserializer,
  Duration debounce = const Duration(milliseconds: 300),
  bool enabled = true,
}) => StateNotifierProvider<PersistentNotifier<T>, T>((ref) => PersistentNotifier<T>(
      namespace: namespace,
      key: key,
      defaultValue: defaultValue,
      serializer: serializer,
      deserializer: deserializer,
      debounce: debounce,
      enabled: enabled,
    ),);

// ==================== Specialized Notifiers ====================

/// Persistent notifier for enum values
class EnumPersistentNotifier<T extends Enum> extends PersistentNotifier<T> {
  EnumPersistentNotifier({
    required super.namespace,
    required super.key,
    required super.defaultValue,
    required List<T> values,
    super.debounce,
    super.enabled,
  }) : super(
          serializer: (e) => e.name,
          deserializer: (s) => EnumSerializer.deserializeEnum(s, values),
        );

  /// Get the current enum value
  T get currentValue => state;

  /// Set a new enum value
  void setValue(T value) {
    state = value;
  }
}

/// Persistent notifier for string values
class StringPersistentNotifier extends PersistentNotifier<String> {
  StringPersistentNotifier({
    required super.namespace,
    required super.key,
    super.defaultValue = '',
    super.debounce,
    super.enabled,
  }) : super(
          serializer: (s) => s,
          deserializer: (s) => s ?? '',
        );
}

/// Persistent notifier for int values
class IntPersistentNotifier extends PersistentNotifier<int> {
  IntPersistentNotifier({
    required super.namespace,
    required super.key,
    super.defaultValue = 0,
    super.debounce,
    super.enabled,
  }) : super(
          serializer: (i) => i.toString(),
          deserializer: (s) => int.tryParse(s ?? ''),
        );
}

/// Persistent notifier for double values
class DoublePersistentNotifier extends PersistentNotifier<double> {
  DoublePersistentNotifier({
    required super.namespace,
    required super.key,
    super.defaultValue = 0.0,
    super.debounce,
    super.enabled,
  }) : super(
          serializer: (d) => d.toString(),
          deserializer: (s) => double.tryParse(s ?? ''),
        );
}

/// Persistent notifier for bool values
class BoolPersistentNotifier extends PersistentNotifier<bool> {
  BoolPersistentNotifier({
    required super.namespace,
    required super.key,
    super.defaultValue = false,
    super.debounce,
    super.enabled,
  }) : super(
          serializer: (b) => b ? '1' : '0',
          deserializer: (s) => s == '1',
        );
}

/// Persistent notifier for StringSet values
class StringSetPersistentNotifier extends StateNotifier<Set<String>> {
  StringSetPersistentNotifier({
    required this.namespace,
    required this.key,
    Set<String> defaultValue = const {},
    this.debounce = const Duration(milliseconds: 300),
    this.enabled = true,
  }) : super(defaultValue) {
    _storage = ViewStorageService.instance;
    if (enabled) {
      _loadState();
    }
  }

  /// Storage namespace
  final String namespace;

  /// Storage key within namespace
  final String key;

  /// Debounce duration
  final Duration debounce;

  /// Whether persistence is enabled
  final bool enabled;

  late final ViewStorageService _storage;
  Timer? _saveTimer;
  bool _isLoaded = false;
  final List<StateChangeListener<Set<String>>> _listeners = [];

  /// Load set from storage
  Future<void> _loadState() async {
    try {
      final storedSet = _storage.getStringSet(namespace, key);
      if (storedSet != null) {
        state = storedSet;
      }
      _isLoaded = true;
    } catch (e) {
      debugPrint('StringSetPersistentNotifier: Failed to load $namespace.$key: $e');
      _isLoaded = true;
    }
  }

  /// Save set to storage (with debouncing)
  void _scheduleSave() {
    if (!enabled) return;

    _saveTimer?.cancel();
    _saveTimer = Timer(debounce, () async {
      await _saveState();
    });
  }

  /// Save set to storage immediately
  Future<void> _saveState() async {
    if (!enabled) return;

    try {
      await _storage.setStringSet(namespace, key, state, debounce: debounce);
    } catch (e) {
      debugPrint('StringSetPersistentNotifier: Failed to save $namespace.$key: $e');
    }
  }

  /// Add an item to the set
  void add(String item) {
    state = {...state, item};
  }

  /// Remove an item from the set
  void remove(String item) {
    final newState = Set<String>.from(state);
    newState.remove(item);
    state = newState;
  }

  /// Toggle an item in the set
  void toggle(String item) {
    if (state.contains(item)) {
      remove(item);
    } else {
      add(item);
    }
  }

  /// Clear the set
  void clear() {
    state = {};
  }

  /// Save immediately (override debounce)
  Future<void> saveImmediate() async {
    _saveTimer?.cancel();
    await _saveState();
  }

  /// Reset to empty and clear storage
  Future<void> reset() async {
    state = {};
    try {
      await _storage.remove(namespace, key);
    } catch (e) {
      debugPrint('StringSetPersistentNotifier: Failed to clear storage for $namespace.$key: $e');
    }
  }

  @override
  set state(Set<String> value) {
    final oldState = state;
    super.state = value;
    if (_isLoaded) {
      _scheduleSave();
    }
    // Notify listeners (skip initial load)
    if (_isLoaded && oldState != value) {
      for (var i = 0; i < _listeners.length; i++) {
        try {
          _listeners[i](oldState, value);
        } catch (e, stackTrace) {
          debugPrint('[$namespace.$key] StateListener #$i error: $e\n'
              '  oldState: $oldState\n  newState: $value\n'
              '  stackTrace: $stackTrace');
        }
      }
    }
  }

  /// Add a state change listener.
  ///
  /// Returns `true` if the listener was added, `false` if it was already
  /// registered (duplicate listeners are prevented).
  bool addStateListener(StateChangeListener<Set<String>> listener) {
    if (_listeners.contains(listener)) {
      debugPrint('[$namespace.$key] Duplicate listener ignored');
      return false;
    }
    _listeners.add(listener);
    return true;
  }

  /// Remove a state change listener.
  ///
  /// Returns `true` if the listener was found and removed, `false` otherwise.
  bool removeStateListener(StateChangeListener<Set<String>> listener) => _listeners.remove(listener);

  /// Clear all listeners.
  ///
  /// Returns the number of listeners that were removed.
  int clearStateListeners() {
    final count = _listeners.length;
    _listeners.clear();
    return count;
  }

  /// Get the current number of registered listeners.
  int get listenerCount => _listeners.length;

  @override
  void dispose() {
    _saveTimer?.cancel();
    _listeners.clear();
    super.dispose();
  }
}
