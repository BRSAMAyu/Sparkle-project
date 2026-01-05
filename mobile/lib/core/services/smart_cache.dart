import 'dart:collection';

/// 智能缓存管理器 - 支持LRU+时间限制清理
///
/// 功能:
/// 1. LRU (Least Recently Used) 淘汰策略
/// 2. 基于时间的过期清理
/// 3. 最大容量限制
/// 4. 内存使用监控
class SmartCache<K, V> {
  SmartCache({
    this.maxSize = 50,
    this.maxAge = const Duration(minutes: 5),
    this.onEvicted,
  });

  final int maxSize;
  final Duration maxAge;
  final void Function(K key, V value)? onEvicted;

  final LinkedHashMap<K, _CacheEntry<V>> _cache = LinkedHashMap();

  /// 获取缓存值
  V? get(K key) {
    final entry = _cache[key];
    if (entry == null) return null;

    // 检查是否过期
    if (DateTime.now().difference(entry.accessTime) > maxAge) {
      remove(key);
      return null;
    }

    // 更新访问时间并移到末尾（最近使用）
    _cache.remove(key);
    _cache[key] = _CacheEntry(
      value: entry.value,
      accessTime: DateTime.now(),
      createdTime: entry.createdTime,
    );

    return entry.value;
  }

  /// 设置缓存值
  void set(K key, V value) {
    // 如果key已存在，先移除
    if (_cache.containsKey(key)) {
      _cache.remove(key);
    }

    // 检查容量
    _cleanup();

    _cache[key] = _CacheEntry(
      value: value,
      accessTime: DateTime.now(),
      createdTime: DateTime.now(),
    );
  }

  /// 检查是否包含key
  bool containsKey(K key) {
    final entry = _cache[key];
    if (entry == null) return false;

    // 检查是否过期
    if (DateTime.now().difference(entry.accessTime) > maxAge) {
      remove(key);
      return false;
    }

    return true;
  }

  /// 移除指定key
  V? remove(K key) {
    final entry = _cache.remove(key);
    if (entry != null) {
      onEvicted?.call(key, entry.value);
      return entry.value;
    }
    return null;
  }

  /// 清空缓存
  void clear() {
    if (onEvicted != null) {
      for (final entry in _cache.entries) {
        onEvicted!(entry.key, entry.value.value);
      }
    }
    _cache.clear();
  }

  /// 获取当前缓存大小
  int get size => _cache.length;

  /// 获取所有key
  Iterable<K> get keys => _cache.keys;

  /// 获取所有值
  Iterable<V> get values => _cache.values.map((e) => e.value);

  /// 清理过期和超出容量的条目
  void _cleanup() {
    final now = DateTime.now();

    // 1. 清理过期条目
    final expiredKeys = <K>[];
    for (final entry in _cache.entries) {
      if (now.difference(entry.value.accessTime) > maxAge) {
        expiredKeys.add(entry.key);
      }
    }
    for (final key in expiredKeys) {
      remove(key);
    }

    // 2. 基于LRU清理超出容量的条目
    while (_cache.length >= maxSize) {
      final oldestKey = _cache.keys.first;
      remove(oldestKey);
    }
  }

  /// 手动触发清理
  void cleanup() => _cleanup();

  /// 获取缓存统计信息
  CacheStats get stats => CacheStats(
        size: _cache.length,
        maxSize: maxSize,
        oldestEntry: _cache.isNotEmpty
            ? DateTime.now().difference(_cache.values.first.createdTime)
            : Duration.zero,
        newestEntry: _cache.isNotEmpty
            ? DateTime.now().difference(_cache.values.last.createdTime)
            : Duration.zero,
      );
}

class _CacheEntry<V> {
  _CacheEntry({
    required this.value,
    required this.accessTime,
    required this.createdTime,
  });

  final V value;
  final DateTime accessTime;
  final DateTime createdTime;
}

/// 缓存统计信息
class CacheStats {
  const CacheStats({
    required this.size,
    required this.maxSize,
    required this.oldestEntry,
    required this.newestEntry,
  });

  final int size;
  final int maxSize;
  final Duration oldestEntry;
  final Duration newestEntry;

  double get utilizationRate => maxSize > 0 ? size / maxSize : 0;

  @override
  String toString() =>
      'CacheStats(size: $size/$maxSize, oldest: ${oldestEntry.inSeconds}s, newest: ${newestEntry.inSeconds}s)';
}

/// 带有大小估算的智能缓存
class SizedSmartCache<K, V> extends SmartCache<K, V> {
  SizedSmartCache({
    required this.sizeEstimator,
    super.maxSize = 50,
    super.maxAge = const Duration(minutes: 5),
    super.onEvicted,
    this.maxMemoryBytes = 100 * 1024 * 1024, // 100MB
  });

  final int maxMemoryBytes;
  final int Function(V value) sizeEstimator;

  int _currentMemoryBytes = 0;

  @override
  void set(K key, V value) {
    final valueSize = sizeEstimator(value);

    // 如果单个值超过最大内存，不缓存
    if (valueSize > maxMemoryBytes) {
      return;
    }

    // 清理直到有足够空间
    while (
        _currentMemoryBytes + valueSize > maxMemoryBytes && _cache.isNotEmpty) {
      final oldestKey = _cache.keys.first;
      final oldEntry = _cache[oldestKey];
      if (oldEntry != null) {
        _currentMemoryBytes -= sizeEstimator(oldEntry.value);
      }
      remove(oldestKey);
    }

    _currentMemoryBytes += valueSize;
    super.set(key, value);
  }

  @override
  V? remove(K key) {
    final entry = _cache[key];
    if (entry != null) {
      _currentMemoryBytes -= sizeEstimator(entry.value);
    }
    return super.remove(key);
  }

  @override
  void clear() {
    _currentMemoryBytes = 0;
    super.clear();
  }

  /// 获取当前内存使用量
  int get currentMemoryBytes => _currentMemoryBytes;

  /// 获取内存使用率
  double get memoryUtilization =>
      maxMemoryBytes > 0 ? _currentMemoryBytes / maxMemoryBytes : 0;
}
